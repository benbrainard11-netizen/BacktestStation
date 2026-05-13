# ML snapshot leaderboard

_Generated `2026-05-12T14:30:31.901373+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots_xctx.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots_xctx.schema.json`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshot_leaderboard_xctx.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshot_leaderboard_xctx.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 209339 |
| schema_feature_columns | 637 |
| schema_label_columns | 67 |
| grid_attempts | 15 |
| trained_ok | 15 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.mitigation.fully_filled | 41532 | 77.7% | 0.775 | 0.809 | 0.777 | 4154 | 94.4% | 16.7% |
| at_fire | bearish | label.mitigation.fully_filled | 18746 | 78.6% | 0.767 | 0.817 | 0.786 | 1875 | 93.5% | 14.9% |
| at_fire | bullish | label.mitigation.fully_filled | 22786 | 77.0% | 0.767 | 0.801 | 0.770 | 2279 | 92.6% | 15.6% |
| at_fire | all | label.mitigation.mid_filled | 41532 | 81.4% | 0.757 | 0.831 | 0.814 | 4154 | 94.4% | 13.0% |
| at_fire | bullish | label.mitigation.mid_filled | 22786 | 80.7% | 0.753 | 0.826 | 0.807 | 2279 | 94.3% | 13.5% |
| at_fire | all | label.mitigation.closed_through | 41532 | 68.8% | 0.752 | 0.750 | 0.688 | 4154 | 88.6% | 19.8% |
| at_fire | bearish | label.mitigation.closed_through | 18746 | 70.8% | 0.745 | 0.763 | 0.708 | 1875 | 87.6% | 16.7% |
| at_fire | bearish | label.mitigation.mid_filled | 18746 | 82.3% | 0.744 | 0.835 | 0.823 | 1875 | 93.0% | 10.7% |
| at_fire | bullish | label.mitigation.closed_through | 22786 | 67.1% | 0.738 | 0.731 | 0.671 | 2279 | 85.9% | 18.7% |
| at_fire | bullish | label.mitigation.tapped | 22786 | 86.2% | 0.735 | 0.863 | 0.862 | 2279 | 95.9% | 9.7% |
| at_fire | all | label.mitigation.tapped | 41532 | 86.6% | 0.734 | 0.867 | 0.866 | 4154 | 96.0% | 9.4% |
| at_fire | bearish | label.mitigation.tapped | 18746 | 87.0% | 0.725 | 0.870 | 0.870 | 1875 | 95.1% | 8.1% |
| at_fire | all | label.mitigation.closed_inside | 41532 | 55.9% | 0.719 | 0.669 | 0.559 | 4154 | 81.8% | 26.0% |
| at_fire | bearish | label.mitigation.closed_inside | 18746 | 57.5% | 0.718 | 0.674 | 0.575 | 1875 | 82.9% | 25.4% |
| at_fire | bullish | label.mitigation.closed_inside | 22786 | 54.6% | 0.710 | 0.657 | 0.546 | 2279 | 81.7% | 27.2% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.mitigation.fully_filled | ts.hour_of_day_utc=168784; fvg.ed.fvg_width_pts=62834; fvg.ctx.hour_of_day_et=38138; fvg.hour_of_day_utc=34501; fvg.event_type_15m_fvg=32386; xctx.n_eql_same_primary_7d=6783; ts.day_of_week=6005; xctx.n_disp_side_bearish_24h=5810; xctx.minutes_since_last_vp_24h=5237; xctx.minutes_since_last_ft_24h=3953 |
| at_fire | bearish | label.mitigation.fully_filled | ts.hour_of_day_utc=72200; fvg.ed.fvg_width_pts=33594; fvg.hour_of_day_utc=21988; fvg.ctx.hour_of_day_et=18927; fvg.event_type_15m_fvg=14574; xctx.minutes_since_last_ft_24h=3815; xctx.n_eql_same_primary_7d=3430; xctx.n_disp_side_bearish_24h=2857; xctx.minutes_since_last_vp_24h=2687; xctx.n_eql_7d=2633 |
| at_fire | bullish | label.mitigation.fully_filled | ts.hour_of_day_utc=85864; fvg.ed.fvg_width_pts=31813; fvg.hour_of_day_utc=24996; fvg.event_type_15m_fvg=14659; fvg.ctx.hour_of_day_et=13652; xctx.minutes_since_last_orb_24h=4250; ts.day_of_week=3364; xctx.n_disp_7d=2957; xctx.n_eql_side_high_7d=2851; xctx.minutes_since_last_smt_side_high_7d=2784 |
| at_fire | all | label.mitigation.mid_filled | ts.hour_of_day_utc=142231; fvg.ctx.hour_of_day_et=34803; fvg.ed.fvg_width_pts=31721; fvg.hour_of_day_utc=28730; fvg.event_type_15m_fvg=27286; xctx.minutes_since_last_vp_24h=6539; ts.day_of_week=6271; xctx.n_disp_side_bearish_24h=4901; xctx.minutes_since_last_smt_side_high_7d=4647; xctx.minutes_since_last_orb_24h=3895 |
| at_fire | bullish | label.mitigation.mid_filled | ts.hour_of_day_utc=74227; fvg.hour_of_day_utc=19607; fvg.ed.fvg_width_pts=14930; fvg.ctx.hour_of_day_et=12567; fvg.event_type_15m_fvg=12121; xctx.minutes_since_last_orb_24h=4383; xctx.minutes_since_last_smt_side_high_7d=3168; ts.day_of_week=2875; xctx.minutes_since_last_smt_side_low_7d=2696; xctx.n_disp_7d=2526 |
| at_fire | all | label.mitigation.closed_through | ts.hour_of_day_utc=180858; fvg.ed.fvg_width_pts=42412; fvg.hour_of_day_utc=40680; fvg.ctx.hour_of_day_et=40648; fvg.event_type_15m_fvg=35271; fvg.side_bearish=8979; ts.day_of_week=7618; xctx.n_eql_same_primary_7d=6095; xctx.n_disp_side_bearish_24h=5831; xctx.n_eql_side_high_7d=5012 |
| at_fire | bearish | label.mitigation.closed_through | ts.hour_of_day_utc=77069; fvg.hour_of_day_utc=24791; fvg.ctx.hour_of_day_et=21464; fvg.ed.fvg_width_pts=20564; fvg.event_type_15m_fvg=14727; xctx.minutes_since_last_ft_24h=3566; ts.day_of_week=3184; xctx.n_eql_same_primary_7d=3143; xctx.n_sweep_side_high_7d=2972; xctx.n_disp_side_bullish_7d=2893 |
| at_fire | bearish | label.mitigation.mid_filled | ts.hour_of_day_utc=59764; fvg.hour_of_day_utc=17911; fvg.ctx.hour_of_day_et=15633; fvg.ed.fvg_width_pts=14929; fvg.event_type_15m_fvg=12573; xctx.minutes_since_last_vp_24h=3446; ts.day_of_week=3250; xctx.n_vp_side_buying_7d=3219; xctx.minutes_since_last_ft_24h=3169; xctx.n_disp_side_bullish_7d=2295 |
| at_fire | bullish | label.mitigation.closed_through | ts.hour_of_day_utc=92752; fvg.hour_of_day_utc=26651; fvg.ed.fvg_width_pts=18411; fvg.event_type_15m_fvg=15566; fvg.ctx.hour_of_day_et=13467; ts.day_of_week=4366; ts.year=3917; xctx.n_psp_7d=1954; xctx.minutes_since_last_smt_side_high_7d=1872; xctx.n_eql_24h=1843 |
| at_fire | bullish | label.mitigation.tapped | ts.hour_of_day_utc=54455; fvg.hour_of_day_utc=13649; fvg.event_type_15m_fvg=7582; fvg.ctx.hour_of_day_et=7023; xctx.minutes_since_last_orb_24h=5795; xctx.minutes_since_last_smt_side_high_7d=2563; ts.day_of_week=2431; xctx.n_disp_7d=2153; xctx.minutes_since_last_smt_side_low_7d=1880; xctx.minutes_since_last_orb_side_bullish_24h=1661 |
| at_fire | all | label.mitigation.tapped | ts.hour_of_day_utc=98414; fvg.hour_of_day_utc=19519; fvg.ctx.hour_of_day_et=17351; fvg.event_type_15m_fvg=15942; xctx.minutes_since_last_orb_24h=7163; ts.day_of_week=4744; xctx.minutes_since_last_vp_24h=4628; xctx.n_disp_side_bearish_24h=3542; fvg.ed.fvg_width_pts=3154; xd.has_disp_in_24h=2952 |
| at_fire | bearish | label.mitigation.tapped | ts.hour_of_day_utc=38693; fvg.hour_of_day_utc=11151; fvg.ctx.hour_of_day_et=6931; fvg.event_type_15m_fvg=6181; xctx.minutes_since_last_vp_24h=2554; xctx.n_vp_side_buying_7d=2094; ts.day_of_week=2024; xctx.minutes_since_last_tp_24h=1849; xctx.minutes_since_last_ob_side_bullish_24h=1615; xctx.minutes_since_last_orb_side_doji_7d=1527 |
| at_fire | all | label.mitigation.closed_inside | ts.hour_of_day_utc=78458; fvg.ed.fvg_width_pts=68540; fvg.event_type_15m_fvg=33231; fvg.hour_of_day_utc=26601; xctx.n_eql_same_primary_7d=10777; ts.year=10684; fvg.ed.fvg_mid=9892; fvg.ctx.hour_of_day_et=8408; fvg.ed.candle_1.high=7735; ts.day_of_week=6806 |
| at_fire | bearish | label.mitigation.closed_inside | fvg.ed.fvg_width_pts=36449; ts.hour_of_day_utc=34773; fvg.hour_of_day_utc=14739; fvg.event_type_15m_fvg=13474; ts.year=6538; xctx.n_eql_same_primary_7d=5961; fvg.ed.fvg_mid=5082; xctx.n_eql_7d=3822; fvg.ctx.hour_of_day_et=3814; fvg.ed.candle_1.open=3796 |
| at_fire | bullish | label.mitigation.closed_inside | ts.hour_of_day_utc=40568; fvg.ed.fvg_width_pts=37432; fvg.hour_of_day_utc=15777; fvg.event_type_15m_fvg=14017; xctx.n_eql_same_primary_7d=5761; fvg.ed.fvg_mid=5428; ts.year=5169; fvg.ed.candle_3.high=4446; ts.day_of_week=4114; xctx.minutes_since_last_ft_24h=3350 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
