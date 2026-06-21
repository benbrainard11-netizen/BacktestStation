"""Monte Carlo of the VALIDATED strategy (model-selected, concurrency-aware portfolio).
Block-bootstraps the historical portfolio's MONTHLY returns (preserves loss clustering) into
many 5-year paths. This MC's the REAL equity stream (with concurrency + the selection model),
unlike the earlier sequential per-trade MC. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
cv = pd.read_parquet(OUT / "portfolio_curve_model.parquet")["equity"]
cv.index = pd.to_datetime(cv.index)
monthly = cv.resample("ME").last().pct_change().dropna().to_numpy()   # monthly portfolio returns
print(f"historical: {len(monthly)} monthly returns, mean {monthly.mean()*100:+.2f}%/mo, "
      f"std {monthly.std()*100:.2f}%")

START, MONTHS, SIMS, BLOCK = 10_000.0, 60, 5000, 3
rng = np.random.default_rng(0)
n = len(monthly)
ends, maxdd = np.empty(SIMS), np.empty(SIMS)
paths = np.empty((SIMS, MONTHS + 1))
for s in range(SIMS):
    seq = []
    while len(seq) < MONTHS:
        i = rng.integers(0, n)
        seq.extend(monthly[i:i + BLOCK])
    seq = np.array(seq[:MONTHS])
    eq = START * np.cumprod(1 + seq)
    eq = np.concatenate([[START], eq])
    paths[s], ends[s] = eq, eq[-1]
    peak = np.maximum.accumulate(eq)
    maxdd[s] = ((peak - eq) / peak).max()

pcts = [5, 25, 50, 75, 95]
bands = pd.DataFrame({f"p{p}": np.percentile(paths, p, axis=0) for p in pcts})
bands.to_parquet(OUT / "mc_final_bands.parquet")

cagr_med = (np.median(ends) / START) ** (1 / 5) - 1
print(f"\n=== MONTE CARLO of the validated strategy ({SIMS} sims, 5 years, block-bootstrap) ===")
print(f"  ending equity ($10k): median ${np.median(ends):,.0f} | 5th ${np.percentile(ends,5):,.0f} "
      f"| 95th ${np.percentile(ends,95):,.0f}")
print(f"  median CAGR {cagr_med*100:.1f}% | P(profit) {np.mean(ends>START)*100:.0f}% | "
      f"P(>2x) {np.mean(ends>2*START)*100:.0f}% | P(lose>20%) {np.mean(ends<0.8*START)*100:.0f}%")
print(f"  avg max drawdown {maxdd.mean()*100:.0f}% | worst (95th) {np.percentile(maxdd,95)*100:.0f}%")
print("  NOTE: MC of the model-selected concurrency-aware portfolio (8% proxy stop, 0.5%/30pos).")
