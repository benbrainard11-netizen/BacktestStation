# ML snapshot walk-forward validation

_Generated `2026-05-13T21:49:14.063028+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots_xctx_fvggeom.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots_xctx_fvggeom.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshot_leaderboard_xctx_fvggeom.parquet`
- Event type: `all`
- Candidates: `9`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\AppData\Local\Temp\sweep_walk_forward_fvggeom_summary_itr.csv | candidate summary CSV |
| C:\Users\benbr\AppData\Local\Temp\sweep_walk_forward_fvggeom_summary_itr.parquet | candidate summary parquet |
| C:\Users\benbr\AppData\Local\Temp\sweep_walk_forward_fvggeom_folds_itr.csv | per-fold CSV |
| C:\Users\benbr\AppData\Local\Temp\sweep_walk_forward_fvggeom_folds_itr.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 1253 |
| schema_label_columns | 31 |
| folds_attempted | 54 |
| folds_ok | 54 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.ob_confirmation.did_confirm | 6 | 28718 | 0.893 | 0.896 | 0.862 | 0.018 | 100.0% | 100.0% | 3.6% |
| at_fire | high | label.ob_confirmation.did_confirm | 6 | 15564 | 0.888 | 0.892 | 0.852 | 0.026 | 100.0% | 100.0% | 4.3% |
| at_fire | low | label.ob_confirmation.did_confirm | 6 | 13154 | 0.868 | 0.862 | 0.809 | 0.039 | 99.9% | 99.5% | 2.6% |
| at_fire | low | label.swept_level_recovery.level_recovered | 6 | 13154 | 0.798 | 0.800 | 0.779 | 0.009 | 96.1% | 92.8% | 20.1% |
| at_fire | all | label.swept_level_recovery.level_recovered | 6 | 28718 | 0.794 | 0.804 | 0.758 | 0.019 | 95.3% | 93.4% | 24.8% |
| at_fire | high | label.swept_level_recovery.level_recovered | 6 | 15564 | 0.776 | 0.788 | 0.722 | 0.026 | 93.0% | 91.0% | 26.6% |
| at_fire | all | label.forward_continuation.continued | 6 | 28718 | 0.666 | 0.667 | 0.621 | 0.030 | 96.4% | 95.3% | 5.2% |
| at_fire | high | label.forward_continuation.continued | 6 | 15564 | 0.665 | 0.661 | 0.596 | 0.047 | 97.9% | 95.8% | 4.9% |
| at_fire | low | label.forward_continuation.continued | 6 | 13154 | 0.655 | 0.662 | 0.608 | 0.024 | 94.8% | 91.0% | 5.8% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.forward_continuation.continued | 2020 | 4634 | 88.5% | 0.636 | 0.885 | 0.885 | 464 | 95.9% |
| at_fire | all | label.forward_continuation.continued | 2021 | 4867 | 91.0% | 0.668 | 0.910 | 0.910 | 487 | 95.3% |
| at_fire | all | label.forward_continuation.continued | 2022 | 4842 | 92.5% | 0.621 | 0.925 | 0.925 | 485 | 95.5% |
| at_fire | all | label.forward_continuation.continued | 2023 | 4812 | 92.7% | 0.667 | 0.927 | 0.927 | 482 | 95.9% |
| at_fire | all | label.forward_continuation.continued | 2024 | 4806 | 92.2% | 0.702 | 0.922 | 0.922 | 481 | 97.7% |
| at_fire | all | label.forward_continuation.continued | 2025 | 4757 | 90.3% | 0.702 | 0.903 | 0.903 | 476 | 97.9% |
| at_fire | all | label.ob_confirmation.did_confirm | 2020 | 4634 | 96.7% | 0.862 | 0.967 | 0.967 | 464 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2021 | 4867 | 96.5% | 0.903 | 0.967 | 0.965 | 487 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2022 | 4842 | 97.0% | 0.890 | 0.971 | 0.970 | 485 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2023 | 4812 | 96.1% | 0.910 | 0.962 | 0.961 | 482 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2024 | 4806 | 96.0% | 0.882 | 0.959 | 0.960 | 481 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2025 | 4757 | 96.1% | 0.912 | 0.962 | 0.961 | 476 | 100.0% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2020 | 4634 | 70.7% | 0.758 | 0.730 | 0.707 | 464 | 95.5% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2021 | 4867 | 71.2% | 0.804 | 0.769 | 0.712 | 487 | 95.9% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2022 | 4842 | 71.6% | 0.777 | 0.773 | 0.716 | 485 | 93.4% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2023 | 4812 | 69.1% | 0.804 | 0.769 | 0.691 | 482 | 94.8% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2024 | 4806 | 69.9% | 0.813 | 0.771 | 0.699 | 481 | 96.3% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2025 | 4757 | 70.9% | 0.806 | 0.771 | 0.709 | 476 | 96.2% |
| at_fire | high | label.forward_continuation.continued | 2020 | 2624 | 92.4% | 0.596 | 0.924 | 0.924 | 263 | 95.8% |
| at_fire | high | label.forward_continuation.continued | 2021 | 2755 | 92.7% | 0.626 | 0.927 | 0.927 | 276 | 98.6% |
| at_fire | high | label.forward_continuation.continued | 2022 | 2337 | 91.6% | 0.667 | 0.917 | 0.916 | 234 | 97.4% |
| at_fire | high | label.forward_continuation.continued | 2023 | 2624 | 92.8% | 0.654 | 0.928 | 0.928 | 263 | 97.3% |
| at_fire | high | label.forward_continuation.continued | 2024 | 2635 | 95.1% | 0.708 | 0.951 | 0.951 | 264 | 98.9% |
| at_fire | high | label.forward_continuation.continued | 2025 | 2589 | 93.0% | 0.737 | 0.933 | 0.930 | 259 | 99.2% |
| at_fire | high | label.ob_confirmation.did_confirm | 2020 | 2624 | 96.6% | 0.852 | 0.966 | 0.966 | 263 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2021 | 2755 | 95.6% | 0.881 | 0.958 | 0.956 | 276 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2022 | 2337 | 96.7% | 0.926 | 0.967 | 0.967 | 234 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2023 | 2624 | 94.5% | 0.904 | 0.946 | 0.945 | 263 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2024 | 2635 | 95.4% | 0.862 | 0.953 | 0.954 | 264 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2025 | 2589 | 95.4% | 0.902 | 0.956 | 0.954 | 259 | 100.0% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2020 | 2624 | 66.6% | 0.722 | 0.704 | 0.666 | 263 | 93.2% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2021 | 2755 | 63.8% | 0.787 | 0.732 | 0.638 | 276 | 94.6% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2022 | 2337 | 75.1% | 0.768 | 0.781 | 0.751 | 234 | 91.0% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2023 | 2624 | 62.5% | 0.789 | 0.732 | 0.625 | 263 | 92.0% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2024 | 2635 | 64.4% | 0.802 | 0.734 | 0.644 | 264 | 92.0% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2025 | 2589 | 65.9% | 0.788 | 0.742 | 0.659 | 259 | 95.0% |
| at_fire | low | label.forward_continuation.continued | 2020 | 2010 | 83.3% | 0.608 | 0.833 | 0.833 | 201 | 91.0% |
| at_fire | low | label.forward_continuation.continued | 2021 | 2112 | 88.6% | 0.666 | 0.886 | 0.886 | 212 | 97.2% |
| at_fire | low | label.forward_continuation.continued | 2022 | 2505 | 93.3% | 0.659 | 0.931 | 0.933 | 251 | 96.0% |
| at_fire | low | label.forward_continuation.continued | 2023 | 2188 | 92.7% | 0.684 | 0.927 | 0.927 | 219 | 96.8% |
| at_fire | low | label.forward_continuation.continued | 2024 | 2171 | 88.7% | 0.648 | 0.887 | 0.887 | 218 | 94.5% |
| at_fire | low | label.forward_continuation.continued | 2025 | 2168 | 87.1% | 0.665 | 0.871 | 0.871 | 217 | 93.1% |
| at_fire | low | label.ob_confirmation.did_confirm | 2020 | 2010 | 96.7% | 0.844 | 0.967 | 0.967 | 201 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2021 | 2112 | 97.7% | 0.849 | 0.977 | 0.977 | 212 | 99.5% |
| at_fire | low | label.ob_confirmation.did_confirm | 2022 | 2505 | 97.3% | 0.809 | 0.973 | 0.973 | 251 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2023 | 2188 | 98.1% | 0.908 | 0.981 | 0.981 | 219 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2024 | 2171 | 96.9% | 0.874 | 0.969 | 0.969 | 218 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2025 | 2168 | 97.0% | 0.925 | 0.970 | 0.970 | 217 | 100.0% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2020 | 2010 | 76.1% | 0.798 | 0.782 | 0.761 | 201 | 98.0% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2021 | 2112 | 80.7% | 0.803 | 0.818 | 0.807 | 212 | 95.8% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2022 | 2505 | 68.4% | 0.779 | 0.749 | 0.684 | 251 | 92.8% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2023 | 2188 | 77.0% | 0.796 | 0.806 | 0.770 | 219 | 95.4% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2024 | 2171 | 76.5% | 0.807 | 0.813 | 0.765 | 218 | 96.8% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2025 | 2168 | 77.0% | 0.804 | 0.808 | 0.770 | 217 | 97.7% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
