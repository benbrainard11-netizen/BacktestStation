"""Why are 38% of DJX wall-days' spot off vs YM? Two hypotheses:
  (a) real DJX, STALE/garbage underlying_price field  -> strikes are fine, just fix spot.
  (b) a DIFFERENT product (~250-520) misclassified as DJX -> strikes are garbage, drop it.
Inspect a known-bad day and a known-good day: underlying_price distribution + the strike
range of the gamma>0 contracts. If strikes track the real Dow/100 (~450), it's (a); if
strikes track the low spot (~330), the whole chain is another product = (b).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

GREEKS = Path(r"D:\data\raw\thetadata\bulk_hist_option_eod_greeks")
DJX_LO, DJX_HI = 250.0, 520.0

# scan DJX-classified greeks, keep two probe dates
PROBE = {20250904, 20260203, 20251201}   # bad, mild-bad, (likely good)
parts = []
for fp in sorted(GREEKS.glob("*.parquet")):
    try:
        d = pd.read_parquet(fp, columns=["date", "strike", "right", "expiration", "gamma", "underlying_price"])
    except Exception:
        continue
    if d.empty or not (DJX_LO <= d["underlying_price"].median() < DJX_HI):
        continue
    d = d[d["date"].astype(int).isin(PROBE)]
    if len(d):
        parts.append(d)
df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

for D in sorted(PROBE):
    g = df[df["date"].astype(int) == D]
    if g.empty:
        print(f"\n{D}: no DJX-classified rows"); continue
    up = g["underlying_price"].to_numpy(float)
    gpos = g[g["gamma"] > 0]
    ks = gpos["strike"].to_numpy(float)
    print(f"\n=== {D} ===  rows={len(g)} gamma>0={len(gpos)}")
    print(f"  underlying_price: median={np.median(up):.1f} min={up.min():.1f} max={up.max():.1f} "
          f"unique~{len(np.unique(np.round(up,1)))}")
    print(f"  underlying_price percentiles 5/50/95: {np.percentile(up,[5,50,95]).round(1)}")
    if len(ks):
        print(f"  gamma>0 STRIKE range: {ks.min():.0f}..{ks.max():.0f}  median={np.median(ks):.0f} "
              f"(p25/p75 {np.percentile(ks,[25,75]).round(0)})")
        # where is gamma concentrated? near-spot strikes carry it
        atm = gpos.assign(d=(gpos["strike"] - np.median(up)).abs()).nsmallest(5, "d")
        print(f"  5 highest-gamma-OI-region strikes nearest underlying: {sorted(atm['strike'].round(0).tolist())}")
