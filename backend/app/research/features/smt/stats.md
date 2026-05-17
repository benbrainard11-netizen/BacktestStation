# SMT - HTF Reference Divergence - Current Stats

_Generated `2026-05-17T19:28:53+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

One index takes a higher-timeframe reference high/low while peers do not.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `smt` / `smt_htf_reference_divergence` |
| Total feature rows | 10,889 |
| Date range | 2015-01-08 -> 2026-05-05 |
| Outcomes coverage | 2,891 / 2,891 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `previous_day_smt` | 2,360 | 81.6% |
| `weekly_smt` | 531 | 18.4% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v2` | 2,891 | 100.0% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `ES.c.0` | 1,159 | 40.1% |
| `NQ.c.0` | 983 | 34.0% |
| `YM.c.0` | 749 | 25.9% |

### By Side

| Side | Events | Share |
|---|---|---|
| `high` | 1,525 | 52.7% |
| `low` | 1,366 | 47.3% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 10,889 |
| Columns | 301 |
| ed.* event_data | 224 |
| oc.* outcome labels | 49 |
| ctx.* context | 5 |
| xd.* cross-detector | 14 |
| numeric | 193 |
| object/category | 107 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.next_period.thesis_confirmed_strict` | 5,025 / 10,827 | 46.4% |
| `oc.n_plus_2.thesis_confirmed_strict` | 5,154 / 10,815 | 47.7% |
| `oc.period_close.smt_active_for_side_at_close` | 4,422 / 10,889 | 40.6% |

### Breakdown - `oc.next_period.thesis_confirmed_strict` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `previous_day_smt` | 3,695 / 7,845 | 47.1% |
| `weekly_smt` | 1,330 / 2,982 | 44.6% |

### Breakdown - `oc.next_period.thesis_confirmed_strict` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `high` | 2,506 / 5,598 | 44.8% |
| `low` | 2,519 / 5,229 | 48.2% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.period_close.primary_still_swept_at_close` | 5,593 / 10,889 | 51.4% |
| `oc.period_close.smt_active_for_side_at_close` | 4,422 / 10,889 | 40.6% |
| `oc.next_period.primary_took_period_n_high` | 5,539 / 10,827 | 51.2% |
| `oc.next_period.primary_took_period_n_low` | 5,122 / 10,827 | 47.3% |
| `oc.next_period.thesis_confirmed_strict` | 5,025 / 10,827 | 46.4% |
| `oc.next_period.close_moved_with_thesis` | 5,371 / 10,827 | 49.6% |
| `oc.n_plus_2.primary_took_period_n_high` | 5,599 / 10,815 | 51.8% |
| `oc.n_plus_2.primary_took_period_n_low` | 5,143 / 10,815 | 47.6% |
| `oc.n_plus_2.thesis_confirmed_strict` | 5,154 / 10,815 | 47.7% |
| `oc.n_plus_2.close_moved_with_thesis` | 5,348 / 10,815 | 49.4% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

| Label | test n | majority | LGB AUC | LGB acc | lift | status | note |
|---|---|---|---|---|---|---|---|
| `oc.period_close.smt_active_for_side_at_close` | 644 | 0.671 | 0.819 | 0.818 | 0.147 | ok | suspect within-period target; prefer snapshot labels for strict ML |
| `oc.next_period.primary_took_period_n_high` | 635 | 0.539 | 0.547 | 0.542 | 0.003 | ok |  |
| `oc.next_period.thesis_confirmed_strict` | 635 | 0.537 | 0.533 | 0.535 | -0.002 | ok |  |
| `oc.n_plus_2.thesis_confirmed_strict` | 630 | 0.543 | 0.513 | 0.471 | -0.072 | ok |  |
| `oc.next_period.primary_took_period_n_low` | 635 | 0.553 | 0.507 | 0.551 | -0.002 | ok |  |

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

| Artifact | Side | Label | test n | base | AUC | top bucket | note |
|---|---|---|---|---|---|---|---|
| smt | high | `label.n1_thesis_confirmed_strict` | 277 | 43.3% | 0.910 | 100.0% |  |
| smt | high | `label.n1_primary_took_period_n_low` | 277 | 43.3% | 0.910 | 100.0% |  |
| smt | all | `label.n1_primary_took_period_n_low` | 528 | 45.6% | 0.906 | 98.1% |  |
| smt | all | `label.n1_close_moved_with_thesis` | 528 | 46.8% | 0.900 | 100.0% |  |
| smt | high | `label.n1_primary_took_period_n_high` | 277 | 56.3% | 0.900 | 100.0% |  |
| smt | high | `label.n1_close_moved_with_thesis` | 277 | 43.7% | 0.898 | 96.4% |  |
| smt | all | `label.n1_thesis_confirmed_strict` | 528 | 46.2% | 0.895 | 100.0% |  |
| smt | low | `label.n1_primary_took_period_n_low` | 251 | 48.2% | 0.893 | 96.2% |  |
| smt | all | `label.n1_primary_took_period_n_high` | 528 | 53.0% | 0.889 | 100.0% |  |
| smt | low | `label.n1_close_moved_with_thesis` | 251 | 50.2% | 0.878 | 100.0% |  |

## Reading

Strong standalone signal.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/smt.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_SMT.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
