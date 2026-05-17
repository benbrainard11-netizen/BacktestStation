# PSP Candle Divergence - Current Stats

_Generated `2026-05-17T22:06:13+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Paired-symbol candle divergence and majority reaction behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `psp` / `psp_candle_divergence` |
| Total feature rows | 77,933 |
| Date range | 2015-01-02 -> 2026-05-07 |
| Outcomes coverage | 77,933 / 77,933 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `15m_psp` | 40,241 | 51.6% |
| `30m_psp` | 21,865 | 28.1% |
| `1h_psp` | 11,641 | 14.9% |
| `4h_psp` | 3,373 | 4.3% |
| `daily_psp` | 813 | 1.0% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v1` | 77,499 | 99.4% |
| `(missing)` | 434 | 0.6% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 37,272 | 47.8% |
| `YM.c.0` | 34,229 | 43.9% |
| `ES.c.0` | 6,432 | 8.3% |

### By Side

| Side | Events | Share |
|---|---|---|
| `bearish` | 39,790 | 51.1% |
| `bullish` | 38,143 | 48.9% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 77,933 |
| Columns | 90 |
| ed.* event_data | 26 |
| oc.* outcome labels | 36 |
| ctx.* context | 3 |
| xd.* cross-detector | 16 |
| numeric | 68 |
| object/category | 21 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.majority_reaction.all_rolled` | 32,114 / 77,499 | 41.4% |

### Breakdown - `oc.majority_reaction.all_rolled` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `15m_psp` | 16,360 / 40,089 | 40.8% |
| `1h_psp` | 4,885 / 11,513 | 42.4% |
| `30m_psp` | 9,060 / 21,716 | 41.7% |
| `4h_psp` | 1,453 / 3,368 | 43.1% |
| `daily_psp` | 356 / 813 | 43.8% |

### Breakdown - `oc.majority_reaction.all_rolled` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 15,602 / 39,570 | 39.4% |
| `bullish` | 16,512 / 37,929 | 43.5% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.majority_reaction.all_rolled` | 32,114 / 77,499 | 41.4% |

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
