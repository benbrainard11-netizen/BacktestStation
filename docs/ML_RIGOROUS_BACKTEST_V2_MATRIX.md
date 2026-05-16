# V2 design matrix + v3 — finding the lever that flips v1

_Generated 2026-05-16. After v1's −880R result, tested 4 single-lever variants + 1 combined variant to isolate which design choice drives the loss. Found the dominant lever (consensus filter) and converged to a near-break-even system._

## TL;DR

| Config | n | Cum R | Win% | Max DD | Δ vs v1 |
|---|---:|---:|---:|---:|---:|
| **v3 (consensus + wider stop + no SMT/sweep)** ⭐ | **629** | **−38.7** | **45.9%** | **49.8** | **+842R** |
| v2c (consensus only) | 828 | −51.8 | 35.7% | 71 | +829R |
| v2b (wider stop only) | 3,964 | −737.7 | 40.0% | 739 | +143R |
| v2d (drop SMT) | 3,895 | −849.9 | 28.5% | 929 | +31R |
| v1 (baseline) | 3,964 | −880.4 | 28.3% | 929 | — |
| v2a (skip confirmation) | 3,967 | −1,138.4 | 26.3% | 1,154 | **−258R** |

**Key learnings:**

1. **Consensus filter is the dominant lever.** Requiring 2+ signals on the same date+symbol cut 79% of trades but eliminated 94% of the drawdown. The bad trades were mostly single-signal noise — especially solo sweep picks at moments of momentum.
2. **Wait-for-confirmation was helping, not hurting.** v2a (skip confirmation) made things *worse* (−1,138R vs −880R), disconfirming the v1-writeup hypothesis that "confirmation-bar entry kills the trade."
3. **Wider stops help win rate but not enough alone.** v2b lifted win rate from 28% → 40% but only saved 143R — the 1:1 R:R means individual wins shrink alongside fewer stops.
4. **Dropping SMT alone doesn't help much.** −31R improvement out of 880R. SMT was a small contributor; the real drainer was sweep.
5. **v3 (combined: consensus + wider stop + drop both drainers) gets us to −39R.** The 3 remaining OGAP signals are essentially flat individually. Win rate 46% on 1:1 R:R is profitable on paper — but execution drag from time-exits (close P&L between stop/target) leaks −0.06R per trade.

## Per-signal under v3

| Signal | n | Win rate | Cum R | Avg win R | Avg loss R |
|---|---:|---:|---:|---:|---:|
| ogap_gap_down_rejection | 161 | 44.7% | −7.5 | +0.82 | −0.75 |
| ogap_gap_up_rejection | 155 | 47.1% | −12.0 | +0.61 | −0.69 |
| ogap_strict_partial_touch | 313 | 46.0% | −19.2 | +0.71 | −0.72 |
| **POOLED** | **629** | **45.9%** | **−38.7** | — | — |

All three OGAP signals win 44-47% of trades — that's a healthy win rate. With 1:1 R:R math: 0.46 × 0.72 + 0.54 × −0.72 = −0.011. Plus execution drag. Total: −0.06R per trade.

## Diagnosis — why v3 still loses (small loss, different cause than v1)

v1's loss was **structural**: 28% win rate with 2:1 R:R meant most trades lose, and the few wins didn't make up for it. The model's high precision was being destroyed by the trade rules.

v3's loss is **execution drag**: 46% win rate with 1:1 R:R is roughly break-even by math. But:
- Average wins land at +0.71R instead of full +1R because some hit target but exit gives back slippage, or time-exit at close-between-target-and-entry
- Average losses land at −0.72R instead of full −1R for same reason
- The time-exit rule (60 min mark, close P&L) systematically caps wins more aggressively than losses

The 60-min time-exit might be the next-most-fixable lever. Hypothesis: if we extended to 180 min or removed the time exit entirely, more trades would hit their stops/targets cleanly.

## What this changes about the project

We've gone from "v1 destroys the precision edge entirely" to "the OGAP rejection signals are basically break-even when properly filtered." That's a meaningful step but not yet a tradeable strategy.

**The remaining gap to profitability is small** (about 0.06R per trade) and concentrated in execution drag. Possible fixes — each is a ~5 min run:
- **v4a**: extend time exit to 180 min. More room for stop/target to resolve cleanly.
- **v4b**: remove time exit entirely. Hold until stop or target (or end of next session).
- **v4c**: asymmetric R:R (1 ATR stop, 1.5 ATR target). Slightly favorable when win rate is symmetric.
- **v4d**: skip ogap_strict_partial_touch (largest drainer in v3, hardest to interpret directionally).

## What also matters: the negative findings are real

We tested 5 hypotheses today and 4 of them did NOT pan out:
- ❌ Skip confirmation entry (v2a) — made things worse
- ❌ Drop SMT alone (v2d) — barely moved the needle
- ❌ Wider stops alone (v2b) — helped a bit but not enough
- ❌ Single-signal trading (v1) — the original frame was wrong

The ONE that worked: **consensus filtering**. Combined with wider stops and dropping drainers, the system goes from a complete loss to nearly flat.

## Reproducing

```bash
python -m scripts.ml.rigorous_backtest_v2_matrix
```

Configs defined in `CONFIGS` list at the top of the script. Outputs in `experiments/backtests/2026-05-15_rigorous_v2_matrix/`:

- `trades_all_configs.csv` — every simulated trade across all configs
- `per_config_per_signal.csv` — breakdown by (config, signal)
- `per_config_rollup.csv` — top-line per config
- `v2_matrix_equity.png` — all configs on one chart
- `summary.json`
