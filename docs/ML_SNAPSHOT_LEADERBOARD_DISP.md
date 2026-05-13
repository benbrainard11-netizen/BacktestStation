# ML snapshot leaderboard

_Generated `2026-05-11T23:01:25.251324+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\disp_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\disp_snapshots.schema.json`
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
| C:\Users\benbr\BacktestStation\data\ml\anchors\disp_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\disp_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 38747 |
| schema_feature_columns | 44 |
| schema_label_columns | 33 |
| grid_attempts | 15 |
| trained_ok | 12 |
| skipped | 3 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | bearish | label.retracement.tapped_open | 3714 | 77.2% | 0.681 | 0.789 | 0.772 | 372 | 90.9% | 13.7% |
| at_fire | bearish | label.retracement.tapped_full | 3714 | 73.2% | 0.675 | 0.747 | 0.732 | 372 | 86.8% | 13.7% |
| at_fire | bearish | label.retracement.tapped_mid | 3714 | 89.0% | 0.673 | 0.890 | 0.890 | 372 | 94.6% | 5.6% |
| at_fire | all | label.retracement.tapped_open | 7430 | 73.4% | 0.671 | 0.744 | 0.734 | 743 | 89.9% | 16.5% |
| at_fire | bearish | label.invalidation.invalidated | 3714 | 70.1% | 0.665 | 0.714 | 0.701 | 372 | 86.3% | 16.2% |
| at_fire | all | label.retracement.tapped_full | 7430 | 69.3% | 0.662 | 0.706 | 0.693 | 743 | 86.7% | 17.3% |
| at_fire | all | label.retracement.tapped_mid | 7430 | 86.3% | 0.661 | 0.863 | 0.863 | 743 | 95.8% | 9.5% |
| at_fire | all | label.invalidation.invalidated | 7430 | 64.9% | 0.655 | 0.670 | 0.649 | 743 | 82.4% | 17.5% |
| at_fire | bullish | label.retracement.tapped_open | 3716 | 69.7% | 0.636 | 0.707 | 0.697 | 372 | 83.6% | 13.9% |
| at_fire | bullish | label.retracement.tapped_mid | 3716 | 83.6% | 0.631 | 0.836 | 0.836 | 372 | 93.3% | 9.6% |
| at_fire | bullish | label.retracement.tapped_full | 3716 | 65.5% | 0.625 | 0.668 | 0.655 | 372 | 82.3% | 16.8% |
| at_fire | bullish | label.invalidation.invalidated | 3716 | 59.7% | 0.616 | 0.623 | 0.597 | 372 | 70.2% | 10.4% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | bearish | label.retracement.tapped_open | disp.ed.ratio_vs_recent_mean=6719; disp.ctx.day_of_week_et=2955; ts.day_of_week=1889; ts.month=1725; disp.ed.body_to_range_ratio=1700; ts.year=1354; ts.hour_of_day_utc=1282; disp.event_type_1h_disp=1198; disp.day_of_week=1132; disp.ctx.hour_of_day_et=1039 |
| at_fire | bearish | label.retracement.tapped_full | disp.ed.ratio_vs_recent_mean=6141; disp.ctx.day_of_week_et=2981; disp.day_of_week=2266; ts.month=1962; ts.year=1639; ts.hour_of_day_utc=1563; disp.event_type_1h_disp=1510; ts.day_of_week=1408; disp.hour_of_day_utc=1116; disp.ed.body_to_range_ratio=931 |
| at_fire | bearish | label.retracement.tapped_mid | disp.ed.ratio_vs_recent_mean=3368; disp.ctx.day_of_week_et=1898; ts.month=1501; ts.year=1280; disp.ed.body_to_range_ratio=1211; ts.hour_of_day_utc=783; disp.hour_of_day_utc=770; ts.day_of_week=560; disp.event_type_1h_disp=545; disp.ctx.hour_of_day_et=458 |
| at_fire | all | label.retracement.tapped_open | disp.ed.ratio_vs_recent_mean=13709; disp.day_of_week=5913; disp.ed.body_to_range_ratio=4276; disp.side_bearish=3862; ts.hour_of_day_utc=3263; ts.day_of_week=3027; disp.ctx.day_of_week_et=2632; ts.month=2350; ts.year=2343; disp.ctx.hour_of_day_et=1924 |
| at_fire | bearish | label.invalidation.invalidated | disp.ed.ratio_vs_recent_mean=5204; disp.ctx.day_of_week_et=3687; ts.month=1938; disp.event_type_1h_disp=1741; ts.year=1585; disp.day_of_week=1385; ts.hour_of_day_utc=1281; ts.day_of_week=1197; disp.ed.body_to_range_ratio=1008; disp.hour_of_day_utc=893 |
| at_fire | all | label.retracement.tapped_full | disp.ed.ratio_vs_recent_mean=12165; disp.day_of_week=7319; ts.hour_of_day_utc=5462; disp.side_bearish=3958; ts.day_of_week=2822; ts.month=2321; disp.event_type_1h_disp=2261; ts.year=2147; disp.ctx.hour_of_day_et=2060; disp.ed.body_to_range_ratio=2017 |
| at_fire | all | label.retracement.tapped_mid | disp.ed.ratio_vs_recent_mean=8274; disp.ctx.day_of_week_et=4499; disp.ed.body_to_range_ratio=3012; disp.side_bearish=2931; ts.hour_of_day_utc=1788; ts.month=1293; ts.year=1271; disp.ctx.hour_of_day_et=1257; disp.hour_of_day_utc=1074; disp.day_of_week=877 |
| at_fire | all | label.invalidation.invalidated | disp.ed.ratio_vs_recent_mean=10556; disp.day_of_week=8750; disp.side_bearish=5111; ts.hour_of_day_utc=3039; disp.event_type_1h_disp=2955; disp.ed.body_to_range_ratio=2723; ts.year=2444; ts.day_of_week=2346; ts.month=2256; disp.hour_of_day_utc=1852 |
| at_fire | bullish | label.retracement.tapped_open | disp.ed.ratio_vs_recent_mean=7010; disp.day_of_week=3571; disp.ed.body_to_range_ratio=3174; ts.month=2263; ts.year=2167; ts.hour_of_day_utc=1953; disp.ctx.hour_of_day_et=1708; disp.ctx.day_of_week_et=1449; disp.ed.body_pts=1377; disp.hour_of_day_utc=1156 |
| at_fire | bullish | label.retracement.tapped_mid | disp.ed.ratio_vs_recent_mean=4704; disp.ed.body_to_range_ratio=2266; disp.ctx.day_of_week_et=1880; ts.hour_of_day_utc=1541; disp.day_of_week=1513; ts.month=1481; ts.year=1207; disp.ctx.hour_of_day_et=1082; disp.ed.rolling_mean_body_pts=784; disp.ed.body_pts=629 |
| at_fire | bullish | label.retracement.tapped_full | disp.ed.ratio_vs_recent_mean=5591; disp.day_of_week=3584; ts.hour_of_day_utc=3358; disp.ed.body_to_range_ratio=2681; ts.year=2408; ts.month=1671; disp.ctx.hour_of_day_et=1554; disp.ed.range_pts=1425; ts.day_of_week=1408; disp.ed.body_pts=1262 |
| at_fire | bullish | label.invalidation.invalidated | disp.ed.ratio_vs_recent_mean=5298; disp.day_of_week=3811; ts.year=2640; disp.ed.body_to_range_ratio=2524; ts.month=2398; ts.hour_of_day_utc=2252; ts.day_of_week=1879; disp.hour_of_day_utc=1418; disp.ctx.hour_of_day_et=1394; disp.ed.body_pts=959 |

## Skipped Summary

| status | count |
|---|---|
| skip_train_imbalance | 2 |
| skip_test_imbalance | 1 |

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
