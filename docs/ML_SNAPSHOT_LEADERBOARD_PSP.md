# ML snapshot leaderboard

_Generated `2026-05-11T23:25:01.922882+00:00`._

## Setup

- Matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\psp_snapshots.parquet`
- Schema: `C:\Users\benbr\BacktestStation\data\ml\anchors\psp_snapshots.schema.json`
- Event type: `all`
- Snapshots: `at_fire`
- Sides: `bullish, bearish, all`
- Labels searched: `1` binary labels
- Top bucket: `10%` of test rows
- Split: train <= 2022 / val = 2023 / test >= 2024
- Manual composite feature included in training: `False`

## Output Files

| file | purpose |
|---|---|
| C:\Users\benbr\BacktestStation\data\ml\anchors\psp_snapshot_leaderboard.csv | CSV leaderboard |
| C:\Users\benbr\BacktestStation\data\ml\anchors\psp_snapshot_leaderboard.parquet | Parquet leaderboard |

## Coverage

| item | value |
|---|---|
| schema_rows | 15827 |
| schema_feature_columns | 51 |
| schema_label_columns | 33 |
| grid_attempts | 3 |
| trained_ok | 3 |
| skipped | 0 |

## Top Models

| snapshot | side | label | test_n | base_rate | test_auc | test_acc | majority_acc | top_n | top_rate | top_lift |
|---|---|---|---|---|---|---|---|---|---|---|
| at_fire | bullish | label.majority_reaction.all_rolled | 1891 | 43.4% | 0.514 | 0.566 | 0.566 | 190 | 46.3% | 2.9% |
| at_fire | bearish | label.majority_reaction.all_rolled | 1958 | 39.9% | 0.500 | 0.601 | 0.601 | 196 | 43.9% | 4.0% |
| at_fire | all | label.majority_reaction.all_rolled | 3849 | 41.6% | 0.493 | 0.570 | 0.584 | 385 | 40.3% | -1.4% |

## Top Features For Best Models

| snapshot | side | label | top_features |
|---|---|---|---|
| at_fire | bullish | label.majority_reaction.all_rolled | psp.ed.per_symbol_states.NQ.c.0.body_pts=95; psp.ed.per_symbol_states.NQ.c.0.open=47; psp.ed.per_symbol_states.YM.c.0.body_pts=27; psp.ed.per_symbol_states.ES.c.0.open=27; psp.ed.per_symbol_states.YM.c.0.close=23; ts.day_of_week=20; psp.ed.per_symbol_states.NQ.c.0.close=20; psp.ed.per_symbol_states.NQ.c.0.high=20; psp.hour_of_day_utc=19; ts.hour_of_day_utc=15 |
| at_fire | bearish | label.majority_reaction.all_rolled | psp.ed.per_symbol_states.YM.c.0.body_pts=81; psp.ed.per_symbol_states.YM.c.0.high=66; psp.ed.per_symbol_states.NQ.c.0.body_pts=59; psp.ed.per_symbol_states.NQ.c.0.high=38; psp.ed.per_symbol_states.ES.c.0.body_pts=31; psp.ctx.hour_of_day_et=31; psp.hour_of_day_utc=27; psp.ed.per_symbol_states.ES.c.0.open=20; ts.day_of_week=18; psp.ed.per_symbol_states.ES.c.0.low=15 |
| at_fire | all | label.majority_reaction.all_rolled | psp.ed.per_symbol_states.NQ.c.0.body_pts=709; psp.ed.bullish_symbols__len=595; psp.ed.per_symbol_states.YM.c.0.body_pts=571; psp.ed.per_symbol_states.ES.c.0.body_pts=461; psp.ed.per_symbol_states.YM.c.0.high=330; psp.ed.per_symbol_states.NQ.c.0.open=309; psp.ed.per_symbol_states.ES.c.0.open=298; ts.hour_of_day_utc=282; psp.ed.per_symbol_states.YM.c.0.close=271; ts.month=251 |

## Skipped Summary

None.

## Interpretation

- Treat this as a signal triage table, not a final trading model.
- The current best rows still use one fixed chronological split; the next hardening step is walk-forward validation.
- `primary_took_period_n_high` and `primary_took_period_n_low` are raw directional labels. For one SMT side they can duplicate thesis confirmation; for the opposite side they represent the other range side.
- `at_period_close` models can legally use `pc.*` features; `at_fire` models cannot, and should be expected to rank weaker unless fire-time features improve.
