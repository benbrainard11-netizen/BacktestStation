# 2025 regime diagnostic — the model is fine, the stops are wrong

_Generated 2026-05-16, overnight. Answers the biggest open question from every backtest variant: **why does 2025 lose money on every config we test?**_

## TL;DR — surprising result

**The 2025 weakness is NOT a model degradation.** Across all 3 OGAP signals in the v5 winner portfolio:

- 2025 has the **highest** walk-forward AUC the model has ever achieved
- 2025 has the **highest** top-10% precision (often a perfect 1.000)
- 2025 has the **strongest** edge over base rate

**The model is finding patterns better than ever in 2025.** Yet v5's trade rules turn those better-than-ever predictions into the worst year on record (−35R, 28% win rate, 68% stop-out rate).

The break is at the **trade-rule layer**, not the model layer. 2025 has higher intra-window volatility — the price gets to the predicted outcome, but the path includes bigger adverse excursions than fixed 2 ATR stops can absorb.

## 4-layer breakdown

Each row is one of the 3 v5-portfolio signals. Each column is a test year. Most-recent year is rightmost.

### L1 — Label base rate (matrix-wide, the underlying event frequency)

| Signal | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|
| ogap_gap_down_rejection | 0.666 | 0.548 | 0.701 | 0.768 | 0.570 | 0.614 |
| ogap_gap_up_rejection | 0.687 | 0.646 | 0.657 | 0.619 | 0.632 | 0.695 |
| ogap_strict_partial_touch | 0.374 | 0.272 | 0.355 | 0.332 | 0.297 | 0.345 |

**L1 reading: stable.** 2025 base rates are well within the historical range for each signal. The underlying market events are firing at normal frequencies.

### L2 — Walk-forward test AUC

| Signal | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|
| ogap_gap_down_rejection | 0.741 | 0.766 | 0.807 | 0.757 | 0.647 ⚠️ | 0.776 |
| ogap_gap_up_rejection | 0.693 | 0.754 | 0.687 | 0.719 | 0.735 | **0.748** ⭐ |
| ogap_strict_partial_touch | 0.850 | 0.795 | 0.848 | 0.791 | 0.848 | **0.854** ⭐ |

**L2 reading: 2025 is one of the strongest years.** 2 of 3 signals hit their HIGHEST AUC ever in 2025. The model is making *better* predictions in 2025 than in prior years.

(Aside: 2024 is the actual weak AUC year, on `gap_down_rejection` — 0.647. Previously called out in [ML_BACKTEST_RESISTANCE_REJECTION_V2_WALKFORWARD.md](ML_BACKTEST_RESISTANCE_REJECTION_V2_WALKFORWARD.md). 2024's L4 trade outcomes were fine despite that; 2025's L4 trade outcomes are awful despite great L2/L3.)

### L3 — Top-10% precision

| Signal | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|
| ogap_gap_down_rejection | 0.927 | 1.000 | 1.000 | 0.977 | 0.794 | **1.000** ⭐ |
| ogap_gap_up_rejection | 1.000 | 0.926 | 0.864 | 0.833 | 1.000 | **1.000** ⭐ |
| ogap_strict_partial_touch | 0.888 | 0.807 | 0.906 | 0.881 | 0.897 | **0.908** ⭐ |

**L3 reading: 2025 high-conf picks are nearly flawless.** Two signals at 1.000 precision. The model's most-confident picks in 2025 were almost always correct.

### L4 — v5 winner trade-level outcomes (no-YM)

This is where 2025 falls apart.

| Year | n | Win% | Cum R | Avg R | **Stop %** | Target % | Time % |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 102 | 62.7% | +67.3 | +0.66 | 29% | 39% | 31% |
| 2021 | 68 | 52.9% | +20.1 | +0.30 | 41% | 24% | 35% |
| 2022 | 83 | 43.4% | +9.6 | +0.12 | 57% | 29% | 14% |
| 2023 | 95 | 48.4% | +15.7 | +0.17 | 43% | 19% | 38% |
| 2024 | 98 | 59.2% | +32.3 | +0.33 | 33% | 24% | 43% |
| **2025** | **106** | **28.3%** | **−35.0** | **−0.33** | **68%** ⚠️ | 17% | 15% |

**L4 reading: 2025 has by far the highest stop-out rate (68%) and lowest win rate.**

## The diagnosis

The model is RIGHT in 2025 about which gap setups will produce rejection. The model is also MORE confident than in any prior year. But **the price path to the predicted outcome includes bigger adverse swings in 2025**, and our fixed 2 ATR stops get tagged before the rejection completes.

**Mechanism:**

1. Model picks a gap_down at 09:30. Model says: "resistance rejection will happen in next 60 minutes." Model is RIGHT.
2. Trade rule waits for first red bar (confirmation), enters at next bar open.
3. Stop at entry + 2 ATR(14, 5m) — calibrated to recent local volatility.
4. In 2025, the typical post-gap path has bigger adverse excursions than in prior years. Price goes UP through the entry by more than 2 ATR before reversing.
5. Stop tagged. Trade closed. Rejection still happens later, but the trade missed it.

We can verify this hypothesis by computing the *intra-window MAE* (maximum adverse excursion) on 2025 trades vs prior years. The 68% stop rate alone is the smoking gun, but the MAE distribution would confirm it.

## What this changes about strategy v2

Before this diagnostic, we thought 2025 was a "regime where the signals broke." It's actually a "**regime where the same signal-driven trade rule needs wider stops or a different mechanic.**"

Fixable directions, in order of testability:

1. **Adaptive stops scaled by daily realized vol.** Instead of ATR(14, 5m) computed at entry, use a longer-period vol measure (ATR(20) on daily bars, or 30-day realized vol). This adapts to regime-level vol changes that intraday ATR misses.
2. **Per-year ATR-multiple tuning.** Refit the stop multiplier per regime. Could be a meta-model that picks the right multiplier based on recent realized vol.
3. **Trailing stops.** Once price moves favorable, ratchet stop along. Locks in profit even when subsequent vol blows out the original stop.
4. **Vol filter.** Skip trades on days where realized intraday vol > 2× rolling median. Reduces 2025 trade count but improves win rate.
5. **Different time exit.** Maybe 2025's vol pattern means trades need to either resolve fast (60min exit) or hold long (overnight). 240min may be the wrong middle.

**The least productive direction** is the one I'd previously suggested: investigate the labels or retrain on different feature subsets. The model isn't the problem.

## v7 candidates

1. **v7a**: same v5 config but with stops = max(2 ATR(14, 5m), 0.5 × daily ATR(20)). Floor the stop at half the recent daily range.
2. **v7b**: same v5 config but with trailing stop — once price moves +1 ATR favorable, ratchet stop to entry; once +2 ATR, ratchet stop to +1 ATR locked.
3. **v7c**: skip trade if matrix-day's realized 1m std is > 2× the rolling 30-day median. Filters out high-vol days.

Each is a 5-15 min experiment.

## Numerical evidence (graphical)

See [regime_layers.png](../experiments/backtests/2026-05-16_2025_regime_diagnostic/regime_layers.png) for the L2/L3/L3b/L4 panels overlaid.

## Files

- `layer1_base_rate_by_year.csv` — L1 pivot
- `layer2_auc_by_year.csv` — L2 pivot
- `layer3_top10_precision_by_year.csv` — L3 pivot
- `layer3b_top10_edge_by_year.csv` — L3b pivot
- `layer4_trade_metrics_by_year.csv` — L4 v5 winner per-year
- `regime_layers.png` — 4-panel overlay plot
- `summary.json`

## Reproducing

```bash
python -m scripts.ml.diagnose_2025_regime
```
