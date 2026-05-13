# ML snapshot leaderboard

_Generated `2026-05-12T14:31:50.943262+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots_xctx.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `high, low, all`
- Labels searched: `3` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshot_leaderboard_xctx.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshot_leaderboard_xctx.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 634 |
| schema_label_columns | 31 |
| grid_attempts | 9 |
| trained_ok | 9 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | low | label.ob_confirmation.did_confirm | 4646 | 96.7% | 0.901 | 0.967 | 0.967 | 465 | 100.0% | 3.3% |
| at_fire | all | label.ob_confirmation.did_confirm | 10146 | 95.8% | 0.864 | 0.958 | 0.958 | 1015 | 99.4% | 3.6% |
| at_fire | high | label.ob_confirmation.did_confirm | 5500 | 95.1% | 0.840 | 0.952 | 0.951 | 550 | 100.0% | 4.9% |
| at_fire | all | label.swept_level_recovery.level_recovered | 10146 | 70.5% | 0.795 | 0.766 | 0.705 | 1015 | 94.2% | 23.7% |
| at_fire | high | label.swept_level_recovery.level_recovered | 5500 | 65.3% | 0.785 | 0.728 | 0.653 | 550 | 91.5% | 26.1% |
| at_fire | low | label.swept_level_recovery.level_recovered | 4646 | 76.5% | 0.778 | 0.791 | 0.765 | 465 | 95.5% | 19.0% |
| at_fire | high | label.forward_continuation.continued | 5500 | 93.9% | 0.681 | 0.939 | 0.939 | 550 | 98.4% | 4.5% |
| at_fire | all | label.forward_continuation.continued | 10146 | 91.1% | 0.664 | 0.911 | 0.911 | 1015 | 95.9% | 4.7% |
| at_fire | low | label.forward_continuation.continued | 4646 | 87.9% | 0.595 | 0.878 | 0.879 | 465 | 91.4% | 3.5% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | low | label.ob_confirmation.did_confirm | sweep.day_of_week=6995; sweep.ctx.day_of_week_et=3168; sweep.ed.tracking_timeframe_1h=2020; xctx.n_fvg_side_bearish_24h=815; xctx.n_fvg_7d=756; xctx.minutes_since_last_smt_side_high_7d=745; sweep.event_type_pdl_4h=694; xctx.n_ob_side_bullish_7d=627; xctx.n_swing_side_low_7d=613; xctx.n_disp_7d=590 |
| at_fire | all | label.ob_confirmation.did_confirm | sweep.ctx.day_of_week_et=11590; sweep.day_of_week=7789; sweep.ed.tracking_timeframe_1h=5902; sweep.event_type_pwh_4h=3775; sweep.event_type_pdh_1h=3540; ts.day_of_week=3300; xctx.n_swing_side_low_7d=1713; xctx.minutes_since_last_ft_24h=1460; xctx.minutes_since_last_tp_24h=1422; xctx.n_fvg_side_bearish_7d=1044 |
| at_fire | high | label.ob_confirmation.did_confirm | sweep.ctx.day_of_week_et=6980; ts.day_of_week=4241; sweep.event_type_pdh_4h=3851; sweep.event_type_pwh_4h=2555; sweep.day_of_week=2507; xctx.minutes_since_last_tp_24h=1813; sweep.event_type_pdh_1h=1308; sweep.ed.tracking_timeframe_1h=1138; sweep.ed.mode_pdh_4h=910; xctx.n_swing_side_low_7d=868 |
| at_fire | all | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=63888; sweep.ed.swept_reference.level_price=12474; sweep.ed.tracking_timeframe_1h=9944; sweep.ed.manipulation_candle.high=6796; xctx.minutes_since_last_vp_24h=5977; xctx.n_fvg_side_bearish_24h=5315; ts.day_of_week=5090; xctx.n_eql_same_primary_7d=4948; sweep.side_high=4089; xctx.n_eql_side_high_7d=3101 |
| at_fire | high | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=37615; sweep.ed.manipulation_candle.open=4141; sweep.ed.swept_reference.level_price=4126; xctx.n_fvg_side_bearish_24h=3317; sweep.ed.tracking_timeframe_1h=3292; ts.year=2847; sweep.ed.manipulation_candle.close=2630; xctx.minutes_since_last_vp_24h=2557; ts.day_of_week=2194; xctx.n_eql_side_low_7d=1878 |
| at_fire | low | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=30135; sweep.ed.tracking_timeframe_1h=6667; xctx.n_eql_same_primary_7d=3620; sweep.ed.manipulation_candle.high=3437; sweep.ed.manipulation_candle.open=2902; xctx.n_fvg_side_bearish_24h=2701; ts.day_of_week=2428; xctx.n_eql_side_high_7d=2117; xctx.n_ob_side_bullish_7d=1854; xctx.n_eql_7d=1826 |
| at_fire | high | label.forward_continuation.continued | xctx.n_eql_side_low_7d=1775; sweep.event_type_ny_high_1h=1483; xctx.n_fvg_side_bullish_7d=1290; xctx.n_disp_side_bullish_7d=1123; ts.month=1068; xctx.n_orb_side_bearish_7d=1011; xctx.minutes_since_last_tp_24h=965; xctx.n_eql_side_high_7d=957; xctx.minutes_since_last_smt_side_low_7d=956; xctx.minutes_since_last_orb_side_doji_7d=940 |
| at_fire | all | label.forward_continuation.continued | xctx.minutes_since_last_tp_24h=3502; xctx.minutes_since_last_orb_side_doji_7d=2101; sweep.side_high=1990; xctx.n_fvg_side_bullish_7d=1826; xctx.n_disp_7d=1792; xctx.minutes_since_last_smt_side_low_7d=1695; xctx.n_eql_side_low_7d=1553; xctx.total_events_7d=1534; xctx.n_ob_side_bearish_7d=1483; xctx.n_swing_7d=1404 |
| at_fire | low | label.forward_continuation.continued | xctx.minutes_since_last_orb_24h=2050; ts.year=1916; xctx.minutes_since_last_orb_side_doji_7d=1858; xctx.minutes_since_last_smt_side_low_7d=1685; xctx.n_fvg_7d=1631; xctx.minutes_since_last_smt_side_high_7d=1587; xctx.n_disp_side_bullish_7d=1428; xctx.n_swing_7d=1407; xctx.minutes_since_last_ft_side_doji_7d=1396; xctx.n_ob_side_bullish_7d=1392 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
