# ML snapshot walk-forward validation

_Generated `2026-05-12T14:55:09.558435+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshots.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshot_leaderboard.parquet`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_walk_forward_summary_base.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_walk_forward_summary_base.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_walk_forward_folds_base.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_walk_forward_folds_base.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 19414 |
| schema_feature_columns | 46 |
| schema_label_columns | 24 |
| folds_attempted | 48 |
| folds_ok | 48 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_period.took_parent_high | 6 | 10364 | 0.778 | 0.778 | 0.751 | 0.017 | 83.9% | 79.2% | 27.7% |
| at_fire | all | label.next_period.took_parent_low | 6 | 10364 | 0.754 | 0.750 | 0.730 | 0.022 | 75.6% | 66.5% | 31.3% |
| at_fire | bearish | label.next_period.took_parent_high | 6 | 4718 | 0.713 | 0.714 | 0.669 | 0.026 | 62.3% | 53.8% | 28.0% |
| at_fire | bullish | label.next_period.took_parent_low | 6 | 5622 | 0.702 | 0.710 | 0.617 | 0.052 | 57.1% | 45.6% | 28.5% |
| at_fire | all | label.next_period.thesis_confirmed | 6 | 10364 | 0.657 | 0.660 | 0.621 | 0.020 | 81.9% | 78.0% | 12.5% |
| at_fire | bullish | label.next_period.took_parent_high | 6 | 5622 | 0.648 | 0.647 | 0.621 | 0.023 | 83.4% | 77.0% | 8.8% |
| at_fire | bullish | label.next_period.thesis_confirmed | 6 | 5622 | 0.648 | 0.647 | 0.621 | 0.023 | 83.4% | 77.0% | 8.8% |
| at_fire | bearish | label.next_period.took_parent_low | 6 | 4718 | 0.635 | 0.645 | 0.591 | 0.027 | 76.5% | 61.3% | 13.7% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_period.thesis_confirmed | 2020 | 1724 | 70.9% | 0.670 | 0.716 | 0.709 | 173 | 80.3% |
| at_fire | all | label.next_period.thesis_confirmed | 2021 | 1743 | 68.4% | 0.673 | 0.695 | 0.684 | 175 | 84.0% |
| at_fire | all | label.next_period.thesis_confirmed | 2022 | 1722 | 71.1% | 0.621 | 0.696 | 0.711 | 173 | 79.8% |
| at_fire | all | label.next_period.thesis_confirmed | 2023 | 1728 | 72.3% | 0.648 | 0.730 | 0.723 | 173 | 81.5% |
| at_fire | all | label.next_period.thesis_confirmed | 2024 | 1728 | 67.8% | 0.650 | 0.679 | 0.678 | 173 | 78.0% |
| at_fire | all | label.next_period.thesis_confirmed | 2025 | 1719 | 66.0% | 0.679 | 0.671 | 0.660 | 172 | 87.8% |
| at_fire | all | label.next_period.took_parent_high | 2020 | 1724 | 58.3% | 0.807 | 0.747 | 0.583 | 173 | 79.2% |
| at_fire | all | label.next_period.took_parent_high | 2021 | 1743 | 59.7% | 0.775 | 0.721 | 0.597 | 175 | 86.3% |
| at_fire | all | label.next_period.took_parent_high | 2022 | 1722 | 49.6% | 0.771 | 0.702 | 0.496 | 173 | 80.9% |
| at_fire | all | label.next_period.took_parent_high | 2023 | 1728 | 56.2% | 0.782 | 0.726 | 0.562 | 173 | 83.8% |
| at_fire | all | label.next_period.took_parent_high | 2024 | 1728 | 57.0% | 0.783 | 0.720 | 0.570 | 173 | 87.9% |
| at_fire | all | label.next_period.took_parent_high | 2025 | 1719 | 56.5% | 0.751 | 0.695 | 0.565 | 172 | 85.5% |
| at_fire | all | label.next_period.took_parent_low | 2020 | 1724 | 41.1% | 0.732 | 0.701 | 0.589 | 173 | 72.8% |
| at_fire | all | label.next_period.took_parent_low | 2021 | 1743 | 40.3% | 0.764 | 0.707 | 0.597 | 175 | 70.9% |
| at_fire | all | label.next_period.took_parent_low | 2022 | 1722 | 53.8% | 0.754 | 0.681 | 0.462 | 173 | 85.0% |
| at_fire | all | label.next_period.took_parent_low | 2023 | 1728 | 45.5% | 0.795 | 0.733 | 0.545 | 173 | 80.9% |
| at_fire | all | label.next_period.took_parent_low | 2024 | 1728 | 42.9% | 0.746 | 0.683 | 0.571 | 173 | 66.5% |
| at_fire | all | label.next_period.took_parent_low | 2025 | 1719 | 42.4% | 0.730 | 0.678 | 0.576 | 172 | 77.3% |
| at_fire | bearish | label.next_period.took_parent_high | 2020 | 727 | 31.4% | 0.755 | 0.710 | 0.686 | 73 | 67.1% |
| at_fire | bearish | label.next_period.took_parent_high | 2021 | 741 | 38.2% | 0.698 | 0.677 | 0.618 | 75 | 68.0% |
| at_fire | bearish | label.next_period.took_parent_high | 2022 | 936 | 31.7% | 0.720 | 0.708 | 0.683 | 94 | 56.4% |
| at_fire | bearish | label.next_period.took_parent_high | 2023 | 780 | 32.9% | 0.709 | 0.687 | 0.671 | 78 | 59.0% |
| at_fire | bearish | label.next_period.took_parent_high | 2024 | 758 | 34.6% | 0.727 | 0.681 | 0.654 | 76 | 69.7% |
| at_fire | bearish | label.next_period.took_parent_high | 2025 | 776 | 37.2% | 0.669 | 0.640 | 0.628 | 78 | 53.8% |
| at_fire | bearish | label.next_period.took_parent_low | 2020 | 727 | 61.5% | 0.591 | 0.612 | 0.615 | 73 | 82.2% |
| at_fire | bearish | label.next_period.took_parent_low | 2021 | 741 | 58.7% | 0.645 | 0.640 | 0.587 | 75 | 61.3% |
| at_fire | bearish | label.next_period.took_parent_low | 2022 | 936 | 70.9% | 0.671 | 0.690 | 0.709 | 94 | 84.0% |
| at_fire | bearish | label.next_period.took_parent_low | 2023 | 780 | 68.6% | 0.652 | 0.665 | 0.686 | 78 | 85.9% |
| at_fire | bearish | label.next_period.took_parent_low | 2024 | 758 | 58.8% | 0.607 | 0.595 | 0.588 | 76 | 65.8% |
| at_fire | bearish | label.next_period.took_parent_low | 2025 | 776 | 58.0% | 0.646 | 0.584 | 0.580 | 78 | 79.5% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2020 | 993 | 77.8% | 0.631 | 0.780 | 0.778 | 100 | 77.0% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2021 | 1000 | 75.6% | 0.665 | 0.747 | 0.756 | 100 | 88.0% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2022 | 782 | 71.2% | 0.624 | 0.708 | 0.712 | 79 | 77.2% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2023 | 944 | 75.4% | 0.621 | 0.753 | 0.754 | 95 | 85.3% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2024 | 962 | 74.9% | 0.663 | 0.754 | 0.749 | 97 | 84.5% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2025 | 941 | 72.5% | 0.680 | 0.728 | 0.725 | 95 | 88.4% |
| at_fire | bullish | label.next_period.took_parent_high | 2020 | 993 | 77.8% | 0.631 | 0.780 | 0.778 | 100 | 77.0% |
| at_fire | bullish | label.next_period.took_parent_high | 2021 | 1000 | 75.6% | 0.665 | 0.747 | 0.756 | 100 | 88.0% |
| at_fire | bullish | label.next_period.took_parent_high | 2022 | 782 | 71.2% | 0.624 | 0.708 | 0.712 | 79 | 77.2% |
| at_fire | bullish | label.next_period.took_parent_high | 2023 | 944 | 75.4% | 0.621 | 0.753 | 0.754 | 95 | 85.3% |
| at_fire | bullish | label.next_period.took_parent_high | 2024 | 962 | 74.9% | 0.663 | 0.754 | 0.749 | 97 | 84.5% |
| at_fire | bullish | label.next_period.took_parent_high | 2025 | 941 | 72.5% | 0.680 | 0.728 | 0.725 | 95 | 88.4% |
| at_fire | bullish | label.next_period.took_parent_low | 2020 | 993 | 26.1% | 0.660 | 0.750 | 0.739 | 100 | 53.0% |
| at_fire | bullish | label.next_period.took_parent_low | 2021 | 1000 | 26.5% | 0.748 | 0.740 | 0.735 | 100 | 63.0% |
| at_fire | bullish | label.next_period.took_parent_low | 2022 | 782 | 33.0% | 0.617 | 0.665 | 0.670 | 79 | 45.6% |
| at_fire | bullish | label.next_period.took_parent_low | 2023 | 944 | 26.4% | 0.727 | 0.745 | 0.736 | 95 | 53.7% |
| at_fire | bullish | label.next_period.took_parent_low | 2024 | 962 | 30.2% | 0.767 | 0.716 | 0.698 | 97 | 63.9% |
| at_fire | bullish | label.next_period.took_parent_low | 2025 | 941 | 29.3% | 0.693 | 0.729 | 0.707 | 95 | 63.2% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
