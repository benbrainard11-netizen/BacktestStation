"""STAGE 1 -- do GEX levels PULL price toward them (magnets), or not?

For each candidate magnet, at sampled intraday times run the SYMMETRIC RACE: with the level at signed distance d
from spot, does price reach the magnet (at +d) before an equidistant MIRROR (at -d)? It's literally the trade
(target=magnet, stop=mirror, win=+1R loss=-1R minus cost). No-lookahead: level + spot known at T0, outcome is the
future path.

DRIFT/GEOMETRY CONTROL = a same-side PLACEBO: race to a RANDOM level at the same side and a shuffled distance.
Real-minus-placebo cancels market drift and the distance distribution, isolating whether the SPECIFIC magnet
location attracts price. Split by side too (a real magnet pulls both; drift only lifts one).

Magnets: HTF (standing book re-priced on live spot) pin/call_wall/put_wall/zero_gamma [intraday_gex_spx];
LTF (today's live 0DTE flow) pin0dte [dte0_intraday_spx]. Reads options_signals_v0/out/*.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import boot  # noqa: E402

GEX = Path(__file__).resolve().parents[1] / "options_signals_v0" / "out"
OBS = list(range(36_000_000, 50_400_001, 1_800_000))   # 10:00..14:00 ET, every 30 min
H_MS = 120 * 60_000                                    # 120-min race horizon
COST, PTV = 26.5, 50.0                                 # ES proxy: $26.5 round-turn, $50/pt
ATR_WIN, LO, HI = 14, 0.10, 1.50                       # distance band in prior-day ATR
INF = 10**9


def atr_by_day(g: pd.DataFrame) -> dict:
    rng = g.groupby("date")["spot"].agg(lambda s: float(s.max() - s.min()))
    return rng.rolling(ATR_WIN, min_periods=5).mean().shift(1).to_dict()           # prior-day, no lookahead


def collect(col: str, g: pd.DataFrame) -> list:
    """Resolved-able observations: (day, d, S0, forward-path). One per (session, obs-time) in the distance band."""
    atr = atr_by_day(g[["date", "spot"]])
    obs = []
    for day, dd in g.groupby("date"):
        a = atr.get(day, np.nan)
        if not (a and a > 0):
            continue
        dd = dd.sort_values("ms_of_day")
        ms, sp, lv = dd["ms_of_day"].to_numpy(), dd["spot"].to_numpy(float), dd[col].to_numpy(float)
        for t0 in OBS:
            j = int(np.searchsorted(ms, t0))
            if j >= len(ms):
                continue
            S0, L = sp[j], lv[j]
            if not np.isfinite(L):
                continue
            d = L - S0
            if abs(d) < LO * a or abs(d) > HI * a:
                continue
            fut = sp[(ms > ms[j]) & (ms <= ms[j] + H_MS)]
            if len(fut):
                obs.append((int(day), float(d), float(S0), fut))
    return obs


def _race(S0: float, d: float, path: np.ndarray) -> float:
    """+1 if price reaches S0+d before S0-d, -1 if the mirror first, nan if neither within the horizon."""
    th = np.where(path >= S0 + d if d > 0 else path <= S0 + d)[0]
    mh = np.where(path <= S0 - d if d > 0 else path >= S0 - d)[0]
    t = th[0] if len(th) else INF
    m = mh[0] if len(mh) else INF
    if t == INF and m == INF:
        return np.nan
    return 1.0 if t < m else -1.0


def score(name: str, obs: list) -> None:
    if len(obs) < 30:
        print(f"  {name:11} thin ({len(obs)} obs)")
        return
    rng = np.random.default_rng(0)
    for lab, side in [("both sides", 0), ("long (above)", 1), ("short (below)", -1)]:
        sub = [o for o in obs if side == 0 or np.sign(o[1]) == side]
        if len(sub) < 20:
            print(f"  {name:11} {lab:13} n<20")
            continue
        pool = np.abs([o[1] for o in sub])                       # same-side distance distribution
        rr, pr, dy = [], [], []
        for day, d, S0, path in sub:
            ro = _race(S0, d, path)
            dp = float(rng.choice(pool)) * (1.0 if d > 0 else -1.0)
            po = _race(S0, dp, path)
            if np.isnan(ro) or np.isnan(po):                     # paired: keep only where both resolve
                continue
            rr.append(ro - COST / (abs(d) * PTV))
            pr.append(po - COST / (abs(dp) * PTV))
            dy.append(day)
        if len(rr) < 20:
            print(f"  {name:11} {lab:13} thin paired ({len(rr)})")
            continue
        rr, pr, dy = np.array(rr), np.array(pr), np.array(dy)
        m, lo, hi = boot(rr, dy)
        pm = pr.mean()
        diff, dl, dh = boot(rr - pr, dy)
        flag = "  <== PULLS (edge CI>0)" if dl > 0 else ""
        print(f"  {name:11} {lab:13} R {m:+.2f}[{lo:+.2f},{hi:+.2f}] wr{(rr > 0).mean():.2f}  "
              f"placebo {pm:+.2f}  EDGE {diff:+.2f}[{dl:+.2f},{dh:+.2f}] n{len(rr)}{flag}")


def main() -> int:
    htf = pd.read_parquet(GEX / "intraday_gex_spx.parquet")
    print(f"HTF magnets (standing book re-priced on live spot) -- {htf['date'].nunique()} days. "
          f"EDGE = real minus same-side placebo (drift-removed):\n")
    for col in ["pin", "call_wall", "put_wall", "zero_gamma"]:
        if col in htf.columns:
            score(col, collect(col, htf[["date", "ms_of_day", "spot", col]]))
    ltf = GEX / "dte0_intraday_spx.parquet"
    if ltf.exists():
        d0 = pd.read_parquet(ltf)
        if "pin" in d0.columns:
            print(f"\nLTF magnet (today's live 0DTE flow) -- {d0['date'].nunique()} days:")
            score("pin0dte", collect("pin", d0[["date", "ms_of_day", "spot", "pin"]]))
    print("\nREAD: EDGE (real - placebo) CI>0 on BOTH sides = a genuine, drift-free pull. EDGE ~0 = the level isn't "
          "special, the raw R was drift/geometry. This is the mirage check before any full-range pull.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
