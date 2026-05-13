# PSP Candle Divergence - Current Stats

_Generated `2026-05-12T02:14:04+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Paired-symbol candle divergence and majority reaction behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `psp` / `psp_candle_divergence` |
| Total feature rows | 15,827 |
| Date range | 2015-01-02 -> 2026-05-07 |
| Outcomes coverage | 15,827 / 15,827 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `1h_psp` | 11,641 | 73.6% |
| `4h_psp` | 3,373 | 21.3% |
| `daily_psp` | 813 | 5.1% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 7,542 | 47.7% |
| `YM.c.0` | 7,011 | 44.3% |
| `ES.c.0` | 1,274 | 8.0% |

### By Side

| Side | Events | Share |
|---|---|---|
| `bearish` | 8,116 | 51.3% |
| `bullish` | 7,711 | 48.7% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 15,827 |
| Columns | 85 |
| ed.* event_data | 26 |
| oc.* outcome labels | 36 |
| ctx.* context | 3 |
| xd.* cross-detector | 11 |
| numeric | 63 |
| object/category | 21 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.majority_reaction.all_rolled` | 6,694 / 15,694 | 42.7% |

### Breakdown - `oc.majority_reaction.all_rolled` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `1h_psp` | 4,885 / 11,513 | 42.4% |
| `4h_psp` | 1,453 / 3,368 | 43.1% |
| `daily_psp` | 356 / 813 | 43.8% |

### Breakdown - `oc.majority_reaction.all_rolled` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 3,160 / 8,053 | 39.2% |
| `bullish` | 3,534 / 7,641 | 46.3% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.majority_reaction.all_rolled` | 6,694 / 15,694 | 42.7% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

| Label | test n | majority | LGB AUC | LGB acc | lift | status | note |
|---|---|---|---|---|---|---|---|
| `oc.next_candle.relative_to_minority` | — | — | — | — | — | skip_non_bool |  |

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| psp | bullish | `label.majority_reaction.all_rolled` | 1,891 | 43.4% | 0.514 | 46.3% |  |
| psp | bearish | `label.majority_reaction.all_rolled` | 1,958 | 39.9% | 0.500 | 43.9% |  |
| psp | all | `label.majority_reaction.all_rolled` | 3,849 | 41.6% | 0.493 | 40.3% |  |

## Reading

Weak signal in the current label setup.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/psp.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_PSP.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
