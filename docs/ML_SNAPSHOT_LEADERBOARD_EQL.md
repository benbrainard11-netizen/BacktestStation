# ML snapshot leaderboard

_Generated `2026-05-11T23:26:47.390576+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\eql_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\eql_snapshots.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `high, low, all`
- Labels searched: `3` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\eql_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\eql_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 60338 |
| schema_feature_columns | 39 |
| schema_label_columns | 38 |
| grid_attempts | 9 |
| trained_ok | 9 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | low | label.take.wick_taken | 4033 | 77.8% | 0.639 | 0.781 | 0.778 | 404 | 88.1% | 10.3% |
| at_fire | all | label.take.wick_taken | 8383 | 82.2% | 0.612 | 0.825 | 0.822 | 839 | 91.9% | 9.7% |
| at_fire | low | label.take.close_past | 4033 | 70.7% | 0.592 | 0.712 | 0.707 | 404 | 79.0% | 8.2% |
| at_fire | all | label.take.close_past | 8383 | 77.1% | 0.577 | 0.771 | 0.771 | 839 | 85.0% | 7.9% |
| at_fire | high | label.take.close_past | 4350 | 83.1% | 0.563 | 0.831 | 0.831 | 435 | 80.5% | -2.6% |
| at_fire | high | label.take.wick_taken | 4350 | 86.3% | 0.535 | 0.863 | 0.863 | 435 | 89.2% | 2.9% |
| at_fire | all | label.take.first_take_was_reversal | 6891 | 49.6% | 0.517 | 0.504 | 0.504 | 690 | 50.6% | 1.0% |
| at_fire | low | label.take.first_take_was_reversal | 3137 | 51.4% | 0.514 | 0.486 | 0.486 | 314 | 55.7% | 4.3% |
| at_fire | high | label.take.first_take_was_reversal | 3754 | 48.1% | 0.486 | 0.519 | 0.519 | 376 | 46.3% | -1.8% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | low | label.take.wick_taken | eql.ed.cluster_max_price=8358; eql.ed.cluster_mid=5811; ts.month=5736; eql.ed.level_price=5466; eql.ed.cluster_spread_pts=4458; ts.year=3603; eql.month=2523; ts.hour_of_day_utc=2244; eql.ctx.hour_of_day_et=2186; eql.ed.parent_pivot_mode_pivot_3_1h=1866 |
| at_fire | all | label.take.wick_taken | eql.ed.level_price=13405; eql.side_high=10983; ts.month=10275; eql.ed.cluster_min_price=10050; ts.year=8234; eql.ed.cluster_spread_pts=7396; eql.ed.cluster_max_price=6954; eql.ed.cluster_mid=6524; eql.ed.tolerance_pts=4756; ts.hour_of_day_utc=4479 |
| at_fire | low | label.take.close_past | eql.ed.cluster_mid=12830; eql.ed.level_price=12004; ts.month=11447; eql.ed.cluster_max_price=9080; ts.year=6657; eql.month=5461; eql.ed.cluster_spread_pts=4387; eql.ctx.hour_of_day_et=3150; eql.ed.cluster_min_price=3018; eql.ed.parent_pivot_mode_pivot_3_1h=2052 |
| at_fire | all | label.take.close_past | eql.ed.level_price=19687; ts.month=15672; eql.side_high=15472; ts.year=12114; eql.ed.cluster_min_price=12090; eql.ed.cluster_max_price=10817; eql.ed.cluster_mid=9795; eql.month=7313; eql.ed.cluster_spread_pts=7240; eql.year=5097 |
| at_fire | high | label.take.close_past | eql.ed.level_price=1236; ts.year=649; ts.month=631; eql.ed.tolerance_pts=601; eql.ed.n_members=508; ts.day_of_week=237; eql.ed.cluster_mid=224; eql.event_type_eq_pivot_3_4h_15pts=220; eql.ed.cluster_min_price=165; eql.ed.parent_pivot_mode_pivot_5_4h=148 |
| at_fire | high | label.take.wick_taken | ts.year=1263; ts.month=1079; eql.ed.tolerance_pts=1072; eql.ed.level_price=1042; eql.ed.cluster_max_price=713; eql.ed.cluster_min_price=484; eql.ed.cluster_spread_pts=452; ts.day_of_week=403; eql.ed.n_members=358; ts.hour_of_day_utc=284 |
| at_fire | all | label.take.first_take_was_reversal | eql.ed.level_price=1197; eql.ed.cluster_max_price=545; ts.month=303; eql.ed.cluster_min_price=299; eql.ed.cluster_spread_pts=276; eql.side_high=228; eql.day_of_week=166; eql.ed.cluster_mid=163; eql.month=121; ts.year=110 |
| at_fire | low | label.take.first_take_was_reversal | eql.ed.cluster_max_price=428; eql.ed.level_price=405; eql.ed.cluster_mid=291; ts.month=284; eql.month=170; eql.year=161; ts.year=75; xd.has_psp_in_24h=75; eql.hour_of_day_utc=68; eql.ctx.hour_of_day_et=63 |
| at_fire | high | label.take.first_take_was_reversal | eql.ed.level_price=645; eql.ed.cluster_max_price=337; eql.month=266; ts.year=260; ts.month=257; eql.ed.cluster_mid=213; eql.ed.cluster_spread_pts=173; eql.ed.cluster_min_price=163; eql.day_of_week=142; eql.ed.n_members=133 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
