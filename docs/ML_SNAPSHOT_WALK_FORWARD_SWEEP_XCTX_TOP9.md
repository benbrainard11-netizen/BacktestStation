# ML snapshot walk-forward validation

_Generated `2026-05-12T21:59:23.595260+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots_xctx.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshot_leaderboard_xctx.parquet`
- Event type: `all`
- Candidates: `9`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025, 2026`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_walk_forward_xctx_top9_summary.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_walk_forward_xctx_top9_summary.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_walk_forward_xctx_top9_folds.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_walk_forward_xctx_top9_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 634 |
| schema_label_columns | 31 |
| folds_attempted | 63 |
| folds_ok | 63 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | low | label.ob_confirmation.did_confirm | 7 | 13461 | 0.873 | 0.888 | 0.809 | 0.038 | 100.0% | 100.0% | 3.2% |
| at_fire | all | label.ob_confirmation.did_confirm | 7 | 29301 | 0.858 | 0.885 | 0.670 | 0.079 | 98.8% | 91.5% | 3.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 7 | 15840 | 0.844 | 0.882 | 0.559 | 0.118 | 99.5% | 96.4% | 4.6% |
| at_fire | all | label.swept_level_recovery.level_recovered | 7 | 29301 | 0.778 | 0.796 | 0.724 | 0.028 | 93.1% | 86.4% | 22.4% |
| at_fire | high | label.swept_level_recovery.level_recovered | 7 | 15840 | 0.769 | 0.782 | 0.709 | 0.027 | 90.1% | 82.1% | 23.3% |
| at_fire | low | label.swept_level_recovery.level_recovered | 7 | 13461 | 0.769 | 0.781 | 0.673 | 0.040 | 95.4% | 92.0% | 19.9% |
| at_fire | all | label.forward_continuation.continued | 7 | 29301 | 0.635 | 0.644 | 0.587 | 0.036 | 95.1% | 91.5% | 4.3% |
| at_fire | high | label.forward_continuation.continued | 7 | 15840 | 0.630 | 0.626 | 0.546 | 0.055 | 95.5% | 82.1% | 3.0% |
| at_fire | low | label.forward_continuation.continued | 7 | 13461 | 0.609 | 0.619 | 0.538 | 0.033 | 91.9% | 83.1% | 3.3% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.forward_continuation.continued | 2020 | 4634 | 88.5% | 0.587 | 0.885 | 0.885 | 464 | 91.8% |
| at_fire | all | label.forward_continuation.continued | 2021 | 4867 | 91.0% | 0.644 | 0.910 | 0.910 | 487 | 96.1% |
| at_fire | all | label.forward_continuation.continued | 2022 | 4842 | 92.5% | 0.595 | 0.925 | 0.925 | 485 | 95.7% |
| at_fire | all | label.forward_continuation.continued | 2023 | 4812 | 92.7% | 0.649 | 0.927 | 0.927 | 482 | 97.1% |
| at_fire | all | label.forward_continuation.continued | 2024 | 4806 | 92.2% | 0.677 | 0.922 | 0.922 | 481 | 96.7% |
| at_fire | all | label.forward_continuation.continued | 2025 | 4757 | 90.3% | 0.685 | 0.903 | 0.903 | 476 | 97.1% |
| at_fire | all | label.forward_continuation.continued | 2026 | 583 | 88.5% | 0.609 | 0.885 | 0.885 | 59 | 91.5% |
| at_fire | all | label.ob_confirmation.did_confirm | 2020 | 4634 | 96.7% | 0.851 | 0.966 | 0.967 | 464 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2021 | 4867 | 96.5% | 0.903 | 0.965 | 0.965 | 487 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2022 | 4842 | 97.0% | 0.885 | 0.970 | 0.970 | 485 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2023 | 4812 | 96.1% | 0.915 | 0.962 | 0.961 | 482 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2024 | 4806 | 96.0% | 0.878 | 0.960 | 0.960 | 481 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2025 | 4757 | 96.1% | 0.906 | 0.961 | 0.961 | 476 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2026 | 583 | 91.9% | 0.670 | 0.919 | 0.919 | 59 | 91.5% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2020 | 4634 | 70.7% | 0.753 | 0.726 | 0.707 | 464 | 94.8% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2021 | 4867 | 71.2% | 0.796 | 0.763 | 0.712 | 487 | 94.9% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2022 | 4842 | 71.6% | 0.771 | 0.765 | 0.716 | 485 | 92.0% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2023 | 4812 | 69.1% | 0.798 | 0.763 | 0.691 | 482 | 93.6% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2024 | 4806 | 69.9% | 0.808 | 0.770 | 0.699 | 481 | 94.4% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2025 | 4757 | 70.9% | 0.797 | 0.771 | 0.709 | 476 | 95.6% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2026 | 583 | 71.4% | 0.724 | 0.744 | 0.714 | 59 | 86.4% |
| at_fire | high | label.forward_continuation.continued | 2020 | 2624 | 92.4% | 0.579 | 0.924 | 0.924 | 263 | 96.2% |
| at_fire | high | label.forward_continuation.continued | 2021 | 2755 | 92.7% | 0.626 | 0.927 | 0.927 | 276 | 97.8% |
| at_fire | high | label.forward_continuation.continued | 2022 | 2337 | 91.6% | 0.607 | 0.916 | 0.916 | 234 | 98.3% |
| at_fire | high | label.forward_continuation.continued | 2023 | 2624 | 92.8% | 0.646 | 0.928 | 0.928 | 263 | 97.0% |
| at_fire | high | label.forward_continuation.continued | 2024 | 2635 | 95.1% | 0.696 | 0.951 | 0.951 | 264 | 98.1% |
| at_fire | high | label.forward_continuation.continued | 2025 | 2589 | 93.0% | 0.712 | 0.931 | 0.930 | 259 | 99.2% |
| at_fire | high | label.forward_continuation.continued | 2026 | 276 | 90.2% | 0.546 | 0.902 | 0.902 | 28 | 82.1% |
| at_fire | high | label.ob_confirmation.did_confirm | 2020 | 2624 | 96.6% | 0.872 | 0.967 | 0.966 | 263 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2021 | 2755 | 95.6% | 0.882 | 0.957 | 0.956 | 276 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2022 | 2337 | 96.7% | 0.932 | 0.967 | 0.967 | 234 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2023 | 2624 | 94.5% | 0.907 | 0.948 | 0.945 | 263 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2024 | 2635 | 95.4% | 0.864 | 0.954 | 0.954 | 264 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2025 | 2589 | 95.4% | 0.891 | 0.954 | 0.954 | 259 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2026 | 276 | 89.9% | 0.559 | 0.899 | 0.899 | 28 | 96.4% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2020 | 2624 | 66.6% | 0.709 | 0.696 | 0.666 | 263 | 88.6% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2021 | 2755 | 63.8% | 0.787 | 0.727 | 0.638 | 276 | 93.1% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2022 | 2337 | 75.1% | 0.756 | 0.772 | 0.751 | 234 | 90.6% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2023 | 2624 | 62.5% | 0.782 | 0.728 | 0.625 | 263 | 91.3% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2024 | 2635 | 64.4% | 0.793 | 0.728 | 0.644 | 264 | 91.3% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2025 | 2589 | 65.9% | 0.776 | 0.736 | 0.659 | 259 | 93.8% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2026 | 276 | 69.6% | 0.783 | 0.804 | 0.696 | 28 | 82.1% |
| at_fire | low | label.forward_continuation.continued | 2020 | 2010 | 83.3% | 0.538 | 0.833 | 0.833 | 201 | 83.1% |
| at_fire | low | label.forward_continuation.continued | 2021 | 2112 | 88.6% | 0.630 | 0.886 | 0.886 | 212 | 94.8% |
| at_fire | low | label.forward_continuation.continued | 2022 | 2505 | 93.3% | 0.629 | 0.929 | 0.933 | 251 | 98.4% |
| at_fire | low | label.forward_continuation.continued | 2023 | 2188 | 92.7% | 0.646 | 0.927 | 0.927 | 219 | 97.3% |
| at_fire | low | label.forward_continuation.continued | 2024 | 2171 | 88.7% | 0.592 | 0.887 | 0.887 | 218 | 92.2% |
| at_fire | low | label.forward_continuation.continued | 2025 | 2168 | 87.1% | 0.619 | 0.871 | 0.871 | 217 | 90.8% |
| at_fire | low | label.forward_continuation.continued | 2026 | 307 | 87.0% | 0.608 | 0.870 | 0.870 | 31 | 87.1% |
| at_fire | low | label.ob_confirmation.did_confirm | 2020 | 2010 | 96.7% | 0.843 | 0.967 | 0.967 | 201 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2021 | 2112 | 97.7% | 0.888 | 0.977 | 0.977 | 212 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2022 | 2505 | 97.3% | 0.809 | 0.973 | 0.973 | 251 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2023 | 2188 | 98.1% | 0.896 | 0.981 | 0.981 | 219 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2024 | 2171 | 96.9% | 0.894 | 0.969 | 0.969 | 218 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2025 | 2168 | 97.0% | 0.930 | 0.970 | 0.970 | 217 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2026 | 307 | 93.8% | 0.849 | 0.938 | 0.938 | 31 | 100.0% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2020 | 2010 | 76.1% | 0.776 | 0.774 | 0.761 | 201 | 99.5% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2021 | 2112 | 80.7% | 0.781 | 0.822 | 0.807 | 212 | 96.2% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2022 | 2505 | 68.4% | 0.778 | 0.743 | 0.684 | 251 | 92.0% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2023 | 2188 | 77.0% | 0.786 | 0.798 | 0.770 | 219 | 94.1% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2024 | 2171 | 76.5% | 0.791 | 0.802 | 0.765 | 218 | 95.9% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2025 | 2168 | 77.0% | 0.795 | 0.794 | 0.770 | 217 | 96.8% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2026 | 307 | 73.0% | 0.673 | 0.717 | 0.730 | 31 | 93.5% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
