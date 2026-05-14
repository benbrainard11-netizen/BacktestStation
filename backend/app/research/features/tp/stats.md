# Time Profile - Current Stats

_Generated `2026-05-14T13:41:20+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Parent-period shape and next-period high/low/thesis outcomes.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `tp` / `time_profile` |
| Total feature rows | 19,414 |
| Date range | 2014-12-28 -> 2026-05-07 |
| Outcomes coverage | 19,414 / 19,414 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `daily_4session` | 8,630 | 44.5% |
| `daily_3session` | 8,630 | 44.5% |
| `weekly` | 1,749 | 9.0% |
| `monthly` | 405 | 2.1% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v1` | 19,381 | 99.8% |
| `(missing)` | 33 | 0.2% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 6,472 | 33.3% |
| `ES.c.0` | 6,472 | 33.3% |
| `YM.c.0` | 6,470 | 33.3% |

### By Side

| Side | Events | Share |
|---|---|---|
| `bullish` | 10,711 | 55.2% |
| `bearish` | 8,618 | 44.4% |
| `doji` | 85 | 0.4% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 19,414 |
| Columns | 84 |
| ed.* event_data | 26 |
| oc.* outcome labels | 32 |
| ctx.* context | 3 |
| xd.* cross-detector | 14 |
| numeric | 61 |
| object/category | 22 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.next_period.took_parent_high` | 10,744 / 19,205 | 55.9% |
| `oc.next_period.took_parent_low` | 8,306 / 19,205 | 43.2% |
| `oc.next_period.thesis_confirmed` | 13,169 / 19,205 | 68.6% |

### Breakdown - `oc.next_period.took_parent_high` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `daily_3session` | 4,693 / 8,536 | 55.0% |
| `daily_4session` | 4,693 / 8,536 | 55.0% |
| `monthly` | 290 / 393 | 73.8% |
| `weekly` | 1,068 / 1,740 | 61.4% |

### Breakdown - `oc.next_period.took_parent_high` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 2,915 / 8,531 | 34.2% |
| `bullish` | 7,781 / 10,591 | 73.5% |
| `doji` | 48 / 83 | 57.8% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.next_period.took_parent_high` | 10,744 / 19,205 | 55.9% |
| `oc.next_period.took_parent_low` | 8,306 / 19,205 | 43.2% |
| `oc.next_period.thesis_confirmed` | 13,169 / 19,205 | 68.6% |
| `oc.n_plus_2.took_parent_high` | 1,419 / 2,121 | 66.9% |
| `oc.n_plus_2.took_parent_low` | 781 / 2,121 | 36.8% |
| `oc.n_plus_2.thesis_confirmed` | 1,335 / 2,121 | 62.9% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

| Label | test n | majority | LGB AUC | LGB acc | lift | status | note |
|---|---|---|---|---|---|---|---|
| `oc.next_period.took_parent_high` | 3666 | 0.562 | 0.768 | 0.707 | 0.145 | ok |  |
| `oc.next_period.took_parent_low` | 3666 | 0.565 | 0.741 | 0.676 | 0.111 | ok |  |
| `oc.next_period.thesis_confirmed` | 3666 | 0.672 | 0.662 | 0.679 | 0.007 | ok |  |

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| tp | all | `label.next_period.took_parent_high` | 3,672 | 56.2% | 0.766 | 84.2% |  |
| tp | bullish | `label.next_period.took_parent_low` | 2,000 | 29.9% | 0.740 | 65.0% |  |
| tp | all | `label.next_period.took_parent_low` | 3,672 | 43.4% | 0.739 | 72.3% |  |
| tp | bearish | `label.next_period.took_parent_high` | 1,662 | 35.6% | 0.681 | 58.7% |  |
| tp | bullish | `label.next_period.took_parent_high` | 2,000 | 73.6% | 0.664 | 84.0% |  |
| tp | bullish | `label.next_period.thesis_confirmed` | 2,000 | 73.6% | 0.664 | 84.0% |  |
| tp | all | `label.next_period.thesis_confirmed` | 3,672 | 67.2% | 0.661 | 81.5% |  |
| tp | bearish | `label.next_period.took_parent_low` | 1,662 | 59.6% | 0.638 | 80.8% |  |
| tp | bearish | `label.next_period.thesis_confirmed` | 1,662 | 59.6% | 0.638 | 80.8% |  |
| tp | bearish | `label.n_plus_2.took_parent_high` | 165 | 61.2% | 0.625 | 76.5% |  |

## Reading

Good standalone signal.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/tp.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_TP.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
