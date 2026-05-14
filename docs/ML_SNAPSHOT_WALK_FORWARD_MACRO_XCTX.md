# ML Snapshot Walk-Forward - Macro XCTX

_Generated from `data/ml/anchors/macro_snapshot_walk_forward_summary_xctx.csv` on 2026-05-14._

## Setup

- Matrix: `data/ml/anchors/macro_event_snapshots_xctx.parquet`
- Schema: `data/ml/anchors/macro_event_snapshots_xctx.schema.json`
- Leaderboard source: `data/ml/anchors/macro_snapshot_leaderboard_xctx.parquet`
- Candidates tested: `8`
- Test years: `2020`, `2021`, `2022`, `2023`, `2024`, `2025`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`
- Top bucket: highest-probability `10%` of each test year
- Model: LightGBM binary classifier

## Output Files

| file | purpose |
|---|---|
| `data/ml/anchors/macro_snapshot_walk_forward_summary_xctx.csv` | Candidate summary CSV |
| `data/ml/anchors/macro_snapshot_walk_forward_summary_xctx.parquet` | Candidate summary parquet |
| `data/ml/anchors/macro_snapshot_walk_forward_folds_xctx.csv` | Per-year fold CSV |
| `data/ml/anchors/macro_snapshot_walk_forward_folds_xctx.parquet` | Per-year fold parquet |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | mean_top_rate | mean_top_lift |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| at_fire | all | `label.next_5m.range_expanded_2x_pre_15m` | 6 | 8,511 | 0.858 | 0.865 | 0.809 | 36.5% | 30.2% |
| at_fire | all | `label.next_15m.range_expanded_2x_pre_60m` | 6 | 8,528 | 0.854 | 0.875 | 0.730 | 21.4% | 17.9% |
| at_fire | high | `label.next_5m.range_expanded_2x_pre_15m` | 6 | 4,460 | 0.846 | 0.883 | 0.754 | 45.9% | 36.0% |
| at_fire | medium | `label.next_15m.took_pre_60m_high` | 6 | 4,052 | 0.837 | 0.856 | 0.724 | 73.3% | 43.0% |
| at_fire | high | `label.next_15m.range_expanded_2x_pre_60m` | 6 | 4,476 | 0.831 | 0.834 | 0.716 | 33.5% | 27.3% |
| at_fire | medium | `label.next_15m.took_pre_60m_low` | 6 | 4,052 | 0.825 | 0.827 | 0.801 | 71.6% | 42.8% |
| at_fire | medium | `label.next_60m.range_expanded_1x_pre_60m` | 6 | 4,068 | 0.792 | 0.805 | 0.709 | 88.4% | 37.1% |
| at_fire | high | `label.next_15m.swept_both_pre_60m_sides` | 6 | 4,476 | 0.763 | 0.775 | 0.627 | 23.7% | 18.4% |

## Interpretation

- The strongest macro signals survive stricter year-by-year validation.
- The cleanest label so far is `next_5m.range_expanded_2x_pre_15m`: it held a mean AUC of `0.858` across six test years with no weak year below `0.809`.
- The `next_15m.range_expanded_2x_pre_60m` label is strong on average, but its weakest year is lower, so it needs event-type breakdown before being trusted.
- The 15-minute high/low take labels work especially well for medium-impact releases, which suggests pre-release position inside the 60-minute range matters.
- This is still feature-database research, not entry logic. These labels tell the future trainer what kind of news reaction happened after the scheduled event.
