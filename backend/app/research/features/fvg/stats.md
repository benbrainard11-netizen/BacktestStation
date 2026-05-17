# FVG Formation - Current Stats

_Generated `2026-05-17T22:05:12+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Fair-value-gap formation and later mitigation behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `fvg` / `fvg_formation` |
| Total feature rows | 1,243,757 |
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
| Rows | 1,243,757 |
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
| `oc.mitigation.fully_filled` | 1,007,051 / 1,240,341 | 81.2% |
| `oc.mitigation.closed_through` | 920,368 / 1,240,341 | 74.2% |
| `oc.mitigation.tapped` | 1,121,810 / 1,240,341 | 90.4% |

### Breakdown - `oc.mitigation.fully_filled` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `15m_fvg` | 725,438 / 895,394 | 81.0% |
| `1h_fvg` | 205,954 / 253,191 | 81.3% |
| `4h_fvg` | 62,535 / 76,007 | 82.3% |
| `daily_fvg` | 13,124 / 15,749 | 83.3% |

### Breakdown - `oc.mitigation.fully_filled` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 496,369 / 611,432 | 81.2% |
| `bullish` | 510,682 / 628,909 | 81.2% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.mitigation.tapped` | 1,121,810 / 1,240,341 | 90.4% |
| `oc.mitigation.mid_filled` | 1,057,500 / 1,240,341 | 85.3% |
| `oc.mitigation.fully_filled` | 1,007,051 / 1,240,341 | 81.2% |
| `oc.mitigation.closed_inside` | 875,392 / 1,240,341 | 70.6% |
| `oc.mitigation.closed_through` | 920,368 / 1,240,341 | 74.2% |

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
