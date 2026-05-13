# ML snapshot leaderboard

_Generated `2026-05-11T23:30:29.017651+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshots.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `bullish, bearish, all`
- Labels searched: `6` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\tp_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 19414 |
| schema_feature_columns | 46 |
| schema_label_columns | 24 |
| grid_attempts | 18 |
| trained_ok | 18 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.next_period.took_parent_high | 3672 | 56.2% | 0.766 | 0.705 | 0.562 | 368 | 84.2% | 28.0% |
| at_fire | bullish | label.next_period.took_parent_low | 2000 | 29.9% | 0.740 | 0.721 | 0.701 | 200 | 65.0% | 35.1% |
| at_fire | all | label.next_period.took_parent_low | 3672 | 43.4% | 0.739 | 0.674 | 0.566 | 368 | 72.3% | 28.8% |
| at_fire | bearish | label.next_period.took_parent_high | 1662 | 35.6% | 0.681 | 0.661 | 0.644 | 167 | 58.7% | 23.1% |
| at_fire | bullish | label.next_period.took_parent_high | 2000 | 73.6% | 0.664 | 0.739 | 0.736 | 200 | 84.0% | 10.4% |
| at_fire | bullish | label.next_period.thesis_confirmed | 2000 | 73.6% | 0.664 | 0.739 | 0.736 | 200 | 84.0% | 10.4% |
| at_fire | all | label.next_period.thesis_confirmed | 3672 | 67.2% | 0.661 | 0.680 | 0.672 | 368 | 81.5% | 14.3% |
| at_fire | bearish | label.next_period.took_parent_low | 1662 | 59.6% | 0.638 | 0.597 | 0.596 | 167 | 80.8% | 21.3% |
| at_fire | bearish | label.next_period.thesis_confirmed | 1662 | 59.6% | 0.638 | 0.597 | 0.596 | 167 | 80.8% | 21.3% |
| at_fire | bearish | label.n_plus_2.took_parent_high | 165 | 61.2% | 0.625 | 0.564 | 0.612 | 17 | 76.5% | 15.3% |
| at_fire | all | label.n_plus_2.took_parent_high | 390 | 70.8% | 0.615 | 0.708 | 0.708 | 39 | 66.7% | -4.1% |
| at_fire | bullish | label.n_plus_2.took_parent_low | 225 | 28.0% | 0.598 | 0.702 | 0.720 | 23 | 39.1% | 11.1% |
| at_fire | bearish | label.n_plus_2.took_parent_low | 165 | 41.2% | 0.531 | 0.588 | 0.588 | 17 | 35.3% | -5.9% |
| at_fire | bearish | label.n_plus_2.thesis_confirmed | 165 | 41.2% | 0.531 | 0.588 | 0.588 | 17 | 35.3% | -5.9% |
| at_fire | all | label.n_plus_2.took_parent_low | 390 | 33.6% | 0.503 | 0.664 | 0.664 | 39 | 17.9% | -15.6% |
| at_fire | bullish | label.n_plus_2.took_parent_high | 225 | 77.8% | 0.437 | 0.778 | 0.778 | 23 | 56.5% | -21.3% |
| at_fire | bullish | label.n_plus_2.thesis_confirmed | 225 | 77.8% | 0.437 | 0.778 | 0.778 | 23 | 56.5% | -21.3% |
| at_fire | all | label.n_plus_2.thesis_confirmed | 390 | 62.3% | 0.417 | 0.623 | 0.623 | 39 | 35.9% | -26.4% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.next_period.took_parent_high | tp.ed.is_bearish_classic_po3=23979; tp.ed.parent_body_pts=13422; tp.side_bearish=7161; tp.ed.parent_range_pts=5989; tp.ed.parent_open=3396; tp.ed.parent_close=2210; tp.ed.parent_high=1930; ts.month=1755; ts.year=1408; tp.ed.parent_low=1325 |
| at_fire | bullish | label.next_period.took_parent_low | tp.ed.parent_body_pts=8356; tp.ed.parent_range_pts=2740; tp.ed.parent_low=1397; tp.ed.parent_open=1249; tp.ed.parent_high=1235; tp.ed.high_sub_period_london=1224; ts.year=1115; tp.ed.high_first=938; ts.month=850; tp.ed.low_sub_period_asia=838 |
| at_fire | all | label.next_period.took_parent_low | tp.ed.parent_body_pts=13283; tp.side_bullish=9797; tp.side_bearish=8082; tp.ed.is_bullish_classic_po3=7181; tp.ed.parent_range_pts=6476; ts.month=2874; ts.year=2818; tp.ed.parent_open=2446; tp.ed.parent_high=2407; tp.ed.high_sub_period_london=1839 |
| at_fire | bearish | label.next_period.took_parent_high | tp.ed.parent_body_pts=10251; tp.ed.parent_range_pts=4225; tp.ed.parent_open=2305; tp.ed.parent_low=1714; tp.ed.parent_high=1581; tp.ed.parent_close=1259; ts.month=1112; tp.ed.low_first=820; ts.year=807; tp.month=791 |
| at_fire | bullish | label.next_period.took_parent_high | tp.ed.parent_body_pts=4689; tp.ed.parent_range_pts=3354; tp.ed.parent_open=1205; tp.ed.low_sub_period_asia=1021; tp.ed.high_sub_period_london=986; tp.ed.parent_high=820; tp.ed.high_sub_period_ny_am=743; ts.month=717; tp.month=638; tp.ed.high_first=576 |
| at_fire | bullish | label.next_period.thesis_confirmed | tp.ed.parent_body_pts=4689; tp.ed.parent_range_pts=3354; tp.ed.parent_open=1205; tp.ed.low_sub_period_asia=1021; tp.ed.high_sub_period_london=986; tp.ed.parent_high=820; tp.ed.high_sub_period_ny_am=743; ts.month=717; tp.month=638; tp.ed.high_first=576 |
| at_fire | all | label.next_period.thesis_confirmed | tp.ed.parent_body_pts=9787; tp.ed.parent_range_pts=7901; tp.ed.is_bullish_classic_po3=2955; tp.ed.parent_open=2532; ts.month=1897; ts.year=1555; tp.ed.parent_close=1539; tp.ed.parent_low=1465; tp.ed.low_sub_period_asia=1260; tp.ed.high_sub_period_london=1218 |
| at_fire | bearish | label.next_period.took_parent_low | tp.ed.parent_range_pts=3211; tp.ed.parent_body_pts=2909; tp.ed.parent_open=716; ts.year=673; ts.day_of_week=498; tp.ed.parent_low=483; ts.month=467; tp.day_of_week=448; tp.ed.high_sub_period_asia=419; tp.ed.parent_close=406 |
| at_fire | bearish | label.next_period.thesis_confirmed | tp.ed.parent_range_pts=3211; tp.ed.parent_body_pts=2909; tp.ed.parent_open=716; ts.year=673; ts.day_of_week=498; tp.ed.parent_low=483; ts.month=467; tp.day_of_week=448; tp.ed.high_sub_period_asia=419; tp.ed.parent_close=406 |
| at_fire | bearish | label.n_plus_2.took_parent_high | tp.ed.parent_body_pts=319; tp.ctx.day_of_week_et=116; ts.year=86; tp.ed.parent_close=71; tp.ed.parent_range_pts=58; tp.ed.low_sub_period_friday=51; ts.month=49; tp.ed.high_sub_period_wednesday=34; tp.month=29; tp.ed.parent_open=24 |
| at_fire | all | label.n_plus_2.took_parent_high | tp.side_bullish=210; ts.year=193; tp.month=121; tp.ed.parent_body_pts=114; tp.ed.high_sub_period_friday=103; tp.year=74; tp.ed.parent_range_pts=58; ts.month=44; xd.has_fvg_in_24h=41; tp.ed.low_sub_period_friday=31 |
| at_fire | bullish | label.n_plus_2.took_parent_low | ts.year=787; tp.ed.parent_body_pts=677; tp.ed.parent_range_pts=451; tp.ed.parent_open=352; tp.ed.high_sub_period_friday=332; tp.ed.parent_high=317; tp.month=234; tp.ed.parent_close=232; tp.year=196; xd.has_fvg_in_24h=195 |
| at_fire | bearish | label.n_plus_2.took_parent_low | ts.year=27; xd.has_swing_in_24h=19; tp.ed.parent_range_pts=17; tp.ed.low_sub_period_friday=12; tp.ed.parent_open=9; tp.ed.low_sub_period_tuesday=7; tp.month=6; tp.ed.high_sub_period_wednesday=5; ts.month=5; xd.has_fvg_in_24h=3 |
| at_fire | bearish | label.n_plus_2.thesis_confirmed | ts.year=27; xd.has_swing_in_24h=19; tp.ed.parent_range_pts=17; tp.ed.low_sub_period_friday=12; tp.ed.parent_open=9; tp.ed.low_sub_period_tuesday=7; tp.month=6; tp.ed.high_sub_period_wednesday=5; ts.month=5; xd.has_fvg_in_24h=3 |
| at_fire | all | label.n_plus_2.took_parent_low | ts.year=306; tp.ed.high_sub_period_friday=212; tp.year=198; tp.ed.parent_body_pts=148; ts.month=137; ts.hour_of_day_utc=127; tp.ed.parent_range_pts=116; tp.month=96; tp.ed.parent_open=77; tp.ed.low_sub_period_friday=52 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
