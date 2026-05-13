# ML snapshot walk-forward validation

_Generated `2026-05-12T14:50:49.526091+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshots_xctx.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshot_leaderboard_xctx.parquet`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_walk_forward_summary_xctx.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_walk_forward_summary_xctx.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_walk_forward_folds_xctx.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_walk_forward_folds_xctx.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 19414 |
| schema_feature_columns | 626 |
| schema_label_columns | 24 |
| folds_attempted | 48 |
| folds_ok | 48 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_period.took_parent_high | 6 | 10364 | 0.793 | 0.799 | 0.758 | 0.022 | 89.4% | 83.2% | 33.2% |
| at_fire | all | label.next_period.took_parent_low | 6 | 10364 | 0.768 | 0.769 | 0.740 | 0.021 | 78.1% | 70.5% | 33.8% |
| at_fire | bullish | label.next_period.took_parent_low | 6 | 5622 | 0.723 | 0.734 | 0.629 | 0.046 | 63.0% | 51.0% | 34.5% |
| at_fire | bearish | label.next_period.took_parent_high | 6 | 4718 | 0.717 | 0.716 | 0.687 | 0.018 | 61.8% | 52.1% | 27.5% |
| at_fire | bullish | label.next_period.took_parent_high | 6 | 5622 | 0.695 | 0.697 | 0.654 | 0.025 | 92.8% | 84.0% | 18.2% |
| at_fire | bullish | label.next_period.thesis_confirmed | 6 | 5622 | 0.695 | 0.697 | 0.654 | 0.025 | 92.8% | 84.0% | 18.2% |
| at_fire | all | label.next_period.thesis_confirmed | 6 | 10364 | 0.673 | 0.669 | 0.635 | 0.027 | 92.1% | 88.4% | 22.7% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 6 | 485 | 0.615 | 0.607 | 0.443 | 0.108 | 55.7% | 8.3% | -1.4% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_period.thesis_confirmed | 2020 | 1724 | 70.9% | 0.658 | 0.718 | 0.709 | 173 | 88.4% |
| at_fire | all | label.next_period.thesis_confirmed | 2021 | 1743 | 68.4% | 0.711 | 0.719 | 0.684 | 175 | 89.1% |
| at_fire | all | label.next_period.thesis_confirmed | 2022 | 1722 | 71.1% | 0.635 | 0.704 | 0.711 | 173 | 91.3% |
| at_fire | all | label.next_period.thesis_confirmed | 2023 | 1728 | 72.3% | 0.702 | 0.736 | 0.723 | 173 | 98.8% |
| at_fire | all | label.next_period.thesis_confirmed | 2024 | 1728 | 67.8% | 0.655 | 0.673 | 0.678 | 173 | 91.3% |
| at_fire | all | label.next_period.thesis_confirmed | 2025 | 1719 | 66.0% | 0.680 | 0.686 | 0.660 | 172 | 93.6% |
| at_fire | all | label.next_period.took_parent_high | 2020 | 1724 | 58.3% | 0.820 | 0.762 | 0.583 | 173 | 88.4% |
| at_fire | all | label.next_period.took_parent_high | 2021 | 1743 | 59.7% | 0.772 | 0.709 | 0.597 | 175 | 88.0% |
| at_fire | all | label.next_period.took_parent_high | 2022 | 1722 | 49.6% | 0.789 | 0.701 | 0.496 | 173 | 83.2% |
| at_fire | all | label.next_period.took_parent_high | 2023 | 1728 | 56.2% | 0.811 | 0.722 | 0.562 | 173 | 94.2% |
| at_fire | all | label.next_period.took_parent_high | 2024 | 1728 | 57.0% | 0.809 | 0.742 | 0.570 | 173 | 93.1% |
| at_fire | all | label.next_period.took_parent_high | 2025 | 1719 | 56.5% | 0.758 | 0.707 | 0.565 | 172 | 89.5% |
| at_fire | all | label.next_period.took_parent_low | 2020 | 1724 | 41.1% | 0.740 | 0.704 | 0.589 | 173 | 70.5% |
| at_fire | all | label.next_period.took_parent_low | 2021 | 1743 | 40.3% | 0.790 | 0.725 | 0.597 | 175 | 81.1% |
| at_fire | all | label.next_period.took_parent_low | 2022 | 1722 | 53.8% | 0.790 | 0.716 | 0.462 | 173 | 86.1% |
| at_fire | all | label.next_period.took_parent_low | 2023 | 1728 | 45.5% | 0.786 | 0.703 | 0.545 | 173 | 78.6% |
| at_fire | all | label.next_period.took_parent_low | 2024 | 1728 | 42.9% | 0.749 | 0.688 | 0.571 | 173 | 81.5% |
| at_fire | all | label.next_period.took_parent_low | 2025 | 1719 | 42.4% | 0.752 | 0.691 | 0.576 | 172 | 70.9% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 2020 | 79 | 59.5% | 0.624 | 0.595 | 0.595 | 8 | 75.0% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 2021 | 65 | 63.1% | 0.443 | 0.492 | 0.631 | 7 | 57.1% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 2022 | 112 | 31.2% | 0.540 | 0.312 | 0.312 | 12 | 8.3% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 2023 | 74 | 60.8% | 0.730 | 0.676 | 0.608 | 8 | 87.5% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 2024 | 70 | 60.0% | 0.589 | 0.600 | 0.600 | 7 | 28.6% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 2025 | 85 | 68.2% | 0.761 | 0.600 | 0.682 | 9 | 77.8% |
| at_fire | bearish | label.next_period.took_parent_high | 2020 | 727 | 31.4% | 0.738 | 0.713 | 0.686 | 73 | 63.0% |
| at_fire | bearish | label.next_period.took_parent_high | 2021 | 741 | 38.2% | 0.704 | 0.663 | 0.618 | 75 | 72.0% |
| at_fire | bearish | label.next_period.took_parent_high | 2022 | 936 | 31.7% | 0.716 | 0.681 | 0.683 | 94 | 52.1% |
| at_fire | bearish | label.next_period.took_parent_high | 2023 | 780 | 32.9% | 0.717 | 0.709 | 0.671 | 78 | 56.4% |
| at_fire | bearish | label.next_period.took_parent_high | 2024 | 758 | 34.6% | 0.740 | 0.714 | 0.654 | 76 | 67.1% |
| at_fire | bearish | label.next_period.took_parent_high | 2025 | 776 | 37.2% | 0.687 | 0.648 | 0.628 | 78 | 60.3% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2020 | 993 | 77.8% | 0.686 | 0.784 | 0.778 | 100 | 84.0% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2021 | 1000 | 75.6% | 0.678 | 0.757 | 0.756 | 100 | 90.0% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2022 | 782 | 71.2% | 0.708 | 0.728 | 0.712 | 79 | 96.2% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2023 | 944 | 75.4% | 0.713 | 0.767 | 0.754 | 95 | 97.9% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2024 | 962 | 74.9% | 0.729 | 0.749 | 0.749 | 97 | 96.9% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2025 | 941 | 72.5% | 0.654 | 0.727 | 0.725 | 95 | 91.6% |
| at_fire | bullish | label.next_period.took_parent_high | 2020 | 993 | 77.8% | 0.686 | 0.784 | 0.778 | 100 | 84.0% |
| at_fire | bullish | label.next_period.took_parent_high | 2021 | 1000 | 75.6% | 0.678 | 0.757 | 0.756 | 100 | 90.0% |
| at_fire | bullish | label.next_period.took_parent_high | 2022 | 782 | 71.2% | 0.708 | 0.728 | 0.712 | 79 | 96.2% |
| at_fire | bullish | label.next_period.took_parent_high | 2023 | 944 | 75.4% | 0.713 | 0.767 | 0.754 | 95 | 97.9% |
| at_fire | bullish | label.next_period.took_parent_high | 2024 | 962 | 74.9% | 0.729 | 0.749 | 0.749 | 97 | 96.9% |
| at_fire | bullish | label.next_period.took_parent_high | 2025 | 941 | 72.5% | 0.654 | 0.727 | 0.725 | 95 | 91.6% |
| at_fire | bullish | label.next_period.took_parent_low | 2020 | 993 | 26.1% | 0.629 | 0.745 | 0.739 | 100 | 51.0% |
| at_fire | bullish | label.next_period.took_parent_low | 2021 | 1000 | 26.5% | 0.777 | 0.745 | 0.735 | 100 | 68.0% |
| at_fire | bullish | label.next_period.took_parent_low | 2022 | 782 | 33.0% | 0.748 | 0.706 | 0.670 | 79 | 73.4% |
| at_fire | bullish | label.next_period.took_parent_low | 2023 | 944 | 26.4% | 0.718 | 0.753 | 0.736 | 95 | 61.1% |
| at_fire | bullish | label.next_period.took_parent_low | 2024 | 962 | 30.2% | 0.723 | 0.738 | 0.698 | 97 | 71.1% |
| at_fire | bullish | label.next_period.took_parent_low | 2025 | 941 | 29.3% | 0.745 | 0.714 | 0.707 | 95 | 53.7% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
