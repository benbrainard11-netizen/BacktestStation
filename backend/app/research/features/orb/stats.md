# Opening Range Breakout - Current Stats

_Generated `2026-05-17T22:06:35+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Session opening ranges and later one-sided/two-sided breaks.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `orb` / `opening_range_breakout` |
| Total feature rows | 158,941 |
| Date range | 2015-01-02 -> 2026-05-08 |
| Outcomes coverage | 34,040 / 34,040 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `asia_60m` | 8,618 | 25.3% |
| `ny_5m` | 8,474 | 24.9% |
| `ny_30m` | 8,474 | 24.9% |
| `ny_15m` | 8,474 | 24.9% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v1` | 34,021 | 99.9% |
| `(missing)` | 19 | 0.1% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `ES.c.0` | 11,351 | 33.3% |
| `NQ.c.0` | 11,348 | 33.3% |
| `YM.c.0` | 11,341 | 33.3% |

### By Side

| Side | Events | Share |
|---|---|---|
| `bullish` | 17,253 | 50.7% |
| `bearish` | 16,265 | 47.8% |
| `doji` | 522 | 1.5% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 158,941 |
| Columns | 99 |
| ed.* event_data | 21 |
| oc.* outcome labels | 53 |
| ctx.* context | 2 |
| xd.* cross-detector | 14 |
| numeric | 72 |
| object/category | 26 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.broke_only_high` | 32,604 / 151,336 | 21.5% |
| `oc.broke_only_low` | 32,105 / 151,336 | 21.2% |
| `oc.broke_both_sides` | 85,869 / 151,336 | 56.7% |

### Breakdown - `oc.broke_only_high` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `asia_60m` | 6,157 / 32,471 | 19.0% |
| `ny_15m` | 8,948 / 39,725 | 22.5% |
| `ny_30m` | 11,854 / 41,323 | 28.7% |
| `ny_5m` | 5,645 / 37,817 | 14.9% |

### Breakdown - `oc.broke_only_high` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `bearish` | 9,134 / 71,432 | 12.8% |
| `bullish` | 22,159 / 72,629 | 30.5% |
| `doji` | 1,311 / 7,275 | 18.0% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.break_high.wick_breached` | 118,473 / 151,336 | 78.3% |
| `oc.break_high.close_past` | 114,847 / 151,336 | 75.9% |
| `oc.break_high_05ext.wick_breached` | 95,494 / 151,336 | 63.1% |
| `oc.break_high_05ext.close_past` | 92,273 / 151,336 | 61.0% |
| `oc.break_high_1ext.wick_breached` | 74,783 / 151,336 | 49.4% |
| `oc.break_high_1ext.close_past` | 72,030 / 151,336 | 47.6% |
| `oc.break_low.wick_breached` | 117,974 / 151,336 | 78.0% |
| `oc.break_low.close_past` | 114,421 / 151,336 | 75.6% |
| `oc.break_low_05ext.wick_breached` | 95,032 / 151,336 | 62.8% |
| `oc.break_low_05ext.close_past` | 91,690 / 151,336 | 60.6% |
| `oc.break_low_1ext.wick_breached` | 75,044 / 151,336 | 49.6% |
| `oc.break_low_1ext.close_past` | 72,031 / 151,336 | 47.6% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

| Label | test n | majority | LGB AUC | LGB acc | lift | status | note |
|---|---|---|---|---|---|---|---|
| `oc.break_high.wick_breached` | 6510 | 0.785 | 0.7 | 0.783 | -0.002 | ok |  |
| `oc.break_low.wick_breached` | 6510 | 0.767 | 0.695 | 0.771 | 0.004 | ok |  |
| `oc.broke_both_sides` | 6510 | 0.556 | 0.631 | 0.615 | 0.059 | ok |  |

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| orb | all | `label.broke_only_low` | 6,510 | 21.2% | 0.704 | 43.2% |  |
| orb | all | `label.break_high.wick_breached` | 6,510 | 78.5% | 0.703 | 93.1% |  |
| orb | all | `label.break_low.wick_breached` | 6,510 | 76.7% | 0.699 | 93.1% |  |
| orb | all | `label.broke_only_high` | 6,510 | 23.0% | 0.694 | 45.3% |  |
| orb | all | `label.break_low.close_past` | 6,510 | 73.7% | 0.678 | 86.3% |  |
| orb | all | `label.break_high.close_past` | 6,510 | 76.0% | 0.672 | 87.4% |  |
| orb | all | `label.break_low_1ext.wick_breached` | 6,510 | 44.0% | 0.666 | 70.0% |  |
| orb | all | `label.break_low_1ext.close_past` | 6,510 | 41.4% | 0.660 | 63.0% |  |
| orb | all | `label.break_low_05ext.wick_breached` | 6,510 | 58.5% | 0.653 | 76.5% |  |
| orb | all | `label.break_high_05ext.wick_breached` | 6,510 | 60.1% | 0.652 | 79.7% |  |

## Reading

Useful context signal, but not top-tier standalone.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/orb.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_ORB.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
