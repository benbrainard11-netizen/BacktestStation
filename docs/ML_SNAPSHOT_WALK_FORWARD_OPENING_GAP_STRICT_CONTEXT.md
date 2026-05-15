# ML snapshot walk-forward validation

_Generated `2026-05-15T04:52:03.151475+00:00`._

## Setup

- Matrix: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict.parquet`
- Schema: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict.schema.json`
- Leaderboard source: `data\ml\anchors\opening_gap_strict_context_leaderboard.parquet`
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
| data\ml\anchors\opening_gap_strict_context_walk_forward_summary.csv | candidate summary CSV |
| data\ml\anchors\opening_gap_strict_context_walk_forward_summary.parquet | candidate summary parquet |
| data\ml\anchors\opening_gap_strict_context_walk_forward_folds.csv | per-fold CSV |
| data\ml\anchors\opening_gap_strict_context_walk_forward_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 9438 |
| schema_feature_columns | 2873 |
| schema_label_columns | 423 |
| folds_attempted | 72 |
| folds_ok | 72 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 6 | 5157 | 0.837 | 0.825 | 0.805 | 0.032 | 75.9% | 64.3% | 53.4% |
| at_fire | gap_down | label.strict.next_240m.partial_touch_rejected | 6 | 2303 | 0.833 | 0.854 | 0.738 | 0.055 | 72.2% | 52.9% | 50.4% |
| at_fire | gap_up | label.strict.next_60m.partial_touch_rejected | 6 | 2854 | 0.830 | 0.832 | 0.777 | 0.042 | 83.9% | 66.7% | 50.3% |
| at_fire | all | label.strict.next_60m.partial_touch_rejected | 6 | 5157 | 0.826 | 0.835 | 0.792 | 0.024 | 89.9% | 77.4% | 57.0% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 6 | 5157 | 0.825 | 0.806 | 0.791 | 0.034 | 40.5% | 27.9% | 31.2% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 6 | 2854 | 0.822 | 0.839 | 0.734 | 0.048 | 68.7% | 48.1% | 46.0% |
| at_fire | gap_down | label.strict.next_60m.partial_touch_rejected | 6 | 2303 | 0.820 | 0.831 | 0.753 | 0.052 | 89.0% | 73.5% | 57.5% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 6 | 2854 | 0.787 | 0.778 | 0.736 | 0.047 | 36.3% | 7.4% | 26.1% |
| at_fire | all | label.strict.next_1d.filled_then_continued_through | 6 | 5157 | 0.762 | 0.755 | 0.731 | 0.028 | 96.0% | 93.1% | 8.3% |
| at_fire | all | label.strict.next_1d.failed_fill_expanded_away | 6 | 5157 | 0.750 | 0.745 | 0.708 | 0.031 | 15.9% | 7.1% | 8.1% |
| at_fire | gap_up | label.strict.next_1d.filled_then_continued_through | 6 | 2854 | 0.740 | 0.749 | 0.661 | 0.056 | 97.9% | 96.3% | 11.3% |
| at_fire | gap_up | label.strict.next_240m.filled_then_continued_through | 6 | 2854 | 0.738 | 0.736 | 0.660 | 0.055 | 86.7% | 71.4% | 19.3% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.strict.next_1d.failed_fill_expanded_away | 2020 | 886 | 12.3% | 0.708 | 0.877 | 0.877 | 89 | 23.6% |
| at_fire | all | label.strict.next_1d.failed_fill_expanded_away | 2021 | 834 | 5.6% | 0.755 | 0.944 | 0.944 | 84 | 11.9% |
| at_fire | all | label.strict.next_1d.failed_fill_expanded_away | 2022 | 854 | 7.1% | 0.728 | 0.929 | 0.929 | 86 | 11.6% |
| at_fire | all | label.strict.next_1d.failed_fill_expanded_away | 2023 | 844 | 6.2% | 0.735 | 0.938 | 0.938 | 85 | 7.1% |
| at_fire | all | label.strict.next_1d.failed_fill_expanded_away | 2024 | 872 | 7.2% | 0.767 | 0.928 | 0.928 | 88 | 18.2% |
| at_fire | all | label.strict.next_1d.failed_fill_expanded_away | 2025 | 867 | 8.3% | 0.806 | 0.917 | 0.917 | 87 | 23.0% |
| at_fire | all | label.strict.next_1d.filled_then_continued_through | 2020 | 886 | 83.4% | 0.768 | 0.832 | 0.834 | 89 | 95.5% |
| at_fire | all | label.strict.next_1d.filled_then_continued_through | 2021 | 834 | 90.4% | 0.731 | 0.897 | 0.904 | 84 | 94.0% |
| at_fire | all | label.strict.next_1d.filled_then_continued_through | 2022 | 854 | 89.5% | 0.742 | 0.885 | 0.895 | 86 | 98.8% |
| at_fire | all | label.strict.next_1d.filled_then_continued_through | 2023 | 844 | 88.6% | 0.740 | 0.889 | 0.886 | 85 | 98.8% |
| at_fire | all | label.strict.next_1d.filled_then_continued_through | 2024 | 872 | 87.7% | 0.776 | 0.882 | 0.877 | 88 | 95.5% |
| at_fire | all | label.strict.next_1d.filled_then_continued_through | 2025 | 867 | 86.4% | 0.814 | 0.875 | 0.864 | 87 | 93.1% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 2020 | 886 | 13.8% | 0.808 | 0.862 | 0.862 | 89 | 43.8% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 2021 | 834 | 5.9% | 0.805 | 0.944 | 0.941 | 84 | 31.0% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 2022 | 854 | 8.2% | 0.791 | 0.904 | 0.918 | 86 | 27.9% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 2023 | 844 | 7.6% | 0.802 | 0.927 | 0.924 | 85 | 31.8% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 2024 | 872 | 9.5% | 0.861 | 0.909 | 0.905 | 88 | 51.1% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 2025 | 867 | 10.8% | 0.882 | 0.908 | 0.892 | 87 | 57.5% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 2020 | 886 | 27.0% | 0.875 | 0.823 | 0.730 | 89 | 79.8% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 2021 | 834 | 16.3% | 0.805 | 0.865 | 0.837 | 84 | 64.3% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 2022 | 854 | 23.7% | 0.835 | 0.816 | 0.763 | 86 | 76.7% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 2023 | 844 | 21.1% | 0.815 | 0.850 | 0.789 | 85 | 80.0% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 2024 | 872 | 21.9% | 0.805 | 0.829 | 0.781 | 88 | 73.9% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 2025 | 867 | 24.8% | 0.885 | 0.856 | 0.752 | 87 | 80.5% |
| at_fire | all | label.strict.next_60m.partial_touch_rejected | 2020 | 886 | 37.4% | 0.848 | 0.797 | 0.626 | 89 | 100.0% |
| at_fire | all | label.strict.next_60m.partial_touch_rejected | 2021 | 834 | 27.2% | 0.794 | 0.799 | 0.728 | 84 | 77.4% |
| at_fire | all | label.strict.next_60m.partial_touch_rejected | 2022 | 854 | 35.5% | 0.838 | 0.788 | 0.645 | 86 | 97.7% |
| at_fire | all | label.strict.next_60m.partial_touch_rejected | 2023 | 844 | 33.2% | 0.792 | 0.770 | 0.668 | 85 | 84.7% |
| at_fire | all | label.strict.next_60m.partial_touch_rejected | 2024 | 872 | 29.7% | 0.832 | 0.808 | 0.703 | 88 | 90.9% |
| at_fire | all | label.strict.next_60m.partial_touch_rejected | 2025 | 867 | 34.5% | 0.852 | 0.811 | 0.655 | 87 | 88.5% |
| at_fire | gap_down | label.strict.next_240m.partial_touch_rejected | 2020 | 407 | 28.0% | 0.896 | 0.857 | 0.720 | 41 | 80.5% |
| at_fire | gap_down | label.strict.next_240m.partial_touch_rejected | 2021 | 294 | 17.0% | 0.873 | 0.891 | 0.830 | 30 | 86.7% |
| at_fire | gap_down | label.strict.next_240m.partial_touch_rejected | 2022 | 411 | 29.2% | 0.843 | 0.803 | 0.708 | 42 | 71.4% |
| at_fire | gap_down | label.strict.next_240m.partial_touch_rejected | 2023 | 427 | 21.5% | 0.782 | 0.813 | 0.785 | 43 | 69.8% |
| at_fire | gap_down | label.strict.next_240m.partial_touch_rejected | 2024 | 337 | 12.8% | 0.738 | 0.878 | 0.872 | 34 | 52.9% |
| at_fire | gap_down | label.strict.next_240m.partial_touch_rejected | 2025 | 427 | 22.2% | 0.865 | 0.857 | 0.778 | 43 | 72.1% |
| at_fire | gap_down | label.strict.next_60m.partial_touch_rejected | 2020 | 407 | 38.6% | 0.885 | 0.830 | 0.614 | 41 | 100.0% |
| at_fire | gap_down | label.strict.next_60m.partial_touch_rejected | 2021 | 294 | 25.2% | 0.839 | 0.850 | 0.748 | 30 | 93.3% |
| at_fire | gap_down | label.strict.next_60m.partial_touch_rejected | 2022 | 411 | 39.7% | 0.871 | 0.798 | 0.603 | 42 | 95.2% |
| at_fire | gap_down | label.strict.next_60m.partial_touch_rejected | 2023 | 427 | 35.1% | 0.753 | 0.735 | 0.649 | 43 | 90.7% |
| at_fire | gap_down | label.strict.next_60m.partial_touch_rejected | 2024 | 337 | 20.2% | 0.753 | 0.855 | 0.798 | 34 | 73.5% |
| at_fire | gap_down | label.strict.next_60m.partial_touch_rejected | 2025 | 427 | 30.2% | 0.823 | 0.808 | 0.698 | 43 | 81.4% |
| at_fire | gap_up | label.strict.next_1d.filled_then_continued_through | 2020 | 479 | 82.7% | 0.771 | 0.839 | 0.827 | 48 | 97.9% |
| at_fire | gap_up | label.strict.next_1d.filled_then_continued_through | 2021 | 540 | 90.0% | 0.728 | 0.878 | 0.900 | 54 | 100.0% |
| at_fire | gap_up | label.strict.next_1d.filled_then_continued_through | 2022 | 443 | 93.2% | 0.684 | 0.919 | 0.932 | 45 | 97.8% |
| at_fire | gap_up | label.strict.next_1d.filled_then_continued_through | 2023 | 417 | 88.0% | 0.661 | 0.885 | 0.880 | 42 | 97.6% |
| at_fire | gap_up | label.strict.next_1d.filled_then_continued_through | 2024 | 535 | 84.9% | 0.777 | 0.849 | 0.849 | 54 | 96.3% |
| at_fire | gap_up | label.strict.next_1d.filled_then_continued_through | 2025 | 440 | 80.9% | 0.822 | 0.809 | 0.809 | 44 | 97.7% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 2020 | 479 | 14.0% | 0.785 | 0.864 | 0.860 | 48 | 37.5% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 2021 | 540 | 5.2% | 0.739 | 0.937 | 0.948 | 54 | 7.4% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 2022 | 443 | 4.5% | 0.736 | 0.941 | 0.955 | 45 | 17.8% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 2023 | 417 | 9.6% | 0.771 | 0.909 | 0.904 | 42 | 28.6% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 2024 | 535 | 12.9% | 0.821 | 0.871 | 0.871 | 54 | 53.7% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 2025 | 440 | 15.0% | 0.871 | 0.855 | 0.850 | 44 | 72.7% |
| at_fire | gap_up | label.strict.next_240m.filled_then_continued_through | 2020 | 479 | 64.3% | 0.760 | 0.754 | 0.643 | 48 | 85.4% |
| at_fire | gap_up | label.strict.next_240m.filled_then_continued_through | 2021 | 540 | 73.5% | 0.711 | 0.730 | 0.735 | 54 | 94.4% |
| at_fire | gap_up | label.strict.next_240m.filled_then_continued_through | 2022 | 443 | 74.3% | 0.694 | 0.716 | 0.743 | 45 | 91.1% |
| at_fire | gap_up | label.strict.next_240m.filled_then_continued_through | 2023 | 417 | 67.1% | 0.660 | 0.705 | 0.671 | 42 | 71.4% |
| at_fire | gap_up | label.strict.next_240m.filled_then_continued_through | 2024 | 535 | 64.1% | 0.782 | 0.727 | 0.641 | 54 | 87.0% |
| at_fire | gap_up | label.strict.next_240m.filled_then_continued_through | 2025 | 440 | 61.4% | 0.820 | 0.761 | 0.614 | 44 | 90.9% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 2020 | 479 | 26.1% | 0.841 | 0.802 | 0.739 | 48 | 79.2% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 2021 | 540 | 15.9% | 0.734 | 0.804 | 0.841 | 54 | 48.1% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 2022 | 443 | 18.5% | 0.793 | 0.824 | 0.815 | 45 | 48.9% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 2023 | 417 | 20.6% | 0.836 | 0.830 | 0.794 | 42 | 64.3% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 2024 | 535 | 27.7% | 0.841 | 0.798 | 0.723 | 54 | 85.2% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 2025 | 440 | 27.3% | 0.889 | 0.836 | 0.727 | 44 | 86.4% |
| at_fire | gap_up | label.strict.next_60m.partial_touch_rejected | 2020 | 479 | 36.3% | 0.839 | 0.783 | 0.637 | 48 | 91.7% |
| at_fire | gap_up | label.strict.next_60m.partial_touch_rejected | 2021 | 540 | 28.3% | 0.779 | 0.759 | 0.717 | 54 | 70.4% |
| at_fire | gap_up | label.strict.next_60m.partial_touch_rejected | 2022 | 443 | 31.6% | 0.777 | 0.765 | 0.684 | 45 | 82.2% |
| at_fire | gap_up | label.strict.next_60m.partial_touch_rejected | 2023 | 417 | 31.2% | 0.824 | 0.765 | 0.688 | 42 | 66.7% |
| at_fire | gap_up | label.strict.next_60m.partial_touch_rejected | 2024 | 535 | 35.7% | 0.881 | 0.785 | 0.643 | 54 | 92.6% |
| at_fire | gap_up | label.strict.next_60m.partial_touch_rejected | 2025 | 440 | 38.6% | 0.877 | 0.802 | 0.614 | 44 | 100.0% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
