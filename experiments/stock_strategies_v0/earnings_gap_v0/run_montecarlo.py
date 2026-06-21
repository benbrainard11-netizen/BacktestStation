"""Trade frequency + Monte Carlo for the earnings-gap strategy, on the HONEST per-trade R
distribution (fixed-% stop). Block-bootstrap (preserves loss clustering like 2025). 1% risk
per trade, sequential compounding (doc-style; concurrency ignored = a simplification).

PREVIEW: 132-name universe, daily fills, holdout unread. Refines with broad universe + model.
Writes out/montecarlo_bands.parquet for the equity-fan viz. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from shell import ShellConfig, Signal, run_signals  # noqa: E402

RISK = 0.01            # 1% of equity risked per trade
START = 10_000.0
HORIZON = 220          # trades per simulated path
SIMS = 5000
BLOCK = 15             # block-bootstrap block length (preserves clustering)
OUT = Path(__file__).resolve().parent / "out"

study = pd.read_parquet(OUT / "earnings_study.parquet")
setup = study[(study["gap"] >= 0.075) & (study["above_high"])].copy()
sigs = [Signal(r.ticker, r.dt, tag="earnings_gap") for r in setup.itertuples()]
tr = run_signals(sigs, ShellConfig(entry_mode="signal_open", stop_mode="pct", stop_pct=0.08,
                                   do_partial=False, move_to_be=False, trail_ma="ma20"))
tr["dt"] = pd.to_datetime(tr["entry_date"])
tr = tr.sort_values("dt").reset_index(drop=True)
R = tr["realized_r"].clip(-1.5, 15).to_numpy()   # honest, lightly winsorized

# --- frequency ---
yrs = (tr["dt"].max() - tr["dt"].min()).days / 365.25
per_yr = len(tr) / yrs
print(f"=== TRADE FREQUENCY (132-name universe) ===")
print(f"  {len(tr)} trades over {yrs:.1f}y = ~{per_yr:.0f}/yr (~{per_yr/12:.1f}/mo). "
      f"Broad ~1500-name universe ~ {per_yr*1500/132:.0f}/yr (>10x).")
print(f"  per-trade: win {(R>0).mean()*100:.0f}%  mean R {R.mean():+.2f}  median {np.median(R):+.2f}")

# --- block bootstrap MC ---
rng = np.random.default_rng(0)
n = len(R)
ends, maxdd, mcl = np.empty(SIMS), np.empty(SIMS), np.empty(SIMS, int)
paths = np.empty((SIMS, HORIZON + 1))
for s in range(SIMS):
    seq = []
    while len(seq) < HORIZON:
        i = rng.integers(0, n)
        seq.extend(R[i:i + BLOCK])
    seq = np.array(seq[:HORIZON])
    eq = START * np.cumprod(1 + RISK * seq)
    eq = np.concatenate([[START], eq])
    paths[s] = eq
    ends[s] = eq[-1]
    peak = np.maximum.accumulate(eq)
    maxdd[s] = ((peak - eq) / peak).max()
    loss = seq < 0
    run = mx = 0
    for L in loss:
        run = run + 1 if L else 0
        mx = max(mx, run)
    mcl[s] = mx

pct = [5, 25, 50, 75, 95]
bands = pd.DataFrame({f"p{p}": np.percentile(paths, p, axis=0) for p in pct})
bands.to_parquet(OUT / "montecarlo_bands.parquet")

print(f"\n=== MONTE CARLO ({SIMS} sims, {HORIZON} trades, 1% risk, block-bootstrap) ===")
print(f"  ending equity ($10k start): median ${np.median(ends):,.0f} | "
      f"5th ${np.percentile(ends,5):,.0f} | 95th ${np.percentile(ends,95):,.0f}")
print(f"  P(profit) {np.mean(ends>START)*100:.0f}% | P(>2x) {np.mean(ends>2*START)*100:.0f}% | "
      f"P(lose>20%) {np.mean(ends<0.8*START)*100:.0f}%")
print(f"  avg max drawdown {maxdd.mean()*100:.0f}% | worst (95th) {np.percentile(maxdd,95)*100:.0f}%")
print(f"  max consecutive losses: median {int(np.median(mcl))} | worst (95th) {int(np.percentile(mcl,95))}")
print(f"\n  (at ~{per_yr:.0f} trades/yr, {HORIZON} trades ~ {HORIZON/per_yr:.1f} years on the 132-name universe)")
print("  CAVEATS: preview — in-sample-ish (holdout unread), 132 names, daily fills, 1% sequential sizing.")
