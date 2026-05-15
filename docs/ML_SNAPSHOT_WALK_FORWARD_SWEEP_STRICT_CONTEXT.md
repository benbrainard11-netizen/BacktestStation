# ML snapshot walk-forward validation

_Generated `2026-05-15T21:17:15.760953+00:00`._

## Setup

- Matrix: `data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.parquet`
- Schema: `data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.schema.json`
- Leaderboard source: explicit strict sweep candidates
- Event type: `all`
- Candidates: `4`
- Test years attempted: `2020, 2021, 2022, 2023, 2024, 2025`
- Fold rule: train through `test_year - 2`, validate on `test_year - 1`, test on `test_year`.
- Top bucket: `10%` of each fold's test rows
- Manual composite feature included in training: `False`
- Per-fold preprocessing selects usable columns from the training slice only; unseen future categorical values are ignored rather than creating future-known dummy columns.

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\sweep_walk_forward_strict_context_summary.csv | candidate summary CSV |
| data\ml\anchors\sweep_walk_forward_strict_context_summary.parquet | candidate summary parquet |
| data\ml\anchors\sweep_walk_forward_strict_context_folds.csv | per-fold CSV |
| data\ml\anchors\sweep_walk_forward_strict_context_folds.parquet | per-fold parquet |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 3131 |
| schema_label_columns | 105 |
| folds_attempted | 24 |
| folds_ok | 24 |
| folds_skipped | 0 |

## Candidate Summary

| snapshot | side | label | ok_folds | test_rows | mean_auc | median_auc | min_auc | std_auc | mean_top_rate | min_top_rate | mean_top_lift |
|---|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | high | label.strict.next_60m.sweep_failed_recovered | 6 | 15564 | 0.910 | 0.909 | 0.903 | 0.005 | 77.7% | 71.9% | 55.8% |
| at_fire | low | label.strict.next_60m.sweep_failed_recovered | 6 | 13160 | 0.908 | 0.908 | 0.904 | 0.003 | 81.9% | 74.5% | 54.8% |
| at_fire | all | label.strict.next_60m.sweep_failed_recovered | 6 | 28724 | 0.903 | 0.903 | 0.895 | 0.005 | 77.5% | 72.2% | 53.3% |
| at_fire | low | label.strict.next_60m.sweep_succeeded_held_rejection | 6 | 13160 | 0.896 | 0.899 | 0.882 | 0.009 | 55.9% | 48.2% | 40.5% |

## Fold Detail

| snapshot | side | label | test_year | test_n | base_rate | auc | acc | majority_acc | top_n | top_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.strict.next_60m.sweep_failed_recovered | 2020 | 4634 | 23.2% | 0.900 | 0.836 | 0.768 | 464 | 75.6% |
| at_fire | all | label.strict.next_60m.sweep_failed_recovered | 2021 | 4867 | 24.4% | 0.905 | 0.833 | 0.756 | 487 | 78.0% |
| at_fire | all | label.strict.next_60m.sweep_failed_recovered | 2022 | 4842 | 23.1% | 0.895 | 0.833 | 0.769 | 485 | 72.2% |
| at_fire | all | label.strict.next_60m.sweep_failed_recovered | 2023 | 4812 | 25.1% | 0.905 | 0.836 | 0.749 | 482 | 76.8% |
| at_fire | all | label.strict.next_60m.sweep_failed_recovered | 2024 | 4806 | 24.4% | 0.911 | 0.840 | 0.756 | 481 | 80.2% |
| at_fire | all | label.strict.next_60m.sweep_failed_recovered | 2025 | 4763 | 25.0% | 0.901 | 0.837 | 0.750 | 477 | 82.4% |
| at_fire | high | label.strict.next_60m.sweep_failed_recovered | 2020 | 2624 | 18.9% | 0.905 | 0.856 | 0.811 | 263 | 71.9% |
| at_fire | high | label.strict.next_60m.sweep_failed_recovered | 2021 | 2755 | 21.2% | 0.914 | 0.844 | 0.788 | 276 | 75.7% |
| at_fire | high | label.strict.next_60m.sweep_failed_recovered | 2022 | 2337 | 23.5% | 0.903 | 0.840 | 0.765 | 234 | 75.6% |
| at_fire | high | label.strict.next_60m.sweep_failed_recovered | 2023 | 2624 | 22.9% | 0.912 | 0.848 | 0.771 | 263 | 81.0% |
| at_fire | high | label.strict.next_60m.sweep_failed_recovered | 2024 | 2635 | 22.5% | 0.918 | 0.859 | 0.775 | 264 | 82.2% |
| at_fire | high | label.strict.next_60m.sweep_failed_recovered | 2025 | 2589 | 22.5% | 0.905 | 0.850 | 0.775 | 259 | 79.9% |
| at_fire | low | label.strict.next_60m.sweep_failed_recovered | 2020 | 2010 | 28.8% | 0.910 | 0.820 | 0.712 | 201 | 84.1% |
| at_fire | low | label.strict.next_60m.sweep_failed_recovered | 2021 | 2112 | 28.6% | 0.908 | 0.832 | 0.714 | 212 | 83.5% |
| at_fire | low | label.strict.next_60m.sweep_failed_recovered | 2022 | 2505 | 22.6% | 0.904 | 0.845 | 0.774 | 251 | 74.5% |
| at_fire | low | label.strict.next_60m.sweep_failed_recovered | 2023 | 2188 | 27.7% | 0.907 | 0.835 | 0.723 | 219 | 83.6% |
| at_fire | low | label.strict.next_60m.sweep_failed_recovered | 2024 | 2171 | 26.6% | 0.915 | 0.848 | 0.734 | 218 | 81.7% |
| at_fire | low | label.strict.next_60m.sweep_failed_recovered | 2025 | 2174 | 28.0% | 0.908 | 0.846 | 0.720 | 218 | 83.9% |
| at_fire | low | label.strict.next_60m.sweep_succeeded_held_rejection | 2020 | 2010 | 16.3% | 0.882 | 0.845 | 0.837 | 201 | 58.2% |
| at_fire | low | label.strict.next_60m.sweep_succeeded_held_rejection | 2021 | 2112 | 16.2% | 0.902 | 0.854 | 0.838 | 212 | 57.5% |
| at_fire | low | label.strict.next_60m.sweep_succeeded_held_rejection | 2022 | 2505 | 13.9% | 0.897 | 0.867 | 0.861 | 251 | 53.8% |
| at_fire | low | label.strict.next_60m.sweep_succeeded_held_rejection | 2023 | 2188 | 17.2% | 0.901 | 0.848 | 0.828 | 219 | 58.9% |
| at_fire | low | label.strict.next_60m.sweep_succeeded_held_rejection | 2024 | 2171 | 13.4% | 0.886 | 0.862 | 0.866 | 218 | 48.2% |
| at_fire | low | label.strict.next_60m.sweep_succeeded_held_rejection | 2025 | 2174 | 15.4% | 0.908 | 0.865 | 0.846 | 218 | 58.7% |

## Skipped Folds

None.

## Interpretation

- This is stricter than the Leaderboard because each test year is held out separately.
- Favor candidates with high mean AUC, acceptable min AUC, and positive top-bucket lift across most folds.
- Treat 2026 as partial data if it appears in skipped folds; a small current-year sample should not drive conclusions.
- Directional high/low range labels are retained for diagnostics, but `thesis_confirmed` labels are cleaner for trading thesis validation.
