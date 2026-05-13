# Liquidity Sweep - Current Stats

_Generated `2026-05-12T02:13:43+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Reference high/low sweeps and later recovery/confirmation behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `sweep` / `liquidity_sweep` |
| Total feature rows | 52,946 |
| Date range | 2015-01-04 -> 2026-05-08 |
| Outcomes coverage | 52,946 / 52,946 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `pdh_4h` | 6,417 | 12.1% |
| `pdh_1h` | 6,416 | 12.1% |
| `pdl_1h` | 5,604 | 10.6% |
| `pdl_4h` | 5,591 | 10.6% |
| `london_high_1h` | 4,972 | 9.4% |
| `asia_high_1h` | 4,619 | 8.7% |
| `ny_high_1h` | 4,286 | 8.1% |
| `london_low_1h` | 4,029 | 7.6% |
| `asia_low_1h` | 3,816 | 7.2% |
| `ny_low_1h` | 3,452 | 6.5% |
| `pwh_daily` | 1,112 | 2.1% |
| `pwh_4h` | 1,112 | 2.1% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 17,673 | 33.4% |
| `ES.c.0` | 17,654 | 33.3% |
| `YM.c.0` | 17,619 | 33.3% |

### By Side

| Side | Events | Share |
|---|---|---|
| `high` | 28,934 | 54.6% |
| `low` | 24,012 | 45.4% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 52,946 |
| Columns | 83 |
| ed.* event_data | 20 |
| oc.* outcome labels | 37 |
| ctx.* context | 6 |
| xd.* cross-detector | 11 |
| numeric | 56 |
| object/category | 26 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.swept_level_recovery.level_recovered` | 37,349 / 52,940 | 70.5% |
| `oc.ob_confirmation.did_confirm` | 51,008 / 52,940 | 96.4% |
| `oc.forward_continuation.continued` | 48,109 / 52,940 | 90.9% |

### Breakdown - `oc.swept_level_recovery.level_recovered` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `asia_high_1h` | 2,707 / 4,619 | 58.6% |
| `asia_low_1h` | 2,597 / 3,813 | 68.1% |
| `london_high_1h` | 3,141 / 4,972 | 63.2% |
| `london_low_1h` | 2,863 / 4,029 | 71.1% |
| `ny_high_1h` | 2,902 / 4,286 | 67.7% |
| `ny_low_1h` | 2,711 / 3,452 | 78.5% |
| `pdh_1h` | 3,967 / 6,416 | 61.8% |
| `pdh_4h` | 4,620 / 6,417 | 72.0% |
| `pdl_1h` | 3,964 / 5,601 | 70.8% |
| `pdl_4h` | 4,713 / 5,591 | 84.3% |
| `pwh_4h` | 857 / 1,112 | 77.1% |
| `pwh_daily` | 914 / 1,112 | 82.2% |
| `pwl_4h` | 675 / 760 | 88.8% |
| `pwl_daily` | 718 / 760 | 94.5% |

### Breakdown - `oc.swept_level_recovery.level_recovered` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `high` | 19,108 / 28,934 | 66.0% |
| `low` | 18,241 / 24,006 | 76.0% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.swept_level_recovery.level_recovered` | 37,349 / 52,940 | 70.5% |
| `oc.forward_continuation.continued` | 48,109 / 52,940 | 90.9% |
| `oc.ob_confirmation.did_confirm` | 51,008 / 52,940 | 96.4% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

| Label | test n | majority | LGB AUC | LGB acc | lift | status | note |
|---|---|---|---|---|---|---|---|
| `oc.ob_confirmation.did_confirm` | 10146 | 0.958 | 0.865 | 0.96 | 0.002 | ok |  |
| `oc.swept_level_recovery.level_recovered` | 10146 | 0.705 | 0.796 | 0.765 | 0.06 | ok |  |
| `oc.forward_continuation.continued` | 10146 | 0.911 | 0.629 | 0.911 | 0.0 | ok |  |

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| sweep | low | `label.ob_confirmation.did_confirm` | 4,646 | 96.7% | 0.888 | 100.0% | high base rate |
| sweep | all | `label.ob_confirmation.did_confirm` | 10,146 | 95.8% | 0.864 | 99.5% | high base rate |
| sweep | high | `label.ob_confirmation.did_confirm` | 5,500 | 95.1% | 0.839 | 100.0% | high base rate |
| sweep | low | `label.swept_level_recovery.level_recovered` | 4,646 | 76.5% | 0.797 | 96.8% |  |
| sweep | high | `label.swept_level_recovery.level_recovered` | 5,500 | 65.3% | 0.794 | 93.5% |  |
| sweep | all | `label.swept_level_recovery.level_recovered` | 10,146 | 70.5% | 0.790 | 94.4% |  |
| sweep | high | `label.forward_continuation.continued` | 5,500 | 93.9% | 0.673 | 98.7% | high base rate |
| sweep | all | `label.forward_continuation.continued` | 10,146 | 91.1% | 0.628 | 96.2% | high base rate |
| sweep | low | `label.forward_continuation.continued` | 4,646 | 87.9% | 0.598 | 89.0% |  |

## Reading

Strong ranking signal, but the best label is very imbalanced. Keep it, but design harder labels.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/sweep.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_SWEEP.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
