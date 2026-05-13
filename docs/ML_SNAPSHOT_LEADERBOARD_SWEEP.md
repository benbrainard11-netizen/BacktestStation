# ML snapshot leaderboard

_Generated `2026-05-11T23:01:27.585626+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots.schema.json`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 42 |
| schema_label_columns | 31 |
| grid_attempts | 9 |
| trained_ok | 9 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | low | label.ob_confirmation.did_confirm | 4646 | 96.7% | 0.888 | 0.967 | 0.967 | 465 | 100.0% | 3.3% |
| at_fire | all | label.ob_confirmation.did_confirm | 10146 | 95.8% | 0.864 | 0.960 | 0.958 | 1015 | 99.5% | 3.7% |
| at_fire | high | label.ob_confirmation.did_confirm | 5500 | 95.1% | 0.839 | 0.953 | 0.951 | 550 | 100.0% | 4.9% |
| at_fire | low | label.swept_level_recovery.level_recovered | 4646 | 76.5% | 0.797 | 0.797 | 0.765 | 465 | 96.8% | 20.3% |
| at_fire | high | label.swept_level_recovery.level_recovered | 5500 | 65.3% | 0.794 | 0.714 | 0.653 | 550 | 93.5% | 28.1% |
| at_fire | all | label.swept_level_recovery.level_recovered | 10146 | 70.5% | 0.790 | 0.762 | 0.705 | 1015 | 94.4% | 23.9% |
| at_fire | high | label.forward_continuation.continued | 5500 | 93.9% | 0.673 | 0.939 | 0.939 | 550 | 98.7% | 4.8% |
| at_fire | all | label.forward_continuation.continued | 10146 | 91.1% | 0.628 | 0.911 | 0.911 | 1015 | 96.2% | 5.0% |
| at_fire | low | label.forward_continuation.continued | 4646 | 87.9% | 0.598 | 0.879 | 0.879 | 465 | 89.0% | 1.2% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | low | label.ob_confirmation.did_confirm | sweep.day_of_week=5624; sweep.ctx.day_of_week_et=4941; sweep.ed.sweep_depth_pts=3820; ts.month=2225; ts.year=2074; sweep.ed.tracking_timeframe_1h=1799; sweep.ed.swept_reference.level_price=1737; sweep.hour_of_day_utc=1248; sweep.ctx.hour_of_day_et=1095; ts.hour_of_day_utc=1087 |
| at_fire | all | label.ob_confirmation.did_confirm | sweep.ctx.day_of_week_et=11841; sweep.day_of_week=11090; sweep.ed.tracking_timeframe_1h=5973; sweep.ed.sweep_depth_pts=4126; sweep.event_type_pdh_1h=4014; sweep.event_type_pwh_4h=3092; ts.month=3019; ts.year=2698; sweep.hour_of_day_utc=2399; sweep.ctx.hour_of_day_et=1743 |
| at_fire | high | label.ob_confirmation.did_confirm | sweep.ctx.day_of_week_et=7880; ts.day_of_week=4899; sweep.event_type_pdh_4h=3821; sweep.ed.sweep_depth_pts=3074; ts.month=2051; sweep.event_type_pwh_4h=2028; sweep.ed.tracking_timeframe_1h=1939; sweep.hour_of_day_utc=1873; ts.year=1841; ts.hour_of_day_utc=1815 |
| at_fire | low | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=33934; sweep.ed.tracking_timeframe_1h=7340; sweep.ed.manipulation_candle.open=5621; sweep.ed.swept_reference.level_price=5265; sweep.ed.manipulation_candle.high=4933; ts.day_of_week=3245; sweep.ed.manipulation_candle.low=3078; ts.year=2983; ts.month=2510; sweep.ed.manipulation_candle.close=2391 |
| at_fire | high | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=35546; sweep.ed.manipulation_candle.open=5536; sweep.ed.swept_reference.level_price=4561; ts.year=3880; sweep.ed.tracking_timeframe_1h=3702; sweep.ed.manipulation_candle.high=3075; sweep.ed.manipulation_candle.close=2156; sweep.hour_of_day_utc=2086; ts.day_of_week=1666; ts.month=1152 |
| at_fire | all | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=68663; sweep.ed.swept_reference.level_price=16622; sweep.ed.tracking_timeframe_1h=12155; sweep.ed.manipulation_candle.high=10236; ts.year=7128; ts.day_of_week=5205; sweep.side_high=5141; sweep.ed.manipulation_candle.open=3982; sweep.ed.manipulation_candle.low=2471; sweep.hour_of_day_utc=2177 |
| at_fire | high | label.forward_continuation.continued | sweep.event_type_ny_high_1h=2283; ts.month=2265; sweep.ed.sweep_depth_pts=2123; ts.year=1702; sweep.month=1107; sweep.day_of_week=1046; sweep.ed.swept_reference.level_price=1045; sweep.hour_of_day_utc=988; ts.day_of_week=977; sweep.ctx.hour_of_day_et=911 |
| at_fire | all | label.forward_continuation.continued | ts.year=5486; sweep.ed.sweep_depth_pts=4711; sweep.ed.swept_reference.prior_period_label_session_ny=4414; ts.month=4151; sweep.ctx.hour_of_day_et=2200; ts.day_of_week=2122; sweep.hour_of_day_utc=2119; sweep.side_high=2089; sweep.ed.swept_reference.level_price=2056; sweep.ctx.day_of_week_et=1968 |
| at_fire | low | label.forward_continuation.continued | ts.year=4067; sweep.ed.sweep_depth_pts=3664; ts.month=2835; sweep.ed.swept_reference.level_price=2216; sweep.event_type_ny_low_1h=2142; sweep.ctx.day_of_week_et=1845; ts.day_of_week=1600; sweep.ctx.hour_of_day_et=1530; sweep.ed.manipulation_candle.open=1399; ts.hour_of_day_utc=1247 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
