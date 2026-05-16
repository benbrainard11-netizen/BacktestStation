# ML snapshot walk-forward validation

_Generated `2026-05-16T01:08:47.282411+00:00`._

## Setup

- Matrix: `data\ml\anchors\swing_snapshots_strict.parquet`
- Schema: `data\ml\anchors\swing_snapshots_strict.schema.json`
- Leaderboard source: `data\ml\anchors\swing_snapshot_leaderboard_strict_context.parquet`
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
| data\ml\anchors\swing_walk_forward_strict_context_summary.csv | candidate summary CSV |
| data\ml\anchors\swing_walk_forward_strict_context_summary.parquet | candidate summary parquet |
| data\ml\anchors\swing_walk_forward_strict_context_folds.csv | per-fold CSV |
| data\ml\anchors\swing_walk_forward_strict_context_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 76786 |
| schema_feature_columns | 37 |
| schema_label_columns | 39 |
| folds_attempted | 48 |
| folds_ok | 48 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.strict.next_60m.pivot_broken_through_continuation | 6 | 41731 | 0.804 | 0.811 | 0.771 | 0.022 | 20.0% | 17.0% | 14.7% |
| at_fire | high | label.strict.next_60m.pivot_broken_through_continuation | 6 | 20980 | 0.796 | 0.799 | 0.759 | 0.029 | 18.1% | 13.9% | 12.6% |
| at_fire | all | label.strict.next_240m.pivot_broken_through_continuation | 6 | 41731 | 0.792 | 0.791 | 0.736 | 0.030 | 48.1% | 42.9% | 29.1% |
| at_fire | low | label.strict.next_240m.pivot_broken_through_continuation | 6 | 20751 | 0.790 | 0.792 | 0.750 | 0.026 | 47.4% | 41.3% | 29.4% |
| at_fire | low | label.strict.next_60m.pivot_broken_through_continuation | 6 | 20751 | 0.788 | 0.785 | 0.754 | 0.021 | 17.3% | 13.3% | 12.1% |
| at_fire | high | label.strict.next_240m.pivot_broken_through_continuation | 6 | 20980 | 0.785 | 0.785 | 0.714 | 0.038 | 47.5% | 39.2% | 27.7% |
| at_fire | all | label.strict.next_60m.pivot_failed_immediately | 6 | 41731 | 0.775 | 0.778 | 0.747 | 0.016 | 20.6% | 17.4% | 14.1% |
| at_fire | low | label.strict.next_60m.pivot_failed_immediately | 6 | 20751 | 0.775 | 0.779 | 0.739 | 0.019 | 19.7% | 15.1% | 13.6% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.strict.next_240m.pivot_broken_through_continuation | 2020 | 6876 | 19.4% | 0.736 | 0.806 | 0.806 | 688 | 42.9% |
| at_fire | all | label.strict.next_240m.pivot_broken_through_continuation | 2021 | 6927 | 19.3% | 0.780 | 0.807 | 0.807 | 693 | 44.6% |
| at_fire | all | label.strict.next_240m.pivot_broken_through_continuation | 2022 | 7035 | 19.8% | 0.790 | 0.802 | 0.802 | 704 | 50.0% |
| at_fire | all | label.strict.next_240m.pivot_broken_through_continuation | 2023 | 6993 | 18.7% | 0.828 | 0.815 | 0.813 | 700 | 53.9% |
| at_fire | all | label.strict.next_240m.pivot_broken_through_continuation | 2024 | 6954 | 18.1% | 0.823 | 0.823 | 0.819 | 696 | 48.1% |
| at_fire | all | label.strict.next_240m.pivot_broken_through_continuation | 2025 | 6946 | 18.5% | 0.792 | 0.814 | 0.815 | 695 | 49.4% |
| at_fire | all | label.strict.next_60m.pivot_broken_through_continuation | 2020 | 6876 | 5.1% | 0.771 | 0.949 | 0.949 | 688 | 17.0% |
| at_fire | all | label.strict.next_60m.pivot_broken_through_continuation | 2021 | 6927 | 5.2% | 0.816 | 0.948 | 0.948 | 693 | 20.3% |
| at_fire | all | label.strict.next_60m.pivot_broken_through_continuation | 2022 | 7035 | 5.7% | 0.779 | 0.943 | 0.943 | 704 | 18.8% |
| at_fire | all | label.strict.next_60m.pivot_broken_through_continuation | 2023 | 6993 | 5.6% | 0.834 | 0.944 | 0.944 | 700 | 23.6% |
| at_fire | all | label.strict.next_60m.pivot_broken_through_continuation | 2024 | 6954 | 5.5% | 0.814 | 0.945 | 0.945 | 696 | 21.1% |
| at_fire | all | label.strict.next_60m.pivot_broken_through_continuation | 2025 | 6946 | 5.2% | 0.807 | 0.948 | 0.948 | 695 | 19.4% |
| at_fire | all | label.strict.next_60m.pivot_failed_immediately | 2020 | 6876 | 6.2% | 0.747 | 0.938 | 0.938 | 688 | 17.4% |
| at_fire | all | label.strict.next_60m.pivot_failed_immediately | 2021 | 6927 | 5.9% | 0.781 | 0.941 | 0.941 | 693 | 19.6% |
| at_fire | all | label.strict.next_60m.pivot_failed_immediately | 2022 | 7035 | 6.7% | 0.767 | 0.933 | 0.933 | 704 | 19.7% |
| at_fire | all | label.strict.next_60m.pivot_failed_immediately | 2023 | 6993 | 7.1% | 0.800 | 0.929 | 0.929 | 700 | 26.3% |
| at_fire | all | label.strict.next_60m.pivot_failed_immediately | 2024 | 6954 | 6.4% | 0.783 | 0.936 | 0.936 | 696 | 21.1% |
| at_fire | all | label.strict.next_60m.pivot_failed_immediately | 2025 | 6946 | 6.2% | 0.775 | 0.938 | 0.938 | 695 | 19.1% |
| at_fire | high | label.strict.next_240m.pivot_broken_through_continuation | 2020 | 3434 | 21.0% | 0.714 | 0.788 | 0.790 | 344 | 39.2% |
| at_fire | high | label.strict.next_240m.pivot_broken_through_continuation | 2021 | 3473 | 21.6% | 0.786 | 0.785 | 0.784 | 348 | 49.7% |
| at_fire | high | label.strict.next_240m.pivot_broken_through_continuation | 2022 | 3519 | 19.7% | 0.778 | 0.800 | 0.803 | 352 | 44.9% |
| at_fire | high | label.strict.next_240m.pivot_broken_through_continuation | 2023 | 3571 | 19.2% | 0.834 | 0.812 | 0.808 | 358 | 56.4% |
| at_fire | high | label.strict.next_240m.pivot_broken_through_continuation | 2024 | 3507 | 18.8% | 0.817 | 0.807 | 0.812 | 351 | 46.4% |
| at_fire | high | label.strict.next_240m.pivot_broken_through_continuation | 2025 | 3476 | 18.9% | 0.784 | 0.807 | 0.811 | 348 | 48.6% |
| at_fire | high | label.strict.next_60m.pivot_broken_through_continuation | 2020 | 3434 | 5.3% | 0.761 | 0.947 | 0.947 | 344 | 15.4% |
| at_fire | high | label.strict.next_60m.pivot_broken_through_continuation | 2021 | 3473 | 5.5% | 0.824 | 0.945 | 0.945 | 348 | 19.5% |
| at_fire | high | label.strict.next_60m.pivot_broken_through_continuation | 2022 | 3519 | 5.2% | 0.759 | 0.948 | 0.948 | 352 | 13.9% |
| at_fire | high | label.strict.next_60m.pivot_broken_through_continuation | 2023 | 3571 | 6.0% | 0.835 | 0.940 | 0.940 | 358 | 23.7% |
| at_fire | high | label.strict.next_60m.pivot_broken_through_continuation | 2024 | 3507 | 5.2% | 0.792 | 0.948 | 0.948 | 351 | 17.1% |
| at_fire | high | label.strict.next_60m.pivot_broken_through_continuation | 2025 | 3476 | 5.7% | 0.806 | 0.943 | 0.943 | 348 | 19.0% |
| at_fire | low | label.strict.next_240m.pivot_broken_through_continuation | 2020 | 3442 | 17.8% | 0.750 | 0.821 | 0.822 | 345 | 41.4% |
| at_fire | low | label.strict.next_240m.pivot_broken_through_continuation | 2021 | 3454 | 17.1% | 0.765 | 0.830 | 0.829 | 346 | 41.3% |
| at_fire | low | label.strict.next_240m.pivot_broken_through_continuation | 2022 | 3516 | 19.9% | 0.793 | 0.802 | 0.801 | 352 | 52.8% |
| at_fire | low | label.strict.next_240m.pivot_broken_through_continuation | 2023 | 3422 | 18.3% | 0.815 | 0.818 | 0.817 | 343 | 55.7% |
| at_fire | low | label.strict.next_240m.pivot_broken_through_continuation | 2024 | 3447 | 17.4% | 0.826 | 0.830 | 0.826 | 345 | 49.3% |
| at_fire | low | label.strict.next_240m.pivot_broken_through_continuation | 2025 | 3470 | 18.2% | 0.790 | 0.812 | 0.818 | 347 | 44.1% |
| at_fire | low | label.strict.next_60m.pivot_broken_through_continuation | 2020 | 3442 | 5.0% | 0.754 | 0.950 | 0.950 | 345 | 13.3% |
| at_fire | low | label.strict.next_60m.pivot_broken_through_continuation | 2021 | 3454 | 4.8% | 0.793 | 0.952 | 0.952 | 346 | 16.2% |
| at_fire | low | label.strict.next_60m.pivot_broken_through_continuation | 2022 | 3516 | 6.3% | 0.775 | 0.937 | 0.937 | 352 | 18.2% |
| at_fire | low | label.strict.next_60m.pivot_broken_through_continuation | 2023 | 3422 | 5.1% | 0.819 | 0.949 | 0.949 | 343 | 20.1% |
| at_fire | low | label.strict.next_60m.pivot_broken_through_continuation | 2024 | 3447 | 5.7% | 0.807 | 0.943 | 0.943 | 345 | 22.0% |
| at_fire | low | label.strict.next_60m.pivot_broken_through_continuation | 2025 | 3470 | 4.7% | 0.778 | 0.953 | 0.953 | 347 | 14.1% |
| at_fire | low | label.strict.next_60m.pivot_failed_immediately | 2020 | 3442 | 5.7% | 0.739 | 0.943 | 0.943 | 345 | 15.1% |
| at_fire | low | label.strict.next_60m.pivot_failed_immediately | 2021 | 3454 | 5.4% | 0.784 | 0.946 | 0.946 | 346 | 18.5% |
| at_fire | low | label.strict.next_60m.pivot_failed_immediately | 2022 | 3516 | 7.1% | 0.775 | 0.929 | 0.929 | 352 | 22.7% |
| at_fire | low | label.strict.next_60m.pivot_failed_immediately | 2023 | 3422 | 6.6% | 0.796 | 0.934 | 0.934 | 343 | 24.5% |
| at_fire | low | label.strict.next_60m.pivot_failed_immediately | 2024 | 3447 | 6.3% | 0.793 | 0.936 | 0.937 | 345 | 21.7% |
| at_fire | low | label.strict.next_60m.pivot_failed_immediately | 2025 | 3470 | 5.5% | 0.764 | 0.941 | 0.945 | 347 | 15.9% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
