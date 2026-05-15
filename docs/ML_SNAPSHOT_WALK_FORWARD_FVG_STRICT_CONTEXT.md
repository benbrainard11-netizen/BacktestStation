# ML snapshot walk-forward validation

_Generated `2026-05-15T17:29:09.140379+00:00`._

## Setup

- Matrix: `data\ml\anchors\fvg_snapshots_xctx_fvggeom_obgeom_strict.parquet`
- Schema: `data\ml\anchors\fvg_snapshots_xctx_fvggeom_obgeom_strict.schema.json`
- Leaderboard source: `data\ml\anchors\fvg_snapshot_leaderboard_strict_context.parquet`
- Event type: `all`
- Candidates: `4`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\fvg_walk_forward_strict_context_summary.csv | candidate summary CSV |
| data\ml\anchors\fvg_walk_forward_strict_context_summary.parquet | candidate summary parquet |
| data\ml\anchors\fvg_walk_forward_strict_context_folds.csv | per-fold CSV |
| data\ml\anchors\fvg_walk_forward_strict_context_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 209339 |
| schema_feature_columns | 1969 |
| schema_label_columns | 133 |
| folds_attempted | 24 |
| folds_ok | 24 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.strict.forward_10c.after_tap_failed_1x_against | 6 | 116489 | 0.717 | 0.718 | 0.712 | 0.004 | 25.2% | 24.2% | 13.3% |
| at_fire | all | label.strict.no_touch_continuation | 6 | 116489 | 0.715 | 0.720 | 0.671 | 0.021 | 14.0% | 11.6% | 8.9% |
| at_fire | all | label.strict.forward_10c.after_tap_1x_clean | 6 | 116489 | 0.692 | 0.694 | 0.672 | 0.010 | 15.0% | 14.1% | 7.9% |
| at_fire | all | label.strict.tap_wick_rejected | 6 | 116489 | 0.533 | 0.533 | 0.527 | 0.004 | 48.5% | 47.2% | 3.2% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.strict.forward_10c.after_tap_1x_clean | 2020 | 19458 | 7.3% | 0.672 | 0.927 | 0.927 | 1946 | 14.1% |
| at_fire | all | label.strict.forward_10c.after_tap_1x_clean | 2021 | 19154 | 7.3% | 0.698 | 0.927 | 0.927 | 1916 | 16.2% |
| at_fire | all | label.strict.forward_10c.after_tap_1x_clean | 2022 | 20059 | 6.9% | 0.700 | 0.931 | 0.931 | 2006 | 14.7% |
| at_fire | all | label.strict.forward_10c.after_tap_1x_clean | 2023 | 18955 | 6.9% | 0.689 | 0.931 | 0.931 | 1896 | 14.6% |
| at_fire | all | label.strict.forward_10c.after_tap_1x_clean | 2024 | 19338 | 7.2% | 0.703 | 0.928 | 0.928 | 1934 | 15.7% |
| at_fire | all | label.strict.forward_10c.after_tap_1x_clean | 2025 | 19525 | 7.4% | 0.688 | 0.926 | 0.926 | 1953 | 14.7% |
| at_fire | all | label.strict.forward_10c.after_tap_failed_1x_against | 2020 | 19458 | 11.8% | 0.723 | 0.882 | 0.882 | 1946 | 25.4% |
| at_fire | all | label.strict.forward_10c.after_tap_failed_1x_against | 2021 | 19154 | 11.4% | 0.712 | 0.886 | 0.886 | 1916 | 24.4% |
| at_fire | all | label.strict.forward_10c.after_tap_failed_1x_against | 2022 | 20059 | 11.6% | 0.718 | 0.884 | 0.884 | 2006 | 24.2% |
| at_fire | all | label.strict.forward_10c.after_tap_failed_1x_against | 2023 | 18955 | 11.9% | 0.719 | 0.881 | 0.881 | 1896 | 25.5% |
| at_fire | all | label.strict.forward_10c.after_tap_failed_1x_against | 2024 | 19338 | 12.3% | 0.719 | 0.877 | 0.877 | 1934 | 26.8% |
| at_fire | all | label.strict.forward_10c.after_tap_failed_1x_against | 2025 | 19525 | 12.4% | 0.714 | 0.876 | 0.876 | 1953 | 25.2% |
| at_fire | all | label.strict.no_touch_continuation | 2020 | 19458 | 5.4% | 0.671 | 0.946 | 0.946 | 1946 | 11.6% |
| at_fire | all | label.strict.no_touch_continuation | 2021 | 19154 | 5.6% | 0.715 | 0.944 | 0.944 | 1916 | 15.4% |
| at_fire | all | label.strict.no_touch_continuation | 2022 | 20059 | 4.8% | 0.714 | 0.952 | 0.952 | 2006 | 12.8% |
| at_fire | all | label.strict.no_touch_continuation | 2023 | 18955 | 5.2% | 0.734 | 0.948 | 0.948 | 1896 | 16.2% |
| at_fire | all | label.strict.no_touch_continuation | 2024 | 19338 | 5.2% | 0.729 | 0.948 | 0.948 | 1934 | 14.7% |
| at_fire | all | label.strict.no_touch_continuation | 2025 | 19525 | 4.8% | 0.725 | 0.952 | 0.952 | 1953 | 13.5% |
| at_fire | all | label.strict.tap_wick_rejected | 2020 | 19458 | 46.3% | 0.527 | 0.537 | 0.537 | 1946 | 47.7% |
| at_fire | all | label.strict.tap_wick_rejected | 2021 | 19154 | 44.2% | 0.534 | 0.557 | 0.558 | 1916 | 49.3% |
| at_fire | all | label.strict.tap_wick_rejected | 2022 | 20059 | 45.6% | 0.531 | 0.542 | 0.544 | 2006 | 47.8% |
| at_fire | all | label.strict.tap_wick_rejected | 2023 | 18955 | 46.1% | 0.534 | 0.539 | 0.539 | 1896 | 49.1% |
| at_fire | all | label.strict.tap_wick_rejected | 2024 | 19338 | 45.0% | 0.540 | 0.550 | 0.550 | 1934 | 49.8% |
| at_fire | all | label.strict.tap_wick_rejected | 2025 | 19525 | 44.6% | 0.531 | 0.551 | 0.554 | 1953 | 47.2% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
