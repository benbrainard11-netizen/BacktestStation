# Volume Profile - Current Stats

_Generated `2026-05-14T13:41:26+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Profile levels, VWAP bands, and forward touch/close behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `vp` / `volume_profile` |
| Total feature rows | 36,095 |
| Date range | 2014-12-28 -> 2026-05-08 |
| Outcomes coverage | 36,095 / 36,095 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `daily_volume_profile` | 8,630 | 23.9% |
| `asia_volume_profile` | 8,630 | 23.9% |
| `london_volume_profile` | 8,615 | 23.9% |
| `ny_volume_profile` | 8,471 | 23.5% |
| `weekly_volume_profile` | 1,749 | 4.8% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v2` | 34,356 | 95.2% |
| `(missing)` | 1,739 | 4.8% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 12,033 | 33.3% |
| `ES.c.0` | 12,033 | 33.3% |
| `YM.c.0` | 12,029 | 33.3% |

### By Side

| Side | Events | Share |
|---|---|---|
| `balanced` | 19,533 | 54.1% |
| `buying` | 9,718 | 26.9% |
| `selling` | 6,844 | 19.0% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 36,095 |
| Columns | 212 |
| ed.* event_data | 42 |
| oc.* outcome labels | 144 |
| ctx.* context | 3 |
| xd.* cross-detector | 14 |
| numeric | 197 |
| object/category | 14 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.took_period_high` | 23,127 / 34,356 | 67.3% |
| `oc.took_period_low` | 20,162 / 34,356 | 58.7% |
| `oc.forward_close_in_value_area` | 0 / 34,356 | 0.0% |
| `oc.forward_close_above_vah` | 22,092 / 34,356 | 64.3% |
| `oc.forward_close_below_val` | 18,288 / 34,356 | 53.2% |

### Breakdown - `oc.took_period_high` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `asia_volume_profile` | 7,047 / 8,624 | 81.7% |
| `daily_volume_profile` | 4,695 / 8,539 | 55.0% |
| `london_volume_profile` | 6,133 / 8,474 | 72.4% |
| `ny_volume_profile` | 4,182 / 6,976 | 59.9% |
| `weekly_volume_profile` | 1,070 / 1,743 | 61.4% |

### Breakdown - `oc.took_period_high` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `balanced` | 12,840 / 18,637 | 68.9% |
| `buying` | 6,760 / 9,222 | 73.3% |
| `selling` | 3,527 / 6,497 | 54.3% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.poc_touch.wicked_into` | 27,674 / 34,356 | 80.6% |
| `oc.poc_touch.wicked_above` | 31,735 / 34,356 | 92.4% |
| `oc.poc_touch.wicked_below` | 30,295 / 34,356 | 88.2% |
| `oc.poc_touch.closed_above` | 31,312 / 34,356 | 91.1% |
| `oc.poc_touch.closed_below` | 29,757 / 34,356 | 86.6% |
| `oc.poc_touch.first_touch_from_above` | 14,774 / 34,356 | 43.0% |
| `oc.poc_touch.first_touch_from_below` | 12,862 / 34,356 | 37.4% |
| `oc.poc_touch.held_above_3bar_after_touch` | 8,204 / 34,356 | 23.9% |
| `oc.poc_touch.held_below_3bar_after_touch` | 8,133 / 34,356 | 23.7% |
| `oc.poc_touch.accepted_above_3bar` | 30,821 / 34,356 | 89.7% |
| `oc.poc_touch.accepted_below_3bar` | 29,037 / 34,356 | 84.5% |
| `oc.poc_touch.support_rejection_3bar` | 4,462 / 34,356 | 13.0% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

| Label | test n | majority | LGB AUC | LGB acc | lift | status | note |
|---|---|---|---|---|---|---|---|
| `oc.took_period_high` | 6543 | 0.683 | 0.802 | 0.763 | 0.08 | ok |  |
| `oc.took_period_low` | 6543 | 0.601 | 0.786 | 0.732 | 0.131 | ok |  |
| `oc.forward_close_in_value_area` | — | — | — | — | — | class_imbalance |  |

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| vp | buying | `label.vwap_1sd_low_touch.wicked_above` | 1,803 | 98.2% | 0.961 | 100.0% | imbalanced base rate |
| vp | buying | `label.vah_touch.wicked_above` | 1,803 | 97.2% | 0.946 | 100.0% | imbalanced base rate |
| vp | buying | `label.vwap_1sd_low_touch.closed_above` | 1,803 | 97.9% | 0.945 | 100.0% | imbalanced base rate |
| vp | buying | `label.vwap_touch.wicked_above` | 1,803 | 94.8% | 0.940 | 100.0% | imbalanced base rate |
| vp | selling | `label.val_touch.wicked_below` | 1,133 | 92.7% | 0.937 | 100.0% | imbalanced base rate |
| vp | all | `label.vah_touch.wicked_above` | 6,546 | 97.6% | 0.937 | 100.0% | imbalanced base rate |
| vp | all | `label.vwap_1sd_low_touch.wicked_above` | 6,546 | 97.8% | 0.935 | 100.0% | imbalanced base rate |
| vp | balanced | `label.vwap_1sd_low_touch.wicked_above` | 3,610 | 97.6% | 0.932 | 100.0% | imbalanced base rate |
| vp | buying | `label.vah_touch.closed_above` | 1,803 | 96.7% | 0.930 | 100.0% | imbalanced base rate |
| vp | selling | `label.vwap_1sd_high_touch.wicked_below` | 1,133 | 94.4% | 0.928 | 100.0% | imbalanced base rate |

## Reading

Strong ranking signal, but the best label is very imbalanced. Keep it, but design harder labels.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/vp.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_VP.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
