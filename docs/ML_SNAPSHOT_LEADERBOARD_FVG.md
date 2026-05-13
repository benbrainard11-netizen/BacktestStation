# ML snapshot leaderboard

_Generated `2026-05-11T23:02:11.384626+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshots.schema.json`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\fvg_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 209339 |
| schema_feature_columns | 45 |
| schema_label_columns | 67 |
| grid_attempts | 15 |
| trained_ok | 15 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.mitigation.fully_filled | 41532 | 77.7% | 0.773 | 0.810 | 0.777 | 4154 | 93.8% | 16.1% |
| at_fire | bullish | label.mitigation.fully_filled | 22786 | 77.0% | 0.770 | 0.802 | 0.770 | 2279 | 93.4% | 16.4% |
| at_fire | bearish | label.mitigation.fully_filled | 18746 | 78.6% | 0.768 | 0.814 | 0.786 | 1875 | 93.8% | 15.2% |
| at_fire | all | label.mitigation.mid_filled | 41532 | 81.4% | 0.755 | 0.831 | 0.814 | 4154 | 94.6% | 13.1% |
| at_fire | bullish | label.mitigation.mid_filled | 22786 | 80.7% | 0.751 | 0.827 | 0.807 | 2279 | 94.2% | 13.4% |
| at_fire | all | label.mitigation.closed_through | 41532 | 68.8% | 0.749 | 0.746 | 0.688 | 4154 | 89.4% | 20.6% |
| at_fire | bearish | label.mitigation.closed_through | 18746 | 70.8% | 0.746 | 0.762 | 0.708 | 1875 | 88.7% | 17.9% |
| at_fire | bearish | label.mitigation.mid_filled | 18746 | 82.3% | 0.746 | 0.833 | 0.823 | 1875 | 94.2% | 11.9% |
| at_fire | bullish | label.mitigation.closed_through | 22786 | 67.1% | 0.742 | 0.730 | 0.671 | 2279 | 87.7% | 20.5% |
| at_fire | bullish | label.mitigation.tapped | 22786 | 86.2% | 0.734 | 0.863 | 0.862 | 2279 | 96.7% | 10.4% |
| at_fire | all | label.mitigation.tapped | 41532 | 86.6% | 0.730 | 0.867 | 0.866 | 4154 | 96.1% | 9.5% |
| at_fire | bearish | label.mitigation.tapped | 18746 | 87.0% | 0.718 | 0.871 | 0.870 | 1875 | 95.8% | 8.8% |
| at_fire | bearish | label.mitigation.closed_inside | 18746 | 57.5% | 0.713 | 0.670 | 0.575 | 1875 | 83.3% | 25.8% |
| at_fire | all | label.mitigation.closed_inside | 41532 | 55.9% | 0.711 | 0.660 | 0.559 | 4154 | 81.5% | 25.6% |
| at_fire | bullish | label.mitigation.closed_inside | 22786 | 54.6% | 0.699 | 0.650 | 0.546 | 2279 | 78.3% | 23.7% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.mitigation.fully_filled | ts.hour_of_day_utc=151310; fvg.ed.fvg_width_pts=66018; fvg.ctx.hour_of_day_et=63893; fvg.hour_of_day_utc=41121; fvg.event_type_15m_fvg=29711; ts.day_of_week=10493; ts.year=7483; fvg.event_type_1h_fvg=5311; fvg.ed.candle_1.open=4814; fvg.side_bearish=4806 |
| at_fire | bullish | label.mitigation.fully_filled | ts.hour_of_day_utc=85747; fvg.ed.fvg_width_pts=33934; fvg.hour_of_day_utc=26870; fvg.ctx.hour_of_day_et=18707; fvg.event_type_15m_fvg=13354; ts.day_of_week=6098; ts.year=5833; fvg.event_type_1h_fvg=4463; fvg.ed.fvg_mid=2899; ts.month=2887 |
| at_fire | bearish | label.mitigation.fully_filled | ts.hour_of_day_utc=76559; fvg.ed.fvg_width_pts=34489; fvg.ctx.hour_of_day_et=24674; fvg.hour_of_day_utc=22433; fvg.event_type_15m_fvg=13455; ts.day_of_week=5401; ts.month=4685; fvg.event_type_1h_fvg=4041; ts.year=3628; fvg.ed.candle_3.low=2241 |
| at_fire | all | label.mitigation.mid_filled | ts.hour_of_day_utc=128266; fvg.ctx.hour_of_day_et=56880; fvg.ed.fvg_width_pts=34987; fvg.hour_of_day_utc=33223; fvg.event_type_15m_fvg=24804; ts.day_of_week=10644; ts.year=5474; fvg.event_type_1h_fvg=5124; ts.month=4787; fvg.side_bearish=4716 |
| at_fire | bullish | label.mitigation.mid_filled | ts.hour_of_day_utc=75734; fvg.hour_of_day_utc=23258; fvg.ed.fvg_width_pts=19899; fvg.ctx.hour_of_day_et=18528; fvg.event_type_15m_fvg=11670; ts.day_of_week=6353; ts.year=6199; fvg.event_type_1h_fvg=4486; ts.month=4306; fvg.ed.fvg_mid=2150 |
| at_fire | all | label.mitigation.closed_through | ts.hour_of_day_utc=160341; fvg.ctx.hour_of_day_et=67467; fvg.hour_of_day_utc=45106; fvg.ed.fvg_width_pts=42296; fvg.event_type_15m_fvg=30326; ts.day_of_week=11377; fvg.side_bearish=9268; ts.year=7748; fvg.event_type_1h_fvg=7448; ts.month=4931 |
| at_fire | bearish | label.mitigation.closed_through | ts.hour_of_day_utc=81455; fvg.ctx.hour_of_day_et=25557; fvg.hour_of_day_utc=25437; fvg.ed.fvg_width_pts=22932; fvg.event_type_15m_fvg=14845; ts.day_of_week=6527; fvg.event_type_1h_fvg=5125; ts.year=4565; ts.month=4066; fvg.day_of_week=2141 |
| at_fire | bearish | label.mitigation.mid_filled | ts.hour_of_day_utc=63842; fvg.ctx.hour_of_day_et=21138; fvg.hour_of_day_utc=19324; fvg.ed.fvg_width_pts=17486; fvg.event_type_15m_fvg=11029; ts.day_of_week=5327; ts.month=4405; fvg.event_type_1h_fvg=3760; ts.year=3020; fvg.ed.fvg_mid=1513 |
| at_fire | bullish | label.mitigation.closed_through | ts.hour_of_day_utc=92908; fvg.hour_of_day_utc=32675; fvg.ed.fvg_width_pts=23533; fvg.ctx.hour_of_day_et=19018; fvg.event_type_15m_fvg=13966; ts.year=9570; ts.day_of_week=7824; ts.month=6463; fvg.event_type_1h_fvg=5063; fvg.day_of_week=2884 |
| at_fire | bullish | label.mitigation.tapped | ts.hour_of_day_utc=55880; fvg.hour_of_day_utc=16056; fvg.ctx.hour_of_day_et=11846; fvg.event_type_15m_fvg=7461; ts.day_of_week=5219; fvg.ed.fvg_width_pts=3936; fvg.event_type_1h_fvg=3493; ts.month=3476; ts.year=3471; xd.has_disp_in_24h=1637 |
| at_fire | all | label.mitigation.tapped | ts.hour_of_day_utc=91294; fvg.ctx.hour_of_day_et=37742; fvg.hour_of_day_utc=21678; fvg.event_type_15m_fvg=15326; ts.day_of_week=7820; fvg.ed.fvg_width_pts=6120; ts.year=4293; ts.month=4256; fvg.event_type_1h_fvg=3966; xd.has_disp_in_24h=3955 |
| at_fire | bearish | label.mitigation.tapped | ts.hour_of_day_utc=42480; fvg.ctx.hour_of_day_et=12771; fvg.hour_of_day_utc=12141; fvg.event_type_15m_fvg=5235; ts.month=4311; ts.day_of_week=3832; fvg.ed.fvg_width_pts=3494; ts.year=3441; fvg.event_type_1h_fvg=2861; xd.has_disp_in_24h=1337 |
| at_fire | bearish | label.mitigation.closed_inside | ts.hour_of_day_utc=35736; fvg.ed.fvg_width_pts=32677; fvg.hour_of_day_utc=14667; ts.year=11466; fvg.event_type_15m_fvg=11418; fvg.ctx.hour_of_day_et=7479; fvg.ed.fvg_mid=7288; fvg.ed.candle_1.open=4500; ts.day_of_week=4475; fvg.event_type_1h_fvg=2831 |
| at_fire | all | label.mitigation.closed_inside | ts.hour_of_day_utc=71576; fvg.ed.fvg_width_pts=65559; fvg.event_type_15m_fvg=29165; fvg.hour_of_day_utc=28536; fvg.ctx.hour_of_day_et=20036; ts.year=19141; fvg.ed.fvg_mid=12836; ts.day_of_week=8258; fvg.ed.candle_1.high=7973; fvg.ed.candle_3.high=4621 |
| at_fire | bullish | label.mitigation.closed_inside | ts.hour_of_day_utc=43225; fvg.ed.fvg_width_pts=39699; fvg.hour_of_day_utc=19621; fvg.event_type_15m_fvg=12968; ts.year=12236; fvg.ed.fvg_mid=8131; fvg.ctx.hour_of_day_et=7930; fvg.ed.candle_3.high=7763; ts.day_of_week=6206; ts.month=3974 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
