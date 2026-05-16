# ML snapshot walk-forward validation

_Generated `2026-05-16T17:04:48.621295+00:00`._

## Setup

- Matrix: `data\ml\anchors\ob_snapshots_xctx_strict.parquet`
- Schema: `data\ml\anchors\ob_snapshots_xctx_strict.schema.json`
- Leaderboard source: `data\ml\anchors\ob_snapshot_leaderboard_strict_context.parquet`
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
| data\ml\anchors\ob_walk_forward_strict_context_summary.csv | candidate summary CSV |
| data\ml\anchors\ob_walk_forward_strict_context_summary.parquet | candidate summary parquet |
| data\ml\anchors\ob_walk_forward_strict_context_folds.csv | per-fold CSV |
| data\ml\anchors\ob_walk_forward_strict_context_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 46331 |
| schema_feature_columns | 650 |
| schema_label_columns | 236 |
| folds_attempted | 48 |
| folds_ok | 48 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.strict.next_60m.ob_broken_through_continuation | 6 | 25018 | 0.797 | 0.803 | 0.772 | 0.013 | 55.2% | 51.8% | 36.5% |
| at_fire | bearish | label.strict.next_60m.ob_broken_through_continuation | 6 | 13359 | 0.794 | 0.801 | 0.771 | 0.015 | 54.3% | 49.8% | 34.9% |
| at_fire | all | label.strict.next_60m.ob_swept_and_recovered | 6 | 25018 | 0.793 | 0.806 | 0.753 | 0.023 | 19.7% | 15.3% | 14.2% |
| at_fire | bullish | label.strict.next_60m.ob_broken_through_continuation | 6 | 11659 | 0.785 | 0.791 | 0.744 | 0.019 | 53.2% | 48.6% | 35.1% |
| at_fire | bullish | label.strict.next_60m.ob_swept_and_recovered | 6 | 11659 | 0.781 | 0.791 | 0.720 | 0.037 | 20.6% | 15.6% | 15.1% |
| at_fire | all | label.strict.next_240m.ob_broken_through_continuation | 6 | 25018 | 0.770 | 0.776 | 0.737 | 0.017 | 76.6% | 71.6% | 38.6% |
| at_fire | all | label.strict.next_60m.ob_failed_immediately | 6 | 25018 | 0.767 | 0.768 | 0.756 | 0.008 | 62.0% | 55.6% | 31.3% |
| at_fire | bearish | label.strict.next_240m.ob_broken_through_continuation | 6 | 13359 | 0.766 | 0.768 | 0.734 | 0.020 | 75.7% | 68.1% | 36.3% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.strict.next_240m.ob_broken_through_continuation | 2020 | 4088 | 36.2% | 0.737 | 0.698 | 0.638 | 409 | 71.6% |
| at_fire | all | label.strict.next_240m.ob_broken_through_continuation | 2021 | 4260 | 36.3% | 0.759 | 0.705 | 0.637 | 426 | 73.2% |
| at_fire | all | label.strict.next_240m.ob_broken_through_continuation | 2022 | 4262 | 38.4% | 0.784 | 0.710 | 0.616 | 427 | 79.2% |
| at_fire | all | label.strict.next_240m.ob_broken_through_continuation | 2023 | 4129 | 39.9% | 0.785 | 0.713 | 0.601 | 413 | 79.7% |
| at_fire | all | label.strict.next_240m.ob_broken_through_continuation | 2024 | 4188 | 39.2% | 0.777 | 0.707 | 0.608 | 419 | 76.8% |
| at_fire | all | label.strict.next_240m.ob_broken_through_continuation | 2025 | 4091 | 38.1% | 0.776 | 0.721 | 0.619 | 410 | 79.0% |
| at_fire | all | label.strict.next_60m.ob_broken_through_continuation | 2020 | 4088 | 16.8% | 0.772 | 0.839 | 0.832 | 409 | 51.8% |
| at_fire | all | label.strict.next_60m.ob_broken_through_continuation | 2021 | 4260 | 17.3% | 0.790 | 0.838 | 0.827 | 426 | 52.3% |
| at_fire | all | label.strict.next_60m.ob_broken_through_continuation | 2022 | 4262 | 19.4% | 0.807 | 0.825 | 0.806 | 427 | 57.4% |
| at_fire | all | label.strict.next_60m.ob_broken_through_continuation | 2023 | 4129 | 19.8% | 0.808 | 0.822 | 0.802 | 413 | 57.6% |
| at_fire | all | label.strict.next_60m.ob_broken_through_continuation | 2024 | 4188 | 20.1% | 0.800 | 0.809 | 0.799 | 419 | 54.2% |
| at_fire | all | label.strict.next_60m.ob_broken_through_continuation | 2025 | 4091 | 19.0% | 0.806 | 0.828 | 0.810 | 410 | 57.8% |
| at_fire | all | label.strict.next_60m.ob_failed_immediately | 2020 | 4088 | 29.8% | 0.756 | 0.724 | 0.702 | 409 | 55.7% |
| at_fire | all | label.strict.next_60m.ob_failed_immediately | 2021 | 4260 | 28.9% | 0.757 | 0.734 | 0.711 | 426 | 55.6% |
| at_fire | all | label.strict.next_60m.ob_failed_immediately | 2022 | 4262 | 31.7% | 0.773 | 0.728 | 0.683 | 427 | 65.3% |
| at_fire | all | label.strict.next_60m.ob_failed_immediately | 2023 | 4129 | 30.0% | 0.766 | 0.727 | 0.700 | 413 | 63.4% |
| at_fire | all | label.strict.next_60m.ob_failed_immediately | 2024 | 4188 | 31.7% | 0.779 | 0.736 | 0.683 | 419 | 65.9% |
| at_fire | all | label.strict.next_60m.ob_failed_immediately | 2025 | 4091 | 31.8% | 0.771 | 0.726 | 0.682 | 410 | 65.9% |
| at_fire | all | label.strict.next_60m.ob_swept_and_recovered | 2020 | 4088 | 5.0% | 0.753 | 0.949 | 0.950 | 409 | 17.4% |
| at_fire | all | label.strict.next_60m.ob_swept_and_recovered | 2021 | 4260 | 4.9% | 0.803 | 0.952 | 0.951 | 426 | 19.7% |
| at_fire | all | label.strict.next_60m.ob_swept_and_recovered | 2022 | 4262 | 6.1% | 0.809 | 0.939 | 0.939 | 427 | 20.6% |
| at_fire | all | label.strict.next_60m.ob_swept_and_recovered | 2023 | 4129 | 5.7% | 0.813 | 0.941 | 0.943 | 413 | 22.8% |
| at_fire | all | label.strict.next_60m.ob_swept_and_recovered | 2024 | 4188 | 5.4% | 0.770 | 0.943 | 0.946 | 419 | 15.3% |
| at_fire | all | label.strict.next_60m.ob_swept_and_recovered | 2025 | 4091 | 5.5% | 0.813 | 0.945 | 0.945 | 410 | 22.2% |
| at_fire | bearish | label.strict.next_240m.ob_broken_through_continuation | 2020 | 2298 | 38.7% | 0.747 | 0.689 | 0.613 | 230 | 74.8% |
| at_fire | bearish | label.strict.next_240m.ob_broken_through_continuation | 2021 | 2342 | 37.6% | 0.734 | 0.685 | 0.624 | 235 | 68.1% |
| at_fire | bearish | label.strict.next_240m.ob_broken_through_continuation | 2022 | 2068 | 40.4% | 0.791 | 0.719 | 0.596 | 207 | 85.5% |
| at_fire | bearish | label.strict.next_240m.ob_broken_through_continuation | 2023 | 2204 | 39.9% | 0.772 | 0.695 | 0.601 | 221 | 74.7% |
| at_fire | bearish | label.strict.next_240m.ob_broken_through_continuation | 2024 | 2265 | 40.7% | 0.765 | 0.693 | 0.593 | 227 | 74.4% |
| at_fire | bearish | label.strict.next_240m.ob_broken_through_continuation | 2025 | 2182 | 39.1% | 0.785 | 0.718 | 0.609 | 219 | 76.7% |
| at_fire | bearish | label.strict.next_60m.ob_broken_through_continuation | 2020 | 2298 | 17.0% | 0.771 | 0.832 | 0.830 | 230 | 54.3% |
| at_fire | bearish | label.strict.next_60m.ob_broken_through_continuation | 2021 | 2342 | 17.8% | 0.777 | 0.831 | 0.822 | 235 | 49.8% |
| at_fire | bearish | label.strict.next_60m.ob_broken_through_continuation | 2022 | 2068 | 19.8% | 0.811 | 0.821 | 0.802 | 207 | 55.6% |
| at_fire | bearish | label.strict.next_60m.ob_broken_through_continuation | 2023 | 2204 | 20.5% | 0.805 | 0.810 | 0.795 | 221 | 53.4% |
| at_fire | bearish | label.strict.next_60m.ob_broken_through_continuation | 2024 | 2265 | 21.5% | 0.799 | 0.802 | 0.785 | 227 | 56.8% |
| at_fire | bearish | label.strict.next_60m.ob_broken_through_continuation | 2025 | 2182 | 19.3% | 0.804 | 0.826 | 0.807 | 219 | 55.7% |
| at_fire | bullish | label.strict.next_60m.ob_broken_through_continuation | 2020 | 1790 | 16.5% | 0.744 | 0.836 | 0.835 | 179 | 48.6% |
| at_fire | bullish | label.strict.next_60m.ob_broken_through_continuation | 2021 | 1918 | 16.7% | 0.802 | 0.842 | 0.833 | 192 | 49.0% |
| at_fire | bullish | label.strict.next_60m.ob_broken_through_continuation | 2022 | 2194 | 19.0% | 0.783 | 0.825 | 0.810 | 220 | 55.0% |
| at_fire | bullish | label.strict.next_60m.ob_broken_through_continuation | 2023 | 1925 | 19.1% | 0.798 | 0.817 | 0.809 | 193 | 58.5% |
| at_fire | bullish | label.strict.next_60m.ob_broken_through_continuation | 2024 | 1923 | 18.4% | 0.788 | 0.819 | 0.816 | 193 | 51.8% |
| at_fire | bullish | label.strict.next_60m.ob_broken_through_continuation | 2025 | 1909 | 18.6% | 0.795 | 0.827 | 0.814 | 191 | 56.0% |
| at_fire | bullish | label.strict.next_60m.ob_swept_and_recovered | 2020 | 1790 | 5.3% | 0.720 | 0.947 | 0.947 | 179 | 15.6% |
| at_fire | bullish | label.strict.next_60m.ob_swept_and_recovered | 2021 | 1918 | 5.2% | 0.750 | 0.948 | 0.948 | 192 | 20.3% |
| at_fire | bullish | label.strict.next_60m.ob_swept_and_recovered | 2022 | 2194 | 6.4% | 0.799 | 0.934 | 0.936 | 220 | 22.3% |
| at_fire | bullish | label.strict.next_60m.ob_swept_and_recovered | 2023 | 1925 | 5.6% | 0.783 | 0.944 | 0.944 | 193 | 17.6% |
| at_fire | bullish | label.strict.next_60m.ob_swept_and_recovered | 2024 | 1923 | 5.5% | 0.800 | 0.945 | 0.945 | 193 | 19.2% |
| at_fire | bullish | label.strict.next_60m.ob_swept_and_recovered | 2025 | 1909 | 5.7% | 0.835 | 0.942 | 0.943 | 191 | 28.8% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
