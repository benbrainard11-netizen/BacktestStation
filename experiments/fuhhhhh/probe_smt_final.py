"""Final honesty checks on the NQ-vs-ES SMT SHORT edge before verdict.

Q1. Is the edge the CROSS-ASSET divergence, or just "NQ made a fresh HH => mean-revert short"?
    Control: short on every NQ fresh-HH (the same NQ pivot trigger) WITHOUT requiring ES to
    diverge (ES makes HH too, or LH). If the no-divergence subset is also short-profitable,
    the SMT cross-asset part adds nothing.
Q2. drop-WORST-2 and drop-best-2 together (robustness band) on short leg.
Q3. shuffled-y control on the short subset (permute up/down labels) — standard control.
Q4. recent-regime isolation: train sign on pre-2026 only, apply to 2026 (true forward).
Q5. cost stress: double the cost (subtract another 0.69 NQ pts from each R) — still > 0?
"""
from __future__ import annotations

import sys
from datetime import date as Date
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
from build_xasset_feats import load_day_et, fractal_pivots

ET = ZoneInfo(C.ET)
OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20260613)
NQ_ROOT = C.BARS_1M_ROOT / "symbol=NQ.c.0"
ES_ROOT = C.BARS_1M_ROOT / "symbol=ES.c.0"


def block_boot(df, col="r", b=4000):
    days = df["date"].unique()
    by = {d: df[df["date"] == d][col].to_numpy() for d in days}
    means = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean()
                      for _ in range(b)])
    return float(df[col].mean()), float((means <= 0).mean())


def nq_hh_es_state(nq, es, ms, k=3, fresh=20):
    """At decision ms, did NQ make a fresh confirmed HH (vs prior HH)? If so, what did ES do
    at the two pivot times? Returns (nq_made_hh, es_diverged) where es_diverged=True means ES
    LH (the SMT short). Also returns nq_made_ll / es_diverged_bull for the long side."""
    nmask = nq["close_ms"].to_numpy() <= ms; emask = es["close_ms"].to_numpy() <= ms
    ni = np.nonzero(nmask)[0]; ei = np.nonzero(emask)[0]
    if len(ni) < 2 * k + 3 or len(ei) < 2 * k + 3:
        return None
    nci, eci = ni[-1], ei[-1]
    nl = nq["low"].to_numpy()[:nci+1]; nh = nq["high"].to_numpy()[:nci+1]
    el = es["low"].to_numpy()[:eci+1]; eh = es["high"].to_numpy()[:eci+1]
    n_cms = nq["close_ms"].to_numpy()[:nci+1]; e_cms = es["close_ms"].to_numpy()[:eci+1]
    nlo, nhi = fractal_pivots(nl, nh, k)
    cutoff = nci - k
    nlo = nlo[nlo <= cutoff]; nhi = nhi[nhi <= cutoff]
    res = dict(nq_hh=False, es_lh=False, nq_ll=False, es_hl=False)
    def es_at(cms, arr):
        j = np.searchsorted(e_cms, cms, side="right") - 1
        return arr[j] if j >= 0 else np.nan
    if len(nhi) >= 2 and (nci - nhi[-1]) <= fresh:
        p1, p2 = nhi[-2], nhi[-1]
        if nh[p2] > nh[p1]:
            res["nq_hh"] = True
            e1, e2 = es_at(n_cms[p1], eh), es_at(n_cms[p2], eh)
            if np.isfinite(e1) and np.isfinite(e2):
                res["es_lh"] = bool(e2 < e1)
    if len(nlo) >= 2 and (nci - nlo[-1]) <= fresh:
        p1, p2 = nlo[-2], nlo[-1]
        if nl[p2] < nl[p1]:
            res["nq_ll"] = True
            e1, e2 = es_at(n_cms[p1], el), es_at(n_cms[p2], el)
            if np.isfinite(e1) and np.isfinite(e2):
                res["es_hl"] = bool(e2 > e1)
    return res


def main() -> int:
    ds = pd.read_parquet(OUT / "dataset_ndx.parquet")
    assert ds["date"].max() < "2026-04-01"
    ds = ds[ds["y"].isin([0, 1])].copy()
    states = {}
    for d, grp in ds.groupby("date"):
        day = Date.fromisoformat(d)
        nq = load_day_et(NQ_ROOT, day); es = load_day_et(ES_ROOT, day)
        if nq is None or es is None:
            continue
        for ms in grp["ms"].tolist():
            states[(d, int(ms))] = nq_hh_es_state(nq, es, int(ms))
    for kk in ["nq_hh", "es_lh", "nq_ll", "es_hl"]:
        ds[kk] = [bool(states.get((d, int(m)) , {}).get(kk, False)) if states.get((d, int(m))) else False
                  for d, m in zip(ds.date, ds.ms)]
    ds["mo"] = ds["date"].str.slice(0, 7)

    print("### Q1. cross-asset divergence vs raw NQ-HH (short side)")
    # SMT short = NQ HH + ES LH ; control = NQ HH + ES NOT LH (ES also made HH/equal)
    smt_sh = ds[ds.nq_hh & ds.es_lh].copy(); smt_sh["r"] = smt_sh["r_short"]
    ctl_sh = ds[ds.nq_hh & ~ds.es_lh].copy(); ctl_sh["r"] = ctl_sh["r_short"]
    for tag, sub in [("SMT short (NQ HH & ES LH)", smt_sh), ("CTRL short (NQ HH & ES !LH)", ctl_sh)]:
        m, p = block_boot(sub)
        bymo = sub.groupby("mo")["r"].mean().sort_values(ascending=False)
        d2 = sub[~sub.mo.isin(bymo.index[:2])]["r"].mean()
        print(f"  {tag:32s} R={m:+.4f} p={p:.3f} win%={(sub.r>0).mean()*100:.1f} drop2={d2:+.4f} "
              f"mo+={int((bymo>0).sum())}/{len(bymo)} n={len(sub)}")

    print("\n### Q1b. long side (NQ LL & ES HL) vs control")
    smt_lo = ds[ds.nq_ll & ds.es_hl].copy(); smt_lo["r"] = smt_lo["r_long"]
    ctl_lo = ds[ds.nq_ll & ~ds.es_hl].copy(); ctl_lo["r"] = ctl_lo["r_long"]
    for tag, sub in [("SMT long (NQ LL & ES HL)", smt_lo), ("CTRL long (NQ LL & ES !HL)", ctl_lo)]:
        m, p = block_boot(sub)
        print(f"  {tag:32s} R={m:+.4f} p={p:.3f} win%={(sub.r>0).mean()*100:.1f} n={len(sub)}")

    sh = smt_sh  # the headline short edge
    print(f"\n### Q2. robustness band (short, n={len(sh)})")
    bymo = sh.groupby("mo")["r"].mean().sort_values(ascending=False)
    print("  per-month:", {k: round(v, 3) for k, v in sh.groupby("mo")["r"].mean().items()})
    print(f"  full={sh['r'].mean():+.4f}  drop-best-2={sh[~sh.mo.isin(bymo.index[:2])]['r'].mean():+.4f}  "
          f"drop-WORST-2={sh[~sh.mo.isin(bymo.index[-2:])]['r'].mean():+.4f}")

    print("\n### Q3. shuffled-y control (permute up/down outcome labels, 2000x) on short subset")
    # y here: a short 'wins' when move is down. Shuffle which rows are down vs up, recompute r_short proxy.
    # Cleaner: shuffle the actual r_short across the subset's own rows is trivial-mean-preserving;
    # instead permute the SMT membership: draw n random NQ-HH rows (any ES state) and short them.
    pool = ds[ds.nq_hh].copy()  # all NQ-HH rows
    obs = sh["r"].mean(); n = len(sh)
    draws = []
    for _ in range(2000):
        idx = RNG.choice(len(pool), n, replace=False)
        draws.append(pool["r_short"].to_numpy()[idx].mean())
    draws = np.array(draws)
    print(f"  observed short R={obs:+.4f}  random-NQ-HH-subset mean={draws.mean():+.4f} "
          f"(std {draws.std():.4f})  p(random>=obs)={float((draws>=obs).mean()):.4f}")

    print("\n### Q4. true-forward: sign known a-priori, eval ONLY on 2026 (Jan-Mar dev)")
    pre = sh[sh.date < "2026-01-01"]; post = sh[sh.date >= "2026-01-01"]
    print(f"  pre-2026 short R={pre['r'].mean():+.4f} n={len(pre)}   "
          f"2026(Jan-Mar) short R={post['r'].mean():+.4f} n={len(post)}")

    print("\n### Q5. cost stress: subtract another full round-trip (0.69 NQ pts) from each short R")
    # r is in R-units (per 0.5*ATR stop). Convert extra cost to R: extra_pts / stop_pts.
    # stop ~ 0.5*ATR; approximate using geo_atr if present else use median. Use dataset r scale:
    # r already net of 1x cost; doubling cost subtracts cost_R. cost_R ~ COST_PTS_NQ / (0.10*ATR? )
    # The move target is 0.10*ATR; r_long/short are net-cost bracket R. Extra 0.69 pts as fraction of
    # the ~target distance. Use median ATR to estimate stop in pts.
    atr = ds["geo_atr"].median() if "geo_atr" in ds else 350.0
    # label move = 0.10*ATR points; bracket R denominated by that move; cost in R = COST/(0.10*ATR)
    extra_R = C.COST_PTS_NQ / (0.10 * atr)
    sh2 = sh.copy(); sh2["r"] = sh2["r_short"] - extra_R
    m, p = block_boot(sh2)
    print(f"  median ATR~{atr:.0f}pts, extra cost ~{extra_R:.4f} R/trade -> short R={m:+.4f} p={p:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
