# ML snapshot walk-forward validation

_Generated `2026-05-13T03:05:52.201143+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshots_xctx.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\vp_snapshot_leaderboard_v2_xctx.parquet`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\vp_walk_forward_v2_xctx_summary.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\vp_walk_forward_v2_xctx_summary.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\vp_walk_forward_v2_xctx_folds.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\vp_walk_forward_v2_xctx_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 36095 |
| schema_feature_columns | 657 |
| schema_label_columns | 139 |
| folds_attempted | 72 |
| folds_ok | 72 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | buying | label.vah_touch.resistance_break_acceptance_3bar | 6 | 4954 | 0.911 | 0.914 | 0.886 | 0.015 | 23.3% | 21.0% | 18.6% |
| at_fire | all | label.vah_touch.resistance_rejection_3bar | 6 | 18458 | 0.908 | 0.904 | 0.897 | 0.009 | 23.8% | 21.1% | 19.1% |
| at_fire | all | label.vah_touch.resistance_break_acceptance_3bar | 6 | 18458 | 0.904 | 0.902 | 0.898 | 0.006 | 23.0% | 20.1% | 18.3% |
| at_fire | selling | label.vah_touch.resistance_break_acceptance_3bar | 6 | 3449 | 0.902 | 0.897 | 0.872 | 0.021 | 19.4% | 11.8% | 16.1% |
| at_fire | balanced | label.vah_touch.resistance_rejection_3bar | 6 | 10055 | 0.897 | 0.897 | 0.887 | 0.005 | 23.6% | 19.8% | 18.2% |
| at_fire | buying | label.vah_touch.resistance_rejection_3bar | 6 | 4954 | 0.896 | 0.904 | 0.859 | 0.023 | 24.8% | 17.8% | 19.6% |
| at_fire | balanced | label.vah_touch.resistance_break_acceptance_3bar | 6 | 10055 | 0.893 | 0.893 | 0.882 | 0.007 | 22.6% | 20.3% | 17.4% |
| at_fire | buying | label.vwap_touch.resistance_rejection_3bar | 6 | 4954 | 0.886 | 0.892 | 0.818 | 0.034 | 25.4% | 16.4% | 18.9% |
| at_fire | buying | label.vwap_touch.resistance_break_acceptance_3bar | 6 | 4954 | 0.885 | 0.883 | 0.867 | 0.013 | 24.0% | 18.9% | 17.7% |
| at_fire | selling | label.vwap_touch.support_break_acceptance_3bar | 6 | 3449 | 0.872 | 0.872 | 0.853 | 0.012 | 28.7% | 20.8% | 20.7% |
| at_fire | all | label.val_touch.support_break_acceptance_3bar | 6 | 18458 | 0.871 | 0.871 | 0.840 | 0.018 | 21.5% | 15.9% | 15.9% |
| at_fire | selling | label.val_touch.support_break_acceptance_3bar | 6 | 3449 | 0.866 | 0.875 | 0.811 | 0.030 | 21.1% | 13.7% | 15.4% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.vah_touch.resistance_break_acceptance_3bar | 2020 | 3073 | 4.5% | 0.898 | 0.955 | 0.955 | 308 | 20.1% |
| at_fire | all | label.vah_touch.resistance_break_acceptance_3bar | 2021 | 3093 | 4.7% | 0.901 | 0.953 | 0.953 | 310 | 21.3% |
| at_fire | all | label.vah_touch.resistance_break_acceptance_3bar | 2022 | 3075 | 5.8% | 0.898 | 0.942 | 0.942 | 308 | 25.6% |
| at_fire | all | label.vah_touch.resistance_break_acceptance_3bar | 2023 | 3076 | 4.3% | 0.904 | 0.957 | 0.957 | 308 | 22.4% |
| at_fire | all | label.vah_touch.resistance_break_acceptance_3bar | 2024 | 3081 | 4.2% | 0.913 | 0.958 | 0.958 | 309 | 23.6% |
| at_fire | all | label.vah_touch.resistance_break_acceptance_3bar | 2025 | 3060 | 5.0% | 0.911 | 0.950 | 0.950 | 306 | 25.2% |
| at_fire | all | label.vah_touch.resistance_rejection_3bar | 2020 | 3073 | 5.6% | 0.905 | 0.943 | 0.944 | 308 | 26.3% |
| at_fire | all | label.vah_touch.resistance_rejection_3bar | 2021 | 3093 | 4.6% | 0.924 | 0.953 | 0.954 | 310 | 24.8% |
| at_fire | all | label.vah_touch.resistance_rejection_3bar | 2022 | 3075 | 4.4% | 0.897 | 0.955 | 0.956 | 308 | 21.1% |
| at_fire | all | label.vah_touch.resistance_rejection_3bar | 2023 | 3076 | 5.0% | 0.903 | 0.950 | 0.950 | 308 | 23.1% |
| at_fire | all | label.vah_touch.resistance_rejection_3bar | 2024 | 3081 | 4.2% | 0.916 | 0.958 | 0.958 | 309 | 23.9% |
| at_fire | all | label.vah_touch.resistance_rejection_3bar | 2025 | 3060 | 4.6% | 0.901 | 0.955 | 0.954 | 306 | 23.9% |
| at_fire | all | label.val_touch.support_break_acceptance_3bar | 2020 | 3073 | 5.1% | 0.840 | 0.949 | 0.949 | 308 | 15.9% |
| at_fire | all | label.val_touch.support_break_acceptance_3bar | 2021 | 3093 | 5.9% | 0.866 | 0.941 | 0.941 | 310 | 19.7% |
| at_fire | all | label.val_touch.support_break_acceptance_3bar | 2022 | 3075 | 5.2% | 0.892 | 0.948 | 0.948 | 308 | 24.4% |
| at_fire | all | label.val_touch.support_break_acceptance_3bar | 2023 | 3076 | 5.9% | 0.876 | 0.941 | 0.941 | 308 | 21.4% |
| at_fire | all | label.val_touch.support_break_acceptance_3bar | 2024 | 3081 | 6.8% | 0.860 | 0.932 | 0.932 | 309 | 24.3% |
| at_fire | all | label.val_touch.support_break_acceptance_3bar | 2025 | 3060 | 5.2% | 0.891 | 0.948 | 0.948 | 306 | 23.5% |
| at_fire | balanced | label.vah_touch.resistance_break_acceptance_3bar | 2020 | 1718 | 4.8% | 0.888 | 0.952 | 0.952 | 172 | 20.3% |
| at_fire | balanced | label.vah_touch.resistance_break_acceptance_3bar | 2021 | 1666 | 5.0% | 0.902 | 0.948 | 0.950 | 167 | 22.2% |
| at_fire | balanced | label.vah_touch.resistance_break_acceptance_3bar | 2022 | 1619 | 6.9% | 0.882 | 0.931 | 0.931 | 162 | 22.8% |
| at_fire | balanced | label.vah_touch.resistance_break_acceptance_3bar | 2023 | 1677 | 4.5% | 0.891 | 0.956 | 0.955 | 168 | 21.4% |
| at_fire | balanced | label.vah_touch.resistance_break_acceptance_3bar | 2024 | 1734 | 5.0% | 0.899 | 0.950 | 0.950 | 174 | 24.1% |
| at_fire | balanced | label.vah_touch.resistance_break_acceptance_3bar | 2025 | 1641 | 5.2% | 0.895 | 0.947 | 0.948 | 165 | 24.8% |
| at_fire | balanced | label.vah_touch.resistance_rejection_3bar | 2020 | 1718 | 6.1% | 0.897 | 0.938 | 0.939 | 172 | 26.7% |
| at_fire | balanced | label.vah_touch.resistance_rejection_3bar | 2021 | 1666 | 5.2% | 0.906 | 0.950 | 0.948 | 167 | 25.7% |
| at_fire | balanced | label.vah_touch.resistance_rejection_3bar | 2022 | 1619 | 5.4% | 0.895 | 0.944 | 0.946 | 162 | 19.8% |
| at_fire | balanced | label.vah_touch.resistance_rejection_3bar | 2023 | 1677 | 5.7% | 0.896 | 0.941 | 0.943 | 168 | 23.2% |
| at_fire | balanced | label.vah_touch.resistance_rejection_3bar | 2024 | 1734 | 5.1% | 0.899 | 0.949 | 0.949 | 174 | 24.7% |
| at_fire | balanced | label.vah_touch.resistance_rejection_3bar | 2025 | 1641 | 4.6% | 0.887 | 0.954 | 0.954 | 165 | 21.2% |
| at_fire | buying | label.vah_touch.resistance_break_acceptance_3bar | 2020 | 852 | 5.0% | 0.897 | 0.945 | 0.950 | 86 | 22.1% |
| at_fire | buying | label.vah_touch.resistance_break_acceptance_3bar | 2021 | 899 | 4.4% | 0.930 | 0.956 | 0.956 | 90 | 26.7% |
| at_fire | buying | label.vah_touch.resistance_break_acceptance_3bar | 2022 | 722 | 5.3% | 0.886 | 0.947 | 0.947 | 73 | 21.9% |
| at_fire | buying | label.vah_touch.resistance_break_acceptance_3bar | 2023 | 782 | 4.6% | 0.912 | 0.954 | 0.954 | 79 | 22.8% |
| at_fire | buying | label.vah_touch.resistance_break_acceptance_3bar | 2024 | 808 | 3.6% | 0.923 | 0.960 | 0.964 | 81 | 21.0% |
| at_fire | buying | label.vah_touch.resistance_break_acceptance_3bar | 2025 | 891 | 5.3% | 0.916 | 0.947 | 0.947 | 90 | 25.6% |
| at_fire | buying | label.vah_touch.resistance_rejection_3bar | 2020 | 852 | 5.6% | 0.899 | 0.944 | 0.944 | 86 | 25.6% |
| at_fire | buying | label.vah_touch.resistance_rejection_3bar | 2021 | 899 | 5.0% | 0.921 | 0.949 | 0.950 | 90 | 26.7% |
| at_fire | buying | label.vah_touch.resistance_rejection_3bar | 2022 | 722 | 4.6% | 0.859 | 0.954 | 0.954 | 73 | 17.8% |
| at_fire | buying | label.vah_touch.resistance_rejection_3bar | 2023 | 782 | 6.1% | 0.870 | 0.939 | 0.939 | 79 | 25.3% |
| at_fire | buying | label.vah_touch.resistance_rejection_3bar | 2024 | 808 | 4.3% | 0.909 | 0.957 | 0.957 | 81 | 23.5% |
| at_fire | buying | label.vah_touch.resistance_rejection_3bar | 2025 | 891 | 5.8% | 0.915 | 0.941 | 0.942 | 90 | 30.0% |
| at_fire | buying | label.vwap_touch.resistance_break_acceptance_3bar | 2020 | 852 | 6.3% | 0.879 | 0.935 | 0.937 | 86 | 26.7% |
| at_fire | buying | label.vwap_touch.resistance_break_acceptance_3bar | 2021 | 899 | 6.3% | 0.909 | 0.937 | 0.937 | 90 | 30.0% |
| at_fire | buying | label.vwap_touch.resistance_break_acceptance_3bar | 2022 | 722 | 7.8% | 0.885 | 0.921 | 0.922 | 73 | 26.0% |
| at_fire | buying | label.vwap_touch.resistance_break_acceptance_3bar | 2023 | 782 | 4.9% | 0.867 | 0.951 | 0.951 | 79 | 20.3% |
| at_fire | buying | label.vwap_touch.resistance_break_acceptance_3bar | 2024 | 808 | 5.6% | 0.891 | 0.944 | 0.944 | 81 | 22.2% |
| at_fire | buying | label.vwap_touch.resistance_break_acceptance_3bar | 2025 | 891 | 6.8% | 0.880 | 0.930 | 0.932 | 90 | 18.9% |
| at_fire | buying | label.vwap_touch.resistance_rejection_3bar | 2020 | 852 | 6.8% | 0.882 | 0.932 | 0.932 | 86 | 22.1% |
| at_fire | buying | label.vwap_touch.resistance_rejection_3bar | 2021 | 899 | 7.0% | 0.902 | 0.932 | 0.930 | 90 | 31.1% |
| at_fire | buying | label.vwap_touch.resistance_rejection_3bar | 2022 | 722 | 5.4% | 0.818 | 0.943 | 0.946 | 73 | 16.4% |
| at_fire | buying | label.vwap_touch.resistance_rejection_3bar | 2023 | 782 | 8.4% | 0.889 | 0.909 | 0.916 | 79 | 25.3% |
| at_fire | buying | label.vwap_touch.resistance_rejection_3bar | 2024 | 808 | 5.1% | 0.930 | 0.949 | 0.949 | 81 | 29.6% |
| at_fire | buying | label.vwap_touch.resistance_rejection_3bar | 2025 | 891 | 6.4% | 0.894 | 0.934 | 0.936 | 90 | 27.8% |
| at_fire | selling | label.vah_touch.resistance_break_acceptance_3bar | 2020 | 503 | 2.6% | 0.872 | 0.974 | 0.974 | 51 | 11.8% |
| at_fire | selling | label.vah_touch.resistance_break_acceptance_3bar | 2021 | 528 | 4.0% | 0.914 | 0.960 | 0.960 | 53 | 24.5% |
| at_fire | selling | label.vah_touch.resistance_break_acceptance_3bar | 2022 | 734 | 4.0% | 0.890 | 0.960 | 0.960 | 74 | 21.6% |
| at_fire | selling | label.vah_touch.resistance_break_acceptance_3bar | 2023 | 617 | 3.2% | 0.897 | 0.968 | 0.968 | 62 | 21.0% |
| at_fire | selling | label.vah_touch.resistance_break_acceptance_3bar | 2024 | 539 | 2.6% | 0.897 | 0.974 | 0.974 | 54 | 13.0% |
| at_fire | selling | label.vah_touch.resistance_break_acceptance_3bar | 2025 | 528 | 3.6% | 0.940 | 0.964 | 0.964 | 53 | 24.5% |
| at_fire | selling | label.val_touch.support_break_acceptance_3bar | 2020 | 503 | 4.8% | 0.811 | 0.952 | 0.952 | 51 | 13.7% |
| at_fire | selling | label.val_touch.support_break_acceptance_3bar | 2021 | 528 | 6.4% | 0.848 | 0.936 | 0.936 | 53 | 17.0% |
| at_fire | selling | label.val_touch.support_break_acceptance_3bar | 2022 | 734 | 6.5% | 0.870 | 0.935 | 0.935 | 74 | 23.0% |
| at_fire | selling | label.val_touch.support_break_acceptance_3bar | 2023 | 617 | 4.9% | 0.879 | 0.951 | 0.951 | 62 | 22.6% |
| at_fire | selling | label.val_touch.support_break_acceptance_3bar | 2024 | 539 | 7.2% | 0.892 | 0.926 | 0.928 | 54 | 31.5% |
| at_fire | selling | label.val_touch.support_break_acceptance_3bar | 2025 | 528 | 4.2% | 0.897 | 0.956 | 0.958 | 53 | 18.9% |
| at_fire | selling | label.vwap_touch.support_break_acceptance_3bar | 2020 | 503 | 7.6% | 0.853 | 0.922 | 0.924 | 51 | 25.5% |
| at_fire | selling | label.vwap_touch.support_break_acceptance_3bar | 2021 | 528 | 8.0% | 0.879 | 0.920 | 0.920 | 53 | 28.3% |
| at_fire | selling | label.vwap_touch.support_break_acceptance_3bar | 2022 | 734 | 8.9% | 0.877 | 0.911 | 0.911 | 74 | 32.4% |
| at_fire | selling | label.vwap_touch.support_break_acceptance_3bar | 2023 | 617 | 8.8% | 0.867 | 0.912 | 0.912 | 62 | 24.2% |
| at_fire | selling | label.vwap_touch.support_break_acceptance_3bar | 2024 | 539 | 8.3% | 0.889 | 0.913 | 0.917 | 54 | 40.7% |
| at_fire | selling | label.vwap_touch.support_break_acceptance_3bar | 2025 | 528 | 6.4% | 0.866 | 0.938 | 0.936 | 53 | 20.8% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
