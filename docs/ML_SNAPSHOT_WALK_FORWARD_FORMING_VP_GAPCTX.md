# ML snapshot walk-forward validation

_Generated `2026-05-14T09:59:48.395193+00:00`._

## Setup

- Matrix: `data\ml\anchors\forming_vp_snapshots_xctx_gapctx.parquet`
- Schema: `data\ml\anchors\forming_vp_snapshots_xctx_gapctx.schema.json`
- Leaderboard source: `data\ml\anchors\forming_vp_snapshot_leaderboard_gapctx.parquet`
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
| data\ml\anchors\forming_vp_walk_forward_gapctx_summary.csv | candidate summary CSV |
| data\ml\anchors\forming_vp_walk_forward_gapctx_summary.parquet | candidate summary parquet |
| data\ml\anchors\forming_vp_walk_forward_gapctx_folds.csv | per-fold CSV |
| data\ml\anchors\forming_vp_walk_forward_gapctx_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 43150 |
| schema_feature_columns | 1067 |
| schema_label_columns | 507 |
| folds_attempted | 72 |
| folds_ok | 72 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | balanced | label.rest_of_day.range_expanded_1x_profile_so_far | 6 | 12916 | 0.952 | 0.952 | 0.925 | 0.015 | 99.9% | 99.5% | 27.1% |
| at_fire | all | label.rest_of_day.range_expanded_1x_profile_so_far | 6 | 22922 | 0.950 | 0.951 | 0.917 | 0.017 | 99.9% | 99.7% | 29.6% |
| at_fire | buying | label.rest_of_day.range_expanded_1x_profile_so_far | 6 | 5814 | 0.943 | 0.947 | 0.905 | 0.019 | 99.7% | 98.2% | 33.0% |
| at_fire | selling | label.rest_of_day.range_expanded_1x_profile_so_far | 6 | 4192 | 0.942 | 0.946 | 0.904 | 0.020 | 99.5% | 98.5% | 31.2% |
| at_fire | selling | label.next_60m.took_profile_so_far_high | 6 | 4192 | 0.916 | 0.918 | 0.895 | 0.012 | 67.6% | 63.1% | 52.4% |
| at_fire | buying | label.next_60m.took_profile_so_far_low | 6 | 5811 | 0.899 | 0.895 | 0.877 | 0.020 | 66.3% | 61.2% | 53.1% |
| at_fire | all | label.next_60m.took_profile_so_far_high | 6 | 22912 | 0.887 | 0.886 | 0.882 | 0.005 | 78.2% | 74.7% | 54.2% |
| at_fire | balanced | label.next_60m.took_profile_so_far_high | 6 | 12909 | 0.883 | 0.881 | 0.873 | 0.008 | 78.9% | 73.5% | 55.8% |
| at_fire | all | label.next_60m.took_profile_so_far_low | 6 | 22912 | 0.876 | 0.871 | 0.868 | 0.009 | 73.2% | 67.4% | 53.8% |
| at_fire | buying | label.next_60m.took_profile_so_far_low_rejected_inside | 6 | 5811 | 0.875 | 0.867 | 0.850 | 0.021 | 31.3% | 21.6% | 24.7% |
| at_fire | selling | label.next_60m.took_profile_so_far_high_rejected_inside | 6 | 4192 | 0.865 | 0.866 | 0.816 | 0.029 | 28.2% | 23.0% | 20.7% |
| at_fire | buying | label.next_60m.took_profile_so_far_high | 6 | 5811 | 0.860 | 0.856 | 0.847 | 0.013 | 82.8% | 77.3% | 50.6% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_60m.took_profile_so_far_high | 2020 | 3826 | 23.8% | 0.885 | 0.832 | 0.762 | 383 | 74.7% |
| at_fire | all | label.next_60m.took_profile_so_far_high | 2021 | 3834 | 22.9% | 0.882 | 0.837 | 0.771 | 384 | 77.9% |
| at_fire | all | label.next_60m.took_profile_so_far_high | 2022 | 3822 | 23.1% | 0.887 | 0.843 | 0.769 | 383 | 74.9% |
| at_fire | all | label.next_60m.took_profile_so_far_high | 2023 | 3813 | 23.7% | 0.891 | 0.849 | 0.763 | 382 | 78.3% |
| at_fire | all | label.next_60m.took_profile_so_far_high | 2024 | 3831 | 25.8% | 0.883 | 0.831 | 0.742 | 384 | 80.2% |
| at_fire | all | label.next_60m.took_profile_so_far_high | 2025 | 3786 | 24.7% | 0.895 | 0.838 | 0.753 | 379 | 83.4% |
| at_fire | all | label.next_60m.took_profile_so_far_low | 2020 | 3826 | 16.6% | 0.894 | 0.878 | 0.834 | 383 | 71.3% |
| at_fire | all | label.next_60m.took_profile_so_far_low | 2021 | 3834 | 18.4% | 0.868 | 0.856 | 0.816 | 384 | 67.4% |
| at_fire | all | label.next_60m.took_profile_so_far_low | 2022 | 3822 | 21.6% | 0.869 | 0.844 | 0.784 | 383 | 78.3% |
| at_fire | all | label.next_60m.took_profile_so_far_low | 2023 | 3813 | 21.2% | 0.871 | 0.849 | 0.788 | 382 | 76.7% |
| at_fire | all | label.next_60m.took_profile_so_far_low | 2024 | 3831 | 19.3% | 0.880 | 0.864 | 0.807 | 384 | 76.8% |
| at_fire | all | label.next_60m.took_profile_so_far_low | 2025 | 3786 | 19.4% | 0.872 | 0.849 | 0.806 | 379 | 68.9% |
| at_fire | all | label.rest_of_day.range_expanded_1x_profile_so_far | 2020 | 3827 | 63.6% | 0.917 | 0.828 | 0.636 | 383 | 99.7% |
| at_fire | all | label.rest_of_day.range_expanded_1x_profile_so_far | 2021 | 3834 | 68.5% | 0.947 | 0.878 | 0.685 | 384 | 100.0% |
| at_fire | all | label.rest_of_day.range_expanded_1x_profile_so_far | 2022 | 3822 | 72.3% | 0.949 | 0.882 | 0.723 | 383 | 100.0% |
| at_fire | all | label.rest_of_day.range_expanded_1x_profile_so_far | 2023 | 3813 | 73.7% | 0.968 | 0.908 | 0.737 | 382 | 100.0% |
| at_fire | all | label.rest_of_day.range_expanded_1x_profile_so_far | 2024 | 3831 | 73.7% | 0.965 | 0.912 | 0.737 | 384 | 99.7% |
| at_fire | all | label.rest_of_day.range_expanded_1x_profile_so_far | 2025 | 3795 | 70.4% | 0.954 | 0.898 | 0.704 | 380 | 100.0% |
| at_fire | balanced | label.next_60m.took_profile_so_far_high | 2020 | 2072 | 21.8% | 0.878 | 0.836 | 0.782 | 208 | 73.6% |
| at_fire | balanced | label.next_60m.took_profile_so_far_high | 2021 | 2142 | 21.1% | 0.884 | 0.852 | 0.789 | 215 | 73.5% |
| at_fire | balanced | label.next_60m.took_profile_so_far_high | 2022 | 2119 | 23.2% | 0.879 | 0.844 | 0.768 | 212 | 81.6% |
| at_fire | balanced | label.next_60m.took_profile_so_far_high | 2023 | 2187 | 23.1% | 0.883 | 0.845 | 0.769 | 219 | 78.1% |
| at_fire | balanced | label.next_60m.took_profile_so_far_high | 2024 | 2231 | 25.1% | 0.873 | 0.822 | 0.749 | 224 | 81.2% |
| at_fire | balanced | label.next_60m.took_profile_so_far_high | 2025 | 2158 | 24.4% | 0.898 | 0.846 | 0.756 | 216 | 85.2% |
| at_fire | balanced | label.rest_of_day.range_expanded_1x_profile_so_far | 2020 | 2073 | 66.3% | 0.925 | 0.836 | 0.663 | 208 | 100.0% |
| at_fire | balanced | label.rest_of_day.range_expanded_1x_profile_so_far | 2021 | 2142 | 71.7% | 0.946 | 0.880 | 0.717 | 215 | 100.0% |
| at_fire | balanced | label.rest_of_day.range_expanded_1x_profile_so_far | 2022 | 2119 | 75.0% | 0.945 | 0.895 | 0.750 | 212 | 100.0% |
| at_fire | balanced | label.rest_of_day.range_expanded_1x_profile_so_far | 2023 | 2187 | 75.3% | 0.972 | 0.920 | 0.753 | 219 | 100.0% |
| at_fire | balanced | label.rest_of_day.range_expanded_1x_profile_so_far | 2024 | 2231 | 75.9% | 0.964 | 0.915 | 0.759 | 224 | 100.0% |
| at_fire | balanced | label.rest_of_day.range_expanded_1x_profile_so_far | 2025 | 2164 | 72.6% | 0.959 | 0.915 | 0.726 | 217 | 99.5% |
| at_fire | buying | label.next_60m.took_profile_so_far_high | 2020 | 1111 | 33.7% | 0.847 | 0.769 | 0.663 | 112 | 82.1% |
| at_fire | buying | label.next_60m.took_profile_so_far_high | 2021 | 1033 | 32.6% | 0.848 | 0.784 | 0.674 | 104 | 82.7% |
| at_fire | buying | label.next_60m.took_profile_so_far_high | 2022 | 879 | 29.9% | 0.849 | 0.784 | 0.701 | 88 | 77.3% |
| at_fire | buying | label.next_60m.took_profile_so_far_high | 2023 | 889 | 31.2% | 0.882 | 0.821 | 0.688 | 89 | 84.3% |
| at_fire | buying | label.next_60m.took_profile_so_far_high | 2024 | 928 | 33.8% | 0.871 | 0.794 | 0.662 | 93 | 84.9% |
| at_fire | buying | label.next_60m.took_profile_so_far_high | 2025 | 971 | 32.1% | 0.863 | 0.781 | 0.679 | 98 | 85.7% |
| at_fire | buying | label.next_60m.took_profile_so_far_low | 2020 | 1111 | 9.5% | 0.928 | 0.926 | 0.905 | 112 | 62.5% |
| at_fire | buying | label.next_60m.took_profile_so_far_low | 2021 | 1033 | 11.9% | 0.906 | 0.912 | 0.881 | 104 | 64.4% |
| at_fire | buying | label.next_60m.took_profile_so_far_low | 2022 | 879 | 14.8% | 0.883 | 0.882 | 0.852 | 88 | 67.0% |
| at_fire | buying | label.next_60m.took_profile_so_far_low | 2023 | 889 | 14.5% | 0.877 | 0.883 | 0.855 | 89 | 64.0% |
| at_fire | buying | label.next_60m.took_profile_so_far_low | 2024 | 928 | 14.1% | 0.919 | 0.906 | 0.859 | 93 | 78.5% |
| at_fire | buying | label.next_60m.took_profile_so_far_low | 2025 | 971 | 14.1% | 0.878 | 0.878 | 0.859 | 98 | 61.2% |
| at_fire | buying | label.next_60m.took_profile_so_far_low_rejected_inside | 2020 | 1111 | 5.2% | 0.902 | 0.951 | 0.948 | 112 | 28.6% |
| at_fire | buying | label.next_60m.took_profile_so_far_low_rejected_inside | 2021 | 1033 | 7.1% | 0.906 | 0.933 | 0.929 | 104 | 39.4% |
| at_fire | buying | label.next_60m.took_profile_so_far_low_rejected_inside | 2022 | 879 | 5.8% | 0.850 | 0.935 | 0.942 | 88 | 21.6% |
| at_fire | buying | label.next_60m.took_profile_so_far_low_rejected_inside | 2023 | 889 | 6.6% | 0.863 | 0.927 | 0.934 | 89 | 29.2% |
| at_fire | buying | label.next_60m.took_profile_so_far_low_rejected_inside | 2024 | 928 | 8.1% | 0.872 | 0.919 | 0.919 | 93 | 36.6% |
| at_fire | buying | label.next_60m.took_profile_so_far_low_rejected_inside | 2025 | 971 | 7.1% | 0.860 | 0.924 | 0.929 | 98 | 32.7% |
| at_fire | buying | label.rest_of_day.range_expanded_1x_profile_so_far | 2020 | 1111 | 57.5% | 0.905 | 0.821 | 0.575 | 112 | 98.2% |
| at_fire | buying | label.rest_of_day.range_expanded_1x_profile_so_far | 2021 | 1033 | 62.1% | 0.942 | 0.862 | 0.621 | 104 | 100.0% |
| at_fire | buying | label.rest_of_day.range_expanded_1x_profile_so_far | 2022 | 879 | 68.8% | 0.952 | 0.874 | 0.688 | 88 | 100.0% |
| at_fire | buying | label.rest_of_day.range_expanded_1x_profile_so_far | 2023 | 889 | 74.4% | 0.964 | 0.884 | 0.744 | 89 | 100.0% |
| at_fire | buying | label.rest_of_day.range_expanded_1x_profile_so_far | 2024 | 928 | 70.6% | 0.956 | 0.900 | 0.706 | 93 | 100.0% |
| at_fire | buying | label.rest_of_day.range_expanded_1x_profile_so_far | 2025 | 974 | 66.7% | 0.940 | 0.879 | 0.667 | 98 | 100.0% |
| at_fire | selling | label.next_60m.took_profile_so_far_high | 2020 | 643 | 13.2% | 0.931 | 0.899 | 0.868 | 65 | 63.1% |
| at_fire | selling | label.next_60m.took_profile_so_far_high | 2021 | 659 | 13.8% | 0.907 | 0.888 | 0.862 | 66 | 65.2% |
| at_fire | selling | label.next_60m.took_profile_so_far_high | 2022 | 824 | 15.5% | 0.920 | 0.875 | 0.845 | 83 | 63.9% |
| at_fire | selling | label.next_60m.took_profile_so_far_high | 2023 | 737 | 16.7% | 0.916 | 0.890 | 0.833 | 74 | 74.3% |
| at_fire | selling | label.next_60m.took_profile_so_far_high | 2024 | 672 | 17.1% | 0.895 | 0.874 | 0.829 | 68 | 64.7% |
| at_fire | selling | label.next_60m.took_profile_so_far_high | 2025 | 657 | 14.6% | 0.926 | 0.900 | 0.854 | 66 | 74.2% |
| at_fire | selling | label.next_60m.took_profile_so_far_high_rejected_inside | 2020 | 643 | 7.8% | 0.886 | 0.922 | 0.922 | 65 | 29.2% |
| at_fire | selling | label.next_60m.took_profile_so_far_high_rejected_inside | 2021 | 659 | 7.6% | 0.872 | 0.924 | 0.924 | 66 | 25.8% |
| at_fire | selling | label.next_60m.took_profile_so_far_high_rejected_inside | 2022 | 824 | 6.6% | 0.860 | 0.926 | 0.934 | 83 | 24.1% |
| at_fire | selling | label.next_60m.took_profile_so_far_high_rejected_inside | 2023 | 737 | 7.9% | 0.816 | 0.916 | 0.921 | 74 | 23.0% |
| at_fire | selling | label.next_60m.took_profile_so_far_high_rejected_inside | 2024 | 672 | 7.7% | 0.847 | 0.923 | 0.923 | 68 | 27.9% |
| at_fire | selling | label.next_60m.took_profile_so_far_high_rejected_inside | 2025 | 657 | 7.5% | 0.908 | 0.925 | 0.925 | 66 | 39.4% |
| at_fire | selling | label.rest_of_day.range_expanded_1x_profile_so_far | 2020 | 643 | 65.6% | 0.904 | 0.818 | 0.656 | 65 | 98.5% |
| at_fire | selling | label.rest_of_day.range_expanded_1x_profile_so_far | 2021 | 659 | 68.0% | 0.943 | 0.874 | 0.680 | 66 | 98.5% |
| at_fire | selling | label.rest_of_day.range_expanded_1x_profile_so_far | 2022 | 824 | 68.9% | 0.938 | 0.881 | 0.689 | 83 | 100.0% |
| at_fire | selling | label.rest_of_day.range_expanded_1x_profile_so_far | 2023 | 737 | 68.5% | 0.949 | 0.883 | 0.685 | 74 | 100.0% |
| at_fire | selling | label.rest_of_day.range_expanded_1x_profile_so_far | 2024 | 672 | 70.4% | 0.972 | 0.923 | 0.704 | 68 | 100.0% |
| at_fire | selling | label.rest_of_day.range_expanded_1x_profile_so_far | 2025 | 657 | 68.5% | 0.949 | 0.880 | 0.685 | 66 | 100.0% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
