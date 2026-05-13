# ML snapshot walk-forward validation

_Generated `2026-05-13T01:14:40.331155+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots_xctx.schema.json`
- Leaderboard source: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshot_leaderboard_xctx.parquet`
- Event type: `all`
- Candidates: `5`
- Test years attempted: `2022, 2023, 2024, 2025, 2026`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_walk_forward_xctx_top5_summary.csv | candidate summary CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_walk_forward_xctx_top5_summary.parquet | candidate summary parquet |
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_walk_forward_xctx_top5_folds.csv | per-fold CSV |
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_walk_forward_xctx_top5_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 209339 |
| schema_feature_columns | 637 |
| schema_label_columns | 67 |
| folds_attempted | 25 |
| folds_ok | 25 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | bullish | label.mitigation.fully_filled | 5 | 43033 | 0.773 | 0.776 | 0.737 | 0.020 | 93.7% | 92.8% | 16.7% |
| at_fire | all | label.mitigation.fully_filled | 5 | 80505 | 0.768 | 0.781 | 0.707 | 0.031 | 93.3% | 86.8% | 15.8% |
| at_fire | bullish | label.mitigation.mid_filled | 5 | 43033 | 0.761 | 0.762 | 0.726 | 0.022 | 94.5% | 92.9% | 13.7% |
| at_fire | all | label.mitigation.mid_filled | 5 | 80505 | 0.752 | 0.763 | 0.686 | 0.034 | 93.9% | 87.9% | 12.6% |
| at_fire | bearish | label.mitigation.fully_filled | 5 | 37472 | 0.751 | 0.774 | 0.662 | 0.045 | 91.2% | 79.4% | 13.2% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.mitigation.fully_filled | 2022 | 20042 | 77.9% | 0.784 | 0.817 | 0.779 | 2005 | 95.0% |
| at_fire | all | label.mitigation.fully_filled | 2023 | 18931 | 78.5% | 0.787 | 0.819 | 0.785 | 1894 | 95.1% |
| at_fire | all | label.mitigation.fully_filled | 2024 | 19308 | 77.7% | 0.781 | 0.808 | 0.777 | 1931 | 95.1% |
| at_fire | all | label.mitigation.fully_filled | 2025 | 19510 | 78.1% | 0.781 | 0.816 | 0.781 | 1951 | 94.7% |
| at_fire | all | label.mitigation.fully_filled | 2026 | 2714 | 75.3% | 0.707 | 0.783 | 0.753 | 272 | 86.8% |
| at_fire | all | label.mitigation.mid_filled | 2022 | 20042 | 81.8% | 0.776 | 0.842 | 0.818 | 2005 | 95.5% |
| at_fire | all | label.mitigation.mid_filled | 2023 | 18931 | 82.1% | 0.775 | 0.839 | 0.821 | 1894 | 96.1% |
| at_fire | all | label.mitigation.mid_filled | 2024 | 19308 | 81.4% | 0.763 | 0.830 | 0.814 | 1931 | 95.5% |
| at_fire | all | label.mitigation.mid_filled | 2025 | 19510 | 81.8% | 0.761 | 0.835 | 0.818 | 1951 | 94.4% |
| at_fire | all | label.mitigation.mid_filled | 2026 | 2714 | 79.3% | 0.686 | 0.808 | 0.793 | 272 | 87.9% |
| at_fire | bearish | label.mitigation.fully_filled | 2022 | 9907 | 77.0% | 0.760 | 0.802 | 0.770 | 991 | 93.2% |
| at_fire | bearish | label.mitigation.fully_filled | 2023 | 8819 | 79.8% | 0.782 | 0.829 | 0.798 | 882 | 95.5% |
| at_fire | bearish | label.mitigation.fully_filled | 2024 | 8665 | 79.0% | 0.774 | 0.819 | 0.790 | 867 | 93.3% |
| at_fire | bearish | label.mitigation.fully_filled | 2025 | 8775 | 78.6% | 0.776 | 0.822 | 0.786 | 878 | 94.6% |
| at_fire | bearish | label.mitigation.fully_filled | 2026 | 1306 | 75.9% | 0.662 | 0.780 | 0.759 | 131 | 79.4% |
| at_fire | bullish | label.mitigation.fully_filled | 2022 | 10135 | 78.8% | 0.796 | 0.825 | 0.788 | 1014 | 95.3% |
| at_fire | bullish | label.mitigation.fully_filled | 2023 | 10112 | 77.3% | 0.785 | 0.810 | 0.773 | 1012 | 93.7% |
| at_fire | bullish | label.mitigation.fully_filled | 2024 | 10643 | 76.7% | 0.770 | 0.796 | 0.767 | 1065 | 92.8% |
| at_fire | bullish | label.mitigation.fully_filled | 2025 | 10735 | 77.7% | 0.776 | 0.809 | 0.777 | 1074 | 93.2% |
| at_fire | bullish | label.mitigation.fully_filled | 2026 | 1408 | 74.8% | 0.737 | 0.783 | 0.748 | 141 | 93.6% |
| at_fire | bullish | label.mitigation.mid_filled | 2022 | 10135 | 82.8% | 0.795 | 0.853 | 0.828 | 1014 | 96.7% |
| at_fire | bullish | label.mitigation.mid_filled | 2023 | 10112 | 80.9% | 0.764 | 0.826 | 0.809 | 1012 | 93.3% |
| at_fire | bullish | label.mitigation.mid_filled | 2024 | 10643 | 80.4% | 0.757 | 0.823 | 0.804 | 1065 | 94.3% |
| at_fire | bullish | label.mitigation.mid_filled | 2025 | 10735 | 81.3% | 0.762 | 0.832 | 0.813 | 1074 | 95.2% |
| at_fire | bullish | label.mitigation.mid_filled | 2026 | 1408 | 78.5% | 0.726 | 0.797 | 0.785 | 141 | 92.9% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
