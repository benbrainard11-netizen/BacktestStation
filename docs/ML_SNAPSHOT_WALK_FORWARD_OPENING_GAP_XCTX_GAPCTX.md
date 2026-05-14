# ML snapshot walk-forward validation

_Generated `2026-05-14T04:17:09.469743+00:00`._

## Setup

- Matrix: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx.parquet`
- Schema: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx.schema.json`
- Leaderboard source: `data\ml\anchors\opening_gap_snapshot_leaderboard_xctx_gapctx.parquet`
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
| data\ml\anchors\opening_gap_walk_forward_xctx_gapctx_summary.csv | candidate summary CSV |
| data\ml\anchors\opening_gap_walk_forward_xctx_gapctx_summary.parquet | candidate summary parquet |
| data\ml\anchors\opening_gap_walk_forward_xctx_gapctx_folds.csv | per-fold CSV |
| data\ml\anchors\opening_gap_walk_forward_xctx_gapctx_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 9438 |
| schema_feature_columns | 1047 |
| schema_label_columns | 396 |
| folds_attempted | 72 |
| folds_ok | 72 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_240m.fully_filled | 6 | 5157 | 0.834 | 0.828 | 0.805 | 0.026 | 97.1% | 95.5% | 19.6% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 6 | 5157 | 0.834 | 0.828 | 0.805 | 0.026 | 75.8% | 61.9% | 53.4% |
| at_fire | gap_down | label.next_240m.fully_filled | 6 | 2303 | 0.829 | 0.855 | 0.720 | 0.065 | 96.1% | 88.2% | 17.9% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 6 | 2303 | 0.829 | 0.855 | 0.720 | 0.065 | 76.8% | 50.0% | 55.0% |
| at_fire | all | label.next_1d.fully_filled | 6 | 5157 | 0.823 | 0.820 | 0.776 | 0.037 | 99.0% | 97.7% | 8.3% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 6 | 5157 | 0.822 | 0.831 | 0.779 | 0.025 | 86.3% | 78.6% | 53.4% |
| at_fire | all | label.next_60m.fully_filled | 6 | 5157 | 0.822 | 0.831 | 0.779 | 0.025 | 94.0% | 89.9% | 26.9% |
| at_fire | gap_up | label.next_60m.fully_filled | 6 | 2854 | 0.817 | 0.809 | 0.772 | 0.034 | 95.2% | 94.4% | 28.8% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 6 | 2854 | 0.817 | 0.809 | 0.772 | 0.034 | 81.7% | 61.1% | 48.0% |
| at_fire | gap_up | label.next_240m.fully_filled | 6 | 2854 | 0.817 | 0.821 | 0.753 | 0.045 | 96.4% | 92.6% | 19.0% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 6 | 2854 | 0.817 | 0.821 | 0.753 | 0.045 | 67.0% | 37.0% | 44.3% |
| at_fire | gap_up | label.next_1d.fully_filled | 6 | 2854 | 0.783 | 0.776 | 0.715 | 0.049 | 98.7% | 95.8% | 8.9% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_1d.fully_filled | 2020 | 886 | 86.2% | 0.786 | 0.858 | 0.862 | 89 | 98.9% |
| at_fire | all | label.next_1d.fully_filled | 2021 | 834 | 94.1% | 0.838 | 0.928 | 0.941 | 84 | 98.8% |
| at_fire | all | label.next_1d.fully_filled | 2022 | 854 | 91.8% | 0.776 | 0.902 | 0.918 | 86 | 97.7% |
| at_fire | all | label.next_1d.fully_filled | 2023 | 844 | 92.4% | 0.802 | 0.924 | 0.924 | 85 | 100.0% |
| at_fire | all | label.next_1d.fully_filled | 2024 | 872 | 90.5% | 0.868 | 0.912 | 0.905 | 88 | 100.0% |
| at_fire | all | label.next_1d.fully_filled | 2025 | 867 | 89.2% | 0.867 | 0.899 | 0.892 | 87 | 98.9% |
| at_fire | all | label.next_240m.fully_filled | 2020 | 886 | 73.0% | 0.856 | 0.807 | 0.730 | 89 | 98.9% |
| at_fire | all | label.next_240m.fully_filled | 2021 | 834 | 83.7% | 0.815 | 0.850 | 0.837 | 84 | 96.4% |
| at_fire | all | label.next_240m.fully_filled | 2022 | 854 | 76.3% | 0.841 | 0.824 | 0.763 | 86 | 98.8% |
| at_fire | all | label.next_240m.fully_filled | 2023 | 844 | 78.9% | 0.811 | 0.844 | 0.789 | 85 | 96.5% |
| at_fire | all | label.next_240m.fully_filled | 2024 | 872 | 78.1% | 0.805 | 0.828 | 0.781 | 88 | 95.5% |
| at_fire | all | label.next_240m.fully_filled | 2025 | 867 | 75.2% | 0.875 | 0.841 | 0.752 | 87 | 96.6% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 2020 | 886 | 27.0% | 0.856 | 0.807 | 0.730 | 89 | 79.8% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 2021 | 834 | 16.3% | 0.815 | 0.850 | 0.837 | 84 | 61.9% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 2022 | 854 | 23.7% | 0.841 | 0.824 | 0.763 | 86 | 74.4% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 2023 | 844 | 21.1% | 0.811 | 0.844 | 0.789 | 85 | 77.6% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 2024 | 872 | 21.9% | 0.805 | 0.828 | 0.781 | 88 | 77.3% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 2025 | 867 | 24.8% | 0.875 | 0.841 | 0.752 | 87 | 83.9% |
| at_fire | all | label.next_60m.fully_filled | 2020 | 886 | 62.6% | 0.846 | 0.796 | 0.626 | 89 | 89.9% |
| at_fire | all | label.next_60m.fully_filled | 2021 | 834 | 72.8% | 0.800 | 0.796 | 0.728 | 84 | 95.2% |
| at_fire | all | label.next_60m.fully_filled | 2022 | 854 | 64.5% | 0.838 | 0.788 | 0.645 | 86 | 94.2% |
| at_fire | all | label.next_60m.fully_filled | 2023 | 844 | 66.8% | 0.779 | 0.776 | 0.668 | 85 | 92.9% |
| at_fire | all | label.next_60m.fully_filled | 2024 | 872 | 70.3% | 0.825 | 0.811 | 0.703 | 88 | 96.6% |
| at_fire | all | label.next_60m.fully_filled | 2025 | 867 | 65.5% | 0.845 | 0.813 | 0.655 | 87 | 95.4% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 2020 | 886 | 37.4% | 0.846 | 0.796 | 0.626 | 89 | 88.8% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 2021 | 834 | 27.2% | 0.800 | 0.796 | 0.728 | 84 | 78.6% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 2022 | 854 | 35.5% | 0.838 | 0.788 | 0.645 | 86 | 95.3% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 2023 | 844 | 33.2% | 0.779 | 0.776 | 0.668 | 85 | 83.5% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 2024 | 872 | 29.7% | 0.825 | 0.811 | 0.703 | 88 | 86.4% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 2025 | 867 | 34.5% | 0.845 | 0.813 | 0.655 | 87 | 85.1% |
| at_fire | gap_down | label.next_240m.fully_filled | 2020 | 407 | 72.0% | 0.903 | 0.855 | 0.720 | 41 | 97.6% |
| at_fire | gap_down | label.next_240m.fully_filled | 2021 | 294 | 83.0% | 0.879 | 0.905 | 0.830 | 30 | 100.0% |
| at_fire | gap_down | label.next_240m.fully_filled | 2022 | 411 | 70.8% | 0.858 | 0.818 | 0.708 | 42 | 100.0% |
| at_fire | gap_down | label.next_240m.fully_filled | 2023 | 427 | 78.5% | 0.765 | 0.815 | 0.785 | 43 | 95.3% |
| at_fire | gap_down | label.next_240m.fully_filled | 2024 | 337 | 87.2% | 0.720 | 0.887 | 0.872 | 34 | 88.2% |
| at_fire | gap_down | label.next_240m.fully_filled | 2025 | 427 | 77.8% | 0.852 | 0.836 | 0.778 | 43 | 95.3% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 2020 | 407 | 28.0% | 0.903 | 0.855 | 0.720 | 41 | 92.7% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 2021 | 294 | 17.0% | 0.879 | 0.905 | 0.830 | 30 | 100.0% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 2022 | 411 | 29.2% | 0.858 | 0.818 | 0.708 | 42 | 81.0% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 2023 | 427 | 21.5% | 0.765 | 0.815 | 0.785 | 43 | 67.4% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 2024 | 337 | 12.8% | 0.720 | 0.887 | 0.872 | 34 | 50.0% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 2025 | 427 | 22.2% | 0.852 | 0.836 | 0.778 | 43 | 69.8% |
| at_fire | gap_up | label.next_1d.fully_filled | 2020 | 479 | 86.0% | 0.753 | 0.864 | 0.860 | 48 | 95.8% |
| at_fire | gap_up | label.next_1d.fully_filled | 2021 | 540 | 94.8% | 0.763 | 0.937 | 0.948 | 54 | 100.0% |
| at_fire | gap_up | label.next_1d.fully_filled | 2022 | 443 | 95.5% | 0.715 | 0.941 | 0.955 | 45 | 100.0% |
| at_fire | gap_up | label.next_1d.fully_filled | 2023 | 417 | 90.4% | 0.790 | 0.914 | 0.904 | 42 | 100.0% |
| at_fire | gap_up | label.next_1d.fully_filled | 2024 | 535 | 87.1% | 0.806 | 0.871 | 0.871 | 54 | 96.3% |
| at_fire | gap_up | label.next_1d.fully_filled | 2025 | 440 | 85.0% | 0.870 | 0.859 | 0.850 | 44 | 100.0% |
| at_fire | gap_up | label.next_240m.fully_filled | 2020 | 479 | 73.9% | 0.839 | 0.789 | 0.739 | 48 | 95.8% |
| at_fire | gap_up | label.next_240m.fully_filled | 2021 | 540 | 84.1% | 0.753 | 0.798 | 0.841 | 54 | 94.4% |
| at_fire | gap_up | label.next_240m.fully_filled | 2022 | 443 | 81.5% | 0.776 | 0.788 | 0.815 | 45 | 100.0% |
| at_fire | gap_up | label.next_240m.fully_filled | 2023 | 417 | 79.4% | 0.810 | 0.818 | 0.794 | 42 | 95.2% |
| at_fire | gap_up | label.next_240m.fully_filled | 2024 | 535 | 72.3% | 0.832 | 0.813 | 0.723 | 54 | 92.6% |
| at_fire | gap_up | label.next_240m.fully_filled | 2025 | 440 | 72.7% | 0.891 | 0.832 | 0.727 | 44 | 100.0% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 2020 | 479 | 26.1% | 0.839 | 0.789 | 0.739 | 48 | 75.0% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 2021 | 540 | 15.9% | 0.753 | 0.798 | 0.841 | 54 | 37.0% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 2022 | 443 | 18.5% | 0.776 | 0.788 | 0.815 | 45 | 44.4% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 2023 | 417 | 20.6% | 0.810 | 0.818 | 0.794 | 42 | 61.9% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 2024 | 535 | 27.7% | 0.832 | 0.813 | 0.723 | 54 | 92.6% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 2025 | 440 | 27.3% | 0.891 | 0.832 | 0.727 | 44 | 90.9% |
| at_fire | gap_up | label.next_60m.fully_filled | 2020 | 479 | 63.7% | 0.819 | 0.768 | 0.637 | 48 | 95.8% |
| at_fire | gap_up | label.next_60m.fully_filled | 2021 | 540 | 71.7% | 0.791 | 0.765 | 0.717 | 54 | 94.4% |
| at_fire | gap_up | label.next_60m.fully_filled | 2022 | 443 | 68.4% | 0.772 | 0.747 | 0.684 | 45 | 95.6% |
| at_fire | gap_up | label.next_60m.fully_filled | 2023 | 417 | 68.8% | 0.798 | 0.746 | 0.688 | 42 | 95.2% |
| at_fire | gap_up | label.next_60m.fully_filled | 2024 | 535 | 64.3% | 0.853 | 0.776 | 0.643 | 54 | 94.4% |
| at_fire | gap_up | label.next_60m.fully_filled | 2025 | 440 | 61.4% | 0.869 | 0.798 | 0.614 | 44 | 95.5% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 2020 | 479 | 36.3% | 0.819 | 0.768 | 0.637 | 48 | 91.7% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 2021 | 540 | 28.3% | 0.791 | 0.765 | 0.717 | 54 | 61.1% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 2022 | 443 | 31.6% | 0.772 | 0.747 | 0.684 | 45 | 75.6% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 2023 | 417 | 31.2% | 0.798 | 0.746 | 0.688 | 42 | 69.0% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 2024 | 535 | 35.7% | 0.853 | 0.776 | 0.643 | 54 | 92.6% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 2025 | 440 | 38.6% | 0.869 | 0.798 | 0.614 | 44 | 100.0% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
