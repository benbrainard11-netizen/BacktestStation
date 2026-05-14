# ML snapshot walk-forward validation

_Generated `2026-05-14T04:19:13.007734+00:00`._

## Setup

- Matrix: `data\ml\anchors\itr_snapshots_xctx.parquet`
- Schema: `data\ml\anchors\itr_snapshots_xctx.schema.json`
- Leaderboard source: `data\ml\anchors\itr_snapshot_leaderboard_xctx.parquet`
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
| data\ml\anchors\itr_snapshot_walk_forward_summary_xctx.csv | candidate summary CSV |
| data\ml\anchors\itr_snapshot_walk_forward_summary_xctx.parquet | candidate summary parquet |
| data\ml\anchors\itr_snapshot_walk_forward_folds_xctx.csv | per-fold CSV |
| data\ml\anchors\itr_snapshot_walk_forward_folds_xctx.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 36095 |
| schema_feature_columns | 899 |
| schema_label_columns | 59 |
| folds_attempted | 72 |
| folds_ok | 72 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 6 | 10250 | 0.794 | 0.806 | 0.753 | 0.022 | 74.2% | 64.8% | 43.5% |
| at_fire | all | label.next_interval.range_expanded_2x_interval | 6 | 19190 | 0.791 | 0.800 | 0.712 | 0.043 | 37.4% | 29.5% | 27.3% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 6 | 19190 | 0.789 | 0.798 | 0.757 | 0.022 | 74.4% | 63.8% | 44.6% |
| at_fire | bearish | label.next_interval.range_expanded_2x_interval | 6 | 8867 | 0.786 | 0.789 | 0.730 | 0.039 | 35.1% | 22.9% | 24.9% |
| at_fire | bullish | label.next_interval.range_expanded_2x_interval | 6 | 10250 | 0.783 | 0.798 | 0.685 | 0.045 | 37.0% | 32.4% | 27.1% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 6 | 8867 | 0.776 | 0.785 | 0.717 | 0.033 | 69.2% | 54.5% | 40.5% |
| at_fire | bullish | label.next_interval.range_expanded_1x_interval | 6 | 10250 | 0.771 | 0.775 | 0.719 | 0.027 | 85.6% | 77.7% | 37.8% |
| at_fire | all | label.next_interval.range_expanded_1x_interval | 6 | 19190 | 0.769 | 0.780 | 0.723 | 0.029 | 86.4% | 79.9% | 37.5% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 6 | 10250 | 0.767 | 0.774 | 0.713 | 0.030 | 72.4% | 62.6% | 40.9% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 6 | 19190 | 0.766 | 0.772 | 0.722 | 0.025 | 73.6% | 64.9% | 41.2% |
| at_fire | bearish | label.next_interval.range_expanded_1x_interval | 6 | 8867 | 0.761 | 0.763 | 0.712 | 0.031 | 84.8% | 78.3% | 34.7% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 6 | 8867 | 0.760 | 0.756 | 0.727 | 0.025 | 71.7% | 62.1% | 38.4% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_interval.compressed_range_0_75x | 2020 | 3190 | 30.2% | 0.761 | 0.750 | 0.698 | 319 | 71.2% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 2021 | 3225 | 28.3% | 0.757 | 0.742 | 0.717 | 323 | 63.8% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 2022 | 3192 | 29.0% | 0.808 | 0.772 | 0.710 | 320 | 75.3% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 2023 | 3199 | 29.3% | 0.798 | 0.773 | 0.707 | 320 | 78.8% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 2024 | 3204 | 31.1% | 0.813 | 0.777 | 0.689 | 321 | 82.6% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 2025 | 3180 | 30.7% | 0.798 | 0.764 | 0.693 | 318 | 74.8% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 2020 | 3190 | 31.0% | 0.722 | 0.706 | 0.690 | 319 | 64.9% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 2021 | 3225 | 31.1% | 0.749 | 0.731 | 0.689 | 323 | 69.3% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 2022 | 3192 | 32.6% | 0.800 | 0.755 | 0.674 | 320 | 79.7% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 2023 | 3199 | 33.1% | 0.767 | 0.734 | 0.669 | 320 | 75.3% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 2024 | 3204 | 34.4% | 0.782 | 0.733 | 0.656 | 321 | 76.3% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 2025 | 3180 | 32.4% | 0.776 | 0.747 | 0.676 | 318 | 76.1% |
| at_fire | all | label.next_interval.range_expanded_1x_interval | 2020 | 3190 | 47.2% | 0.723 | 0.666 | 0.528 | 319 | 79.9% |
| at_fire | all | label.next_interval.range_expanded_1x_interval | 2021 | 3225 | 48.3% | 0.737 | 0.685 | 0.517 | 323 | 84.5% |
| at_fire | all | label.next_interval.range_expanded_1x_interval | 2022 | 3192 | 50.8% | 0.800 | 0.723 | 0.492 | 320 | 91.9% |
| at_fire | all | label.next_interval.range_expanded_1x_interval | 2023 | 3199 | 49.8% | 0.784 | 0.703 | 0.502 | 320 | 89.1% |
| at_fire | all | label.next_interval.range_expanded_1x_interval | 2024 | 3204 | 49.3% | 0.794 | 0.713 | 0.507 | 321 | 85.0% |
| at_fire | all | label.next_interval.range_expanded_1x_interval | 2025 | 3180 | 48.0% | 0.776 | 0.702 | 0.520 | 318 | 88.1% |
| at_fire | all | label.next_interval.range_expanded_2x_interval | 2020 | 3190 | 9.7% | 0.712 | 0.908 | 0.903 | 319 | 29.5% |
| at_fire | all | label.next_interval.range_expanded_2x_interval | 2021 | 3225 | 9.1% | 0.784 | 0.915 | 0.909 | 323 | 32.8% |
| at_fire | all | label.next_interval.range_expanded_2x_interval | 2022 | 3192 | 9.5% | 0.821 | 0.913 | 0.905 | 320 | 38.8% |
| at_fire | all | label.next_interval.range_expanded_2x_interval | 2023 | 3199 | 9.9% | 0.843 | 0.908 | 0.901 | 320 | 42.2% |
| at_fire | all | label.next_interval.range_expanded_2x_interval | 2024 | 3204 | 11.0% | 0.816 | 0.904 | 0.890 | 321 | 43.0% |
| at_fire | all | label.next_interval.range_expanded_2x_interval | 2025 | 3180 | 11.2% | 0.772 | 0.897 | 0.888 | 318 | 38.1% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 2020 | 1392 | 30.1% | 0.753 | 0.749 | 0.699 | 140 | 68.6% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 2021 | 1426 | 25.7% | 0.717 | 0.738 | 0.743 | 143 | 54.5% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 2022 | 1633 | 28.6% | 0.796 | 0.764 | 0.714 | 164 | 69.5% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 2023 | 1487 | 28.6% | 0.805 | 0.766 | 0.714 | 149 | 73.8% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 2024 | 1463 | 30.8% | 0.810 | 0.775 | 0.692 | 147 | 78.9% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 2025 | 1466 | 28.4% | 0.773 | 0.765 | 0.716 | 147 | 70.1% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 2020 | 1392 | 31.0% | 0.727 | 0.708 | 0.690 | 140 | 62.1% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 2021 | 1426 | 31.5% | 0.738 | 0.722 | 0.685 | 143 | 63.6% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 2022 | 1633 | 33.6% | 0.783 | 0.742 | 0.664 | 164 | 81.1% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 2023 | 1487 | 34.5% | 0.800 | 0.740 | 0.655 | 149 | 77.2% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 2024 | 1463 | 35.7% | 0.757 | 0.712 | 0.643 | 147 | 70.1% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 2025 | 1466 | 33.9% | 0.755 | 0.722 | 0.661 | 147 | 76.2% |
| at_fire | bearish | label.next_interval.range_expanded_1x_interval | 2020 | 1392 | 46.7% | 0.736 | 0.665 | 0.467 | 140 | 82.1% |
| at_fire | bearish | label.next_interval.range_expanded_1x_interval | 2021 | 1426 | 49.9% | 0.712 | 0.654 | 0.499 | 143 | 78.3% |
| at_fire | bearish | label.next_interval.range_expanded_1x_interval | 2022 | 1633 | 51.6% | 0.788 | 0.710 | 0.516 | 164 | 91.5% |
| at_fire | bearish | label.next_interval.range_expanded_1x_interval | 2023 | 1487 | 51.3% | 0.803 | 0.720 | 0.513 | 149 | 87.9% |
| at_fire | bearish | label.next_interval.range_expanded_1x_interval | 2024 | 1463 | 50.8% | 0.774 | 0.711 | 0.508 | 147 | 83.7% |
| at_fire | bearish | label.next_interval.range_expanded_1x_interval | 2025 | 1466 | 49.9% | 0.752 | 0.685 | 0.499 | 147 | 85.0% |
| at_fire | bearish | label.next_interval.range_expanded_2x_interval | 2020 | 1392 | 8.4% | 0.730 | 0.915 | 0.916 | 140 | 22.9% |
| at_fire | bearish | label.next_interval.range_expanded_2x_interval | 2021 | 1426 | 9.3% | 0.787 | 0.912 | 0.907 | 143 | 31.5% |
| at_fire | bearish | label.next_interval.range_expanded_2x_interval | 2022 | 1633 | 8.9% | 0.810 | 0.916 | 0.911 | 164 | 37.8% |
| at_fire | bearish | label.next_interval.range_expanded_2x_interval | 2023 | 1487 | 11.2% | 0.849 | 0.902 | 0.888 | 149 | 43.0% |
| at_fire | bearish | label.next_interval.range_expanded_2x_interval | 2024 | 1463 | 11.4% | 0.790 | 0.900 | 0.886 | 147 | 39.5% |
| at_fire | bearish | label.next_interval.range_expanded_2x_interval | 2025 | 1466 | 12.1% | 0.747 | 0.885 | 0.879 | 147 | 36.1% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 2020 | 1789 | 30.2% | 0.753 | 0.741 | 0.698 | 179 | 67.6% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 2021 | 1786 | 30.3% | 0.774 | 0.736 | 0.697 | 179 | 64.8% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 2022 | 1547 | 29.7% | 0.807 | 0.772 | 0.703 | 155 | 75.5% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 2023 | 1697 | 30.1% | 0.804 | 0.775 | 0.699 | 170 | 78.8% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 2024 | 1723 | 31.6% | 0.810 | 0.768 | 0.684 | 173 | 79.2% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 2025 | 1708 | 32.8% | 0.813 | 0.746 | 0.672 | 171 | 79.5% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 2020 | 1789 | 30.9% | 0.713 | 0.720 | 0.691 | 179 | 62.6% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 2021 | 1786 | 30.9% | 0.761 | 0.734 | 0.691 | 179 | 73.7% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 2022 | 1547 | 31.4% | 0.796 | 0.769 | 0.686 | 155 | 76.1% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 2023 | 1697 | 31.8% | 0.749 | 0.720 | 0.682 | 170 | 66.5% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 2024 | 1723 | 33.0% | 0.798 | 0.748 | 0.670 | 173 | 79.2% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 2025 | 1708 | 30.9% | 0.787 | 0.761 | 0.691 | 171 | 76.0% |
| at_fire | bullish | label.next_interval.range_expanded_1x_interval | 2020 | 1789 | 47.4% | 0.719 | 0.665 | 0.526 | 179 | 77.7% |
| at_fire | bullish | label.next_interval.range_expanded_1x_interval | 2021 | 1786 | 47.0% | 0.762 | 0.695 | 0.530 | 179 | 84.4% |
| at_fire | bullish | label.next_interval.range_expanded_1x_interval | 2022 | 1547 | 49.8% | 0.786 | 0.707 | 0.502 | 155 | 92.3% |
| at_fire | bullish | label.next_interval.range_expanded_1x_interval | 2023 | 1697 | 48.4% | 0.763 | 0.685 | 0.516 | 170 | 88.2% |
| at_fire | bullish | label.next_interval.range_expanded_1x_interval | 2024 | 1723 | 47.9% | 0.799 | 0.717 | 0.521 | 173 | 86.1% |
| at_fire | bullish | label.next_interval.range_expanded_1x_interval | 2025 | 1708 | 46.1% | 0.795 | 0.721 | 0.539 | 171 | 84.8% |
| at_fire | bullish | label.next_interval.range_expanded_2x_interval | 2020 | 1789 | 10.5% | 0.685 | 0.903 | 0.895 | 179 | 33.0% |
| at_fire | bullish | label.next_interval.range_expanded_2x_interval | 2021 | 1786 | 8.9% | 0.797 | 0.917 | 0.911 | 179 | 32.4% |
| at_fire | bullish | label.next_interval.range_expanded_2x_interval | 2022 | 1547 | 10.1% | 0.799 | 0.908 | 0.899 | 155 | 38.1% |
| at_fire | bullish | label.next_interval.range_expanded_2x_interval | 2023 | 1697 | 8.7% | 0.794 | 0.915 | 0.913 | 170 | 36.5% |
| at_fire | bullish | label.next_interval.range_expanded_2x_interval | 2024 | 1723 | 10.8% | 0.826 | 0.907 | 0.892 | 173 | 46.8% |
| at_fire | bullish | label.next_interval.range_expanded_2x_interval | 2025 | 1708 | 10.2% | 0.799 | 0.902 | 0.898 | 171 | 35.1% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
