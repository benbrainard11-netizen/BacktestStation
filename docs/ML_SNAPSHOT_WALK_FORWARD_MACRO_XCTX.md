# ML snapshot walk-forward validation

_Generated `2026-05-14T01:56:01.434906+00:00`._

## Setup

- Matrix: `data\ml\anchors\macro_event_snapshots_xctx.parquet`
- Schema: `data\ml\anchors\macro_event_snapshots_xctx.schema.json`
- Leaderboard source: `data\ml\anchors\macro_snapshot_leaderboard_xctx.parquet`
- Event type: `all`
- Candidates: `10`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\macro_snapshot_walk_forward_summary_xctx.csv | candidate summary CSV |
| data\ml\anchors\macro_snapshot_walk_forward_summary_xctx.parquet | candidate summary parquet |
| data\ml\anchors\macro_snapshot_walk_forward_folds_xctx.csv | per-fold CSV |
| data\ml\anchors\macro_snapshot_walk_forward_folds_xctx.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 18414 |
| schema_feature_columns | 878 |
| schema_label_columns | 372 |
| folds_attempted | 60 |
| folds_ok | 60 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_5m.range_expanded_2x_pre_15m | 6 | 8511 | 0.858 | 0.865 | 0.809 | 0.028 | 36.5% | 27.3% | 30.2% |
| at_fire | all | label.next_15m.range_expanded_2x_pre_60m | 6 | 8528 | 0.854 | 0.875 | 0.730 | 0.071 | 21.4% | 7.7% | 17.9% |
| at_fire | high | label.next_5m.range_expanded_2x_pre_15m | 6 | 4460 | 0.846 | 0.883 | 0.754 | 0.062 | 45.9% | 27.6% | 36.0% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_low | 6 | 4052 | 0.840 | 0.840 | 0.822 | 0.016 | 73.2% | 57.9% | 46.0% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_high | 6 | 4052 | 0.840 | 0.859 | 0.735 | 0.051 | 76.8% | 59.1% | 48.2% |
| at_fire | medium | label.next_15m.took_pre_60m_high | 6 | 4052 | 0.837 | 0.856 | 0.724 | 0.054 | 73.3% | 54.5% | 43.0% |
| at_fire | high | label.next_15m.range_expanded_2x_pre_60m | 6 | 4476 | 0.831 | 0.834 | 0.716 | 0.074 | 33.5% | 8.7% | 27.3% |
| at_fire | medium | label.next_15m.took_pre_60m_low | 6 | 4052 | 0.825 | 0.827 | 0.801 | 0.017 | 71.6% | 60.9% | 42.8% |
| at_fire | all | label.next_15m.one_sided_took_pre_60m_high | 6 | 8528 | 0.820 | 0.829 | 0.756 | 0.029 | 71.3% | 64.2% | 43.2% |
| at_fire | high | label.next_15m.swept_both_pre_60m_sides | 6 | 4476 | 0.763 | 0.775 | 0.627 | 0.086 | 23.7% | 13.1% | 18.4% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_15m.one_sided_took_pre_60m_high | 2020 | 1421 | 28.1% | 0.827 | 0.775 | 0.719 | 143 | 72.0% |
| at_fire | all | label.next_15m.one_sided_took_pre_60m_high | 2021 | 1482 | 29.8% | 0.827 | 0.771 | 0.702 | 149 | 67.1% |
| at_fire | all | label.next_15m.one_sided_took_pre_60m_high | 2022 | 1626 | 30.1% | 0.831 | 0.777 | 0.699 | 163 | 73.0% |
| at_fire | all | label.next_15m.one_sided_took_pre_60m_high | 2023 | 1650 | 24.1% | 0.844 | 0.813 | 0.759 | 165 | 76.4% |
| at_fire | all | label.next_15m.one_sided_took_pre_60m_high | 2024 | 1827 | 27.9% | 0.832 | 0.801 | 0.721 | 183 | 75.4% |
| at_fire | all | label.next_15m.one_sided_took_pre_60m_high | 2025 | 522 | 28.9% | 0.756 | 0.743 | 0.711 | 53 | 64.2% |
| at_fire | all | label.next_15m.range_expanded_2x_pre_60m | 2020 | 1421 | 2.6% | 0.730 | 0.974 | 0.974 | 143 | 7.7% |
| at_fire | all | label.next_15m.range_expanded_2x_pre_60m | 2021 | 1482 | 3.9% | 0.863 | 0.962 | 0.961 | 149 | 24.8% |
| at_fire | all | label.next_15m.range_expanded_2x_pre_60m | 2022 | 1626 | 5.4% | 0.893 | 0.946 | 0.946 | 163 | 31.9% |
| at_fire | all | label.next_15m.range_expanded_2x_pre_60m | 2023 | 1650 | 2.8% | 0.802 | 0.972 | 0.972 | 165 | 15.8% |
| at_fire | all | label.next_15m.range_expanded_2x_pre_60m | 2024 | 1827 | 3.1% | 0.950 | 0.981 | 0.969 | 183 | 25.7% |
| at_fire | all | label.next_15m.range_expanded_2x_pre_60m | 2025 | 522 | 3.4% | 0.886 | 0.964 | 0.966 | 53 | 22.6% |
| at_fire | all | label.next_5m.range_expanded_2x_pre_15m | 2020 | 1409 | 5.5% | 0.839 | 0.947 | 0.945 | 141 | 28.4% |
| at_fire | all | label.next_5m.range_expanded_2x_pre_15m | 2021 | 1479 | 7.0% | 0.878 | 0.933 | 0.930 | 148 | 39.9% |
| at_fire | all | label.next_5m.range_expanded_2x_pre_15m | 2022 | 1626 | 8.2% | 0.883 | 0.925 | 0.918 | 163 | 52.8% |
| at_fire | all | label.next_5m.range_expanded_2x_pre_15m | 2023 | 1650 | 6.9% | 0.809 | 0.934 | 0.931 | 165 | 27.3% |
| at_fire | all | label.next_5m.range_expanded_2x_pre_15m | 2024 | 1825 | 5.0% | 0.853 | 0.964 | 0.950 | 183 | 35.0% |
| at_fire | all | label.next_5m.range_expanded_2x_pre_15m | 2025 | 522 | 5.4% | 0.888 | 0.964 | 0.946 | 53 | 35.8% |
| at_fire | high | label.next_15m.range_expanded_2x_pre_60m | 2020 | 681 | 4.3% | 0.716 | 0.957 | 0.957 | 69 | 8.7% |
| at_fire | high | label.next_15m.range_expanded_2x_pre_60m | 2021 | 612 | 8.8% | 0.802 | 0.912 | 0.912 | 62 | 46.8% |
| at_fire | high | label.next_15m.range_expanded_2x_pre_60m | 2022 | 762 | 10.6% | 0.779 | 0.894 | 0.894 | 77 | 48.1% |
| at_fire | high | label.next_15m.range_expanded_2x_pre_60m | 2023 | 1044 | 3.8% | 0.866 | 0.962 | 0.962 | 105 | 24.8% |
| at_fire | high | label.next_15m.range_expanded_2x_pre_60m | 2024 | 1068 | 4.5% | 0.942 | 0.978 | 0.955 | 107 | 37.4% |
| at_fire | high | label.next_15m.range_expanded_2x_pre_60m | 2025 | 309 | 5.2% | 0.881 | 0.951 | 0.948 | 31 | 35.5% |
| at_fire | high | label.next_15m.swept_both_pre_60m_sides | 2020 | 681 | 4.8% | 0.713 | 0.947 | 0.952 | 69 | 17.4% |
| at_fire | high | label.next_15m.swept_both_pre_60m_sides | 2021 | 612 | 6.9% | 0.706 | 0.931 | 0.931 | 62 | 35.5% |
| at_fire | high | label.next_15m.swept_both_pre_60m_sides | 2022 | 762 | 8.0% | 0.848 | 0.920 | 0.920 | 77 | 46.8% |
| at_fire | high | label.next_15m.swept_both_pre_60m_sides | 2023 | 1044 | 4.2% | 0.627 | 0.957 | 0.958 | 105 | 13.3% |
| at_fire | high | label.next_15m.swept_both_pre_60m_sides | 2024 | 1068 | 4.1% | 0.836 | 0.959 | 0.959 | 107 | 13.1% |
| at_fire | high | label.next_15m.swept_both_pre_60m_sides | 2025 | 309 | 3.9% | 0.850 | 0.961 | 0.961 | 31 | 16.1% |
| at_fire | high | label.next_5m.range_expanded_2x_pre_15m | 2020 | 669 | 9.0% | 0.754 | 0.912 | 0.910 | 67 | 40.3% |
| at_fire | high | label.next_5m.range_expanded_2x_pre_15m | 2021 | 609 | 12.6% | 0.886 | 0.880 | 0.874 | 61 | 55.7% |
| at_fire | high | label.next_5m.range_expanded_2x_pre_15m | 2022 | 762 | 14.8% | 0.886 | 0.869 | 0.852 | 77 | 55.8% |
| at_fire | high | label.next_5m.range_expanded_2x_pre_15m | 2023 | 1044 | 9.0% | 0.765 | 0.907 | 0.910 | 105 | 27.6% |
| at_fire | high | label.next_5m.range_expanded_2x_pre_15m | 2024 | 1067 | 6.8% | 0.879 | 0.948 | 0.932 | 107 | 47.7% |
| at_fire | high | label.next_5m.range_expanded_2x_pre_15m | 2025 | 309 | 7.4% | 0.908 | 0.948 | 0.926 | 31 | 48.4% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_high | 2020 | 740 | 24.6% | 0.859 | 0.846 | 0.754 | 74 | 89.2% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_high | 2021 | 870 | 27.8% | 0.827 | 0.797 | 0.722 | 87 | 73.6% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_high | 2022 | 864 | 33.7% | 0.859 | 0.769 | 0.663 | 87 | 73.6% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_high | 2023 | 606 | 26.2% | 0.895 | 0.850 | 0.738 | 61 | 85.2% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_high | 2024 | 759 | 26.5% | 0.868 | 0.823 | 0.735 | 76 | 80.3% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_high | 2025 | 213 | 32.9% | 0.735 | 0.704 | 0.671 | 22 | 59.1% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_low | 2020 | 740 | 31.9% | 0.843 | 0.793 | 0.681 | 74 | 82.4% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_low | 2021 | 870 | 24.3% | 0.869 | 0.821 | 0.757 | 87 | 70.1% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_low | 2022 | 864 | 26.9% | 0.837 | 0.786 | 0.731 | 87 | 65.5% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_low | 2023 | 606 | 28.9% | 0.850 | 0.794 | 0.711 | 61 | 72.1% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_low | 2024 | 759 | 24.1% | 0.822 | 0.808 | 0.759 | 76 | 57.9% |
| at_fire | medium | label.next_15m.one_sided_took_pre_60m_low | 2025 | 213 | 27.2% | 0.823 | 0.803 | 0.728 | 22 | 90.9% |
| at_fire | medium | label.next_15m.took_pre_60m_high | 2020 | 740 | 27.3% | 0.869 | 0.820 | 0.727 | 74 | 85.1% |
| at_fire | medium | label.next_15m.took_pre_60m_high | 2021 | 870 | 29.2% | 0.824 | 0.793 | 0.708 | 87 | 70.1% |
| at_fire | medium | label.next_15m.took_pre_60m_high | 2022 | 864 | 34.0% | 0.858 | 0.775 | 0.660 | 87 | 77.0% |
| at_fire | medium | label.next_15m.took_pre_60m_high | 2023 | 606 | 27.4% | 0.891 | 0.848 | 0.726 | 61 | 73.8% |
| at_fire | medium | label.next_15m.took_pre_60m_high | 2024 | 759 | 28.1% | 0.853 | 0.814 | 0.719 | 76 | 78.9% |
| at_fire | medium | label.next_15m.took_pre_60m_high | 2025 | 213 | 35.7% | 0.724 | 0.695 | 0.643 | 22 | 54.5% |
| at_fire | medium | label.next_15m.took_pre_60m_low | 2020 | 740 | 34.6% | 0.810 | 0.770 | 0.654 | 74 | 77.0% |
| at_fire | medium | label.next_15m.took_pre_60m_low | 2021 | 870 | 25.6% | 0.855 | 0.813 | 0.744 | 87 | 74.7% |
| at_fire | medium | label.next_15m.took_pre_60m_low | 2022 | 864 | 27.2% | 0.830 | 0.792 | 0.728 | 87 | 60.9% |
| at_fire | medium | label.next_15m.took_pre_60m_low | 2023 | 606 | 30.0% | 0.833 | 0.795 | 0.700 | 61 | 68.9% |
| at_fire | medium | label.next_15m.took_pre_60m_low | 2024 | 759 | 25.7% | 0.824 | 0.791 | 0.743 | 76 | 61.8% |
| at_fire | medium | label.next_15m.took_pre_60m_low | 2025 | 213 | 30.0% | 0.801 | 0.784 | 0.700 | 22 | 86.4% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
