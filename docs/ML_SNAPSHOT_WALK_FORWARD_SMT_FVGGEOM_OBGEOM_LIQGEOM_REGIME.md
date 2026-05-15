# ML snapshot walk-forward validation

_Generated `2026-05-15T02:04:19.554572+00:00`._

## Setup

- Matrix: `data\ml\anchors\smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- Schema: `data\ml\anchors\smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- Leaderboard source: `data\ml\anchors\smt_previous_day_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- Event type: `previous_day_smt`
- Candidates: `8`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\smt_previous_day_walk_forward_fvggeom_obgeom_liqgeom_regime_summary.csv | candidate summary CSV |
| data\ml\anchors\smt_previous_day_walk_forward_fvggeom_obgeom_liqgeom_regime_summary.parquet | candidate summary parquet |
| data\ml\anchors\smt_previous_day_walk_forward_fvggeom_obgeom_liqgeom_regime_folds.csv | per-fold CSV |
| data\ml\anchors\smt_previous_day_walk_forward_fvggeom_obgeom_liqgeom_regime_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 4676 |
| schema_feature_columns | 3150 |
| schema_label_columns | 18 |
| folds_attempted | 48 |
| folds_ok | 48 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_period_close | high | label.n1_primary_took_period_n_high | 6 | 699 | 0.975 | 0.973 | 0.966 | 0.007 | 100.0% | 100.0% | 42.1% |
| at_period_close | high | label.n1_close_moved_with_thesis | 6 | 699 | 0.970 | 0.971 | 0.953 | 0.010 | 98.7% | 92.3% | 57.8% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 6 | 699 | 0.967 | 0.965 | 0.955 | 0.010 | 100.0% | 100.0% | 59.1% |
| at_period_close | high | label.n1_primary_took_period_n_low | 6 | 699 | 0.967 | 0.965 | 0.955 | 0.010 | 100.0% | 100.0% | 59.1% |
| at_period_close | low | label.n1_primary_took_period_n_low | 6 | 650 | 0.964 | 0.965 | 0.931 | 0.019 | 100.0% | 100.0% | 52.8% |
| at_period_close | all | label.n1_primary_took_period_n_high | 6 | 1349 | 0.964 | 0.962 | 0.959 | 0.006 | 100.0% | 100.0% | 46.2% |
| at_period_close | all | label.n1_primary_took_period_n_low | 6 | 1349 | 0.963 | 0.960 | 0.949 | 0.012 | 99.4% | 96.2% | 55.5% |
| at_period_close | all | label.n1_close_moved_with_thesis | 6 | 1349 | 0.957 | 0.955 | 0.946 | 0.007 | 100.0% | 100.0% | 54.4% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_period_close | all | label.n1_close_moved_with_thesis | 2020 | 179 | 44.7% | 0.965 | 0.911 | 0.553 | 18 | 100.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2021 | 227 | 42.7% | 0.968 | 0.894 | 0.573 | 23 | 100.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2022 | 185 | 46.5% | 0.951 | 0.886 | 0.535 | 19 | 100.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2023 | 255 | 46.7% | 0.955 | 0.867 | 0.533 | 26 | 100.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2024 | 279 | 47.3% | 0.955 | 0.867 | 0.527 | 28 | 100.0% |
| at_period_close | all | label.n1_close_moved_with_thesis | 2025 | 224 | 45.5% | 0.946 | 0.848 | 0.545 | 23 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_high | 2020 | 179 | 55.3% | 0.965 | 0.894 | 0.447 | 18 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_high | 2021 | 227 | 59.0% | 0.976 | 0.921 | 0.410 | 23 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_high | 2022 | 185 | 47.6% | 0.959 | 0.881 | 0.476 | 19 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_high | 2023 | 255 | 56.5% | 0.964 | 0.906 | 0.565 | 26 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_high | 2024 | 279 | 53.8% | 0.959 | 0.864 | 0.538 | 28 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_high | 2025 | 224 | 50.4% | 0.959 | 0.897 | 0.504 | 23 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2020 | 179 | 40.8% | 0.981 | 0.916 | 0.592 | 18 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2021 | 227 | 39.2% | 0.977 | 0.907 | 0.608 | 23 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2022 | 185 | 48.6% | 0.949 | 0.892 | 0.514 | 19 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2023 | 255 | 42.0% | 0.960 | 0.875 | 0.580 | 26 | 96.2% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2024 | 279 | 45.5% | 0.952 | 0.871 | 0.545 | 28 | 100.0% |
| at_period_close | all | label.n1_primary_took_period_n_low | 2025 | 224 | 47.3% | 0.960 | 0.888 | 0.527 | 23 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2020 | 93 | 37.6% | 0.980 | 0.914 | 0.624 | 10 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2021 | 114 | 34.2% | 0.983 | 0.947 | 0.658 | 12 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2022 | 95 | 45.3% | 0.973 | 0.926 | 0.547 | 10 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2023 | 130 | 40.0% | 0.969 | 0.877 | 0.600 | 13 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2024 | 142 | 45.1% | 0.965 | 0.880 | 0.549 | 15 | 100.0% |
| at_period_close | high | label.n1_close_moved_with_thesis | 2025 | 125 | 43.2% | 0.953 | 0.864 | 0.568 | 13 | 92.3% |
| at_period_close | high | label.n1_primary_took_period_n_high | 2020 | 93 | 61.3% | 0.982 | 0.935 | 0.613 | 10 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_high | 2021 | 114 | 64.9% | 0.986 | 0.947 | 0.649 | 12 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_high | 2022 | 95 | 50.5% | 0.975 | 0.916 | 0.505 | 10 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_high | 2023 | 130 | 59.2% | 0.971 | 0.900 | 0.592 | 13 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_high | 2024 | 142 | 56.3% | 0.969 | 0.887 | 0.563 | 15 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_high | 2025 | 125 | 55.2% | 0.966 | 0.896 | 0.552 | 13 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2020 | 93 | 36.6% | 0.974 | 0.914 | 0.634 | 10 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2021 | 114 | 35.1% | 0.984 | 0.930 | 0.649 | 12 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2022 | 95 | 45.3% | 0.969 | 0.905 | 0.547 | 10 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2023 | 130 | 40.8% | 0.960 | 0.877 | 0.592 | 13 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2024 | 142 | 44.4% | 0.958 | 0.880 | 0.556 | 15 | 100.0% |
| at_period_close | high | label.n1_primary_took_period_n_low | 2025 | 125 | 43.2% | 0.955 | 0.864 | 0.568 | 13 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2020 | 93 | 36.6% | 0.974 | 0.914 | 0.634 | 10 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2021 | 114 | 35.1% | 0.984 | 0.930 | 0.649 | 12 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2022 | 95 | 45.3% | 0.969 | 0.905 | 0.547 | 10 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2023 | 130 | 40.8% | 0.960 | 0.877 | 0.592 | 13 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2024 | 142 | 44.4% | 0.958 | 0.880 | 0.556 | 15 | 100.0% |
| at_period_close | high | label.n1_thesis_confirmed_strict | 2025 | 125 | 43.2% | 0.955 | 0.864 | 0.568 | 13 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2020 | 86 | 45.3% | 0.995 | 0.953 | 0.547 | 9 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2021 | 113 | 43.4% | 0.971 | 0.912 | 0.566 | 12 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2022 | 90 | 52.2% | 0.931 | 0.867 | 0.478 | 9 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2023 | 125 | 43.2% | 0.963 | 0.904 | 0.568 | 13 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2024 | 137 | 46.7% | 0.957 | 0.891 | 0.533 | 14 | 100.0% |
| at_period_close | low | label.n1_primary_took_period_n_low | 2025 | 99 | 52.5% | 0.966 | 0.899 | 0.475 | 10 | 100.0% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
