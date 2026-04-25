# Data warehouse format

> **Status: canonical.** This is the actual layout BacktestStation uses for storing market data on disk. Producers (live ingester, historical puller, parquet mirror) write to this layout; consumers (the reader library, future engine, future drift monitor) read from it.

## Top-level directory

```
{BS_DATA_ROOT}/
├── raw/                          immutable source archives
│   ├── live/                     Databento Live TBBO DBN (per UTC day)
│   ├── historical/               Databento Historical MBP-1 DBN (per day)
│   ├── databento/                Hive-partitioned parquet derived from DBN
│   │   ├── tbbo/
│   │   └── mbp-1/
│   └── bot/                      live trading bot Rithmic CSVs (future)
├── processed/                    derived from raw, regeneratable
│   └── bars/                     pre-computed bars
│       └── timeframe=1m/         only 1m is pre-computed
├── features/                     engineered features (reserved, unused yet)
├── manifests/                    JSON audit trail per ingest run
│   └── ingest_runs/
├── heartbeat/                    live ingester status JSON
└── logs/                         daemon log files
```

The three tiers — `raw/`, `processed/`, `features/` — form a dependency chain:

```
raw/ (DBN, immutable)
  └─> raw/databento/ (parquet mirror of DBN)
       └─> processed/bars/ (computed from parquet)
            └─> features/ (computed from bars, unused yet)
```

Each tier regenerates from the one above. If `processed/` corrupts, regenerate from `raw/databento/`. If `raw/databento/` corrupts, regenerate from DBN. DBN itself is never regenerated — it's the source of truth.

## Hive partitioning

All parquet outputs use `key=value` directory partitioning. This is the standard format for DuckDB, Polars, Spark, and `pyarrow.dataset.dataset(partitioning="hive")`. Auto-discovery just works — every tool sees the partitions without configuration.

### `raw/databento/`

```
raw/databento/{schema}/symbol={symbol}/date={YYYY-MM-DD}/part-000.parquet
```

Examples:
- `raw/databento/tbbo/symbol=NQ.c.0/date=2026-04-24/part-000.parquet`
- `raw/databento/mbp-1/symbol=ES.c.0/date=2026-03-15/part-000.parquet`

`{schema}` is the databento schema name (`tbbo`, `mbp-1`, etc.).
`{symbol}` is the resolved continuous symbol (`NQ.c.0`, not `NQM6`).
`{date}` is UTC date.

File name is always `part-000.parquet` for single-part outputs. Multi-part producers (Spark-style) would use `part-001`, `part-002`, etc., but our parquet mirror always produces one file per partition.

### `processed/bars/`

```
processed/bars/timeframe={tf}/symbol={symbol}/date={YYYY-MM-DD}/part-000.parquet
```

Currently `{tf}` is only ever `1m`. Other timeframes (5m, 15m, 1h, daily) are derived at read time from the 1m bars by the reader library — not pre-computed. Adding pre-computed timeframes would mean storing six near-redundant copies of the same data.

### `features/`

```
features/symbol={symbol}/date={YYYY-MM-DD}/{feature_set}.parquet
```

Reserved for future feature-engineering output (regime labels, setup quality scores, ML features). Not populated yet.

## Column schemas

Schemas defined in `backend/app/data/schema.py`. Producers must emit exactly these columns. Readers can project subsets.

### TBBO

| Column | Type | Notes |
|---|---|---|
| `ts_event` | `timestamp[ns, tz=UTC]` | venue timestamp (primary sort key) |
| `ts_recv` | `timestamp[ns, tz=UTC]` | timestamp received by databento |
| `symbol` | `string` (dictionary) | resolved continuous symbol, e.g. "NQ.c.0" |
| `action` | `string` (dictionary) | "T" trade, "A" add, "C" cancel, etc. |
| `side` | `string` (dictionary) | "A" ask aggressor, "B" bid aggressor, "N" |
| `price` | `float64` | trade or quote price |
| `size` | `uint32` | trade or quote size |
| `bid_px` | `float64` | top-of-book bid price (after this event) |
| `ask_px` | `float64` | top-of-book ask price (after this event) |
| `bid_sz` | `uint32` | top-of-book bid size |
| `ask_sz` | `uint32` | top-of-book ask size |
| `publisher_id` | `int16` | databento publisher (CME = 1) |
| `instrument_id` | `uint32` | venue instrument id |
| `sequence` | `uint32` | venue sequence number |

**NOT stored** (compute at read time):
- `mid_px` = `(bid_px + ask_px) / 2`
- `spread` = `ask_px - bid_px`
- `spread_bps` = `spread / mid_px * 10_000`

### MBP-1

Same as TBBO plus:

| Column | Type | Notes |
|---|---|---|
| `depth` | `uint8` | book level (always 0 for MBP-1) |
| `flags` | `uint8` | databento bit flags |
| `bid_ct` | `uint32` | order count at top bid |
| `ask_ct` | `uint32` | order count at top ask |
| `ts_in_delta` | `int32` | nanos between event and recv |

### OHLCV-1m bars

| Column | Type | Notes |
|---|---|---|
| `ts_event` | `timestamp[ns, tz=UTC]` | bar start (UTC minute boundary) |
| `symbol` | `string` (dictionary) | |
| `open` | `float64` | first trade in bar (or NaN if no trades) |
| `high` | `float64` | max trade price |
| `low` | `float64` | min trade price |
| `close` | `float64` | last trade price |
| `volume` | `uint64` | sum of trade sizes |
| `trade_count` | `uint32` | count of trade actions |
| `vwap` | `float64` | volume-weighted average price |

Empty minutes (no trades) emit a row with `open=high=low=close=last_close`, `volume=0`, `trade_count=0`. This makes the bar series gap-free, which is what most analysis tools expect.

## Embedded parquet metadata

Each parquet file carries key/value metadata in its footer (via `pyarrow.parquet.write_table(metadata=...)`). Keys are namespaced with `bs.` prefix:

| Key | Value |
|---|---|
| `bs.source.kind` | `"dbn"` for parquet derived from DBN |
| `bs.source.path` | absolute path to the source DBN file |
| `bs.source.sha256` | sha256 of the source DBN |
| `bs.generator.name` | e.g. `"parquet_mirror"` |
| `bs.generator.version` | e.g. `"2"` (bumped on producer changes) |
| `bs.generator.timestamp` | ISO-8601 UTC of generation |
| `bs.row_count` | total rows (also in parquet's native metadata) |
| `bs.ts_event.min` | ISO-8601 UTC, earliest event in file |
| `bs.ts_event.max` | ISO-8601 UTC, latest event in file |
| `bs.schema.name` | "tbbo", "mbp-1", "ohlcv-1m" |
| `bs.schema.version` | "1" |

Lets you trace any parquet back to its DBN source, detect generator-version drift, and verify integrity offline.

## Manifest files

```
manifests/ingest_runs/{date}_{schema}_manifest.json
```

One manifest per (UTC date × schema). Covers all symbols processed for that combination. Independent of the database — files are the source of truth, manifests are the audit trail.

Schema:

```json
{
  "schema_version": 1,
  "date": "2026-04-24",
  "data_schema": "tbbo",
  "source": {
    "kind": "dbn",
    "path": "/abs/path/to/source.dbn",
    "sha256": "abc...",
    "size_bytes": 12345678
  },
  "outputs": [
    {
      "kind": "raw_parquet",
      "schema": "tbbo",
      "symbol": "NQ.c.0",
      "path": "/abs/path/to/raw/databento/tbbo/symbol=NQ.c.0/date=2026-04-24/part-000.parquet",
      "rows": 1234567,
      "size_bytes": 9876543,
      "ts_event_min": "2026-04-24T00:00:00.000000000+00:00",
      "ts_event_max": "2026-04-24T23:59:59.999999999+00:00"
    },
    {
      "kind": "bars_1m",
      "symbol": "NQ.c.0",
      "path": "/abs/path/to/processed/bars/timeframe=1m/symbol=NQ.c.0/date=2026-04-24/part-000.parquet",
      "rows": 1440,
      "size_bytes": 45678
    }
  ],
  "validation": {
    "row_count_ok": true,
    "schema_columns_ok": true,
    "duplicate_ts_event_count": 0,
    "warnings": []
  },
  "generator": {
    "name": "parquet_mirror",
    "version": "2",
    "started_at": "2026-04-25T03:00:00+00:00",
    "completed_at": "2026-04-25T03:00:14+00:00"
  },
  "status": "complete",
  "errors": []
}
```

`status` is one of: `"complete"`, `"partial"`, `"failed"`.

## Validation rules

Every parquet write must pass:

1. **Row count > 0** — empty DBN doesn't produce a parquet (skipped, manifest records why).
2. **Schema columns present** — every column in the schema definition must exist with the declared type.
3. **No duplicate `ts_event`** within a single file (warn + record count; doesn't fail the write).
4. **`ts_event` monotonic non-decreasing** within a partition (warn if violated).
5. **`ts_event` falls within the partition's date** (UTC) — fail loudly if events leak across days.

Validation results land in `validation` of the manifest.

## Symbol naming

Continuous front-month symbology, e.g. `NQ.c.0`, is used throughout. The `.` characters in partition values work fine in pyarrow / DuckDB / Polars; tested.

If you need to reference a specific contract (e.g. `NQM6`) for a one-off backfill, use that as the `symbol=` partition value — it goes through the same schema and reader API.

## Reader API

`backend/app/data/reader.py` exposes:

```python
from app.data import read_tbbo, read_mbp1, read_bars

# Single symbol, date range
df = read_tbbo(
    symbol="NQ.c.0",
    start="2026-04-01",
    end="2026-04-24",
    columns=None,        # optional projection
    as_pandas=True,      # else returns pyarrow.Table
)

# Bars (any timeframe — 5m, 15m, 1h, etc. derive from 1m)
bars = read_bars(
    symbol="NQ.c.0",
    timeframe="5m",
    start="2026-04-01",
    end="2026-04-24",
)
```

Behavior:
- Missing days: returned silently with a `warnings` log entry; result simply skips that day's rows.
- Date range half-open `[start, end)` matching ISO conventions.
- Returns are gap-aware — bar reads include empty-minute rows.

Higher timeframe derivation: `5m`, `15m`, `1h`, `4h`, `1d`. Read 1m bars, group by floor(ts_event, timeframe), aggregate. ~10ms per day per symbol — cheap enough to do on every read.

## Migration from legacy layout

The pre-rewrite parquet layout was:

```
data/parquet/{symbol}/{schema}/{YYYY-MM-DD}.parquet
```

To migrate, run:

```bash
python -m app.ingest.parquet_mirror --rebuild
```

This reprocesses every DBN file under `raw/live/` and `raw/historical/`, emits Hive-style parquet at the new paths, and writes manifests. After it succeeds, the legacy `data/parquet/` tree can be deleted manually:

```powershell
Remove-Item -Recurse C:\data\parquet
```

DBN files are not touched. They remain the immutable source.

## What this format is NOT

- **Not a query engine.** It's just files on disk in a standard layout. Use DuckDB, Polars, or pyarrow to query.
- **Not real-time.** Live DBN is real-time; parquet is generated hourly via Task Scheduler.
- **Not deduplicated across days.** A trade reported with both `ts_event` on day N and `ts_recv` on day N+1 lands in day N's partition (by `ts_event`).
- **Not multi-tenant.** Single user, single warehouse.

## Versioning

Schema changes bump `bs.schema.version` in embedded metadata. Producer changes bump `bs.generator.version`. Reader code should check schema version on read and either upgrade in-memory or refuse with a clear error.

For the foreseeable future, schema is `"1"` and generator is `"2"` (post-rewrite).
