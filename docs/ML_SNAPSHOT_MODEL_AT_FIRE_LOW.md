# ML snapshot model

_Generated `2026-05-11T04:30:40.991724+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots.schema.json`
- Snapshot: `at_fire`
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
| usable_feature_columns | 32 |
| encoded_feature_columns | 38 |
| dropped_empty_or_constant_features | 248 |
| prediction_output | C:\Users\benbr\BacktestStation\data\ml\anchors\smt_snapshot_model_predictions_at_fire_low.parquet |

## Metrics

| split | n | positives | actual_rate | auc | accuracy |
|---|---|---|---|---|---|
| train | 761 | 367 | 48.2% | 0.789 | 0.710 |
| val | 125 | 67 | 53.6% | 0.589 | 0.560 |
| test | 251 | 124 | 49.4% | 0.511 | 0.478 |

Majority-class test accuracy: `0.506`. Top 10% test bucket: `61.5%` on n=26.

## Feature Families

| family | usable_columns |
|---|---|
| smt | 17 |
| ts | 4 |
| xd | 11 |

## Top LightGBM Features

| rank | feature | gain |
|---|---|---|
| 1 | smt.ed.symbol_states.YM.c.0.reference_high | 254 |
| 2 | smt.ed.symbol_states.ES.c.0.reference_high | 215 |
| 3 | ts.day_of_week | 157 |
| 4 | smt.ed.symbol_states.NQ.c.0.reference_high | 154 |
| 5 | smt.ed.symbol_states.ES.c.0.reference_low | 141 |
| 6 | smt.ed.first_break_price | 114 |
| 7 | smt.month | 92 |
| 8 | smt.ed.symbol_states.NQ.c.0.reference_low | 75 |
| 9 | smt.ctx.hour_of_day_et | 57 |
| 10 | smt.hour_of_day_utc | 42 |
| 11 | smt.day_of_week | 37 |
| 12 | smt.ed.symbol_states.YM.c.0.reference_low | 30 |
| 13 | ts.month | 15 |
| 14 | smt.year | 13 |
| 15 | smt.ctx.day_of_week_et | 10 |
| 16 | xd.has_psp_in_24h | 9 |
| 17 | ts.year | 7 |
| 18 | xd.has_disp_in_24h | 7 |
| 19 | ts.hour_of_day_utc | 7 |
| 20 | smt.ed.lagging_symbols_at_break__len | 5 |
| 21 | smt.primary_symbol_ES.c.0 | 4 |
| 22 | xd.has_eql_in_24h | 4 |
| 23 | smt.primary_symbol_NQ.c.0 | 3 |
| 24 | smt.ed.first_break_symbol_ES.c.0 | 3 |
| 25 | smt.ed.first_break_symbol_NQ.c.0 | 3 |

## Composite Cell Comparison

| slice | n | selected_label_rate | n1_or_n2_rate |
|---|---|---|---|
| all_test | 251 | 49.4% | 64.9% |
| model_top_bucket | 26 | 61.5% | 69.2% |
| manual_cell | 0 | - | - |
| overlap | 0 | - | - |
| model_only | 26 | 61.5% | 69.2% |
| manual_only | 0 | - | - |

## Calibration

| decile | n | mean_pred | actual_rate | plot |
|---|---|---|---|---|
| 1 | 26 | 0.413 | 42.3% | ######## |
| 2 | 25 | 0.443 | 48.0% | ########## |
| 3 | 25 | 0.474 | 64.0% | ############# |
| 4 | 25 | 0.491 | 52.0% | ########## |
| 5 | 25 | 0.501 | 40.0% | ######## |
| 6 | 25 | 0.514 | 44.0% | ######### |
| 7 | 25 | 0.528 | 56.0% | ########### |
| 8 | 25 | 0.536 | 44.0% | ######### |
| 9 | 25 | 0.544 | 44.0% | ######### |
| 10 | 25 | 0.551 | 60.0% | ############ |

## Notes

- This runner uses only feature columns declared by the snapshot schema.
- `pc.*` features are valid only for `at_period_close`; the snapshot audit enforces that they are empty on `at_fire` rows.
- The handcrafted manual composite is excluded from training by default and is used as a benchmark slice.
- Categorical source columns one-hot encoded: 2.
