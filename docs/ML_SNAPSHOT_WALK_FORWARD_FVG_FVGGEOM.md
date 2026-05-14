# ML snapshot walk-forward validation

_Generated `2026-05-14T09:37:18.721866+00:00`._

## Setup

- Matrix: `data\ml\anchors\fvg_snapshots_xctx_fvggeom.parquet`
- Schema: `data\ml\anchors\fvg_snapshots_xctx_fvggeom.schema.json`
- Leaderboard source: `data\ml\anchors\fvg_snapshot_leaderboard_xctx_fvggeom.parquet`
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
| data\ml\anchors\fvg_walk_forward_fvggeom_summary.csv | candidate summary CSV |
| data\ml\anchors\fvg_walk_forward_fvggeom_summary.parquet | candidate summary parquet |
| data\ml\anchors\fvg_walk_forward_fvggeom_folds.csv | per-fold CSV |
| data\ml\anchors\fvg_walk_forward_fvggeom_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 209339 |
| schema_feature_columns | 1308 |
| schema_label_columns | 109 |
| folds_attempted | 72 |
| folds_ok | 72 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.zone_reaction.took_fvg_high | 6 | 116366 | 0.888 | 0.889 | 0.874 | 0.009 | 99.9% | 99.8% | 7.9% |
| at_fire | all | label.zone_reaction.took_fvg_low | 6 | 116366 | 0.862 | 0.867 | 0.835 | 0.017 | 99.9% | 99.6% | 10.5% |
| at_fire | all | label.zone_reaction.closed_outside_fvg_range | 6 | 116366 | 0.745 | 0.747 | 0.717 | 0.016 | 99.5% | 99.3% | 3.3% |
| at_fire | all | label.zone_reaction.closed_inside_fvg_range | 6 | 116366 | 0.745 | 0.747 | 0.717 | 0.016 | 12.4% | 10.4% | 8.6% |
| at_fire | bearish | label.zone_reaction.closed_outside_fvg_range | 6 | 53165 | 0.744 | 0.744 | 0.732 | 0.010 | 99.4% | 99.2% | 3.5% |
| at_fire | bearish | label.zone_reaction.closed_inside_fvg_range | 6 | 53165 | 0.744 | 0.744 | 0.732 | 0.010 | 13.5% | 11.6% | 9.4% |
| at_fire | bearish | label.zone_reaction.took_fvg_low_rejected_inside | 6 | 53165 | 0.744 | 0.740 | 0.731 | 0.013 | 13.1% | 10.3% | 9.0% |
| at_fire | all | label.mitigation.fully_filled | 6 | 116366 | 0.736 | 0.744 | 0.695 | 0.020 | 95.0% | 93.3% | 13.0% |
| at_fire | all | label.zone_reaction.took_fvg_low_rejected_inside | 6 | 116366 | 0.732 | 0.734 | 0.710 | 0.013 | 10.4% | 8.7% | 6.9% |
| at_fire | bullish | label.zone_reaction.closed_outside_fvg_range | 6 | 63201 | 0.732 | 0.735 | 0.692 | 0.026 | 99.5% | 99.3% | 3.1% |
| at_fire | bullish | label.zone_reaction.closed_inside_fvg_range | 6 | 63201 | 0.732 | 0.735 | 0.692 | 0.026 | 10.5% | 7.9% | 7.0% |
| at_fire | bullish | label.zone_reaction.took_fvg_high_rejected_inside | 6 | 63201 | 0.729 | 0.739 | 0.688 | 0.027 | 10.6% | 7.6% | 7.0% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.mitigation.fully_filled | 2020 | 19438 | 81.5% | 0.695 | 0.824 | 0.815 | 1944 | 93.3% |
| at_fire | all | label.mitigation.fully_filled | 2021 | 19137 | 81.6% | 0.731 | 0.825 | 0.816 | 1914 | 94.9% |
| at_fire | all | label.mitigation.fully_filled | 2022 | 20042 | 82.3% | 0.747 | 0.835 | 0.823 | 2005 | 95.1% |
| at_fire | all | label.mitigation.fully_filled | 2023 | 18931 | 82.8% | 0.750 | 0.835 | 0.828 | 1894 | 96.0% |
| at_fire | all | label.mitigation.fully_filled | 2024 | 19308 | 81.6% | 0.753 | 0.827 | 0.816 | 1931 | 95.5% |
| at_fire | all | label.mitigation.fully_filled | 2025 | 19510 | 82.0% | 0.741 | 0.831 | 0.820 | 1951 | 95.0% |
| at_fire | all | label.zone_reaction.closed_inside_fvg_range | 2020 | 19438 | 3.8% | 0.717 | 0.962 | 0.962 | 1944 | 10.4% |
| at_fire | all | label.zone_reaction.closed_inside_fvg_range | 2021 | 19137 | 3.7% | 0.735 | 0.962 | 0.963 | 1914 | 11.2% |
| at_fire | all | label.zone_reaction.closed_inside_fvg_range | 2022 | 20042 | 3.8% | 0.761 | 0.962 | 0.962 | 2005 | 13.2% |
| at_fire | all | label.zone_reaction.closed_inside_fvg_range | 2023 | 18931 | 3.7% | 0.744 | 0.963 | 0.963 | 1894 | 12.7% |
| at_fire | all | label.zone_reaction.closed_inside_fvg_range | 2024 | 19308 | 3.8% | 0.749 | 0.962 | 0.962 | 1931 | 12.5% |
| at_fire | all | label.zone_reaction.closed_inside_fvg_range | 2025 | 19510 | 3.8% | 0.765 | 0.962 | 0.962 | 1951 | 14.5% |
| at_fire | all | label.zone_reaction.closed_outside_fvg_range | 2020 | 19438 | 96.2% | 0.717 | 0.962 | 0.962 | 1944 | 99.3% |
| at_fire | all | label.zone_reaction.closed_outside_fvg_range | 2021 | 19137 | 96.3% | 0.735 | 0.962 | 0.963 | 1914 | 99.5% |
| at_fire | all | label.zone_reaction.closed_outside_fvg_range | 2022 | 20042 | 96.2% | 0.761 | 0.962 | 0.962 | 2005 | 99.7% |
| at_fire | all | label.zone_reaction.closed_outside_fvg_range | 2023 | 18931 | 96.3% | 0.744 | 0.963 | 0.963 | 1894 | 99.5% |
| at_fire | all | label.zone_reaction.closed_outside_fvg_range | 2024 | 19308 | 96.2% | 0.749 | 0.962 | 0.962 | 1931 | 99.8% |
| at_fire | all | label.zone_reaction.closed_outside_fvg_range | 2025 | 19510 | 96.2% | 0.765 | 0.962 | 0.962 | 1951 | 99.3% |
| at_fire | all | label.zone_reaction.took_fvg_high | 2020 | 19438 | 92.6% | 0.874 | 0.930 | 0.926 | 1944 | 99.8% |
| at_fire | all | label.zone_reaction.took_fvg_high | 2021 | 19137 | 92.7% | 0.899 | 0.931 | 0.927 | 1914 | 99.9% |
| at_fire | all | label.zone_reaction.took_fvg_high | 2022 | 20042 | 90.6% | 0.878 | 0.911 | 0.906 | 2005 | 100.0% |
| at_fire | all | label.zone_reaction.took_fvg_high | 2023 | 18931 | 92.7% | 0.886 | 0.930 | 0.927 | 1894 | 100.0% |
| at_fire | all | label.zone_reaction.took_fvg_high | 2024 | 19308 | 92.0% | 0.898 | 0.926 | 0.920 | 1931 | 99.9% |
| at_fire | all | label.zone_reaction.took_fvg_high | 2025 | 19510 | 92.0% | 0.892 | 0.924 | 0.920 | 1951 | 99.8% |
| at_fire | all | label.zone_reaction.took_fvg_low | 2020 | 19438 | 88.4% | 0.835 | 0.888 | 0.884 | 1944 | 99.6% |
| at_fire | all | label.zone_reaction.took_fvg_low | 2021 | 19137 | 88.4% | 0.843 | 0.888 | 0.884 | 1914 | 100.0% |
| at_fire | all | label.zone_reaction.took_fvg_low | 2022 | 20042 | 91.4% | 0.885 | 0.919 | 0.914 | 2005 | 100.0% |
| at_fire | all | label.zone_reaction.took_fvg_low | 2023 | 18931 | 89.6% | 0.874 | 0.900 | 0.896 | 1894 | 100.0% |
| at_fire | all | label.zone_reaction.took_fvg_low | 2024 | 19308 | 89.0% | 0.870 | 0.895 | 0.890 | 1931 | 99.9% |
| at_fire | all | label.zone_reaction.took_fvg_low | 2025 | 19510 | 89.5% | 0.863 | 0.900 | 0.895 | 1951 | 100.0% |
| at_fire | all | label.zone_reaction.took_fvg_low_rejected_inside | 2020 | 19438 | 3.6% | 0.710 | 0.964 | 0.964 | 1944 | 10.0% |
| at_fire | all | label.zone_reaction.took_fvg_low_rejected_inside | 2021 | 19137 | 3.5% | 0.721 | 0.965 | 0.965 | 1914 | 8.7% |
| at_fire | all | label.zone_reaction.took_fvg_low_rejected_inside | 2022 | 20042 | 3.6% | 0.742 | 0.964 | 0.964 | 2005 | 10.1% |
| at_fire | all | label.zone_reaction.took_fvg_low_rejected_inside | 2023 | 18931 | 3.5% | 0.733 | 0.965 | 0.965 | 1894 | 10.7% |
| at_fire | all | label.zone_reaction.took_fvg_low_rejected_inside | 2024 | 19308 | 3.6% | 0.736 | 0.964 | 0.964 | 1931 | 11.0% |
| at_fire | all | label.zone_reaction.took_fvg_low_rejected_inside | 2025 | 19510 | 3.6% | 0.750 | 0.964 | 0.964 | 1951 | 12.0% |
| at_fire | bearish | label.zone_reaction.closed_inside_fvg_range | 2020 | 8633 | 4.4% | 0.732 | 0.956 | 0.956 | 864 | 13.5% |
| at_fire | bearish | label.zone_reaction.closed_inside_fvg_range | 2021 | 8366 | 4.1% | 0.747 | 0.959 | 0.959 | 837 | 12.8% |
| at_fire | bearish | label.zone_reaction.closed_inside_fvg_range | 2022 | 9907 | 3.8% | 0.741 | 0.962 | 0.962 | 991 | 11.6% |
| at_fire | bearish | label.zone_reaction.closed_inside_fvg_range | 2023 | 8819 | 4.2% | 0.752 | 0.958 | 0.958 | 882 | 15.5% |
| at_fire | bearish | label.zone_reaction.closed_inside_fvg_range | 2024 | 8665 | 3.9% | 0.733 | 0.961 | 0.961 | 867 | 12.3% |
| at_fire | bearish | label.zone_reaction.closed_inside_fvg_range | 2025 | 8775 | 4.4% | 0.759 | 0.956 | 0.956 | 878 | 15.3% |
| at_fire | bearish | label.zone_reaction.closed_outside_fvg_range | 2020 | 8633 | 95.6% | 0.732 | 0.956 | 0.956 | 864 | 99.5% |
| at_fire | bearish | label.zone_reaction.closed_outside_fvg_range | 2021 | 8366 | 95.9% | 0.747 | 0.959 | 0.959 | 837 | 99.5% |
| at_fire | bearish | label.zone_reaction.closed_outside_fvg_range | 2022 | 9907 | 96.2% | 0.741 | 0.962 | 0.962 | 991 | 99.6% |
| at_fire | bearish | label.zone_reaction.closed_outside_fvg_range | 2023 | 8819 | 95.8% | 0.752 | 0.958 | 0.958 | 882 | 99.3% |
| at_fire | bearish | label.zone_reaction.closed_outside_fvg_range | 2024 | 8665 | 96.1% | 0.733 | 0.961 | 0.961 | 867 | 99.4% |
| at_fire | bearish | label.zone_reaction.closed_outside_fvg_range | 2025 | 8775 | 95.6% | 0.759 | 0.956 | 0.956 | 878 | 99.2% |
| at_fire | bearish | label.zone_reaction.took_fvg_low_rejected_inside | 2020 | 8633 | 4.3% | 0.731 | 0.957 | 0.957 | 864 | 13.2% |
| at_fire | bearish | label.zone_reaction.took_fvg_low_rejected_inside | 2021 | 8366 | 4.1% | 0.747 | 0.959 | 0.959 | 837 | 12.8% |
| at_fire | bearish | label.zone_reaction.took_fvg_low_rejected_inside | 2022 | 9907 | 3.8% | 0.733 | 0.962 | 0.962 | 991 | 10.3% |
| at_fire | bearish | label.zone_reaction.took_fvg_low_rejected_inside | 2023 | 8819 | 4.2% | 0.756 | 0.958 | 0.958 | 882 | 15.3% |
| at_fire | bearish | label.zone_reaction.took_fvg_low_rejected_inside | 2024 | 8665 | 3.9% | 0.732 | 0.961 | 0.961 | 867 | 12.5% |
| at_fire | bearish | label.zone_reaction.took_fvg_low_rejected_inside | 2025 | 8775 | 4.4% | 0.765 | 0.956 | 0.956 | 878 | 14.4% |
| at_fire | bullish | label.zone_reaction.closed_inside_fvg_range | 2020 | 10805 | 3.3% | 0.692 | 0.967 | 0.967 | 1081 | 7.9% |
| at_fire | bullish | label.zone_reaction.closed_inside_fvg_range | 2021 | 10771 | 3.5% | 0.711 | 0.965 | 0.965 | 1078 | 9.0% |
| at_fire | bullish | label.zone_reaction.closed_inside_fvg_range | 2022 | 10135 | 3.9% | 0.756 | 0.961 | 0.961 | 1014 | 12.1% |
| at_fire | bullish | label.zone_reaction.closed_inside_fvg_range | 2023 | 10112 | 3.4% | 0.719 | 0.966 | 0.966 | 1012 | 10.0% |
| at_fire | bullish | label.zone_reaction.closed_inside_fvg_range | 2024 | 10643 | 3.8% | 0.751 | 0.962 | 0.962 | 1065 | 11.4% |
| at_fire | bullish | label.zone_reaction.closed_inside_fvg_range | 2025 | 10735 | 3.4% | 0.760 | 0.966 | 0.966 | 1074 | 12.8% |
| at_fire | bullish | label.zone_reaction.closed_outside_fvg_range | 2020 | 10805 | 96.7% | 0.692 | 0.967 | 0.967 | 1081 | 99.5% |
| at_fire | bullish | label.zone_reaction.closed_outside_fvg_range | 2021 | 10771 | 96.5% | 0.711 | 0.965 | 0.965 | 1078 | 99.5% |
| at_fire | bullish | label.zone_reaction.closed_outside_fvg_range | 2022 | 10135 | 96.1% | 0.756 | 0.961 | 0.961 | 1014 | 99.8% |
| at_fire | bullish | label.zone_reaction.closed_outside_fvg_range | 2023 | 10112 | 96.6% | 0.719 | 0.966 | 0.966 | 1012 | 99.4% |
| at_fire | bullish | label.zone_reaction.closed_outside_fvg_range | 2024 | 10643 | 96.2% | 0.751 | 0.962 | 0.962 | 1065 | 99.5% |
| at_fire | bullish | label.zone_reaction.closed_outside_fvg_range | 2025 | 10735 | 96.6% | 0.760 | 0.966 | 0.966 | 1074 | 99.3% |
| at_fire | bullish | label.zone_reaction.took_fvg_high_rejected_inside | 2020 | 10805 | 3.3% | 0.688 | 0.967 | 0.967 | 1081 | 8.1% |
| at_fire | bullish | label.zone_reaction.took_fvg_high_rejected_inside | 2021 | 10771 | 3.5% | 0.701 | 0.965 | 0.965 | 1078 | 7.6% |
| at_fire | bullish | label.zone_reaction.took_fvg_high_rejected_inside | 2022 | 10135 | 3.9% | 0.756 | 0.961 | 0.961 | 1014 | 13.0% |
| at_fire | bullish | label.zone_reaction.took_fvg_high_rejected_inside | 2023 | 10112 | 3.4% | 0.724 | 0.966 | 0.966 | 1012 | 10.0% |
| at_fire | bullish | label.zone_reaction.took_fvg_high_rejected_inside | 2024 | 10643 | 3.8% | 0.754 | 0.962 | 0.962 | 1065 | 11.9% |
| at_fire | bullish | label.zone_reaction.took_fvg_high_rejected_inside | 2025 | 10735 | 3.4% | 0.753 | 0.966 | 0.966 | 1074 | 12.7% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
