# Order Block - Current Stats

_Generated `2026-05-14T04:32:07+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Order-block zones formed after swept references.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `ob` / `order_block` |
| Total feature rows | 46,331 |
| Date range | 2015-01-05 -> 2026-05-08 |
| Outcomes coverage | 46,331 / 46,331 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `swept_pdh_1h` | 5,541 | 12.0% |
| `swept_pdh_4h` | 5,497 | 11.9% |
| `swept_pdl_4h` | 5,008 | 10.8% |
| `swept_pdl_1h` | 4,908 | 10.6% |
| `swept_london_high_1h` | 4,512 | 9.7% |
| `swept_asia_high_1h` | 4,017 | 8.7% |
| `swept_london_low_1h` | 3,739 | 8.1% |
| `swept_ny_high_1h` | 3,626 | 7.8% |
| `swept_asia_low_1h` | 3,332 | 7.2% |
| `swept_ny_low_1h` | 3,108 | 6.7% |
| `swept_pwh_4h` | 917 | 2.0% |
| `swept_pwh_daily` | 856 | 1.8% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v1` | 46,331 | 100.0% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 15,480 | 33.4% |
| `ES.c.0` | 15,458 | 33.4% |
| `YM.c.0` | 15,393 | 33.2% |

### By Side

| Side | Events | Share |
|---|---|---|
| `bearish` | 24,966 | 53.9% |
| `bullish` | 21,365 | 46.1% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 46,331 |
| Columns | 297 |
| ed.* event_data | 38 |
| oc.* outcome labels | 230 |
| ctx.* context | 6 |
| xd.* cross-detector | 14 |
| numeric | 275 |
| object/category | 21 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.invalidation.invalidated` | 37,301 / 46,331 | 80.5% |
| `oc.level_tags.range_far.wick_tapped` | 38,812 / 46,331 | 83.8% |
| `oc.level_tags.open.wick_tapped` | 44,190 / 46,331 | 95.4% |

### Breakdown - `oc.invalidation.invalidated` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `swept_asia_high_1h` | 3,491 / 4,017 | 86.9% |
| `swept_asia_low_1h` | 2,696 / 3,332 | 80.9% |
| `swept_london_high_1h` | 3,645 / 4,512 | 80.8% |
| `swept_london_low_1h` | 2,823 / 3,739 | 75.5% |
| `swept_ny_high_1h` | 2,710 / 3,626 | 74.7% |
| `swept_ny_low_1h` | 2,121 / 3,108 | 68.2% |
| `swept_pdh_1h` | 4,723 / 5,541 | 85.2% |
| `swept_pdh_4h` | 4,836 / 5,497 | 88.0% |
| `swept_pdl_1h` | 3,837 / 4,908 | 78.2% |
| `swept_pdl_4h` | 3,879 / 5,008 | 77.5% |
| `swept_pwh_4h` | 819 / 917 | 89.3% |
| `swept_pwh_daily` | 784 / 856 | 91.6% |
| `swept_pwl_4h` | 494 / 647 | 76.4% |
| `swept_pwl_daily` | 443 / 623 | 71.1% |

### Breakdown - `oc.invalidation.invalidated` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 21,008 / 24,966 | 84.1% |
| `bullish` | 16,293 / 21,365 | 76.3% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.level_tags.open.wick_tapped` | 44,190 / 46,331 | 95.4% |
| `oc.level_tags.open.close_past` | 41,591 / 46,331 | 89.8% |
| `oc.level_tags.q25.wick_tapped` | 43,764 / 46,331 | 94.5% |
| `oc.level_tags.q25.close_past` | 40,831 / 46,331 | 88.1% |
| `oc.level_tags.q50.wick_tapped` | 43,228 / 46,331 | 93.3% |
| `oc.level_tags.q50.close_past` | 39,939 / 46,331 | 86.2% |
| `oc.level_tags.q75.wick_tapped` | 42,453 / 46,331 | 91.6% |
| `oc.level_tags.q75.close_past` | 38,764 / 46,331 | 83.7% |
| `oc.level_tags.close.wick_tapped` | 41,246 / 46,331 | 89.0% |
| `oc.level_tags.close.close_past` | 37,483 / 46,331 | 80.9% |
| `oc.level_tags.range_far.wick_tapped` | 38,812 / 46,331 | 83.8% |
| `oc.level_tags.range_far.close_past` | 35,159 / 46,331 | 75.9% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

| Label | test n | majority | LGB AUC | LGB acc | lift | status | note |
|---|---|---|---|---|---|---|---|
| `oc.level_tags.open.wick_tapped` | 8764 | 0.953 | 0.87 | 0.951 | -0.002 | ok |  |
| `oc.level_tags.close.wick_tapped` | 8764 | 0.892 | 0.731 | 0.893 | 0.001 | ok |  |
| `oc.invalidation.invalidated` | 8764 | 0.808 | 0.664 | 0.811 | 0.003 | ok |  |

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| ob | all | `label.level_tags.open.wick_tapped` | 8,764 | 95.3% | 0.872 | 100.0% | imbalanced base rate |
| ob | bearish | `label.level_tags.open.wick_tapped` | 4,679 | 96.2% | 0.868 | 100.0% | imbalanced base rate |
| ob | bullish | `label.level_tags.open.wick_tapped` | 4,085 | 94.2% | 0.858 | 100.0% | imbalanced base rate |
| ob | bearish | `label.level_tags.q25.wick_tapped` | 4,679 | 95.6% | 0.858 | 99.8% | imbalanced base rate |
| ob | all | `label.level_tags.q25.wick_tapped` | 8,764 | 94.5% | 0.850 | 99.4% | imbalanced base rate |
| ob | bearish | `label.level_tags.q50.wick_tapped` | 4,679 | 94.9% | 0.841 | 100.0% | imbalanced base rate |
| ob | bullish | `label.level_tags.q25.wick_tapped` | 4,085 | 93.2% | 0.830 | 99.5% | imbalanced base rate |
| ob | all | `label.level_tags.q50.wick_tapped` | 8,764 | 93.3% | 0.817 | 99.9% | imbalanced base rate |
| ob | bearish | `label.level_tags.q75.wick_tapped` | 4,679 | 94.0% | 0.808 | 99.8% | imbalanced base rate |
| ob | bullish | `label.level_tags.q50.wick_tapped` | 4,085 | 91.6% | 0.791 | 99.0% | imbalanced base rate |

## Reading

Strong ranking signal, but the best label is very imbalanced. Keep it, but design harder labels.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/ob.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_OB.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
