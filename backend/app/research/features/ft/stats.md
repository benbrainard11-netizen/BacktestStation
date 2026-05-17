# First-Third Range - Current Stats

_Generated `2026-05-17T19:32:03+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

First-third parent-period range and later break/extension behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `ft` / `first_third_range` |
| Total feature rows | 52,791 |
| Date range | 2015-01-02 -> 2026-05-08 |
| Outcomes coverage | 10,373 / 10,373 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `first_third_daily` | 8,630 | 83.2% |
| `first_third_weekly` | 1,743 | 16.8% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v1` | 10,364 | 99.9% |
| `(missing)` | 9 | 0.1% |

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
| Rows | 52,791 |
| Columns | 97 |
| ed.* event_data | 20 |
| oc.* outcome labels | 52 |
| ctx.* context | 2 |
| xd.* cross-detector | 14 |
| numeric | 69 |
| object/category | 27 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.rest_confirms_first_third` | 25,560 / 52,603 | 48.6% |
| `oc.rest_reverses_first_third` | 25,594 / 52,603 | 48.7% |
| `oc.break_high.wick_breached` | 38,430 / 52,603 | 73.1% |
| `oc.break_low.wick_breached` | 38,031 / 52,603 | 72.3% |

### Breakdown - `oc.rest_confirms_first_third` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `first_third_daily` | 20,841 / 43,073 | 48.4% |
| `first_third_weekly` | 4,719 / 9,530 | 49.5% |

### Breakdown - `oc.rest_confirms_first_third` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 12,438 / 25,268 | 49.2% |
| `bullish` | 13,122 / 26,235 | 50.0% |
| `doji` | 0 / 1,100 | 0.0% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.rest_confirms_first_third` | 25,560 / 52,603 | 48.6% |
| `oc.rest_reverses_first_third` | 25,594 / 52,603 | 48.7% |
| `oc.break_high.wick_breached` | 38,430 / 52,603 | 73.1% |
| `oc.break_high.close_past` | 37,795 / 52,603 | 71.8% |
| `oc.break_high_05ext.wick_breached` | 28,032 / 52,603 | 53.3% |
| `oc.break_high_05ext.close_past` | 27,290 / 52,603 | 51.9% |
| `oc.break_high_1ext.wick_breached` | 19,856 / 52,603 | 37.7% |
| `oc.break_high_1ext.close_past` | 19,276 / 52,603 | 36.6% |
| `oc.break_low.wick_breached` | 38,031 / 52,603 | 72.3% |
| `oc.break_low.close_past` | 37,356 / 52,603 | 71.0% |
| `oc.break_low_05ext.wick_breached` | 27,861 / 52,603 | 53.0% |
| `oc.break_low_05ext.close_past` | 27,055 / 52,603 | 51.4% |

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
