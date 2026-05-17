# Opening Gap Levels - Current Stats

_Generated `2026-05-17T22:07:02+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

NDOG/NWOG gap zones, fill state, and support/resistance reaction behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `ogap` / `opening_gap_levels` |
| Total feature rows | 36,944 |
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
| Rows | 36,944 |
| Columns | 210 |
| ed.* event_data | 18 |
| oc.* outcome labels | 166 |
| ctx.* context | 3 |
| xd.* cross-detector | 14 |
| numeric | 151 |
| object/category | 58 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.next_60m.fully_filled` | 22,300 / 36,944 | 60.4% |
| `oc.next_240m.fully_filled` | 27,563 / 36,944 | 74.6% |
| `oc.next_1d.fully_filled` | 33,121 / 36,944 | 89.7% |

### Breakdown - `oc.next_60m.fully_filled` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `ndog` | 19,389 / 30,257 | 64.1% |
| `nwog` | 2,911 / 6,687 | 43.5% |

### Breakdown - `oc.next_60m.fully_filled` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `gap_down` | 10,920 / 18,074 | 60.4% |
| `gap_up` | 11,380 / 18,870 | 60.3% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.full_horizon.touched_gap` | 36,944 / 36,944 | 100.0% |
| `oc.full_horizon.touched_midpoint` | 34,484 / 36,944 | 93.3% |
| `oc.full_horizon.fully_filled` | 35,925 / 36,944 | 97.2% |
| `oc.full_horizon.closed_inside` | 36,489 / 36,944 | 98.8% |
| `oc.full_horizon.closed_through` | 35,805 / 36,944 | 96.9% |
| `oc.full_horizon.accepted_above_3bar` | 35,803 / 36,944 | 96.9% |
| `oc.full_horizon.accepted_below_3bar` | 35,624 / 36,944 | 96.4% |
| `oc.full_horizon.support_rejection_3bar` | 12,209 / 36,944 | 33.0% |
| `oc.full_horizon.resistance_rejection_3bar` | 11,487 / 36,944 | 31.1% |
| `oc.full_horizon.support_break_acceptance_3bar` | 1,947 / 36,944 | 5.3% |
| `oc.full_horizon.resistance_break_acceptance_3bar` | 1,888 / 36,944 | 5.1% |
| `oc.full_horizon.first_touch_minutes` | 0 / 36,944 | 0.0% |

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
