# ML snapshot leaderboard

_Generated `2026-05-13T17:34:37.707891+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\itr_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\itr_snapshots_xctx.schema.json`
- Event type: `all`
- Snapshots: `at_fire, at_period_close`
- Sides: `bullish, bearish, all`
- Labels searched: `13` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\AppData\Local\Temp\itr_snapshot_leaderboard_xctx_20260513T173437Z.csv | CSV leaderboard |
| C:\Users\benbr\AppData\Local\Temp\itr_snapshot_leaderboard_xctx_20260513T173437Z.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 36095 |
| schema_feature_columns | 850 |
| schema_label_columns | 35 |
| grid_attempts | 78 |
| trained_ok | 39 |
| skipped | 39 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 3640 | 32.4% | 0.813 | 0.773 | 0.676 | 364 | 80.2% | 47.8% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 6801 | 31.2% | 0.803 | 0.771 | 0.688 | 681 | 77.1% | 45.9% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 3137 | 29.9% | 0.785 | 0.764 | 0.701 | 314 | 70.7% | 40.8% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 3640 | 32.3% | 0.783 | 0.745 | 0.677 | 364 | 75.8% | 43.5% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 6801 | 33.4% | 0.779 | 0.743 | 0.666 | 681 | 76.2% | 42.8% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 3137 | 34.5% | 0.764 | 0.724 | 0.655 | 314 | 77.1% | 42.5% |
| at_fire | all | label.next_interval.touched_interval_mid | 6801 | 43.0% | 0.759 | 0.716 | 0.570 | 681 | 88.4% | 45.4% |
| at_fire | bullish | label.next_interval.touched_interval_mid | 3640 | 40.8% | 0.752 | 0.718 | 0.592 | 364 | 86.8% | 46.0% |
| at_fire | bearish | label.next_interval.swept_both_sides | 3137 | 8.2% | 0.751 | 0.918 | 0.918 | 314 | 26.8% | 18.6% |
| at_fire | bearish | label.next_interval.touched_interval_mid | 3137 | 45.6% | 0.751 | 0.704 | 0.544 | 314 | 89.2% | 43.5% |
| at_fire | all | label.next_interval.swept_both_sides | 6801 | 9.1% | 0.726 | 0.909 | 0.909 | 681 | 26.9% | 17.8% |
| at_fire | all | label.next_interval.took_interval_high | 6801 | 55.2% | 0.707 | 0.647 | 0.552 | 681 | 87.4% | 32.1% |
| at_fire | bullish | label.next_interval.swept_both_sides | 3640 | 9.9% | 0.705 | 0.901 | 0.901 | 364 | 25.3% | 15.4% |
| at_fire | bullish | label.next_interval.outside_continuation_down | 3640 | 18.1% | 0.701 | 0.813 | 0.819 | 364 | 33.5% | 15.4% |
| at_fire | all | label.next_interval.closed_inside_interval | 6801 | 35.1% | 0.698 | 0.680 | 0.649 | 681 | 63.6% | 28.4% |
| at_fire | bearish | label.next_interval.closed_inside_interval | 3137 | 36.1% | 0.695 | 0.667 | 0.639 | 314 | 60.2% | 24.1% |
| at_fire | bearish | label.next_interval.took_interval_high | 3137 | 42.2% | 0.689 | 0.631 | 0.578 | 314 | 65.9% | 23.7% |
| at_fire | bullish | label.next_interval.took_interval_low | 3640 | 35.5% | 0.688 | 0.670 | 0.645 | 364 | 59.1% | 23.5% |
| at_fire | all | label.next_interval.took_interval_low | 6801 | 44.4% | 0.679 | 0.628 | 0.556 | 681 | 72.1% | 27.7% |
| at_fire | bearish | label.next_interval.outside_continuation_up | 3137 | 27.2% | 0.679 | 0.726 | 0.728 | 314 | 43.6% | 16.5% |
| at_fire | bullish | label.next_interval.closed_inside_interval | 3640 | 34.4% | 0.673 | 0.680 | 0.656 | 364 | 62.4% | 28.0% |
| at_fire | bullish | label.next_interval.closed_below_interval_low | 3640 | 21.3% | 0.671 | 0.787 | 0.787 | 364 | 34.9% | 13.6% |
| at_fire | all | label.next_interval.outside_continuation_down | 6801 | 24.4% | 0.663 | 0.757 | 0.756 | 681 | 33.2% | 8.8% |
| at_fire | bullish | label.next_interval.took_interval_high | 3640 | 66.6% | 0.658 | 0.673 | 0.666 | 364 | 92.9% | 26.3% |
| at_fire | all | label.next_interval.outside_continuation_up | 6801 | 34.9% | 0.657 | 0.648 | 0.651 | 681 | 49.6% | 14.7% |
| at_fire | bearish | label.next_interval.closed_above_interval_high | 3137 | 30.2% | 0.656 | 0.690 | 0.698 | 314 | 47.8% | 17.6% |
| at_fire | all | label.next_interval.closed_above_interval_high | 6801 | 37.7% | 0.640 | 0.628 | 0.623 | 681 | 53.3% | 15.6% |
| at_fire | all | label.next_interval.closed_below_interval_low | 6801 | 27.1% | 0.634 | 0.725 | 0.729 | 681 | 34.2% | 7.1% |
| at_fire | bearish | label.next_interval.took_interval_low | 3137 | 54.5% | 0.608 | 0.570 | 0.545 | 314 | 78.0% | 23.5% |
| at_fire | bullish | label.next_interval.outside_continuation_up | 3640 | 41.7% | 0.575 | 0.576 | 0.583 | 364 | 44.8% | 3.0% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | bullish | label.next_interval.compressed_range_0_75x | itr.ed.range_vs_prev_10_interval_avg=24609; itr.ed.range_vs_prev_3_interval_avg=11329; itr.ed.range_percentile_vs_prev_10_intervals=3787; itr.ed.range_vs_prev_5_interval_avg=2091; itr.ed.interval_wick_share=1955; itr.ed.range_percentile_vs_prev_3_intervals=1428; xctx.n_fvg_side_bearish_24h=1342; itr.ed.range_vs_prev_interval=1327; itr.ed.interval_body_share=1126; xctx.n_disp_side_bullish_24h=1026 |
| at_fire | all | label.next_interval.compressed_range_0_75x | itr.ed.range_vs_prev_10_interval_avg=42438; itr.ed.range_vs_prev_3_interval_avg=22761; itr.ed.range_vs_prev_5_interval_avg=4638; itr.ed.range_percentile_vs_prev_10_intervals=4461; xctx.n_fvg_side_bearish_24h=2511; itr.ed.interval_close_location=2500; itr.ed.interval_return_pts=2273; itr.ed.range_vs_prev_interval=1968; itr.ed.close_vs_prev_mid_pts=1637; xctx.minutes_since_last_smt_side_low_7d=1628 |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | itr.ed.range_vs_prev_3_interval_avg=12917; itr.ed.range_vs_prev_5_interval_avg=10793; itr.ed.range_vs_prev_10_interval_avg=9659; xctx.n_fvp_side_buying_7d=1171; itr.ed.range_vs_prev_interval=1139; xctx.minutes_since_last_ob_side_bearish_24h=1113; itr.ed.range_percentile_vs_prev_10_intervals=1088; xctx.minutes_since_last_psp_side_bullish_24h=1034; xctx.n_fvg_side_bullish_7d=913; xctx.minutes_since_last_smt_side_low_7d=871 |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | itr.ed.range_vs_prev_10_interval_avg=17784; itr.ed.range_vs_prev_5_interval_avg=11749; itr.ed.range_vs_prev_3_interval_avg=4593; itr.ed.range_percentile_vs_prev_10_intervals=2070; xctx.n_fvg_side_bullish_7d=1130; xctx.n_fvg_side_bearish_24h=996; itr.ed.range_vs_prev_interval=925; xctx.n_vp_side_balanced_7d=882; xctx.n_fvp_side_balanced_7d=850; xctx.minutes_since_last_smt_side_low_7d=817 |
| at_fire | all | label.next_interval.expanded_range_1_25x | itr.ed.range_vs_prev_10_interval_avg=32907; itr.ed.range_vs_prev_5_interval_avg=28939; itr.ed.range_vs_prev_3_interval_avg=5445; itr.ed.range_percentile_vs_prev_10_intervals=3692; xctx.n_fvg_side_bullish_7d=2252; itr.ed.range_delta_vs_prev_interval_pts=2025; xctx.n_fvg_side_bearish_24h=1617; itr.ed.range_vs_prev_interval=1559; xctx.n_disp_side_bearish_7d=1482; itr.ed.interval_return_pts=1339 |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | itr.ed.range_vs_prev_5_interval_avg=19052; itr.ed.range_vs_prev_10_interval_avg=12101; itr.ed.range_percentile_vs_prev_10_intervals=4819; itr.ed.range_vs_prev_3_interval_avg=2075; xctx.n_fvg_side_bullish_7d=1262; xctx.minutes_since_last_smt_side_low_7d=1194; xctx.n_disp_side_bullish_7d=1152; xctx.minutes_since_last_psp_side_bullish_24h=1067; xctx.minutes_since_last_smt_side_high_7d=1061; xctx.minutes_since_last_orb_side_doji_7d=990 |
| at_fire | all | label.next_interval.touched_interval_mid | ts.hour_of_day_utc=23046; itr.ed.interval_close_location=15761; xctx.minutes_since_last_fvp_24h=10418; xctx.minutes_since_last_fvp_same_primary_24h=6221; itr.ed.n_1m_bars=4443; xctx.minutes_since_last_ogap_24h=1976; itr.ed.range_vs_prev_10_interval_avg=1691; xctx.n_fvg_side_bullish_7d=1190; xctx.n_disp_side_bullish_7d=1134; itr.ed.range_vs_prev_5_interval_avg=1129 |
| at_fire | bullish | label.next_interval.touched_interval_mid | ts.hour_of_day_utc=10187; itr.ed.interval_close_location=8533; xctx.minutes_since_last_ogap_24h=3617; xctx.minutes_since_last_fvp_24h=3482; itr.ed.n_1m_bars=2167; itr.ed.range_vs_prev_10_interval_avg=1273; itr.ed.range_vs_prev_5_interval_avg=1271; xctx.n_disp_side_bullish_7d=1191; xctx.minutes_since_last_smt_side_low_7d=1137; xctx.n_fvg_side_bearish_7d=812 |
| at_fire | bearish | label.next_interval.swept_both_sides | itr.ed.range_vs_prev_5_interval_avg=2476; itr.ed.range_vs_prev_10_interval_avg=1883; itr.ed.range_percentile_vs_prev_10_intervals=1360; ts.hour_of_day_utc=1261; itr.ed.range_vs_prev_3_interval_avg=1100; xctx.minutes_since_last_fvp_24h=1069; itr.ed.n_1m_bars=447; xctx.minutes_since_last_smt_7d=431; xctx.minutes_since_last_orb_side_doji_7d=382; xctx.n_fvg_24h=380 |
| at_fire | bearish | label.next_interval.touched_interval_mid | ts.hour_of_day_utc=17739; itr.ed.interval_close_location=4128; xctx.minutes_since_last_fvp_same_primary_24h=3185; xctx.minutes_since_last_fvp_24h=2480; itr.ed.n_1m_bars=2251; xctx.minutes_since_last_fvp_4h=1047; itr.event_type_ny_itr=793; itr.ed.interval_body_share=752; ts.day_of_week=682; xctx.n_fvg_side_bullish_7d=680 |
| at_fire | all | label.next_interval.swept_both_sides | itr.ed.range_vs_prev_5_interval_avg=4572; itr.ed.range_vs_prev_10_interval_avg=4269; itr.ed.range_percentile_vs_prev_10_intervals=3420; ts.hour_of_day_utc=2503; itr.ed.range_vs_prev_3_interval_avg=1269; xctx.minutes_since_last_fvp_24h=950; xctx.minutes_since_last_smt_7d=909; xctx.n_fvg_side_bullish_7d=860; xctx.n_fvg_side_bearish_24h=859; xctx.minutes_since_last_psp_side_bullish_24h=779 |
| at_fire | all | label.next_interval.took_interval_high | itr.ed.interval_close_location=34110; itr.ed.range_vs_prev_5_interval_avg=2795; itr.ed.range_vs_prev_10_interval_avg=2481; itr.ed.n_1m_bars=2194; itr.ed.range_delta_vs_prev_interval_pts=2126; itr.ed.interval_return_pts=2063; itr.ctx.hour_of_day_et=1747; xctx.n_sweep_7d=1279; xctx.n_disp_side_bullish_7d=1267; itr.hour_of_day_utc=1251 |
| at_fire | bullish | label.next_interval.swept_both_sides | itr.ed.range_vs_prev_10_interval_avg=2638; itr.ed.range_vs_prev_5_interval_avg=1455; itr.ed.range_percentile_vs_prev_10_intervals=1390; xctx.n_fvg_side_bearish_24h=960; itr.ed.range_vs_prev_3_interval_avg=880; xctx.n_vp_side_balanced_7d=878; xctx.n_fvg_side_bullish_7d=798; xctx.n_ft_side_bullish_1h=573; xctx.total_events_1h=558; xctx.minutes_since_last_ogap_side_gap_up_7d=534 |
| at_fire | bullish | label.next_interval.outside_continuation_down | itr.ctx.hour_of_day_et=7599; itr.ed.interval_close_location=5368; itr.hour_of_day_utc=2658; itr.ed.n_1m_bars=2201; xctx.minutes_since_last_psp_side_bullish_24h=1054; xctx.minutes_since_last_orb_side_doji_7d=906; itr.ed.interval_wick_share=833; xctx.n_eql_side_high_7d=824; xctx.n_fvg_side_bearish_7d=813; xctx.n_fvg_side_bullish_7d=811 |
| at_fire | all | label.next_interval.closed_inside_interval | itr.ctx.hour_of_day_et=9406; itr.ed.range_vs_prev_10_interval_avg=4906; itr.hour_of_day_utc=4131; xctx.minutes_since_last_fvp_24h=3489; itr.ed.range_vs_prev_3_interval_avg=2877; itr.ed.interval_close_location=1525; xctx.minutes_since_last_disp_24h=1295; xctx.minutes_since_last_fvp_4h=1107; xctx.minutes_since_last_smt_side_low_7d=886; itr.ed.range_vs_prev_5_interval_avg=825 |

## Skipped Summary

| status | count |
|---|---|
| skip_non_binary | 39 |

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
