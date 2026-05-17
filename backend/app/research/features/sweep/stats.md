# Liquidity Sweep - Current Stats

_Generated `2026-05-17T22:05:31+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Reference high/low sweeps and later recovery/confirmation behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `sweep` / `liquidity_sweep` |
| Total feature rows | 237,569 |
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

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v2` | 52,940 | 100.0% |
| `(missing)` | 6 | 0.0% |

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
| Rows | 237,569 |
| Columns | 82 |
| ed.* event_data | 20 |
| oc.* outcome labels | 33 |
| ctx.* context | 6 |
| xd.* cross-detector | 14 |
| numeric | 58 |
| object/category | 23 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.swept_level_recovery.level_recovered` | 183,993 / 237,546 | 77.5% |
| `oc.ob_confirmation.did_confirm` | 0 / 237,546 | 0.0% |
| `oc.forward_continuation.continued` | 213,800 / 237,546 | 90.0% |

### Breakdown - `oc.swept_level_recovery.level_recovered` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `asia_high_1h` | 13,481 / 21,219 | 63.5% |
| `asia_low_1h` | 13,548 / 20,730 | 65.4% |
| `london_high_1h` | 16,489 / 23,113 | 71.3% |
| `london_low_1h` | 16,324 / 22,574 | 72.3% |
| `ny_high_1h` | 15,598 / 21,486 | 72.6% |
| `ny_low_1h` | 14,936 / 20,569 | 72.6% |
| `pdh_1h` | 19,357 / 22,730 | 85.2% |
| `pdh_4h` | 19,850 / 22,751 | 87.2% |
| `pdl_1h` | 18,627 / 21,876 | 85.1% |
| `pdl_4h` | 19,302 / 21,819 | 88.5% |
| `pwh_4h` | 4,178 / 4,835 | 86.4% |
| `pwh_daily` | 4,293 / 4,835 | 88.8% |
| `pwl_4h` | 3,962 / 4,505 | 87.9% |
| `pwl_daily` | 4,048 / 4,504 | 89.9% |

### Breakdown - `oc.swept_level_recovery.level_recovered` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `high` | 93,246 / 120,969 | 77.1% |
| `low` | 90,747 / 116,577 | 77.8% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.swept_level_recovery.level_recovered` | 183,993 / 237,546 | 77.5% |
| `oc.forward_continuation.continued` | 213,800 / 237,546 | 90.0% |
| `oc.ob_confirmation.did_confirm` | 0 / 237,546 | 0.0% |

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
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | low | `label.ob_confirmation.did_confirm` | 4,646 | 96.7% | 0.894 | 100.0% | imbalanced base rate |
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | all | `label.ob_confirmation.did_confirm` | 10,146 | 96.8% | 0.875 | 99.7% | imbalanced base rate |
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | high | `label.ob_confirmation.did_confirm` | 5,500 | 96.9% | 0.852 | 100.0% | imbalanced base rate |
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | low | `label.swept_level_recovery.level_recovered` | 4,646 | 78.2% | 0.793 | 96.1% |  |
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | high | `label.swept_level_recovery.level_recovered` | 5,500 | 66.7% | 0.792 | 92.2% |  |
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | all | `label.swept_level_recovery.level_recovered` | 10,146 | 72.0% | 0.790 | 95.0% |  |
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | all | `label.manipulation_range_reaction.took_manipulation_high` | 10,146 | 92.6% | 0.737 | 96.6% | imbalanced base rate |
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | low | `label.manipulation_range_reaction.took_manipulation_high` | 4,646 | 90.1% | 0.735 | 97.4% | imbalanced base rate |
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | low | `label.manipulation_range_reaction.one_sided_took_manipulation_low` | 4,646 | 9.9% | 0.732 | 32.7% | imbalanced base rate |
| sweep_snapshot_leaderboard_xctx_fvggeom.parquet | all | `label.manipulation_range_reaction.one_sided_took_manipulation_low` | 10,146 | 7.4% | 0.731 | 24.3% | imbalanced base rate |

## Reading

Strong ranking signal, but the best label is very imbalanced. Keep it, but design harder labels.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/sweep.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_SWEEP_FVGGEOM.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
