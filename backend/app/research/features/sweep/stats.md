# Liquidity Sweep - Current Stats

_Generated `2026-05-14T13:40:58+00:00` by `backend/scripts/refresh_dashboards.py`._

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
| Rows | 52,946 |
| Columns | 155 |
| ed.* event_data | 20 |
| oc.* outcome labels | 105 |
| ctx.* context | 6 |
| xd.* cross-detector | 15 |
| numeric | 120 |
| object/category | 34 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.swept_level_recovery.level_recovered` | 38,135 / 52,940 | 72.0% |
| `oc.ob_confirmation.did_confirm` | 51,481 / 52,940 | 97.2% |
| `oc.forward_continuation.continued` | 48,441 / 52,940 | 91.5% |
| `oc.swept_reference_reaction.close_above_reference` | 31,259 / 52,940 | 59.0% |
| `oc.swept_reference_reaction.close_below_reference` | 21,612 / 52,940 | 40.8% |
| `oc.manipulation_range_reaction.took_manipulation_high` | 48,697 / 52,940 | 92.0% |
| `oc.manipulation_range_reaction.took_manipulation_low` | 46,392 / 52,940 | 87.6% |
| `oc.manipulation_range_reaction.closed_inside_manipulation_range` | 4,858 / 52,940 | 9.2% |

### Breakdown - `oc.swept_level_recovery.level_recovered` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `asia_high_1h` | 2,792 / 4,619 | 60.4% |
| `asia_low_1h` | 2,673 / 3,813 | 70.1% |
| `london_high_1h` | 3,243 / 4,972 | 65.2% |
| `london_low_1h` | 2,969 / 4,029 | 73.7% |
| `ny_high_1h` | 3,010 / 4,286 | 70.2% |
| `ny_low_1h` | 2,795 / 3,452 | 81.0% |
| `pdh_1h` | 4,073 / 6,416 | 63.5% |
| `pdh_4h` | 4,632 / 6,417 | 72.2% |
| `pdl_1h` | 4,067 / 5,601 | 72.6% |
| `pdl_4h` | 4,717 / 5,591 | 84.4% |
| `pwh_4h` | 857 / 1,112 | 77.1% |
| `pwh_daily` | 914 / 1,112 | 82.2% |
| `pwl_4h` | 675 / 760 | 88.8% |
| `pwl_daily` | 718 / 760 | 94.5% |

### Breakdown - `oc.swept_level_recovery.level_recovered` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `high` | 19,521 / 28,934 | 67.5% |
| `low` | 18,614 / 24,006 | 77.5% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.swept_level_recovery.level_recovered` | 38,135 / 52,940 | 72.0% |
| `oc.forward_continuation.continued` | 48,441 / 52,940 | 91.5% |
| `oc.ob_confirmation.did_confirm` | 51,481 / 52,940 | 97.2% |
| `oc.swept_reference_reaction.close_above_reference` | 31,259 / 52,940 | 59.0% |
| `oc.swept_reference_reaction.close_below_reference` | 21,612 / 52,940 | 40.8% |
| `oc.swept_reference_reaction.wicked_above_ref_closed_below_ref` | 17,140 / 52,940 | 32.4% |
| `oc.swept_reference_reaction.wicked_below_ref_closed_above_ref` | 23,523 / 52,940 | 44.4% |
| `oc.swept_reference_reaction.first_bar_up_then_final_down` | 8,722 / 52,940 | 16.5% |
| `oc.swept_reference_reaction.first_bar_down_then_final_up` | 10,933 / 52,940 | 20.7% |
| `oc.swept_reference_reaction.direction_reversed_from_first_bar` | 19,655 / 52,940 | 37.1% |
| `oc.manipulation_range_reaction.close_above_reference` | 30,944 / 52,940 | 58.5% |
| `oc.manipulation_range_reaction.close_below_reference` | 21,905 / 52,940 | 41.4% |

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
