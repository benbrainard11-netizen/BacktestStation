# SMT - Previous-Candle MTF Divergence - Current Stats

_Generated `2026-05-17T22:02:50+00:00` by `backend/scripts/refresh_dashboards.py`._

> Generated file. Edit the stable concept explanation in `README.md`; rerun the script for numbers.

## What This Is

One symbol sweeps its own previous candle high/low while peers do not, tracked from 15m through 6h.

## Event Counts

| Metric | Value |
|---|---|
| Feature key | `smt_mtf` / `smt_prev_candle_divergence` |
| Total feature rows | 244,615 |
| Date range | 2015-01-01 -> 2026-05-08 |
| Outcomes coverage | 244,615 / 244,615 (100.0%) |

### By Event Type

| Event type | Events | Share |
|---|---|---|
| `15m_prev_candle_smt_high` | 63,774 | 26.1% |
| `15m_prev_candle_smt_low` | 59,796 | 24.4% |
| `30m_prev_candle_smt_high` | 30,957 | 12.7% |
| `30m_prev_candle_smt_low` | 28,810 | 11.8% |
| `1h_prev_candle_smt_high` | 15,178 | 6.2% |
| `1h_prev_candle_smt_low` | 13,826 | 5.7% |
| `90m_prev_candle_smt_high` | 10,243 | 4.2% |
| `90m_prev_candle_smt_low` | 9,436 | 3.9% |
| `4h_prev_candle_smt_high` | 3,943 | 1.6% |
| `4h_prev_candle_smt_low` | 3,623 | 1.5% |
| `6h_prev_candle_smt_high` | 2,630 | 1.1% |
| `6h_prev_candle_smt_low` | 2,399 | 1.0% |

### By Outcome Version

| Outcome version | Events | Share |
|---|---|---|
| `v1` | 243,052 | 99.4% |
| `(missing)` | 1,563 | 0.6% |

### By Symbol

| Symbol | Events | Share |
|---|---|---|
| `ES.c.0` | 107,495 | 43.9% |
| `NQ.c.0` | 81,855 | 33.5% |
| `YM.c.0` | 55,265 | 22.6% |

### By Side

| Side | Events | Share |
|---|---|---|
| `high` | 126,725 | 51.8% |
| `low` | 117,890 | 48.2% |

## Feature Matrix

| Metric | Value |
|---|---|
| Rows | 244,615 |
| Columns | 190 |
| ed.* event_data | 62 |
| oc.* outcome labels | 99 |
| ctx.* context | 4 |
| xd.* cross-detector | 16 |
| numeric | 161 |
| object/category | 28 |

## Primary Labels

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.next_15m.thesis_confirmed` | 98,093 / 237,610 | 41.3% |
| `oc.next_30m.thesis_confirmed` | 121,933 / 238,408 | 51.1% |
| `oc.next_60m.thesis_confirmed` | 146,144 / 238,889 | 61.2% |
| `oc.next_240m.thesis_confirmed` | 189,163 / 242,787 | 77.9% |
| `oc.next_1d.thesis_confirmed` | 218,637 / 243,048 | 90.0% |

### Breakdown - `oc.next_15m.thesis_confirmed` by event type

| event_type | Wins / Total | Hit rate |
|---|---|---|
| `15m_prev_candle_smt_high` | 30,612 / 62,364 | 49.1% |
| `15m_prev_candle_smt_low` | 30,039 / 58,515 | 51.3% |
| `1h_prev_candle_smt_high` | 4,098 / 14,556 | 28.2% |
| `1h_prev_candle_smt_low` | 4,059 / 13,308 | 30.5% |
| `30m_prev_candle_smt_high` | 11,400 / 30,118 | 37.9% |
| `30m_prev_candle_smt_low` | 11,430 / 28,116 | 40.7% |
| `4h_prev_candle_smt_high` | 533 / 3,822 | 13.9% |
| `4h_prev_candle_smt_low` | 576 / 3,526 | 16.3% |
| `6h_prev_candle_smt_high` | 262 / 2,477 | 10.6% |
| `6h_prev_candle_smt_low` | 285 / 2,278 | 12.5% |
| `90m_prev_candle_smt_high` | 2,287 / 9,613 | 23.8% |
| `90m_prev_candle_smt_low` | 2,512 / 8,917 | 28.2% |

### Breakdown - `oc.next_15m.thesis_confirmed` by side

| side | Wins / Total | Hit rate |
|---|---|---|
| `high` | 49,192 / 122,950 | 40.0% |
| `low` | 48,901 / 114,660 | 42.6% |

## Binary Label Hit Rates

| Label | Wins / Total | Hit rate |
|---|---|---|
| `oc.close_confirmed_at_close` | 77,872 / 243,052 | 32.0% |
| `oc.primary_close_confirmed` | 56,294 / 243,052 | 23.2% |
| `oc.next_1d.thesis_confirmed` | 218,637 / 243,048 | 90.0% |
| `oc.next_1d.close_moved_with_thesis` | 120,272 / 243,048 | 49.5% |
| `oc.next_1d.took_current_candle_high` | 220,899 / 243,048 | 90.9% |
| `oc.next_1d.took_current_candle_low` | 214,144 / 243,048 | 88.1% |
| `oc.next_1d.swept_both_current_candle_sides` | 193,206 / 243,048 | 79.5% |
| `oc.next_1d.closed_above_current_candle_high` | 120,650 / 243,048 | 49.6% |
| `oc.next_1d.closed_below_current_candle_low` | 97,514 / 243,048 | 40.1% |
| `oc.next_1d.closed_inside_current_candle_range` | 24,884 / 243,048 | 10.2% |
| `oc.next_240m.thesis_confirmed` | 189,163 / 242,787 | 77.9% |
| `oc.next_240m.close_moved_with_thesis` | 119,585 / 242,787 | 49.3% |

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
| Feature matrix | `data/ml/features/smt_mtf.parquet` |
| Model summary | `docs/ML_SNAPSHOT_LEADERBOARD_SMT_MTF.md` |
| Dataset catalog | `docs/ML_DATASET_CATALOG.md` |
