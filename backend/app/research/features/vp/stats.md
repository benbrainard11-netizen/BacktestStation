# Volume Profile - Current Stats

_Generated `2026-05-17T22:06:54+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Profile levels, VWAP bands, and forward touch/close behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `vp` / `volume_profile` |
| Total feature rows | 183,662 |
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
| Rows | 183,662 |
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
| `oc.took_period_high` | 106,419 / 173,798 | 61.2% |
| `oc.took_period_low` | 103,729 / 173,798 | 59.7% |
| `oc.forward_close_in_value_area` | 24 / 173,798 | 0.0% |
| `oc.forward_close_above_vah` | 102,914 / 173,798 | 59.2% |
| `oc.forward_close_below_val` | 102,344 / 173,798 | 58.9% |

### Breakdown - `oc.took_period_high` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `asia_volume_profile` | 31,228 / 40,940 | 76.3% |
| `daily_volume_profile` | 22,211 / 45,228 | 49.1% |
| `london_volume_profile` | 26,813 / 43,013 | 62.3% |
| `ny_volume_profile` | 21,318 / 35,057 | 60.8% |
| `weekly_volume_profile` | 4,849 / 9,560 | 50.7% |

### Breakdown - `oc.took_period_high` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `balanced` | 53,476 / 84,969 | 62.9% |
| `buying` | 31,081 / 45,344 | 68.5% |
| `selling` | 21,862 / 43,485 | 50.3% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.poc_touch.wicked_into` | 133,422 / 173,798 | 76.8% |
| `oc.poc_touch.wicked_above` | 154,195 / 173,798 | 88.7% |
| `oc.poc_touch.wicked_below` | 153,025 / 173,798 | 88.0% |
| `oc.poc_touch.closed_above` | 152,439 / 173,798 | 87.7% |
| `oc.poc_touch.closed_below` | 151,275 / 173,798 | 87.0% |
| `oc.poc_touch.first_touch_from_above` | 59,899 / 173,798 | 34.5% |
| `oc.poc_touch.first_touch_from_below` | 58,630 / 173,798 | 33.7% |
| `oc.poc_touch.held_above_3bar_after_touch` | 34,039 / 173,798 | 19.6% |
| `oc.poc_touch.held_below_3bar_after_touch` | 33,855 / 173,798 | 19.5% |
| `oc.poc_touch.accepted_above_3bar` | 147,170 / 173,798 | 84.7% |
| `oc.poc_touch.accepted_below_3bar` | 145,849 / 173,798 | 83.9% |
| `oc.poc_touch.support_rejection_3bar` | 15,866 / 173,798 | 9.1% |

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
