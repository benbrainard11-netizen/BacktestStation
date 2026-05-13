# ML snapshot model

_Generated `2026-05-11T04:29:50.944430+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots.schema.json`
- Snapshot: `at_period_close`
- Event type: `previous_day_smt`
- Side: `low`
- Label: `label.n1_thesis_confirmed_strict`
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Dataset

| item | value |
|---|---|
| schema_rows | 4676 |
| filtered_rows | 1137 |
| original_feature_columns | 281 |
| usable_feature_columns | 100 |
| encoded_feature_columns | 152 |
| dropped_empty_or_constant_features | 180 |
| prediction_output | C:\Users\benbr\BacktestStation\data\ml\anchors\smt_snapshot_model_predictions.parquet |

## Metrics

| split | n | positives | actual_rate | auc | accuracy |
|---|---|---|---|---|---|
| train | 761 | 367 | 48.2% | 0.981 | 0.934 |
| val | 125 | 67 | 53.6% | 0.853 | 0.760 |
| test | 251 | 124 | 49.4% | 0.865 | 0.801 |

Majority-class test accuracy: `0.506`. Top 10% test bucket: `100.0%` on n=26.

## Feature Families

| family | usable_columns |
|---|---|
| pc | 68 |
| smt | 17 |
| ts | 4 |
| xd | 11 |

## Top LightGBM Features

| rank | feature | gain |
|---|---|---|
| 1 | pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window | 1619 |
| 2 | pc.minutes_since_last_sweep_low_same_primary_in_window | 1602 |
| 3 | pc.n_1h_fvg_bullish_same_primary_in_window | 1054 |
| 4 | pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window | 714 |
| 5 | pc.minutes_since_last_1h_disp_bullish_same_primary_in_window | 514 |
| 6 | pc.minutes_since_last_sweep_ny_low_1h_low_same_primary_in_window | 422 |
| 7 | pc.minutes_since_last_15m_fvg_bullish_same_primary_in_window | 392 |
| 8 | pc.n_1h_disp_bullish_same_primary_in_window | 343 |
| 9 | pc.n_15m_fvg_bullish_same_primary_in_window | 235 |
| 10 | pc.active_at_close | 227 |
| 11 | pc.minutes_since_last_4h_disp_bullish_same_primary_in_window | 225 |
| 12 | pc.n_sweep_ny_low_1h_low_same_primary_in_window | 213 |
| 13 | ts.day_of_week | 201 |
| 14 | smt.hour_of_day_utc | 179 |
| 15 | pc.n_sweep_low_same_primary_in_window | 167 |
| 16 | smt.ed.first_break_price | 165 |
| 17 | pc.minutes_since_last_1h_psp_bullish_in_window | 145 |
| 18 | smt.ed.symbol_states.NQ.c.0.reference_high | 106 |
| 19 | pc.minutes_since_last_ob_swept_pdl_4h_bullish_same_primary_in_window | 92 |
| 20 | smt.day_of_week | 89 |
| 21 | smt.ed.symbol_states.ES.c.0.reference_high | 89 |
| 22 | pc.minutes_since_last_sweep_pwl_4h_low_same_primary_in_window | 80 |
| 23 | smt.month | 74 |
| 24 | pc.minutes_since_last_sweep_pdl_4h_low_same_primary_in_window | 73 |
| 25 | smt.ed.symbol_states.YM.c.0.reference_high | 72 |

## Composite Cell Comparison

| slice | n | selected_label_rate | n1_or_n2_rate |
|---|---|---|---|
| all_test | 251 | 49.4% | 64.9% |
| model_top_bucket | 26 | 100.0% | 100.0% |
| manual_cell | 28 | 96.4% | 100.0% |
| overlap | 11 | 100.0% | 100.0% |
| model_only | 15 | 100.0% | 100.0% |
| manual_only | 17 | 94.1% | 100.0% |

## Calibration

| decile | n | mean_pred | actual_rate | plot |
|---|---|---|---|---|
| 1 | 26 | 0.082 | 7.7% | ## |
| 2 | 25 | 0.127 | 20.0% | #### |
| 3 | 25 | 0.167 | 24.0% | ##### |
| 4 | 25 | 0.250 | 20.0% | #### |
| 5 | 25 | 0.342 | 40.0% | ######## |
| 6 | 25 | 0.473 | 36.0% | ####### |
| 7 | 25 | 0.652 | 68.0% | ############## |
| 8 | 25 | 0.808 | 84.0% | ################# |
| 9 | 25 | 0.911 | 96.0% | ################### |
| 10 | 25 | 0.946 | 100.0% | #################### |

## Notes

- This runner uses only feature columns declared by the snapshot schema.
- `pc.*` features are valid only for `at_period_close`; the snapshot audit enforces that they are empty on `at_fire` rows.
- The handcrafted manual composite is excluded from training by default and is used as a benchmark slice.
- Categorical source columns one-hot encoded: 25.
