# ML snapshot leaderboard

_Generated `2026-05-13T21:34:17.412269+00:00`._

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
| schema_feature_columns | 1253 |
| schema_label_columns | 31 |
| grid_attempts | 9 |
| trained_ok | 9 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | low | label.ob_confirmation.did_confirm | 4646 | 96.7% | 0.891 | 0.967 | 0.967 | 465 | 100.0% | 3.3% |
| at_fire | all | label.ob_confirmation.did_confirm | 10146 | 95.8% | 0.872 | 0.958 | 0.958 | 1015 | 99.7% | 3.9% |
| at_fire | high | label.ob_confirmation.did_confirm | 5500 | 95.1% | 0.842 | 0.951 | 0.951 | 550 | 99.8% | 4.7% |
| at_fire | all | label.swept_level_recovery.level_recovered | 10146 | 70.5% | 0.803 | 0.769 | 0.705 | 1015 | 95.5% | 25.0% |
| at_fire | low | label.swept_level_recovery.level_recovered | 4646 | 76.5% | 0.801 | 0.804 | 0.765 | 465 | 96.3% | 19.8% |
| at_fire | high | label.swept_level_recovery.level_recovered | 5500 | 65.3% | 0.796 | 0.739 | 0.653 | 550 | 92.9% | 27.6% |
| at_fire | high | label.forward_continuation.continued | 5500 | 93.9% | 0.715 | 0.939 | 0.939 | 550 | 98.7% | 4.8% |
| at_fire | all | label.forward_continuation.continued | 10146 | 91.1% | 0.698 | 0.911 | 0.911 | 1015 | 97.4% | 6.3% |
| at_fire | low | label.forward_continuation.continued | 4646 | 87.9% | 0.644 | 0.879 | 0.879 | 465 | 92.5% | 4.6% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | low | label.ob_confirmation.did_confirm | sweep.day_of_week=5662; sweep.ctx.day_of_week_et=4711; sweep.ed.tracking_timeframe_1h=1938; sweep.event_type_pdl_4h=1021; xctx.minutes_since_last_disp_side_bullish_7d=569; xctx.minutes_since_last_ogap_side_gap_down_7d=467; xctx.n_disp_side_bearish_7d=433; xctx.n_ob_side_bullish_7d=433; xctx.minutes_since_last_smt_side_high_7d=425; sweep.ed.ref_type_pdl=405 |
| at_fire | all | label.ob_confirmation.did_confirm | sweep.ctx.day_of_week_et=11656; sweep.day_of_week=9052; sweep.ed.tracking_timeframe_1h=5520; sweep.event_type_pdh_1h=3032; sweep.event_type_pwh_4h=2975; xctx.minutes_since_last_ogap_24h=2669; ts.day_of_week=2185; xctx.minutes_since_last_ft_24h=1002; xctx.n_swing_side_low_7d=970; sweep.event_type_pdh_4h=943 |
| at_fire | high | label.ob_confirmation.did_confirm | sweep.ctx.day_of_week_et=7000; ts.day_of_week=4646; sweep.event_type_pdh_4h=3882; sweep.event_type_pwh_4h=2205; sweep.day_of_week=1587; sweep.event_type_pdh_1h=1580; xctx.minutes_since_last_ogap_24h=1536; xctx.minutes_since_last_tp_24h=1061; sweep.ed.tracking_timeframe_1h=884; sweep.event_type_pwh_daily=637 |
| at_fire | all | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=68473; sweep.ed.tracking_timeframe_1h=10187; sweep.ed.swept_reference.level_price=9595; ts.day_of_week=5121; sweep.ed.manipulation_candle.high=5120; xctx.minutes_since_last_itr_24h=4853; sweep.ed.manipulation_candle.open=3459; xctx.n_eql_same_primary_7d=3364; xctx.n_fvg_side_bearish_24h=2281; xctx.minutes_since_last_smt_side_low_7d=2035 |
| at_fire | low | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=31021; sweep.ed.tracking_timeframe_1h=7131; sweep.ed.manipulation_candle.high=3172; ts.day_of_week=2678; xctx.n_eql_same_primary_7d=1864; xctx.n_ob_side_bullish_7d=1783; xctx.n_ob_side_bearish_24h=1505; xctx.n_itr_side_bearish_4h=1451; sweep.ed.manipulation_candle.open=1339; fvggeom.distance_pts_same_primary_bullish_untouched_below=1256 |
| at_fire | high | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=36737; sweep.ed.tracking_timeframe_1h=4261; sweep.ed.swept_reference.level_price=3293; sweep.ed.manipulation_candle.high=2770; sweep.ed.manipulation_candle.open=2465; ts.year=2090; fvggeom.distance_pts_same_primary_any_side_untouched_above=2070; fvggeom.distance_pts_any_symbol_any_side_untouched_above=2044; ts.day_of_week=1933; xctx.n_fvg_side_bearish_24h=1518 |
| at_fire | high | label.forward_continuation.continued | sweep.event_type_ny_high_1h=1379; xctx.n_eql_side_low_7d=1286; fvggeom.distance_pts_any_symbol_any_side_untouched_above=1242; xctx.n_disp_side_bullish_7d=1035; xctx.minutes_since_last_tp_24h=827; fvggeom.width_pts_same_primary_bullish_untouched_inside=818; xctx.n_fvg_side_bullish_7d=777; fvggeom.age_min_any_symbol_bearish_untouched_above=751; fvggeom.width_pts_same_primary_bullish_untouched_above=705; sweep.ed.tracking_timeframe_1h=688 |
| at_fire | all | label.forward_continuation.continued | xctx.minutes_since_last_tp_24h=2562; xctx.minutes_since_last_orb_24h=2153; sweep.side_high=1851; fvggeom.age_min_same_primary_any_side_untouched_below=1368; sweep.ed.swept_reference.prior_period_label_session_ny=1330; fvggeom.age_min_same_primary_any_side_untouched_inside=1320; xctx.minutes_since_last_orb_side_doji_7d=1150; fvggeom.age_min_same_primary_any_side_untouched_above=1079; xd.has_swing_in_24h=1048; xctx.n_ob_side_bearish_7d=1031 |
| at_fire | low | label.forward_continuation.continued | xctx.minutes_since_last_orb_24h=1993; xctx.minutes_since_last_orb_side_doji_7d=1344; fvggeom.age_min_same_primary_any_side_untouched_below=1325; xctx.n_ob_side_bullish_7d=1242; xctx.minutes_since_last_smt_side_low_7d=1162; xctx.minutes_since_last_tp_side_bearish_7d=1132; ts.year=1084; xctx.n_disp_side_bullish_7d=1042; xctx.minutes_since_last_ogap_side_gap_down_24h=984; xctx.n_fvg_7d=981 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
