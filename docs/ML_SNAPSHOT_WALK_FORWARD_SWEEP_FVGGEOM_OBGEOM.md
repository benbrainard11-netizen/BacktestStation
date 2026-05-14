# ML snapshot walk-forward validation

_Generated `2026-05-14T16:08:17.169328+00:00`._

## Setup

- Matrix: `data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom.parquet`
- Schema: `data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom.schema.json`
- Leaderboard source: `data\ml\anchors\sweep_snapshot_leaderboard_xctx_fvggeom_obgeom.parquet`
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
| data\ml\anchors\sweep_walk_forward_fvggeom_obgeom_summary.csv | candidate summary CSV |
| data\ml\anchors\sweep_walk_forward_fvggeom_obgeom_summary.parquet | candidate summary parquet |
| data\ml\anchors\sweep_walk_forward_fvggeom_obgeom_folds.csv | per-fold CSV |
| data\ml\anchors\sweep_walk_forward_fvggeom_obgeom_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 1966 |
| schema_label_columns | 95 |
| folds_attempted | 72 |
| folds_ok | 72 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | high | label.ob_confirmation.did_confirm | 6 | 15564 | 0.898 | 0.884 | 0.874 | 0.025 | 99.9% | 99.6% | 2.7% |
| at_fire | all | label.ob_confirmation.did_confirm | 6 | 28718 | 0.897 | 0.901 | 0.866 | 0.016 | 100.0% | 99.8% | 2.7% |
| at_fire | low | label.ob_confirmation.did_confirm | 6 | 13154 | 0.864 | 0.860 | 0.817 | 0.036 | 99.9% | 99.5% | 2.6% |
| at_fire | low | label.swept_level_recovery.level_recovered | 6 | 13154 | 0.797 | 0.796 | 0.783 | 0.009 | 96.1% | 91.2% | 18.6% |
| at_fire | all | label.swept_level_recovery.level_recovered | 6 | 28718 | 0.795 | 0.801 | 0.768 | 0.017 | 95.5% | 92.6% | 23.5% |
| at_fire | high | label.swept_level_recovery.level_recovered | 6 | 15564 | 0.775 | 0.777 | 0.741 | 0.017 | 93.9% | 90.6% | 26.2% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 6 | 15564 | 0.724 | 0.734 | 0.653 | 0.034 | 34.4% | 25.1% | 21.4% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 6 | 15564 | 0.724 | 0.735 | 0.651 | 0.034 | 95.8% | 92.4% | 8.8% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 6 | 13154 | 0.722 | 0.734 | 0.639 | 0.050 | 96.4% | 94.5% | 6.4% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 6 | 13154 | 0.721 | 0.734 | 0.643 | 0.047 | 29.9% | 24.7% | 19.9% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 6 | 28718 | 0.701 | 0.714 | 0.628 | 0.040 | 96.7% | 94.6% | 4.7% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 6 | 28718 | 0.699 | 0.704 | 0.629 | 0.039 | 24.3% | 19.3% | 16.3% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2020 | 4634 | 8.4% | 0.629 | 0.916 | 0.916 | 464 | 21.1% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2021 | 4867 | 6.9% | 0.707 | 0.931 | 0.931 | 487 | 22.4% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2022 | 4842 | 10.9% | 0.700 | 0.893 | 0.891 | 485 | 32.2% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2023 | 4812 | 7.4% | 0.675 | 0.927 | 0.926 | 482 | 19.3% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2024 | 4806 | 6.9% | 0.737 | 0.932 | 0.931 | 481 | 22.9% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2025 | 4757 | 7.5% | 0.745 | 0.925 | 0.925 | 476 | 27.9% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 2020 | 4634 | 91.5% | 0.628 | 0.915 | 0.915 | 464 | 94.6% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 2021 | 4867 | 93.0% | 0.722 | 0.930 | 0.930 | 487 | 96.7% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 2022 | 4842 | 89.1% | 0.705 | 0.892 | 0.891 | 485 | 95.7% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 2023 | 4812 | 92.6% | 0.672 | 0.926 | 0.926 | 482 | 97.9% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 2024 | 4806 | 93.1% | 0.736 | 0.931 | 0.931 | 481 | 97.5% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 2025 | 4757 | 92.5% | 0.741 | 0.925 | 0.925 | 476 | 97.5% |
| at_fire | all | label.ob_confirmation.did_confirm | 2020 | 4634 | 97.5% | 0.866 | 0.975 | 0.975 | 464 | 99.8% |
| at_fire | all | label.ob_confirmation.did_confirm | 2021 | 4867 | 97.3% | 0.903 | 0.973 | 0.973 | 487 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2022 | 4842 | 97.5% | 0.899 | 0.975 | 0.975 | 485 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2023 | 4812 | 97.1% | 0.920 | 0.971 | 0.971 | 482 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2024 | 4806 | 97.1% | 0.891 | 0.970 | 0.971 | 481 | 100.0% |
| at_fire | all | label.ob_confirmation.did_confirm | 2025 | 4757 | 97.1% | 0.905 | 0.970 | 0.971 | 476 | 100.0% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2020 | 4634 | 72.2% | 0.768 | 0.746 | 0.722 | 464 | 96.1% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2021 | 4867 | 72.7% | 0.803 | 0.774 | 0.727 | 487 | 96.7% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2022 | 4842 | 72.4% | 0.777 | 0.768 | 0.724 | 485 | 92.6% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2023 | 4812 | 70.6% | 0.804 | 0.772 | 0.706 | 482 | 94.8% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2024 | 4806 | 71.2% | 0.819 | 0.781 | 0.712 | 481 | 96.5% |
| at_fire | all | label.swept_level_recovery.level_recovered | 2025 | 4757 | 72.5% | 0.799 | 0.779 | 0.725 | 476 | 96.2% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 2020 | 2624 | 14.1% | 0.653 | 0.859 | 0.859 | 263 | 25.1% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 2021 | 2755 | 14.3% | 0.727 | 0.857 | 0.857 | 276 | 35.9% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 2022 | 2337 | 10.2% | 0.741 | 0.899 | 0.898 | 234 | 28.2% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 2023 | 2624 | 13.3% | 0.749 | 0.869 | 0.867 | 263 | 36.1% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 2024 | 2635 | 12.9% | 0.752 | 0.874 | 0.871 | 264 | 44.7% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 2025 | 2589 | 12.9% | 0.722 | 0.871 | 0.871 | 259 | 36.3% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 2020 | 2624 | 85.8% | 0.651 | 0.858 | 0.858 | 263 | 95.8% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 2021 | 2755 | 85.7% | 0.727 | 0.857 | 0.857 | 276 | 92.4% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 2022 | 2337 | 89.8% | 0.748 | 0.899 | 0.898 | 234 | 96.6% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 2023 | 2624 | 86.7% | 0.743 | 0.870 | 0.867 | 263 | 98.1% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 2024 | 2635 | 87.1% | 0.750 | 0.873 | 0.871 | 264 | 95.5% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 2025 | 2589 | 87.1% | 0.726 | 0.872 | 0.871 | 259 | 96.5% |
| at_fire | high | label.ob_confirmation.did_confirm | 2020 | 2624 | 98.2% | 0.883 | 0.982 | 0.982 | 263 | 99.6% |
| at_fire | high | label.ob_confirmation.did_confirm | 2021 | 2755 | 97.0% | 0.874 | 0.970 | 0.970 | 276 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2022 | 2337 | 97.6% | 0.942 | 0.976 | 0.976 | 234 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2023 | 2624 | 96.3% | 0.924 | 0.960 | 0.963 | 263 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2024 | 2635 | 97.2% | 0.886 | 0.972 | 0.972 | 264 | 100.0% |
| at_fire | high | label.ob_confirmation.did_confirm | 2025 | 2589 | 97.1% | 0.880 | 0.971 | 0.971 | 259 | 100.0% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2020 | 2624 | 67.9% | 0.741 | 0.713 | 0.679 | 263 | 95.4% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2021 | 2755 | 65.5% | 0.779 | 0.726 | 0.655 | 276 | 93.5% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2022 | 2337 | 75.8% | 0.775 | 0.778 | 0.758 | 234 | 90.6% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2023 | 2624 | 63.7% | 0.775 | 0.723 | 0.637 | 263 | 95.4% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2024 | 2635 | 65.6% | 0.798 | 0.734 | 0.656 | 264 | 92.8% |
| at_fire | high | label.swept_level_recovery.level_recovered | 2025 | 2589 | 67.4% | 0.780 | 0.737 | 0.674 | 259 | 95.4% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2020 | 2010 | 10.7% | 0.643 | 0.893 | 0.893 | 201 | 25.9% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2021 | 2112 | 7.4% | 0.794 | 0.926 | 0.926 | 212 | 25.9% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2022 | 2505 | 13.6% | 0.735 | 0.867 | 0.864 | 251 | 41.0% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2023 | 2188 | 8.5% | 0.686 | 0.915 | 0.915 | 219 | 24.7% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2024 | 2171 | 9.9% | 0.734 | 0.901 | 0.901 | 218 | 29.4% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 2025 | 2168 | 9.5% | 0.735 | 0.905 | 0.905 | 217 | 32.3% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 2020 | 2010 | 89.2% | 0.639 | 0.894 | 0.892 | 201 | 95.0% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 2021 | 2112 | 92.5% | 0.800 | 0.925 | 0.925 | 212 | 99.1% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 2022 | 2505 | 86.3% | 0.728 | 0.866 | 0.863 | 251 | 96.0% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 2023 | 2188 | 91.5% | 0.685 | 0.914 | 0.915 | 219 | 96.8% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 2024 | 2171 | 90.1% | 0.742 | 0.901 | 0.901 | 218 | 96.8% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 2025 | 2168 | 90.5% | 0.741 | 0.905 | 0.905 | 217 | 94.5% |
| at_fire | low | label.ob_confirmation.did_confirm | 2020 | 2010 | 96.7% | 0.840 | 0.967 | 0.967 | 201 | 99.5% |
| at_fire | low | label.ob_confirmation.did_confirm | 2021 | 2112 | 97.7% | 0.841 | 0.977 | 0.977 | 212 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2022 | 2505 | 97.3% | 0.817 | 0.973 | 0.973 | 251 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2023 | 2188 | 98.1% | 0.886 | 0.981 | 0.981 | 219 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2024 | 2171 | 96.9% | 0.878 | 0.968 | 0.969 | 218 | 100.0% |
| at_fire | low | label.ob_confirmation.did_confirm | 2025 | 2168 | 97.0% | 0.924 | 0.970 | 0.970 | 217 | 100.0% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2020 | 2010 | 77.9% | 0.807 | 0.795 | 0.779 | 201 | 99.0% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2021 | 2112 | 82.1% | 0.796 | 0.830 | 0.821 | 212 | 97.6% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2022 | 2505 | 69.3% | 0.783 | 0.747 | 0.693 | 251 | 91.2% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2023 | 2188 | 78.8% | 0.791 | 0.819 | 0.788 | 219 | 95.9% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2024 | 2171 | 78.0% | 0.810 | 0.818 | 0.780 | 218 | 97.2% |
| at_fire | low | label.swept_level_recovery.level_recovered | 2025 | 2168 | 78.6% | 0.796 | 0.825 | 0.786 | 217 | 95.4% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
