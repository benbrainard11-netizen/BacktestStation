# Swing Pivot - Current Stats

_Generated `2026-05-14T04:32:12+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Confirmed swing highs/lows used as liquidity-map levels.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `swing` / `swing_pivot` |
| Total feature rows | 76,786 |
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
| Rows | 76,786 |
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
| `oc.breakout.wick_taken` | 53,560 / 76,779 | 69.8% |
| `oc.breakout.close_taken` | 47,754 / 76,779 | 62.2% |

### Breakdown - `oc.breakout.wick_taken` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `pivot_3_1h` | 25,640 / 35,919 | 71.4% |
| `pivot_3_4h` | 8,124 / 10,689 | 76.0% |
| `pivot_5_1h` | 14,378 / 22,424 | 64.1% |
| `pivot_5_4h` | 4,631 / 6,581 | 70.4% |
| `pivot_5_daily` | 787 / 1,166 | 67.5% |

### Breakdown - `oc.breakout.wick_taken` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `high` | 28,748 / 38,653 | 74.4% |
| `low` | 24,812 / 38,126 | 65.1% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.breakout.wick_taken` | 53,560 / 76,779 | 69.8% |
| `oc.breakout.close_taken` | 47,754 / 76,779 | 62.2% |

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
| swing | all | `label.breakout.wick_taken` | 14,740 | 69.8% | 0.668 | 85.3% |  |
| swing | high | `label.breakout.wick_taken` | 7,406 | 74.8% | 0.666 | 86.6% |  |
| swing | low | `label.breakout.wick_taken` | 7,334 | 64.7% | 0.647 | 79.8% |  |
| swing | high | `label.breakout.close_taken` | 7,406 | 68.6% | 0.639 | 79.5% |  |
| swing | all | `label.breakout.close_taken` | 14,740 | 61.8% | 0.626 | 75.6% |  |
| swing | low | `label.breakout.close_taken` | 7,334 | 55.0% | 0.623 | 69.3% |  |

## Reading

Useful context signal, but not top-tier standalone.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/swing.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_SWING.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
