# Displacement Candle - Current Stats

_Generated `2026-05-17T19:31:25+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Large directional candles and later retracement/invalidation behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `disp` / `displacement_candle` |
| Total feature rows | 187,595 |
| Date range | 2015-01-02 -> 2026-05-07 |
| Outcomes coverage | 38,747 / 38,747 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `1h_disp` | 29,664 | 76.6% |
| `4h_disp` | 7,471 | 19.3% |
| `daily_disp` | 1,612 | 4.2% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v1` | 38,747 | 100.0% |

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
| Rows | 187,595 |
| Columns | 91 |
| ed.* event_data | 20 |
| oc.* outcome labels | 45 |
| ctx.* context | 3 |
| xd.* cross-detector | 14 |
| numeric | 80 |
| object/category | 10 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.retracement.tapped_open` | 144,236 / 187,563 | 76.9% |
| `oc.retracement.tapped_full` | 138,010 / 187,563 | 73.6% |
| `oc.invalidation.invalidated` | 128,698 / 187,563 | 68.6% |

### Breakdown - `oc.retracement.tapped_open` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `1h_disp` | 107,465 / 140,575 | 76.4% |
| `4h_disp` | 30,453 / 38,911 | 78.3% |
| `daily_disp` | 6,318 / 8,077 | 78.2% |

### Breakdown - `oc.retracement.tapped_open` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 73,214 / 94,513 | 77.5% |
| `bullish` | 71,022 / 93,050 | 76.3% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.retracement.tapped_close` | 185,312 / 187,563 | 98.8% |
| `oc.retracement.tapped_mid` | 164,493 / 187,563 | 87.7% |
| `oc.retracement.tapped_open` | 144,236 / 187,563 | 76.9% |
| `oc.retracement.tapped_full` | 138,010 / 187,563 | 73.6% |
| `oc.invalidation.invalidated` | 128,698 / 187,563 | 68.6% |

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
