# First-Third Range - Current Stats

_Generated `2026-05-12T02:14:19+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

First-third parent-period range and later break/extension behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `ft` / `first_third_range` |
| Total feature rows | 10,373 |
| Date range | 2015-01-02 -> 2026-05-08 |
| Outcomes coverage | 10,373 / 10,373 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `first_third_daily` | 8,630 | 83.2% |
| `first_third_weekly` | 1,743 | 16.8% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 3,458 | 33.3% |
| `ES.c.0` | 3,458 | 33.3% |
| `YM.c.0` | 3,457 | 33.3% |

### By Side

| Side | Events | Share |
|---|---|---|
| `bullish` | 5,569 | 53.7% |
| `bearish` | 4,720 | 45.5% |
| `doji` | 84 | 0.8% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 10,373 |
| Columns | 94 |
| ed.* event_data | 20 |
| oc.* outcome labels | 52 |
| ctx.* context | 2 |
| xd.* cross-detector | 11 |
| numeric | 66 |
| object/category | 27 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.rest_confirms_first_third` | 5,058 / 10,364 | 48.8% |
| `oc.rest_reverses_first_third` | 5,191 / 10,364 | 50.1% |
| `oc.break_high.wick_breached` | 8,215 / 10,364 | 79.3% |
| `oc.break_low.wick_breached` | 7,468 / 10,364 | 72.1% |

### Breakdown - `oc.rest_confirms_first_third` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `first_third_daily` | 4,183 / 8,621 | 48.5% |
| `first_third_weekly` | 875 / 1,743 | 50.2% |

### Breakdown - `oc.rest_confirms_first_third` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 2,067 / 4,717 | 43.8% |
| `bullish` | 2,991 / 5,563 | 53.8% |
| `doji` | 0 / 84 | 0.0% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.rest_confirms_first_third` | 5,058 / 10,364 | 48.8% |
| `oc.rest_reverses_first_third` | 5,191 / 10,364 | 50.1% |
| `oc.break_high.wick_breached` | 8,215 / 10,364 | 79.3% |
| `oc.break_high.close_past` | 8,076 / 10,364 | 77.9% |
| `oc.break_high_05ext.wick_breached` | 5,999 / 10,364 | 57.9% |
| `oc.break_high_05ext.close_past` | 5,808 / 10,364 | 56.0% |
| `oc.break_high_1ext.wick_breached` | 4,175 / 10,364 | 40.3% |
| `oc.break_high_1ext.close_past` | 4,034 / 10,364 | 38.9% |
| `oc.break_low.wick_breached` | 7,468 / 10,364 | 72.1% |
| `oc.break_low.close_past` | 7,265 / 10,364 | 70.1% |
| `oc.break_low_05ext.wick_breached` | 5,591 / 10,364 | 53.9% |
| `oc.break_low_05ext.close_past` | 5,350 / 10,364 | 51.6% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

| Label | test n | majority | LGB AUC | LGB acc | lift | status | note |
|---|---|---|---|---|---|---|---|
| `oc.break_high.wick_breached` | 1986 | 0.812 | 0.715 | 0.812 | 0.0 | ok |  |
| `oc.break_low.wick_breached` | 1986 | 0.742 | 0.689 | 0.75 | 0.008 | ok |  |
| `oc.rest_confirms_first_third` | 1986 | 0.513 | 0.484 | 0.513 | 0.0 | ok |  |
| `oc.rest_reverses_first_third` | 1986 | 0.494 | 0.473 | 0.487 | -0.007 | ok |  |

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| ft | all | `label.break_high.wick_breached` | 1,986 | 81.2% | 0.724 | 93.0% |  |
| ft | all | `label.break_high.close_past` | 1,986 | 80.0% | 0.701 | 91.5% |  |
| ft | all | `label.break_low.wick_breached` | 1,986 | 74.2% | 0.691 | 92.0% |  |
| ft | all | `label.break_low.close_past` | 1,986 | 72.0% | 0.684 | 89.9% |  |
| ft | all | `label.break_low_1ext.wick_breached` | 1,986 | 41.8% | 0.677 | 55.8% |  |
| ft | all | `label.break_low_05ext.wick_breached` | 1,986 | 56.2% | 0.676 | 78.4% |  |
| ft | bullish | `label.break_low_05ext.wick_breached` | 1,068 | 50.3% | 0.673 | 70.1% |  |
| ft | bullish | `label.break_low_1ext.wick_breached` | 1,068 | 37.8% | 0.671 | 49.5% |  |
| ft | bullish | `label.break_low_05ext.close_past` | 1,068 | 48.2% | 0.668 | 64.5% |  |
| ft | bullish | `label.break_low.wick_breached` | 1,068 | 66.1% | 0.665 | 85.0% |  |

## Reading

Useful context signal, but not top-tier standalone.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/ft.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_FT.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
