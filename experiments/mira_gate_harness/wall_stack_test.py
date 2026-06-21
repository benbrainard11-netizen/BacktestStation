"""Does the VALIDATED selection model (drift x zone) rescue the gamma walls, like it does the working
levels? Applies the SAME frozen rule (per-symbol drift threshold = 70th pct of 2026 zone-formed drift,
zone_5m_has==1 AND drift>=thr) to the wall reclaims over the 13-month MBP-1 window. Compares to the
working-levels stack (pooled +0.244, 2025-OOS +0.155) + the falsifiable control (drift WITHOUT a zone
must be <=0 if the mechanism is real, as it was for the working levels)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
POL = "trail_2R"

fc = pd.read_parquet(RUNS / "mbp1_stack_legal_bars_wall_mbp1.parquet")
key = ["symbol", "session_date", "level_price", "side"]
if POL not in fc.columns or "level_type" not in fc.columns:
    u = pd.read_parquet(RUNS / "legal_bars_wall_mbp1.parquet")
    cols = key + [c for c in ["trail_2R", "fixed_3R", "level_type"] if c not in fc.columns]
    fc = fc.merge(u[cols].drop_duplicates(key), on=key, how="left")
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
print(f"wall reclaims (MBP-1 13mo): {len(fc)}; zone-formed rate {100*fc['zf'].mean():.0f}%")
print(f"per-symbol drift thr (2026 zone-formed 70pct): {dict((k, round(v,1)) for k,v in thr.items())}")

stack = fc[fc.zf & (fc.drift >= fc.symbol.map(thr))]
ctrl = fc[(~fc.zf) & (fc.drift >= fc.symbol.map(thr))]
print(f"\n=== WALL drift x zone STACK (same frozen rule as working levels) ===")
print(f"  wall baseline (all)         {st(fc['R'])}")
print(f"  zone-formed only            {st(fc[fc.zf]['R'])}")
print(f"  STACK (zone & drift>=thr)   {st(stack['R'])}")
print(f"  CONTROL drift WITHOUT zone  {st(ctrl['R'])}   <- must be <=0 if mechanism real")
print(f"\n  REF working-levels stack: pooled +0.244, 2025-OOS +0.155, YM-led")

print(f"\n=== STACK by year (2026=design-threshold-fit, 2025=fresh OOS) ===")
print(f"  2026: {st(stack[stack.yr == 2026]['R'])}")
print(f"  2025: {st(stack[stack.yr == 2025]['R'])}  (FRESH OOS)")
print(f"\n=== STACK by symbol + call/put ===")
for s, g in stack.groupby("symbol"):
    print(f"  {s:8s} {st(g['R'])}")
for lt, g in stack.groupby("level_type"):
    print(f"  {('call/short' if lt=='gwc' else 'put/long')}: {st(g['R'])}")

print(f"\n=== SHUFFLE NULL on the stack lift (zone&drift vs rest), N=300 ===")
rng = np.random.default_rng(9)
sel = (fc.zf & (fc.drift >= fc.symbol.map(thr))).to_numpy()
real = fc[sel]["R"].mean() - fc[~sel]["R"].mean()
null = []
for _ in range(300):
    p = rng.permutation(sel)
    null.append(fc[p]["R"].mean() - fc[~p]["R"].mean())
null = np.array(null)
zsc = (real - null.mean()) / null.std() if null.std() > 0 else np.nan
print(f"  stack lift {real:+.4f} | null {null.mean():+.4f} +/- {null.std():.4f} | "
      f"z={zsc:+.2f} p={float((null>=real).mean()):.3f}")
