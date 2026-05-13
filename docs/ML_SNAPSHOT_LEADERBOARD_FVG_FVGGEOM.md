# ML snapshot leaderboard

_Generated `2026-05-12T23:14:52.573245+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots_xctx_fvggeom.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots_xctx_fvggeom.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `bullish, bearish, all`
- Labels searched: `5` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshot_leaderboard_xctx_fvggeom.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshot_leaderboard_xctx_fvggeom.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 209339 |
| schema_feature_columns | 1088 |
| schema_label_columns | 67 |
| grid_attempts | 15 |
| trained_ok | 15 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.mitigation.fully_filled | 41532 | 77.7% | 0.784 | 0.812 | 0.777 | 4154 | 94.8% | 17.1% |
| at_fire | bearish | label.mitigation.fully_filled | 18746 | 78.6% | 0.779 | 0.821 | 0.786 | 1875 | 93.8% | 15.2% |
| at_fire | bullish | label.mitigation.fully_filled | 22786 | 77.0% | 0.776 | 0.802 | 0.770 | 2279 | 93.5% | 16.5% |
| at_fire | all | label.mitigation.mid_filled | 41532 | 81.4% | 0.769 | 0.833 | 0.814 | 4154 | 95.8% | 14.3% |
| at_fire | bullish | label.mitigation.mid_filled | 22786 | 80.7% | 0.766 | 0.827 | 0.807 | 2279 | 95.9% | 15.2% |
| at_fire | bearish | label.mitigation.mid_filled | 18746 | 82.3% | 0.761 | 0.837 | 0.823 | 1875 | 94.5% | 12.2% |
| at_fire | bearish | label.mitigation.closed_through | 18746 | 70.8% | 0.759 | 0.768 | 0.708 | 1875 | 90.1% | 19.3% |
| at_fire | all | label.mitigation.closed_through | 41532 | 68.8% | 0.759 | 0.753 | 0.688 | 4154 | 90.1% | 21.3% |
| at_fire | bullish | label.mitigation.tapped | 22786 | 86.2% | 0.756 | 0.864 | 0.862 | 2279 | 97.1% | 10.8% |
| at_fire | all | label.mitigation.tapped | 41532 | 86.6% | 0.755 | 0.868 | 0.866 | 4154 | 96.8% | 10.2% |
| at_fire | bearish | label.mitigation.tapped | 18746 | 87.0% | 0.750 | 0.870 | 0.870 | 1875 | 96.9% | 9.9% |
| at_fire | bullish | label.mitigation.closed_through | 22786 | 67.1% | 0.745 | 0.734 | 0.671 | 2279 | 87.7% | 20.5% |
| at_fire | bearish | label.mitigation.closed_inside | 18746 | 57.5% | 0.730 | 0.681 | 0.575 | 1875 | 84.7% | 27.3% |
| at_fire | all | label.mitigation.closed_inside | 41532 | 55.9% | 0.728 | 0.676 | 0.559 | 4154 | 83.5% | 27.6% |
| at_fire | bullish | label.mitigation.closed_inside | 22786 | 54.6% | 0.724 | 0.668 | 0.546 | 2279 | 81.6% | 27.0% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.mitigation.fully_filled | ts.hour_of_day_utc=171760; fvg.ed.fvg_width_pts=65454; fvg.ctx.hour_of_day_et=48518; fvg.event_type_15m_fvg=28243; fvg.hour_of_day_utc=24132; ts.day_of_week=7655; xctx.minutes_since_last_vp_24h=6024; fvggeom.distance_pts_any_symbol_bearish_untouched_below=5030; xctx.n_disp_side_bearish_24h=4780; fvggeom.age_min_same_primary_bearish_untouched_above=4570 |
| at_fire | bearish | label.mitigation.fully_filled | ts.hour_of_day_utc=78848; fvg.ed.fvg_width_pts=31046; fvg.ctx.hour_of_day_et=18052; fvg.hour_of_day_utc=17948; fvg.event_type_15m_fvg=12678; xctx.minutes_since_last_ft_24h=3126; xctx.n_disp_side_bearish_24h=3097; ts.day_of_week=2680; xd.has_disp_in_24h=2032; fvg.ed.tracking_timeframe_15m=2014 |
| at_fire | bullish | label.mitigation.fully_filled | ts.hour_of_day_utc=95042; fvg.ed.fvg_width_pts=32529; fvg.hour_of_day_utc=14803; fvg.ctx.hour_of_day_et=14495; fvg.event_type_15m_fvg=12687; ts.day_of_week=4172; xctx.minutes_since_last_orb_24h=3916; fvggeom.distance_pts_any_symbol_bearish_untouched_below=3829; xctx.minutes_since_last_smt_side_high_7d=3641; xctx.minutes_since_last_smt_side_low_7d=3045 |
| at_fire | all | label.mitigation.mid_filled | ts.hour_of_day_utc=144009; fvg.ctx.hour_of_day_et=42256; fvg.ed.fvg_width_pts=30780; fvg.event_type_15m_fvg=23336; fvg.hour_of_day_utc=19611; ts.day_of_week=7374; xctx.minutes_since_last_vp_24h=6464; fvg.event_type_1h_fvg=3900; xctx.n_disp_side_bearish_24h=3900; fvggeom.distance_pts_any_symbol_bearish_untouched_below=3546 |
| at_fire | bullish | label.mitigation.mid_filled | ts.hour_of_day_utc=83674; fvg.ed.fvg_width_pts=14293; fvg.ctx.hour_of_day_et=13631; fvg.hour_of_day_utc=10210; fvg.event_type_15m_fvg=9750; xctx.minutes_since_last_orb_24h=3654; ts.day_of_week=3350; fvggeom.distance_pts_any_symbol_bearish_untouched_below=3252; fvg.event_type_1h_fvg=3240; xctx.minutes_since_last_smt_side_high_7d=2982 |
| at_fire | bearish | label.mitigation.mid_filled | ts.hour_of_day_utc=65241; fvg.hour_of_day_utc=15634; fvg.ctx.hour_of_day_et=15217; fvg.ed.fvg_width_pts=13374; fvg.event_type_15m_fvg=10878; xctx.n_disp_side_bearish_24h=3124; ts.day_of_week=2968; xctx.n_vp_side_buying_7d=2771; xctx.minutes_since_last_vp_24h=2696; xctx.minutes_since_last_ob_side_bullish_24h=2413 |
| at_fire | bearish | label.mitigation.closed_through | ts.hour_of_day_utc=83131; fvg.hour_of_day_utc=19864; fvg.ctx.hour_of_day_et=19860; fvg.ed.fvg_width_pts=18982; fvg.event_type_15m_fvg=15760; ts.day_of_week=3291; xctx.minutes_since_last_ft_24h=2842; xctx.n_disp_side_bearish_24h=2362; xctx.n_eql_side_high_7d=2301; xctx.n_sweep_side_high_7d=2288 |
| at_fire | all | label.mitigation.closed_through | ts.hour_of_day_utc=182888; fvg.ctx.hour_of_day_et=48389; fvg.ed.fvg_width_pts=41730; fvg.event_type_15m_fvg=31746; fvg.hour_of_day_utc=29124; ts.day_of_week=8976; fvg.side_bearish=7558; fvg.event_type_1h_fvg=6286; fvggeom.age_min_same_primary_bearish_untouched_above=4521; xctx.minutes_since_last_ft_24h=3619 |
| at_fire | bullish | label.mitigation.tapped | ts.hour_of_day_utc=61260; fvg.event_type_15m_fvg=6959; fvg.ctx.hour_of_day_et=6938; fvg.hour_of_day_utc=6783; xctx.minutes_since_last_orb_24h=4787; fvggeom.distance_pts_same_primary_bullish_untouched_below=2826; ts.day_of_week=2750; xctx.minutes_since_last_smt_side_high_7d=2733; xctx.n_disp_7d=2291; xctx.minutes_since_last_smt_side_low_7d=2054 |
| at_fire | all | label.mitigation.tapped | ts.hour_of_day_utc=99783; fvg.ctx.hour_of_day_et=20594; fvg.event_type_15m_fvg=15327; fvg.hour_of_day_utc=13230; xctx.minutes_since_last_orb_24h=7209; ts.day_of_week=6050; xctx.minutes_since_last_tp_24h=4971; fvggeom.distance_pts_same_primary_bearish_untouched_above=4780; fvggeom.distance_pts_same_primary_bullish_untouched_below=4652; xctx.minutes_since_last_vp_24h=3686 |
| at_fire | bearish | label.mitigation.tapped | ts.hour_of_day_utc=42958; fvg.hour_of_day_utc=9623; fvg.ctx.hour_of_day_et=6846; fvg.event_type_15m_fvg=5985; fvggeom.distance_pts_same_primary_bearish_untouched_above=3181; xctx.minutes_since_last_vp_24h=2933; xctx.n_disp_side_bearish_24h=2703; xctx.minutes_since_last_ob_side_bullish_24h=2231; xctx.n_vp_side_buying_7d=2230; xctx.n_ob_24h=2103 |
| at_fire | bullish | label.mitigation.closed_through | ts.hour_of_day_utc=104266; fvg.ed.fvg_width_pts=20157; fvg.hour_of_day_utc=15089; fvg.event_type_15m_fvg=14880; fvg.ctx.hour_of_day_et=12316; ts.day_of_week=5118; xctx.minutes_since_last_tp_24h=3717; fvg.event_type_1h_fvg=3703; ts.year=3658; xctx.minutes_since_last_smt_side_low_7d=3458 |
| at_fire | bearish | label.mitigation.closed_inside | fvg.ed.fvg_width_pts=40797; ts.hour_of_day_utc=38150; fvg.event_type_15m_fvg=13706; fvg.hour_of_day_utc=12367; fvggeom.distance_pts_same_primary_bearish_untouched_above=7666; ts.year=5289; fvggeom.distance_pts_same_primary_bearish_fully_filled_above=5103; fvg.ctx.hour_of_day_et=4393; fvg.ed.fvg_mid=3722; xctx.n_eql_same_primary_7d=2873 |
| at_fire | all | label.mitigation.closed_inside | ts.hour_of_day_utc=81003; fvg.ed.fvg_width_pts=75142; fvg.event_type_15m_fvg=30111; fvg.hour_of_day_utc=22801; fvg.ed.fvg_mid=9542; fvggeom.distance_pts_same_primary_bearish_untouched_above=9143; ts.year=8499; ts.day_of_week=7537; fvg.ctx.hour_of_day_et=6996; xctx.n_eql_same_primary_7d=6259 |
| at_fire | bullish | label.mitigation.closed_inside | ts.hour_of_day_utc=45414; fvg.ed.fvg_width_pts=40569; fvg.event_type_15m_fvg=12726; fvg.hour_of_day_utc=10578; fvggeom.distance_pts_same_primary_bullish_untouched_below=5519; ts.day_of_week=3743; ts.year=3291; fvg.ed.fvg_mid=3045; xctx.minutes_since_last_orb_24h=2736; xctx.minutes_since_last_ft_24h=2645 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
