# Displacement Candle - Current Stats

_Generated `2026-05-17T22:05:48+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Large directional candles and later retracement/invalidation behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `disp` / `displacement_candle` |
| Total feature rows | 214,599 |
| Date range | 2015-01-02 -> 2026-05-07 |
| Outcomes coverage | 214,599 / 214,599 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `15m_disp` | 113,396 | 52.8% |
| `30m_disp` | 62,456 | 29.1% |
| `1h_disp` | 29,664 | 13.8% |
| `4h_disp` | 7,471 | 3.5% |
| `daily_disp` | 1,612 | 0.8% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v1` | 214,482 | 99.9% |
| `(missing)` | 117 | 0.1% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `YM.c.0` | 71,706 | 33.4% |
| `ES.c.0` | 71,645 | 33.4% |
| `NQ.c.0` | 71,248 | 33.2% |

### By Side

| Side | Events | Share |
|---|---|---|
| `bearish` | 107,538 | 50.1% |
| `bullish` | 107,061 | 49.9% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 214,599 |
| Columns | 93 |
| ed.* event_data | 20 |
| oc.* outcome labels | 45 |
| ctx.* context | 3 |
| xd.* cross-detector | 16 |
| numeric | 82 |
| object/category | 10 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.retracement.tapped_open` | 166,565 / 214,482 | 77.7% |
| `oc.retracement.tapped_full` | 158,597 / 214,482 | 73.9% |
| `oc.invalidation.invalidated` | 147,692 / 214,482 | 68.9% |

### Breakdown - `oc.retracement.tapped_open` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `15m_disp` | 89,289 / 113,282 | 78.8% |
| `1h_disp` | 21,597 / 29,664 | 72.8% |
| `30m_disp` | 48,544 / 62,453 | 77.7% |
| `4h_disp` | 5,845 / 7,471 | 78.2% |
| `daily_disp` | 1,290 / 1,612 | 80.0% |

### Breakdown - `oc.retracement.tapped_open` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 85,525 / 107,482 | 79.6% |
| `bullish` | 81,040 / 107,000 | 75.7% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.retracement.tapped_close` | 213,929 / 214,482 | 99.7% |
| `oc.retracement.tapped_mid` | 189,537 / 214,482 | 88.4% |
| `oc.retracement.tapped_open` | 166,565 / 214,482 | 77.7% |
| `oc.retracement.tapped_full` | 158,597 / 214,482 | 73.9% |
| `oc.invalidation.invalidated` | 147,692 / 214,482 | 68.9% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

| Label | test n | majority | LGB AUC | LGB acc | lift | status | note |
|---|---|---|---|---|---|---|---|
| `oc.retracement.tapped_open` | 7430 | 0.734 | 0.672 | 0.744 | 0.01 | ok |  |
| `oc.retracement.tapped_full` | 7430 | 0.693 | 0.658 | 0.703 | 0.01 | ok |  |
| `oc.invalidation.invalidated` | 7430 | 0.649 | 0.648 | 0.667 | 0.018 | ok |  |

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| disp | bearish | `label.retracement.tapped_open` | 3,714 | 77.2% | 0.681 | 90.9% |  |
| disp | bearish | `label.retracement.tapped_full` | 3,714 | 73.2% | 0.675 | 86.8% |  |
| disp | bearish | `label.retracement.tapped_mid` | 3,714 | 89.0% | 0.673 | 94.6% |  |
| disp | all | `label.retracement.tapped_open` | 7,430 | 73.4% | 0.671 | 89.9% |  |
| disp | bearish | `label.invalidation.invalidated` | 3,714 | 70.1% | 0.665 | 86.3% |  |
| disp | all | `label.retracement.tapped_full` | 7,430 | 69.3% | 0.662 | 86.7% |  |
| disp | all | `label.retracement.tapped_mid` | 7,430 | 86.3% | 0.661 | 95.8% |  |
| disp | all | `label.invalidation.invalidated` | 7,430 | 64.9% | 0.655 | 82.4% |  |
| disp | bullish | `label.retracement.tapped_open` | 3,716 | 69.7% | 0.636 | 83.6% |  |
| disp | bullish | `label.retracement.tapped_mid` | 3,716 | 83.6% | 0.631 | 93.3% |  |

## Reading

Useful context signal, but not top-tier standalone.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/disp.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_DISP.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
