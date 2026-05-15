# ML snapshot walk-forward validation

_Generated `2026-05-15T02:08:49.970400+00:00`._

## Setup

- Matrix: `data\ml\anchors\smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- Schema: `data\ml\anchors\smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- Leaderboard source: `data\ml\anchors\smt_previous_day_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- Event type: `previous_day_smt`
- Candidates: `6`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\smt_previous_day_walk_forward_at_fire_thesis_context_layers_summary.csv | candidate summary CSV |
| data\ml\anchors\smt_previous_day_walk_forward_at_fire_thesis_context_layers_summary.parquet | candidate summary parquet |
| data\ml\anchors\smt_previous_day_walk_forward_at_fire_thesis_context_layers_folds.csv | per-fold CSV |
| data\ml\anchors\smt_previous_day_walk_forward_at_fire_thesis_context_layers_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 4676 |
| schema_feature_columns | 3150 |
| schema_label_columns | 18 |
| folds_attempted | 36 |
| folds_ok | 36 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | high | label.n1_thesis_confirmed_strict | 6 | 699 | 0.560 | 0.568 | 0.462 | 0.064 | 46.1% | 20.0% | 5.2% |
| at_fire | low | label.n1_close_moved_with_thesis | 6 | 650 | 0.551 | 0.556 | 0.482 | 0.048 | 57.5% | 42.9% | 7.0% |
| at_fire | high | label.n1_close_moved_with_thesis | 6 | 699 | 0.551 | 0.575 | 0.443 | 0.052 | 39.8% | 20.0% | -1.1% |
| at_fire | low | label.n1_thesis_confirmed_strict | 6 | 650 | 0.527 | 0.529 | 0.479 | 0.034 | 50.0% | 33.3% | 0.7% |
| at_fire | all | label.n1_close_moved_with_thesis | 6 | 1349 | 0.512 | 0.504 | 0.459 | 0.042 | 47.4% | 26.9% | 1.9% |
| at_fire | all | label.n1_thesis_confirmed_strict | 6 | 1349 | 0.512 | 0.507 | 0.489 | 0.020 | 47.7% | 38.9% | 2.8% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.n1_close_moved_with_thesis | 2020 | 179 | 44.7% | 0.594 | 0.592 | 0.553 | 18 | 77.8% |
| at_fire | all | label.n1_close_moved_with_thesis | 2021 | 227 | 42.7% | 0.487 | 0.542 | 0.573 | 23 | 39.1% |
| at_fire | all | label.n1_close_moved_with_thesis | 2022 | 185 | 46.5% | 0.506 | 0.535 | 0.535 | 19 | 47.4% |
| at_fire | all | label.n1_close_moved_with_thesis | 2023 | 255 | 46.7% | 0.459 | 0.533 | 0.533 | 26 | 26.9% |
| at_fire | all | label.n1_close_moved_with_thesis | 2024 | 279 | 47.3% | 0.523 | 0.527 | 0.527 | 28 | 50.0% |
| at_fire | all | label.n1_close_moved_with_thesis | 2025 | 224 | 45.5% | 0.501 | 0.545 | 0.545 | 23 | 43.5% |
| at_fire | all | label.n1_thesis_confirmed_strict | 2020 | 179 | 42.5% | 0.501 | 0.575 | 0.575 | 18 | 38.9% |
| at_fire | all | label.n1_thesis_confirmed_strict | 2021 | 227 | 44.1% | 0.537 | 0.542 | 0.559 | 23 | 52.2% |
| at_fire | all | label.n1_thesis_confirmed_strict | 2022 | 185 | 44.9% | 0.538 | 0.551 | 0.551 | 19 | 52.6% |
| at_fire | all | label.n1_thesis_confirmed_strict | 2023 | 255 | 47.1% | 0.492 | 0.529 | 0.529 | 26 | 50.0% |
| at_fire | all | label.n1_thesis_confirmed_strict | 2024 | 279 | 47.7% | 0.514 | 0.523 | 0.523 | 28 | 53.6% |
| at_fire | all | label.n1_thesis_confirmed_strict | 2025 | 224 | 43.8% | 0.489 | 0.562 | 0.562 | 23 | 39.1% |
| at_fire | high | label.n1_close_moved_with_thesis | 2020 | 93 | 37.6% | 0.443 | 0.624 | 0.624 | 10 | 20.0% |
| at_fire | high | label.n1_close_moved_with_thesis | 2021 | 114 | 34.2% | 0.585 | 0.623 | 0.658 | 12 | 41.7% |
| at_fire | high | label.n1_close_moved_with_thesis | 2022 | 95 | 45.3% | 0.567 | 0.547 | 0.547 | 10 | 40.0% |
| at_fire | high | label.n1_close_moved_with_thesis | 2023 | 130 | 40.0% | 0.584 | 0.600 | 0.600 | 13 | 38.5% |
| at_fire | high | label.n1_close_moved_with_thesis | 2024 | 142 | 45.1% | 0.539 | 0.549 | 0.549 | 15 | 60.0% |
| at_fire | high | label.n1_close_moved_with_thesis | 2025 | 125 | 43.2% | 0.591 | 0.568 | 0.568 | 13 | 38.5% |
| at_fire | high | label.n1_thesis_confirmed_strict | 2020 | 93 | 36.6% | 0.462 | 0.634 | 0.634 | 10 | 20.0% |
| at_fire | high | label.n1_thesis_confirmed_strict | 2021 | 114 | 35.1% | 0.502 | 0.658 | 0.649 | 12 | 33.3% |
| at_fire | high | label.n1_thesis_confirmed_strict | 2022 | 95 | 45.3% | 0.584 | 0.558 | 0.547 | 10 | 60.0% |
| at_fire | high | label.n1_thesis_confirmed_strict | 2023 | 130 | 40.8% | 0.602 | 0.592 | 0.592 | 13 | 69.2% |
| at_fire | high | label.n1_thesis_confirmed_strict | 2024 | 142 | 44.4% | 0.551 | 0.556 | 0.556 | 15 | 40.0% |
| at_fire | high | label.n1_thesis_confirmed_strict | 2025 | 125 | 43.2% | 0.658 | 0.576 | 0.568 | 13 | 53.8% |
| at_fire | low | label.n1_close_moved_with_thesis | 2020 | 86 | 52.3% | 0.509 | 0.465 | 0.477 | 9 | 44.4% |
| at_fire | low | label.n1_close_moved_with_thesis | 2021 | 113 | 51.3% | 0.568 | 0.549 | 0.487 | 12 | 58.3% |
| at_fire | low | label.n1_close_moved_with_thesis | 2022 | 90 | 47.8% | 0.630 | 0.622 | 0.522 | 9 | 77.8% |
| at_fire | low | label.n1_close_moved_with_thesis | 2023 | 125 | 53.6% | 0.482 | 0.464 | 0.464 | 13 | 61.5% |
| at_fire | low | label.n1_close_moved_with_thesis | 2024 | 137 | 49.6% | 0.575 | 0.555 | 0.504 | 14 | 42.9% |
| at_fire | low | label.n1_close_moved_with_thesis | 2025 | 99 | 48.5% | 0.543 | 0.535 | 0.515 | 10 | 60.0% |
| at_fire | low | label.n1_thesis_confirmed_strict | 2020 | 86 | 48.8% | 0.543 | 0.523 | 0.512 | 9 | 33.3% |
| at_fire | low | label.n1_thesis_confirmed_strict | 2021 | 113 | 53.1% | 0.561 | 0.522 | 0.469 | 12 | 66.7% |
| at_fire | low | label.n1_thesis_confirmed_strict | 2022 | 90 | 44.4% | 0.493 | 0.511 | 0.556 | 9 | 55.6% |
| at_fire | low | label.n1_thesis_confirmed_strict | 2023 | 125 | 53.6% | 0.515 | 0.480 | 0.464 | 13 | 61.5% |
| at_fire | low | label.n1_thesis_confirmed_strict | 2024 | 137 | 51.1% | 0.570 | 0.569 | 0.489 | 14 | 42.9% |
| at_fire | low | label.n1_thesis_confirmed_strict | 2025 | 99 | 44.4% | 0.479 | 0.535 | 0.556 | 10 | 40.0% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
