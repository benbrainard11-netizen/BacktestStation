# Research Events Dictionary

> **Status: canonical.** Single reference for navigating the BacktestStation research warehouse. If you're an ML researcher, an LLM agent, or someone building a strategy on top of this data — start here.

This doc covers the **research events** layer: 4.4M+ detector fires across 15 detectors, 22+ symbols, 11 years of futures history. For raw bar storage + file layout, see [`DATA_FORMAT.md`](./DATA_FORMAT.md). For per-column field types and nullability, see [`SCHEMA_SPEC.md`](./SCHEMA_SPEC.md).

## TL;DR — what's in the warehouse

| Layer | Where | What |
|---|---|---|
| **Raw bars** | `D:/data/processed/bars/timeframe=1m/symbol=*/date=*/part-*.parquet` | 1m OHLCV for 22+ symbols, 2015–present |
| **Research events** | `data/meta.sqlite` → `research_events` table | 4.39M detector fires with event metadata + outcomes |
| **Backtests** | `data/meta.sqlite` → `backtest_runs` + parquet equity/trades | Per-run results, reproducible |

A "research event" = ONE moment in time where a detector fired, with full context: what was detected, the bars around it, and the forward-looking R-multiple outcome.

## The `research_events` table

```sql
CREATE TABLE research_events (
  id                  INTEGER PRIMARY KEY,
  event_id            VARCHAR(80),       -- stable unique id (idempotent re-runs)
  feature_name        VARCHAR(80),       -- one of the 15 detector names below
  event_type          VARCHAR(60),       -- detector-specific variant (see grid)
  bar_end_utc         DATETIME,          -- the bar that triggered the detection
  primary_symbol      VARCHAR(40),       -- e.g. "NQ.c.0"
  symbols             JSON,              -- list (for multi-symbol detections like SMT)
  timeframe           VARCHAR(20),       -- HTF the detector was watching (1H, 4H, 15M, etc.)
  side                VARCHAR(20),       -- detector-specific (bullish/bearish, high/low, etc.)
  event_data          JSON,              -- detector-specific "what was detected"
  context             JSON,              -- nearby bars / parent period info
  outcomes            JSON,              -- forward-looking results (R-multiple, hits, etc.)
  replay_pointer      JSON,              -- how to load this exact moment back from parquet
  source_dataset      TEXT,              -- dataset snapshot id
  source_run_id       INTEGER,           -- which detector run produced this
  detector_version    VARCHAR(40),       -- "v1", "v2", etc — see Versioning section
  knowledge_card_id   INTEGER,           -- link to research_entries (if any)
  created_at          DATETIME
);
```

Key idea: **the `feature_name` + `event_type` + `timeframe` combo identifies a SPECIFIC PATTERN VARIANT.** The other columns describe when/where/what happened and what came after.

## ⚠️ Session-mode disambiguation (read this before using session events)

The mode names use a compact convention that's easy to misread. Here's exactly what each means:

| Mode name | Reads as | Actually means |
|---|---|---|
| `swept_pdh_1h` | "swept previous day high, 1h timeframe" | Today's bar swept the **prior globex day's** high (24h+ ago) |
| `swept_pwh_4h` | "swept previous week high, 4h timeframe" | This week's bar swept the **prior globex week's** high (7d+ ago) |
| `swept_asia_high_1h` | "swept asia high, 1h timeframe" | Today's asia session swept **yesterday's asia high** (24h ago, SAME session) |
| `swept_london_high_1h` | "swept london high" | Today's london swept **yesterday's london** high |
| `swept_ny_high_1h` | "swept ny high" | Today's ny swept **yesterday's ny** high |

**The session modes refer to the SAME session 24h ago, not the most-recently-closed session of today.** This is v20's convention. If you want "today's NY swept today's london high" (a chained intraday view), that's a DIFFERENT signal and isn't currently in the warehouse — it would need a new detector run with new mode names.

Source of truth: `backend/app/research/sessions.py::previous_session()`.

## The 15 detectors

Counts as of 2026-05-19. Per-symbol distribution is roughly uniform (NQ ~280k, YM ~270k, ES ~270k, others scale by liquidity).

### 1. `order_block` (208,885 events, 14 variants)

The v20 family. Detects sweep + opposite-close OB candle + confirmation close.

| event_type | timeframe | side | count |
|---|---|---|---:|
| swept_pdh_1h / swept_pdl_1h | 1H | bearish/bullish | ~38k |
| swept_pdh_4h / swept_pdl_4h | 4H | bearish/bullish | ~40k |
| swept_pwh_4h / swept_pwl_4h | 4H | bearish/bullish | ~8.5k |
| swept_pwh_daily / swept_pwl_daily | 1D | bearish/bullish | ~8k |
| swept_asia_high_1h / swept_asia_low_1h | 1H | bearish/bullish | ~37k |
| swept_london_high_1h / swept_london_low_1h | 1H | bearish/bullish | ~40k |
| swept_ny_high_1h / swept_ny_low_1h | 1H | bearish/bullish | ~37k |

**Note**: only 1H/4H/1D tracking timeframes. To add 15m/30m, see Gap 4 in `tradebot/ROADMAP_NOTES.md` (pending).

### 2. `liquidity_sweep` (249,774 events, 14 variants)

Same 14 modes as order_block, but fires on the SWEEP alone (no OB + confirmation requirement). Higher event count, lower per-event signal quality. Used REVERSED in v20 (sweep of high → LONG signal).

### 3. `fvg_formation` (1,296,636 events, 8 variants)

Fair Value Gap detection — 3-candle pattern with an unfilled gap.

| event_type | timeframe | count |
|---|---|---:|
| 15m_fvg | 15M | 937k |
| 1h_fvg | 1H | 264k |
| 4h_fvg | 4H | 79k |
| daily_fvg | 1D | 16k |

Sides: bullish/bearish. Outcomes track mitigation (was the gap tapped/filled).

### 4. `forming_volume_profile` (1,195,635 events, 6 variants)

Daily volume profile snapshotted at intermediate timestamps (1h / 4h marks).

| event_type | timeframe | side | count |
|---|---|---|---:|
| daily_vp_asof_1h | ASOF_1H | balanced/buying/selling | 971k |
| daily_vp_asof_4h | ASOF_4H | balanced/buying/selling | 225k |

Used for "is the day's profile shaping up bullish or bearish at this snapshot point?"

### 5. `swing_pivot` (366,123 events, 10 variants)

N-bar swing highs/lows (pivot_3 = 3 bars on each side, pivot_5 = 5).

| event_type | timeframe | count |
|---|---|---:|
| pivot_3_1h / pivot_5_1h | 1H | 271k |
| pivot_3_4h / pivot_5_4h | 4H | 87k |
| pivot_5_daily | 1D | 6.7k |

Sides: high/low.

### 6. `displacement_candle` (198,287 events, 6 variants)

Large-body candles relative to recent average — momentum signals.

| event_type | timeframe | count |
|---|---|---:|
| 1h_disp | 1H | 149k |
| 4h_disp | 4H | 41k |
| daily_disp | 1D | 8.5k |

Sides: bullish/bearish.

### 7. `opening_range_breakout` (168,121 events, 12 variants)

Opening-range break of N-minute window after session open.

| event_type | timeframe | count |
|---|---|---:|
| ny_5m / ny_15m / ny_30m | 5M / 15M / 30M | ~40k each |
| asia_60m | 60M | 36k |

Sides: bullish/bearish/doji.

### 8. `interval_true_range` (199,912 events, 15 variants)

ATR-style range measurement over distinct intervals.

| event_type | timeframe | count |
|---|---|---:|
| daily_itr | 1D | 49k |
| asia_itr / london_itr / ny_itr | session | ~47k each |
| weekly_itr | 1W | 10k |

Sides: bullish/bearish/doji.

### 9. `volume_profile` (193,391 events, 15 variants)

Completed volume profiles per period.

| event_type | timeframe | count |
|---|---|---:|
| daily_volume_profile | 1D | 48k |
| asia_volume_profile / london_volume_profile / ny_volume_profile | ASIA/LONDON/NY | ~45k each |
| weekly_volume_profile | 1W | 10k |

Sides: balanced/buying/selling.

### 10. `time_profile` (111,054 events, 12 variants)

Time-of-day session structure (3-session vs 4-session segmentations).

| event_type | timeframe | count |
|---|---|---:|
| daily_3session / daily_4session | 1D | 49k each |
| weekly | 1W | 10k |
| monthly | 1MO | 2.3k |

Sides: bullish/bearish/doji.

### 11. `psp_candle_divergence` (76,714 events, 6 variants)

Power-of-3 / candle divergence between correlated symbols.

| event_type | timeframe | count |
|---|---|---:|
| 1h_psp | 1H | 53k |
| 4h_psp | 4H | 18.5k |
| daily_psp | 1D | 4.8k |

Sides: bullish/bearish.

### 12. `first_third_range` (55,587 events, 6 variants)

First 1/3 of period range — early indicator of period direction.

| event_type | timeframe | count |
|---|---|---:|
| first_third_daily | 1D | 45k |
| first_third_weekly | 1W | 10k |

Sides: bullish/bearish/doji.

### 13. `opening_gap_levels` (39,424 events, 4 variants)

New daily / weekly opening gaps (NDOG / NWOG).

| event_type | timeframe | count |
|---|---|---:|
| ndog | 1D_GAP | 32k |
| nwog | 1W_GAP | 7k |

Sides: gap_up/gap_down.

### 14. `equal_levels` (22,595 events, 14 variants)

Repeated highs/lows at the same price (within 5pts or 15pts tolerance).

| event_type | timeframe | count |
|---|---|---:|
| eq_pivot_3_1h_15pts / eq_pivot_3_1h_5pts | LEVEL | ~12k |
| eq_pivot_5_1h_15pts / eq_pivot_5_1h_5pts | LEVEL | ~7.5k |
| ...4h / daily variants | LEVEL | ~3.5k |

Sides: high/low.

### 15. `smt_htf_reference_divergence` (11,630 events, 4 variants)

Smart-money-technique divergence between correlated symbols (NQ vs ES, etc.).

| event_type | timeframe | count |
|---|---|---:|
| previous_day_smt | 1H | 8.5k |
| weekly_smt | 4H | 3.1k |

Sides: high/low.

## The JSON columns

Each event carries three JSON blobs. All schemas live in `backend/app/schemas/research_events.py` and are versioned.

### `event_data` — what was detected

Shape varies by detector. Always includes:
- `schema_version` (int)
- `detector_version` (string, e.g. "v1")
- `tracking_timeframe` (string)
- Detector-specific fields (mode, prices, candle context)

Example (`order_block` event_data):
```json
{
  "schema_version": 1,
  "detector_version": "v1",
  "mode": "swept_pdl_1h",
  "direction": "bullish",
  "tracking_timeframe": "1h",
  "swept_reference": {
    "type": "pdl",
    "level_price": 6595.5,
    "level_set_ts_utc": "2018-04-30T16:17:00+00:00",
    "prior_period_label": "globex_day",
    "prior_period_start_utc": "2018-04-29T22:00:00+00:00",
    "prior_period_end_utc": "2018-04-30T21:00:00+00:00"
  },
  "manipulation_candle": {...},
  "ob_candle": {...},
  "confirmation_candle": {...}
}
```

### `outcomes` — what happened after

The R-multiple research data. Schema varies by detector but always includes:
- `outcome_version` (int, distinct from detector_version)
- `thesis_direction` ("up" or "down")
- `reference_close` (price at event time, baseline for R math)

Per-detector outcome fields:
- **order_block / liquidity_sweep**: `forward_continuation` (continued? bars to extreme? max favorable excursion?), `swept_level_recovery`, `ob_levels`
- **fvg_formation**: `mitigation` (tapped, mid_filled, fully_filled), `forward_window_max/min`
- **swing_pivot**: `breakout` (wick_taken, close_taken, bars_to_break), `extreme` (max favorable excursion)
- **volume_profile / forming_volume_profile**: `forward_window_*` price stats

### `context` — surrounding bars

Always includes:
- `bars_before` / `bars_after` arrays of (ts, OHLCV) tuples
- `parent_period` info (which globex day / week this event lives in)

Used for replay and feature engineering.

### `replay_pointer` — load me back

JSON pointer for fetching the exact bars used to produce this event from parquet. Lets you re-run analysis on the underlying data without re-running the detector.

## Versioning

The `detector_version` column lets you distinguish events produced by different detector generations. Convention:

- `"v1"` — original detector logic
- `"v2"` — significant rule change (e.g. boundary semantics, threshold tuning)

When changing a detector's logic, bump `detector_version` and re-run on history. Old events keep their `"v1"` tag; queries can filter `WHERE detector_version = 'v2'` to use only the new generation.

The `event_data.schema_version` and `outcomes.outcome_version` track shape changes within a detector_version.

## Query examples

### Find all NQ order-block events with positive forward continuation

```python
import sqlite3, json, pandas as pd
con = sqlite3.connect("data/meta.sqlite")
df = pd.read_sql("""
    SELECT event_id, bar_end_utc, event_type, side,
           json_extract(outcomes, '$.forward_continuation.max_favorable_pts') AS mfe_pts
    FROM research_events
    WHERE feature_name = 'order_block' AND primary_symbol = 'NQ.c.0'
    AND json_extract(outcomes, '$.forward_continuation.continued') = 1
""", con)
print(df.head())
```

### Group by mode and compute hit rate

```python
df = pd.read_sql("""
    SELECT event_type, side, COUNT(*) AS total,
           SUM(json_extract(outcomes, '$.forward_continuation.continued')) AS hits
    FROM research_events
    WHERE feature_name = 'order_block' AND primary_symbol = 'NQ.c.0'
    GROUP BY event_type, side
""", con)
df['hit_rate'] = df['hits'] / df['total']
print(df.sort_values('hit_rate', ascending=False))
```

### Load underlying bars for one event via replay_pointer

```python
import duckdb
event = con.execute("""
    SELECT primary_symbol, bar_end_utc, replay_pointer
    FROM research_events WHERE event_id = ?
""", ("evt_abc123",)).fetchone()

# replay_pointer typically contains start/end timestamps + parquet glob
ptr = json.loads(event[2])
duckdb_query = f"""
    SELECT * FROM read_parquet('D:/data/processed/bars/timeframe=1m/symbol={event[0]}/date=*/part-*.parquet')
    WHERE ts_event BETWEEN '{ptr['start_utc']}' AND '{ptr['end_utc']}'
"""
bars = duckdb.query(duckdb_query).to_df()
```

## Adding a new detector

1. Create `backend/app/research/detectors/your_detector.py` with class implementing `scan(ctx) → list[ResearchEventCreate]`
2. Register in `_DETECTOR_REGISTRY`
3. Add JSON schemas to `backend/app/schemas/research_events.py` for your event_data + outcomes
4. Run `python -m backend.scripts.generate_events --feature your_detector --symbols NQ.c.0 --start 2018-01-01 --end 2018-12-31` to populate
5. Add a section to THIS doc describing your detector + variants
6. If you change rules later: bump `detector_version`, re-run, document the diff

## Files this doc references

- `backend/app/research/detectors/*.py` — each detector
- `backend/app/research/sessions.py` — globex day/week + session boundary math
- `backend/app/schemas/research_events.py` — pydantic schemas for event_data/outcomes/context
- `backend/app/data/schema.py` — SCHEMA_VERSION + table DDL
- `docs/DATA_FORMAT.md` — raw bar storage layout
- `docs/SCHEMA_SPEC.md` — column-level type/nullability spec

## Cross-references

- Live trading engine: `services/tradebot/` — separate from this research data (intentionally). Strategies in the live engine are re-ports of research detectors as streaming state machines. Currently only `order_block` and `liquidity_sweep` are ported to live; the other 13 detectors are research-only.
- Knowledge cards: each event can link to a `research_entries` row (currently empty — feature unused, may be deprecated).
