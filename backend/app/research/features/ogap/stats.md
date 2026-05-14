# Opening Gap Levels - Current Stats

_Generated `2026-05-14T13:41:30+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

NDOG/NWOG gap zones, fill state, and support/resistance reaction behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `ogap` / `opening_gap_levels` |
| Total feature rows | 9,438 |
| Date range | 2015-01-04 -> 2026-05-07 |
| Outcomes coverage | 9,438 / 9,438 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `ndog` | 7,815 | 82.8% |
| `nwog` | 1,623 | 17.2% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v2` | 9,438 | 100.0% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 3,230 | 34.2% |
| `YM.c.0` | 3,173 | 33.6% |
| `ES.c.0` | 3,035 | 32.2% |

### By Side

| Side | Events | Share |
|---|---|---|
| `gap_down` | 4,873 | 51.6% |
| `gap_up` | 4,565 | 48.4% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 9,438 |
| Columns | 487 |
| ed.* event_data | 18 |
| oc.* outcome labels | 442 |
| ctx.* context | 3 |
| xd.* cross-detector | 15 |
| numeric | 416 |
| object/category | 70 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.next_60m.fully_filled` | 6,279 / 9,438 | 66.5% |
| `oc.next_240m.fully_filled` | 7,258 / 9,438 | 76.9% |
| `oc.next_1d.fully_filled` | 8,565 / 9,438 | 90.8% |
| `oc.next_60m.unfilled_at_window_end` | 3,159 / 9,438 | 33.5% |
| `oc.next_240m.unfilled_at_window_end` | 2,180 / 9,438 | 23.1% |
| `oc.next_240m.closed_inside_gap_range` | 1,080 / 9,438 | 11.4% |
| `oc.next_60m.took_gap_high_rejected_inside` | 1,254 / 9,438 | 13.3% |
| `oc.next_60m.took_gap_low_rejected_inside` | 1,385 / 9,438 | 14.7% |

### Breakdown - `oc.next_60m.fully_filled` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `ndog` | 5,559 / 7,815 | 71.1% |
| `nwog` | 720 / 1,623 | 44.4% |

### Breakdown - `oc.next_60m.fully_filled` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `gap_down` | 3,222 / 4,873 | 66.1% |
| `gap_up` | 3,057 / 4,565 | 67.0% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.full_horizon.touched_gap` | 9,438 / 9,438 | 100.0% |
| `oc.full_horizon.touched_midpoint` | 9,311 / 9,438 | 98.7% |
| `oc.full_horizon.fully_filled` | 9,192 / 9,438 | 97.4% |
| `oc.full_horizon.unfilled_at_window_end` | 246 / 9,438 | 2.6% |
| `oc.full_horizon.closed_inside` | 9,294 / 9,438 | 98.5% |
| `oc.full_horizon.closed_through` | 9,164 / 9,438 | 97.1% |
| `oc.full_horizon.accepted_above_3bar` | 9,320 / 9,438 | 98.7% |
| `oc.full_horizon.accepted_below_3bar` | 9,080 / 9,438 | 96.2% |
| `oc.full_horizon.support_rejection_3bar` | 2,953 / 9,438 | 31.3% |
| `oc.full_horizon.resistance_rejection_3bar` | 3,283 / 9,438 | 34.8% |
| `oc.full_horizon.support_break_acceptance_3bar` | 717 / 9,438 | 7.6% |
| `oc.full_horizon.resistance_break_acceptance_3bar` | 732 / 9,438 | 7.8% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

_No baseline rows found in `docs/ML_BASELINE.md`._

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| opening_gap | gap_up | `label.next_240m.unfilled_at_window_end` | 1,032 | 27.3% | 0.850 | 90.4% |  |
| opening_gap | gap_up | `label.next_240m.fully_filled` | 1,032 | 72.7% | 0.850 | 94.2% |  |
| opening_gap | all | `label.next_1d.fully_filled` | 1,854 | 90.2% | 0.849 | 98.9% | imbalanced base rate |
| opening_gap | gap_up | `label.next_60m.unfilled_at_window_end` | 1,032 | 37.1% | 0.849 | 97.1% |  |
| opening_gap | gap_up | `label.next_60m.fully_filled` | 1,032 | 62.9% | 0.849 | 95.2% |  |
| opening_gap | all | `label.next_240m.unfilled_at_window_end` | 1,854 | 23.7% | 0.841 | 81.2% |  |
| opening_gap | all | `label.next_240m.fully_filled` | 1,854 | 76.3% | 0.841 | 95.7% |  |
| opening_gap | gap_down | `label.next_240m.unfilled_at_window_end` | 822 | 19.1% | 0.836 | 66.3% |  |
| opening_gap | gap_down | `label.next_240m.fully_filled` | 822 | 80.9% | 0.836 | 96.4% |  |
| opening_gap | all | `label.next_60m.unfilled_at_window_end` | 1,854 | 32.7% | 0.831 | 89.2% |  |

## Reading

Strong standalone signal.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/ogap.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_OPENING_GAP_XCTX_GAPCTX.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
