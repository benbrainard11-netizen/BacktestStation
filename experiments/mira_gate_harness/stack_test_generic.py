"""Generic drift x zone STACK test for ANY reclaim universe (walls, equal-levels, etc.). Applies the
SAME frozen rule the working levels were validated with (per-symbol drift thr = 70pct of 2026
zone-formed drift; zone_5m_has==1 AND drift>=thr), reports baseline/zone/stack + the falsifiable
control (drift WITHOUT zone must be <=0) + design(2026)/OOS(2025) + per-symbol + shuffle null.

Usage: stack_test_generic.py <mbp1_stack_features_parquet> <source_universe_parquet>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
POL = "trail_2R"


def main():
    panel, univ = sys.argv[1], sys.argv[2]
    fc = pd.read_parquet(RUNS / panel)
    key = ["symbol", "session_date", "level_price", "side"]
    need = [c for c in ["trail_2R", "fixed_3R", "level_type", "level_family"] if c not in fc.columns]
    if need:
        u = pd.read_parquet(RUNS / univ)
        fc = fc.merge(u[key + need].drop_duplicates(key), on=key, how="left")
    fc["drift"] = pd.to_numeric(fc["w90_drift_dir_ticks"], errors="coerce")
    fc["zf"] = fc["zone_5m_has"] == 1
    fc["R"] = pd.to_numeric(fc[POL], errors="coerce")
    fc = fc[fc["R"].abs() < 50].copy()
    fc["yr"] = pd.to_datetime(fc["session_date"]).dt.year
    SYMS = sorted(fc["symbol"].unique())

    def st(x):
        x = pd.to_numeric(x, errors="coerce").dropna()
        return f"n={len(x):4d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=   0"

    thr = {s: float(np.percentile(fc[(fc.symbol == s) & fc.zf & (fc.yr == 2026)]["drift"].dropna(), 70))
           for s in SYMS if ((fc.symbol == s) & fc.zf & (fc.yr == 2026)).sum() >= 5}
    print(f"universe {panel}: {len(fc)} reclaims, zone-formed {100*fc['zf'].mean():.0f}%, "
          f"freq ~{len(fc)/13:.0f}/mo")
    print(f"drift thr (2026 zone 70pct): {dict((k, round(v,1)) for k,v in thr.items())}")
    stack = fc[fc.zf & (fc.drift >= fc.symbol.map(thr))]
    ctrl = fc[(~fc.zf) & (fc.drift >= fc.symbol.map(thr))]
    print(f"\n  baseline (all)            {st(fc['R'])}")
    print(f"  zone-formed only          {st(fc[fc.zf]['R'])}")
    print(f"  STACK (zone & drift>=thr) {st(stack['R'])}   ~{len(stack)/13:.1f}/mo")
    print(f"  CONTROL drift w/o zone    {st(ctrl['R'])}   <- must be <=0")
    print(f"  REF working-levels stack: pooled +0.244, 2025-OOS +0.155")
    print(f"\n  2026(design-thr) {st(stack[stack.yr == 2026]['R'])} | 2025(OOS) {st(stack[stack.yr == 2025]['R'])}")
    for s, g in stack.groupby("symbol"):
        print(f"    {s:8s} {st(g['R'])}")
    if "level_type" in stack:
        for lt, g in stack.groupby("level_type"):
            print(f"    type {lt}: {st(g['R'])}")
    rng = np.random.default_rng(13)
    sel = (fc.zf & (fc.drift >= fc.symbol.map(thr))).to_numpy()
    real = fc[sel]["R"].mean() - fc[~sel]["R"].mean()
    null = np.array([(lambda p: fc[p]["R"].mean() - fc[~p]["R"].mean())(rng.permutation(sel)) for _ in range(300)])
    zsc = (real - null.mean()) / null.std() if null.std() > 0 else np.nan
    print(f"\n  SHUFFLE NULL: stack lift {real:+.4f} | null {null.mean():+.4f}+/-{null.std():.4f} | "
          f"z={zsc:+.2f} p={float((null>=real).mean()):.3f}")


if __name__ == "__main__":
    main()
