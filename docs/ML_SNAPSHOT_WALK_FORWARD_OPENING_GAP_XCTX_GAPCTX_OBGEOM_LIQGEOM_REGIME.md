# ML snapshot walk-forward validation

_Generated `2026-05-15T04:00:03.830749+00:00`._

## Setup

- Matrix: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.parquet`
- Schema: `data\ml\anchors\opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.schema.json`
- Leaderboard source: `data\ml\anchors\opening_gap_snapshot_leaderboard_xctx_gapctx_obgeom_liqgeom_regime.parquet`
- Event type: `all`
- Candidates: `16`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\opening_gap_walk_forward_xctx_gapctx_obgeom_liqgeom_regime_summary.csv | candidate summary CSV |
| data\ml\anchors\opening_gap_walk_forward_xctx_gapctx_obgeom_liqgeom_regime_summary.parquet | candidate summary parquet |
| data\ml\anchors\opening_gap_walk_forward_xctx_gapctx_obgeom_liqgeom_regime_folds.csv | per-fold CSV |
| data\ml\anchors\opening_gap_walk_forward_xctx_gapctx_obgeom_liqgeom_regime_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 9438 |
| schema_feature_columns | 2873 |
| schema_label_columns | 396 |
| folds_attempted | 96 |
| folds_ok | 93 |
| folds_skipped | 3 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_240m.range_expanded_2x_gap | 6 | 5157 | 0.974 | 0.974 | 0.965 | 0.006 | 100.0% | 100.0% | 9.9% |
| at_fire | all | label.next_60m.range_expanded_2x_gap | 6 | 5157 | 0.953 | 0.954 | 0.941 | 0.008 | 100.0% | 100.0% | 18.9% |
| at_fire | all | label.next_60m.resistance_rejection_3bar | 6 | 5157 | 0.942 | 0.944 | 0.922 | 0.012 | 91.0% | 73.9% | 61.8% |
| at_fire | all | label.next_60m.support_rejection_3bar | 6 | 5157 | 0.912 | 0.912 | 0.896 | 0.014 | 89.7% | 77.9% | 53.5% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 6 | 5157 | 0.837 | 0.825 | 0.805 | 0.032 | 75.9% | 64.3% | 53.4% |
| at_fire | all | label.next_240m.fully_filled | 6 | 5157 | 0.837 | 0.825 | 0.805 | 0.032 | 97.5% | 95.5% | 20.0% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 6 | 2303 | 0.833 | 0.854 | 0.738 | 0.055 | 72.2% | 52.9% | 50.4% |
| at_fire | gap_down | label.next_240m.fully_filled | 6 | 2303 | 0.833 | 0.854 | 0.738 | 0.055 | 96.5% | 94.1% | 18.3% |
| at_fire | gap_up | label.next_60m.fully_filled | 6 | 2854 | 0.832 | 0.830 | 0.783 | 0.040 | 95.4% | 93.2% | 29.0% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 6 | 2854 | 0.832 | 0.830 | 0.783 | 0.040 | 84.3% | 70.4% | 50.6% |
| at_fire | all | label.next_60m.fully_filled | 6 | 5157 | 0.827 | 0.835 | 0.789 | 0.024 | 93.8% | 87.1% | 26.7% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 6 | 5157 | 0.827 | 0.835 | 0.789 | 0.024 | 89.1% | 81.0% | 56.2% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 6 | 2854 | 0.822 | 0.839 | 0.734 | 0.048 | 68.7% | 48.1% | 46.0% |
| at_fire | gap_up | label.next_240m.fully_filled | 6 | 2854 | 0.822 | 0.839 | 0.734 | 0.048 | 98.0% | 94.4% | 20.6% |
| at_fire | all | label.next_1d.range_expanded_2x_gap | 5 | 4323 | 0.988 | 0.989 | 0.978 | 0.007 | 100.0% | 100.0% | 2.7% |
| at_fire | gap_up | label.next_240m.range_expanded_1x_gap | 4 | 1835 | 0.979 | 0.981 | 0.958 | 0.017 | 100.0% | 100.0% | 6.1% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_1d.range_expanded_2x_gap | 2020 | 886 | 97.4% | 0.984 | 0.976 | 0.974 | 89 | 100.0% |
| at_fire | all | label.next_1d.range_expanded_2x_gap | 2022 | 854 | 98.6% | 0.989 | 0.986 | 0.986 | 86 | 100.0% |
| at_fire | all | label.next_1d.range_expanded_2x_gap | 2023 | 844 | 98.3% | 0.990 | 0.983 | 0.983 | 85 | 100.0% |
| at_fire | all | label.next_1d.range_expanded_2x_gap | 2024 | 872 | 97.0% | 0.999 | 0.970 | 0.970 | 88 | 100.0% |
| at_fire | all | label.next_1d.range_expanded_2x_gap | 2025 | 867 | 94.9% | 0.978 | 0.961 | 0.949 | 87 | 100.0% |
| at_fire | all | label.next_240m.fully_filled | 2020 | 886 | 73.0% | 0.875 | 0.823 | 0.730 | 89 | 98.9% |
| at_fire | all | label.next_240m.fully_filled | 2021 | 834 | 83.7% | 0.805 | 0.865 | 0.837 | 84 | 98.8% |
| at_fire | all | label.next_240m.fully_filled | 2022 | 854 | 76.3% | 0.835 | 0.816 | 0.763 | 86 | 98.8% |
| at_fire | all | label.next_240m.fully_filled | 2023 | 844 | 78.9% | 0.815 | 0.850 | 0.789 | 85 | 96.5% |
| at_fire | all | label.next_240m.fully_filled | 2024 | 872 | 78.1% | 0.805 | 0.829 | 0.781 | 88 | 95.5% |
| at_fire | all | label.next_240m.fully_filled | 2025 | 867 | 75.2% | 0.885 | 0.856 | 0.752 | 87 | 96.6% |
| at_fire | all | label.next_240m.range_expanded_2x_gap | 2020 | 886 | 88.4% | 0.972 | 0.926 | 0.884 | 89 | 100.0% |
| at_fire | all | label.next_240m.range_expanded_2x_gap | 2021 | 834 | 95.3% | 0.975 | 0.966 | 0.953 | 84 | 100.0% |
| at_fire | all | label.next_240m.range_expanded_2x_gap | 2022 | 854 | 90.5% | 0.978 | 0.946 | 0.905 | 86 | 100.0% |
| at_fire | all | label.next_240m.range_expanded_2x_gap | 2023 | 844 | 89.8% | 0.972 | 0.943 | 0.898 | 85 | 100.0% |
| at_fire | all | label.next_240m.range_expanded_2x_gap | 2024 | 872 | 90.8% | 0.965 | 0.955 | 0.908 | 88 | 100.0% |
| at_fire | all | label.next_240m.range_expanded_2x_gap | 2025 | 867 | 85.7% | 0.984 | 0.953 | 0.857 | 87 | 100.0% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 2020 | 886 | 27.0% | 0.875 | 0.823 | 0.730 | 89 | 79.8% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 2021 | 834 | 16.3% | 0.805 | 0.865 | 0.837 | 84 | 64.3% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 2022 | 854 | 23.7% | 0.835 | 0.816 | 0.763 | 86 | 76.7% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 2023 | 844 | 21.1% | 0.815 | 0.850 | 0.789 | 85 | 80.0% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 2024 | 872 | 21.9% | 0.805 | 0.829 | 0.781 | 88 | 73.9% |
| at_fire | all | label.next_240m.unfilled_at_window_end | 2025 | 867 | 24.8% | 0.885 | 0.856 | 0.752 | 87 | 80.5% |
| at_fire | all | label.next_60m.fully_filled | 2020 | 886 | 62.6% | 0.849 | 0.795 | 0.626 | 89 | 89.9% |
| at_fire | all | label.next_60m.fully_filled | 2021 | 834 | 72.8% | 0.802 | 0.793 | 0.728 | 84 | 96.4% |
| at_fire | all | label.next_60m.fully_filled | 2022 | 854 | 64.5% | 0.837 | 0.789 | 0.645 | 86 | 96.5% |
| at_fire | all | label.next_60m.fully_filled | 2023 | 844 | 66.8% | 0.789 | 0.771 | 0.668 | 85 | 87.1% |
| at_fire | all | label.next_60m.fully_filled | 2024 | 872 | 70.3% | 0.833 | 0.815 | 0.703 | 88 | 95.5% |
| at_fire | all | label.next_60m.fully_filled | 2025 | 867 | 65.5% | 0.854 | 0.809 | 0.655 | 87 | 97.7% |
| at_fire | all | label.next_60m.range_expanded_2x_gap | 2020 | 886 | 80.6% | 0.941 | 0.869 | 0.806 | 89 | 100.0% |
| at_fire | all | label.next_60m.range_expanded_2x_gap | 2021 | 834 | 86.1% | 0.947 | 0.911 | 0.861 | 84 | 100.0% |
| at_fire | all | label.next_60m.range_expanded_2x_gap | 2022 | 854 | 81.5% | 0.958 | 0.919 | 0.815 | 86 | 100.0% |
| at_fire | all | label.next_60m.range_expanded_2x_gap | 2023 | 844 | 81.0% | 0.953 | 0.898 | 0.810 | 85 | 100.0% |
| at_fire | all | label.next_60m.range_expanded_2x_gap | 2024 | 872 | 81.4% | 0.954 | 0.890 | 0.814 | 88 | 100.0% |
| at_fire | all | label.next_60m.range_expanded_2x_gap | 2025 | 867 | 76.0% | 0.966 | 0.915 | 0.760 | 87 | 100.0% |
| at_fire | all | label.next_60m.resistance_rejection_3bar | 2020 | 886 | 30.6% | 0.942 | 0.865 | 0.694 | 89 | 94.4% |
| at_fire | all | label.next_60m.resistance_rejection_3bar | 2021 | 834 | 19.3% | 0.955 | 0.882 | 0.807 | 84 | 86.9% |
| at_fire | all | label.next_60m.resistance_rejection_3bar | 2022 | 854 | 33.7% | 0.956 | 0.874 | 0.663 | 86 | 97.7% |
| at_fire | all | label.next_60m.resistance_rejection_3bar | 2023 | 844 | 38.9% | 0.946 | 0.848 | 0.611 | 85 | 94.1% |
| at_fire | all | label.next_60m.resistance_rejection_3bar | 2024 | 872 | 22.0% | 0.922 | 0.849 | 0.780 | 88 | 73.9% |
| at_fire | all | label.next_60m.resistance_rejection_3bar | 2025 | 867 | 30.2% | 0.932 | 0.822 | 0.698 | 87 | 98.9% |
| at_fire | all | label.next_60m.support_rejection_3bar | 2020 | 886 | 37.1% | 0.915 | 0.824 | 0.629 | 89 | 92.1% |
| at_fire | all | label.next_60m.support_rejection_3bar | 2021 | 834 | 41.8% | 0.896 | 0.797 | 0.582 | 84 | 92.9% |
| at_fire | all | label.next_60m.support_rejection_3bar | 2022 | 854 | 34.1% | 0.908 | 0.829 | 0.659 | 86 | 77.9% |
| at_fire | all | label.next_60m.support_rejection_3bar | 2023 | 844 | 30.6% | 0.916 | 0.832 | 0.694 | 85 | 83.5% |
| at_fire | all | label.next_60m.support_rejection_3bar | 2024 | 872 | 38.8% | 0.900 | 0.794 | 0.612 | 88 | 97.7% |
| at_fire | all | label.next_60m.support_rejection_3bar | 2025 | 867 | 35.3% | 0.939 | 0.856 | 0.647 | 87 | 94.3% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 2020 | 886 | 37.4% | 0.849 | 0.795 | 0.626 | 89 | 93.3% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 2021 | 834 | 27.2% | 0.802 | 0.793 | 0.728 | 84 | 81.0% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 2022 | 854 | 35.5% | 0.837 | 0.789 | 0.645 | 86 | 97.7% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 2023 | 844 | 33.2% | 0.789 | 0.771 | 0.668 | 85 | 84.7% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 2024 | 872 | 29.7% | 0.833 | 0.815 | 0.703 | 88 | 89.8% |
| at_fire | all | label.next_60m.unfilled_at_window_end | 2025 | 867 | 34.5% | 0.854 | 0.809 | 0.655 | 87 | 88.5% |
| at_fire | gap_down | label.next_240m.fully_filled | 2020 | 407 | 72.0% | 0.896 | 0.857 | 0.720 | 41 | 95.1% |
| at_fire | gap_down | label.next_240m.fully_filled | 2021 | 294 | 83.0% | 0.873 | 0.891 | 0.830 | 30 | 96.7% |
| at_fire | gap_down | label.next_240m.fully_filled | 2022 | 411 | 70.8% | 0.843 | 0.803 | 0.708 | 42 | 100.0% |
| at_fire | gap_down | label.next_240m.fully_filled | 2023 | 427 | 78.5% | 0.782 | 0.813 | 0.785 | 43 | 97.7% |
| at_fire | gap_down | label.next_240m.fully_filled | 2024 | 337 | 87.2% | 0.738 | 0.878 | 0.872 | 34 | 94.1% |
| at_fire | gap_down | label.next_240m.fully_filled | 2025 | 427 | 77.8% | 0.865 | 0.857 | 0.778 | 43 | 95.3% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 2020 | 407 | 28.0% | 0.896 | 0.857 | 0.720 | 41 | 80.5% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 2021 | 294 | 17.0% | 0.873 | 0.891 | 0.830 | 30 | 86.7% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 2022 | 411 | 29.2% | 0.843 | 0.803 | 0.708 | 42 | 71.4% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 2023 | 427 | 21.5% | 0.782 | 0.813 | 0.785 | 43 | 69.8% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 2024 | 337 | 12.8% | 0.738 | 0.878 | 0.872 | 34 | 52.9% |
| at_fire | gap_down | label.next_240m.unfilled_at_window_end | 2025 | 427 | 22.2% | 0.865 | 0.857 | 0.778 | 43 | 72.1% |
| at_fire | gap_up | label.next_240m.fully_filled | 2020 | 479 | 73.9% | 0.841 | 0.802 | 0.739 | 48 | 97.9% |
| at_fire | gap_up | label.next_240m.fully_filled | 2021 | 540 | 84.1% | 0.734 | 0.804 | 0.841 | 54 | 94.4% |
| at_fire | gap_up | label.next_240m.fully_filled | 2022 | 443 | 81.5% | 0.793 | 0.824 | 0.815 | 45 | 97.8% |
| at_fire | gap_up | label.next_240m.fully_filled | 2023 | 417 | 79.4% | 0.836 | 0.830 | 0.794 | 42 | 97.6% |
| at_fire | gap_up | label.next_240m.fully_filled | 2024 | 535 | 72.3% | 0.841 | 0.798 | 0.723 | 54 | 100.0% |
| at_fire | gap_up | label.next_240m.fully_filled | 2025 | 440 | 72.7% | 0.889 | 0.836 | 0.727 | 44 | 100.0% |
| at_fire | gap_up | label.next_240m.range_expanded_1x_gap | 2022 | 443 | 96.4% | 0.968 | 0.964 | 0.964 | 45 | 100.0% |
| at_fire | gap_up | label.next_240m.range_expanded_1x_gap | 2023 | 417 | 95.7% | 0.958 | 0.957 | 0.957 | 42 | 100.0% |
| at_fire | gap_up | label.next_240m.range_expanded_1x_gap | 2024 | 535 | 94.6% | 0.996 | 0.957 | 0.946 | 54 | 100.0% |
| at_fire | gap_up | label.next_240m.range_expanded_1x_gap | 2025 | 440 | 89.1% | 0.994 | 0.909 | 0.891 | 44 | 100.0% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 2020 | 479 | 26.1% | 0.841 | 0.802 | 0.739 | 48 | 79.2% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 2021 | 540 | 15.9% | 0.734 | 0.804 | 0.841 | 54 | 48.1% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 2022 | 443 | 18.5% | 0.793 | 0.824 | 0.815 | 45 | 48.9% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 2023 | 417 | 20.6% | 0.836 | 0.830 | 0.794 | 42 | 64.3% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 2024 | 535 | 27.7% | 0.841 | 0.798 | 0.723 | 54 | 85.2% |
| at_fire | gap_up | label.next_240m.unfilled_at_window_end | 2025 | 440 | 27.3% | 0.889 | 0.836 | 0.727 | 44 | 86.4% |
| at_fire | gap_up | label.next_60m.fully_filled | 2020 | 479 | 63.7% | 0.833 | 0.764 | 0.637 | 48 | 97.9% |
| at_fire | gap_up | label.next_60m.fully_filled | 2021 | 540 | 71.7% | 0.784 | 0.763 | 0.717 | 54 | 94.4% |
| at_fire | gap_up | label.next_60m.fully_filled | 2022 | 443 | 68.4% | 0.783 | 0.754 | 0.684 | 45 | 93.3% |
| at_fire | gap_up | label.next_60m.fully_filled | 2023 | 417 | 68.8% | 0.827 | 0.746 | 0.688 | 42 | 95.2% |
| at_fire | gap_up | label.next_60m.fully_filled | 2024 | 535 | 64.3% | 0.884 | 0.807 | 0.643 | 54 | 98.1% |
| at_fire | gap_up | label.next_60m.fully_filled | 2025 | 440 | 61.4% | 0.879 | 0.818 | 0.614 | 44 | 93.2% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 2020 | 479 | 36.3% | 0.833 | 0.764 | 0.637 | 48 | 91.7% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 2021 | 540 | 28.3% | 0.784 | 0.763 | 0.717 | 54 | 70.4% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 2022 | 443 | 31.6% | 0.783 | 0.754 | 0.684 | 45 | 82.2% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 2023 | 417 | 31.2% | 0.827 | 0.746 | 0.688 | 42 | 76.2% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 2024 | 535 | 35.7% | 0.884 | 0.807 | 0.643 | 54 | 85.2% |
| at_fire | gap_up | label.next_60m.unfilled_at_window_end | 2025 | 440 | 38.6% | 0.879 | 0.818 | 0.614 | 44 | 100.0% |

## Skipped Folds

| status | count |
|---|---|
| skip_test_imbalance | 3 |

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
