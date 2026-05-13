# ML snapshot walk-forward validation

_Generated `2026-05-13T01:16:08.941106+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots_xctx_fvggeom.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots_xctx_fvggeom.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshot_leaderboard_xctx_fvggeom.parquet`
- Event type: `all`
- Candidates: `15`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025, 2026`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_walk_forward_fvggeom_summary.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_walk_forward_fvggeom_summary.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_walk_forward_fvggeom_folds.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_walk_forward_fvggeom_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 209339 |
| schema_feature_columns | 1088 |
| schema_label_columns | 67 |
| folds_attempted | 105 |
| folds_ok | 105 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.mitigation.fully_filled | 7 | 119080 | 0.773 | 0.788 | 0.721 | 0.025 | 93.8% | 86.4% | 16.4% |
| at_fire | bullish | label.mitigation.fully_filled | 7 | 64609 | 0.771 | 0.780 | 0.736 | 0.023 | 94.2% | 92.7% | 17.7% |
| at_fire | bearish | label.mitigation.fully_filled | 7 | 54471 | 0.769 | 0.788 | 0.686 | 0.036 | 93.8% | 82.4% | 15.3% |
| at_fire | bullish | label.mitigation.mid_filled | 7 | 64609 | 0.760 | 0.770 | 0.723 | 0.025 | 95.6% | 93.6% | 15.1% |
| at_fire | all | label.mitigation.mid_filled | 7 | 119080 | 0.758 | 0.775 | 0.692 | 0.031 | 94.6% | 88.6% | 13.4% |
| at_fire | bearish | label.mitigation.mid_filled | 7 | 54471 | 0.752 | 0.771 | 0.659 | 0.040 | 94.1% | 84.0% | 11.9% |
| at_fire | all | label.mitigation.closed_through | 7 | 119080 | 0.748 | 0.754 | 0.719 | 0.017 | 88.1% | 81.2% | 19.7% |
| at_fire | bullish | label.mitigation.tapped | 7 | 64609 | 0.748 | 0.759 | 0.712 | 0.029 | 96.6% | 94.9% | 10.8% |
| at_fire | bullish | label.mitigation.closed_through | 7 | 64609 | 0.743 | 0.749 | 0.707 | 0.020 | 88.4% | 84.0% | 21.5% |
| at_fire | bearish | label.mitigation.closed_through | 7 | 54471 | 0.743 | 0.753 | 0.701 | 0.023 | 88.5% | 80.2% | 18.2% |
| at_fire | all | label.mitigation.tapped | 7 | 119080 | 0.742 | 0.759 | 0.671 | 0.033 | 96.2% | 91.9% | 9.9% |
| at_fire | bearish | label.mitigation.tapped | 7 | 54471 | 0.733 | 0.756 | 0.625 | 0.046 | 95.4% | 86.3% | 8.3% |
| at_fire | bearish | label.mitigation.closed_inside | 7 | 54471 | 0.728 | 0.732 | 0.707 | 0.010 | 84.4% | 82.4% | 26.6% |
| at_fire | all | label.mitigation.closed_inside | 7 | 119080 | 0.727 | 0.729 | 0.715 | 0.008 | 82.9% | 76.5% | 26.6% |
| at_fire | bullish | label.mitigation.closed_inside | 7 | 64609 | 0.722 | 0.724 | 0.706 | 0.012 | 82.1% | 79.4% | 27.2% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.mitigation.closed_inside | 2020 | 19438 | 56.4% | 0.718 | 0.673 | 0.564 | 1944 | 81.9% |
| at_fire | all | label.mitigation.closed_inside | 2021 | 19137 | 57.8% | 0.728 | 0.674 | 0.578 | 1914 | 85.9% |
| at_fire | all | label.mitigation.closed_inside | 2022 | 20042 | 55.4% | 0.741 | 0.683 | 0.554 | 2005 | 84.3% |
| at_fire | all | label.mitigation.closed_inside | 2023 | 18931 | 56.9% | 0.729 | 0.682 | 0.569 | 1894 | 84.3% |
| at_fire | all | label.mitigation.closed_inside | 2024 | 19308 | 56.0% | 0.731 | 0.678 | 0.560 | 1931 | 83.2% |
| at_fire | all | label.mitigation.closed_inside | 2025 | 19510 | 55.9% | 0.730 | 0.677 | 0.559 | 1951 | 84.0% |
| at_fire | all | label.mitigation.closed_inside | 2026 | 2714 | 55.2% | 0.715 | 0.672 | 0.552 | 272 | 76.5% |
| at_fire | all | label.mitigation.closed_through | 2020 | 19438 | 67.5% | 0.719 | 0.732 | 0.675 | 1944 | 86.7% |
| at_fire | all | label.mitigation.closed_through | 2021 | 19137 | 68.4% | 0.750 | 0.746 | 0.684 | 1914 | 90.0% |
| at_fire | all | label.mitigation.closed_through | 2022 | 20042 | 69.3% | 0.754 | 0.761 | 0.693 | 2005 | 88.6% |
| at_fire | all | label.mitigation.closed_through | 2023 | 18931 | 69.3% | 0.766 | 0.760 | 0.693 | 1894 | 90.1% |
| at_fire | all | label.mitigation.closed_through | 2024 | 19308 | 68.6% | 0.764 | 0.749 | 0.686 | 1931 | 90.2% |
| at_fire | all | label.mitigation.closed_through | 2025 | 19510 | 69.3% | 0.759 | 0.758 | 0.693 | 1951 | 90.0% |
| at_fire | all | label.mitigation.closed_through | 2026 | 2714 | 66.3% | 0.725 | 0.732 | 0.663 | 272 | 81.2% |
| at_fire | all | label.mitigation.fully_filled | 2020 | 19438 | 76.9% | 0.754 | 0.804 | 0.769 | 1944 | 93.6% |
| at_fire | all | label.mitigation.fully_filled | 2021 | 19137 | 77.3% | 0.772 | 0.806 | 0.773 | 1914 | 94.8% |
| at_fire | all | label.mitigation.fully_filled | 2022 | 20042 | 77.9% | 0.788 | 0.819 | 0.779 | 2005 | 94.8% |
| at_fire | all | label.mitigation.fully_filled | 2023 | 18931 | 78.5% | 0.795 | 0.820 | 0.785 | 1894 | 95.8% |
| at_fire | all | label.mitigation.fully_filled | 2024 | 19308 | 77.7% | 0.790 | 0.811 | 0.777 | 1931 | 95.6% |
| at_fire | all | label.mitigation.fully_filled | 2025 | 19510 | 78.1% | 0.789 | 0.816 | 0.781 | 1951 | 95.4% |
| at_fire | all | label.mitigation.fully_filled | 2026 | 2714 | 75.3% | 0.721 | 0.790 | 0.753 | 272 | 86.4% |
| at_fire | all | label.mitigation.mid_filled | 2020 | 19438 | 80.9% | 0.738 | 0.832 | 0.809 | 1944 | 93.4% |
| at_fire | all | label.mitigation.mid_filled | 2021 | 19137 | 81.3% | 0.761 | 0.830 | 0.813 | 1914 | 95.7% |
| at_fire | all | label.mitigation.mid_filled | 2022 | 20042 | 81.8% | 0.785 | 0.842 | 0.818 | 2005 | 96.2% |
| at_fire | all | label.mitigation.mid_filled | 2023 | 18931 | 82.1% | 0.783 | 0.840 | 0.821 | 1894 | 96.7% |
| at_fire | all | label.mitigation.mid_filled | 2024 | 19308 | 81.4% | 0.775 | 0.832 | 0.814 | 1931 | 96.0% |
| at_fire | all | label.mitigation.mid_filled | 2025 | 19510 | 81.8% | 0.775 | 0.838 | 0.818 | 1951 | 95.7% |
| at_fire | all | label.mitigation.mid_filled | 2026 | 2714 | 79.3% | 0.692 | 0.807 | 0.793 | 272 | 88.6% |
| at_fire | all | label.mitigation.tapped | 2020 | 19438 | 85.8% | 0.721 | 0.863 | 0.858 | 1944 | 95.5% |
| at_fire | all | label.mitigation.tapped | 2021 | 19137 | 86.0% | 0.746 | 0.865 | 0.860 | 1914 | 97.1% |
| at_fire | all | label.mitigation.tapped | 2022 | 20042 | 86.4% | 0.772 | 0.869 | 0.864 | 2005 | 96.7% |
| at_fire | all | label.mitigation.tapped | 2023 | 18931 | 87.0% | 0.766 | 0.874 | 0.870 | 1894 | 97.6% |
| at_fire | all | label.mitigation.tapped | 2024 | 19308 | 86.3% | 0.763 | 0.867 | 0.863 | 1931 | 97.4% |
| at_fire | all | label.mitigation.tapped | 2025 | 19510 | 86.9% | 0.759 | 0.870 | 0.869 | 1951 | 97.5% |
| at_fire | all | label.mitigation.tapped | 2026 | 2714 | 85.8% | 0.671 | 0.859 | 0.858 | 272 | 91.9% |
| at_fire | bearish | label.mitigation.closed_inside | 2020 | 8633 | 59.2% | 0.721 | 0.685 | 0.592 | 864 | 83.3% |
| at_fire | bearish | label.mitigation.closed_inside | 2021 | 8366 | 60.7% | 0.739 | 0.692 | 0.607 | 837 | 88.4% |
| at_fire | bearish | label.mitigation.closed_inside | 2022 | 9907 | 55.7% | 0.731 | 0.676 | 0.557 | 991 | 83.0% |
| at_fire | bearish | label.mitigation.closed_inside | 2023 | 8819 | 59.0% | 0.732 | 0.688 | 0.590 | 882 | 84.6% |
| at_fire | bearish | label.mitigation.closed_inside | 2024 | 8665 | 58.9% | 0.734 | 0.688 | 0.589 | 867 | 85.7% |
| at_fire | bearish | label.mitigation.closed_inside | 2025 | 8775 | 56.5% | 0.735 | 0.684 | 0.565 | 878 | 83.6% |
| at_fire | bearish | label.mitigation.closed_inside | 2026 | 1306 | 54.9% | 0.707 | 0.665 | 0.549 | 131 | 82.4% |
| at_fire | bearish | label.mitigation.closed_through | 2020 | 8633 | 71.7% | 0.721 | 0.760 | 0.717 | 864 | 88.8% |
| at_fire | bearish | label.mitigation.closed_through | 2021 | 8366 | 72.5% | 0.762 | 0.780 | 0.725 | 837 | 91.5% |
| at_fire | bearish | label.mitigation.closed_through | 2022 | 9907 | 68.5% | 0.735 | 0.749 | 0.685 | 991 | 89.6% |
| at_fire | bearish | label.mitigation.closed_through | 2023 | 8819 | 71.7% | 0.753 | 0.776 | 0.717 | 882 | 88.2% |
| at_fire | bearish | label.mitigation.closed_through | 2024 | 8665 | 71.2% | 0.766 | 0.772 | 0.712 | 867 | 89.7% |
| at_fire | bearish | label.mitigation.closed_through | 2025 | 8775 | 71.3% | 0.763 | 0.770 | 0.713 | 878 | 91.6% |
| at_fire | bearish | label.mitigation.closed_through | 2026 | 1306 | 65.2% | 0.701 | 0.718 | 0.652 | 131 | 80.2% |
| at_fire | bearish | label.mitigation.fully_filled | 2020 | 8633 | 79.5% | 0.760 | 0.823 | 0.795 | 864 | 95.9% |
| at_fire | bearish | label.mitigation.fully_filled | 2021 | 8366 | 79.3% | 0.790 | 0.827 | 0.793 | 837 | 96.4% |
| at_fire | bearish | label.mitigation.fully_filled | 2022 | 9907 | 77.0% | 0.776 | 0.807 | 0.770 | 991 | 95.7% |
| at_fire | bearish | label.mitigation.fully_filled | 2023 | 8819 | 79.8% | 0.791 | 0.829 | 0.798 | 882 | 96.1% |
| at_fire | bearish | label.mitigation.fully_filled | 2024 | 8665 | 79.0% | 0.788 | 0.825 | 0.790 | 867 | 94.3% |
| at_fire | bearish | label.mitigation.fully_filled | 2025 | 8775 | 78.6% | 0.791 | 0.826 | 0.786 | 878 | 95.4% |
| at_fire | bearish | label.mitigation.fully_filled | 2026 | 1306 | 75.9% | 0.686 | 0.782 | 0.759 | 131 | 82.4% |
| at_fire | bearish | label.mitigation.mid_filled | 2020 | 8633 | 83.2% | 0.743 | 0.848 | 0.832 | 864 | 95.4% |
| at_fire | bearish | label.mitigation.mid_filled | 2021 | 8366 | 83.0% | 0.781 | 0.845 | 0.830 | 837 | 97.3% |
| at_fire | bearish | label.mitigation.mid_filled | 2022 | 9907 | 80.7% | 0.763 | 0.828 | 0.807 | 991 | 96.4% |
| at_fire | bearish | label.mitigation.mid_filled | 2023 | 8819 | 83.3% | 0.778 | 0.848 | 0.833 | 882 | 96.1% |
| at_fire | bearish | label.mitigation.mid_filled | 2024 | 8665 | 82.6% | 0.771 | 0.837 | 0.826 | 867 | 94.1% |
| at_fire | bearish | label.mitigation.mid_filled | 2025 | 8775 | 82.4% | 0.771 | 0.838 | 0.824 | 878 | 95.4% |
| at_fire | bearish | label.mitigation.mid_filled | 2026 | 1306 | 80.2% | 0.659 | 0.820 | 0.802 | 131 | 84.0% |
| at_fire | bearish | label.mitigation.tapped | 2020 | 8633 | 88.0% | 0.726 | 0.883 | 0.880 | 864 | 96.4% |
| at_fire | bearish | label.mitigation.tapped | 2021 | 8366 | 87.5% | 0.759 | 0.876 | 0.875 | 837 | 98.4% |
| at_fire | bearish | label.mitigation.tapped | 2022 | 9907 | 85.6% | 0.738 | 0.857 | 0.856 | 991 | 95.2% |
| at_fire | bearish | label.mitigation.tapped | 2023 | 8819 | 88.2% | 0.759 | 0.884 | 0.882 | 882 | 97.3% |
| at_fire | bearish | label.mitigation.tapped | 2024 | 8665 | 86.9% | 0.768 | 0.871 | 0.869 | 867 | 97.3% |
| at_fire | bearish | label.mitigation.tapped | 2025 | 8775 | 87.2% | 0.756 | 0.872 | 0.872 | 878 | 96.6% |
| at_fire | bearish | label.mitigation.tapped | 2026 | 1306 | 86.1% | 0.625 | 0.861 | 0.861 | 131 | 86.3% |
| at_fire | bullish | label.mitigation.closed_inside | 2020 | 10805 | 54.2% | 0.707 | 0.653 | 0.542 | 1081 | 79.6% |
| at_fire | bullish | label.mitigation.closed_inside | 2021 | 10771 | 55.5% | 0.706 | 0.653 | 0.555 | 1078 | 83.1% |
| at_fire | bullish | label.mitigation.closed_inside | 2022 | 10135 | 55.1% | 0.744 | 0.686 | 0.551 | 1014 | 84.7% |
| at_fire | bullish | label.mitigation.closed_inside | 2023 | 10112 | 55.1% | 0.722 | 0.668 | 0.551 | 1012 | 84.3% |
| at_fire | bullish | label.mitigation.closed_inside | 2024 | 10643 | 53.7% | 0.725 | 0.668 | 0.537 | 1065 | 80.1% |
| at_fire | bullish | label.mitigation.closed_inside | 2025 | 10735 | 55.4% | 0.725 | 0.669 | 0.554 | 1074 | 83.5% |
| at_fire | bullish | label.mitigation.closed_inside | 2026 | 1408 | 55.4% | 0.724 | 0.675 | 0.554 | 141 | 79.4% |
| at_fire | bullish | label.mitigation.closed_through | 2020 | 10805 | 64.2% | 0.707 | 0.710 | 0.642 | 1081 | 84.0% |
| at_fire | bullish | label.mitigation.closed_through | 2021 | 10771 | 65.3% | 0.723 | 0.712 | 0.653 | 1078 | 85.8% |
| at_fire | bullish | label.mitigation.closed_through | 2022 | 10135 | 70.0% | 0.763 | 0.766 | 0.700 | 1014 | 89.3% |
| at_fire | bullish | label.mitigation.closed_through | 2023 | 10112 | 67.1% | 0.765 | 0.742 | 0.671 | 1012 | 91.2% |
| at_fire | bullish | label.mitigation.closed_through | 2024 | 10643 | 66.6% | 0.749 | 0.726 | 0.666 | 1065 | 87.6% |
| at_fire | bullish | label.mitigation.closed_through | 2025 | 10735 | 67.7% | 0.750 | 0.741 | 0.677 | 1074 | 89.5% |
| at_fire | bullish | label.mitigation.closed_through | 2026 | 1408 | 67.3% | 0.747 | 0.729 | 0.673 | 141 | 91.5% |
| at_fire | bullish | label.mitigation.fully_filled | 2020 | 10805 | 74.8% | 0.736 | 0.793 | 0.748 | 1081 | 93.1% |
| at_fire | bullish | label.mitigation.fully_filled | 2021 | 10771 | 75.7% | 0.743 | 0.786 | 0.757 | 1078 | 92.7% |
| at_fire | bullish | label.mitigation.fully_filled | 2022 | 10135 | 78.8% | 0.800 | 0.827 | 0.788 | 1014 | 95.3% |
| at_fire | bullish | label.mitigation.fully_filled | 2023 | 10112 | 77.3% | 0.793 | 0.813 | 0.773 | 1012 | 95.2% |
| at_fire | bullish | label.mitigation.fully_filled | 2024 | 10643 | 76.7% | 0.780 | 0.799 | 0.767 | 1065 | 93.9% |
| at_fire | bullish | label.mitigation.fully_filled | 2025 | 10735 | 77.7% | 0.781 | 0.808 | 0.777 | 1074 | 93.2% |
| at_fire | bullish | label.mitigation.fully_filled | 2026 | 1408 | 74.8% | 0.765 | 0.786 | 0.748 | 141 | 96.5% |
| at_fire | bullish | label.mitigation.mid_filled | 2020 | 10805 | 79.1% | 0.723 | 0.819 | 0.791 | 1081 | 93.6% |
| at_fire | bullish | label.mitigation.mid_filled | 2021 | 10771 | 79.9% | 0.733 | 0.813 | 0.799 | 1078 | 94.3% |
| at_fire | bullish | label.mitigation.mid_filled | 2022 | 10135 | 82.8% | 0.797 | 0.855 | 0.828 | 1014 | 95.9% |
| at_fire | bullish | label.mitigation.mid_filled | 2023 | 10112 | 80.9% | 0.778 | 0.828 | 0.809 | 1012 | 96.9% |
| at_fire | bullish | label.mitigation.mid_filled | 2024 | 10643 | 80.4% | 0.770 | 0.825 | 0.804 | 1065 | 97.0% |
| at_fire | bullish | label.mitigation.mid_filled | 2025 | 10735 | 81.3% | 0.773 | 0.833 | 0.813 | 1074 | 96.2% |
| at_fire | bullish | label.mitigation.mid_filled | 2026 | 1408 | 78.5% | 0.747 | 0.803 | 0.785 | 141 | 95.0% |
| at_fire | bullish | label.mitigation.tapped | 2020 | 10805 | 84.1% | 0.715 | 0.846 | 0.841 | 1081 | 94.9% |
| at_fire | bullish | label.mitigation.tapped | 2021 | 10771 | 84.9% | 0.727 | 0.852 | 0.849 | 1078 | 95.7% |
| at_fire | bullish | label.mitigation.tapped | 2022 | 10135 | 87.1% | 0.799 | 0.875 | 0.871 | 1014 | 97.0% |
| at_fire | bullish | label.mitigation.tapped | 2023 | 10112 | 85.9% | 0.759 | 0.861 | 0.859 | 1012 | 96.9% |
| at_fire | bullish | label.mitigation.tapped | 2024 | 10643 | 85.9% | 0.759 | 0.862 | 0.859 | 1065 | 96.9% |
| at_fire | bullish | label.mitigation.tapped | 2025 | 10735 | 86.7% | 0.764 | 0.868 | 0.867 | 1074 | 97.4% |
| at_fire | bullish | label.mitigation.tapped | 2026 | 1408 | 85.6% | 0.712 | 0.854 | 0.856 | 141 | 97.2% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
