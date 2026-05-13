# ML snapshot leaderboard

_Generated `2026-05-11T05:02:54.551828+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\smt_previous_day_snapshots.schema.json`
- Event type: `previous_day_smt`
- Snapshots: `at_fire, at_period_close`
- Sides: `low, high, all`
- Labels searched: `10` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\smt_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 4676 |
| schema_feature_columns | 281 |
| schema_label_columns | 18 |
| grid_attempts | 60 |
| trained_ok | 60 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_period_close | high | label.n1_thesis_confirmed_strict | 277 | 43.3% | 0.910 | 0.841 | 0.567 | 28 | 100.0% | 56.7% |
| at_period_close | high | label.n1_primary_took_period_n_low | 277 | 43.3% | 0.910 | 0.841 | 0.567 | 28 | 100.0% | 56.7% |
| at_period_close | all | label.n1_primary_took_period_n_low | 528 | 45.6% | 0.906 | 0.816 | 0.544 | 53 | 98.1% | 52.5% |
| at_period_close | all | label.n1_close_moved_with_thesis | 528 | 46.8% | 0.900 | 0.805 | 0.532 | 53 | 100.0% | 53.2% |
| at_period_close | high | label.n1_primary_took_period_n_high | 277 | 56.3% | 0.900 | 0.827 | 0.563 | 28 | 100.0% | 43.7% |
| at_period_close | high | label.n1_close_moved_with_thesis | 277 | 43.7% | 0.898 | 0.816 | 0.563 | 28 | 96.4% | 52.7% |
| at_period_close | all | label.n1_thesis_confirmed_strict | 528 | 46.2% | 0.895 | 0.830 | 0.538 | 53 | 100.0% | 53.8% |
| at_period_close | low | label.n1_primary_took_period_n_low | 251 | 48.2% | 0.893 | 0.805 | 0.518 | 26 | 96.2% | 47.9% |
| at_period_close | all | label.n1_primary_took_period_n_high | 528 | 53.0% | 0.889 | 0.811 | 0.530 | 53 | 100.0% | 47.0% |
| at_period_close | low | label.n1_close_moved_with_thesis | 251 | 50.2% | 0.878 | 0.801 | 0.498 | 26 | 100.0% | 49.8% |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | 277 | 55.6% | 0.871 | 0.780 | 0.556 | 28 | 100.0% | 44.4% |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | 277 | 54.2% | 0.870 | 0.773 | 0.542 | 28 | 100.0% | 45.8% |
| at_period_close | low | label.n1_thesis_confirmed_strict | 251 | 49.4% | 0.861 | 0.813 | 0.506 | 26 | 100.0% | 50.6% |
| at_period_close | low | label.n1_primary_took_period_n_high | 251 | 49.4% | 0.861 | 0.813 | 0.506 | 26 | 100.0% | 50.6% |
| at_period_close | all | label.n1_or_n2_close_moved_with_thesis | 528 | 60.0% | 0.858 | 0.759 | 0.600 | 53 | 100.0% | 40.0% |
| at_period_close | all | label.n1_or_n2_thesis_confirmed_strict | 528 | 59.3% | 0.853 | 0.771 | 0.593 | 53 | 100.0% | 40.7% |
| at_period_close | low | label.n1_or_n2_close_moved_with_thesis | 251 | 64.9% | 0.838 | 0.741 | 0.649 | 26 | 100.0% | 35.1% |
| at_period_close | low | label.n1_or_n2_thesis_confirmed_strict | 251 | 64.9% | 0.828 | 0.757 | 0.649 | 26 | 100.0% | 35.1% |
| at_period_close | all | label.n2_primary_took_period_n_low | 518 | 43.4% | 0.743 | 0.674 | 0.566 | 52 | 78.8% | 35.4% |
| at_period_close | high | label.n2_close_moved_with_thesis | 274 | 39.1% | 0.742 | 0.686 | 0.609 | 28 | 78.6% | 39.5% |
| at_period_close | low | label.n2_primary_took_period_n_low | 244 | 46.7% | 0.737 | 0.672 | 0.533 | 25 | 80.0% | 33.3% |
| at_period_close | all | label.n2_primary_took_period_n_high | 518 | 56.4% | 0.737 | 0.668 | 0.564 | 52 | 86.5% | 30.2% |
| at_period_close | high | label.n2_primary_took_period_n_high | 274 | 59.9% | 0.736 | 0.682 | 0.599 | 28 | 89.3% | 29.4% |
| at_period_close | all | label.n2_thesis_confirmed_strict | 518 | 46.1% | 0.735 | 0.649 | 0.539 | 52 | 88.5% | 42.3% |
| at_period_close | high | label.n2_thesis_confirmed_strict | 274 | 40.5% | 0.734 | 0.675 | 0.595 | 28 | 78.6% | 38.1% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_period_close | high | label.n1_thesis_confirmed_strict | pc.n_1h_disp_bearish_same_primary_in_window=2518; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1379; pc.minutes_since_last_sweep_high_same_primary_in_window=925; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=826; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=754; pc.n_1h_fvg_bearish_same_primary_in_window=719; pc.minutes_since_last_15m_fvg_bearish_same_primary_in_window=564; pc.n_15m_fvg_bearish_same_primary_in_window=416; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=314; pc.n_sweep_high_same_primary_in_window=284 |
| at_period_close | high | label.n1_primary_took_period_n_low | pc.n_1h_disp_bearish_same_primary_in_window=2518; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1379; pc.minutes_since_last_sweep_high_same_primary_in_window=925; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=826; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=754; pc.n_1h_fvg_bearish_same_primary_in_window=719; pc.minutes_since_last_15m_fvg_bearish_same_primary_in_window=564; pc.n_15m_fvg_bearish_same_primary_in_window=416; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=314; pc.n_sweep_high_same_primary_in_window=284 |
| at_period_close | all | label.n1_primary_took_period_n_low | pc.n_1h_disp_bearish_same_primary_in_window=2205; pc.n_sweep_ny_low_1h_low_same_primary_in_window=2025; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1656; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1301; pc.minutes_since_last_sweep_high_same_primary_in_window=1221; pc.minutes_since_last_sweep_low_same_primary_in_window=1137; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=875; pc.n_1h_fvg_bullish_same_primary_in_window=711; pc.minutes_since_last_15m_fvg_bullish_same_primary_in_window=657; pc.minutes_since_last_15m_fvg_bearish_same_primary_in_window=650 |
| at_period_close | all | label.n1_close_moved_with_thesis | pc.n_1h_disp_bearish_same_primary_in_window=2242; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=2041; pc.n_1h_fvg_bullish_same_primary_in_window=1330; pc.minutes_since_last_sweep_high_same_primary_in_window=1315; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1225; pc.minutes_since_last_sweep_low_same_primary_in_window=1132; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=1047; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=958; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=944; pc.minutes_since_last_1h_disp_bullish_same_primary_in_window=618 |
| at_period_close | high | label.n1_primary_took_period_n_high | pc.n_1h_disp_bearish_same_primary_in_window=2458; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=1438; pc.minutes_since_last_sweep_high_same_primary_in_window=1344; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=774; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=741; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=716; pc.minutes_since_last_15m_fvg_bearish_same_primary_in_window=519; pc.n_15m_fvg_bearish_same_primary_in_window=494; pc.n_1h_fvg_bearish_same_primary_in_window=341; pc.active_at_close=326 |
| at_period_close | high | label.n1_close_moved_with_thesis | pc.n_1h_disp_bearish_same_primary_in_window=3054; pc.minutes_since_last_sweep_high_same_primary_in_window=1097; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=1027; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=995; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=803; pc.minutes_since_last_15m_fvg_bearish_same_primary_in_window=512; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=508; pc.n_15m_fvg_bearish_same_primary_in_window=446; pc.minutes_since_last_ob_swept_pdh_4h_bearish_same_primary_in_window=198; smt.ed.first_break_price=185 |
| at_period_close | all | label.n1_thesis_confirmed_strict | pc.n_1h_disp_bearish_same_primary_in_window=2435; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1724; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1534; pc.n_1h_fvg_bullish_same_primary_in_window=1345; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=1315; pc.minutes_since_last_sweep_low_same_primary_in_window=1192; pc.minutes_since_last_sweep_high_same_primary_in_window=1028; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=870; pc.minutes_since_last_1h_disp_bullish_same_primary_in_window=715; pc.minutes_since_last_15m_fvg_bearish_same_primary_in_window=616 |
| at_period_close | low | label.n1_primary_took_period_n_low | pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=2057; pc.n_sweep_ny_low_1h_low_same_primary_in_window=1260; pc.minutes_since_last_sweep_low_same_primary_in_window=651; pc.n_1h_fvg_bullish_same_primary_in_window=487; pc.active_at_close=475; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=418; pc.minutes_since_last_15m_fvg_bullish_same_primary_in_window=403; pc.n_1h_disp_bullish_same_primary_in_window=283; pc.minutes_since_last_1h_disp_bullish_same_primary_in_window=256; pc.minutes_since_last_sweep_ny_low_1h_low_same_primary_in_window=215 |
| at_period_close | all | label.n1_primary_took_period_n_high | pc.minutes_since_last_sweep_low_same_primary_in_window=2025; pc.n_1h_disp_bearish_same_primary_in_window=1588; pc.minutes_since_last_sweep_high_same_primary_in_window=1461; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=1377; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1160; pc.n_1h_fvg_bullish_same_primary_in_window=1067; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=870; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=856; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=801; pc.minutes_since_last_15m_fvg_bearish_same_primary_in_window=615 |
| at_period_close | low | label.n1_close_moved_with_thesis | pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=2322; pc.minutes_since_last_sweep_low_same_primary_in_window=1065; pc.n_1h_fvg_bullish_same_primary_in_window=794; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=680; pc.minutes_since_last_1h_disp_bullish_same_primary_in_window=506; pc.active_at_close=444; pc.minutes_since_last_15m_fvg_bullish_same_primary_in_window=427; pc.minutes_since_last_sweep_ny_low_1h_low_same_primary_in_window=275; pc.minutes_since_last_1h_psp_bullish_in_window=244; pc.minutes_since_last_4h_disp_bullish_same_primary_in_window=239 |
| at_period_close | high | label.n1_or_n2_close_moved_with_thesis | pc.n_1h_disp_bearish_same_primary_in_window=1705; pc.minutes_since_last_sweep_high_same_primary_in_window=1078; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=974; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=950; pc.minutes_since_last_15m_fvg_bearish_same_primary_in_window=729; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=467; smt.ed.first_break_price=418; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=388; pc.minutes_since_last_1h_psp_bearish_in_window=342; pc.minutes_since_last_ob_swept_pdh_4h_bearish_same_primary_in_window=283 |
| at_period_close | high | label.n1_or_n2_thesis_confirmed_strict | pc.n_1h_disp_bearish_same_primary_in_window=1681; pc.minutes_since_last_sweep_high_same_primary_in_window=1008; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=880; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=811; pc.minutes_since_last_15m_fvg_bearish_same_primary_in_window=483; pc.minutes_since_last_4h_disp_bearish_same_primary_in_window=410; pc.minutes_since_last_1h_psp_bearish_in_window=368; smt.ed.first_break_price=358; pc.n_15m_fvg_bearish_same_primary_in_window=353; pc.minutes_since_last_4h_fvg_bearish_same_primary_in_window=302 |
| at_period_close | low | label.n1_thesis_confirmed_strict | pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1691; pc.minutes_since_last_sweep_low_same_primary_in_window=1252; pc.n_1h_fvg_bullish_same_primary_in_window=1017; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=607; pc.minutes_since_last_1h_disp_bullish_same_primary_in_window=547; pc.minutes_since_last_sweep_ny_low_1h_low_same_primary_in_window=368; pc.minutes_since_last_15m_fvg_bullish_same_primary_in_window=342; pc.n_sweep_ny_low_1h_low_same_primary_in_window=291; pc.minutes_since_last_4h_disp_bullish_same_primary_in_window=251; pc.n_1h_disp_bullish_same_primary_in_window=204 |
| at_period_close | low | label.n1_primary_took_period_n_high | pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=1691; pc.minutes_since_last_sweep_low_same_primary_in_window=1252; pc.n_1h_fvg_bullish_same_primary_in_window=1017; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=607; pc.minutes_since_last_1h_disp_bullish_same_primary_in_window=547; pc.minutes_since_last_sweep_ny_low_1h_low_same_primary_in_window=368; pc.minutes_since_last_15m_fvg_bullish_same_primary_in_window=342; pc.n_sweep_ny_low_1h_low_same_primary_in_window=291; pc.minutes_since_last_4h_disp_bullish_same_primary_in_window=251; pc.n_1h_disp_bullish_same_primary_in_window=204 |
| at_period_close | all | label.n1_or_n2_close_moved_with_thesis | pc.minutes_since_last_sweep_high_same_primary_in_window=1565; pc.minutes_since_last_4h_fvg_bullish_same_primary_in_window=1203; pc.n_1h_disp_bearish_same_primary_in_window=1167; pc.minutes_since_last_sweep_low_same_primary_in_window=884; pc.minutes_since_last_1h_fvg_bullish_same_primary_in_window=773; pc.minutes_since_last_1h_fvg_bearish_same_primary_in_window=757; pc.minutes_since_last_1h_disp_bearish_same_primary_in_window=643; pc.minutes_since_last_15m_fvg_bearish_same_primary_in_window=632; smt.ed.first_break_price=629; pc.minutes_since_last_15m_fvg_bullish_same_primary_in_window=613 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
