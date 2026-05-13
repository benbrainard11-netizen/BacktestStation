# ML snapshot walk-forward validation

_Generated `2026-05-12T21:54:19.277058+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots_xctx_fvggeom.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots_xctx_fvggeom.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshot_leaderboard_xctx_fvggeom.parquet`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_walk_forward_fvggeom_summary.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_walk_forward_fvggeom_summary.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_walk_forward_fvggeom_folds.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_walk_forward_fvggeom_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 1085 |
| schema_label_columns | 31 |
| folds_attempted | 63 |
| folds_ok | 63 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | low | label.ob_confirmation.did_confirm | 7 | 13461 | 0.872 | 0.872 | 0.825 | 0.028 | 100.0% | 100.0% | 3.2% |
| at_fire | all | label.ob_confirmation.did_confirm | 7 | 29301 | 0.865 | 0.883 | 0.708 | 0.066 | 99.5% | 96.6% | 3.7% |
| at_fire | high | label.ob_confirmation.did_confirm | 7 | 15840 | 0.848 | 0.879 | 0.594 | 0.105 | 99.0% | 92.9% | 4.1% |
| at_fire | all | label.swept_level_recovery.level_recovered | 7 | 29301 | 0.787 | 0.804 | 0.739 | 0.025 | 94.0% | 88.1% | 23.3% |
| at_fire | high | label.swept_level_recovery.level_recovered | 7 | 15840 | 0.782 | 0.788 | 0.723 | 0.026 | 93.0% | 91.6% | 26.1% |
| at_fire | low | label.swept_level_recovery.level_recovered | 7 | 13461 | 0.780 | 0.800 | 0.673 | 0.044 | 96.0% | 93.2% | 20.5% |
| at_fire | all | label.forward_continuation.continued | 7 | 29301 | 0.669 | 0.665 | 0.645 | 0.021 | 97.1% | 95.9% | 6.3% |
| at_fire | high | label.forward_continuation.continued | 7 | 15840 | 0.669 | 0.673 | 0.603 | 0.038 | 97.4% | 95.8% | 4.8% |
| at_fire | low | label.forward_continuation.continued | 7 | 13461 | 0.642 | 0.668 | 0.532 | 0.054 | 95.0% | 88.1% | 6.3% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.forward_continuation.continued | 2020 | 4634 | 88.5% | 0.649 | 0.885 | 0.885 | 464 | 97.0% |
| at_fire | all | label.forward_continuation.continued | 2021 | 4867 | 91.0% | 0.660 | 0.910 | 0.910 | 487 | 95.9% |
| at_fire | all | label.forward_continuation.continued | 2022 | 4842 | 92.5% | 0.645 | 0.924 | 0.925 | 485 | 97.5% |
| at_fire | all | label.forward_continuation.continued | 2023 | 4812 | 92.7% | 0.669 | 0.927 | 0.927 | 482 | 97.3% |
| at_fire | all | label.forward_continuation.continued | 2024 | 4806 | 92.2% | 0.710 | 0.922 | 0.922 | 481 | 98.8% |
| at_fire | all | label.forward_continuation.continued | 2025 | 4757 | 90.3% | 0.687 | 0.903 | 0.903 | 476 | 96.4% |
| at_fire | all | label.forward_continuation.continued | 2026 | 583 | 88.5% | 0.665 | 0.885 | 0.885 | 59 | 96.6% |
| at_fire | all | label.ob_confirmation.did_confirm | 2020 | 4634 | 96.7% | 0.858 | 0.967 | 0.967 | 464 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2021 | 4867 | 96.5% | 0.899 | 0.966 | 0.965 | 487 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2022 | 4842 | 97.0% | 0.883 | 0.970 | 0.970 | 485 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2023 | 4812 | 96.1% | 0.915 | 0.962 | 0.961 | 482 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2024 | 4806 | 96.0% | 0.881 | 0.960 | 0.960 | 481 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2025 | 4757 | 96.1% | 0.910 | 0.962 | 0.961 | 476 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2026 | 583 | 91.9% | 0.708 | 0.919 | 0.919 | 59 | 96.6% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2020 | 4634 | 70.7% | 0.765 | 0.730 | 0.707 | 464 | 94.4% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2021 | 4867 | 71.2% | 0.804 | 0.766 | 0.712 | 487 | 96.1% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2022 | 4842 | 71.6% | 0.778 | 0.767 | 0.716 | 485 | 93.0% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2023 | 4812 | 69.1% | 0.804 | 0.767 | 0.691 | 482 | 94.6% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2024 | 4806 | 69.9% | 0.813 | 0.772 | 0.699 | 481 | 95.4% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2025 | 4757 | 70.9% | 0.807 | 0.773 | 0.709 | 476 | 96.4% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2026 | 583 | 71.4% | 0.739 | 0.722 | 0.714 | 59 | 88.1% |
| at_fire | high | label.forward_continuation.continued | 2020 | 2624 | 92.4% | 0.603 | 0.924 | 0.924 | 263 | 95.8% |
| at_fire | high | label.forward_continuation.continued | 2021 | 2755 | 92.7% | 0.631 | 0.927 | 0.927 | 276 | 96.7% |
| at_fire | high | label.forward_continuation.continued | 2022 | 2337 | 91.6% | 0.668 | 0.917 | 0.916 | 234 | 97.4% |
| at_fire | high | label.forward_continuation.continued | 2023 | 2624 | 92.8% | 0.673 | 0.928 | 0.928 | 263 | 96.6% |
| at_fire | high | label.forward_continuation.continued | 2024 | 2635 | 95.1% | 0.702 | 0.951 | 0.951 | 264 | 99.2% |
| at_fire | high | label.forward_continuation.continued | 2025 | 2589 | 93.0% | 0.723 | 0.932 | 0.930 | 259 | 99.2% |
| at_fire | high | label.forward_continuation.continued | 2026 | 276 | 90.2% | 0.685 | 0.899 | 0.902 | 28 | 96.4% |
| at_fire | high | label.ob_confirmation.did_confirm | 2020 | 2624 | 96.6% | 0.871 | 0.966 | 0.966 | 263 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2021 | 2755 | 95.6% | 0.879 | 0.958 | 0.956 | 276 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2022 | 2337 | 96.7% | 0.922 | 0.967 | 0.967 | 234 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2023 | 2624 | 94.5% | 0.903 | 0.946 | 0.945 | 263 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2024 | 2635 | 95.4% | 0.861 | 0.954 | 0.954 | 264 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2025 | 2589 | 95.4% | 0.904 | 0.955 | 0.954 | 259 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2026 | 276 | 89.9% | 0.594 | 0.899 | 0.899 | 28 | 92.9% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2020 | 2624 | 66.6% | 0.723 | 0.703 | 0.666 | 263 | 92.0% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2021 | 2755 | 63.8% | 0.790 | 0.736 | 0.638 | 276 | 95.3% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2022 | 2337 | 75.1% | 0.776 | 0.784 | 0.751 | 234 | 93.2% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2023 | 2624 | 62.5% | 0.787 | 0.727 | 0.625 | 263 | 91.6% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2024 | 2635 | 64.4% | 0.800 | 0.737 | 0.644 | 264 | 92.4% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2025 | 2589 | 65.9% | 0.788 | 0.746 | 0.659 | 259 | 93.4% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2026 | 276 | 69.6% | 0.807 | 0.793 | 0.696 | 28 | 92.9% |
| at_fire | low | label.forward_continuation.continued | 2020 | 2010 | 83.3% | 0.620 | 0.833 | 0.833 | 201 | 88.1% |
| at_fire | low | label.forward_continuation.continued | 2021 | 2112 | 88.6% | 0.684 | 0.888 | 0.886 | 212 | 97.2% |
| at_fire | low | label.forward_continuation.continued | 2022 | 2505 | 93.3% | 0.668 | 0.928 | 0.933 | 251 | 96.8% |
| at_fire | low | label.forward_continuation.continued | 2023 | 2188 | 92.7% | 0.701 | 0.926 | 0.927 | 219 | 96.8% |
| at_fire | low | label.forward_continuation.continued | 2024 | 2171 | 88.7% | 0.613 | 0.887 | 0.887 | 218 | 90.4% |
| at_fire | low | label.forward_continuation.continued | 2025 | 2168 | 87.1% | 0.674 | 0.871 | 0.871 | 217 | 95.9% |
| at_fire | low | label.forward_continuation.continued | 2026 | 307 | 87.0% | 0.532 | 0.870 | 0.870 | 31 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2020 | 2010 | 96.7% | 0.849 | 0.967 | 0.967 | 201 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2021 | 2112 | 97.7% | 0.872 | 0.977 | 0.977 | 212 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2022 | 2505 | 97.3% | 0.825 | 0.973 | 0.973 | 251 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2023 | 2188 | 98.1% | 0.891 | 0.981 | 0.981 | 219 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2024 | 2171 | 96.9% | 0.883 | 0.969 | 0.969 | 218 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2025 | 2168 | 97.0% | 0.917 | 0.970 | 0.970 | 217 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2026 | 307 | 93.8% | 0.864 | 0.938 | 0.938 | 31 | 100.0% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2020 | 2010 | 76.1% | 0.799 | 0.775 | 0.761 | 201 | 98.0% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2021 | 2112 | 80.7% | 0.804 | 0.824 | 0.807 | 212 | 97.2% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2022 | 2505 | 68.4% | 0.781 | 0.758 | 0.684 | 251 | 93.2% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2023 | 2188 | 77.0% | 0.800 | 0.805 | 0.770 | 219 | 97.3% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2024 | 2171 | 76.5% | 0.803 | 0.809 | 0.765 | 218 | 96.3% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2025 | 2168 | 77.0% | 0.800 | 0.806 | 0.770 | 217 | 96.3% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2026 | 307 | 73.0% | 0.673 | 0.700 | 0.730 | 31 | 93.5% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
