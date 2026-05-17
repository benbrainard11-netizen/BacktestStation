# Order Block - Current Stats

_Generated `2026-05-17T22:06:07+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Order-block zones formed after swept references.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `ob` / `order_block` |
| Total feature rows | 198,069 |
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
| Rows | 198,069 |
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
| `oc.invalidation.invalidated` | 159,835 / 198,063 | 80.7% |
| `oc.level_tags.range_far.wick_tapped` | 165,701 / 198,063 | 83.7% |
| `oc.level_tags.open.wick_tapped` | 187,811 / 198,063 | 94.8% |

### Breakdown - `oc.invalidation.invalidated` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `swept_asia_high_1h` | 14,848 / 17,596 | 84.4% |
| `swept_asia_low_1h` | 14,229 / 17,250 | 82.5% |
| `swept_london_high_1h` | 15,345 / 19,170 | 80.0% |
| `swept_london_low_1h` | 14,685 / 18,697 | 78.5% |
| `swept_ny_high_1h` | 13,921 / 18,076 | 77.0% |
| `swept_ny_low_1h` | 13,282 / 17,479 | 76.0% |
| `swept_pdh_1h` | 15,133 / 18,508 | 81.8% |
| `swept_pdh_4h` | 16,059 / 19,236 | 83.5% |
| `swept_pdl_1h` | 14,242 / 17,832 | 79.9% |
| `swept_pdl_4h` | 15,147 / 18,572 | 81.6% |
| `swept_pwh_4h` | 3,494 / 4,158 | 84.0% |
| `swept_pwh_daily` | 3,292 / 3,898 | 84.5% |
| `swept_pwl_4h` | 3,145 / 3,901 | 80.6% |
| `swept_pwl_daily` | 3,013 / 3,690 | 81.7% |

### Breakdown - `oc.invalidation.invalidated` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 82,092 / 100,642 | 81.6% |
| `bullish` | 77,743 / 97,421 | 79.8% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.level_tags.open.wick_tapped` | 187,811 / 198,063 | 94.8% |
| `oc.level_tags.open.close_past` | 179,010 / 198,063 | 90.4% |
| `oc.level_tags.q25.wick_tapped` | 185,729 / 198,063 | 93.8% |
| `oc.level_tags.q25.close_past` | 175,570 / 198,063 | 88.6% |
| `oc.level_tags.q50.wick_tapped` | 183,471 / 198,063 | 92.6% |
| `oc.level_tags.q50.close_past` | 172,073 / 198,063 | 86.9% |
| `oc.level_tags.q75.wick_tapped` | 179,898 / 198,063 | 90.8% |
| `oc.level_tags.q75.close_past` | 167,028 / 198,063 | 84.3% |
| `oc.level_tags.close.wick_tapped` | 175,107 / 198,063 | 88.4% |
| `oc.level_tags.close.close_past` | 161,565 / 198,063 | 81.6% |
| `oc.level_tags.range_far.wick_tapped` | 165,701 / 198,063 | 83.7% |
| `oc.level_tags.range_far.close_past` | 152,657 / 198,063 | 77.1% |

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
| ob_snapshot_leaderboard_strict_context.parquet | bullish | `label.strict.next_60m.ob_swept_and_recovered` | 4,085 | 5.5% | 0.811 | 21.3% | imbalanced base rate |
| ob_snapshot_leaderboard_strict_context.parquet | all | `label.strict.next_60m.ob_broken_through_continuation` | 8,764 | 19.5% | 0.803 | 57.1% |  |
| ob_snapshot_leaderboard_strict_context.parquet | bearish | `label.strict.next_60m.ob_broken_through_continuation` | 4,679 | 20.6% | 0.803 | 59.8% |  |
| ob_snapshot_leaderboard_strict_context.parquet | bullish | `label.strict.next_60m.ob_broken_through_continuation` | 4,085 | 18.2% | 0.792 | 55.7% |  |
| ob_snapshot_leaderboard_strict_context.parquet | all | `label.strict.next_60m.ob_swept_and_recovered` | 8,764 | 5.4% | 0.790 | 18.7% | imbalanced base rate |
| ob_snapshot_leaderboard_strict_context.parquet | bearish | `label.strict.next_240m.ob_broken_through_continuation` | 4,679 | 39.6% | 0.776 | 75.6% |  |
| ob_snapshot_leaderboard_strict_context.parquet | all | `label.strict.next_240m.ob_broken_through_continuation` | 8,764 | 38.3% | 0.776 | 77.7% |  |
| ob_snapshot_leaderboard_strict_context.parquet | all | `label.strict.next_60m.ob_failed_immediately` | 8,764 | 31.9% | 0.771 | 66.5% |  |
| ob_snapshot_leaderboard_strict_context.parquet | bullish | `label.strict.next_240m.ob_broken_through_continuation` | 4,085 | 36.7% | 0.770 | 77.0% |  |
| ob_snapshot_leaderboard_strict_context.parquet | all | `label.strict.next_240m.ob_failed_immediately` | 8,764 | 32.1% | 0.770 | 65.8% |  |

## Reading

Good standalone signal.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/ob.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_OB_STRICT_CONTEXT.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
