# ML snapshot walk-forward validation

_Generated `2026-05-13T23:05:26.800171+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots_xctx_fvggeom.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots_xctx_fvggeom.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshot_leaderboard_xctx_fvggeom.parquet`
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
| C:\Users\benbr\AppData\Local\Temp\fvg_walk_forward_fvggeom_summary_itr.csv | candidate summary CSV |
| C:\Users\benbr\AppData\Local\Temp\fvg_walk_forward_fvggeom_summary_itr.parquet | candidate summary parquet |
| C:\Users\benbr\AppData\Local\Temp\fvg_walk_forward_fvggeom_folds_itr.csv | per-fold CSV |
| C:\Users\benbr\AppData\Local\Temp\fvg_walk_forward_fvggeom_folds_itr.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 209339 |
| schema_feature_columns | 1256 |
| schema_label_columns | 67 |
| folds_attempted | 48 |
| folds_ok | 48 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | bearish | label.mitigation.fully_filled | 6 | 53165 | 0.781 | 0.788 | 0.751 | 0.015 | 95.5% | 94.6% | 16.7% |
| at_fire | all | label.mitigation.fully_filled | 6 | 116366 | 0.780 | 0.787 | 0.750 | 0.015 | 94.6% | 93.2% | 16.9% |
| at_fire | bullish | label.mitigation.fully_filled | 6 | 63201 | 0.772 | 0.781 | 0.737 | 0.025 | 94.1% | 93.1% | 17.2% |
| at_fire | all | label.mitigation.mid_filled | 6 | 116366 | 0.768 | 0.774 | 0.738 | 0.016 | 95.3% | 93.2% | 13.8% |
| at_fire | bearish | label.mitigation.mid_filled | 6 | 53165 | 0.766 | 0.770 | 0.743 | 0.011 | 95.6% | 94.5% | 13.1% |
| at_fire | bullish | label.mitigation.mid_filled | 6 | 63201 | 0.762 | 0.769 | 0.724 | 0.029 | 95.6% | 93.6% | 14.8% |
| at_fire | bullish | label.mitigation.tapped | 6 | 63201 | 0.753 | 0.760 | 0.715 | 0.029 | 96.8% | 94.9% | 11.1% |
| at_fire | all | label.mitigation.closed_through | 6 | 116366 | 0.750 | 0.756 | 0.714 | 0.017 | 88.9% | 86.3% | 20.1% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.mitigation.closed_through | 2020 | 19438 | 67.5% | 0.714 | 0.730 | 0.675 | 1944 | 86.3% |
| at_fire | all | label.mitigation.closed_through | 2021 | 19137 | 68.4% | 0.746 | 0.745 | 0.684 | 1914 | 89.6% |
| at_fire | all | label.mitigation.closed_through | 2022 | 20042 | 69.3% | 0.753 | 0.761 | 0.693 | 2005 | 88.7% |
| at_fire | all | label.mitigation.closed_through | 2023 | 18931 | 69.3% | 0.764 | 0.761 | 0.693 | 1894 | 89.0% |
| at_fire | all | label.mitigation.closed_through | 2024 | 19308 | 68.6% | 0.763 | 0.749 | 0.686 | 1931 | 89.8% |
| at_fire | all | label.mitigation.closed_through | 2025 | 19510 | 69.3% | 0.759 | 0.758 | 0.693 | 1951 | 89.9% |
| at_fire | all | label.mitigation.fully_filled | 2020 | 19438 | 76.9% | 0.750 | 0.805 | 0.769 | 1944 | 93.2% |
| at_fire | all | label.mitigation.fully_filled | 2021 | 19137 | 77.3% | 0.771 | 0.807 | 0.773 | 1914 | 94.3% |
| at_fire | all | label.mitigation.fully_filled | 2022 | 20042 | 77.9% | 0.787 | 0.818 | 0.779 | 2005 | 94.7% |
| at_fire | all | label.mitigation.fully_filled | 2023 | 18931 | 78.5% | 0.794 | 0.820 | 0.785 | 1894 | 95.7% |
| at_fire | all | label.mitigation.fully_filled | 2024 | 19308 | 77.7% | 0.790 | 0.811 | 0.777 | 1931 | 95.0% |
| at_fire | all | label.mitigation.fully_filled | 2025 | 19510 | 78.1% | 0.786 | 0.816 | 0.781 | 1951 | 94.8% |
| at_fire | all | label.mitigation.mid_filled | 2020 | 19438 | 80.9% | 0.738 | 0.832 | 0.809 | 1944 | 93.2% |
| at_fire | all | label.mitigation.mid_filled | 2021 | 19137 | 81.3% | 0.758 | 0.829 | 0.813 | 1914 | 95.3% |
| at_fire | all | label.mitigation.mid_filled | 2022 | 20042 | 81.8% | 0.781 | 0.841 | 0.818 | 2005 | 95.8% |
| at_fire | all | label.mitigation.mid_filled | 2023 | 18931 | 82.1% | 0.783 | 0.841 | 0.821 | 1894 | 96.3% |
| at_fire | all | label.mitigation.mid_filled | 2024 | 19308 | 81.4% | 0.775 | 0.832 | 0.814 | 1931 | 96.1% |
| at_fire | all | label.mitigation.mid_filled | 2025 | 19510 | 81.8% | 0.773 | 0.837 | 0.818 | 1951 | 95.3% |
| at_fire | bearish | label.mitigation.fully_filled | 2020 | 8633 | 79.5% | 0.751 | 0.821 | 0.795 | 864 | 94.9% |
| at_fire | bearish | label.mitigation.fully_filled | 2021 | 8366 | 79.3% | 0.790 | 0.827 | 0.793 | 837 | 97.0% |
| at_fire | bearish | label.mitigation.fully_filled | 2022 | 9907 | 77.0% | 0.773 | 0.807 | 0.770 | 991 | 94.6% |
| at_fire | bearish | label.mitigation.fully_filled | 2023 | 8819 | 79.8% | 0.793 | 0.830 | 0.798 | 882 | 95.7% |
| at_fire | bearish | label.mitigation.fully_filled | 2024 | 8665 | 79.0% | 0.790 | 0.824 | 0.790 | 867 | 95.6% |
| at_fire | bearish | label.mitigation.fully_filled | 2025 | 8775 | 78.6% | 0.787 | 0.825 | 0.786 | 878 | 95.4% |
| at_fire | bearish | label.mitigation.mid_filled | 2020 | 8633 | 83.2% | 0.743 | 0.844 | 0.832 | 864 | 95.3% |
| at_fire | bearish | label.mitigation.mid_filled | 2021 | 8366 | 83.0% | 0.774 | 0.845 | 0.830 | 837 | 95.9% |
| at_fire | bearish | label.mitigation.mid_filled | 2022 | 9907 | 80.7% | 0.763 | 0.830 | 0.807 | 991 | 97.2% |
| at_fire | bearish | label.mitigation.mid_filled | 2023 | 8819 | 83.3% | 0.777 | 0.849 | 0.833 | 882 | 95.8% |
| at_fire | bearish | label.mitigation.mid_filled | 2024 | 8665 | 82.6% | 0.769 | 0.838 | 0.826 | 867 | 94.5% |
| at_fire | bearish | label.mitigation.mid_filled | 2025 | 8775 | 82.4% | 0.770 | 0.837 | 0.824 | 878 | 95.1% |
| at_fire | bullish | label.mitigation.fully_filled | 2020 | 10805 | 74.8% | 0.737 | 0.792 | 0.748 | 1081 | 93.2% |
| at_fire | bullish | label.mitigation.fully_filled | 2021 | 10771 | 75.7% | 0.738 | 0.786 | 0.757 | 1078 | 93.1% |
| at_fire | bullish | label.mitigation.fully_filled | 2022 | 10135 | 78.8% | 0.801 | 0.828 | 0.788 | 1014 | 95.0% |
| at_fire | bullish | label.mitigation.fully_filled | 2023 | 10112 | 77.3% | 0.793 | 0.813 | 0.773 | 1012 | 95.8% |
| at_fire | bullish | label.mitigation.fully_filled | 2024 | 10643 | 76.7% | 0.781 | 0.798 | 0.767 | 1065 | 93.8% |
| at_fire | bullish | label.mitigation.fully_filled | 2025 | 10735 | 77.7% | 0.781 | 0.809 | 0.777 | 1074 | 93.6% |
| at_fire | bullish | label.mitigation.mid_filled | 2020 | 10805 | 79.1% | 0.725 | 0.820 | 0.791 | 1081 | 94.5% |
| at_fire | bullish | label.mitigation.mid_filled | 2021 | 10771 | 79.9% | 0.724 | 0.812 | 0.799 | 1078 | 93.6% |
| at_fire | bullish | label.mitigation.mid_filled | 2022 | 10135 | 82.8% | 0.800 | 0.855 | 0.828 | 1014 | 96.4% |
| at_fire | bullish | label.mitigation.mid_filled | 2023 | 10112 | 80.9% | 0.785 | 0.828 | 0.809 | 1012 | 97.4% |
| at_fire | bullish | label.mitigation.mid_filled | 2024 | 10643 | 80.4% | 0.770 | 0.826 | 0.804 | 1065 | 95.9% |
| at_fire | bullish | label.mitigation.mid_filled | 2025 | 10735 | 81.3% | 0.767 | 0.834 | 0.813 | 1074 | 95.5% |
| at_fire | bullish | label.mitigation.tapped | 2020 | 10805 | 84.1% | 0.715 | 0.847 | 0.841 | 1081 | 94.9% |
| at_fire | bullish | label.mitigation.tapped | 2021 | 10771 | 84.9% | 0.719 | 0.852 | 0.849 | 1078 | 96.5% |
| at_fire | bullish | label.mitigation.tapped | 2022 | 10135 | 87.1% | 0.799 | 0.877 | 0.871 | 1014 | 97.1% |
| at_fire | bullish | label.mitigation.tapped | 2023 | 10112 | 85.9% | 0.762 | 0.862 | 0.859 | 1012 | 98.0% |
| at_fire | bullish | label.mitigation.tapped | 2024 | 10643 | 85.9% | 0.760 | 0.862 | 0.859 | 1065 | 98.0% |
| at_fire | bullish | label.mitigation.tapped | 2025 | 10735 | 86.7% | 0.761 | 0.869 | 0.867 | 1074 | 96.4% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
