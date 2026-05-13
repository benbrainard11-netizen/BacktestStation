# ML snapshot leaderboard

_Generated `2026-05-12T21:42:34.772640+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots_xctx_fvggeom.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshots_xctx_fvggeom.schema.json`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshot_leaderboard_xctx_fvggeom.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\sweep_snapshot_leaderboard_xctx_fvggeom.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 1085 |
| schema_label_columns | 31 |
| grid_attempts | 9 |
| trained_ok | 9 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | low | label.ob_confirmation.did_confirm | 4646 | 96.7% | 0.899 | 0.967 | 0.967 | 465 | 100.0% | 3.3% |
| at_fire | all | label.ob_confirmation.did_confirm | 10146 | 95.8% | 0.869 | 0.959 | 0.958 | 1015 | 99.6% | 3.8% |
| at_fire | high | label.ob_confirmation.did_confirm | 5500 | 95.1% | 0.840 | 0.952 | 0.951 | 550 | 100.0% | 4.9% |
| at_fire | all | label.swept_level_recovery.level_recovered | 10146 | 70.5% | 0.803 | 0.770 | 0.705 | 1015 | 95.1% | 24.6% |
| at_fire | low | label.swept_level_recovery.level_recovered | 4646 | 76.5% | 0.799 | 0.803 | 0.765 | 465 | 97.0% | 20.5% |
| at_fire | high | label.swept_level_recovery.level_recovered | 5500 | 65.3% | 0.796 | 0.743 | 0.653 | 550 | 92.9% | 27.6% |
| at_fire | high | label.forward_continuation.continued | 5500 | 93.9% | 0.732 | 0.939 | 0.939 | 550 | 99.1% | 5.2% |
| at_fire | all | label.forward_continuation.continued | 10146 | 91.1% | 0.696 | 0.911 | 0.911 | 1015 | 98.2% | 7.1% |
| at_fire | low | label.forward_continuation.continued | 4646 | 87.9% | 0.621 | 0.879 | 0.879 | 465 | 91.0% | 3.1% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | low | label.ob_confirmation.did_confirm | sweep.ctx.day_of_week_et=5655; sweep.day_of_week=4707; sweep.ed.tracking_timeframe_1h=1728; sweep.event_type_pdl_4h=1117; xctx.minutes_since_last_disp_side_bullish_7d=482; xctx.minutes_since_last_smt_side_high_7d=459; xctx.n_fvg_7d=441; xctx.n_fvg_side_bearish_24h=423; ts.month=423; xctx.minutes_since_last_psp_side_bullish_24h=400 |
| at_fire | all | label.ob_confirmation.did_confirm | sweep.ctx.day_of_week_et=13320; sweep.day_of_week=6928; sweep.ed.tracking_timeframe_1h=4465; sweep.event_type_pwh_4h=3396; sweep.event_type_pdh_1h=3335; ts.day_of_week=2450; xctx.minutes_since_last_ft_24h=1955; xctx.minutes_since_last_tp_24h=1369; sweep.ctx.tracking_timeframe_1h=1350; xctx.n_swing_side_low_7d=1227 |
| at_fire | high | label.ob_confirmation.did_confirm | sweep.ctx.day_of_week_et=7492; sweep.event_type_pdh_4h=4759; ts.day_of_week=3477; sweep.day_of_week=2742; sweep.event_type_pwh_4h=2180; xctx.minutes_since_last_tp_24h=1623; sweep.ed.tracking_timeframe_1h=1324; sweep.event_type_pdh_1h=1235; xctx.minutes_since_last_ft_24h=1120; sweep.event_type_pwh_daily=640 |
| at_fire | all | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=68328; sweep.ed.swept_reference.level_price=9561; sweep.ed.tracking_timeframe_1h=8632; sweep.ed.manipulation_candle.high=6465; ts.day_of_week=5153; xctx.minutes_since_last_vp_24h=4705; xctx.n_eql_same_primary_7d=3415; xctx.n_fvg_side_bearish_24h=2929; sweep.ctx.tracking_timeframe_1h=2419; xctx.minutes_since_last_smt_side_low_7d=2318 |
| at_fire | low | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=30241; sweep.ed.tracking_timeframe_1h=6745; ts.day_of_week=2612; sweep.ed.manipulation_candle.high=2518; xctx.n_fvg_side_bearish_24h=2057; xctx.n_eql_same_primary_7d=1809; xctx.n_ob_side_bullish_7d=1795; fvggeom.age_min_same_primary_bearish_untouched_above=1645; sweep.ed.manipulation_candle.open=1621; xctx.n_ob_side_bearish_24h=1583 |
| at_fire | high | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=37161; sweep.ed.tracking_timeframe_1h=4512; sweep.ed.swept_reference.level_price=3450; fvggeom.distance_pts_same_primary_any_side_untouched_above=2493; sweep.ed.manipulation_candle.open=2421; ts.day_of_week=2188; xctx.n_fvg_side_bearish_24h=2170; xctx.minutes_since_last_vp_24h=2140; sweep.ed.manipulation_candle.high=2113; ts.year=1680 |
| at_fire | high | label.forward_continuation.continued | xctx.n_eql_side_low_7d=1488; sweep.event_type_ny_high_1h=1267; fvggeom.distance_pts_any_symbol_any_side_untouched_above=1086; xctx.n_disp_side_bullish_7d=933; xctx.minutes_since_last_tp_24h=910; fvggeom.age_min_any_symbol_bearish_untouched_above=884; fvggeom.width_pts_same_primary_bullish_untouched_inside=824; fvggeom.width_pts_same_primary_bullish_untouched_above=804; fvggeom.age_min_same_primary_bullish_fully_filled_above=802; xctx.n_eql_7d=787 |
| at_fire | all | label.forward_continuation.continued | xctx.minutes_since_last_tp_24h=2957; xctx.minutes_since_last_orb_24h=1885; sweep.side_high=1703; fvggeom.age_min_same_primary_any_side_untouched_below=1400; sweep.ed.swept_reference.prior_period_label_session_ny=1319; xctx.minutes_since_last_orb_side_doji_7d=1019; fvggeom.age_min_same_primary_bearish_untouched_above=1018; xd.has_swing_in_24h=993; xctx.minutes_since_last_tp_side_bearish_7d=964; xctx.n_ob_side_bullish_7d=948 |
| at_fire | low | label.forward_continuation.continued | xctx.minutes_since_last_orb_24h=2009; xctx.n_ob_side_bullish_7d=1373; fvggeom.age_min_same_primary_any_side_untouched_below=1330; xctx.n_disp_side_bullish_7d=1325; fvggeom.age_min_same_primary_bullish_untouched_below=1323; xctx.minutes_since_last_orb_side_doji_7d=1290; xctx.minutes_since_last_tp_side_bearish_7d=1290; fvggeom.age_min_same_primary_bearish_fully_filled_below=1270; xctx.minutes_since_last_tp_side_bearish_24h=1235; ts.year=1198 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
