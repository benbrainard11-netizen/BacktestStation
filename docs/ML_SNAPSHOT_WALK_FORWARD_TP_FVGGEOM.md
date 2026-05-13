# ML snapshot walk-forward validation

_Generated `2026-05-12T19:54:05.665227+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshots_xctx_fvggeom.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshots_xctx_fvggeom.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshot_leaderboard_xctx_fvggeom.parquet`
- Event type: `all`
- Candidates: `10`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025, 2026`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_walk_forward_fvggeom_summary.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_walk_forward_fvggeom_summary.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_walk_forward_fvggeom_folds.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_walk_forward_fvggeom_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 19414 |
| schema_feature_columns | 1077 |
| schema_label_columns | 24 |
| folds_attempted | 70 |
| folds_ok | 69 |
| folds_skipped | 1 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_period.took_parent_high | 7 | 10589 | 0.797 | 0.792 | 0.745 | 0.029 | 92.0% | 83.2% | 36.9% |
| at_fire | all | label.next_period.took_parent_low | 7 | 10589 | 0.778 | 0.776 | 0.755 | 0.017 | 83.3% | 74.6% | 37.3% |
| at_fire | bullish | label.next_period.took_parent_high | 7 | 5719 | 0.740 | 0.725 | 0.697 | 0.046 | 94.2% | 86.0% | 20.1% |
| at_fire | bullish | label.next_period.thesis_confirmed | 7 | 5719 | 0.740 | 0.725 | 0.697 | 0.046 | 94.2% | 86.0% | 20.1% |
| at_fire | bullish | label.next_period.took_parent_low | 7 | 5719 | 0.737 | 0.753 | 0.661 | 0.034 | 70.6% | 55.0% | 41.4% |
| at_fire | bearish | label.next_period.took_parent_high | 7 | 4846 | 0.710 | 0.741 | 0.558 | 0.064 | 57.9% | 7.7% | 24.0% |
| at_fire | all | label.next_period.thesis_confirmed | 7 | 10589 | 0.696 | 0.695 | 0.650 | 0.033 | 93.3% | 89.6% | 23.5% |
| at_fire | bearish | label.next_period.took_parent_low | 7 | 4846 | 0.680 | 0.675 | 0.650 | 0.032 | 85.4% | 74.0% | 21.1% |
| at_fire | bearish | label.next_period.thesis_confirmed | 7 | 4846 | 0.680 | 0.675 | 0.650 | 0.032 | 85.4% | 74.0% | 21.1% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 6 | 485 | 0.594 | 0.565 | 0.471 | 0.097 | 76.6% | 41.7% | 19.4% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_period.thesis_confirmed | 2020 | 1724 | 70.9% | 0.650 | 0.695 | 0.709 | 173 | 90.2% |
| at_fire | all | label.next_period.thesis_confirmed | 2021 | 1743 | 68.4% | 0.736 | 0.718 | 0.684 | 175 | 93.1% |
| at_fire | all | label.next_period.thesis_confirmed | 2022 | 1722 | 71.1% | 0.656 | 0.698 | 0.711 | 173 | 89.6% |
| at_fire | all | label.next_period.thesis_confirmed | 2023 | 1728 | 72.3% | 0.703 | 0.730 | 0.723 | 173 | 96.5% |
| at_fire | all | label.next_period.thesis_confirmed | 2024 | 1728 | 67.8% | 0.692 | 0.675 | 0.678 | 173 | 93.6% |
| at_fire | all | label.next_period.thesis_confirmed | 2025 | 1719 | 66.0% | 0.695 | 0.700 | 0.660 | 172 | 90.1% |
| at_fire | all | label.next_period.thesis_confirmed | 2026 | 225 | 72.4% | 0.742 | 0.702 | 0.724 | 23 | 100.0% |
| at_fire | all | label.next_period.took_parent_high | 2020 | 1724 | 58.3% | 0.834 | 0.765 | 0.583 | 173 | 90.8% |
| at_fire | all | label.next_period.took_parent_high | 2021 | 1743 | 59.7% | 0.792 | 0.722 | 0.597 | 175 | 89.7% |
| at_fire | all | label.next_period.took_parent_high | 2022 | 1722 | 49.6% | 0.791 | 0.704 | 0.496 | 173 | 83.2% |
| at_fire | all | label.next_period.took_parent_high | 2023 | 1728 | 56.2% | 0.817 | 0.741 | 0.562 | 173 | 93.1% |
| at_fire | all | label.next_period.took_parent_high | 2024 | 1728 | 57.0% | 0.824 | 0.752 | 0.570 | 173 | 94.2% |
| at_fire | all | label.next_period.took_parent_high | 2025 | 1719 | 56.5% | 0.772 | 0.693 | 0.565 | 172 | 93.0% |
| at_fire | all | label.next_period.took_parent_high | 2026 | 225 | 48.4% | 0.745 | 0.684 | 0.484 | 23 | 100.0% |
| at_fire | all | label.next_period.took_parent_low | 2020 | 1724 | 41.1% | 0.764 | 0.724 | 0.589 | 173 | 74.6% |
| at_fire | all | label.next_period.took_parent_low | 2021 | 1743 | 40.3% | 0.788 | 0.713 | 0.597 | 175 | 83.4% |
| at_fire | all | label.next_period.took_parent_low | 2022 | 1722 | 53.8% | 0.803 | 0.714 | 0.462 | 173 | 89.6% |
| at_fire | all | label.next_period.took_parent_low | 2023 | 1728 | 45.5% | 0.798 | 0.705 | 0.545 | 173 | 86.1% |
| at_fire | all | label.next_period.took_parent_low | 2024 | 1728 | 42.9% | 0.762 | 0.698 | 0.571 | 173 | 80.9% |
| at_fire | all | label.next_period.took_parent_low | 2025 | 1719 | 42.4% | 0.755 | 0.693 | 0.576 | 172 | 77.3% |
| at_fire | all | label.next_period.took_parent_low | 2026 | 225 | 56.0% | 0.776 | 0.711 | 0.440 | 23 | 91.3% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 2020 | 79 | 59.5% | 0.557 | 0.544 | 0.595 | 8 | 87.5% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 2021 | 65 | 63.1% | 0.471 | 0.508 | 0.631 | 7 | 71.4% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 2022 | 112 | 31.2% | 0.573 | 0.312 | 0.312 | 12 | 41.7% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 2023 | 74 | 60.8% | 0.742 | 0.676 | 0.608 | 8 | 87.5% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 2024 | 70 | 60.0% | 0.520 | 0.486 | 0.600 | 7 | 71.4% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 2025 | 85 | 68.2% | 0.702 | 0.647 | 0.682 | 9 | 100.0% |
| at_fire | bearish | label.next_period.thesis_confirmed | 2020 | 727 | 61.5% | 0.653 | 0.692 | 0.615 | 73 | 74.0% |
| at_fire | bearish | label.next_period.thesis_confirmed | 2021 | 741 | 58.7% | 0.743 | 0.682 | 0.587 | 75 | 84.0% |
| at_fire | bearish | label.next_period.thesis_confirmed | 2022 | 936 | 70.9% | 0.688 | 0.701 | 0.709 | 94 | 87.2% |
| at_fire | bearish | label.next_period.thesis_confirmed | 2023 | 780 | 68.6% | 0.703 | 0.704 | 0.686 | 78 | 84.6% |
| at_fire | bearish | label.next_period.thesis_confirmed | 2024 | 758 | 58.8% | 0.650 | 0.623 | 0.588 | 76 | 90.8% |
| at_fire | bearish | label.next_period.thesis_confirmed | 2025 | 776 | 58.0% | 0.651 | 0.612 | 0.580 | 78 | 76.9% |
| at_fire | bearish | label.next_period.thesis_confirmed | 2026 | 128 | 73.4% | 0.675 | 0.695 | 0.734 | 13 | 100.0% |
| at_fire | bearish | label.next_period.took_parent_high | 2020 | 727 | 31.4% | 0.749 | 0.699 | 0.686 | 73 | 58.9% |
| at_fire | bearish | label.next_period.took_parent_high | 2021 | 741 | 38.2% | 0.743 | 0.677 | 0.618 | 75 | 78.7% |
| at_fire | bearish | label.next_period.took_parent_high | 2022 | 936 | 31.7% | 0.721 | 0.691 | 0.683 | 94 | 53.2% |
| at_fire | bearish | label.next_period.took_parent_high | 2023 | 780 | 32.9% | 0.741 | 0.714 | 0.671 | 78 | 59.0% |
| at_fire | bearish | label.next_period.took_parent_high | 2024 | 758 | 34.6% | 0.756 | 0.710 | 0.654 | 76 | 75.0% |
| at_fire | bearish | label.next_period.took_parent_high | 2025 | 776 | 37.2% | 0.705 | 0.673 | 0.628 | 78 | 73.1% |
| at_fire | bearish | label.next_period.took_parent_high | 2026 | 128 | 31.2% | 0.558 | 0.594 | 0.688 | 13 | 7.7% |
| at_fire | bearish | label.next_period.took_parent_low | 2020 | 727 | 61.5% | 0.653 | 0.692 | 0.615 | 73 | 74.0% |
| at_fire | bearish | label.next_period.took_parent_low | 2021 | 741 | 58.7% | 0.743 | 0.682 | 0.587 | 75 | 84.0% |
| at_fire | bearish | label.next_period.took_parent_low | 2022 | 936 | 70.9% | 0.688 | 0.701 | 0.709 | 94 | 87.2% |
| at_fire | bearish | label.next_period.took_parent_low | 2023 | 780 | 68.6% | 0.703 | 0.704 | 0.686 | 78 | 84.6% |
| at_fire | bearish | label.next_period.took_parent_low | 2024 | 758 | 58.8% | 0.650 | 0.623 | 0.588 | 76 | 90.8% |
| at_fire | bearish | label.next_period.took_parent_low | 2025 | 776 | 58.0% | 0.651 | 0.612 | 0.580 | 78 | 76.9% |
| at_fire | bearish | label.next_period.took_parent_low | 2026 | 128 | 73.4% | 0.675 | 0.695 | 0.734 | 13 | 100.0% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2020 | 993 | 77.8% | 0.740 | 0.784 | 0.778 | 100 | 96.0% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2021 | 1000 | 75.6% | 0.717 | 0.765 | 0.756 | 100 | 86.0% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2022 | 782 | 71.2% | 0.706 | 0.725 | 0.712 | 79 | 89.9% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2023 | 944 | 75.4% | 0.725 | 0.770 | 0.754 | 95 | 97.9% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2024 | 962 | 74.9% | 0.747 | 0.758 | 0.749 | 97 | 95.9% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2025 | 941 | 72.5% | 0.697 | 0.743 | 0.725 | 95 | 93.7% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2026 | 97 | 71.1% | 0.846 | 0.773 | 0.711 | 10 | 100.0% |
| at_fire | bullish | label.next_period.took_parent_high | 2020 | 993 | 77.8% | 0.740 | 0.784 | 0.778 | 100 | 96.0% |
| at_fire | bullish | label.next_period.took_parent_high | 2021 | 1000 | 75.6% | 0.717 | 0.765 | 0.756 | 100 | 86.0% |
| at_fire | bullish | label.next_period.took_parent_high | 2022 | 782 | 71.2% | 0.706 | 0.725 | 0.712 | 79 | 89.9% |
| at_fire | bullish | label.next_period.took_parent_high | 2023 | 944 | 75.4% | 0.725 | 0.770 | 0.754 | 95 | 97.9% |
| at_fire | bullish | label.next_period.took_parent_high | 2024 | 962 | 74.9% | 0.747 | 0.758 | 0.749 | 97 | 95.9% |
| at_fire | bullish | label.next_period.took_parent_high | 2025 | 941 | 72.5% | 0.697 | 0.743 | 0.725 | 95 | 93.7% |
| at_fire | bullish | label.next_period.took_parent_high | 2026 | 97 | 71.1% | 0.846 | 0.773 | 0.711 | 10 | 100.0% |
| at_fire | bullish | label.next_period.took_parent_low | 2020 | 993 | 26.1% | 0.661 | 0.758 | 0.739 | 100 | 55.0% |
| at_fire | bullish | label.next_period.took_parent_low | 2021 | 1000 | 26.5% | 0.755 | 0.746 | 0.735 | 100 | 63.0% |
| at_fire | bullish | label.next_period.took_parent_low | 2022 | 782 | 33.0% | 0.764 | 0.724 | 0.670 | 79 | 81.0% |
| at_fire | bullish | label.next_period.took_parent_low | 2023 | 944 | 26.4% | 0.747 | 0.746 | 0.736 | 95 | 56.8% |
| at_fire | bullish | label.next_period.took_parent_low | 2024 | 962 | 30.2% | 0.762 | 0.746 | 0.698 | 97 | 76.3% |
| at_fire | bullish | label.next_period.took_parent_low | 2025 | 941 | 29.3% | 0.753 | 0.727 | 0.707 | 95 | 62.1% |
| at_fire | bullish | label.next_period.took_parent_low | 2026 | 97 | 33.0% | 0.719 | 0.691 | 0.670 | 10 | 100.0% |

## Skipped Folds

| status | count |
|---|---|
| skip_small_split | 1 |

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
