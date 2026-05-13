# Displacement Candle - Current Stats

_Generated `2026-05-12T02:13:47+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Large directional candles and later retracement/invalidation behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `disp` / `displacement_candle` |
| Total feature rows | 38,747 |
| Date range | 2015-01-02 -> 2026-05-07 |
| Outcomes coverage | 38,747 / 38,747 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `1h_disp` | 29,664 | 76.6% |
| `4h_disp` | 7,471 | 19.3% |
| `daily_disp` | 1,612 | 4.2% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 12,953 | 33.4% |
| `YM.c.0` | 12,942 | 33.4% |
| `ES.c.0` | 12,852 | 33.2% |

### By Side

| Side | Events | Share |
|---|---|---|
| `bullish` | 19,391 | 50.0% |
| `bearish` | 19,356 | 50.0% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 38,747 |
| Columns | 88 |
| ed.* event_data | 20 |
| oc.* outcome labels | 45 |
| ctx.* context | 3 |
| xd.* cross-detector | 11 |
| numeric | 77 |
| object/category | 10 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.retracement.tapped_open` | 28,732 / 38,747 | 74.2% |
| `oc.retracement.tapped_full` | 26,990 / 38,747 | 69.7% |
| `oc.invalidation.invalidated` | 25,238 / 38,747 | 65.1% |

### Breakdown - `oc.retracement.tapped_open` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `1h_disp` | 21,597 / 29,664 | 72.8% |
| `4h_disp` | 5,845 / 7,471 | 78.2% |
| `daily_disp` | 1,290 / 1,612 | 80.0% |

### Breakdown - `oc.retracement.tapped_open` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 15,083 / 19,356 | 77.9% |
| `bullish` | 13,649 / 19,391 | 70.4% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.retracement.tapped_close` | 38,655 / 38,747 | 99.8% |
| `oc.retracement.tapped_mid` | 33,550 / 38,747 | 86.6% |
| `oc.retracement.tapped_open` | 28,732 / 38,747 | 74.2% |
| `oc.retracement.tapped_full` | 26,990 / 38,747 | 69.7% |
| `oc.invalidation.invalidated` | 25,238 / 38,747 | 65.1% |

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
