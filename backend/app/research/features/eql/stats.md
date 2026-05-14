# Equal Levels - Current Stats

_Generated `2026-05-14T04:32:15+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Clustered equal highs/lows and later take/reversal behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `eql` / `equal_levels` |
| Total feature rows | 60,338 |
| Date range | 2015-01-02 -> 2026-05-07 |
| Outcomes coverage | 60,338 / 60,338 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `eq_pivot_3_1h_15pts` | 21,077 | 34.9% |
| `eq_pivot_3_1h_5pts` | 12,975 | 21.5% |
| `eq_pivot_5_1h_15pts` | 11,850 | 19.6% |
| `eq_pivot_5_1h_5pts` | 6,876 | 11.4% |
| `eq_pivot_3_4h_15pts` | 4,681 | 7.8% |
| `eq_pivot_5_4h_15pts` | 2,504 | 4.1% |
| `eq_pivot_5_daily_30pts` | 375 | 0.6% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v1` | 60,338 | 100.0% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `ES.c.0` | 30,380 | 50.3% |
| `NQ.c.0` | 18,307 | 30.3% |
| `YM.c.0` | 11,651 | 19.3% |

### By Side

| Side | Events | Share |
|---|---|---|
| `high` | 31,471 | 52.2% |
| `low` | 28,867 | 47.8% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 60,338 |
| Columns | 81 |
| ed.* event_data | 13 |
| oc.* outcome labels | 41 |
| ctx.* context | 4 |
| xd.* cross-detector | 14 |
| numeric | 70 |
| object/category | 10 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.take.wick_taken` | 48,051 / 60,338 | 79.6% |
| `oc.take.close_past` | 45,422 / 60,338 | 75.3% |
| `oc.take.first_take_was_reversal` | 22,530 / 48,051 | 46.9% |

### Breakdown - `oc.take.wick_taken` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `eq_pivot_3_1h_15pts` | 17,270 / 21,077 | 81.9% |
| `eq_pivot_3_1h_5pts` | 11,063 / 12,975 | 85.3% |
| `eq_pivot_3_4h_15pts` | 3,261 / 4,681 | 69.7% |
| `eq_pivot_5_1h_15pts` | 9,225 / 11,850 | 77.8% |
| `eq_pivot_5_1h_5pts` | 5,576 / 6,876 | 81.1% |
| `eq_pivot_5_4h_15pts` | 1,583 / 2,504 | 63.2% |
| `eq_pivot_5_daily_30pts` | 73 / 375 | 19.5% |

### Breakdown - `oc.take.wick_taken` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `high` | 26,702 / 31,471 | 84.8% |
| `low` | 21,349 / 28,867 | 74.0% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.take.wick_taken` | 48,051 / 60,338 | 79.6% |
| `oc.take.close_past` | 45,422 / 60,338 | 75.3% |
| `oc.take.first_take_was_reversal` | 22,530 / 48,051 | 46.9% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

| Label | test n | majority | LGB AUC | LGB acc | lift | status | note |
|---|---|---|---|---|---|---|---|
| `oc.take.wick_taken` | 8383 | 0.822 | 0.618 | 0.826 | 0.004 | ok |  |
| `oc.take.close_past` | 8383 | 0.771 | 0.567 | 0.774 | 0.003 | ok |  |
| `oc.take.first_take_was_reversal` | 6891 | 0.504 | 0.529 | 0.506 | 0.002 | ok |  |

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| eql | low | `label.take.wick_taken` | 4,033 | 77.8% | 0.639 | 88.1% |  |
| eql | all | `label.take.wick_taken` | 8,383 | 82.2% | 0.612 | 91.9% |  |
| eql | low | `label.take.close_past` | 4,033 | 70.7% | 0.592 | 79.0% |  |
| eql | all | `label.take.close_past` | 8,383 | 77.1% | 0.577 | 85.0% |  |
| eql | high | `label.take.close_past` | 4,350 | 83.1% | 0.563 | 80.5% |  |
| eql | high | `label.take.wick_taken` | 4,350 | 86.3% | 0.535 | 89.2% |  |
| eql | all | `label.take.first_take_was_reversal` | 6,891 | 49.6% | 0.517 | 50.6% |  |
| eql | low | `label.take.first_take_was_reversal` | 3,137 | 51.4% | 0.514 | 55.7% |  |
| eql | high | `label.take.first_take_was_reversal` | 3,754 | 48.1% | 0.486 | 46.3% |  |

## Reading

Weak-to-moderate signal. Useful as context more than as an anchor.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/eql.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_EQL.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
