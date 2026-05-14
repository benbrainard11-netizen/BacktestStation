# ITR - Interval True Range - Current Stats

_Generated `2026-05-14T13:41:33+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Completed daily, weekly, and session range memory for next-interval behavior.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `itr` / `interval_true_range` |
| Total feature rows | 36,095 |
| Date range | 2015-01-02 -> 2026-05-08 |
| Outcomes coverage | 36,095 / 36,095 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `daily_itr` | 8,630 | 23.9% |
| `asia_itr` | 8,630 | 23.9% |
| `london_itr` | 8,615 | 23.9% |
| `ny_itr` | 8,471 | 23.5% |
| `weekly_itr` | 1,749 | 4.8% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v2` | 35,572 | 98.6% |
| `(missing)` | 523 | 1.4% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `NQ.c.0` | 12,033 | 33.3% |
| `ES.c.0` | 12,033 | 33.3% |
| `YM.c.0` | 12,029 | 33.3% |

### By Side

| Side | Events | Share |
|---|---|---|
| `bullish` | 19,487 | 54.0% |
| `bearish` | 16,376 | 45.4% |
| `doji` | 232 | 0.6% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 36,095 |
| Columns | 172 |
| ed.* event_data | 78 |
| oc.* outcome labels | 66 |
| ctx.* context | 4 |
| xd.* cross-detector | 15 |
| numeric | 151 |
| object/category | 20 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.next_interval.compressed_range_0_75x` | 10,689 / 35,572 | 30.0% |
| `oc.next_interval.expanded_range_1_25x` | 11,695 / 35,572 | 32.9% |
| `oc.next_interval.range_expanded_1x_interval` | 17,523 / 35,572 | 49.3% |
| `oc.next_interval.range_expanded_2x_interval` | 3,597 / 35,572 | 10.1% |
| `oc.next_interval.touched_interval_mid` | 15,241 / 35,572 | 42.8% |
| `oc.next_interval.took_interval_high` | 19,543 / 35,572 | 54.9% |
| `oc.next_interval.took_interval_low` | 15,658 / 35,572 | 44.0% |
| `oc.next_interval.swept_both_sides` | 2,876 / 35,572 | 8.1% |
| `oc.next_interval.took_interval_high_rejected_inside` | 5,237 / 35,572 | 14.7% |
| `oc.next_interval.took_interval_low_rejected_inside` | 5,341 / 35,572 | 15.0% |
| `oc.next_interval.closed_inside_interval_range` | 12,638 / 35,572 | 35.5% |

### Breakdown - `oc.next_interval.compressed_range_0_75x` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `asia_itr` | 2,575 / 8,539 | 30.2% |
| `daily_itr` | 2,573 / 8,539 | 30.1% |
| `london_itr` | 2,590 / 8,521 | 30.4% |
| `ny_itr` | 2,470 / 8,230 | 30.0% |
| `weekly_itr` | 481 / 1,743 | 27.6% |

### Breakdown - `oc.next_interval.compressed_range_0_75x` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 4,551 / 16,129 | 28.2% |
| `bullish` | 6,107 / 19,216 | 31.8% |
| `doji` | 31 / 227 | 13.7% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.next_interval.expanded_range_1_25x` | 11,695 / 35,572 | 32.9% |
| `oc.next_interval.compressed_range_0_75x` | 10,689 / 35,572 | 30.0% |
| `oc.next_interval.took_interval_high` | 19,543 / 35,572 | 54.9% |
| `oc.next_interval.took_interval_low` | 15,658 / 35,572 | 44.0% |
| `oc.next_interval.touched_interval_mid` | 15,241 / 35,572 | 42.8% |
| `oc.next_interval.closed_above_interval_high` | 13,440 / 35,572 | 37.8% |
| `oc.next_interval.closed_below_interval_low` | 9,494 / 35,572 | 26.7% |
| `oc.next_interval.closed_inside_interval` | 12,638 / 35,572 | 35.5% |
| `oc.next_interval.outside_continuation_up` | 12,617 / 35,572 | 35.5% |
| `oc.next_interval.outside_continuation_down` | 8,628 / 35,572 | 24.3% |
| `oc.next_interval.swept_both_sides` | 2,876 / 35,572 | 8.1% |
| `oc.next_interval.same_direction_close` | 17,355 / 35,572 | 48.8% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

_No baseline rows found in `docs/ML_BASELINE.md`._

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| itr | bullish | `label.next_interval.range_expanded_2x_interval` | 3,640 | 10.6% | 0.818 | 40.9% |  |
| itr | bullish | `label.next_interval.compressed_range_0_75x` | 3,640 | 32.4% | 0.804 | 79.4% |  |
| itr | all | `label.next_interval.compressed_range_0_75x` | 6,801 | 31.2% | 0.803 | 78.9% |  |
| itr | all | `label.next_interval.range_expanded_2x_interval` | 6,801 | 11.1% | 0.797 | 41.0% |  |
| itr | bullish | `label.next_interval.range_expanded_1x_interval` | 3,640 | 47.3% | 0.796 | 86.3% |  |
| itr | bullish | `label.next_interval.expanded_range_1_25x` | 3,640 | 32.3% | 0.787 | 78.3% |  |
| itr | bearish | `label.next_interval.compressed_range_0_75x` | 3,137 | 29.9% | 0.786 | 72.3% |  |
| itr | all | `label.next_interval.range_expanded_1x_interval` | 6,801 | 48.7% | 0.785 | 86.6% |  |
| itr | all | `label.next_interval.expanded_range_1_25x` | 6,801 | 33.4% | 0.775 | 76.4% |  |
| itr | bearish | `label.next_interval.range_expanded_1x_interval` | 3,137 | 50.2% | 0.764 | 84.4% |  |

## Reading

Good standalone signal.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/itr.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_ITR_XCTX.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
