# Research Events Dictionary

> **Status: canonical.** Single reference for navigating the BacktestStation research warehouse. If you're an ML researcher, an LLM agent, or someone building a strategy on top of this data — start here.

This doc covers the **research events** layer: 4.87M+ detector fires across 16 detectors, 23 symbols, 11 years of futures history. For raw bar storage + file layout, see [`DATA_FORMAT.md`](./DATA_FORMAT.md). For per-column field types and nullability, see [`SCHEMA_SPEC.md`](./SCHEMA_SPEC.md).

> Counts last refreshed: 2026-05-19 from R2 manifest `data/research_events/manifest.json` (4,869,147 rows, 365 parquet files). Local SQLite may lag R2 by hours-to-days depending on sync cadence.

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

## The 16 detectors

Counts as of 2026-05-19 from R2 manifest. Per-symbol distribution is roughly uniform across the major futures (NQ ~280k, YM ~270k, ES ~270k, others scale by liquidity).

### 1. `order_block` (244,400 events, 14 variants)

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

### 2. `liquidity_sweep` (290,515 events, 14 variants)

Same 14 modes as order_block, but fires on the SWEEP alone (no OB + confirmation requirement). Higher event count, lower per-event signal quality. Used REVERSED in v20 (sweep of high → LONG signal).

### 3. `fvg_formation` (1,453,096 events, 8 variants)

Fair Value Gap detection — 3-candle pattern with an unfilled gap.

| event_type | timeframe | count |
|---|---|---:|
| 15m_fvg | 15M | 937k |
| 1h_fvg | 1H | 264k |
| 4h_fvg | 4H | 79k |
| daily_fvg | 1D | 16k |

Sides: bullish/bearish. Outcomes track mitigation (was the gap tapped/filled).

### 4. `forming_volume_profile` (1,176,018 events, 6 variants)

Daily volume profile snapshotted at intermediate timestamps (1h / 4h marks).

| event_type | timeframe | side | count |
|---|---|---|---:|
| daily_vp_asof_1h | ASOF_1H | balanced/buying/selling | 971k |
| daily_vp_asof_4h | ASOF_4H | balanced/buying/selling | 225k |

Used for "is the day's profile shaping up bullish or bearish at this snapshot point?"

### 5. `swing_pivot` (422,488 events, 10 variants)

N-bar swing highs/lows (pivot_3 = 3 bars on each side, pivot_5 = 5).

| event_type | timeframe | count |
|---|---|---:|
| pivot_3_1h / pivot_5_1h | 1H | 271k |
| pivot_3_4h / pivot_5_4h | 4H | 87k |
| pivot_5_daily | 1D | 6.7k |

Sides: high/low.

### 6. `displacement_candle` (226,342 events, 6 variants)

Large-body candles relative to recent average — momentum signals.

| event_type | timeframe | count |
|---|---|---:|
| 1h_disp | 1H | 149k |
| 4h_disp | 4H | 41k |
| daily_disp | 1D | 8.5k |

Sides: bullish/bearish.

### 7. `opening_range_breakout` (192,981 events, 12 variants)

Opening-range break of N-minute window after session open.

| event_type | timeframe | count |
|---|---|---:|
| ny_5m / ny_15m / ny_30m | 5M / 15M / 30M | ~40k each |
| asia_60m | 60M | 36k |

Sides: bullish/bearish/doji.

### 8. `interval_true_range` (226,287 events, 15 variants)

ATR-style range measurement over distinct intervals.

| event_type | timeframe | count |
|---|---|---:|
| daily_itr | 1D | 49k |
| asia_itr / london_itr / ny_itr | session | ~47k each |
| weekly_itr | 1W | 10k |

Sides: bullish/bearish/doji.

### 9. `volume_profile` (219,757 events, 15 variants)

Completed volume profiles per period.

| event_type | timeframe | count |
|---|---|---:|
| daily_volume_profile | 1D | 48k |
| asia_volume_profile / london_volume_profile / ny_volume_profile | ASIA/LONDON/NY | ~45k each |
| weekly_volume_profile | 1W | 10k |

Sides: balanced/buying/selling.

### 10. `time_profile` (125,233 events, 12 variants)

Time-of-day session structure (3-session vs 4-session segmentations).

| event_type | timeframe | count |
|---|---|---:|
| daily_3session / daily_4session | 1D | 49k each |
| weekly | 1W | 10k |
| monthly | 1MO | 2.3k |

Sides: bullish/bearish/doji.

### 11. `psp_candle_divergence` (89,105 events, 6 variants)

Power-of-3 / candle divergence between correlated symbols.

| event_type | timeframe | count |
|---|---|---:|
| 1h_psp | 1H | 53k |
| 4h_psp | 4H | 18.5k |
| daily_psp | 1D | 4.8k |

Sides: bullish/bearish.

### 12. `first_third_range` (63,164 events, 6 variants)

First 1/3 of period range — early indicator of period direction.

| event_type | timeframe | count |
|---|---|---:|
| first_third_daily | 1D | 45k |
| first_third_weekly | 1W | 10k |

Sides: bullish/bearish/doji.

### 13. `opening_gap_levels` (46,382 events, 4 variants)

New daily / weekly opening gaps (NDOG / NWOG).

| event_type | timeframe | count |
|---|---|---:|
| ndog | 1D_GAP | 32k |
| nwog | 1W_GAP | 7k |

Sides: gap_up/gap_down.

### 14. `equal_levels` (61,185 events, 14 variants)

Repeated highs/lows at the same price (within 5pts or 15pts tolerance).

| event_type | timeframe | count |
|---|---|---:|
| eq_pivot_3_1h_15pts / eq_pivot_3_1h_5pts | LEVEL | ~12k |
| eq_pivot_5_1h_15pts / eq_pivot_5_1h_5pts | LEVEL | ~7.5k |
| ...4h / daily variants | LEVEL | ~3.5k |

Sides: high/low.

### 15. `smt_htf_reference_divergence` (13,780 events, 4 variants)

Smart-money-technique divergence between correlated symbols (NQ vs ES, etc.).

| event_type | timeframe | count |
|---|---|---:|
| previous_day_smt | 1H | 8.5k |
| weekly_smt | 4H | 3.1k |

Sides: high/low.

### 16. `macro_event_anchor` (18,414 events, 113 distinct event_types)

Scheduled US economic-release anchor events. For each FOMC / NFP / CPI /
ISM / etc. release, this detector emits one event PER tracked symbol
(currently ES/NQ/YM = 3 rows per release). The event marks the moment
the news prints; `outcomes` carry forward-window R-stats for 1m/5m/etc.
intervals so you can study price reaction.

This is fundamentally different from the price-action detectors above:
it's anchored to **calendar events**, not chart patterns. Use it to
join price-reaction stats against scheduled macro catalysts.

| Field | Value |
|---|---|
| event_types | 113 distinct `pre_<event_group>` strings |
| timeframe | `macro` (single bucket) |
| sides | `high` / `medium` (Forex Factory impact rating) |
| symbols | ES.c.0, NQ.c.0, YM.c.0 (one event = 3 rows) |
| years covered | 2015–2025 |

Event_type families (selection from 113):

- **FOMC**: `pre_fomc_statement`, `pre_fomc_press_conference`, `pre_fomc_member_powell_speaks` (+ historical members: yellen, bernanke, dudley, fischer, brainard, lacker, lockhart, evans, tarullo, williams, rosengren, quarles, waller...)
- **Jobs**: `pre_non_farm_employment_change`, `pre_nfp`, `pre_unemployment_claims`, `pre_unemployment_rate`
- **Inflation/Growth**: `pre_ppi_m_m`, `pre_prelim_gdp_q_q`, `pre_prelim_gdp_price_index_q_q`, `pre_prelim_uom_inflation_expectations`
- **Activity**: `pre_ism_manufacturing_pmi`, `pre_ism_services_pmi`, `pre_ism_manufacturing_prices`, `pre_industrial_production_m_m`, `pre_retail_sales_m_m`, `pre_personal_spending_m_m`
- **Housing**: `pre_housing_starts`, `pre_new_home_sales`, `pre_pending_home_sales_m_m`, `pre_s_and_p_cs_composite_20_hpi_y_y`, `pre_nahb_housing_market_index`
- **Trade**: `pre_trade_balance`, `pre_goods_trade_balance`, `pre_import_prices_m_m`
- **Political**: `pre_president_trump_speaks`, `pre_president_biden_speaks`, `pre_presidential_election`
- **Treasury**: `pre_treasury_sec_yellen_speaks`, `pre_treasury_sec_mnuchin_speaks`, `pre_treasury_sec_lew_speaks`, `pre_treasury_currency_report`
- **Sentiment**: `pre_prelim_uom_consumer_sentiment`, `pre_revised_uom_consumer_sentiment`
- **Regional Fed**: `pre_philly_fed_manufacturing_index`, `pre_richmond_manufacturing_index`

Sample `event_data`:
```json
{
  "schema_version": 1,
  "detector_version": "v1",
  "source_event_id": "2015_01_02_100000_usd_ism_manufacturing_pmi_75aca3",
  "event_name": "ISM Manufacturing PMI",
  "event_group": "ism_manufacturing_pmi",
  "country": "US",
  "currency": "USD",
  "impact": "high",
  "source": "forex_factory_archive",
  "release_ts_utc": "2015-01-02T15:00:00+00:00",
  "release_ts_et": "2015-01-02T10:00:00-05:00",
  "minutes_until_release": 1.0,
  "scheduled_hour_et": 10,
  "day_of_week_et": 4,
  "has_forecast": true,
  "forecast_raw": "57.6"
}
```

Sample `outcomes`:
```json
{
  "schema_version": 1,
  "outcome_version": "v2",
  "release_ts_utc": "2015-01-02T15:00:00+00:00",
  "reference_close": 2062.25,
  "max_horizon_minutes": 1440,
  "next_1m": {
    "open": 2062.25, "high": 2063.0, "low": 2060.5, "close": 2060.75,
    "range_pts": 2.5, "body_pts": -1.5, "return_pts": -1.5,
    "abs_return_pts": 1.5
  },
  "next_5m": {...},
  "next_15m": {...},
  "next_1h": {...}
}
```

Common query pattern: "what's the median 5m return on NQ after a high-impact NFP release?" — filter by `event_type='pre_non_farm_employment_change'`, `side='high'`, `primary_symbol='NQ.c.0'`, extract `outcomes.next_5m.return_pts`.

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

- Live trading engine: `services/tradebot/` — separate from this research data (intentionally). Strategies in the live engine are re-ports of research detectors as streaming state machines. Currently only `order_block` and `liquidity_sweep` are ported to live (as `ob_sweep_v8a`); the other 14 detectors are research-only.
- Knowledge cards: each event can link to a `research_entries` row (currently empty — feature unused, may be deprecated).
