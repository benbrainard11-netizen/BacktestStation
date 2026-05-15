# ML snapshot walk-forward validation

_Generated `2026-05-15T15:11:29.994286+00:00`._

## Setup

- Matrix: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict.parquet`
- Schema: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict.schema.json`
- Leaderboard source: `data\ml\anchors\opening_gap_snapshot_leaderboard_strict_context.parquet`
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
| data\ml\anchors\opening_gap_walk_forward_strict_context_summary.csv | candidate summary CSV |
| data\ml\anchors\opening_gap_walk_forward_strict_context_summary.parquet | candidate summary parquet |
| data\ml\anchors\opening_gap_walk_forward_strict_context_folds.csv | per-fold CSV |
| data\ml\anchors\opening_gap_walk_forward_strict_context_folds.parquet | per-fold parquet |

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
| at_fire | all | label.strict.next_240m.unfilled_clean_continuation | 6 | 5157 | 0.827 | 0.821 | 0.798 | 0.027 | 68.9% | 60.7% | 47.3% |
| at_fire | all | label.strict.next_60m.partial_touch_rejected | 6 | 5157 | 0.826 | 0.835 | 0.792 | 0.024 | 89.9% | 77.4% | 57.0% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 6 | 5157 | 0.825 | 0.806 | 0.791 | 0.034 | 40.5% | 27.9% | 31.2% |
| at_fire | all | label.strict.next_1d.unfilled_clean_continuation | 6 | 5157 | 0.823 | 0.803 | 0.794 | 0.032 | 39.7% | 24.7% | 30.4% |
| at_fire | gap_down | label.strict.next_240m.unfilled_clean_continuation | 6 | 2303 | 0.822 | 0.852 | 0.710 | 0.063 | 66.9% | 41.2% | 46.2% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 6 | 2854 | 0.822 | 0.839 | 0.734 | 0.048 | 68.7% | 48.1% | 46.0% |
| at_fire | gap_up | label.strict.next_240m.unfilled_clean_continuation | 6 | 2854 | 0.814 | 0.822 | 0.759 | 0.031 | 64.6% | 44.4% | 42.8% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 6 | 2854 | 0.787 | 0.778 | 0.736 | 0.047 | 36.3% | 7.4% | 26.1% |
| at_fire | gap_up | label.strict.next_1d.unfilled_clean_continuation | 6 | 2854 | 0.783 | 0.777 | 0.736 | 0.040 | 35.5% | 7.4% | 25.4% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 2020 | 886 | 13.8% | 0.808 | 0.862 | 0.862 | 89 | 43.8% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 2021 | 834 | 5.9% | 0.805 | 0.944 | 0.941 | 84 | 31.0% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 2022 | 854 | 8.2% | 0.791 | 0.904 | 0.918 | 86 | 27.9% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 2023 | 844 | 7.6% | 0.802 | 0.927 | 0.924 | 85 | 31.8% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 2024 | 872 | 9.5% | 0.861 | 0.909 | 0.905 | 88 | 51.1% |
| at_fire | all | label.strict.next_1d.partial_touch_rejected | 2025 | 867 | 10.8% | 0.882 | 0.908 | 0.892 | 87 | 57.5% |
| at_fire | all | label.strict.next_1d.unfilled_clean_continuation | 2020 | 886 | 13.8% | 0.802 | 0.862 | 0.862 | 89 | 48.3% |
| at_fire | all | label.strict.next_1d.unfilled_clean_continuation | 2021 | 834 | 5.9% | 0.802 | 0.944 | 0.941 | 84 | 26.2% |
| at_fire | all | label.strict.next_1d.unfilled_clean_continuation | 2022 | 854 | 8.2% | 0.794 | 0.911 | 0.918 | 86 | 31.4% |
| at_fire | all | label.strict.next_1d.unfilled_clean_continuation | 2023 | 844 | 7.3% | 0.804 | 0.927 | 0.927 | 85 | 24.7% |
| at_fire | all | label.strict.next_1d.unfilled_clean_continuation | 2024 | 872 | 9.5% | 0.856 | 0.912 | 0.905 | 88 | 50.0% |
| at_fire | all | label.strict.next_1d.unfilled_clean_continuation | 2025 | 867 | 10.8% | 0.878 | 0.915 | 0.892 | 87 | 57.5% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 2020 | 886 | 27.0% | 0.875 | 0.823 | 0.730 | 89 | 79.8% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 2021 | 834 | 16.3% | 0.805 | 0.865 | 0.837 | 84 | 64.3% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 2022 | 854 | 23.7% | 0.835 | 0.816 | 0.763 | 86 | 76.7% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 2023 | 844 | 21.1% | 0.815 | 0.850 | 0.789 | 85 | 80.0% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 2024 | 872 | 21.9% | 0.805 | 0.829 | 0.781 | 88 | 73.9% |
| at_fire | all | label.strict.next_240m.partial_touch_rejected | 2025 | 867 | 24.8% | 0.885 | 0.856 | 0.752 | 87 | 80.5% |
| at_fire | all | label.strict.next_240m.unfilled_clean_continuation | 2020 | 886 | 26.3% | 0.858 | 0.804 | 0.737 | 89 | 73.0% |
| at_fire | all | label.strict.next_240m.unfilled_clean_continuation | 2021 | 834 | 16.1% | 0.807 | 0.853 | 0.839 | 84 | 60.7% |
| at_fire | all | label.strict.next_240m.unfilled_clean_continuation | 2022 | 854 | 23.2% | 0.835 | 0.816 | 0.768 | 86 | 65.1% |
| at_fire | all | label.strict.next_240m.unfilled_clean_continuation | 2023 | 844 | 20.1% | 0.798 | 0.827 | 0.799 | 85 | 68.2% |
| at_fire | all | label.strict.next_240m.unfilled_clean_continuation | 2024 | 872 | 21.2% | 0.799 | 0.825 | 0.788 | 88 | 68.2% |
| at_fire | all | label.strict.next_240m.unfilled_clean_continuation | 2025 | 867 | 22.5% | 0.864 | 0.837 | 0.775 | 87 | 78.2% |
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
| at_fire | gap_down | label.strict.next_240m.unfilled_clean_continuation | 2020 | 407 | 26.5% | 0.881 | 0.838 | 0.735 | 41 | 87.8% |
| at_fire | gap_down | label.strict.next_240m.unfilled_clean_continuation | 2021 | 294 | 16.3% | 0.873 | 0.871 | 0.837 | 30 | 73.3% |
| at_fire | gap_down | label.strict.next_240m.unfilled_clean_continuation | 2022 | 411 | 28.2% | 0.833 | 0.783 | 0.718 | 42 | 71.4% |
| at_fire | gap_down | label.strict.next_240m.unfilled_clean_continuation | 2023 | 427 | 20.1% | 0.767 | 0.799 | 0.799 | 43 | 55.8% |
| at_fire | gap_down | label.strict.next_240m.unfilled_clean_continuation | 2024 | 337 | 12.2% | 0.710 | 0.887 | 0.878 | 34 | 41.2% |
| at_fire | gap_down | label.strict.next_240m.unfilled_clean_continuation | 2025 | 427 | 21.3% | 0.872 | 0.829 | 0.787 | 43 | 72.1% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 2020 | 479 | 14.0% | 0.785 | 0.864 | 0.860 | 48 | 37.5% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 2021 | 540 | 5.2% | 0.739 | 0.937 | 0.948 | 54 | 7.4% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 2022 | 443 | 4.5% | 0.736 | 0.941 | 0.955 | 45 | 17.8% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 2023 | 417 | 9.6% | 0.771 | 0.909 | 0.904 | 42 | 28.6% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 2024 | 535 | 12.9% | 0.821 | 0.871 | 0.871 | 54 | 53.7% |
| at_fire | gap_up | label.strict.next_1d.partial_touch_rejected | 2025 | 440 | 15.0% | 0.871 | 0.855 | 0.850 | 44 | 72.7% |
| at_fire | gap_up | label.strict.next_1d.unfilled_clean_continuation | 2020 | 479 | 14.0% | 0.785 | 0.864 | 0.860 | 48 | 37.5% |
| at_fire | gap_up | label.strict.next_1d.unfilled_clean_continuation | 2021 | 540 | 5.2% | 0.739 | 0.937 | 0.948 | 54 | 7.4% |
| at_fire | gap_up | label.strict.next_1d.unfilled_clean_continuation | 2022 | 443 | 4.5% | 0.736 | 0.941 | 0.955 | 45 | 17.8% |
| at_fire | gap_up | label.strict.next_1d.unfilled_clean_continuation | 2023 | 417 | 9.1% | 0.770 | 0.914 | 0.909 | 42 | 28.6% |
| at_fire | gap_up | label.strict.next_1d.unfilled_clean_continuation | 2024 | 535 | 12.9% | 0.821 | 0.871 | 0.871 | 54 | 53.7% |
| at_fire | gap_up | label.strict.next_1d.unfilled_clean_continuation | 2025 | 440 | 15.0% | 0.847 | 0.855 | 0.850 | 44 | 68.2% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 2020 | 479 | 26.1% | 0.841 | 0.802 | 0.739 | 48 | 79.2% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 2021 | 540 | 15.9% | 0.734 | 0.804 | 0.841 | 54 | 48.1% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 2022 | 443 | 18.5% | 0.793 | 0.824 | 0.815 | 45 | 48.9% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 2023 | 417 | 20.6% | 0.836 | 0.830 | 0.794 | 42 | 64.3% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 2024 | 535 | 27.7% | 0.841 | 0.798 | 0.723 | 54 | 85.2% |
| at_fire | gap_up | label.strict.next_240m.partial_touch_rejected | 2025 | 440 | 27.3% | 0.889 | 0.836 | 0.727 | 44 | 86.4% |
| at_fire | gap_up | label.strict.next_240m.unfilled_clean_continuation | 2020 | 479 | 26.1% | 0.815 | 0.802 | 0.739 | 48 | 79.2% |
| at_fire | gap_up | label.strict.next_240m.unfilled_clean_continuation | 2021 | 540 | 15.9% | 0.759 | 0.811 | 0.841 | 54 | 44.4% |
| at_fire | gap_up | label.strict.next_240m.unfilled_clean_continuation | 2022 | 443 | 18.5% | 0.792 | 0.797 | 0.815 | 45 | 44.4% |
| at_fire | gap_up | label.strict.next_240m.unfilled_clean_continuation | 2023 | 417 | 20.1% | 0.828 | 0.818 | 0.799 | 42 | 61.9% |
| at_fire | gap_up | label.strict.next_240m.unfilled_clean_continuation | 2024 | 535 | 26.9% | 0.837 | 0.798 | 0.731 | 54 | 85.2% |
| at_fire | gap_up | label.strict.next_240m.unfilled_clean_continuation | 2025 | 440 | 23.6% | 0.854 | 0.811 | 0.764 | 44 | 72.7% |
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
