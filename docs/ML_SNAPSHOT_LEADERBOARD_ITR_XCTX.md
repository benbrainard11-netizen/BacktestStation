# ML snapshot leaderboard

_Generated `2026-05-14T04:12:21.664780+00:00`._

## Setup

- Matrix: `data\ml\anchors\itr_snapshots_xctx.parquet`
- Schema: `data\ml\anchors\itr_snapshots_xctx.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `all, bullish, bearish`
- Labels searched: `14` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| data\ml\anchors\itr_snapshot_leaderboard_xctx.csv | CSV leaderboard |
| data\ml\anchors\itr_snapshot_leaderboard_xctx.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 36095 |
| schema_feature_columns | 899 |
| schema_label_columns | 59 |
| grid_attempts | 42 |
| trained_ok | 42 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | bullish | label.next_interval.range_expanded_2x_interval | 3640 | 10.6% | 0.818 | 0.904 | 0.894 | 364 | 40.9% | 30.4% |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | 3640 | 32.4% | 0.804 | 0.761 | 0.676 | 364 | 79.4% | 47.0% |
| at_fire | all | label.next_interval.compressed_range_0_75x | 6801 | 31.2% | 0.803 | 0.767 | 0.688 | 681 | 78.9% | 47.7% |
| at_fire | all | label.next_interval.range_expanded_2x_interval | 6801 | 11.1% | 0.797 | 0.898 | 0.889 | 681 | 41.0% | 29.9% |
| at_fire | bullish | label.next_interval.range_expanded_1x_interval | 3640 | 47.3% | 0.796 | 0.723 | 0.527 | 364 | 86.3% | 39.0% |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | 3640 | 32.3% | 0.787 | 0.748 | 0.677 | 364 | 78.3% | 46.0% |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | 3137 | 29.9% | 0.786 | 0.763 | 0.701 | 314 | 72.3% | 42.4% |
| at_fire | all | label.next_interval.range_expanded_1x_interval | 6801 | 48.7% | 0.785 | 0.708 | 0.513 | 681 | 86.6% | 37.9% |
| at_fire | all | label.next_interval.expanded_range_1_25x | 6801 | 33.4% | 0.775 | 0.736 | 0.666 | 681 | 76.4% | 42.9% |
| at_fire | bearish | label.next_interval.range_expanded_1x_interval | 3137 | 50.2% | 0.764 | 0.696 | 0.502 | 314 | 84.4% | 34.2% |
| at_fire | bearish | label.next_interval.range_expanded_2x_interval | 3137 | 11.7% | 0.763 | 0.894 | 0.883 | 314 | 37.9% | 26.2% |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | 3137 | 34.5% | 0.755 | 0.721 | 0.655 | 314 | 74.8% | 40.3% |
| at_fire | bearish | label.next_interval.swept_both_interval_closed_inside | 3137 | 2.9% | 0.730 | 0.971 | 0.971 | 314 | 8.3% | 5.3% |
| at_fire | bearish | label.next_interval.swept_both_interval_closed_above | 3137 | 3.0% | 0.724 | 0.970 | 0.970 | 314 | 8.0% | 4.9% |
| at_fire | all | label.next_interval.swept_both_interval_closed_above | 6801 | 2.8% | 0.719 | 0.972 | 0.972 | 681 | 7.3% | 4.5% |
| at_fire | bullish | label.next_interval.one_sided_took_interval_low | 3640 | 25.7% | 0.699 | 0.734 | 0.743 | 364 | 41.2% | 15.5% |
| at_fire | all | label.next_interval.one_sided_took_interval_low | 6801 | 35.3% | 0.697 | 0.671 | 0.647 | 681 | 62.6% | 27.2% |
| at_fire | all | label.next_interval.one_sided_took_interval_high | 6801 | 46.2% | 0.696 | 0.633 | 0.538 | 681 | 78.3% | 32.1% |
| at_fire | all | label.next_interval.closed_inside_interval_range | 6801 | 35.1% | 0.694 | 0.682 | 0.649 | 681 | 65.3% | 30.2% |
| at_fire | bearish | label.next_interval.closed_inside_interval_range | 3137 | 36.1% | 0.688 | 0.672 | 0.639 | 314 | 63.4% | 27.3% |
| at_fire | all | label.next_interval.swept_both_interval_closed_inside | 6801 | 3.6% | 0.684 | 0.964 | 0.964 | 681 | 7.6% | 4.1% |
| at_fire | bullish | label.next_interval.swept_both_interval_closed_above | 3640 | 2.6% | 0.680 | 0.974 | 0.974 | 364 | 6.0% | 3.4% |
| at_fire | all | label.next_interval.took_interval_high_rejected_inside | 6801 | 14.8% | 0.678 | 0.852 | 0.852 | 681 | 32.0% | 17.2% |
| at_fire | bullish | label.next_interval.took_interval_low_held_below | 3640 | 21.3% | 0.673 | 0.786 | 0.787 | 364 | 34.1% | 12.8% |
| at_fire | all | label.next_interval.swept_both_interval_closed_below | 6801 | 2.7% | 0.672 | 0.973 | 0.973 | 681 | 5.0% | 2.3% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | bullish | label.next_interval.range_expanded_2x_interval | itr.ed.range_vs_prev_10_interval_avg=10315; itr.ed.range_percentile_vs_prev_10_intervals=3647; itr.ed.range_vs_prev_3_interval_avg=3163; itr.ed.range_vs_prev_5_interval_avg=1833; xctx.minutes_since_last_psp_side_bearish_24h=943; xctx.n_fvp_side_balanced_7d=878; xctx.n_fvg_side_bullish_7d=852; xctx.n_disp_side_bullish_24h=774; itr.ed.range_vs_prev_interval=756; itr.ed.interval_body_pts=725 |
| at_fire | bullish | label.next_interval.compressed_range_0_75x | itr.ed.range_vs_prev_10_interval_avg=25717; itr.ed.range_vs_prev_3_interval_avg=10320; itr.ed.range_vs_prev_5_interval_avg=4252; itr.ed.range_percentile_vs_prev_10_intervals=3112; itr.ed.interval_wick_share=2107; itr.ed.range_vs_prev_interval=1674; xctx.n_fvg_side_bullish_7d=1447; xctx.n_fvg_side_bearish_24h=1322; xctx.minutes_since_last_smt_side_low_7d=1240; xctx.n_disp_side_bullish_24h=1184 |
| at_fire | all | label.next_interval.compressed_range_0_75x | itr.ed.range_vs_prev_10_interval_avg=38998; itr.ed.range_vs_prev_3_interval_avg=20567; itr.ed.range_vs_prev_5_interval_avg=8043; itr.ed.range_percentile_vs_prev_10_intervals=5847; itr.ed.interval_close_location=2355; xctx.n_fvg_side_bearish_24h=2351; itr.ed.interval_return_pts=2232; itr.ed.range_vs_prev_interval=2122; xctx.n_fvg_side_bullish_7d=1709; xctx.minutes_since_last_smt_side_low_7d=1631 |
| at_fire | all | label.next_interval.range_expanded_2x_interval | itr.ed.range_vs_prev_10_interval_avg=22576; itr.ed.range_vs_prev_5_interval_avg=7962; itr.ed.range_vs_prev_3_interval_avg=4191; xctx.n_fvg_side_bullish_7d=2252; itr.ed.range_percentile_vs_prev_10_intervals=2053; xctx.n_fvp_side_balanced_7d=1331; xctx.n_swing_side_high_7d=1113; xctx.minutes_since_last_psp_side_bullish_24h=1112; xctx.n_eql_side_low_7d=1111; xctx.n_fvg_4h=1041 |
| at_fire | bullish | label.next_interval.range_expanded_1x_interval | itr.ed.range_vs_prev_10_interval_avg=25198; itr.ed.range_vs_prev_5_interval_avg=7309; itr.ed.range_vs_prev_3_interval_avg=6667; itr.ed.range_percentile_vs_prev_10_intervals=2486; xctx.n_fvg_side_bearish_24h=1480; itr.ed.close_vs_prev_mid_pts=1350; itr.ed.interval_close_location=1289; itr.ed.interval_wick_share=1136; xctx.minutes_since_last_disp_side_bearish_24h=1091; xctx.n_fvp_side_balanced_7d=1031 |
| at_fire | bullish | label.next_interval.expanded_range_1_25x | itr.ed.range_vs_prev_10_interval_avg=17122; itr.ed.range_vs_prev_5_interval_avg=10782; itr.ed.range_vs_prev_3_interval_avg=5240; itr.ed.range_percentile_vs_prev_10_intervals=1886; xctx.n_fvg_side_bullish_7d=1381; itr.ed.range_vs_prev_interval=1191; itr.ed.is_compression_vs_prev_5_intervals=1176; xctx.n_vp_side_balanced_7d=1066; xctx.n_fvg_side_bearish_24h=1019; itr.ed.interval_close_location=886 |
| at_fire | bearish | label.next_interval.compressed_range_0_75x | itr.ed.range_vs_prev_3_interval_avg=13265; itr.ed.range_vs_prev_5_interval_avg=11544; itr.ed.range_vs_prev_10_interval_avg=9752; itr.ed.range_percentile_vs_prev_10_intervals=1221; xctx.minutes_since_last_ob_side_bearish_24h=1214; itr.ed.range_vs_prev_interval=1098; xctx.minutes_since_last_psp_side_bullish_24h=1090; xctx.minutes_since_last_smt_side_low_7d=1057; xctx.n_fvg_side_bullish_7d=955; itr.ed.n_1m_bars=893 |
| at_fire | all | label.next_interval.range_expanded_1x_interval | itr.ed.range_vs_prev_10_interval_avg=37480; itr.ed.range_vs_prev_5_interval_avg=25064; itr.ed.range_vs_prev_3_interval_avg=11484; itr.ed.range_percentile_vs_prev_10_intervals=6389; xctx.n_fvg_side_bearish_24h=2022; xctx.minutes_since_last_smt_side_low_7d=1772; xctx.n_disp_side_bearish_7d=1753; itr.ed.interval_return_pts=1750; itr.ed.range_delta_vs_prev_interval_pts=1738; itr.ed.interval_close_location=1718 |
| at_fire | all | label.next_interval.expanded_range_1_25x | itr.ed.range_vs_prev_10_interval_avg=31269; itr.ed.range_vs_prev_5_interval_avg=29535; itr.ed.range_vs_prev_3_interval_avg=5125; itr.ed.range_percentile_vs_prev_10_intervals=3288; xctx.n_fvg_side_bullish_7d=2160; itr.ed.range_delta_vs_prev_interval_pts=1898; itr.ed.range_vs_prev_interval=1346; itr.ed.is_compression_vs_prev_10_intervals=1298; xctx.n_fvg_side_bearish_24h=1269; xctx.n_disp_side_bearish_7d=1170 |
| at_fire | bearish | label.next_interval.range_expanded_1x_interval | itr.ed.range_vs_prev_5_interval_avg=17661; itr.ed.range_vs_prev_3_interval_avg=12143; itr.ed.range_vs_prev_10_interval_avg=6747; itr.ed.range_percentile_vs_prev_10_intervals=4207; xctx.minutes_since_last_smt_side_low_7d=1251; xctx.n_fvg_side_bullish_7d=1089; xctx.n_swing_side_low_7d=1056; itr.ed.range_vs_prev_interval=1048; xctx.n_disp_side_bearish_7d=939; xctx.minutes_since_last_psp_side_bullish_24h=877 |
| at_fire | bearish | label.next_interval.range_expanded_2x_interval | itr.ed.range_vs_prev_10_interval_avg=11853; itr.ed.range_vs_prev_5_interval_avg=4373; itr.ed.range_percentile_vs_prev_10_intervals=1400; itr.ed.range_vs_prev_3_interval_avg=1114; xctx.n_fvg_side_bullish_7d=1055; xctx.n_eql_side_low_7d=1002; xctx.n_disp_side_bearish_7d=924; xctx.minutes_since_last_smt_side_low_7d=814; xctx.n_fvg_7d=776; xctx.n_orb_side_bullish_7d=647 |
| at_fire | bearish | label.next_interval.expanded_range_1_25x | itr.ed.range_vs_prev_5_interval_avg=20157; itr.ed.range_vs_prev_10_interval_avg=9768; itr.ed.range_percentile_vs_prev_10_intervals=4979; itr.ed.range_vs_prev_3_interval_avg=1903; xctx.n_fvg_side_bullish_7d=1027; xctx.minutes_since_last_smt_side_high_7d=871; xctx.n_disp_side_bearish_7d=792; xctx.minutes_since_last_smt_side_low_7d=756; itr.ed.range_vs_prev_interval=695; xctx.n_disp_side_bullish_7d=671 |
| at_fire | bearish | label.next_interval.swept_both_interval_closed_inside | itr.ed.range_vs_prev_3_interval_avg=1254; itr.ed.range_vs_prev_10_interval_avg=752; itr.ed.range_vs_prev_5_interval_avg=393; xctx.minutes_since_last_ogap_24h=329; xctx.minutes_since_last_smt_same_primary_7d=298; xctx.minutes_since_last_macro_side_medium_7d=271; itr.ed.range_percentile_vs_prev_10_intervals=248; xctx.n_fvg_7d=227; xctx.minutes_since_last_orb_side_doji_7d=214; itr.ed.abs_gap_from_prev_close_pts=197 |
| at_fire | bearish | label.next_interval.swept_both_interval_closed_above | itr.ed.range_vs_prev_5_interval_avg=1098; itr.ed.n_1m_bars=623; xctx.minutes_since_last_fvp_24h=611; itr.hour_of_day_utc=604; itr.ed.range_vs_prev_10_interval_avg=576; itr.ed.interval_close_location=521; itr.ed.range_percentile_vs_prev_5_intervals=491; xctx.n_eql_side_high_4h=337; itr.ed.range_vs_prev_3_interval_avg=325; xctx.n_ogap_side_gap_up_7d=316 |
| at_fire | all | label.next_interval.swept_both_interval_closed_above | itr.ed.range_vs_prev_5_interval_avg=2516; itr.ed.range_vs_prev_10_interval_avg=1379; itr.ed.interval_close_location=1213; itr.ed.range_percentile_vs_prev_5_intervals=880; itr.hour_of_day_utc=830; xctx.n_swing_7d=647; itr.ed.n_1m_bars=611; xctx.n_fvp_side_buying_7d=576; xctx.minutes_since_last_fvp_side_balanced_24h=534; xctx.n_disp_side_bullish_7d=503 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
