# ML snapshot leaderboard

_Generated `2026-05-11T23:27:35.711374+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\ft_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\ft_snapshots.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `bullish, bearish, all`
- Labels searched: `14` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\ft_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\ft_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 10373 |
| schema_feature_columns | 40 |
| schema_label_columns | 37 |
| grid_attempts | 42 |
| trained_ok | 42 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.break_high.wick_breached | 1986 | 81.2% | 0.724 | 0.810 | 0.812 | 199 | 93.0% | 11.7% |
| at_fire | all | label.break_high.close_past | 1986 | 80.0% | 0.701 | 0.798 | 0.800 | 199 | 91.5% | 11.5% |
| at_fire | all | label.break_low.wick_breached | 1986 | 74.2% | 0.691 | 0.751 | 0.742 | 199 | 92.0% | 17.7% |
| at_fire | all | label.break_low.close_past | 1986 | 72.0% | 0.684 | 0.732 | 0.720 | 199 | 89.9% | 18.0% |
| at_fire | all | label.break_low_1ext.wick_breached | 1986 | 41.8% | 0.677 | 0.636 | 0.582 | 199 | 55.8% | 13.9% |
| at_fire | all | label.break_low_05ext.wick_breached | 1986 | 56.2% | 0.676 | 0.634 | 0.562 | 199 | 78.4% | 22.2% |
| at_fire | bullish | label.break_low_05ext.wick_breached | 1068 | 50.3% | 0.673 | 0.625 | 0.497 | 107 | 70.1% | 19.8% |
| at_fire | bullish | label.break_low_1ext.wick_breached | 1068 | 37.8% | 0.671 | 0.639 | 0.622 | 107 | 49.5% | 11.7% |
| at_fire | bullish | label.break_low_05ext.close_past | 1068 | 48.2% | 0.668 | 0.619 | 0.518 | 107 | 64.5% | 16.3% |
| at_fire | bullish | label.break_low.wick_breached | 1068 | 66.1% | 0.665 | 0.676 | 0.661 | 107 | 85.0% | 18.9% |
| at_fire | all | label.break_low_1ext.close_past | 1986 | 40.1% | 0.663 | 0.628 | 0.599 | 199 | 58.3% | 18.2% |
| at_fire | all | label.break_low_05ext.close_past | 1986 | 54.0% | 0.661 | 0.621 | 0.460 | 199 | 66.3% | 12.4% |
| at_fire | bearish | label.break_high_1ext.wick_breached | 909 | 37.6% | 0.659 | 0.650 | 0.624 | 91 | 58.2% | 20.6% |
| at_fire | bearish | label.break_high_1ext.close_past | 909 | 36.9% | 0.656 | 0.659 | 0.631 | 91 | 54.9% | 18.1% |
| at_fire | all | label.break_high_1ext.wick_breached | 1986 | 43.1% | 0.651 | 0.611 | 0.569 | 199 | 61.3% | 18.3% |
| at_fire | bullish | label.break_low_1ext.close_past | 1068 | 36.0% | 0.650 | 0.632 | 0.640 | 107 | 44.9% | 8.8% |
| at_fire | bearish | label.break_low_1ext.wick_breached | 909 | 46.3% | 0.650 | 0.584 | 0.537 | 91 | 67.0% | 20.7% |
| at_fire | bearish | label.break_low_1ext.close_past | 909 | 44.7% | 0.649 | 0.589 | 0.553 | 91 | 61.5% | 16.9% |
| at_fire | all | label.break_high_1ext.close_past | 1986 | 42.0% | 0.645 | 0.613 | 0.580 | 199 | 55.3% | 13.3% |
| at_fire | bullish | label.break_low.close_past | 1068 | 63.5% | 0.643 | 0.650 | 0.635 | 107 | 74.8% | 11.3% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.break_high.wick_breached | ft.side_bearish=4370; ft.ed.first_third_range_pts=4002; ft.ed.n_1m_bars_in_first_third=2273; ts.month=1396; ts.year=971; ft.ed.first_third_high=910; ts.day_of_week=856; ft.ed.first_third_low=583; ft.side_bullish=476; ft.ed.ext_below_low_1x_range=455 |
| at_fire | all | label.break_high.close_past | ft.side_bearish=4140; ft.ed.first_third_range_pts=3941; ft.ed.n_1m_bars_in_first_third=2047; ts.month=1497; ts.day_of_week=982; ft.ed.first_third_high=927; ts.year=912; ft.side_bullish=480; ft.ed.first_third_low=479; ft.ed.ext_below_low_1x_range=436 |
| at_fire | all | label.break_low.wick_breached | ft.ed.first_third_range_pts=4377; ft.side_bearish=3676; ft.ed.n_1m_bars_in_first_third=2266; ts.year=1547; ts.month=1452; ft.side_bullish=1381; ts.day_of_week=1295; ft.ed.first_third_high=685; ft.ed.first_third_low=525; ft.ed.ext_below_low_05x_range=508 |
| at_fire | all | label.break_low.close_past | ft.side_bearish=4160; ft.ed.first_third_range_pts=3889; ft.ed.n_1m_bars_in_first_third=2433; ts.month=1553; ts.year=1502; ts.day_of_week=1462; ft.side_bullish=880; ft.ed.first_third_high=712; ft.ed.first_third_low=523; ft.ed.ext_below_low_1x_range=463 |
| at_fire | all | label.break_low_1ext.wick_breached | ft.ed.first_third_range_pts=4576; ft.ed.n_1m_bars_in_first_third=3701; ts.year=2025; ts.month=1280; ts.day_of_week=1153; ft.side_bearish=778; ft.ed.ext_below_low_1x_range=748; ft.ed.first_third_low=647; ft.ed.first_third_high=485; ft.ed.ext_below_low_05x_range=386 |
| at_fire | all | label.break_low_05ext.wick_breached | ft.ed.first_third_range_pts=4868; ft.ed.n_1m_bars_in_first_third=2875; ft.side_bearish=2161; ts.year=1588; ts.month=1260; ts.day_of_week=1152; ft.ed.ext_below_low_05x_range=642; ft.ed.first_third_low=590; ft.ed.first_third_high=520; ft.ed.ext_below_low_1x_range=422 |
| at_fire | bullish | label.break_low_05ext.wick_breached | ft.ed.first_third_range_pts=3497; ft.ed.n_1m_bars_in_first_third=1751; ts.month=1066; ts.year=1034; ts.day_of_week=906; ft.ed.first_third_low=474; ft.ed.first_third_high=375; ft.ed.first_third_close=359; ft.ed.ext_below_low_1x_range=339; ft.ed.ext_above_high_1x_range=295 |
| at_fire | bullish | label.break_low_1ext.wick_breached | ft.ed.first_third_range_pts=2388; ft.ed.n_1m_bars_in_first_third=1245; ts.year=912; ts.day_of_week=589; ts.month=539; ft.ed.first_third_high=297; ft.ed.first_third_low=296; ft.ed.ext_below_low_1x_range=242; ft.ed.first_third_mid=160; ft.ed.ext_below_low_05x_range=151 |
| at_fire | bullish | label.break_low_05ext.close_past | ft.ed.first_third_range_pts=2771; ft.ed.n_1m_bars_in_first_third=1227; ts.day_of_week=840; ts.month=823; ts.year=773; ft.ed.first_third_low=429; ft.ed.ext_below_low_1x_range=322; ft.ed.ext_below_low_05x_range=292; ft.ed.first_third_high=250; ft.ed.ext_above_high_1x_range=229 |
| at_fire | bullish | label.break_low.wick_breached | ft.ed.first_third_range_pts=2838; ft.ed.n_1m_bars_in_first_third=1476; ts.year=1169; ts.day_of_week=1101; ft.ed.first_third_high=927; ts.month=797; ft.ed.first_third_low=488; xd.has_disp_in_24h=355; ft.ed.first_third_mid=314; ft.ed.ext_below_low_1x_range=277 |
| at_fire | all | label.break_low_1ext.close_past | ft.ed.first_third_range_pts=4356; ft.ed.n_1m_bars_in_first_third=3168; ts.year=1855; ts.day_of_week=1023; ts.month=1013; ft.ed.ext_below_low_1x_range=758; ft.side_bearish=619; ft.side_bullish=495; ft.ed.first_third_mid=477; ft.ed.ext_below_low_05x_range=465 |
| at_fire | all | label.break_low_05ext.close_past | ft.ed.first_third_range_pts=4946; ft.ed.n_1m_bars_in_first_third=2396; ft.side_bearish=2142; ts.year=1615; ts.month=1446; ts.day_of_week=1283; ft.ed.first_third_low=703; ft.ed.ext_below_low_05x_range=642; ft.ed.ext_below_low_1x_range=593; ft.ed.first_third_high=507 |
| at_fire | bearish | label.break_high_1ext.wick_breached | ft.ed.first_third_range_pts=4673; ft.ed.n_1m_bars_in_first_third=1855; ft.ed.first_third_high=979; ts.month=944; ts.day_of_week=859; ts.year=771; ft.ed.first_third_low=654; ft.ed.ext_above_high_1x_range=496; ft.ed.ext_above_high_05x_range=408; ft.ed.ext_below_low_05x_range=360 |
| at_fire | bearish | label.break_high_1ext.close_past | ft.ed.first_third_range_pts=5003; ft.ed.n_1m_bars_in_first_third=2462; ts.month=1134; ft.ed.first_third_high=1115; ts.day_of_week=1054; ts.year=997; ft.ed.first_third_low=759; ft.ed.ext_above_high_1x_range=753; ft.ed.first_third_mid=503; ft.ed.ext_above_high_05x_range=473 |
| at_fire | all | label.break_high_1ext.wick_breached | ft.ed.first_third_range_pts=6968; ft.ed.n_1m_bars_in_first_third=3892; ts.year=1592; ft.side_bearish=1431; ts.month=1395; ft.ed.first_third_low=1097; ts.day_of_week=913; ft.ed.first_third_high=810; ft.ed.ext_above_high_1x_range=737; ft.ed.first_third_close=686 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
