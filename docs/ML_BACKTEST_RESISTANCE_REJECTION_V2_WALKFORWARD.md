# Multi-year walk-forward — `next_60m.resistance_rejection_3bar`

_Generated 2026-05-15. Six independent test years (2020–2025), one model trained per year on prior years. The honest stress test for v1's single-year result._

## TL;DR — verdict: **ROBUST**

The model's top-10% high-confidence picks averaged **95% precision** across six test years (2020-2025), against a base rate that varied between 55% and 77%. Top 1% picks were **100% accurate in every single year** (24/24 trades total). Average edge over base rate at top-10% was **+30 percentage points**, with the worst year (2024) still at **+22 pp**.

This is the first signal in the lab that survives a six-year walk-forward. The 2025 100% result from [v1](ML_BACKTEST_RESISTANCE_REJECTION_V1.md) is not a fluke — it's consistent with the broader pattern.

## Setup

| Item | Value |
|---|---|
| Label | `label.next_60m.resistance_rejection_3bar` |
| Side | `gap_down` |
| Matrix | `opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.parquet` |
| Test years | 2020, 2021, 2022, 2023, 2024, 2025 (each trained fresh on prior years; val = year−1) |
| Threshold suite | 0.5, 0.6, 0.7, 0.8, 0.9 |
| Top-N% bands | 1%, 5%, 10%, 20%, 50% |
| Trade rule | Synthetic: +1R per hit, −1R per miss |

## Year-by-year

### Top-N model-score precision pivot (the meaningful "edge" view)

| Top-N | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Mean | Min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Top 1% | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | **1.00** | 1.00 |
| Top 5% | 0.90 | 1.00 | 1.00 | 1.00 | 0.77 | 1.00 | **0.94** | 0.77 |
| Top 10% | 0.93 | 1.00 | 1.00 | 0.98 | 0.79 | 1.00 | **0.95** | 0.79 |
| Top 20% | 0.91 | 0.92 | 1.00 | 0.95 | 0.73 | 0.98 | **0.91** | 0.73 |
| Top 50% | 0.82 | 0.74 | 0.89 | 0.90 | 0.68 | 0.82 | **0.81** | 0.68 |
| **Base rate** | 0.67 | 0.55 | 0.70 | 0.77 | 0.57 | 0.61 | 0.65 | — |

**Edge over base rate at top-10%:**

| Year | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|
| Edge | +0.26 | +0.45 | +0.30 | +0.21 | +0.22 | +0.39 |

Average +0.30 pp, minimum +0.21 pp.

### Year-level model quality

| Year | n_train | n_test | test AUC | base rate |
|---|---:|---:|---:|---:|
| 2020 | 2,022 | 407 | 0.741 | 0.666 |
| 2021 | 2,512 | 294 | 0.766 | 0.548 |
| 2022 | 2,919 | 411 | 0.807 | 0.701 |
| 2023 | 3,213 | 427 | 0.757 | 0.768 |
| 2024 | 3,624 | 337 | **0.647** | 0.570 |
| 2025 | 4,051 | 427 | 0.776 | 0.614 |

**Mean AUC: 0.749.** AUC is consistent in the 0.74-0.81 range across 5 of 6 years; **2024 is the outlier at 0.647**. That single year accounts for nearly all of the variance in top-10% precision (0.79 vs the ~1.00 typical).

## What 2024 tells us

The 2024 dip is worth understanding. The model's overall AUC dropped from 0.75-0.81 in surrounding years to 0.647 — that's a meaningful regime miss. Even so, the model still found edge: top-10% precision 0.79 vs base rate 0.57 = +22 pp edge. **Even the worst year was still profitable in expectation.**

Possible causes (not investigated here, but flag for follow-up):
- 2024 may have had unusually trendy / non-reversion price action that the model wasn't trained on (training stopped at end of 2022 + val 2023).
- Macro regime (Fed cycle, election year, US economic shifts) may have changed gap-day reactions.
- A specific subset of features (e.g., regime-context features) may have been less predictive that year.

Worth a focused diagnostic later: which 2024 features had the most distribution shift vs 2023?

## What this changes

Before v2, the lab had one strong result on one year — interesting but unproven. After v2, we have **six years of consistent multi-percentage-point edge**, with the model's top-decile picks averaging 95% precision against a 65% base rate. That's the threshold for "worth real investment."

## What's still missing (the limits of a proxy backtest)

1. **No real P&L.** +1R / −1R assumes uniform trade outcomes. In reality some rejections are deep (5R+), some are shallow (0.5R), losses can be larger than wins if stops get tagged. Need OHLCV backtest.
2. **No transaction costs.** 6 years × ~40 top-10% trades/year × commission + slippage = real drag. Modeling needed.
3. **No live entry mechanic defined.** The "trade rule" is "predict label=1 → +1R." Real trade needs: when does the 3-bar rejection complete? Where do you actually short? Where's the stop? Where's the target?
4. **No per-symbol breakdown.** ES/NQ/YM all pooled. NQ might be the workhorse and YM might be hurting the average — worth splitting.
5. **24 top-1% trades over 6 years is still a small sample.** 100% precision on 24 events is striking but the binomial confidence interval at 95% sample size includes lower bounds like 86%.

These all become productive next questions to chase, not blocking concerns.

## Recommended next steps

1. **Per-symbol breakdown** — quick, ~30 min build. Add a `primary_symbol` group-by to the analysis. Tells us "is this NQ, ES, or YM-driven."
2. **OHLCV-driven rigorous backtest** — the 4-6 hour build. Look up actual NQ/ES/YM bars from `D:\data\processed\bars\` and simulate trades with real entry/stop/target rules. Convert R-curve to dollar P&L.
3. **Strategy v1 spec document** — write up "ML-gated gap_down rejection short" as an actual `Strategy` spec (entry conditions, stop/target rules, R-sizing). Doesn't need to ship to the engine yet, but documents what we're proposing.
4. **Diagnose 2024** — why was that year so much weaker? Feature distribution analysis. Might reveal a robustness gap we need to fix before live capital.

## Reproducing

```bash
python -m scripts.ml.backtest_resistance_rejection_v2_walkforward
```

Outputs land in `experiments/backtests/2026-05-15_resistance_rejection_v2_walkforward/`:

- `per_year_summary.csv` — one row per test year with AUC, base rate, blind-baseline R
- `per_year_by_threshold.csv` — 5 thresholds × 6 years
- `per_year_by_top_pct.csv` — 5 top-N bands × 6 years
- `top_pct_precision_pivot.csv` — the pivot table summarized above
- `equity_curves_by_year.png` — 6 R-curves overlaid (threshold 0.7)
- `top_pct_precision_by_year.png` — bar chart with per-year base-rate references
- `verdict.json` — programmatic summary + verdict string
