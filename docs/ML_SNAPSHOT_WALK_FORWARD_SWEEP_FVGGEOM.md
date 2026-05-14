# ML snapshot walk-forward validation

_Generated `2026-05-14T09:47:57.580064+00:00`._

## Setup

- Matrix: `data\ml\anchors\sweep_snapshots_xctx_fvggeom.parquet`
- Schema: `data\ml\anchors\sweep_snapshots_xctx_fvggeom.schema.json`
- Leaderboard source: `data\ml\anchors\sweep_snapshot_leaderboard_xctx_fvggeom.parquet`
- Event type: `all`
- Candidates: `12`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\sweep_walk_forward_fvggeom_summary.csv | candidate summary CSV |
| data\ml\anchors\sweep_walk_forward_fvggeom_summary.parquet | candidate summary parquet |
| data\ml\anchors\sweep_walk_forward_fvggeom_folds.csv | per-fold CSV |
| data\ml\anchors\sweep_walk_forward_fvggeom_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 1305 |
| schema_label_columns | 95 |
| folds_attempted | 72 |
| folds_ok | 72 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | high | label.ob_confirmation.did_confirm | 6 | 15564 | 0.899 | 0.886 | 0.873 | 0.026 | 99.9% | 99.6% | 2.7% |
| at_fire | all | label.ob_confirmation.did_confirm | 6 | 28718 | 0.896 | 0.899 | 0.869 | 0.015 | 100.0% | 100.0% | 2.7% |
| at_fire | low | label.ob_confirmation.did_confirm | 6 | 13154 | 0.864 | 0.872 | 0.802 | 0.039 | 99.8% | 99.1% | 2.6% |
| at_fire | low | label.swept_level_recovery.level_recovered | 6 | 13154 | 0.797 | 0.797 | 0.785 | 0.008 | 96.5% | 93.6% | 19.0% |
| at_fire | all | label.swept_level_recovery.level_recovered | 6 | 28718 | 0.793 | 0.795 | 0.765 | 0.015 | 95.3% | 94.0% | 23.3% |
| at_fire | high | label.swept_level_recovery.level_recovered | 6 | 15564 | 0.772 | 0.779 | 0.724 | 0.024 | 93.4% | 91.9% | 25.7% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 6 | 15564 | 0.723 | 0.733 | 0.653 | 0.032 | 34.3% | 25.5% | 21.4% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 6 | 15564 | 0.721 | 0.733 | 0.650 | 0.034 | 95.1% | 93.5% | 8.1% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 6 | 13154 | 0.718 | 0.729 | 0.611 | 0.056 | 96.3% | 90.0% | 6.3% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 6 | 13154 | 0.714 | 0.726 | 0.616 | 0.052 | 30.8% | 22.4% | 20.9% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 6 | 28718 | 0.704 | 0.706 | 0.647 | 0.036 | 96.9% | 94.0% | 4.9% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 6 | 28718 | 0.703 | 0.711 | 0.634 | 0.040 | 24.0% | 17.9% | 16.0% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2020 | 4634 | 8.4% | 0.634 | 0.915 | 0.916 | 464 | 17.9% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2021 | 4867 | 6.9% | 0.713 | 0.931 | 0.931 | 487 | 23.6% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2022 | 4842 | 10.9% | 0.709 | 0.892 | 0.891 | 485 | 32.4% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2023 | 4812 | 7.4% | 0.672 | 0.926 | 0.926 | 482 | 20.1% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2024 | 4806 | 6.9% | 0.740 | 0.932 | 0.931 | 481 | 22.9% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2025 | 4757 | 7.5% | 0.750 | 0.925 | 0.925 | 476 | 27.1% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 2020 | 4634 | 91.5% | 0.647 | 0.914 | 0.915 | 464 | 96.6% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 2021 | 4867 | 93.0% | 0.719 | 0.930 | 0.930 | 487 | 97.3% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 2022 | 4842 | 89.1% | 0.694 | 0.891 | 0.891 | 485 | 94.0% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 2023 | 4812 | 92.6% | 0.673 | 0.926 | 0.926 | 482 | 97.3% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 2024 | 4806 | 93.1% | 0.743 | 0.931 | 0.931 | 481 | 97.7% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 2025 | 4757 | 92.5% | 0.747 | 0.925 | 0.925 | 476 | 98.5% |
| at_fire | all | label.ob_confirmation.did_confirm | 2020 | 4634 | 97.5% | 0.869 | 0.975 | 0.975 | 464 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2021 | 4867 | 97.3% | 0.905 | 0.973 | 0.973 | 487 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2022 | 4842 | 97.5% | 0.890 | 0.975 | 0.975 | 485 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2023 | 4812 | 97.1% | 0.914 | 0.971 | 0.971 | 482 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2024 | 4806 | 97.1% | 0.895 | 0.970 | 0.971 | 481 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2025 | 4757 | 97.1% | 0.904 | 0.971 | 0.971 | 476 | 100.0% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2020 | 4634 | 72.2% | 0.765 | 0.740 | 0.722 | 464 | 95.5% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2021 | 4867 | 72.7% | 0.798 | 0.767 | 0.727 | 487 | 95.7% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2022 | 4842 | 72.4% | 0.783 | 0.772 | 0.724 | 485 | 94.0% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2023 | 4812 | 70.6% | 0.805 | 0.774 | 0.706 | 482 | 95.2% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2024 | 4806 | 71.2% | 0.812 | 0.779 | 0.712 | 481 | 94.8% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2025 | 4757 | 72.5% | 0.791 | 0.774 | 0.725 | 476 | 96.4% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 2020 | 2624 | 14.1% | 0.653 | 0.859 | 0.859 | 263 | 25.5% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 2021 | 2755 | 14.3% | 0.734 | 0.857 | 0.857 | 276 | 38.8% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 2022 | 2337 | 10.2% | 0.728 | 0.897 | 0.898 | 234 | 27.8% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 2023 | 2624 | 13.3% | 0.747 | 0.866 | 0.867 | 263 | 37.6% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 2024 | 2635 | 12.9% | 0.745 | 0.873 | 0.871 | 264 | 40.5% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 2025 | 2589 | 12.9% | 0.732 | 0.871 | 0.871 | 259 | 35.5% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 2020 | 2624 | 85.8% | 0.650 | 0.858 | 0.858 | 263 | 93.5% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 2021 | 2755 | 85.7% | 0.734 | 0.857 | 0.857 | 276 | 94.2% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 2022 | 2337 | 89.8% | 0.732 | 0.897 | 0.898 | 234 | 94.0% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 2023 | 2624 | 86.7% | 0.756 | 0.869 | 0.867 | 263 | 98.1% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 2024 | 2635 | 87.1% | 0.736 | 0.871 | 0.871 | 264 | 94.3% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 2025 | 2589 | 87.1% | 0.717 | 0.871 | 0.871 | 259 | 96.5% |
| at_fire | high | label.ob_confirmation.did_confirm | 2020 | 2624 | 98.2% | 0.873 | 0.982 | 0.982 | 263 | 99.6% |
| at_fire | high | label.ob_confirmation.did_confirm | 2021 | 2755 | 97.0% | 0.879 | 0.970 | 0.970 | 276 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2022 | 2337 | 97.6% | 0.938 | 0.976 | 0.976 | 234 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2023 | 2624 | 96.3% | 0.931 | 0.962 | 0.963 | 263 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2024 | 2635 | 97.2% | 0.892 | 0.971 | 0.972 | 264 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2025 | 2589 | 97.1% | 0.880 | 0.971 | 0.971 | 259 | 100.0% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2020 | 2624 | 67.9% | 0.724 | 0.698 | 0.679 | 263 | 94.3% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2021 | 2755 | 65.5% | 0.780 | 0.724 | 0.655 | 276 | 94.6% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2022 | 2337 | 75.8% | 0.763 | 0.780 | 0.758 | 234 | 91.9% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2023 | 2624 | 63.7% | 0.786 | 0.732 | 0.637 | 263 | 92.4% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2024 | 2635 | 65.6% | 0.800 | 0.744 | 0.656 | 264 | 92.4% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2025 | 2589 | 67.4% | 0.778 | 0.739 | 0.674 | 259 | 94.6% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2020 | 2010 | 10.7% | 0.616 | 0.892 | 0.893 | 201 | 22.4% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2021 | 2112 | 7.4% | 0.788 | 0.926 | 0.926 | 212 | 29.7% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2022 | 2505 | 13.6% | 0.719 | 0.867 | 0.864 | 251 | 40.6% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2023 | 2188 | 8.5% | 0.695 | 0.915 | 0.915 | 219 | 26.9% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2024 | 2171 | 9.9% | 0.735 | 0.901 | 0.901 | 218 | 33.9% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2025 | 2168 | 9.5% | 0.733 | 0.905 | 0.905 | 217 | 31.3% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 2020 | 2010 | 89.2% | 0.611 | 0.893 | 0.892 | 201 | 90.0% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 2021 | 2112 | 92.5% | 0.792 | 0.925 | 0.925 | 212 | 98.6% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 2022 | 2505 | 86.3% | 0.717 | 0.869 | 0.863 | 251 | 94.8% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 2023 | 2188 | 91.5% | 0.700 | 0.915 | 0.915 | 219 | 95.9% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 2024 | 2171 | 90.1% | 0.740 | 0.901 | 0.901 | 218 | 98.6% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 2025 | 2168 | 90.5% | 0.748 | 0.905 | 0.905 | 217 | 99.5% |
| at_fire | low | label.ob_confirmation.did_confirm | 2020 | 2010 | 96.7% | 0.832 | 0.967 | 0.967 | 201 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2021 | 2112 | 97.7% | 0.867 | 0.977 | 0.977 | 212 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2022 | 2505 | 97.3% | 0.802 | 0.973 | 0.973 | 251 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2023 | 2188 | 98.1% | 0.878 | 0.981 | 0.981 | 219 | 99.1% |
| at_fire | low | label.ob_confirmation.did_confirm | 2024 | 2171 | 96.9% | 0.878 | 0.968 | 0.969 | 218 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2025 | 2168 | 97.0% | 0.926 | 0.970 | 0.970 | 217 | 100.0% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2020 | 2010 | 77.9% | 0.791 | 0.786 | 0.779 | 201 | 98.5% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2021 | 2112 | 82.1% | 0.796 | 0.834 | 0.821 | 212 | 95.3% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2022 | 2505 | 69.3% | 0.785 | 0.749 | 0.693 | 251 | 93.6% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2023 | 2188 | 78.8% | 0.797 | 0.822 | 0.788 | 219 | 96.8% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2024 | 2171 | 78.0% | 0.808 | 0.824 | 0.780 | 218 | 96.8% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2025 | 2168 | 78.6% | 0.804 | 0.823 | 0.786 | 217 | 97.7% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
