# Scheduled Macro Events - Current Stats

_Generated `2026-05-14T00:23:54+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

Scheduled economic-calendar release anchors and post-release reaction labels.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `macro` / `macro_event_anchor` |
| Total feature rows | 24 |
| Date range | 2026-05-05 -> 2026-05-12 |
| Outcomes coverage | 24 / 24 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `pre_unemployment_rate` | 3 | 12.5% |
| `pre_nfp` | 3 | 12.5% |
| `pre_jolts_job_openings` | 3 | 12.5% |
| `pre_ism_services_pmi` | 3 | 12.5% |
| `pre_cpi_yoy` | 3 | 12.5% |
| `pre_cpi_mom` | 3 | 12.5% |
| `pre_core_cpi_mom` | 3 | 12.5% |
| `pre_average_hourly_earnings_mom` | 3 | 12.5% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `YM.c.0` | 8 | 33.3% |
| `NQ.c.0` | 8 | 33.3% |
| `ES.c.0` | 8 | 33.3% |

### By Side

| Side | Events | Share |
|---|---|---|
| `high` | 24 | 100.0% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 24 |
| Columns | 276 |
| ed.* event_data | 50 |
| oc.* outcome labels | 197 |
| ctx.* context | 5 |
| xd.* cross-detector | 15 |
| numeric | 234 |
| object/category | 41 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.next_5m.range_expanded_2x_pre_15m` | 9 / 24 | 37.5% |
| `oc.next_15m.took_pre_60m_high` | 22 / 24 | 91.7% |
| `oc.next_15m.took_pre_60m_low` | 9 / 24 | 37.5% |
| `oc.next_60m.swept_both_pre_60m_sides` | 18 / 24 | 75.0% |

### Breakdown - `oc.next_5m.range_expanded_2x_pre_15m` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `pre_average_hourly_earnings_mom` | 1 / 3 | 33.3% |
| `pre_core_cpi_mom` | 2 / 3 | 66.7% |
| `pre_cpi_mom` | 2 / 3 | 66.7% |
| `pre_cpi_yoy` | 2 / 3 | 66.7% |
| `pre_ism_services_pmi` | 0 / 3 | 0.0% |
| `pre_jolts_job_openings` | 0 / 3 | 0.0% |
| `pre_nfp` | 1 / 3 | 33.3% |
| `pre_unemployment_rate` | 1 / 3 | 33.3% |

### Breakdown - `oc.next_5m.range_expanded_2x_pre_15m` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `high` | 9 / 24 | 37.5% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.next_1m.n_bars` | 24 / 24 | 100.0% |
| `oc.next_1m.close_above_release_ref` | 14 / 24 | 58.3% |
| `oc.next_1m.close_below_release_ref` | 8 / 24 | 33.3% |
| `oc.next_1m.range_expanded_1x_pre_15m` | 18 / 24 | 75.0% |
| `oc.next_1m.range_expanded_2x_pre_15m` | 9 / 24 | 37.5% |
| `oc.next_1m.took_pre_15m_high` | 17 / 24 | 70.8% |
| `oc.next_1m.took_pre_15m_low` | 8 / 24 | 33.3% |
| `oc.next_1m.swept_both_pre_15m_sides` | 3 / 24 | 12.5% |
| `oc.next_1m.closed_above_pre_15m_high` | 8 / 24 | 33.3% |
| `oc.next_1m.closed_below_pre_15m_low` | 0 / 24 | 0.0% |
| `oc.next_1m.range_expanded_1x_pre_60m` | 15 / 24 | 62.5% |
| `oc.next_1m.range_expanded_2x_pre_60m` | 0 / 24 | 0.0% |

## Per-Detector Baseline

Chronological split from `docs/ML_BASELINE.md`. This is raw detector-matrix screening.

_No baseline rows found in `docs/ML_BASELINE.md`._

## Snapshot Leaderboard

Zero-look-ahead snapshot models. These are safer for ML research than raw detector baselines.

_No snapshot leaderboard artifact found yet._

## Reading

No model leaderboard exists yet.

## Source Artifacts

| Artifact | Path |
|---|---|
| Feature matrix | `data/ml/features/macro.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_MACRO.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
