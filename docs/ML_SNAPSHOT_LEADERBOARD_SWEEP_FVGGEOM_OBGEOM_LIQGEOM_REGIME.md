# ML snapshot leaderboard

_Generated `2026-05-15T01:36:54.843259+00:00`._

## Setup

- Matrix: `data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet`
- Schema: `data\ml\anchors\sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `low, high, all`
- Labels searched: `35` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\sweep_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.csv | CSV leaderboard |
| data\ml\anchors\sweep_snapshot_leaderboard_xctx_fvggeom_obgeom_liqgeom_regime.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 52946 |
| schema_feature_columns | 3131 |
| schema_label_columns | 95 |
| grid_attempts | 105 |
| trained_ok | 103 |
| skipped | 2 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | low | label.ob_confirmation.did_confirm | 4646 | 96.7% | 0.900 | 0.967 | 0.967 | 465 | 100.0% | 3.3% |
| at_fire | low | label.manipulation_range_reaction.range_expanded_2x_manipulation | 4646 | 95.5% | 0.881 | 0.955 | 0.955 | 465 | 100.0% | 4.5% |
| at_fire | all | label.manipulation_range_reaction.range_expanded_2x_manipulation | 10146 | 96.0% | 0.876 | 0.960 | 0.960 | 1015 | 99.6% | 3.6% |
| at_fire | all | label.ob_confirmation.did_confirm | 10146 | 96.8% | 0.872 | 0.968 | 0.968 | 1015 | 99.7% | 2.9% |
| at_fire | high | label.manipulation_range_reaction.range_expanded_2x_manipulation | 5500 | 96.4% | 0.853 | 0.964 | 0.964 | 550 | 100.0% | 3.6% |
| at_fire | high | label.ob_confirmation.did_confirm | 5500 | 96.9% | 0.838 | 0.969 | 0.969 | 550 | 99.8% | 2.9% |
| at_fire | high | label.swept_reference_reaction.first_bar_down_then_final_up | 5500 | 12.1% | 0.827 | 0.877 | 0.879 | 550 | 36.0% | 23.9% |
| at_fire | high | label.swept_level_recovery.level_recovered | 5500 | 66.7% | 0.810 | 0.744 | 0.667 | 550 | 94.2% | 27.4% |
| at_fire | low | label.swept_level_recovery.level_recovered | 4646 | 78.2% | 0.808 | 0.821 | 0.782 | 465 | 97.2% | 19.0% |
| at_fire | all | label.swept_level_recovery.level_recovered | 10146 | 72.0% | 0.807 | 0.783 | 0.720 | 1015 | 94.8% | 22.8% |
| at_fire | low | label.swept_reference_reaction.first_bar_up_then_final_down | 4646 | 10.0% | 0.805 | 0.900 | 0.900 | 465 | 27.1% | 17.1% |
| at_fire | all | label.manipulation_range_reaction.range_expanded_1x_manipulation | 10146 | 99.5% | 0.756 | 0.995 | 0.995 | 1015 | 99.8% | 0.3% |
| at_fire | all | label.swept_reference_reaction.first_bar_down_then_final_up | 10146 | 21.6% | 0.748 | 0.785 | 0.784 | 1015 | 44.2% | 22.7% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | 10146 | 7.4% | 0.742 | 0.928 | 0.926 | 1015 | 26.0% | 18.7% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | 10146 | 92.6% | 0.739 | 0.927 | 0.926 | 1015 | 97.7% | 5.2% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_low | 4646 | 9.9% | 0.738 | 0.902 | 0.901 | 465 | 31.8% | 21.9% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_high | 4646 | 90.1% | 0.738 | 0.902 | 0.901 | 465 | 95.5% | 5.4% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_high | 5500 | 13.1% | 0.730 | 0.868 | 0.869 | 550 | 37.8% | 24.7% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_low | 5500 | 86.8% | 0.729 | 0.868 | 0.868 | 550 | 96.4% | 9.6% |
| at_fire | high | label.manipulation_range_reaction.one_sided_took_manipulation_low | 5500 | 5.2% | 0.720 | 0.948 | 0.948 | 550 | 16.7% | 11.5% |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_high | 10146 | 12.4% | 0.718 | 0.876 | 0.876 | 1015 | 35.2% | 22.7% |
| at_fire | high | label.forward_continuation.continued | 5500 | 94.7% | 0.717 | 0.947 | 0.947 | 550 | 98.5% | 3.9% |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_low | 10146 | 87.5% | 0.716 | 0.875 | 0.875 | 1015 | 96.2% | 8.7% |
| at_fire | high | label.manipulation_range_reaction.took_manipulation_high | 5500 | 94.6% | 0.706 | 0.946 | 0.946 | 550 | 99.3% | 4.6% |
| at_fire | all | label.forward_continuation.continued | 10146 | 91.8% | 0.705 | 0.918 | 0.918 | 1015 | 97.2% | 5.5% |
| at_fire | low | label.forward_continuation.continued | 4646 | 88.3% | 0.700 | 0.883 | 0.883 | 465 | 96.1% | 7.8% |
| at_fire | high | label.manipulation_range_reaction.swept_both_manipulation_sides | 5500 | 81.5% | 0.699 | 0.813 | 0.815 | 550 | 91.6% | 10.1% |
| at_fire | all | label.manipulation_range_reaction.swept_both_manipulation_sides | 10146 | 80.1% | 0.698 | 0.802 | 0.801 | 1015 | 90.0% | 9.9% |
| at_fire | low | label.manipulation_range_reaction.took_manipulation_low | 4646 | 88.3% | 0.687 | 0.883 | 0.883 | 465 | 96.1% | 7.8% |
| at_fire | low | label.manipulation_range_reaction.one_sided_took_manipulation_high | 4646 | 11.7% | 0.677 | 0.883 | 0.883 | 465 | 26.7% | 15.0% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | low | label.ob_confirmation.did_confirm | sweep.day_of_week=5802; sweep.ctx.day_of_week_et=4074; sweep.ed.tracking_timeframe_1h=1947; sweep.event_type_pdl_4h=848; regime.minutes_since_last_any_symbol_weekly_itr=528; sweep.ed.ref_type_pdl=500; xctx.minutes_since_last_ogap_side_gap_down_7d=480; regime.last_range_pts_any_symbol_any_itr=368; xctx.n_ob_side_bullish_7d=337; xctx.n_disp_side_bearish_7d=331 |
| at_fire | low | label.manipulation_range_reaction.range_expanded_2x_manipulation | xctx.minutes_since_last_ogap_24h=14035; xctx.minutes_since_last_ogap_7d=2598; fvggeom.age_min_same_primary_bearish_untouched_above=2489; xctx.minutes_since_last_fvg_same_primary_1h=1039; regime.minutes_since_last_same_primary_weekly_itr=939; xctx.n_fvg_side_bearish_1h=829; sweep.ed.sweep_depth_pts=602; xctx.minutes_since_last_tp_side_bearish_24h=562; xctx.n_macro_24h=537; regime.last_close_location_any_symbol_asia_itr=513 |
| at_fire | all | label.manipulation_range_reaction.range_expanded_2x_manipulation | xctx.minutes_since_last_ogap_24h=26812; xctx.minutes_since_last_ogap_7d=3211; regime.minutes_since_last_any_symbol_weekly_itr=2777; xctx.n_disp_4h=1531; xctx.minutes_since_last_fvg_same_primary_1h=1177; fvggeom.age_min_same_primary_bearish_untouched_above=1154; sweep.ed.sweep_depth_pts=1117; xctx.minutes_since_last_orb_24h=963; fvggeom.age_min_any_symbol_bearish_untouched_above=915; regime.last_close_location_any_symbol_weekly_itr=837 |
| at_fire | all | label.ob_confirmation.did_confirm | sweep.day_of_week=11678; sweep.ctx.day_of_week_et=7703; sweep.ed.tracking_timeframe_1h=4750; regime.minutes_since_last_any_symbol_weekly_itr=3333; sweep.ed.swept_reference.prior_period_label_globex_day=1571; sweep.ctx.scope_period_label_globex_day=1034; sweep.ctx.tracking_timeframe_1h=1014; xctx.minutes_since_last_ogap_24h=976; sweep.ed.swept_reference.prior_period_label_session_ny=919; xctx.minutes_since_last_ogap_side_gap_up_24h=621 |
| at_fire | high | label.manipulation_range_reaction.range_expanded_2x_manipulation | xctx.minutes_since_last_ogap_24h=8917; xctx.minutes_since_last_tp_24h=3017; xctx.minutes_since_last_ogap_7d=1098; regime.minutes_since_last_any_symbol_weekly_itr=1055; fvggeom.distance_pts_same_primary_bearish_untouched_below=867; xctx.n_orb_side_bullish_7d=682; fvggeom.distance_pts_same_primary_any_side_closed_through_below=634; regime.last_close_location_any_symbol_weekly_itr=454; xctx.n_ogap_side_gap_up_7d=448; xctx.n_macro_side_high_24h=435 |
| at_fire | high | label.ob_confirmation.did_confirm | regime.minutes_since_last_same_primary_weekly_itr=6962; sweep.day_of_week=5004; sweep.ed.tracking_timeframe_1h=2365; sweep.ctx.day_of_week_et=2001; sweep.ed.ref_type_pdh=1094; regime.minutes_since_last_any_symbol_weekly_itr=686; sweep.event_type_pdh_4h=615; xctx.total_events_7d=500; sweep.event_type_pwh_4h=411; sweep.ed.mode_ny_high_1h=369 |
| at_fire | high | label.swept_reference_reaction.first_bar_down_then_final_up | sweep.ed.sweep_depth_pts=21996; regime.last_close_location_same_primary_daily_itr=3456; sweep.hour_of_day_utc=1922; xctx.minutes_since_last_ogap_24h=1683; regime.last_direction_bullish_same_primary_daily_itr=1532; fvggeom.age_min_same_primary_any_side_untouched_above=1344; regime.last_range_pts_same_primary_daily_itr=1286; fvggeom.age_min_any_symbol_bullish_untouched_below=1017; sweep.event_type_pwh_daily=1007; regime.last_true_range_pts_same_primary_daily_itr=967 |
| at_fire | high | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=29004; regime.last_close_location_same_primary_daily_itr=7268; sweep.ed.tracking_timeframe_1h=2609; liqgeom.distance_pts_eql_any_symbol_high_fresh_below=2114; liqgeom.distance_pts_eql_same_primary_any_side_fresh_above=1687; liqgeom.age_min_eql_any_symbol_any_side_fresh_below=1664; fvggeom.distance_pts_same_primary_any_side_untouched_above=1575; xctx.n_fvg_side_bearish_24h=1243; liqgeom.age_min_eql_any_symbol_high_wick_taken_above=1236; liqgeom.distance_pts_eql_any_symbol_high_fresh_above=1169 |
| at_fire | low | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=28758; sweep.ed.tracking_timeframe_1h=5457; regime.last_range_percentile_prev10_same_primary_daily_itr=3798; regime.last_range_pts_same_primary_asia_itr=2706; liqgeom.age_min_eql_same_primary_any_side_fresh_above=1791; regime.last_true_range_pts_same_primary_london_itr=1470; regime.last_close_location_any_symbol_london_itr=1137; regime.last_close_location_same_primary_daily_itr=1027; xctx.n_ob_side_bearish_24h=1023; liqgeom.n_eql_same_primary_any_side_horizon_expired_within_100pts=968 |
| at_fire | all | label.swept_level_recovery.level_recovered | sweep.ed.sweep_depth_pts=68436; sweep.ed.tracking_timeframe_1h=5739; regime.last_range_pts_same_primary_asia_itr=4179; liqgeom.distance_pts_eql_any_symbol_high_fresh_below=4176; regime.last_range_percentile_prev10_same_primary_daily_itr=4055; regime.last_range_pts_same_primary_london_itr=3787; sweep.hour_of_day_utc=3462; xctx.minutes_since_last_itr_24h=3298; regime.last_close_location_same_primary_daily_itr=2846; sweep.ctx.tracking_timeframe_1h=2044 |
| at_fire | low | label.swept_reference_reaction.first_bar_up_then_final_down | sweep.ed.sweep_depth_pts=13356; xctx.minutes_since_last_ogap_24h=2305; sweep.hour_of_day_utc=1220; regime.last_range_pts_same_primary_london_itr=1113; regime.last_close_location_same_primary_daily_itr=1046; liqgeom.age_min_eql_any_symbol_low_fresh_below=669; regime.last_range_pts_same_primary_asia_itr=638; regime.last_true_range_pts_same_primary_london_itr=596; fvggeom.age_min_any_symbol_bearish_untouched_above=578; sweep.event_type_pwl_daily=562 |
| at_fire | all | label.manipulation_range_reaction.range_expanded_1x_manipulation | xctx.minutes_since_last_tp_24h=1047; liqgeom.spread_pts_eql_same_primary_high_close_taken_below=777; xctx.n_itr_side_bullish_7d=355; obgeom.age_min_same_primary_bullish_invalidated_below=333; fvggeom.distance_pts_same_primary_bullish_untouched_above=329; fvggeom.age_min_same_primary_bullish_closed_through_below=270; fvggeom.width_pts_any_symbol_bullish_tapped_above=231; regime.last_range_pts_any_symbol_asia_itr=221; xctx.n_swing_1h=220; xctx.minutes_since_last_tp_same_primary_24h=218 |
| at_fire | all | label.swept_reference_reaction.first_bar_down_then_final_up | sweep.ed.sweep_depth_pts=19920; sweep.side_high=19867; regime.last_close_location_same_primary_daily_itr=5708; sweep.side_low=4885; fvggeom.age_min_same_primary_any_side_untouched_above=3412; regime.last_direction_bullish_same_primary_daily_itr=2873; fvggeom.age_min_any_symbol_bullish_untouched_below=2158; liqgeom.age_min_any_source_same_primary_low_fresh_above=1948; xctx.minutes_since_last_ogap_24h=1608; liqgeom.age_min_eql_same_primary_any_side_fresh_above=1379 |
| at_fire | all | label.manipulation_range_reaction.one_sided_took_manipulation_low | xctx.minutes_since_last_ogap_24h=8902; fvggeom.age_min_same_primary_bearish_untouched_above=6051; liqgeom.age_min_eql_same_primary_any_side_fresh_above=1864; fvggeom.age_min_any_symbol_bearish_untouched_above=1829; fvggeom.age_min_same_primary_any_side_untouched_below=1341; liqgeom.age_min_eql_any_symbol_low_fresh_above=1281; fvggeom.age_min_same_primary_any_side_untouched_above=1220; regime.last_close_location_any_symbol_daily_itr=1213; fvggeom.width_pts_same_primary_bullish_untouched_inside=1149; regime.last_close_location_any_symbol_weekly_itr=1143 |
| at_fire | all | label.manipulation_range_reaction.took_manipulation_high | xctx.minutes_since_last_ogap_24h=9048; fvggeom.age_min_same_primary_bearish_untouched_above=6309; liqgeom.age_min_eql_same_primary_any_side_fresh_above=2177; fvggeom.age_min_any_symbol_bearish_untouched_above=2023; regime.last_close_location_any_symbol_daily_itr=1479; regime.last_close_location_any_symbol_weekly_itr=1430; liqgeom.age_min_eql_any_symbol_low_fresh_above=1345; regime.minutes_since_last_same_primary_weekly_itr=1290; fvggeom.distance_pts_same_primary_any_side_untouched_below=1263; fvggeom.age_min_same_primary_any_side_untouched_below=1222 |

## Skipped Summary

| status | count |
|---|---|
| skip_train_imbalance | 2 |

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
