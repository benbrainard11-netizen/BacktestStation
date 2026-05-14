# FVG Formation - Current Stats

_Generated `2026-05-14T13:40:50+00:00` by `backend/scripts/refresh_dashboards.py`._

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
| `v3` | 209,103 | 99.9% |
| `(missing)` | 236 | 0.1% |

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
| Columns | 169 |
| ed.* event_data | 23 |
| oc.* outcome labels | 119 |
| ctx.* context | 3 |
| xd.* cross-detector | 15 |
| numeric | 150 |
| object/category | 18 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.mitigation.fully_filled` | 171,251 / 209,103 | 81.9% |
| `oc.mitigation.closed_through` | 153,911 / 209,103 | 73.6% |
| `oc.mitigation.tapped` | 186,840 / 209,103 | 89.4% |
| `oc.zone_reaction.took_fvg_high` | 192,590 / 209,103 | 92.1% |
| `oc.zone_reaction.took_fvg_low` | 186,196 / 209,103 | 89.0% |
| `oc.zone_reaction.closed_inside_fvg_range` | 8,432 / 209,103 | 4.0% |
| `oc.zone_reaction.closed_outside_fvg_range` | 200,671 / 209,103 | 96.0% |
| `oc.zone_reaction.took_fvg_high_rejected_inside` | 7,811 / 209,103 | 3.7% |
| `oc.zone_reaction.took_fvg_low_rejected_inside` | 7,968 / 209,103 | 3.8% |

### Breakdown - `oc.mitigation.fully_filled` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `15m_fvg` | 126,130 / 154,228 | 81.8% |
| `1h_fvg` | 32,981 / 40,207 | 82.0% |
| `4h_fvg` | 9,820 / 11,880 | 82.7% |
| `daily_fvg` | 2,320 / 2,788 | 83.2% |

### Breakdown - `oc.mitigation.fully_filled` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 80,022 / 95,917 | 83.4% |
| `bullish` | 91,229 / 113,186 | 80.6% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.mitigation.tapped` | 186,840 / 209,103 | 89.4% |
| `oc.mitigation.mid_filled` | 178,409 / 209,103 | 85.3% |
| `oc.mitigation.fully_filled` | 171,251 / 209,103 | 81.9% |
| `oc.mitigation.closed_inside` | 132,639 / 209,103 | 63.4% |
| `oc.mitigation.closed_through` | 153,911 / 209,103 | 73.6% |
| `oc.zone_reaction.close_above_reference` | 115,331 / 209,103 | 55.2% |
| `oc.zone_reaction.close_below_reference` | 92,973 / 209,103 | 44.5% |
| `oc.zone_reaction.wicked_above_ref_closed_below_ref` | 91,727 / 209,103 | 43.9% |
| `oc.zone_reaction.wicked_below_ref_closed_above_ref` | 113,619 / 209,103 | 54.3% |
| `oc.zone_reaction.first_bar_up_then_final_down` | 41,317 / 209,103 | 19.8% |
| `oc.zone_reaction.first_bar_down_then_final_up` | 49,443 / 209,103 | 23.6% |
| `oc.zone_reaction.direction_reversed_from_first_bar` | 90,760 / 209,103 | 43.4% |

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
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | all | `label.zone_reaction.took_fvg_high` | 41,537 | 91.9% | 0.891 | 99.9% | imbalanced base rate |
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | all | `label.zone_reaction.took_fvg_low` | 41,537 | 89.3% | 0.866 | 99.9% |  |
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | all | `label.zone_reaction.closed_inside_fvg_range` | 41,537 | 3.8% | 0.757 | 13.8% | imbalanced base rate |
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | all | `label.zone_reaction.closed_outside_fvg_range` | 41,537 | 96.2% | 0.757 | 99.6% | imbalanced base rate |
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | bullish | `label.zone_reaction.took_fvg_high_rejected_inside` | 22,791 | 3.6% | 0.751 | 12.2% | imbalanced base rate |
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | bullish | `label.zone_reaction.closed_inside_fvg_range` | 22,791 | 3.6% | 0.751 | 12.3% | imbalanced base rate |
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | bullish | `label.zone_reaction.closed_outside_fvg_range` | 22,791 | 96.4% | 0.751 | 99.4% | imbalanced base rate |
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | bearish | `label.zone_reaction.took_fvg_low_rejected_inside` | 18,746 | 4.1% | 0.750 | 13.8% | imbalanced base rate |
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | bearish | `label.zone_reaction.closed_inside_fvg_range` | 18,746 | 4.1% | 0.749 | 13.3% | imbalanced base rate |
| fvg_snapshot_leaderboard_xctx_fvggeom.parquet | bearish | `label.zone_reaction.closed_outside_fvg_range` | 18,746 | 95.9% | 0.749 | 99.4% | imbalanced base rate |

## Reading

Strong ranking signal, but the best label is very imbalanced. Keep it, but design harder labels.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/fvg.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_FVG_FVGGEOM.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
