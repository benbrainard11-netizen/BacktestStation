"""CONFOUND CHECK for the feasibility read. Is d_call (proximity to the GAMMA call wall) actually
gamma-specific, or just "distance below a sticky overhead level"? Two falsifications:

  1. Tougher baseline: residualize next-day/3d realized vol on {rv10, rv20, VIX, mom5, mom20,
     dist-below-20d-high}. Does d_call's incremental IC survive controlling for price structure?
  2. Non-gamma control level: d_hi20 = (20d-high - close)/close (a NON-gamma overhead). If the gamma
     call wall has content beyond price structure, d_call should beat d_hi20 on the SAME residual.

Run: backend\\.venv\\Scripts\\python.exe -u experiments/stock_options_flow_v0/feasibility_confound.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "stock_options_flow_v0"))
from feasibility_megacap import NAMES, load_vix, panel_for, ic, resid_on_baseline  # noqa: E402


def main() -> int:
    vix = load_vix()
    rows = []
    for n in NAMES:
        df = panel_for(n, vix)
        if df.empty:
            continue
        r = pd.Series(np.log(df["close"]).diff().to_numpy(), index=df.index)
        df["rv20"] = r.rolling(20, min_periods=10).std()
        df["mom20"] = r.rolling(20, min_periods=10).sum()
        hi20 = df["close"].rolling(20, min_periods=10).max()
        df["dist20high"] = (hi20 - df["close"]) / df["close"]   # >=0, non-gamma overhead distance
        df["d_hi20"] = df["dist20high"]                          # control level (same construction as d_call)
        rows.append(df)
    big = pd.concat(rows, ignore_index=True)

    B = big[["rv10", "rv20", "vix", "mom5", "mom20", "dist20high"]].to_numpy(float)
    big["absret1_resid2"] = resid_on_baseline(big["absret1"], B)
    big["rvol3_resid2"] = resid_on_baseline(big["rvol3"], B)
    print(f"pooled name-days: {len(big)}  (tougher baseline: rv10,rv20,VIX,mom5,mom20,dist20high)\n")

    print("=== does the gamma call-wall feature survive the TOUGHER baseline? ===")
    print(f"{'feature':10} {'INCRIC absret1':>16} {'INCRIC rvol3':>14}")
    for f in ("d_call", "flip_side", "gex_z", "pin_dist"):
        r1, p1, _ = ic(big[f].to_numpy(float), big["absret1_resid2"].to_numpy(float))
        r2, p2, _ = ic(big[f].to_numpy(float), big["rvol3_resid2"].to_numpy(float))
        print(f"{f:10} {r1:>9.3f}(p{p1:.0e}) {r2:>7.3f}(p{p2:.0e})")

    print("\n=== gamma wall (d_call) vs NON-gamma overhead (d_hi20), SAME residual target ===")
    print("    if d_call ~ d_hi20, the gamma wall adds nothing beyond price structure.")
    for f in ("d_call", "d_hi20"):
        r2, p2, n2 = ic(big[f].to_numpy(float), big["rvol3_resid2"].to_numpy(float))
        print(f"  {f:8} INCRIC vs rvol3resid2 = {r2:>7.3f} (p={p2:.1e}, n={n2})")

    # also: residualize the target on d_hi20 too, then see if d_call STILL adds (gamma beyond the 20d-high)
    Bx = big[["rv10", "rv20", "vix", "mom5", "mom20", "dist20high", "d_hi20"]].to_numpy(float)
    big["rvol3_resid3"] = resid_on_baseline(big["rvol3"], Bx)
    r3, p3, n3 = ic(big["d_call"].to_numpy(float), big["rvol3_resid3"].to_numpy(float))
    print(f"\n=== d_call incremental AFTER also controlling for the 20d-high distance ===")
    print(f"  d_call INCRIC vs rvol3 resid(+d_hi20) = {r3:>7.3f} (p={p3:.1e}, n={n3})")
    print("  ^ this is the cleanest 'is the GAMMA wall real beyond price structure' number.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
