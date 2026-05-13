# ML snapshot walk-forward validation

_Generated `2026-05-12T14:55:14.530533+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshot_leaderboard.parquet`
- Event type: `all`
- Candidates: `6`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_walk_forward_summary_base.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_walk_forward_summary_base.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_walk_forward_folds_base.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_walk_forward_folds_base.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 42 |
| schema_label_columns | 31 |
| folds_attempted | 36 |
| folds_ok | 36 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.ob_confirmation.did_confirm | 6 | 28718 | 0.892 | 0.897 | 0.859 | 0.018 | 100.0% | 100.0% | 3.6% |
| at_fire | high | label.ob_confirmation.did_confirm | 6 | 15564 | 0.889 | 0.890 | 0.868 | 0.017 | 99.9% | 99.6% | 4.2% |
| at_fire | low | label.ob_confirmation.did_confirm | 6 | 13154 | 0.879 | 0.898 | 0.837 | 0.029 | 100.0% | 100.0% | 2.7% |
| at_fire | low | label.swept_level_recovery.level_recovered | 6 | 13154 | 0.789 | 0.783 | 0.774 | 0.016 | 96.2% | 93.2% | 20.2% |
| at_fire | all | label.swept_level_recovery.level_recovered | 6 | 28718 | 0.786 | 0.799 | 0.749 | 0.020 | 95.0% | 92.6% | 24.5% |
| at_fire | high | label.swept_level_recovery.level_recovered | 6 | 15564 | 0.773 | 0.785 | 0.699 | 0.034 | 92.3% | 90.9% | 26.0% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.ob_confirmation.did_confirm | 2020 | 4634 | 96.7% | 0.859 | 0.964 | 0.967 | 464 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2021 | 4867 | 96.5% | 0.899 | 0.967 | 0.965 | 487 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2022 | 4842 | 97.0% | 0.896 | 0.970 | 0.970 | 485 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2023 | 4812 | 96.1% | 0.912 | 0.964 | 0.961 | 482 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2024 | 4806 | 96.0% | 0.881 | 0.961 | 0.960 | 481 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2025 | 4757 | 96.1% | 0.907 | 0.962 | 0.961 | 476 | 100.0% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2020 | 4634 | 70.7% | 0.749 | 0.714 | 0.707 | 464 | 97.2% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2021 | 4867 | 71.2% | 0.800 | 0.771 | 0.712 | 487 | 95.5% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2022 | 4842 | 71.6% | 0.768 | 0.765 | 0.716 | 485 | 92.6% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2023 | 4812 | 69.1% | 0.799 | 0.768 | 0.691 | 482 | 94.0% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2024 | 4806 | 69.9% | 0.800 | 0.763 | 0.699 | 481 | 95.4% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2025 | 4757 | 70.9% | 0.801 | 0.769 | 0.709 | 476 | 95.6% |
| at_fire | high | label.ob_confirmation.did_confirm | 2020 | 2624 | 96.6% | 0.872 | 0.965 | 0.966 | 263 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2021 | 2755 | 95.6% | 0.885 | 0.959 | 0.956 | 276 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2022 | 2337 | 96.7% | 0.920 | 0.967 | 0.967 | 234 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2023 | 2624 | 94.5% | 0.896 | 0.949 | 0.945 | 263 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2024 | 2635 | 95.4% | 0.868 | 0.955 | 0.954 | 264 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2025 | 2589 | 95.4% | 0.895 | 0.958 | 0.954 | 259 | 99.6% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2020 | 2624 | 66.6% | 0.699 | 0.668 | 0.666 | 263 | 90.9% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2021 | 2755 | 63.8% | 0.788 | 0.726 | 0.638 | 276 | 90.9% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2022 | 2337 | 75.1% | 0.781 | 0.774 | 0.751 | 234 | 93.2% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2023 | 2624 | 62.5% | 0.788 | 0.724 | 0.625 | 263 | 93.2% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2024 | 2635 | 64.4% | 0.801 | 0.699 | 0.644 | 264 | 92.4% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2025 | 2589 | 65.9% | 0.783 | 0.732 | 0.659 | 259 | 93.4% |
| at_fire | low | label.ob_confirmation.did_confirm | 2020 | 2010 | 96.7% | 0.841 | 0.967 | 0.967 | 201 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2021 | 2112 | 97.7% | 0.900 | 0.977 | 0.977 | 212 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2022 | 2505 | 97.3% | 0.837 | 0.973 | 0.973 | 251 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2023 | 2188 | 98.1% | 0.901 | 0.981 | 0.981 | 219 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2024 | 2171 | 96.9% | 0.895 | 0.969 | 0.969 | 218 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2025 | 2168 | 97.0% | 0.902 | 0.970 | 0.970 | 217 | 100.0% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2020 | 2010 | 76.1% | 0.775 | 0.753 | 0.761 | 201 | 99.5% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2021 | 2112 | 80.7% | 0.776 | 0.818 | 0.807 | 212 | 97.2% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2022 | 2505 | 68.4% | 0.774 | 0.739 | 0.684 | 251 | 93.2% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2023 | 2188 | 77.0% | 0.789 | 0.807 | 0.770 | 219 | 94.1% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2024 | 2171 | 76.5% | 0.813 | 0.817 | 0.765 | 218 | 95.9% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2025 | 2168 | 77.0% | 0.805 | 0.809 | 0.770 | 217 | 97.2% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
