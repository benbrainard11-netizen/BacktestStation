"""Fragility / robustness stress-test of the CONFIRMED Jan-2026 with-MBO edge.

The whole milk plan rests on ONE number: +0.44R trail_2R over 139 Jan with-MBO entries. Before
scaling to N prop accounts, stress it with what we have:
  1. bootstrap CI on the mean (is +0.44R robustly > 0, and > a milkable 0.2R?)
  2. per-symbol + per-direction breakdown (is it one symbol / one side carrying it?)
  3. trade concentration (does removing the few best trades flip it?)
  4. extra-cost sensitivity (worse slippage than the already-stressed $3.80 + 2-tick)
  5. intra-slice drawdown + worst losing streak (would it have blown a prop trailing-DD mid-month?)

HONEST LIMIT: this quantifies sampling robustness WITHIN January. It CANNOT tell us January
generalizes to other months -- that needs more OOS (the gated MBO pull). A tight bootstrap CI here
is necessary, not sufficient.

Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/mira_jan_fragility.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EX = HERE / "out" / "mira_oos_withmbo" / "jan2026_withmbo_exits.parquet"
V = "r_trail_2R"   # the deployed exit
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}


def main() -> int:
    d = pd.read_parquet(EX)
    r = d[V].to_numpy()
    n = len(r)
    print(f"Jan-2026 with-MBO  {V}:  n={n}  mean={r.mean():+.3f}R  win={(r > 0).mean():.1%}  "
          f"sum={r.sum():+.1f}R  median={np.median(r):+.3f}R\n")

    # 1) bootstrap CI on the mean
    rng = np.random.default_rng(42)
    boot = r[rng.integers(0, n, size=(50_000, n))].mean(axis=1)
    print("1) BOOTSTRAP mean R (50k resamples of the 139 trades):")
    print(f"     5th / 50th / 95th pct:  {np.percentile(boot, 5):+.3f} / "
          f"{np.percentile(boot, 50):+.3f} / {np.percentile(boot, 95):+.3f} R")
    print(f"     P(mean > 0) = {(boot > 0).mean():.1%}     "
          f"P(mean > +0.20R, milkable) = {(boot > 0.20).mean():.1%}\n")

    # 2) per symbol + direction
    print("2) PER SYMBOL:")
    for s, g in d.groupby("symbol"):
        rr = g[V]
        print(f"     {s:9} n={len(rr):3}  mean={rr.mean():+.3f}  win={(rr > 0).mean():.0%}  sum={rr.sum():+.1f}R")
    print("   PER DIRECTION:")
    for dv, g in d.groupby("direction"):
        rr = g[V]
        lbl = "long" if int(dv) == 1 else "short"
        print(f"     {lbl:9} n={len(rr):3}  mean={rr.mean():+.3f}  win={(rr > 0).mean():.0%}  sum={rr.sum():+.1f}R")
    print()

    # 3) concentration
    srt = np.sort(r)[::-1]
    tot = r.sum()
    print("3) CONCENTRATION (is it a few monster trades?):")
    for k in (3, 5, 10, 20):
        rest = (tot - srt[:k].sum()) / (n - k)
        print(f"     top {k:2} trades = {srt[:k].sum():+.1f}R ({srt[:k].sum() / tot:.0%} of total)   "
              f"->  mean without them = {rest:+.3f}R")
    print()

    # 4) extra-cost sensitivity (on top of the already-stressed $3.80 + 2-tick)
    print("4) EXTRA SLIPPAGE sensitivity (already includes $3.80 + 2 ticks):")
    for extra in (1, 2, 4):
        extra_R = d.apply(lambda x: extra * TICK[x["symbol"]] / x["risk_points"], axis=1)
        print(f"     +{extra} tick/trade more:  mean={(d[V] - extra_R).mean():+.3f}R  "
              f"win={((d[V] - extra_R) > 0).mean():.0%}")
    print()

    # 5) intra-slice drawdown + worst losing streak (chronological)
    dchron = d.sort_values("entry_ts")
    rc = dchron[V].to_numpy()
    eq = np.cumsum(rc)
    dd = (eq - np.maximum.accumulate(eq))
    streak = mx = 0
    for x in rc:
        streak = streak + 1 if x < 0 else 0
        mx = max(mx, streak)
    print("5) INTRA-SLICE PATH (chronological, ~1 month):")
    print(f"     max drawdown = {dd.min():+.1f}R   worst losing streak = {mx} trades   "
          f"final = {eq[-1]:+.1f}R")
    print(f"     -> at $75/R that DD = ${dd.min() * 75:,.0f}; at $150/R = ${dd.min() * 150:,.0f} "
          f"(vs a typical ~$2,000-2,500 trailing DD)")

    print("\nHONEST READ: bootstrap = within-January robustness only. The real question -- does Jan "
          "generalize -- still needs more OOS (the live eval is now answering it for free, trade by trade).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
