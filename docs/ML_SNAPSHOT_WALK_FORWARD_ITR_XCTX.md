# ML snapshot walk-forward validation

_Generated `2026-05-13T17:45:43.824121+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\itr_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\itr_snapshots_xctx.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\itr_snapshot_leaderboard_xctx.parquet`
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
| C:\Users\benbr\AppData\Local\Temp\itr_snapshot_walk_forward_summary_xctx.csv | candidate summary CSV |
| C:\Users\benbr\AppData\Local\Temp\itr_snapshot_walk_forward_summary_xctx.parquet | candidate summary parquet |
| C:\Users\benbr\AppData\Local\Temp\itr_snapshot_walk_forward_folds_xctx.csv | per-fold CSV |
| C:\Users\benbr\AppData\Local\Temp\itr_snapshot_walk_forward_folds_xctx.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 36095 |
| schema_feature_columns | 850 |
| schema_label_columns | 35 |
| folds_attempted | 48 |
| folds_ok | 48 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 6 | 10250 | 0.790 | 0.800 | 0.751 | 0.024 | 74.9% | 60.3% | 44.1% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 6 | 19190 | 0.786 | 0.797 | 0.755 | 0.022 | 73.2% | 63.2% | 43.4% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 6 | 8867 | 0.775 | 0.784 | 0.720 | 0.031 | 68.2% | 53.1% | 39.5% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 6 | 19190 | 0.766 | 0.773 | 0.717 | 0.026 | 73.6% | 62.7% | 41.1% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 6 | 10250 | 0.761 | 0.768 | 0.712 | 0.029 | 71.1% | 62.6% | 39.7% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 6 | 8867 | 0.760 | 0.760 | 0.719 | 0.027 | 73.5% | 65.7% | 40.2% |
| at_fire | all | label.next_interval.touched_interval_mid | 6 | 19190 | 0.747 | 0.752 | 0.702 | 0.021 | 86.1% | 76.5% | 44.0% |
| at_fire | bullish | label.next_interval.touched_interval_mid | 6 | 10250 | 0.724 | 0.736 | 0.658 | 0.035 | 80.0% | 65.9% | 40.3% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_interval.compressed_range_0_75x | 2020 | 3190 | 30.2% | 0.755 | 0.741 | 0.698 | 319 | 70.2% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 2021 | 3225 | 28.3% | 0.756 | 0.740 | 0.717 | 323 | 63.2% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 2022 | 3192 | 29.0% | 0.801 | 0.775 | 0.710 | 320 | 73.4% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 2023 | 3199 | 29.3% | 0.795 | 0.767 | 0.707 | 320 | 74.4% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 2024 | 3204 | 31.1% | 0.810 | 0.775 | 0.689 | 321 | 81.0% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 2025 | 3180 | 30.7% | 0.799 | 0.761 | 0.693 | 318 | 77.0% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 2020 | 3190 | 31.0% | 0.717 | 0.711 | 0.690 | 319 | 62.7% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 2021 | 3225 | 31.1% | 0.749 | 0.726 | 0.689 | 323 | 70.6% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 2022 | 3192 | 32.6% | 0.798 | 0.758 | 0.674 | 320 | 79.7% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 2023 | 3199 | 33.1% | 0.772 | 0.736 | 0.669 | 320 | 75.9% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 2024 | 3204 | 34.4% | 0.784 | 0.737 | 0.656 | 321 | 75.7% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 2025 | 3180 | 32.4% | 0.773 | 0.747 | 0.676 | 318 | 76.7% |
| at_fire | all | label.next_interval.touched_interval_mid | 2020 | 3190 | 40.7% | 0.702 | 0.672 | 0.593 | 319 | 76.5% |
| at_fire | all | label.next_interval.touched_interval_mid | 2021 | 3225 | 43.8% | 0.752 | 0.705 | 0.562 | 323 | 90.7% |
| at_fire | all | label.next_interval.touched_interval_mid | 2022 | 3192 | 40.2% | 0.748 | 0.706 | 0.598 | 320 | 88.8% |
| at_fire | all | label.next_interval.touched_interval_mid | 2023 | 3199 | 42.0% | 0.752 | 0.715 | 0.580 | 320 | 82.5% |
| at_fire | all | label.next_interval.touched_interval_mid | 2024 | 3204 | 41.7% | 0.766 | 0.720 | 0.583 | 321 | 90.0% |
| at_fire | all | label.next_interval.touched_interval_mid | 2025 | 3180 | 44.2% | 0.759 | 0.716 | 0.558 | 318 | 88.4% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 2020 | 1392 | 30.1% | 0.753 | 0.746 | 0.699 | 140 | 70.0% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 2021 | 1426 | 25.7% | 0.720 | 0.721 | 0.743 | 143 | 53.1% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 2022 | 1633 | 28.6% | 0.803 | 0.760 | 0.714 | 164 | 72.0% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 2023 | 1487 | 28.6% | 0.796 | 0.764 | 0.714 | 149 | 71.8% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 2024 | 1463 | 30.8% | 0.804 | 0.764 | 0.692 | 147 | 76.9% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 2025 | 1466 | 28.4% | 0.772 | 0.759 | 0.716 | 147 | 65.3% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 2020 | 1392 | 31.0% | 0.719 | 0.710 | 0.690 | 140 | 65.7% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 2021 | 1426 | 31.5% | 0.736 | 0.713 | 0.685 | 143 | 65.7% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 2022 | 1633 | 33.6% | 0.783 | 0.735 | 0.664 | 164 | 82.3% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 2023 | 1487 | 34.5% | 0.802 | 0.746 | 0.655 | 149 | 77.2% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 2024 | 1463 | 35.7% | 0.765 | 0.708 | 0.643 | 147 | 72.8% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 2025 | 1466 | 33.9% | 0.755 | 0.733 | 0.661 | 147 | 77.6% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 2020 | 1789 | 30.2% | 0.751 | 0.733 | 0.698 | 179 | 69.8% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 2021 | 1786 | 30.3% | 0.764 | 0.729 | 0.697 | 179 | 60.3% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 2022 | 1547 | 29.7% | 0.805 | 0.767 | 0.703 | 155 | 80.6% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 2023 | 1697 | 30.1% | 0.795 | 0.770 | 0.699 | 170 | 75.9% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 2024 | 1723 | 31.6% | 0.812 | 0.777 | 0.684 | 173 | 80.9% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 2025 | 1708 | 32.8% | 0.814 | 0.763 | 0.672 | 171 | 81.9% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 2020 | 1789 | 30.9% | 0.712 | 0.717 | 0.691 | 179 | 62.6% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 2021 | 1786 | 30.9% | 0.758 | 0.739 | 0.691 | 179 | 71.5% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 2022 | 1547 | 31.4% | 0.789 | 0.761 | 0.686 | 155 | 72.3% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 2023 | 1697 | 31.8% | 0.738 | 0.715 | 0.682 | 170 | 68.2% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 2024 | 1723 | 33.0% | 0.792 | 0.741 | 0.670 | 173 | 76.9% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 2025 | 1708 | 30.9% | 0.777 | 0.755 | 0.691 | 171 | 75.4% |
| at_fire | bullish | label.next_interval.touched_interval_mid | 2020 | 1789 | 38.7% | 0.658 | 0.651 | 0.613 | 179 | 65.9% |
| at_fire | bullish | label.next_interval.touched_interval_mid | 2021 | 1786 | 40.2% | 0.703 | 0.670 | 0.598 | 179 | 79.9% |
| at_fire | bullish | label.next_interval.touched_interval_mid | 2022 | 1547 | 38.8% | 0.720 | 0.695 | 0.612 | 155 | 80.0% |
| at_fire | bullish | label.next_interval.touched_interval_mid | 2023 | 1697 | 39.0% | 0.753 | 0.724 | 0.610 | 170 | 82.4% |
| at_fire | bullish | label.next_interval.touched_interval_mid | 2024 | 1723 | 40.1% | 0.756 | 0.719 | 0.599 | 173 | 89.0% |
| at_fire | bullish | label.next_interval.touched_interval_mid | 2025 | 1708 | 41.6% | 0.753 | 0.710 | 0.584 | 171 | 83.0% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
