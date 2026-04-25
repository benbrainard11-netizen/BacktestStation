# Data Warehouse Schema Spec

**This document is load-bearing.** Every parquet file produced by the ingest pipeline conforms to one of the schemas below. Field semantics, nullability, type guarantees, and timestamp conventions are pinned here so future code can rely on them. Any change to a schema bumps `SCHEMA_VERSION` in `backend/app/data/schema.py` and produces a migration note in this file.

If you're adding a new schema, edit this file FIRST, get the shape right on paper, then add it to `schema.py`. Schema migration after data accumulates is painful — this doc exists to prevent that.

## Layout

```
{BS_DATA_ROOT}/
├── raw/                                    immutable archive (DBN binary)
│   ├── live/{DATASET}-{SCHEMA}-{YYYY-MM-DD}.dbn
│   └── historical/{DATASET}-{SCHEMA}-{YYYY-MM-DD}.dbn
├── processed/                              derived parquet, regenerable from raw
│   ├── tbbo/symbol={X}/date={Y}/part-000.parquet
│   ├── mbp-1/symbol={X}/date={Y}/part-000.parquet
│   └── bars/timeframe=1m/symbol={X}/date={Y}/part-000.parquet
├── manifests/                              per-file metadata + integrity hashes
└── logs/
```

Hive partitioning (`symbol={X}/date={Y}/`) is the query story. Reading "all of NQ.c.0 in April" hits exactly 30 directories — the filesystem skips the rest.

## Universal conventions

These apply to every schema in this repo. Pin them.

### Timestamps

- **Always nanosecond precision.** All `ts_*` columns are `pa.timestamp("ns", tz="UTC")`. No exceptions.
- **Always tz-aware UTC** in the warehouse. Conversion to ET happens at the strategy / display layer (see `app/strategies/fractal_amd/signals.py:ET`).
- **Two timestamps per row, where the source provides them:**
  - `ts_event` — exchange match/event time (when the venue says it happened).
  - `ts_recv` — your machine's receipt time (when your code saw it).
- The delta `ts_recv - ts_event` is your network + processing latency. Logged so you can track infra drift over time.
- For derived data (1m bars), `ts_event` is the bar's **open time** (closed-left convention: `[ts, ts + 1min)`).

### Symbols (instrument IDs)

- The warehouse uses **canonical continuous symbols**: `NQ.c.0`, `ES.c.0`, `YM.c.0`, `RTY.c.0`. The `.c.0` suffix is Databento's continuous-front-month notation.
- **Never store exchange-specific contract symbols** (e.g. `NQM6`) in warehouse paths. They roll quarterly and break historical queries. Databento's symbology mapping handles the underlying contract resolution at ingest time.
- Per-row `instrument_id` (uint32) is preserved in raw schemas — it's the Databento-internal numeric ID, useful for joining to the symbology mapping if needed.
- Symbol partition values use the canonical form: `processed/tbbo/symbol=NQ.c.0/...`.

### Sequence numbers

- All raw schemas (TBBO, MBP-1) carry a `sequence` (uint32) column. It's monotonic per `(publisher_id, instrument_id)` stream.
- Used for: gap detection (skipped messages → integrity issue), deterministic replay (sort tie-breaker), reconnect resumption.
- Bars don't carry sequence — they're aggregations. The first/last sequence of the source rows is recoverable from the raw partition.

### Schema versioning + lineage

Every parquet file embeds a `bs.*` metadata block in its footer (see `parquet_mirror._attach_metadata`):

| Key | Value |
|---|---|
| `bs.source.kind` | `dbn` (the only producer today) |
| `bs.source.path` | absolute path to the DBN this row came from |
| `bs.source.sha256` | SHA-256 of the source DBN |
| `bs.generator.name` | `parquet_mirror` |
| `bs.generator.version` | bumped on producer-behavior changes (currently `2`) |
| `bs.generator.timestamp` | when this parquet was written |
| `bs.row_count` | row count for fast list-without-load |
| `bs.schema.name` | one of `tbbo`, `mbp-1`, `ohlcv-1m` |
| `bs.schema.version` | bumped on schema changes (currently `1`) |
| `bs.ts_event.min` | first ts in the file (ISO-format) |
| `bs.ts_event.max` | last ts in the file |

Readers (`app.data.read_*`) check `bs.schema.version` and refuse to load future-version files. Old-version files get upgraded in-memory.

## Schema: TBBO (Top of Book + Trades)

`bs.schema.name = "tbbo"`. Every trade plus the book state at the moment it printed.

| Column | Type | Required | Source / Semantics |
|---|---|---|---|
| `ts_event` | timestamp[ns,UTC] | ✅ | Exchange match time |
| `ts_recv` | timestamp[ns,UTC] | | Your machine's receipt time |
| `symbol` | string | ✅ | Canonical continuous (`NQ.c.0`) |
| `action` | string | | Databento trade action: `T` = trade, `A` = add, `M` = modify, `C` = cancel |
| `side` | string | | Aggressor side at trade: `A` = ask-side trade (buyer crossed), `B` = bid-side trade (seller crossed), `N` = none |
| `price` | float64 | ✅ | Trade price (TBBO row only fires on trades) |
| `size` | uint32 | ✅ | Trade size in contracts |
| `bid_px` | float64 | ✅ | Top-of-book bid AT the trade |
| `ask_px` | float64 | ✅ | Top-of-book ask AT the trade |
| `bid_sz` | uint32 | | Top-of-book bid size |
| `ask_sz` | uint32 | | Top-of-book ask size |
| `publisher_id` | int16 | | Databento publisher (CME = 1) |
| `instrument_id` | uint32 | | Databento numeric instrument ID |
| `sequence` | uint32 | | Monotonic per stream |

**Gotcha:** `side="N"` happens for spread leg trades and some implied/auction prints. Treat as "unknown aggressor" not "no trade."

## Schema: MBP-1 (Market By Price, depth 1)

`bs.schema.name = "mbp-1"`. Every change to the top-of-book + trades. Strict superset of TBBO in event count.

| Column | Type | Required | Source / Semantics |
|---|---|---|---|
| `ts_event` | timestamp[ns,UTC] | ✅ | Exchange event time |
| `ts_recv` | timestamp[ns,UTC] | | Your machine's receipt time |
| `ts_in_delta` | int32 | | Delta (ns) from upstream timestamp to ts_recv |
| `symbol` | string | ✅ | Canonical |
| `action` | string | | `T`/`A`/`M`/`C`/`R` (R=clear book) |
| `side` | string | | `A`/`B` for bid-side / ask-side updates; `N` for trades |
| `depth` | uint8 | | Depth level (always 0 for MBP-1) |
| `price` | float64 | ✅ | Order price (or trade price for `T` rows) |
| `size` | uint32 | ✅ | Order size at that level (or trade size) |
| `flags` | uint8 | | Databento flags: bit 0 = last in packet, bit 1 = trade was an aggressor, bit 2 = TOB changed, etc. (see Databento docs) |
| `bid_px` | float64 | ✅ | Top-of-book bid AFTER the event |
| `ask_px` | float64 | ✅ | Top-of-book ask AFTER the event |
| `bid_sz` | uint32 | | Top-of-book bid size after |
| `ask_sz` | uint32 | | Top-of-book ask size after |
| `bid_ct` | uint32 | | Order count at top bid (depth of book) |
| `ask_ct` | uint32 | | Order count at top ask |
| `publisher_id` | int16 | | Databento publisher |
| `instrument_id` | uint32 | | Databento numeric instrument ID |
| `sequence` | uint32 | | Monotonic per stream |

**Gotcha:** the bid_px/ask_px columns are the book state AFTER the event in MBP-1 (vs at-the-trade in TBBO). Don't conflate them across schemas.

## Schema: OHLCV-1m bars

`bs.schema.name = "ohlcv-1m"`. Derived from MBP-1 or TBBO trade rows by `parquet_mirror._compute_1m_bars`.

| Column | Type | Required | Source / Semantics |
|---|---|---|---|
| `ts_event` | timestamp[ns,UTC] | ✅ | Bar **open** time. Closed-left interval: bar covers `[ts, ts+1min)` |
| `symbol` | string | ✅ | Canonical |
| `open` | float64 | ✅ | First trade price in the minute |
| `high` | float64 | ✅ | Max trade price |
| `low` | float64 | ✅ | Min trade price |
| `close` | float64 | ✅ | Last trade price |
| `volume` | uint64 | ✅ | Sum of trade sizes |
| `trade_count` | uint32 | | Number of trade rows aggregated |
| `vwap` | float64 | | Volume-weighted average trade price |

**What's NOT in 1m bars (intentional):**
- No book state: bid/ask snapshots are not aggregated. If you need the book at a bar's close, query MBP-1.
- No sequence numbers: lineage is via the source DBN path (in parquet metadata) + the bar's time range.

**Gotcha:** A bar with zero trades does NOT exist in this schema (no row written for empty minutes). When backtesting, the engine handles missing minutes by skipping forward; if you need contiguous time coverage, forward-fill in the consumer.

## Time-of-day reference

For the strategy layer (Fractal AMD, etc.) we always work in **America/New_York** because that's the futures session calendar:

| Boundary | ET | UTC (during EDT, UTC-4) | UTC (during EST, UTC-5) |
|---|---|---|---|
| Globex open (Sunday) | 18:00 | 22:00 | 23:00 |
| Globex close (Friday) | 17:00 | 21:00 | 22:00 |
| Daily reset | 17:00 → 18:00 | gap from 21:00 → 22:00 | 22:00 → 23:00 |
| RTH cash session open (US) | 09:30 | 13:30 | 14:30 |
| RTH cash session close | 16:00 | 20:00 | 21:00 |

Strategies use ET via `zoneinfo.ZoneInfo("America/New_York")` — see `app/strategies/fractal_amd/signals.py:ET`. Don't hardcode UTC offsets; they shift with daylight saving.

## Migration discipline

Schema changes:
1. Edit this doc with the new field + rationale.
2. Bump `SCHEMA_VERSION` in `backend/app/data/schema.py`.
3. Update `DataSchema(pa_schema=...)` for the affected schema.
4. If existing parquet files need to be re-readable, the reader's version-upgrade path handles old data. If not (rare), document the fact.
5. Add a row to the migration log below.

### Migration log

| Date | From → To | Schemas affected | What changed |
|---|---|---|---|
| 2026-04-25 | n/a → `1` | tbbo, mbp-1, ohlcv-1m | Initial spec doc; pins existing v1 schemas |
