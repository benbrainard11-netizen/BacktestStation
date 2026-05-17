# Swing Pivot - Current Stats

_Generated `2026-05-17T22:06:25+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Confirmed swing highs/lows used as liquidity-map levels.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `swing` / `swing_pivot` |
| Total feature rows | 345,702 |
| Date range | 2015-01-02 -> 2026-05-07 |
| Outcomes coverage | 76,786 / 76,786 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `pivot_3_1h` | 35,920 | 46.8% |
| `pivot_5_1h` | 22,424 | 29.2% |
| `pivot_3_4h` | 10,691 | 13.9% |
| `pivot_5_4h` | 6,585 | 8.6% |
| `pivot_5_daily` | 1,166 | 1.5% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v1` | 76,779 | 100.0% |
| `(missing)` | 7 | 0.0% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `YM.c.0` | 26,036 | 33.9% |
| `NQ.c.0` | 26,036 | 33.9% |
| `ES.c.0` | 24,714 | 32.2% |

### By Side

| Side | Events | Share |
|---|---|---|
| `high` | 38,657 | 50.3% |
| `low` | 38,129 | 49.7% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 345,702 |
| Columns | 73 |
| ed.* event_data | 14 |
| oc.* outcome labels | 33 |
| ctx.* context | 3 |
| xd.* cross-detector | 14 |
| numeric | 61 |
| object/category | 11 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.breakout.wick_taken` | 245,527 / 345,672 | 71.0% |
| `oc.breakout.close_taken` | 222,864 / 345,672 | 64.5% |

### Breakdown - `oc.breakout.wick_taken` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `pivot_3_1h` | 114,974 / 156,794 | 73.3% |
| `pivot_3_4h` | 38,474 / 51,370 | 74.9% |
| `pivot_5_1h` | 66,078 / 99,487 | 66.4% |
| `pivot_5_4h` | 21,691 / 31,622 | 68.6% |
| `pivot_5_daily` | 4,310 / 6,399 | 67.4% |

### Breakdown - `oc.breakout.wick_taken` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `high` | 125,849 / 174,562 | 72.1% |
| `low` | 119,678 / 171,110 | 69.9% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.breakout.wick_taken` | 245,527 / 345,672 | 71.0% |
| `oc.breakout.close_taken` | 222,864 / 345,672 | 64.5% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

| Label | test n | majority | LGB AUC | LGB acc | lift | status | note |
|---|---|---|---|---|---|---|---|
| `oc.breakout.wick_taken` | 14738 | 0.698 | 0.671 | 0.721 | 0.023 | ok |  |
| `oc.breakout.close_taken` | 14738 | 0.618 | 0.638 | 0.654 | 0.036 | ok |  |

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| swing_snapshot_leaderboard_strict_context.parquet | all | `label.strict.next_60m.pivot_broken_through_continuation` | 14,747 | 5.2% | 0.805 | 18.9% | imbalanced base rate |
| swing_snapshot_leaderboard_strict_context.parquet | all | `label.strict.next_240m.pivot_broken_through_continuation` | 14,747 | 18.1% | 0.804 | 47.7% |  |
| swing_snapshot_leaderboard_strict_context.parquet | low | `label.strict.next_240m.pivot_broken_through_continuation` | 7,337 | 17.7% | 0.803 | 46.6% |  |
| swing_snapshot_leaderboard_strict_context.parquet | high | `label.strict.next_240m.pivot_broken_through_continuation` | 7,410 | 18.5% | 0.799 | 47.2% |  |
| swing_snapshot_leaderboard_strict_context.parquet | high | `label.strict.next_60m.pivot_broken_through_continuation` | 7,410 | 5.4% | 0.799 | 18.1% | imbalanced base rate |
| swing_snapshot_leaderboard_strict_context.parquet | low | `label.strict.next_60m.pivot_broken_through_continuation` | 7,337 | 5.1% | 0.789 | 17.7% | imbalanced base rate |
| swing_snapshot_leaderboard_strict_context.parquet | low | `label.strict.next_60m.pivot_failed_immediately` | 7,337 | 5.8% | 0.772 | 17.2% | imbalanced base rate |
| swing_snapshot_leaderboard_strict_context.parquet | all | `label.strict.next_60m.pivot_failed_immediately` | 14,747 | 6.2% | 0.771 | 19.2% | imbalanced base rate |
| swing_snapshot_leaderboard_strict_context.parquet | all | `label.strict.next_240m.pivot_failed_immediately` | 14,747 | 6.3% | 0.769 | 18.2% | imbalanced base rate |
| swing_snapshot_leaderboard_strict_context.parquet | low | `label.strict.next_240m.pivot_failed_immediately` | 7,337 | 6.0% | 0.765 | 18.8% | imbalanced base rate |

## Reading

Good standalone signal.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/swing.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_SWING_STRICT_CONTEXT.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
