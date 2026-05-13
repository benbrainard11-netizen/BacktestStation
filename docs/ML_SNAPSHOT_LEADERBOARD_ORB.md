# ML snapshot leaderboard

_Generated `2026-05-11T23:27:49.042601+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\orb_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\orb_snapshots.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `bullish, bearish, all`
- Labels searched: `15` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\orb_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\orb_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 34040 |
| schema_feature_columns | 40 |
| schema_label_columns | 38 |
| grid_attempts | 45 |
| trained_ok | 45 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.broke_only_low | 6510 | 21.2% | 0.704 | 0.788 | 0.788 | 651 | 43.2% | 22.0% |
| at_fire | all | label.break_high.wick_breached | 6510 | 78.5% | 0.703 | 0.784 | 0.785 | 651 | 93.1% | 14.5% |
| at_fire | all | label.break_low.wick_breached | 6510 | 76.7% | 0.699 | 0.769 | 0.767 | 651 | 93.1% | 16.4% |
| at_fire | all | label.broke_only_high | 6510 | 23.0% | 0.694 | 0.772 | 0.770 | 651 | 45.3% | 22.4% |
| at_fire | all | label.break_low.close_past | 6510 | 73.7% | 0.678 | 0.737 | 0.737 | 651 | 86.3% | 12.6% |
| at_fire | all | label.break_high.close_past | 6510 | 76.0% | 0.672 | 0.749 | 0.760 | 651 | 87.4% | 11.4% |
| at_fire | all | label.break_low_1ext.wick_breached | 6510 | 44.0% | 0.666 | 0.625 | 0.560 | 651 | 70.0% | 26.1% |
| at_fire | all | label.break_low_1ext.close_past | 6510 | 41.4% | 0.660 | 0.629 | 0.586 | 651 | 63.0% | 21.6% |
| at_fire | all | label.break_low_05ext.wick_breached | 6510 | 58.5% | 0.653 | 0.623 | 0.585 | 651 | 76.5% | 18.0% |
| at_fire | all | label.break_high_05ext.wick_breached | 6510 | 60.1% | 0.652 | 0.626 | 0.601 | 651 | 79.7% | 19.6% |
| at_fire | all | label.break_low_05ext.close_past | 6510 | 55.7% | 0.651 | 0.612 | 0.557 | 651 | 74.0% | 18.4% |
| at_fire | all | label.break_high_1ext.wick_breached | 6510 | 43.6% | 0.649 | 0.616 | 0.564 | 651 | 65.0% | 21.4% |
| at_fire | bearish | label.break_low_1ext.wick_breached | 3161 | 51.7% | 0.642 | 0.606 | 0.517 | 317 | 62.8% | 11.1% |
| at_fire | bearish | label.break_high_1ext.wick_breached | 3161 | 35.6% | 0.640 | 0.648 | 0.644 | 317 | 51.1% | 15.5% |
| at_fire | bullish | label.break_low_1ext.wick_breached | 3296 | 36.6% | 0.640 | 0.649 | 0.634 | 330 | 58.8% | 22.2% |
| at_fire | all | label.break_high_1ext.close_past | 6510 | 41.8% | 0.639 | 0.612 | 0.582 | 651 | 60.8% | 19.0% |
| at_fire | bearish | label.break_high_1ext.close_past | 3161 | 34.2% | 0.639 | 0.652 | 0.658 | 317 | 49.2% | 15.0% |
| at_fire | bullish | label.break_low_1ext.close_past | 3296 | 34.3% | 0.638 | 0.668 | 0.657 | 330 | 55.8% | 21.4% |
| at_fire | all | label.break_high_05ext.close_past | 6510 | 57.8% | 0.637 | 0.608 | 0.578 | 651 | 75.3% | 17.4% |
| at_fire | bearish | label.break_low_1ext.close_past | 3161 | 49.0% | 0.633 | 0.598 | 0.510 | 317 | 60.9% | 11.9% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.broke_only_low | orb.side_bearish=13534; orb.ed.or_range_pts=5217; orb.side_bullish=3592; orb.ed.or_direction_bearish=3278; ts.month=3112; orb.event_type_ny_30m=2759; ts.year=2059; orb.ed.or_high=1810; orb.ed.n_bars_in_range=1668; orb.ctx.day_of_week_et=1320 |
| at_fire | all | label.break_high.wick_breached | orb.side_bearish=13583; orb.ed.or_range_pts=4888; orb.side_bullish=3550; orb.ed.or_direction_bearish=3277; orb.event_type_ny_30m=2802; ts.month=2595; ts.year=2003; orb.ed.n_bars_in_range=1643; orb.ed.or_high=1513; orb.ctx.day_of_week_et=1390 |
| at_fire | all | label.break_low.wick_breached | orb.side_bullish=12627; orb.ed.or_range_pts=3709; orb.side_bearish=3167; orb.ed.or_direction_bullish=3054; orb.event_type_ny_30m=3029; ts.year=2633; ts.month=2411; ts.day_of_week=1888; orb.ed.range_minutes=1549; xd.has_ft_in_24h=1233 |
| at_fire | all | label.broke_only_high | orb.side_bullish=12797; orb.ed.or_range_pts=3542; orb.side_bearish=3434; orb.ed.or_direction_bullish=3140; orb.event_type_ny_30m=3056; ts.year=2615; ts.month=2486; ts.day_of_week=1967; orb.ed.range_minutes=1380; orb.ed.or_direction_bearish=1068 |
| at_fire | all | label.break_low.close_past | orb.side_bullish=11107; orb.event_type_ny_30m=3111; orb.ed.or_direction_bullish=2616; orb.ed.or_range_pts=2364; ts.year=2287; orb.side_bearish=2126; ts.month=1872; ts.day_of_week=1640; xd.has_ft_in_24h=904; orb.event_type_ny_15m=889 |
| at_fire | all | label.break_high.close_past | orb.side_bearish=12536; orb.ed.or_range_pts=5693; ts.month=3480; orb.ed.or_direction_bearish=3161; orb.event_type_ny_30m=2944; orb.side_bullish=2767; ts.year=2322; orb.ed.or_high=2040; ts.day_of_week=1580; orb.ed.or_open=1469 |
| at_fire | all | label.break_low_1ext.wick_breached | orb.ed.n_bars_in_range=8654; orb.event_type_ny_30m=4768; orb.ed.or_range_pts=4441; orb.side_bullish=4255; ts.year=1882; ts.month=1717; orb.ed.range_minutes=1393; ts.day_of_week=1063; orb.ed.or_direction_bullish=1061; xd.has_ft_in_24h=937 |
| at_fire | all | label.break_low_1ext.close_past | orb.ed.n_bars_in_range=7969; orb.ed.or_range_pts=5253; orb.event_type_ny_30m=5038; orb.side_bullish=3991; ts.month=2888; ts.year=2431; ts.day_of_week=1311; orb.ed.range_minutes=1188; orb.ed.or_high=1161; orb.ed.or_direction_bullish=993 |
| at_fire | all | label.break_low_05ext.wick_breached | orb.ed.n_bars_in_range=7501; orb.side_bullish=6410; orb.ed.or_range_pts=5163; orb.event_type_ny_30m=3551; ts.month=2854; ts.year=2677; ts.day_of_week=2024; orb.ed.or_direction_bullish=1619; xd.has_ft_in_24h=1269; orb.ed.range_minutes=1232 |
| at_fire | all | label.break_high_05ext.wick_breached | orb.side_bearish=8350; orb.event_type_ny_30m=8105; orb.ed.or_range_pts=6411; ts.month=3007; ts.year=2500; orb.event_type_ny_15m=2208; orb.ed.n_bars_in_range=2089; orb.ctx.day_of_week_et=1978; orb.ed.or_high=1852; orb.ed.or_direction_bearish=1730 |
| at_fire | all | label.break_low_05ext.close_past | orb.ed.n_bars_in_range=6342; orb.side_bullish=6286; orb.ed.or_range_pts=4810; orb.event_type_ny_30m=4625; ts.month=3014; ts.year=2551; ts.day_of_week=1788; orb.ed.or_direction_bullish=1607; orb.ed.range_minutes=1087; orb.ctx.day_of_week_et=1057 |
| at_fire | all | label.break_high_1ext.wick_breached | orb.event_type_ny_30m=13600; orb.ed.or_range_pts=8298; orb.side_bearish=4220; orb.event_type_ny_15m=3728; ts.month=3299; ts.year=3176; xd.has_ft_in_24h=2925; orb.ed.ext_above_high_1x=2459; orb.ed.or_high=2115; orb.ed.n_bars_in_range=2097 |
| at_fire | bearish | label.break_low_1ext.wick_breached | orb.ed.n_bars_in_range=4543; orb.ed.or_range_pts=3159; ts.month=1751; ts.year=1744; orb.event_type_ny_30m=1124; ts.day_of_week=1063; orb.ed.or_high=618; orb.ed.range_minutes=565; xd.has_ft_in_24h=443; orb.ed.mode_ny_30m=426 |
| at_fire | bearish | label.break_high_1ext.wick_breached | orb.event_type_ny_30m=5627; orb.ed.or_range_pts=3757; orb.event_type_ny_15m=3087; orb.ed.mode_ny_30m=2091; orb.ctx.day_of_week_et=1317; ts.month=1311; orb.ed.or_high=1272; ts.year=1254; ts.day_of_week=864; orb.ed.n_bars_in_range=746 |
| at_fire | bullish | label.break_low_1ext.wick_breached | orb.event_type_ny_30m=3751; orb.ed.or_range_pts=3015; orb.ed.n_bars_in_range=2955; orb.ed.mode_ny_30m=1460; ts.year=1263; ts.month=1146; orb.ctx.day_of_week_et=802; ts.day_of_week=796; orb.ed.or_high=791; orb.ed.range_minutes=615 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
