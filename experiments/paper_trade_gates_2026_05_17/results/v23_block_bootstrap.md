# v23 — Block Bootstrap (Paper-Trade Gate 2)

_Generated 2026-05-18T01:28:13.740821Z_

Tests whether the v20 OB strict + Sweep reversed cum_R is robust to resampling daily P&L blocks. 10,000 resamples per block size.

## Verdict: PASS

### OB strict

- Trade days: 548
- Observed cum_R: 1509.26
- Observed annual R (pro-rated to 252 trading days): 694.04

| Block | Mean | Median | 5th | 95th | P(neg) |
|---|---:|---:|---:|---:|---:|
| block_1d | 693.44 | 694.15 | 617.63 | 768.60 | 0.00% |
| block_5d | 694.72 | 694.32 | 620.74 | 771.65 | 0.00% |
| block_20d | 690.47 | 690.01 | 623.65 | 757.59 | 0.00% |

- P(annual_R ≤ 0) ≤ 5% on all blocks: **True**
- 5th percentile > 0 on at least one block: **True**
- Median within [0.5x, 2x] observed: **True**
- **PASS**

### Sweep reversed (filtered)

- Trade days: 526
- Observed cum_R: 1042.72
- Observed annual R (pro-rated to 252 trading days): 499.55

| Block | Mean | Median | 5th | 95th | P(neg) |
|---|---:|---:|---:|---:|---:|
| block_1d | 499.72 | 499.80 | 431.49 | 569.19 | 0.00% |
| block_5d | 496.21 | 496.25 | 433.09 | 560.19 | 0.00% |
| block_20d | 490.87 | 490.67 | 430.15 | 550.63 | 0.00% |

- P(annual_R ≤ 0) ≤ 5% on all blocks: **True**
- 5th percentile > 0 on at least one block: **True**
- Median within [0.5x, 2x] observed: **True**
- **PASS**

## Interpretation

- P(annual_R ≤ 0) is the bootstrap p-value of the null "no edge."
- Block sizes 1d / 5d / 20d test sensitivity to autocorrelation. If results hold under 20d blocks (which preserve month-scale regime), edge isn't just intra-day noise.
- The Sweep family had only ~95 day-2-holdout days plus ~500 holdout-1 days; small samples will have wider intervals.
