# ML snapshot walk-forward validation

_Generated `2026-05-12T04:28:53.076373+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots_xctx.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshot_leaderboard_xctx.parquet`
- Event type: `all`
- Candidates: `8`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_walk_forward_summary_xctx.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_walk_forward_summary_xctx.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_walk_forward_folds_xctx.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_walk_forward_folds_xctx.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 4676 |
| schema_feature_columns | 873 |
| schema_label_columns | 18 |
| folds_attempted | 48 |
| folds_ok | 48 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_period_close | high | label.n1_thesis_confirmed_strict | 6 | 699 | 0.948 | 0.950 | 0.927 | 0.017 | 100.0% | 100.0% | 59.1% |
| at_period_close | high | label.n1_primary_took_period_n_low | 6 | 699 | 0.948 | 0.950 | 0.927 | 0.017 | 100.0% | 100.0% | 59.1% |
| at_period_close | high | label.n1_close_moved_with_thesis | 6 | 699 | 0.945 | 0.946 | 0.923 | 0.016 | 98.7% | 92.3% | 57.8% |
| at_period_close | low | label.n1_primary_took_period_n_low | 6 | 650 | 0.940 | 0.934 | 0.909 | 0.028 | 98.7% | 92.3% | 51.5% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 6 | 1349 | 0.939 | 0.940 | 0.922 | 0.011 | 100.0% | 100.0% | 55.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 6 | 1349 | 0.937 | 0.937 | 0.921 | 0.010 | 98.4% | 94.7% | 52.8% |
| at_period_close | all | label.n1_primary_took_period_n_low | 6 | 1349 | 0.936 | 0.938 | 0.913 | 0.016 | 100.0% | 100.0% | 56.1% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 6 | 650 | 0.930 | 0.930 | 0.914 | 0.011 | 100.0% | 100.0% | 50.7% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_period_close | all | label.n1_close_moved_with_thesis | 2020 | 179 | 44.7% | 0.952 | 0.866 | 0.553 | 18 | 100.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2021 | 227 | 42.7% | 0.945 | 0.841 | 0.573 | 23 | 95.7% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2022 | 185 | 46.5% | 0.937 | 0.865 | 0.535 | 19 | 94.7% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2023 | 255 | 46.7% | 0.921 | 0.843 | 0.533 | 26 | 100.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2024 | 279 | 47.3% | 0.936 | 0.842 | 0.527 | 28 | 100.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2025 | 224 | 45.5% | 0.929 | 0.853 | 0.545 | 23 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2020 | 179 | 40.8% | 0.945 | 0.877 | 0.592 | 18 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2021 | 227 | 39.2% | 0.954 | 0.859 | 0.608 | 23 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2022 | 185 | 48.6% | 0.931 | 0.838 | 0.514 | 19 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2023 | 255 | 42.0% | 0.920 | 0.831 | 0.580 | 26 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2024 | 279 | 45.5% | 0.913 | 0.821 | 0.545 | 28 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2025 | 224 | 47.3% | 0.955 | 0.862 | 0.527 | 23 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2020 | 179 | 42.5% | 0.944 | 0.866 | 0.575 | 18 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2021 | 227 | 44.1% | 0.944 | 0.863 | 0.559 | 23 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2022 | 185 | 44.9% | 0.958 | 0.865 | 0.551 | 19 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2023 | 255 | 47.1% | 0.922 | 0.839 | 0.529 | 26 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2024 | 279 | 47.7% | 0.933 | 0.857 | 0.523 | 28 | 100.0% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 2025 | 224 | 43.8% | 0.935 | 0.857 | 0.562 | 23 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2020 | 93 | 37.6% | 0.958 | 0.892 | 0.624 | 10 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2021 | 114 | 34.2% | 0.967 | 0.904 | 0.658 | 12 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2022 | 95 | 45.3% | 0.955 | 0.895 | 0.547 | 10 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2023 | 130 | 40.0% | 0.937 | 0.846 | 0.600 | 13 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2024 | 142 | 45.1% | 0.923 | 0.845 | 0.549 | 15 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2025 | 125 | 43.2% | 0.927 | 0.848 | 0.568 | 13 | 92.3% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2020 | 93 | 36.6% | 0.962 | 0.925 | 0.634 | 10 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2021 | 114 | 35.1% | 0.970 | 0.868 | 0.649 | 12 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2022 | 95 | 45.3% | 0.961 | 0.884 | 0.547 | 10 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2023 | 130 | 40.8% | 0.927 | 0.838 | 0.592 | 13 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2024 | 142 | 44.4% | 0.931 | 0.845 | 0.556 | 15 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2025 | 125 | 43.2% | 0.938 | 0.856 | 0.568 | 13 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2020 | 93 | 36.6% | 0.962 | 0.925 | 0.634 | 10 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2021 | 114 | 35.1% | 0.970 | 0.868 | 0.649 | 12 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2022 | 95 | 45.3% | 0.961 | 0.884 | 0.547 | 10 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2023 | 130 | 40.8% | 0.927 | 0.838 | 0.592 | 13 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2024 | 142 | 44.4% | 0.931 | 0.845 | 0.556 | 15 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2025 | 125 | 43.2% | 0.938 | 0.856 | 0.568 | 13 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2020 | 86 | 45.3% | 0.987 | 0.953 | 0.547 | 9 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2021 | 113 | 43.4% | 0.941 | 0.832 | 0.566 | 12 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2022 | 90 | 52.2% | 0.909 | 0.833 | 0.478 | 9 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2023 | 125 | 43.2% | 0.909 | 0.816 | 0.568 | 13 | 92.3% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2024 | 137 | 46.7% | 0.926 | 0.854 | 0.533 | 14 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2025 | 99 | 52.5% | 0.964 | 0.869 | 0.475 | 10 | 100.0% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 2020 | 86 | 48.8% | 0.925 | 0.849 | 0.512 | 9 | 100.0% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 2021 | 113 | 53.1% | 0.935 | 0.814 | 0.469 | 12 | 100.0% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 2022 | 90 | 44.4% | 0.949 | 0.867 | 0.556 | 9 | 100.0% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 2023 | 125 | 53.6% | 0.924 | 0.824 | 0.464 | 13 | 100.0% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 2024 | 137 | 51.1% | 0.935 | 0.832 | 0.489 | 14 | 100.0% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 2025 | 99 | 44.4% | 0.914 | 0.808 | 0.556 | 10 | 100.0% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
