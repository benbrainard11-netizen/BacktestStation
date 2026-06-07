"""STAGE 2 -- make the 0DTE pin magnet TRADEABLE: when does it pull hardest?

Theory: dealers PIN price toward the max-gamma strike when they're NET LONG GAMMA (they buy dips / sell rips ->
mean-revert price to the gamma peak). When NET SHORT GAMMA they amplify moves -> no pin, price runs. So the pin
should be a magnet only in the long-gamma regime. We split the pin reach-race (target = pin, stop = equidistant
mirror; drift removed vs a same-side shuffled-distance placebo) by GAMMA REGIME (net_gex sign at entry, no-look-
ahead) x side. The cell with EDGE > 0 AND raw R > 0 = the tradeable pin setup -- the entry filter on top of the
raw magnet. Reads options_signals_v0/out/dte0_intraday_spx.parquet (today's live 0DTE flow).
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
H_MS = 120 * 60_000
COST, PTV = 26.5, 50.0                                  # ES proxy
ATR_WIN, LO, HI = 14, 0.10, 1.50
INF = 10**9


def atr_by_day(g: pd.DataFrame) -> dict:
    rng = g.groupby("date")["spot"].agg(lambda s: float(s.max() - s.min()))
    return rng.rolling(ATR_WIN, min_periods=5).mean().shift(1).to_dict()


def _race(S0: float, d: float, path: np.ndarray) -> float:
    th = np.where(path >= S0 + d if d > 0 else path <= S0 + d)[0]
    mh = np.where(path <= S0 - d if d > 0 else path >= S0 - d)[0]
    t = th[0] if len(th) else INF
    m = mh[0] if len(mh) else INF
    if t == INF and m == INF:
        return np.nan
    return 1.0 if t < m else -1.0


def collect(g: pd.DataFrame) -> list:
    """(day, d, S0, forward-path, net_gex) per obs in the distance band."""
    atr = atr_by_day(g[["date", "spot"]])
    obs = []
    for day, dd in g.groupby("date"):
        a = atr.get(day, np.nan)
        if not (a and a > 0):
            continue
        dd = dd.sort_values("ms_of_day")
        ms = dd["ms_of_day"].to_numpy()
        sp = dd["spot"].to_numpy(float)
        pin = dd["pin"].to_numpy(float)
        ng = dd["net_gex"].to_numpy(float)
        for t0 in OBS:
            j = int(np.searchsorted(ms, t0))
            if j >= len(ms):
                continue
            S0, L, gg = sp[j], pin[j], ng[j]
            if not (np.isfinite(L) and np.isfinite(gg)):
                continue
            d = L - S0
            if abs(d) < LO * a or abs(d) > HI * a:
                continue
            fut = sp[(ms > ms[j]) & (ms <= ms[j] + H_MS)]
            if len(fut):
                obs.append((int(day), float(d), float(S0), fut, float(gg)))
    return obs


def cell(name: str, obs: list) -> None:
    if len(obs) < 25:
        print(f"  {name:24} thin ({len(obs)})")
        return
    rng = np.random.default_rng(0)
    pool = np.abs([o[1] for o in obs])
    rr, pr, dy = [], [], []
    for day, d, S0, path, _ in obs:
        ro = _race(S0, d, path)
        dp = float(rng.choice(pool)) * (1.0 if d > 0 else -1.0)
        po = _race(S0, dp, path)
        if np.isnan(ro) or np.isnan(po):
            continue
        rr.append(ro - COST / (abs(d) * PTV))
        pr.append(po - COST / (abs(dp) * PTV))
        dy.append(day)
    if len(rr) < 20:
        print(f"  {name:24} thin paired ({len(rr)})")
        return
    rr, pr, dy = np.array(rr), np.array(pr), np.array(dy)
    m, lo, hi = boot(rr, dy)
    diff, dl, dh = boot(rr - pr, dy)
    flag = "  <== TRADEABLE (R>0 & edge>0)" if (lo > 0 and dl > 0) else ("  edge>0" if dl > 0 else "")
    print(f"  {name:24} R {m:+.2f}[{lo:+.2f},{hi:+.2f}] wr{(rr > 0).mean():.2f}  EDGE {diff:+.2f}[{dl:+.2f},{dh:+.2f}] n{len(rr)}{flag}")


def main() -> int:
    g = pd.read_parquet(GEX / "dte0_intraday_spx.parquet")[["date", "ms_of_day", "spot", "pin", "net_gex"]]
    obs = collect(g)
    print(f"0DTE pin trades: {len(obs)} obs over {g['date'].nunique()} days (target=pin, stop=mirror)\n")
    print("by GAMMA REGIME x side (EDGE = drift-removed vs same-side placebo):")
    for rlab, rok in [("long-gamma net>0", lambda gg: gg > 0), ("short-gamma net<0", lambda gg: gg < 0)]:
        for slab, sok in [("both", lambda d: True), ("long", lambda d: d > 0), ("short", lambda d: d < 0)]:
            cell(f"{rlab} / {slab}", [o for o in obs if rok(o[4]) and sok(o[1])])
        print()
    print("READ: pin should pull in LONG-GAMMA (dealers mean-revert), not short-gamma. A long-gamma cell with R>0 "
          "AND edge>0 = the tradeable pin setup -- the regime is the entry filter. (59d now; re-run on full range.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
