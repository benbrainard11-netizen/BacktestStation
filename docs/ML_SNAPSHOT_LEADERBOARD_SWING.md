# ML snapshot leaderboard

_Generated `2026-05-11T23:26:46.545592+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\swing_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\swing_snapshots.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `high, low, all`
- Labels searched: `2` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\swing_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\swing_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 76786 |
| schema_feature_columns | 37 |
| schema_label_columns | 29 |
| grid_attempts | 6 |
| trained_ok | 6 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | all | label.breakout.wick_taken | 14740 | 69.8% | 0.668 | 0.722 | 0.698 | 1474 | 85.3% | 15.5% |
| at_fire | high | label.breakout.wick_taken | 7406 | 74.8% | 0.666 | 0.759 | 0.748 | 741 | 86.6% | 11.8% |
| at_fire | low | label.breakout.wick_taken | 7334 | 64.7% | 0.647 | 0.681 | 0.647 | 734 | 79.8% | 15.2% |
| at_fire | high | label.breakout.close_taken | 7406 | 68.6% | 0.639 | 0.708 | 0.686 | 741 | 79.5% | 10.9% |
| at_fire | all | label.breakout.close_taken | 14740 | 61.8% | 0.626 | 0.654 | 0.618 | 1474 | 75.6% | 13.8% |
| at_fire | low | label.breakout.close_taken | 7334 | 55.0% | 0.623 | 0.600 | 0.550 | 734 | 69.3% | 14.3% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | all | label.breakout.wick_taken | ts.hour_of_day_utc=24410; swing.day_of_week=12416; swing.ctx.hour_of_day_et=10073; swing.side_high=6841; ts.day_of_week=6239; swing.ed.tracking_timeframe_1h=4757; ts.month=3865; ts.year=3642; swing.hour_of_day_utc=2184; swing.ed.n=1978 |
| at_fire | high | label.breakout.wick_taken | ts.hour_of_day_utc=9950; ts.day_of_week=7000; swing.ctx.hour_of_day_et=3619; swing.ed.tracking_timeframe_1h=3063; ts.month=2683; ts.year=2678; swing.hour_of_day_utc=1906; swing.day_of_week=1700; swing.month=1139; swing.ctx.day_of_week_et=1091 |
| at_fire | low | label.breakout.wick_taken | ts.hour_of_day_utc=13386; swing.day_of_week=7939; swing.ctx.hour_of_day_et=6358; ts.month=5406; ts.year=5178; swing.hour_of_day_utc=4374; swing.ed.pivot_price=3882; ts.day_of_week=2726; swing.month=2473; swing.ed.pivot_bar.open=1910 |
| at_fire | high | label.breakout.close_taken | ts.hour_of_day_utc=8958; ts.day_of_week=6597; ts.month=3499; swing.ed.tracking_timeframe_1h=3268; swing.ctx.hour_of_day_et=3060; ts.year=2974; swing.hour_of_day_utc=2364; swing.day_of_week=2317; swing.ctx.day_of_week_et=1441; swing.month=1221 |
| at_fire | all | label.breakout.close_taken | ts.hour_of_day_utc=20626; swing.day_of_week=11131; swing.side_high=9296; swing.ctx.hour_of_day_et=8069; ts.day_of_week=7726; ts.month=5041; ts.year=4719; swing.ed.tracking_timeframe_1h=4077; swing.hour_of_day_utc=3352; swing.ed.pivot_price=2941 |
| at_fire | low | label.breakout.close_taken | ts.hour_of_day_utc=10766; swing.day_of_week=7321; swing.ctx.hour_of_day_et=6520; ts.month=5932; ts.year=5825; ts.day_of_week=3107; swing.ed.pivot_price=3070; swing.hour_of_day_utc=3044; swing.month=2542; swing.year=2056 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
