# ML snapshot walk-forward validation

_Generated `2026-05-11T15:54:14.639903+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_snapshot_leaderboard.parquet`
- Event type: `previous_day_smt`
- Candidates: `12`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_snapshot_walk_forward_summary.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_snapshot_walk_forward_summary.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_snapshot_walk_forward_folds.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_snapshot_walk_forward_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 4676 |
| schema_feature_columns | 281 |
| schema_label_columns | 18 |
| folds_attempted | 72 |
| folds_ok | 72 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_period_close | high | label.n1_thesis_confirmed_strict | 6 | 699 | 0.929 | 0.926 | 0.899 | 0.020 | 98.7% | 92.3% | 57.8% |
| at_period_close | high | label.n1_primary_took_period_n_low | 6 | 699 | 0.929 | 0.926 | 0.899 | 0.020 | 98.7% | 92.3% | 57.8% |
| at_period_close | high | label.n1_close_moved_with_thesis | 6 | 699 | 0.928 | 0.927 | 0.891 | 0.025 | 98.7% | 92.3% | 57.8% |
| at_period_close | high | label.n1_primary_took_period_n_high | 6 | 699 | 0.924 | 0.930 | 0.875 | 0.024 | 100.0% | 100.0% | 42.1% |
| at_period_close | all | label.n1_primary_took_period_n_low | 6 | 1349 | 0.912 | 0.919 | 0.867 | 0.022 | 98.6% | 95.7% | 54.6% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 6 | 1349 | 0.912 | 0.911 | 0.875 | 0.022 | 100.0% | 100.0% | 55.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 6 | 1349 | 0.910 | 0.907 | 0.881 | 0.020 | 99.1% | 94.7% | 53.6% |
| at_period_close | all | label.n1_primary_took_period_n_high | 6 | 1349 | 0.904 | 0.907 | 0.878 | 0.019 | 100.0% | 100.0% | 46.2% |
| at_period_close | low | label.n1_close_moved_with_thesis | 6 | 650 | 0.892 | 0.895 | 0.856 | 0.026 | 100.0% | 100.0% | 49.5% |
| at_period_close | low | label.n1_primary_took_period_n_low | 6 | 650 | 0.891 | 0.910 | 0.789 | 0.047 | 97.3% | 91.7% | 50.1% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 6 | 699 | 0.868 | 0.871 | 0.805 | 0.037 | 100.0% | 100.0% | 46.4% |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | 6 | 699 | 0.863 | 0.867 | 0.808 | 0.034 | 98.7% | 92.3% | 44.9% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_period_close | all | label.n1_close_moved_with_thesis | 2020 | 179 | 44.7% | 0.909 | 0.844 | 0.553 | 18 | 100.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2021 | 227 | 42.7% | 0.928 | 0.837 | 0.573 | 23 | 100.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2022 | 185 | 46.5% | 0.940 | 0.870 | 0.535 | 19 | 94.7% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2023 | 255 | 46.7% | 0.881 | 0.792 | 0.533 | 26 | 100.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2024 | 279 | 47.3% | 0.905 | 0.803 | 0.527 | 28 | 100.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2025 | 224 | 45.5% | 0.895 | 0.817 | 0.545 | 23 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_high | 2020 | 179 | 55.3% | 0.909 | 0.855 | 0.447 | 18 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_high | 2021 | 227 | 59.0% | 0.924 | 0.841 | 0.410 | 23 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_high | 2022 | 185 | 47.6% | 0.927 | 0.838 | 0.476 | 19 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_high | 2023 | 255 | 56.5% | 0.878 | 0.792 | 0.565 | 26 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_high | 2024 | 279 | 53.8% | 0.905 | 0.824 | 0.538 | 28 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_high | 2025 | 224 | 50.4% | 0.882 | 0.790 | 0.504 | 23 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2020 | 179 | 40.8% | 0.925 | 0.849 | 0.592 | 18 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2021 | 227 | 39.2% | 0.922 | 0.819 | 0.608 | 23 | 95.7% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2022 | 185 | 48.6% | 0.935 | 0.865 | 0.514 | 19 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2023 | 255 | 42.0% | 0.867 | 0.761 | 0.580 | 26 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2024 | 279 | 45.5% | 0.909 | 0.806 | 0.545 | 28 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2025 | 224 | 47.3% | 0.916 | 0.839 | 0.527 | 23 | 95.7% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2020 | 179 | 42.5% | 0.911 | 0.832 | 0.575 | 18 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2021 | 227 | 44.1% | 0.926 | 0.855 | 0.559 | 23 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2022 | 185 | 44.9% | 0.948 | 0.854 | 0.551 | 19 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2023 | 255 | 47.1% | 0.875 | 0.788 | 0.529 | 26 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2024 | 279 | 47.7% | 0.900 | 0.835 | 0.523 | 28 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2025 | 224 | 43.8% | 0.910 | 0.857 | 0.562 | 23 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2020 | 93 | 37.6% | 0.938 | 0.882 | 0.624 | 10 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2021 | 114 | 34.2% | 0.965 | 0.868 | 0.658 | 12 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2022 | 95 | 45.3% | 0.947 | 0.842 | 0.547 | 10 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2023 | 130 | 40.0% | 0.916 | 0.831 | 0.600 | 13 | 92.3% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2024 | 142 | 45.1% | 0.909 | 0.831 | 0.549 | 15 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2025 | 125 | 43.2% | 0.891 | 0.824 | 0.568 | 13 | 100.0% |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | 2020 | 93 | 47.3% | 0.903 | 0.785 | 0.473 | 10 | 100.0% |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | 2021 | 114 | 47.4% | 0.834 | 0.702 | 0.474 | 12 | 100.0% |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | 2022 | 95 | 64.2% | 0.808 | 0.726 | 0.642 | 10 | 100.0% |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | 2023 | 130 | 53.1% | 0.874 | 0.823 | 0.531 | 13 | 92.3% |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | 2024 | 142 | 53.5% | 0.860 | 0.746 | 0.535 | 15 | 100.0% |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | 2025 | 125 | 57.6% | 0.899 | 0.856 | 0.576 | 13 | 100.0% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 2020 | 93 | 48.4% | 0.906 | 0.839 | 0.484 | 10 | 100.0% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 2021 | 114 | 47.4% | 0.862 | 0.781 | 0.474 | 12 | 100.0% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 2022 | 95 | 63.2% | 0.805 | 0.726 | 0.632 | 10 | 100.0% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 2023 | 130 | 54.6% | 0.879 | 0.808 | 0.546 | 13 | 100.0% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 2024 | 142 | 52.8% | 0.843 | 0.732 | 0.528 | 15 | 100.0% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 2025 | 125 | 55.2% | 0.913 | 0.848 | 0.552 | 13 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_high | 2020 | 93 | 61.3% | 0.938 | 0.839 | 0.613 | 10 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_high | 2021 | 114 | 64.9% | 0.944 | 0.860 | 0.649 | 12 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_high | 2022 | 95 | 50.5% | 0.948 | 0.853 | 0.505 | 10 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_high | 2023 | 130 | 59.2% | 0.918 | 0.831 | 0.592 | 13 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_high | 2024 | 142 | 56.3% | 0.921 | 0.859 | 0.563 | 15 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_high | 2025 | 125 | 55.2% | 0.875 | 0.776 | 0.552 | 13 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2020 | 93 | 36.6% | 0.930 | 0.849 | 0.634 | 10 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2021 | 114 | 35.1% | 0.955 | 0.877 | 0.649 | 12 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2022 | 95 | 45.3% | 0.954 | 0.884 | 0.547 | 10 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2023 | 130 | 40.8% | 0.899 | 0.838 | 0.592 | 13 | 92.3% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2024 | 142 | 44.4% | 0.921 | 0.845 | 0.556 | 15 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2025 | 125 | 43.2% | 0.917 | 0.824 | 0.568 | 13 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2020 | 93 | 36.6% | 0.930 | 0.849 | 0.634 | 10 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2021 | 114 | 35.1% | 0.955 | 0.877 | 0.649 | 12 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2022 | 95 | 45.3% | 0.954 | 0.884 | 0.547 | 10 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2023 | 130 | 40.8% | 0.899 | 0.838 | 0.592 | 13 | 92.3% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2024 | 142 | 44.4% | 0.921 | 0.845 | 0.556 | 15 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2025 | 125 | 43.2% | 0.917 | 0.824 | 0.568 | 13 | 100.0% |
| at_period_close | low | label.n1_close_moved_with_thesis | 2020 | 86 | 52.3% | 0.863 | 0.767 | 0.477 | 9 | 100.0% |
| at_period_close | low | label.n1_close_moved_with_thesis | 2021 | 113 | 51.3% | 0.905 | 0.832 | 0.487 | 12 | 100.0% |
| at_period_close | low | label.n1_close_moved_with_thesis | 2022 | 90 | 47.8% | 0.929 | 0.844 | 0.522 | 9 | 100.0% |
| at_period_close | low | label.n1_close_moved_with_thesis | 2023 | 125 | 53.6% | 0.856 | 0.736 | 0.464 | 13 | 100.0% |
| at_period_close | low | label.n1_close_moved_with_thesis | 2024 | 137 | 49.6% | 0.885 | 0.803 | 0.504 | 14 | 100.0% |
| at_period_close | low | label.n1_close_moved_with_thesis | 2025 | 99 | 48.5% | 0.912 | 0.828 | 0.515 | 10 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2020 | 86 | 45.3% | 0.920 | 0.860 | 0.547 | 9 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2021 | 113 | 43.4% | 0.902 | 0.814 | 0.566 | 12 | 91.7% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2022 | 90 | 52.2% | 0.921 | 0.844 | 0.478 | 9 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2023 | 125 | 43.2% | 0.789 | 0.672 | 0.568 | 13 | 92.3% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2024 | 137 | 46.7% | 0.897 | 0.803 | 0.533 | 14 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2025 | 99 | 52.5% | 0.918 | 0.848 | 0.475 | 10 | 100.0% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
