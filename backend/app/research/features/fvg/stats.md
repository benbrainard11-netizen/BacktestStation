# FVG Formation - Current Stats

_Generated `2026-05-14T04:31:53+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Fair-value-gap formation and later mitigation behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `fvg` / `fvg_formation` |
| Total feature rows | 209,339 |
| Date range | 2015-01-01 -> 2026-05-08 |
| Outcomes coverage | 209,339 / 209,339 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `15m_fvg` | 154,461 | 73.8% |
| `1h_fvg` | 40,207 | 19.2% |
| `4h_fvg` | 11,883 | 5.7% |
| `daily_fvg` | 2,788 | 1.3% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v2` | 209,098 | 99.9% |
| `(missing)` | 241 | 0.1% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 72,521 | 34.6% |
| `YM.c.0` | 71,895 | 34.3% |
| `ES.c.0` | 64,923 | 31.0% |

### By Side

| Side | Events | Share |
|---|---|---|
| `bullish` | 113,302 | 54.1% |
| `bearish` | 96,037 | 45.9% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 209,339 |
| Columns | 124 |
| ed.* event_data | 23 |
| oc.* outcome labels | 75 |
| ctx.* context | 3 |
| xd.* cross-detector | 14 |
| numeric | 109 |
| object/category | 14 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.mitigation.fully_filled` | 162,331 / 209,098 | 77.6% |
| `oc.mitigation.closed_through` | 142,864 / 209,098 | 68.3% |
| `oc.mitigation.tapped` | 181,157 / 209,098 | 86.6% |

### Breakdown - `oc.mitigation.fully_filled` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `15m_fvg` | 118,013 / 154,228 | 76.5% |
| `1h_fvg` | 32,202 / 40,206 | 80.1% |
| `4h_fvg` | 9,798 / 11,879 | 82.5% |
| `daily_fvg` | 2,318 / 2,785 | 83.2% |

### Breakdown - `oc.mitigation.fully_filled` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 75,730 / 95,917 | 79.0% |
| `bullish` | 86,601 / 113,181 | 76.5% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.mitigation.tapped` | 181,157 / 209,098 | 86.6% |
| `oc.mitigation.mid_filled` | 170,454 / 209,098 | 81.5% |
| `oc.mitigation.fully_filled` | 162,331 / 209,098 | 77.6% |
| `oc.mitigation.closed_inside` | 122,612 / 209,098 | 58.6% |
| `oc.mitigation.closed_through` | 142,864 / 209,098 | 68.3% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

| Label | test n | majority | LGB AUC | LGB acc | lift | status | note |
|---|---|---|---|---|---|---|---|
| `oc.mitigation.fully_filled` | 41532 | 0.777 | 0.77 | 0.805 | 0.028 | ok |  |
| `oc.mitigation.closed_through` | 41532 | 0.688 | 0.748 | 0.742 | 0.054 | ok |  |
| `oc.mitigation.tapped` | 41532 | 0.866 | 0.729 | 0.867 | 0.001 | ok |  |
| `oc.mitigation.closed_inside` | 41532 | 0.559 | 0.708 | 0.658 | 0.099 | ok |  |

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| fvg | all | `label.mitigation.fully_filled` | 41,532 | 77.7% | 0.773 | 93.8% |  |
| fvg | bullish | `label.mitigation.fully_filled` | 22,786 | 77.0% | 0.770 | 93.4% |  |
| fvg | bearish | `label.mitigation.fully_filled` | 18,746 | 78.6% | 0.768 | 93.8% |  |
| fvg | all | `label.mitigation.mid_filled` | 41,532 | 81.4% | 0.755 | 94.6% |  |
| fvg | bullish | `label.mitigation.mid_filled` | 22,786 | 80.7% | 0.751 | 94.2% |  |
| fvg | all | `label.mitigation.closed_through` | 41,532 | 68.8% | 0.749 | 89.4% |  |
| fvg | bearish | `label.mitigation.closed_through` | 18,746 | 70.8% | 0.746 | 88.7% |  |
| fvg | bearish | `label.mitigation.mid_filled` | 18,746 | 82.3% | 0.746 | 94.2% |  |
| fvg | bullish | `label.mitigation.closed_through` | 22,786 | 67.1% | 0.742 | 87.7% |  |
| fvg | bullish | `label.mitigation.tapped` | 22,786 | 86.2% | 0.734 | 96.7% |  |

## Reading

Good standalone signal.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/fvg.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_FVG.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
