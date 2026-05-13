# ML snapshot walk-forward validation

_Generated `2026-05-12T19:40:06.439771+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots_xctx_fvggeom.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots_xctx_fvggeom.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshot_leaderboard_xctx_fvggeom.parquet`
- Event type: `all`
- Candidates: `18`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025, 2026`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_walk_forward_fvggeom_summary.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_walk_forward_fvggeom_summary.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_walk_forward_fvggeom_folds.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_walk_forward_fvggeom_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 4676 |
| schema_feature_columns | 1324 |
| schema_label_columns | 18 |
| folds_attempted | 126 |
| folds_ok | 108 |
| folds_skipped | 18 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_period_close | high | label.n1_thesis_confirmed_strict | 6 | 699 | 0.964 | 0.962 | 0.955 | 0.010 | 100.0% | 100.0% | 59.1% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 6 | 650 | 0.959 | 0.956 | 0.946 | 0.012 | 100.0% | 100.0% | 50.7% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 6 | 1349 | 0.955 | 0.957 | 0.944 | 0.008 | 99.1% | 94.4% | 54.1% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 6 | 699 | 0.887 | 0.905 | 0.813 | 0.034 | 100.0% | 100.0% | 46.4% |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | 6 | 1349 | 0.885 | 0.891 | 0.837 | 0.022 | 100.0% | 100.0% | 41.0% |
| at_period_close | low | label.n1_or_n2_thesis_confirmed_strict | 6 | 650 | 0.875 | 0.877 | 0.833 | 0.024 | 100.0% | 100.0% | 35.2% |
| at_period_close | high | label.n2_thesis_confirmed_strict | 6 | 691 | 0.770 | 0.771 | 0.744 | 0.018 | 82.8% | 69.2% | 41.3% |
| at_period_close | all | label.n2_thesis_confirmed_strict | 6 | 1331 | 0.753 | 0.759 | 0.715 | 0.020 | 85.5% | 82.1% | 38.5% |
| at_period_close | low | label.n2_thesis_confirmed_strict | 6 | 640 | 0.748 | 0.758 | 0.700 | 0.036 | 83.9% | 77.8% | 30.8% |
| at_fire | low | label.n2_thesis_confirmed_strict | 6 | 640 | 0.552 | 0.556 | 0.415 | 0.081 | 51.9% | 11.1% | -1.2% |
| at_fire | all | label.n1_or_n2_thesis_confirmed_strict | 6 | 1349 | 0.549 | 0.557 | 0.522 | 0.019 | 61.6% | 50.0% | 2.6% |
| at_fire | all | label.n2_thesis_confirmed_strict | 6 | 1331 | 0.528 | 0.528 | 0.434 | 0.049 | 54.6% | 36.8% | 7.5% |
| at_fire | high | label.n2_thesis_confirmed_strict | 6 | 691 | 0.525 | 0.521 | 0.417 | 0.078 | 43.4% | 25.0% | 2.0% |
| at_fire | high | label.n1_or_n2_thesis_confirmed_strict | 6 | 699 | 0.512 | 0.513 | 0.460 | 0.027 | 56.2% | 33.3% | 2.6% |
| at_fire | high | label.n1_thesis_confirmed_strict | 6 | 699 | 0.511 | 0.510 | 0.431 | 0.044 | 33.5% | 0.0% | -7.3% |
| at_fire | all | label.n1_thesis_confirmed_strict | 6 | 1349 | 0.507 | 0.516 | 0.457 | 0.032 | 41.2% | 26.1% | -3.8% |
| at_fire | low | label.n1_or_n2_thesis_confirmed_strict | 6 | 650 | 0.493 | 0.482 | 0.411 | 0.052 | 67.5% | 55.6% | 2.7% |
| at_fire | low | label.n1_thesis_confirmed_strict | 6 | 650 | 0.483 | 0.463 | 0.422 | 0.061 | 48.4% | 30.0% | -0.9% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.n1_or_n2_thesis_confirmed_strict | 2020 | 179 | 55.9% | 0.574 | 0.559 | 0.559 | 18 | 66.7% |
| at_fire | all | label.n1_or_n2_thesis_confirmed_strict | 2021 | 227 | 58.6% | 0.525 | 0.586 | 0.586 | 23 | 56.5% |
| at_fire | all | label.n1_or_n2_thesis_confirmed_strict | 2022 | 185 | 60.0% | 0.522 | 0.600 | 0.600 | 19 | 57.9% |
| at_fire | all | label.n1_or_n2_thesis_confirmed_strict | 2023 | 255 | 62.0% | 0.559 | 0.624 | 0.620 | 26 | 69.2% |
| at_fire | all | label.n1_or_n2_thesis_confirmed_strict | 2024 | 279 | 58.4% | 0.560 | 0.595 | 0.584 | 28 | 50.0% |
| at_fire | all | label.n1_or_n2_thesis_confirmed_strict | 2025 | 224 | 59.4% | 0.555 | 0.594 | 0.594 | 23 | 69.6% |
| at_fire | all | label.n1_thesis_confirmed_strict | 2020 | 179 | 42.5% | 0.528 | 0.575 | 0.575 | 18 | 50.0% |
| at_fire | all | label.n1_thesis_confirmed_strict | 2021 | 227 | 44.1% | 0.457 | 0.515 | 0.559 | 23 | 26.1% |
| at_fire | all | label.n1_thesis_confirmed_strict | 2022 | 185 | 44.9% | 0.475 | 0.551 | 0.551 | 19 | 36.8% |
| at_fire | all | label.n1_thesis_confirmed_strict | 2023 | 255 | 47.1% | 0.527 | 0.529 | 0.529 | 26 | 53.8% |
| at_fire | all | label.n1_thesis_confirmed_strict | 2024 | 279 | 47.7% | 0.551 | 0.541 | 0.523 | 28 | 50.0% |
| at_fire | all | label.n1_thesis_confirmed_strict | 2025 | 224 | 43.8% | 0.504 | 0.504 | 0.562 | 23 | 30.4% |
| at_fire | all | label.n2_thesis_confirmed_strict | 2020 | 177 | 44.6% | 0.519 | 0.486 | 0.554 | 18 | 61.1% |
| at_fire | all | label.n2_thesis_confirmed_strict | 2021 | 226 | 46.9% | 0.589 | 0.584 | 0.531 | 23 | 60.9% |
| at_fire | all | label.n2_thesis_confirmed_strict | 2022 | 183 | 49.2% | 0.434 | 0.448 | 0.508 | 19 | 36.8% |
| at_fire | all | label.n2_thesis_confirmed_strict | 2023 | 251 | 47.8% | 0.533 | 0.522 | 0.522 | 26 | 46.2% |
| at_fire | all | label.n2_thesis_confirmed_strict | 2024 | 275 | 44.7% | 0.573 | 0.585 | 0.553 | 28 | 67.9% |
| at_fire | all | label.n2_thesis_confirmed_strict | 2025 | 219 | 48.9% | 0.523 | 0.548 | 0.511 | 22 | 54.5% |
| at_fire | high | label.n1_or_n2_thesis_confirmed_strict | 2020 | 93 | 48.4% | 0.460 | 0.484 | 0.484 | 10 | 40.0% |
| at_fire | high | label.n1_or_n2_thesis_confirmed_strict | 2021 | 114 | 47.4% | 0.505 | 0.491 | 0.474 | 12 | 33.3% |
| at_fire | high | label.n1_or_n2_thesis_confirmed_strict | 2022 | 95 | 63.2% | 0.505 | 0.632 | 0.632 | 10 | 50.0% |
| at_fire | high | label.n1_or_n2_thesis_confirmed_strict | 2023 | 130 | 54.6% | 0.539 | 0.546 | 0.546 | 13 | 84.6% |
| at_fire | high | label.n1_or_n2_thesis_confirmed_strict | 2024 | 142 | 52.8% | 0.520 | 0.542 | 0.528 | 15 | 60.0% |
| at_fire | high | label.n1_or_n2_thesis_confirmed_strict | 2025 | 125 | 55.2% | 0.543 | 0.552 | 0.552 | 13 | 69.2% |
| at_fire | high | label.n1_thesis_confirmed_strict | 2020 | 93 | 36.6% | 0.507 | 0.634 | 0.634 | 10 | 30.0% |
| at_fire | high | label.n1_thesis_confirmed_strict | 2021 | 114 | 35.1% | 0.431 | 0.649 | 0.649 | 12 | 0.0% |
| at_fire | high | label.n1_thesis_confirmed_strict | 2022 | 95 | 45.3% | 0.514 | 0.537 | 0.547 | 10 | 40.0% |
| at_fire | high | label.n1_thesis_confirmed_strict | 2023 | 130 | 40.8% | 0.495 | 0.592 | 0.592 | 13 | 30.8% |
| at_fire | high | label.n1_thesis_confirmed_strict | 2024 | 142 | 44.4% | 0.545 | 0.556 | 0.556 | 15 | 46.7% |
| at_fire | high | label.n1_thesis_confirmed_strict | 2025 | 125 | 43.2% | 0.573 | 0.584 | 0.568 | 13 | 53.8% |
| at_fire | high | label.n2_thesis_confirmed_strict | 2020 | 92 | 34.8% | 0.633 | 0.587 | 0.652 | 10 | 40.0% |
| at_fire | high | label.n2_thesis_confirmed_strict | 2021 | 113 | 36.3% | 0.449 | 0.540 | 0.637 | 12 | 25.0% |
| at_fire | high | label.n2_thesis_confirmed_strict | 2022 | 94 | 53.2% | 0.417 | 0.468 | 0.468 | 10 | 30.0% |
| at_fire | high | label.n2_thesis_confirmed_strict | 2023 | 128 | 42.2% | 0.525 | 0.578 | 0.578 | 13 | 38.5% |
| at_fire | high | label.n2_thesis_confirmed_strict | 2024 | 141 | 39.0% | 0.609 | 0.603 | 0.610 | 15 | 73.3% |
| at_fire | high | label.n2_thesis_confirmed_strict | 2025 | 123 | 43.1% | 0.517 | 0.577 | 0.569 | 13 | 53.8% |
| at_fire | low | label.n1_or_n2_thesis_confirmed_strict | 2020 | 86 | 64.0% | 0.411 | 0.593 | 0.640 | 9 | 55.6% |
| at_fire | low | label.n1_or_n2_thesis_confirmed_strict | 2021 | 113 | 69.9% | 0.488 | 0.681 | 0.699 | 12 | 58.3% |
| at_fire | low | label.n1_or_n2_thesis_confirmed_strict | 2022 | 90 | 56.7% | 0.475 | 0.567 | 0.567 | 9 | 55.6% |
| at_fire | low | label.n1_or_n2_thesis_confirmed_strict | 2023 | 125 | 69.6% | 0.471 | 0.696 | 0.696 | 13 | 76.9% |
| at_fire | low | label.n1_or_n2_thesis_confirmed_strict | 2024 | 137 | 64.2% | 0.548 | 0.628 | 0.642 | 14 | 78.6% |
| at_fire | low | label.n1_or_n2_thesis_confirmed_strict | 2025 | 99 | 64.6% | 0.568 | 0.636 | 0.646 | 10 | 80.0% |
| at_fire | low | label.n1_thesis_confirmed_strict | 2020 | 86 | 48.8% | 0.490 | 0.547 | 0.512 | 9 | 55.6% |
| at_fire | low | label.n1_thesis_confirmed_strict | 2021 | 113 | 53.1% | 0.435 | 0.469 | 0.469 | 12 | 41.7% |
| at_fire | low | label.n1_thesis_confirmed_strict | 2022 | 90 | 44.4% | 0.422 | 0.556 | 0.556 | 9 | 44.4% |
| at_fire | low | label.n1_thesis_confirmed_strict | 2023 | 125 | 53.6% | 0.538 | 0.504 | 0.464 | 13 | 61.5% |
| at_fire | low | label.n1_thesis_confirmed_strict | 2024 | 137 | 51.1% | 0.585 | 0.555 | 0.489 | 14 | 57.1% |
| at_fire | low | label.n1_thesis_confirmed_strict | 2025 | 99 | 44.4% | 0.427 | 0.475 | 0.556 | 10 | 30.0% |
| at_fire | low | label.n2_thesis_confirmed_strict | 2020 | 85 | 55.3% | 0.415 | 0.471 | 0.553 | 9 | 55.6% |
| at_fire | low | label.n2_thesis_confirmed_strict | 2021 | 113 | 57.5% | 0.687 | 0.575 | 0.575 | 12 | 66.7% |
| at_fire | low | label.n2_thesis_confirmed_strict | 2022 | 89 | 44.9% | 0.515 | 0.438 | 0.449 | 9 | 11.1% |
| at_fire | low | label.n2_thesis_confirmed_strict | 2023 | 123 | 53.7% | 0.554 | 0.537 | 0.537 | 13 | 53.8% |
| at_fire | low | label.n2_thesis_confirmed_strict | 2024 | 134 | 50.7% | 0.559 | 0.507 | 0.507 | 14 | 64.3% |
| at_fire | low | label.n2_thesis_confirmed_strict | 2025 | 96 | 56.2% | 0.578 | 0.552 | 0.562 | 10 | 60.0% |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | 2020 | 179 | 55.9% | 0.903 | 0.816 | 0.559 | 18 | 100.0% |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | 2021 | 227 | 58.6% | 0.884 | 0.815 | 0.586 | 23 | 100.0% |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | 2022 | 185 | 60.0% | 0.837 | 0.773 | 0.600 | 19 | 100.0% |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | 2023 | 255 | 62.0% | 0.890 | 0.816 | 0.620 | 26 | 100.0% |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | 2024 | 279 | 58.4% | 0.903 | 0.842 | 0.584 | 28 | 100.0% |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | 2025 | 224 | 59.4% | 0.892 | 0.812 | 0.594 | 23 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2020 | 179 | 42.5% | 0.944 | 0.888 | 0.575 | 18 | 94.4% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2021 | 227 | 44.1% | 0.961 | 0.877 | 0.559 | 23 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2022 | 185 | 44.9% | 0.967 | 0.886 | 0.551 | 19 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2023 | 255 | 47.1% | 0.958 | 0.890 | 0.529 | 26 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2024 | 279 | 47.7% | 0.955 | 0.857 | 0.523 | 28 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2025 | 224 | 43.8% | 0.944 | 0.866 | 0.562 | 23 | 100.0% |
| at_period_close | all | label.n2_thesis_confirmed_strict | 2020 | 177 | 44.6% | 0.760 | 0.695 | 0.554 | 18 | 83.3% |
| at_period_close | all | label.n2_thesis_confirmed_strict | 2021 | 226 | 46.9% | 0.775 | 0.717 | 0.531 | 23 | 82.6% |
| at_period_close | all | label.n2_thesis_confirmed_strict | 2022 | 183 | 49.2% | 0.715 | 0.689 | 0.508 | 19 | 89.5% |
| at_period_close | all | label.n2_thesis_confirmed_strict | 2023 | 251 | 47.8% | 0.741 | 0.677 | 0.522 | 26 | 84.6% |
| at_period_close | all | label.n2_thesis_confirmed_strict | 2024 | 275 | 44.7% | 0.759 | 0.713 | 0.553 | 28 | 82.1% |
| at_period_close | all | label.n2_thesis_confirmed_strict | 2025 | 219 | 48.9% | 0.766 | 0.694 | 0.511 | 22 | 90.9% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 2020 | 93 | 48.4% | 0.906 | 0.839 | 0.484 | 10 | 100.0% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 2021 | 114 | 47.4% | 0.886 | 0.816 | 0.474 | 12 | 100.0% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 2022 | 95 | 63.2% | 0.813 | 0.747 | 0.632 | 10 | 100.0% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 2023 | 130 | 54.6% | 0.906 | 0.792 | 0.546 | 13 | 100.0% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 2024 | 142 | 52.8% | 0.904 | 0.866 | 0.528 | 15 | 100.0% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 2025 | 125 | 55.2% | 0.908 | 0.800 | 0.552 | 13 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2020 | 93 | 36.6% | 0.963 | 0.892 | 0.634 | 10 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2021 | 114 | 35.1% | 0.985 | 0.930 | 0.649 | 12 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2022 | 95 | 45.3% | 0.961 | 0.874 | 0.547 | 10 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2023 | 130 | 40.8% | 0.955 | 0.892 | 0.592 | 13 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2024 | 142 | 44.4% | 0.966 | 0.866 | 0.556 | 15 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2025 | 125 | 43.2% | 0.956 | 0.848 | 0.568 | 13 | 100.0% |
| at_period_close | high | label.n2_thesis_confirmed_strict | 2020 | 92 | 34.8% | 0.798 | 0.728 | 0.652 | 10 | 90.0% |
| at_period_close | high | label.n2_thesis_confirmed_strict | 2021 | 113 | 36.3% | 0.753 | 0.690 | 0.637 | 12 | 75.0% |
| at_period_close | high | label.n2_thesis_confirmed_strict | 2022 | 94 | 53.2% | 0.744 | 0.713 | 0.468 | 10 | 90.0% |
| at_period_close | high | label.n2_thesis_confirmed_strict | 2023 | 128 | 42.2% | 0.771 | 0.656 | 0.578 | 13 | 69.2% |
| at_period_close | high | label.n2_thesis_confirmed_strict | 2024 | 141 | 39.0% | 0.779 | 0.723 | 0.610 | 15 | 80.0% |
| at_period_close | high | label.n2_thesis_confirmed_strict | 2025 | 123 | 43.1% | 0.772 | 0.691 | 0.569 | 13 | 92.3% |
| at_period_close | low | label.n1_or_n2_thesis_confirmed_strict | 2020 | 86 | 64.0% | 0.833 | 0.779 | 0.640 | 9 | 100.0% |
| at_period_close | low | label.n1_or_n2_thesis_confirmed_strict | 2021 | 113 | 69.9% | 0.888 | 0.805 | 0.699 | 12 | 100.0% |
| at_period_close | low | label.n1_or_n2_thesis_confirmed_strict | 2022 | 90 | 56.7% | 0.867 | 0.756 | 0.567 | 9 | 100.0% |
| at_period_close | low | label.n1_or_n2_thesis_confirmed_strict | 2023 | 125 | 69.6% | 0.864 | 0.768 | 0.696 | 13 | 100.0% |
| at_period_close | low | label.n1_or_n2_thesis_confirmed_strict | 2024 | 137 | 64.2% | 0.908 | 0.854 | 0.642 | 14 | 100.0% |
| at_period_close | low | label.n1_or_n2_thesis_confirmed_strict | 2025 | 99 | 64.6% | 0.890 | 0.818 | 0.646 | 10 | 100.0% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 2020 | 86 | 48.8% | 0.946 | 0.884 | 0.512 | 9 | 100.0% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 2021 | 113 | 53.1% | 0.963 | 0.876 | 0.469 | 12 | 100.0% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 2022 | 90 | 44.4% | 0.973 | 0.922 | 0.556 | 9 | 100.0% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 2023 | 125 | 53.6% | 0.975 | 0.912 | 0.464 | 13 | 100.0% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 2024 | 137 | 51.1% | 0.950 | 0.839 | 0.489 | 14 | 100.0% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 2025 | 99 | 44.4% | 0.949 | 0.879 | 0.556 | 10 | 100.0% |
| at_period_close | low | label.n2_thesis_confirmed_strict | 2020 | 85 | 55.3% | 0.700 | 0.647 | 0.553 | 9 | 88.9% |
| at_period_close | low | label.n2_thesis_confirmed_strict | 2021 | 113 | 57.5% | 0.762 | 0.708 | 0.575 | 12 | 83.3% |
| at_period_close | low | label.n2_thesis_confirmed_strict | 2022 | 89 | 44.9% | 0.756 | 0.719 | 0.449 | 9 | 77.8% |
| at_period_close | low | label.n2_thesis_confirmed_strict | 2023 | 123 | 53.7% | 0.705 | 0.650 | 0.537 | 13 | 84.6% |
| at_period_close | low | label.n2_thesis_confirmed_strict | 2024 | 134 | 50.7% | 0.760 | 0.701 | 0.507 | 14 | 78.6% |
| at_period_close | low | label.n2_thesis_confirmed_strict | 2025 | 96 | 56.2% | 0.803 | 0.688 | 0.562 | 10 | 90.0% |

## Skipped Folds

| status | count |
|---|---|
| skip_small_split | 18 |

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
