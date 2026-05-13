# ML snapshot walk-forward validation

_Generated `2026-05-13T04:31:04.918655+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\forming_vp_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\forming_vp_snapshots_xctx.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\forming_vp_snapshot_leaderboard_xctx.parquet`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\forming_vp_walk_forward_xctx_summary.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\forming_vp_walk_forward_xctx_summary.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\forming_vp_walk_forward_xctx_folds.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\forming_vp_walk_forward_xctx_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 43150 |
| schema_feature_columns | 710 |
| schema_label_columns | 411 |
| folds_attempted | 72 |
| folds_ok | 70 |
| folds_skipped | 2 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | selling | label.next_240m.vah_touch.resistance_break_acceptance_3bar | 6 | 4192 | 0.919 | 0.925 | 0.881 | 0.019 | 13.7% | 10.6% | 11.4% |
| at_fire | selling | label.next_240m.vah_touch.resistance_rejection_3bar | 6 | 4192 | 0.918 | 0.916 | 0.905 | 0.013 | 14.3% | 10.8% | 12.0% |
| at_fire | selling | label.next_60m.took_profile_high_so_far | 6 | 4192 | 0.912 | 0.916 | 0.894 | 0.012 | 65.2% | 54.5% | 50.0% |
| at_fire | all | label.next_240m.vah_touch.resistance_rejection_3bar | 6 | 22916 | 0.904 | 0.903 | 0.893 | 0.007 | 21.5% | 19.0% | 16.9% |
| at_fire | buying | label.next_60m.vwap_touch.resistance_break_acceptance_3bar | 6 | 5811 | 0.901 | 0.903 | 0.880 | 0.014 | 21.3% | 18.2% | 17.2% |
| at_fire | all | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 6 | 22912 | 0.899 | 0.899 | 0.889 | 0.008 | 16.4% | 14.1% | 13.2% |
| at_fire | buying | label.next_60m.took_profile_low_so_far | 6 | 5811 | 0.898 | 0.898 | 0.873 | 0.021 | 66.0% | 58.9% | 52.8% |
| at_fire | buying | label.next_240m.vah_touch.resistance_rejection_3bar | 6 | 5812 | 0.897 | 0.899 | 0.888 | 0.006 | 21.8% | 17.0% | 16.7% |
| at_fire | buying | label.next_60m.vah_touch.resistance_rejection_3bar | 6 | 5811 | 0.896 | 0.893 | 0.884 | 0.012 | 17.0% | 13.5% | 13.5% |
| at_fire | all | label.next_60m.vah_touch.resistance_rejection_3bar | 6 | 22912 | 0.895 | 0.893 | 0.886 | 0.007 | 15.4% | 14.1% | 12.0% |
| at_fire | selling | label.next_60m.vah_touch.resistance_rejection_3bar | 5 | 3549 | 0.927 | 0.935 | 0.902 | 0.018 | 13.9% | 10.8% | 11.8% |
| at_fire | selling | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 5 | 3549 | 0.916 | 0.914 | 0.888 | 0.020 | 12.8% | 9.1% | 10.7% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_240m.vah_touch.resistance_rejection_3bar | 2020 | 3827 | 4.2% | 0.916 | 0.957 | 0.958 | 383 | 23.8% |
| at_fire | all | label.next_240m.vah_touch.resistance_rejection_3bar | 2021 | 3834 | 4.3% | 0.900 | 0.956 | 0.957 | 384 | 19.0% |
| at_fire | all | label.next_240m.vah_touch.resistance_rejection_3bar | 2022 | 3822 | 5.1% | 0.893 | 0.949 | 0.949 | 383 | 19.8% |
| at_fire | all | label.next_240m.vah_touch.resistance_rejection_3bar | 2023 | 3813 | 4.8% | 0.908 | 0.952 | 0.952 | 382 | 23.3% |
| at_fire | all | label.next_240m.vah_touch.resistance_rejection_3bar | 2024 | 3831 | 4.9% | 0.905 | 0.951 | 0.951 | 384 | 22.7% |
| at_fire | all | label.next_240m.vah_touch.resistance_rejection_3bar | 2025 | 3789 | 4.2% | 0.898 | 0.958 | 0.958 | 379 | 20.6% |
| at_fire | all | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 2020 | 3826 | 2.9% | 0.914 | 0.971 | 0.971 | 383 | 16.7% |
| at_fire | all | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 2021 | 3834 | 3.2% | 0.902 | 0.967 | 0.968 | 384 | 18.5% |
| at_fire | all | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 2022 | 3822 | 3.8% | 0.896 | 0.962 | 0.962 | 383 | 19.6% |
| at_fire | all | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 2023 | 3813 | 2.9% | 0.891 | 0.971 | 0.971 | 382 | 14.1% |
| at_fire | all | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 2024 | 3831 | 2.9% | 0.901 | 0.971 | 0.971 | 384 | 14.8% |
| at_fire | all | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 2025 | 3786 | 3.2% | 0.889 | 0.968 | 0.968 | 379 | 14.5% |
| at_fire | all | label.next_60m.vah_touch.resistance_rejection_3bar | 2020 | 3826 | 3.1% | 0.905 | 0.969 | 0.969 | 383 | 15.1% |
| at_fire | all | label.next_60m.vah_touch.resistance_rejection_3bar | 2021 | 3834 | 3.3% | 0.886 | 0.967 | 0.967 | 384 | 14.1% |
| at_fire | all | label.next_60m.vah_touch.resistance_rejection_3bar | 2022 | 3822 | 4.1% | 0.889 | 0.959 | 0.959 | 383 | 17.5% |
| at_fire | all | label.next_60m.vah_touch.resistance_rejection_3bar | 2023 | 3813 | 3.3% | 0.893 | 0.967 | 0.967 | 382 | 14.1% |
| at_fire | all | label.next_60m.vah_touch.resistance_rejection_3bar | 2024 | 3831 | 3.2% | 0.893 | 0.968 | 0.968 | 384 | 15.6% |
| at_fire | all | label.next_60m.vah_touch.resistance_rejection_3bar | 2025 | 3786 | 3.2% | 0.903 | 0.968 | 0.968 | 379 | 15.8% |
| at_fire | buying | label.next_240m.vah_touch.resistance_rejection_3bar | 2020 | 1111 | 4.4% | 0.900 | 0.956 | 0.956 | 112 | 17.0% |
| at_fire | buying | label.next_240m.vah_touch.resistance_rejection_3bar | 2021 | 1033 | 4.0% | 0.902 | 0.959 | 0.960 | 104 | 21.2% |
| at_fire | buying | label.next_240m.vah_touch.resistance_rejection_3bar | 2022 | 879 | 6.3% | 0.890 | 0.937 | 0.937 | 88 | 22.7% |
| at_fire | buying | label.next_240m.vah_touch.resistance_rejection_3bar | 2023 | 889 | 6.3% | 0.888 | 0.937 | 0.937 | 89 | 27.0% |
| at_fire | buying | label.next_240m.vah_touch.resistance_rejection_3bar | 2024 | 928 | 6.4% | 0.899 | 0.935 | 0.936 | 93 | 25.8% |
| at_fire | buying | label.next_240m.vah_touch.resistance_rejection_3bar | 2025 | 972 | 3.6% | 0.906 | 0.964 | 0.964 | 98 | 17.3% |
| at_fire | buying | label.next_60m.took_profile_low_so_far | 2020 | 1111 | 9.5% | 0.927 | 0.922 | 0.905 | 112 | 58.9% |
| at_fire | buying | label.next_60m.took_profile_low_so_far | 2021 | 1033 | 11.9% | 0.911 | 0.919 | 0.881 | 104 | 66.3% |
| at_fire | buying | label.next_60m.took_profile_low_so_far | 2022 | 879 | 14.8% | 0.873 | 0.883 | 0.852 | 88 | 64.8% |
| at_fire | buying | label.next_60m.took_profile_low_so_far | 2023 | 889 | 14.5% | 0.874 | 0.884 | 0.855 | 89 | 65.2% |
| at_fire | buying | label.next_60m.took_profile_low_so_far | 2024 | 928 | 14.1% | 0.917 | 0.909 | 0.859 | 93 | 77.4% |
| at_fire | buying | label.next_60m.took_profile_low_so_far | 2025 | 971 | 14.1% | 0.885 | 0.885 | 0.859 | 98 | 63.3% |
| at_fire | buying | label.next_60m.vah_touch.resistance_rejection_3bar | 2020 | 1111 | 3.1% | 0.906 | 0.968 | 0.969 | 112 | 16.1% |
| at_fire | buying | label.next_60m.vah_touch.resistance_rejection_3bar | 2021 | 1033 | 3.1% | 0.891 | 0.969 | 0.969 | 104 | 13.5% |
| at_fire | buying | label.next_60m.vah_touch.resistance_rejection_3bar | 2022 | 879 | 4.4% | 0.884 | 0.956 | 0.956 | 88 | 18.2% |
| at_fire | buying | label.next_60m.vah_touch.resistance_rejection_3bar | 2023 | 889 | 3.7% | 0.884 | 0.963 | 0.963 | 89 | 16.9% |
| at_fire | buying | label.next_60m.vah_touch.resistance_rejection_3bar | 2024 | 928 | 4.0% | 0.894 | 0.959 | 0.960 | 93 | 19.4% |
| at_fire | buying | label.next_60m.vah_touch.resistance_rejection_3bar | 2025 | 971 | 2.8% | 0.918 | 0.972 | 0.972 | 98 | 18.4% |
| at_fire | buying | label.next_60m.vwap_touch.resistance_break_acceptance_3bar | 2020 | 1111 | 3.2% | 0.921 | 0.968 | 0.968 | 112 | 19.6% |
| at_fire | buying | label.next_60m.vwap_touch.resistance_break_acceptance_3bar | 2021 | 1033 | 4.6% | 0.880 | 0.954 | 0.954 | 104 | 22.1% |
| at_fire | buying | label.next_60m.vwap_touch.resistance_break_acceptance_3bar | 2022 | 879 | 3.4% | 0.901 | 0.965 | 0.966 | 88 | 18.2% |
| at_fire | buying | label.next_60m.vwap_touch.resistance_break_acceptance_3bar | 2023 | 889 | 4.4% | 0.887 | 0.955 | 0.956 | 89 | 23.6% |
| at_fire | buying | label.next_60m.vwap_touch.resistance_break_acceptance_3bar | 2024 | 928 | 4.8% | 0.905 | 0.950 | 0.952 | 93 | 23.7% |
| at_fire | buying | label.next_60m.vwap_touch.resistance_break_acceptance_3bar | 2025 | 971 | 3.7% | 0.910 | 0.961 | 0.963 | 98 | 20.4% |
| at_fire | selling | label.next_240m.vah_touch.resistance_break_acceptance_3bar | 2020 | 643 | 1.7% | 0.920 | 0.981 | 0.983 | 65 | 10.8% |
| at_fire | selling | label.next_240m.vah_touch.resistance_break_acceptance_3bar | 2021 | 659 | 1.5% | 0.934 | 0.985 | 0.985 | 66 | 10.6% |
| at_fire | selling | label.next_240m.vah_touch.resistance_break_acceptance_3bar | 2022 | 824 | 3.4% | 0.881 | 0.964 | 0.966 | 83 | 15.7% |
| at_fire | selling | label.next_240m.vah_touch.resistance_break_acceptance_3bar | 2023 | 737 | 2.4% | 0.913 | 0.976 | 0.976 | 74 | 12.2% |
| at_fire | selling | label.next_240m.vah_touch.resistance_break_acceptance_3bar | 2024 | 672 | 1.9% | 0.929 | 0.981 | 0.981 | 68 | 13.2% |
| at_fire | selling | label.next_240m.vah_touch.resistance_break_acceptance_3bar | 2025 | 657 | 2.6% | 0.939 | 0.974 | 0.974 | 66 | 19.7% |
| at_fire | selling | label.next_240m.vah_touch.resistance_rejection_3bar | 2020 | 643 | 1.6% | 0.922 | 0.984 | 0.984 | 65 | 10.8% |
| at_fire | selling | label.next_240m.vah_touch.resistance_rejection_3bar | 2021 | 659 | 2.6% | 0.907 | 0.974 | 0.974 | 66 | 15.2% |
| at_fire | selling | label.next_240m.vah_touch.resistance_rejection_3bar | 2022 | 824 | 2.4% | 0.910 | 0.976 | 0.976 | 83 | 10.8% |
| at_fire | selling | label.next_240m.vah_touch.resistance_rejection_3bar | 2023 | 737 | 2.3% | 0.905 | 0.977 | 0.977 | 74 | 16.2% |
| at_fire | selling | label.next_240m.vah_touch.resistance_rejection_3bar | 2024 | 672 | 1.9% | 0.943 | 0.981 | 0.981 | 68 | 14.7% |
| at_fire | selling | label.next_240m.vah_touch.resistance_rejection_3bar | 2025 | 657 | 3.0% | 0.921 | 0.968 | 0.970 | 66 | 18.2% |
| at_fire | selling | label.next_60m.took_profile_high_so_far | 2020 | 643 | 13.2% | 0.925 | 0.890 | 0.868 | 65 | 60.0% |
| at_fire | selling | label.next_60m.took_profile_high_so_far | 2021 | 659 | 13.8% | 0.899 | 0.885 | 0.862 | 66 | 54.5% |
| at_fire | selling | label.next_60m.took_profile_high_so_far | 2022 | 824 | 15.5% | 0.918 | 0.874 | 0.845 | 83 | 60.2% |
| at_fire | selling | label.next_60m.took_profile_high_so_far | 2023 | 737 | 16.7% | 0.913 | 0.883 | 0.833 | 74 | 73.0% |
| at_fire | selling | label.next_60m.took_profile_high_so_far | 2024 | 672 | 17.1% | 0.894 | 0.881 | 0.829 | 68 | 66.2% |
| at_fire | selling | label.next_60m.took_profile_high_so_far | 2025 | 657 | 14.6% | 0.924 | 0.896 | 0.854 | 66 | 77.3% |
| at_fire | selling | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 2021 | 659 | 1.5% | 0.913 | 0.985 | 0.985 | 66 | 9.1% |
| at_fire | selling | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 2022 | 824 | 2.8% | 0.888 | 0.972 | 0.972 | 83 | 16.9% |
| at_fire | selling | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 2023 | 737 | 2.3% | 0.914 | 0.977 | 0.977 | 74 | 9.5% |
| at_fire | selling | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 2024 | 672 | 1.6% | 0.950 | 0.984 | 0.984 | 68 | 14.7% |
| at_fire | selling | label.next_60m.vah_touch.resistance_break_acceptance_3bar | 2025 | 657 | 2.1% | 0.916 | 0.979 | 0.979 | 66 | 13.6% |
| at_fire | selling | label.next_60m.vah_touch.resistance_rejection_3bar | 2021 | 659 | 2.3% | 0.902 | 0.977 | 0.977 | 66 | 13.6% |
| at_fire | selling | label.next_60m.vah_touch.resistance_rejection_3bar | 2022 | 824 | 2.2% | 0.910 | 0.978 | 0.978 | 83 | 10.8% |
| at_fire | selling | label.next_60m.vah_touch.resistance_rejection_3bar | 2023 | 737 | 1.5% | 0.952 | 0.985 | 0.985 | 74 | 13.5% |
| at_fire | selling | label.next_60m.vah_touch.resistance_rejection_3bar | 2024 | 672 | 1.8% | 0.935 | 0.982 | 0.982 | 68 | 13.2% |
| at_fire | selling | label.next_60m.vah_touch.resistance_rejection_3bar | 2025 | 657 | 2.6% | 0.936 | 0.974 | 0.974 | 66 | 18.2% |

## Skipped Folds

| status | count |
|---|---|
| skip_test_imbalance | 2 |

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
