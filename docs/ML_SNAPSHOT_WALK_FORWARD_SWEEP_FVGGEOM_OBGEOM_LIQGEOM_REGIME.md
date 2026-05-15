# ML snapshot walk-forward validation

_Generated `2026-05-15T01:59:29.603561+00:00`._

## Setup

- Matrix: `data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- Schema: `data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- Leaderboard source: `data\ml\anchors\sweep_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
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
| data\ml\anchors\sweep_walk_forward_fvggeom_obgeom_liqgeom_regime_summary.csv | candidate summary CSV |
| data\ml\anchors\sweep_walk_forward_fvggeom_obgeom_liqgeom_regime_summary.parquet | candidate summary parquet |
| data\ml\anchors\sweep_walk_forward_fvggeom_obgeom_liqgeom_regime_folds.csv | per-fold CSV |
| data\ml\anchors\sweep_walk_forward_fvggeom_obgeom_liqgeom_regime_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 3131 |
| schema_label_columns | 95 |
| folds_attempted | 48 |
| folds_ok | 48 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | low | label.manipulation_range_reaction.range_expanded_2x_manipulation | 6 | 13154 | 0.907 | 0.918 | 0.861 | 0.030 | 99.8% | 99.1% | 3.9% |
| at_fire | all | label.manipulation_range_reaction.range_expanded_2x_manipulation | 6 | 28718 | 0.903 | 0.923 | 0.830 | 0.038 | 99.7% | 99.1% | 3.1% |
| at_fire | all | label.ob_confirmation.did_confirm | 6 | 28718 | 0.896 | 0.899 | 0.856 | 0.019 | 100.0% | 100.0% | 2.7% |
| at_fire | high | label.ob_confirmation.did_confirm | 6 | 15564 | 0.894 | 0.886 | 0.873 | 0.022 | 99.9% | 99.2% | 2.6% |
| at_fire | high | label.manipulation_range_reaction.range_expanded_2x_manipulation | 6 | 15564 | 0.887 | 0.901 | 0.800 | 0.042 | 99.8% | 98.9% | 2.8% |
| at_fire | low | label.ob_confirmation.did_confirm | 6 | 13154 | 0.863 | 0.864 | 0.782 | 0.048 | 100.0% | 100.0% | 2.7% |
| at_fire | high | label.swept_reference_reaction.first_bar_down_then_final_up | 6 | 15564 | 0.823 | 0.827 | 0.803 | 0.010 | 33.7% | 27.8% | 22.4% |
| at_fire | high | label.swept_level_recovery.level_recovered | 6 | 15564 | 0.792 | 0.797 | 0.747 | 0.022 | 95.2% | 94.0% | 27.5% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2020 | 4634 | 97.3% | 0.830 | 0.974 | 0.973 | 464 | 99.1% |
| at_fire | all | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2021 | 4867 | 96.9% | 0.931 | 0.968 | 0.969 | 487 | 100.0% |
| at_fire | all | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2022 | 4842 | 96.8% | 0.922 | 0.968 | 0.968 | 485 | 100.0% |
| at_fire | all | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2023 | 4812 | 96.0% | 0.924 | 0.962 | 0.960 | 482 | 100.0% |
| at_fire | all | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2024 | 4806 | 96.9% | 0.934 | 0.968 | 0.969 | 481 | 100.0% |
| at_fire | all | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2025 | 4757 | 95.5% | 0.877 | 0.955 | 0.955 | 476 | 99.2% |
| at_fire | all | label.ob_confirmation.did_confirm | 2020 | 4634 | 97.5% | 0.856 | 0.975 | 0.975 | 464 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2021 | 4867 | 97.3% | 0.903 | 0.973 | 0.973 | 487 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2022 | 4842 | 97.5% | 0.893 | 0.975 | 0.975 | 485 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2023 | 4812 | 97.1% | 0.917 | 0.971 | 0.971 | 482 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2024 | 4806 | 97.1% | 0.895 | 0.970 | 0.971 | 481 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2025 | 4757 | 97.1% | 0.909 | 0.971 | 0.971 | 476 | 100.0% |
| at_fire | high | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2020 | 2624 | 98.4% | 0.800 | 0.984 | 0.984 | 263 | 98.9% |
| at_fire | high | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2021 | 2755 | 97.2% | 0.912 | 0.972 | 0.972 | 276 | 100.0% |
| at_fire | high | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2022 | 2337 | 96.9% | 0.892 | 0.969 | 0.969 | 234 | 100.0% |
| at_fire | high | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2023 | 2624 | 96.1% | 0.909 | 0.961 | 0.961 | 263 | 100.0% |
| at_fire | high | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2024 | 2635 | 97.4% | 0.930 | 0.974 | 0.974 | 264 | 100.0% |
| at_fire | high | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2025 | 2589 | 96.3% | 0.879 | 0.964 | 0.963 | 259 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2020 | 2624 | 98.2% | 0.873 | 0.982 | 0.982 | 263 | 99.2% |
| at_fire | high | label.ob_confirmation.did_confirm | 2021 | 2755 | 97.0% | 0.890 | 0.970 | 0.970 | 276 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2022 | 2337 | 97.6% | 0.926 | 0.976 | 0.976 | 234 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2023 | 2624 | 96.3% | 0.920 | 0.962 | 0.963 | 263 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2024 | 2635 | 97.2% | 0.882 | 0.971 | 0.972 | 264 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2025 | 2589 | 97.1% | 0.873 | 0.972 | 0.971 | 259 | 100.0% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2020 | 2624 | 67.9% | 0.747 | 0.724 | 0.679 | 263 | 94.7% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2021 | 2755 | 65.5% | 0.801 | 0.739 | 0.655 | 276 | 96.4% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2022 | 2337 | 75.8% | 0.792 | 0.798 | 0.758 | 234 | 94.0% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2023 | 2624 | 63.7% | 0.794 | 0.731 | 0.637 | 263 | 95.8% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2024 | 2635 | 65.6% | 0.817 | 0.741 | 0.656 | 264 | 95.5% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2025 | 2589 | 67.4% | 0.801 | 0.756 | 0.674 | 259 | 94.6% |
| at_fire | high | label.swept_reference_reaction.first_bar_down_then_final_up | 2020 | 2624 | 11.1% | 0.816 | 0.891 | 0.889 | 263 | 32.7% |
| at_fire | high | label.swept_reference_reaction.first_bar_down_then_final_up | 2021 | 2755 | 11.9% | 0.828 | 0.881 | 0.881 | 276 | 35.1% |
| at_fire | high | label.swept_reference_reaction.first_bar_down_then_final_up | 2022 | 2337 | 10.2% | 0.803 | 0.891 | 0.898 | 234 | 27.8% |
| at_fire | high | label.swept_reference_reaction.first_bar_down_then_final_up | 2023 | 2624 | 10.5% | 0.833 | 0.895 | 0.895 | 263 | 32.7% |
| at_fire | high | label.swept_reference_reaction.first_bar_down_then_final_up | 2024 | 2635 | 11.7% | 0.832 | 0.880 | 0.883 | 264 | 34.5% |
| at_fire | high | label.swept_reference_reaction.first_bar_down_then_final_up | 2025 | 2589 | 12.5% | 0.827 | 0.877 | 0.875 | 259 | 39.4% |
| at_fire | low | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2020 | 2010 | 96.0% | 0.872 | 0.961 | 0.960 | 201 | 100.0% |
| at_fire | low | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2021 | 2112 | 96.4% | 0.939 | 0.965 | 0.964 | 212 | 100.0% |
| at_fire | low | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2022 | 2505 | 96.7% | 0.920 | 0.966 | 0.967 | 251 | 100.0% |
| at_fire | low | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2023 | 2188 | 95.9% | 0.937 | 0.962 | 0.959 | 219 | 100.0% |
| at_fire | low | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2024 | 2171 | 96.3% | 0.915 | 0.963 | 0.963 | 218 | 100.0% |
| at_fire | low | label.manipulation_range_reaction.range_expanded_2x_manipulation | 2025 | 2168 | 94.5% | 0.861 | 0.944 | 0.945 | 217 | 99.1% |
| at_fire | low | label.ob_confirmation.did_confirm | 2020 | 2010 | 96.7% | 0.782 | 0.967 | 0.967 | 201 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2021 | 2112 | 97.7% | 0.845 | 0.977 | 0.977 | 212 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2022 | 2505 | 97.3% | 0.839 | 0.973 | 0.973 | 251 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2023 | 2188 | 98.1% | 0.899 | 0.981 | 0.981 | 219 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2024 | 2171 | 96.9% | 0.883 | 0.968 | 0.969 | 218 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2025 | 2168 | 97.0% | 0.931 | 0.970 | 0.970 | 217 | 100.0% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
