# ML snapshot leaderboard

_Generated `2026-05-15T20:26:20.836212+00:00`._

## Setup

- Matrix: `data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.parquet`
- Schema: `data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `all, high, low`
- Labels searched: `10` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\sweep_snapshot_leaderboard_strict_context.csv | CSV leaderboard |
| data\ml\anchors\sweep_snapshot_leaderboard_strict_context.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 3131 |
| schema_label_columns | 105 |
| grid_attempts | 30 |
| trained_ok | 30 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | low | label.strict.next_60m.sweep_failed_recovered | 4652 | 27.1% | 0.912 | 0.846 | 0.729 | 466 | 82.8% | 55.8% |
| at_fire | high | label.strict.next_60m.sweep_failed_recovered | 5500 | 22.6% | 0.910 | 0.851 | 0.774 | 550 | 80.4% | 57.7% |
| at_fire | all | label.strict.next_60m.sweep_failed_recovered | 10152 | 24.7% | 0.903 | 0.839 | 0.753 | 1016 | 81.7% | 57.0% |
| at_fire | low | label.strict.next_60m.sweep_succeeded_held_rejection | 4652 | 14.1% | 0.897 | 0.864 | 0.859 | 466 | 52.4% | 38.2% |
| at_fire | all | label.strict.next_60m.sweep_succeeded_held_rejection | 10152 | 13.8% | 0.891 | 0.867 | 0.862 | 1016 | 52.8% | 38.9% |
| at_fire | high | label.strict.next_60m.sweep_succeeded_held_rejection | 5500 | 13.6% | 0.886 | 0.871 | 0.864 | 550 | 52.4% | 38.8% |
| at_fire | low | label.strict.next_240m.sweep_failed_recovered | 4652 | 29.4% | 0.859 | 0.788 | 0.706 | 466 | 77.0% | 47.7% |
| at_fire | high | label.strict.next_240m.sweep_failed_recovered | 5500 | 22.6% | 0.857 | 0.808 | 0.774 | 550 | 65.8% | 43.3% |
| at_fire | all | label.strict.next_240m.sweep_failed_recovered | 10152 | 25.7% | 0.854 | 0.798 | 0.743 | 1016 | 69.3% | 43.6% |
| at_fire | low | label.strict.next_240m.sweep_succeeded_held_rejection | 4652 | 18.0% | 0.834 | 0.825 | 0.820 | 466 | 51.1% | 33.1% |
| at_fire | high | label.strict.next_60m.sweep_extended_continuation | 5500 | 6.2% | 0.828 | 0.938 | 0.938 | 550 | 21.8% | 15.6% |
| at_fire | low | label.strict.next_60m.sweep_partial_retest_rejected | 4652 | 5.0% | 0.828 | 0.950 | 0.950 | 466 | 18.7% | 13.7% |
| at_fire | all | label.strict.next_240m.sweep_succeeded_held_rejection | 10152 | 16.5% | 0.824 | 0.837 | 0.835 | 1016 | 46.0% | 29.5% |
| at_fire | all | label.strict.next_60m.sweep_partial_retest_rejected | 10152 | 5.5% | 0.822 | 0.945 | 0.945 | 1016 | 18.1% | 12.6% |
| at_fire | high | label.strict.next_240m.sweep_succeeded_held_rejection | 5500 | 15.2% | 0.817 | 0.847 | 0.848 | 550 | 43.3% | 28.1% |
| at_fire | high | label.strict.next_60m.sweep_partial_retest_rejected | 5500 | 5.9% | 0.815 | 0.941 | 0.941 | 550 | 18.5% | 12.7% |
| at_fire | all | label.strict.next_60m.sweep_extended_continuation | 10152 | 6.4% | 0.815 | 0.935 | 0.936 | 1016 | 22.6% | 16.2% |
| at_fire | low | label.strict.next_60m.sweep_extended_continuation | 4652 | 6.7% | 0.807 | 0.934 | 0.933 | 466 | 21.7% | 14.9% |
| at_fire | high | label.strict.next_60m.sweep_failed_immediately | 5500 | 21.7% | 0.783 | 0.789 | 0.783 | 550 | 52.5% | 30.8% |
| at_fire | high | label.strict.next_240m.sweep_failed_immediately | 5500 | 21.8% | 0.778 | 0.785 | 0.782 | 550 | 49.6% | 27.9% |
| at_fire | high | label.strict.next_240m.sweep_extended_continuation | 5500 | 10.4% | 0.777 | 0.895 | 0.896 | 550 | 28.4% | 17.9% |
| at_fire | low | label.strict.next_240m.sweep_failed_immediately | 4652 | 18.4% | 0.770 | 0.819 | 0.816 | 466 | 50.4% | 32.0% |
| at_fire | all | label.strict.next_240m.sweep_partial_retest_rejected | 10152 | 9.0% | 0.762 | 0.910 | 0.910 | 1016 | 22.7% | 13.8% |
| at_fire | low | label.strict.next_60m.sweep_failed_immediately | 4652 | 18.4% | 0.762 | 0.816 | 0.816 | 466 | 49.4% | 31.0% |
| at_fire | low | label.strict.next_240m.sweep_partial_retest_rejected | 4652 | 9.5% | 0.755 | 0.905 | 0.905 | 466 | 20.6% | 11.1% |
| at_fire | high | label.strict.next_240m.sweep_partial_retest_rejected | 5500 | 8.5% | 0.752 | 0.915 | 0.915 | 550 | 20.0% | 11.5% |
| at_fire | all | label.strict.next_240m.sweep_failed_immediately | 10152 | 20.2% | 0.739 | 0.798 | 0.798 | 1016 | 46.9% | 26.7% |
| at_fire | all | label.strict.next_240m.sweep_extended_continuation | 10152 | 10.9% | 0.738 | 0.891 | 0.891 | 1016 | 28.1% | 17.2% |
| at_fire | all | label.strict.next_60m.sweep_failed_immediately | 10152 | 20.2% | 0.737 | 0.798 | 0.798 | 1016 | 47.4% | 27.3% |
| at_fire | low | label.strict.next_240m.sweep_extended_continuation | 4652 | 11.5% | 0.724 | 0.886 | 0.885 | 466 | 27.5% | 16.0% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | low | label.strict.next_60m.sweep_failed_recovered | sweep.ed.sweep_depth_pts=56369; xctx.minutes_since_last_ogap_24h=10728; regime.last_range_pts_same_primary_asia_itr=6231; regime.last_range_pts_same_primary_daily_itr=3168; regime.last_range_pts_same_primary_london_itr=3085; sweep.event_type_pwl_daily=2471; sweep.hour_of_day_utc=2356; regime.last_close_location_same_primary_daily_itr=2316; fvggeom.age_min_same_primary_any_side_untouched_below=2211; sweep.ed.ref_type_pwl=2207 |
| at_fire | high | label.strict.next_60m.sweep_failed_recovered | sweep.ed.sweep_depth_pts=60132; regime.last_direction_bullish_same_primary_daily_itr=8976; xctx.minutes_since_last_ogap_24h=7349; regime.last_close_location_same_primary_daily_itr=5672; regime.last_range_pts_same_primary_daily_itr=4196; fvggeom.age_min_same_primary_any_side_untouched_above=4082; fvggeom.distance_pts_any_symbol_bullish_untouched_above=3131; regime.last_true_range_pts_same_primary_daily_itr=2137; regime.last_true_range_pts_same_primary_weekly_itr=1716; liqgeom.age_min_any_source_same_primary_high_wick_taken_above=1715 |
| at_fire | all | label.strict.next_60m.sweep_failed_recovered | sweep.ed.sweep_depth_pts=125366; xctx.minutes_since_last_ogap_24h=22060; regime.last_range_pts_same_primary_asia_itr=11267; regime.last_range_pts_same_primary_daily_itr=9710; sweep.ed.tracking_timeframe_1d=6432; regime.last_range_pts_same_primary_london_itr=5063; regime.last_true_range_pts_same_primary_daily_itr=4951; sweep.ed.swept_reference.prior_period_label_globex_week=3362; sweep.hour_of_day_utc=3234; regime.last_true_range_pts_same_primary_weekly_itr=3145 |
| at_fire | low | label.strict.next_60m.sweep_succeeded_held_rejection | sweep.ed.sweep_depth_pts=44439; xctx.minutes_since_last_ogap_24h=8852; regime.last_range_pts_same_primary_london_itr=4264; regime.last_range_pts_same_primary_daily_itr=3197; regime.last_range_pts_same_primary_asia_itr=2781; sweep.ctx.hour_of_day_et=1575; xctx.minutes_since_last_ogap_7d=1020; regime.last_true_range_pts_same_primary_daily_itr=1013; regime.minutes_since_last_same_primary_london_itr=879; regime.minutes_since_last_same_primary_asia_itr=867 |
| at_fire | all | label.strict.next_60m.sweep_succeeded_held_rejection | sweep.ed.sweep_depth_pts=95911; xctx.minutes_since_last_ogap_24h=19125; regime.last_range_pts_same_primary_daily_itr=8285; regime.last_range_pts_same_primary_asia_itr=6309; regime.last_true_range_pts_same_primary_daily_itr=4236; regime.last_range_pts_same_primary_london_itr=3909; regime.last_range_pts_same_primary_weekly_itr=3092; regime.last_true_range_pts_same_primary_weekly_itr=2412; regime.minutes_since_last_same_primary_asia_itr=2180; xctx.minutes_since_last_ogap_7d=2082 |
| at_fire | high | label.strict.next_60m.sweep_succeeded_held_rejection | sweep.ed.sweep_depth_pts=46131; xctx.minutes_since_last_ogap_24h=10868; regime.last_range_pts_same_primary_daily_itr=2804; regime.last_direction_bullish_same_primary_daily_itr=2497; regime.last_close_location_same_primary_daily_itr=1786; regime.last_range_pts_same_primary_asia_itr=1743; regime.last_true_range_pts_same_primary_weekly_itr=1714; regime.last_true_range_pts_same_primary_ny_itr=1424; xctx.minutes_since_last_ogap_7d=1393; regime.last_true_range_pts_same_primary_daily_itr=1356 |
| at_fire | low | label.strict.next_240m.sweep_failed_recovered | sweep.ed.sweep_depth_pts=46538; xctx.minutes_since_last_ogap_24h=9430; regime.last_range_pts_same_primary_asia_itr=6990; regime.last_range_pts_same_primary_london_itr=2631; sweep.hour_of_day_utc=2479; sweep.ed.ref_type_pwl=2091; fvggeom.age_min_same_primary_bullish_untouched_below=1574; regime.last_close_location_same_primary_daily_itr=1471; xctx.minutes_since_last_ogap_7d=1346; fvggeom.age_min_same_primary_any_side_untouched_above=1330 |
| at_fire | high | label.strict.next_240m.sweep_failed_recovered | sweep.ed.sweep_depth_pts=45198; regime.last_close_location_same_primary_daily_itr=7698; xctx.minutes_since_last_ogap_24h=5818; regime.last_direction_bullish_same_primary_daily_itr=5788; fvggeom.age_min_same_primary_any_side_untouched_above=2821; fvggeom.distance_pts_any_symbol_bullish_untouched_above=2086; regime.last_range_pts_same_primary_daily_itr=2086; regime.last_range_pts_same_primary_london_itr=1856; sweep.ed.ref_type_pwh=1155; fvggeom.age_min_same_primary_bearish_untouched_above=1140 |
| at_fire | all | label.strict.next_240m.sweep_failed_recovered | sweep.ed.sweep_depth_pts=98486; xctx.minutes_since_last_ogap_24h=18888; regime.last_range_pts_same_primary_asia_itr=8659; regime.last_range_pts_same_primary_london_itr=7751; regime.last_range_pts_same_primary_daily_itr=5035; sweep.ed.tracking_timeframe_1d=4481; sweep.hour_of_day_utc=3483; sweep.side_high=2563; sweep.ed.swept_reference.prior_period_label_globex_week=2422; regime.last_range_pts_same_primary_ny_itr=1795 |
| at_fire | low | label.strict.next_240m.sweep_succeeded_held_rejection | sweep.ed.sweep_depth_pts=33235; xctx.minutes_since_last_ogap_24h=6564; regime.last_range_pts_same_primary_asia_itr=4675; regime.last_range_pts_same_primary_london_itr=2074; regime.minutes_since_last_same_primary_asia_itr=1186; regime.last_close_location_same_primary_daily_itr=1074; xctx.minutes_since_last_ogap_7d=1023; fvggeom.width_pts_any_symbol_bearish_untouched_above=802; sweep.ed.manipulation_candle.open=798; fvggeom.age_min_same_primary_any_side_untouched_above=689 |
| at_fire | high | label.strict.next_60m.sweep_extended_continuation | sweep.ed.sweep_depth_pts=6666; sweep.ctx.hour_of_day_et=4496; xctx.minutes_since_last_ogap_24h=1577; sweep.hour_of_day_utc=1524; fvggeom.age_min_same_primary_any_side_untouched_above=1088; sweep.ed.tracking_timeframe_1h=996; regime.last_close_location_any_symbol_daily_itr=829; liqgeom.age_min_any_source_same_primary_high_fresh_below=781; xctx.n_fvg_side_bullish_24h=687; regime.last_close_location_any_symbol_any_itr=662 |
| at_fire | low | label.strict.next_60m.sweep_partial_retest_rejected | sweep.ed.sweep_depth_pts=7973; xctx.minutes_since_last_ogap_24h=2115; sweep.ed.tracking_timeframe_1h=1338; regime.minutes_since_last_same_primary_asia_itr=1332; sweep.ctx.hour_of_day_et=1131; regime.last_close_location_same_primary_daily_itr=581; regime.minutes_since_last_any_symbol_asia_itr=575; xctx.n_ob_7d=520; liqgeom.age_min_any_source_any_symbol_low_fresh_above=505; liqgeom.distance_pts_eql_same_primary_any_side_fresh_below=423 |
| at_fire | all | label.strict.next_240m.sweep_succeeded_held_rejection | sweep.ed.sweep_depth_pts=66357; xctx.minutes_since_last_ogap_24h=14161; regime.last_range_pts_same_primary_london_itr=6581; regime.last_range_pts_same_primary_daily_itr=5576; regime.last_range_pts_same_primary_asia_itr=5427; regime.last_true_range_pts_same_primary_daily_itr=2984; regime.last_true_range_pts_same_primary_weekly_itr=2026; regime.minutes_since_last_same_primary_asia_itr=1717; sweep.ed.manipulation_candle.high=1297; regime.last_range_pts_same_primary_weekly_itr=1291 |
| at_fire | all | label.strict.next_60m.sweep_partial_retest_rejected | sweep.ed.sweep_depth_pts=23278; xctx.minutes_since_last_ogap_24h=8887; sweep.ed.tracking_timeframe_1h=2490; sweep.hour_of_day_utc=2000; regime.last_range_pts_same_primary_london_itr=1459; regime.minutes_since_last_any_symbol_asia_itr=1028; regime.minutes_since_last_same_primary_asia_itr=793; sweep.ctx.hour_of_day_et=665; regime.last_true_range_pts_same_primary_weekly_itr=625; xctx.minutes_since_last_ogap_4h=607 |
| at_fire | high | label.strict.next_240m.sweep_succeeded_held_rejection | sweep.ed.sweep_depth_pts=32127; xctx.minutes_since_last_ogap_24h=5920; regime.last_close_location_same_primary_daily_itr=4655; regime.last_range_pts_same_primary_london_itr=1238; regime.last_direction_bullish_same_primary_daily_itr=1123; liqgeom.n_eql_same_primary_low_fresh_within_100pts=1114; fvggeom.age_min_same_primary_bullish_untouched_below=1061; fvggeom.age_min_same_primary_any_side_untouched_above=1017; regime.last_true_range_pts_same_primary_daily_itr=889; liqgeom.age_min_eql_same_primary_any_side_fresh_above=882 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
