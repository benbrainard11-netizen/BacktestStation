# ML snapshot leaderboard

_Generated `2026-05-13T22:38:40.946385+00:00`._

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
| schema_feature_columns | 1256 |
| schema_label_columns | 67 |
| grid_attempts | 15 |
| trained_ok | 15 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.mitigation.fully_filled | 41532 | 77.7% | 0.784 | 0.812 | 0.777 | 4154 | 94.9% | 17.1% |
| at_fire | bearish | label.mitigation.fully_filled | 18746 | 78.6% | 0.779 | 0.822 | 0.786 | 1875 | 94.5% | 15.9% |
| at_fire | bullish | label.mitigation.fully_filled | 22786 | 77.0% | 0.777 | 0.801 | 0.770 | 2279 | 93.9% | 16.9% |
| at_fire | all | label.mitigation.mid_filled | 41532 | 81.4% | 0.768 | 0.833 | 0.814 | 4154 | 95.4% | 13.9% |
| at_fire | bullish | label.mitigation.mid_filled | 22786 | 80.7% | 0.764 | 0.827 | 0.807 | 2279 | 95.1% | 14.4% |
| at_fire | bearish | label.mitigation.mid_filled | 18746 | 82.3% | 0.761 | 0.837 | 0.823 | 1875 | 94.3% | 12.1% |
| at_fire | all | label.mitigation.closed_through | 41532 | 68.8% | 0.758 | 0.752 | 0.688 | 4154 | 89.8% | 21.0% |
| at_fire | bullish | label.mitigation.tapped | 22786 | 86.2% | 0.757 | 0.864 | 0.862 | 2279 | 97.7% | 11.5% |
| at_fire | all | label.mitigation.tapped | 41532 | 86.6% | 0.757 | 0.868 | 0.866 | 4154 | 96.9% | 10.3% |
| at_fire | bearish | label.mitigation.closed_through | 18746 | 70.8% | 0.756 | 0.769 | 0.708 | 1875 | 89.4% | 18.6% |
| at_fire | bearish | label.mitigation.tapped | 18746 | 87.0% | 0.748 | 0.870 | 0.870 | 1875 | 96.1% | 9.1% |
| at_fire | bullish | label.mitigation.closed_through | 22786 | 67.1% | 0.746 | 0.735 | 0.671 | 2279 | 87.5% | 20.4% |
| at_fire | bearish | label.mitigation.closed_inside | 18746 | 57.5% | 0.732 | 0.682 | 0.575 | 1875 | 84.9% | 27.4% |
| at_fire | all | label.mitigation.closed_inside | 41532 | 55.9% | 0.727 | 0.675 | 0.559 | 4154 | 83.0% | 27.1% |
| at_fire | bullish | label.mitigation.closed_inside | 22786 | 54.6% | 0.725 | 0.668 | 0.546 | 2279 | 82.4% | 27.8% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.mitigation.fully_filled | ts.hour_of_day_utc=159654; fvg.ed.fvg_width_pts=65312; fvg.hour_of_day_utc=42166; fvg.ctx.hour_of_day_et=32952; fvg.event_type_15m_fvg=25035; ts.day_of_week=7115; xctx.minutes_since_last_ogap_24h=5727; fvg.event_type_1h_fvg=5336; fvggeom.distance_pts_any_symbol_bearish_untouched_below=4905; fvggeom.age_min_same_primary_bearish_untouched_above=4518 |
| at_fire | bearish | label.mitigation.fully_filled | ts.hour_of_day_utc=65041; fvg.ed.fvg_width_pts=30522; fvg.hour_of_day_utc=28458; fvg.ctx.hour_of_day_et=14717; fvg.event_type_15m_fvg=11623; xctx.n_disp_side_bearish_24h=3186; xctx.minutes_since_last_ogap_same_primary_1h=2923; xctx.minutes_since_last_ogap_24h=2559; ts.day_of_week=2341; xctx.n_ob_24h=2076 |
| at_fire | bullish | label.mitigation.fully_filled | ts.hour_of_day_utc=84326; fvg.ed.fvg_width_pts=30315; fvg.hour_of_day_utc=24145; fvg.ctx.hour_of_day_et=12431; fvg.event_type_15m_fvg=12228; xctx.minutes_since_last_orb_24h=4318; ts.day_of_week=3572; fvggeom.distance_pts_any_symbol_bearish_untouched_below=3564; xctx.minutes_since_last_smt_side_high_7d=2664; xctx.minutes_since_last_ogap_24h=2588 |
| at_fire | all | label.mitigation.mid_filled | ts.hour_of_day_utc=134793; fvg.hour_of_day_utc=35316; fvg.ed.fvg_width_pts=30293; fvg.ctx.hour_of_day_et=28738; fvg.event_type_15m_fvg=20922; ts.day_of_week=7704; xctx.minutes_since_last_ogap_24h=6474; fvg.event_type_1h_fvg=5125; xctx.minutes_since_last_itr_24h=3776; xctx.n_disp_side_bearish_24h=3628 |
| at_fire | bullish | label.mitigation.mid_filled | ts.hour_of_day_utc=73011; fvg.hour_of_day_utc=19080; fvg.ed.fvg_width_pts=14149; fvg.ctx.hour_of_day_et=11870; fvg.event_type_15m_fvg=10761; xctx.minutes_since_last_ogap_24h=3916; fvggeom.distance_pts_any_symbol_bearish_untouched_below=3284; xctx.minutes_since_last_orb_24h=3113; ts.day_of_week=2786; xctx.minutes_since_last_smt_side_high_7d=2448 |
| at_fire | bearish | label.mitigation.mid_filled | ts.hour_of_day_utc=53914; fvg.hour_of_day_utc=24088; fvg.ed.fvg_width_pts=13182; fvg.ctx.hour_of_day_et=11825; fvg.event_type_15m_fvg=9717; xctx.minutes_since_last_ogap_24h=2953; xctx.n_disp_side_bearish_24h=2683; xctx.minutes_since_last_disp_side_bullish_24h=2652; ts.day_of_week=2635; xctx.minutes_since_last_ogap_1h=2523 |
| at_fire | all | label.mitigation.closed_through | ts.hour_of_day_utc=170366; fvg.hour_of_day_utc=48852; fvg.ed.fvg_width_pts=40691; fvg.ctx.hour_of_day_et=30556; fvg.event_type_15m_fvg=29669; ts.day_of_week=8988; fvg.side_bearish=7166; fvg.event_type_1h_fvg=6428; xctx.minutes_since_last_ogap_1h=4859; xctx.minutes_since_last_ogap_24h=4567 |
| at_fire | bullish | label.mitigation.tapped | ts.hour_of_day_utc=53809; fvg.hour_of_day_utc=14756; fvg.event_type_15m_fvg=7130; fvg.ctx.hour_of_day_et=6471; xctx.minutes_since_last_orb_24h=4357; ts.day_of_week=3134; fvggeom.distance_pts_same_primary_bullish_untouched_below=3086; xctx.minutes_since_last_smt_side_high_7d=2374; xctx.n_disp_7d=2223; xctx.minutes_since_last_ogap_24h=2200 |
| at_fire | all | label.mitigation.tapped | ts.hour_of_day_utc=93721; fvg.hour_of_day_utc=24000; fvg.event_type_15m_fvg=14871; fvg.ctx.hour_of_day_et=13698; ts.day_of_week=6080; fvggeom.distance_pts_same_primary_bearish_untouched_above=5331; xctx.minutes_since_last_itr_24h=4738; fvg.event_type_1h_fvg=4597; fvggeom.distance_pts_same_primary_bullish_untouched_below=4236; xctx.minutes_since_last_orb_24h=4034 |
| at_fire | bearish | label.mitigation.closed_through | ts.hour_of_day_utc=67538; fvg.hour_of_day_utc=30510; fvg.ed.fvg_width_pts=18735; fvg.ctx.hour_of_day_et=16042; fvg.event_type_15m_fvg=13420; xctx.minutes_since_last_ogap_1h=3300; fvg.event_type_1h_fvg=2744; ts.day_of_week=2686; xctx.minutes_since_last_ogap_7d=2351; xctx.n_disp_side_bearish_24h=2291 |
| at_fire | bearish | label.mitigation.tapped | ts.hour_of_day_utc=34887; fvg.hour_of_day_utc=14468; fvg.event_type_15m_fvg=6417; fvg.ctx.hour_of_day_et=5753; fvggeom.distance_pts_same_primary_bearish_untouched_above=2674; xctx.n_disp_side_bearish_24h=2420; xctx.minutes_since_last_tp_24h=2153; xctx.minutes_since_last_itr_24h=2115; xctx.minutes_since_last_ob_side_bullish_24h=1929; fvggeom.width_pts_same_primary_bullish_untouched_above=1893 |
| at_fire | bullish | label.mitigation.closed_through | ts.hour_of_day_utc=91880; fvg.hour_of_day_utc=27434; fvg.ed.fvg_width_pts=20367; fvg.event_type_15m_fvg=15561; fvg.ctx.hour_of_day_et=12535; ts.day_of_week=4980; xctx.minutes_since_last_smt_side_low_7d=4153; ts.year=3564; xctx.minutes_since_last_smt_side_high_7d=3210; xctx.n_vp_side_selling_7d=2992 |
| at_fire | bearish | label.mitigation.closed_inside | fvg.ed.fvg_width_pts=42178; ts.hour_of_day_utc=32027; fvg.hour_of_day_utc=17537; fvg.event_type_15m_fvg=12076; fvggeom.distance_pts_same_primary_bearish_untouched_above=8226; ts.year=4800; fvggeom.distance_pts_same_primary_bearish_fully_filled_above=4792; fvg.ctx.hour_of_day_et=3802; fvg.ed.fvg_mid=3677; xctx.n_eql_same_primary_7d=3371 |
| at_fire | all | label.mitigation.closed_inside | ts.hour_of_day_utc=75398; fvg.ed.fvg_width_pts=73101; fvg.event_type_15m_fvg=29594; fvg.hour_of_day_utc=28827; fvg.ed.fvg_mid=9094; fvggeom.distance_pts_same_primary_bearish_untouched_above=8659; ts.year=8309; ts.day_of_week=7629; fvg.ctx.hour_of_day_et=6119; xctx.n_eql_same_primary_7d=5830 |
| at_fire | bullish | label.mitigation.closed_inside | ts.hour_of_day_utc=40917; fvg.ed.fvg_width_pts=40084; fvg.hour_of_day_utc=15419; fvg.event_type_15m_fvg=14675; fvggeom.distance_pts_same_primary_bullish_untouched_below=5811; ts.day_of_week=3731; ts.year=3438; fvg.ed.candle_3.high=2858; fvg.ed.fvg_mid=2844; xctx.n_eql_same_primary_7d=2500 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
