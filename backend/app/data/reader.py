"""Reader API for the BacktestStation data warehouse.

Wraps pyarrow's Hive-partitioned dataset interface in a tight,
trader-ergonomic API:

    df = read_tbbo(symbol="NQ.c.0", start="2026-04-01", end="2026-04-24")
    bars = read_bars(symbol="NQ.c.0", timeframe="5m", start="...", end="...")

Half-open `[start, end)` matching ISO conventions. Missing days are
silently skipped (logged at info level). Higher-timeframe bar reads
derive from the stored 1m bars at query time — no pre-computation.

See [`docs/DATA_FORMAT.md`](../../../docs/DATA_FORMAT.md) for the
on-disk layout these functions read.
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from app.core.paths import warehouse_root
from app.data.schema import (
    BARS_1M_SCHEMA,
    MBP1_SCHEMA,
    MBO_SCHEMA,
    TBBO_SCHEMA,
    DataSchema,
)
from app.data.storage import LocalStorage, Storage, get_storage

logger = logging.getLogger(__name__)

# Timeframes the bar reader understands. The first is the storage
# timeframe; everything else is derived at read time via groupby/floor.
_BAR_TIMEFRAMES = {
    "1m": dt.timedelta(minutes=1),
    "2m": dt.timedelta(minutes=2),
    "3m": dt.timedelta(minutes=3),
    "5m": dt.timedelta(minutes=5),
    "10m": dt.timedelta(minutes=10),
    "15m": dt.timedelta(minutes=15),
    "30m": dt.timedelta(minutes=30),
    "1h": dt.timedelta(hours=1),
    "90m": dt.timedelta(minutes=90),
    "2h": dt.timedelta(hours=2),
    "4h": dt.timedelta(hours=4),
    "6h": dt.timedelta(hours=6),
    "1d": dt.timedelta(days=1),
}


# --- Path helpers --------------------------------------------------------


def _raw_partition_prefix(schema: str) -> str:
    return f"raw/databento/{schema}"


def _bars_partition_prefix(timeframe: str) -> str:
    return f"processed/bars/timeframe={timeframe}"


def _clean_mbo_trading_day_prefix() -> str:
    return "clean/databento/mbo_trading_day"


def _resolve_storage(data_root: Path | None) -> Storage:
    """If `data_root` is explicitly passed, force LocalStorage there.
    Otherwise pick the backend from env vars (`BS_DATA_BACKEND`)."""
    if data_root is not None:
        return LocalStorage(data_root)
    return get_storage()


# --- Date helpers --------------------------------------------------------


def _parse_date(value: str | dt.date | dt.datetime) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(value)


def _parse_timestamp(value: str | dt.date | dt.datetime) -> dt.datetime:
    """Parse date-ish input as a tz-aware UTC timestamp."""
    if isinstance(value, dt.datetime):
        ts = value
    elif isinstance(value, dt.date):
        ts = dt.datetime.combine(value, dt.time.min)
    else:
        raw = value.strip()
        if "T" in raw or " " in raw:
            ts = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            ts = dt.datetime.combine(dt.date.fromisoformat(raw), dt.time.min)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(dt.timezone.utc)


def _date_range(start: dt.date, end: dt.date) -> list[dt.date]:
    """Half-open [start, end). Empty list if end <= start."""
    out: list[dt.date] = []
    cur = start
    while cur < end:
        out.append(cur)
        cur = cur + dt.timedelta(days=1)
    return out


def _partition_dates_for_window(
    start: str | dt.date | dt.datetime,
    end: str | dt.date | dt.datetime,
) -> list[dt.date]:
    """Calendar partitions whose UTC date overlaps [start, end)."""
    start_ts = _parse_timestamp(start)
    end_ts = _parse_timestamp(end)
    if end_ts <= start_ts:
        return []
    last_ts = end_ts - dt.timedelta(microseconds=1)
    return _date_range(start_ts.date(), last_ts.date() + dt.timedelta(days=1))


def _filter_table_window(
    table: pa.Table,
    *,
    schema: DataSchema,
    start: str | dt.date | dt.datetime,
    end: str | dt.date | dt.datetime,
) -> pa.Table:
    """Apply exact half-open timestamp filtering after partition reads."""
    if table.num_rows == 0 or schema.sort_key not in table.column_names:
        return table
    start_ts = _parse_timestamp(start)
    end_ts = _parse_timestamp(end)
    if end_ts <= start_ts:
        return table.slice(0, 0)
    ts_col = table[schema.sort_key]
    start_scalar = pa.scalar(start_ts, type=ts_col.type)
    end_scalar = pa.scalar(end_ts, type=ts_col.type)
    mask = pc.and_(
        pc.greater_equal(ts_col, start_scalar),
        pc.less(ts_col, end_scalar),
    )
    return table.filter(mask)


def _globex_period_for_trading_day(trading_day: str | dt.date):
    # Imported lazily to keep the base data reader usable without loading
    # the research package at module import time.
    from app.research.sessions import globex_day_for_trading_date

    return globex_day_for_trading_date(_parse_date(trading_day))


def _mbo_trading_day_cache_path(
    *,
    symbol: str,
    trading_day: dt.date,
    data_root: Path | None,
) -> Path:
    root = data_root if data_root is not None else warehouse_root()
    return (
        root
        / "clean"
        / "databento"
        / "mbo_trading_day"
        / f"symbol={symbol}"
        / f"trading_day={trading_day.isoformat()}"
        / "part-000.parquet"
    )


def _read_mbo_trading_day_cache(
    *,
    symbol: str,
    trading_day: dt.date,
    columns: list[str] | None,
    data_root: Path | None,
) -> pa.Table | None:
    read_columns = columns
    if read_columns is not None and MBO_SCHEMA.sort_key not in read_columns:
        read_columns = [MBO_SCHEMA.sort_key] + list(read_columns)
    if data_root is not None:
        path = _mbo_trading_day_cache_path(
            symbol=symbol,
            trading_day=trading_day,
            data_root=data_root,
        )
        if not path.exists():
            return None
        return pq.ParquetFile(path).read(columns=read_columns)

    storage = _resolve_storage(data_root)
    table = storage.read_partitions(
        partition_root=_clean_mbo_trading_day_prefix(),
        symbol=symbol,
        dates=[trading_day],
        empty_schema=MBO_SCHEMA.pa_schema,
        columns=read_columns,
        date_partition_name="trading_day",
    )
    return None if table.num_rows == 0 else table


# --- Core reader ---------------------------------------------------------


def _read_partitioned(
    storage: Storage,
    *,
    partition_root: str,
    symbol: str,
    dates: list[dt.date],
    schema: DataSchema,
    columns: list[str] | None,
    date_partition_name: str = "date",
) -> pa.Table:
    """Read all matching partition files for `(symbol, date)` via `storage`."""
    if columns is not None and schema.sort_key not in columns:
        # Always include the sort key so users can filter even if they
        # didn't request it — common ergonomic surprise otherwise.
        columns = [schema.sort_key] + list(columns)
    return storage.read_partitions(
        partition_root=partition_root,
        symbol=symbol,
        dates=dates,
        empty_schema=schema.pa_schema,
        columns=columns,
        date_partition_name=date_partition_name,
    )


def read_tbbo(
    *,
    symbol: str,
    start: str | dt.date,
    end: str | dt.date,
    columns: list[str] | None = None,
    as_pandas: bool = True,
    data_root: Path | None = None,
):
    """Read TBBO records for `symbol` over [start, end).

    Returns a pandas DataFrame by default, or a pyarrow Table if
    `as_pandas=False`. Missing days are silently skipped.
    """
    storage = _resolve_storage(data_root)
    dates = _partition_dates_for_window(start, end)
    table = _read_partitioned(
        storage,
        partition_root=_raw_partition_prefix("tbbo"),
        symbol=symbol,
        dates=dates,
        schema=TBBO_SCHEMA,
        columns=columns,
    )
    table = _filter_table_window(table, schema=TBBO_SCHEMA, start=start, end=end)
    return table.to_pandas() if as_pandas else table


def read_mbp1(
    *,
    symbol: str,
    start: str | dt.date,
    end: str | dt.date,
    columns: list[str] | None = None,
    as_pandas: bool = True,
    data_root: Path | None = None,
):
    """Read MBP-1 records for `symbol` over [start, end)."""
    storage = _resolve_storage(data_root)
    dates = _partition_dates_for_window(start, end)
    table = _read_partitioned(
        storage,
        partition_root=_raw_partition_prefix("mbp-1"),
        symbol=symbol,
        dates=dates,
        schema=MBP1_SCHEMA,
        columns=columns,
    )
    table = _filter_table_window(table, schema=MBP1_SCHEMA, start=start, end=end)
    return table.to_pandas() if as_pandas else table


def read_mbo(
    *,
    symbol: str,
    start: str | dt.date,
    end: str | dt.date,
    columns: list[str] | None = None,
    as_pandas: bool = True,
    data_root: Path | None = None,
):
    """Read MBO records for `symbol` over [start, end)."""
    storage = _resolve_storage(data_root)
    dates = _partition_dates_for_window(start, end)
    table = _read_partitioned(
        storage,
        partition_root=_raw_partition_prefix("mbo"),
        symbol=symbol,
        dates=dates,
        schema=MBO_SCHEMA,
        columns=columns,
    )
    table = _filter_table_window(table, schema=MBO_SCHEMA, start=start, end=end)
    return table.to_pandas() if as_pandas else table


def read_tbbo_trading_day(
    *,
    symbol: str,
    trading_day: str | dt.date,
    columns: list[str] | None = None,
    as_pandas: bool = True,
    data_root: Path | None = None,
):
    """Read TBBO over the full Globex trading day labeled `trading_day`."""
    period = _globex_period_for_trading_day(trading_day)
    return read_tbbo(
        symbol=symbol,
        start=period.start_utc,
        end=period.end_utc,
        columns=columns,
        as_pandas=as_pandas,
        data_root=data_root,
    )


def read_mbp1_trading_day(
    *,
    symbol: str,
    trading_day: str | dt.date,
    columns: list[str] | None = None,
    as_pandas: bool = True,
    data_root: Path | None = None,
):
    """Read MBP-1 over the full Globex trading day labeled `trading_day`."""
    period = _globex_period_for_trading_day(trading_day)
    return read_mbp1(
        symbol=symbol,
        start=period.start_utc,
        end=period.end_utc,
        columns=columns,
        as_pandas=as_pandas,
        data_root=data_root,
    )


def read_mbo_trading_day(
    *,
    symbol: str,
    trading_day: str | dt.date,
    columns: list[str] | None = None,
    as_pandas: bool = True,
    data_root: Path | None = None,
):
    """Read MBO over the full Globex trading day labeled `trading_day`."""
    trading_day_d = _parse_date(trading_day)
    cached = _read_mbo_trading_day_cache(
        symbol=symbol,
        trading_day=trading_day_d,
        columns=columns,
        data_root=data_root,
    )
    if cached is not None:
        period = _globex_period_for_trading_day(trading_day_d)
        cached = _filter_table_window(
            cached,
            schema=MBO_SCHEMA,
            start=period.start_utc,
            end=period.end_utc,
        )
        return cached.to_pandas() if as_pandas else cached

    period = _globex_period_for_trading_day(trading_day_d)
    return read_mbo(
        symbol=symbol,
        start=period.start_utc,
        end=period.end_utc,
        columns=columns,
        as_pandas=as_pandas,
        data_root=data_root,
    )


def read_bars(
    *,
    symbol: str,
    timeframe: str,
    start: str | dt.date,
    end: str | dt.date,
    columns: list[str] | None = None,
    as_pandas: bool = True,
    data_root: Path | None = None,
):
    """Read OHLCV bars for `symbol` at the requested timeframe.

    Only `timeframe="1m"` is read directly from disk. Higher timeframes
    are derived at query time by grouping the 1m bars on the
    timeframe-floored timestamp. Cheap (~10ms per day per symbol).

    Supported timeframes: 1m, 2m, 3m, 5m, 10m, 15m, 30m, 1h, 90m, 2h, 4h, 6h, 1d.
    """
    if timeframe not in _BAR_TIMEFRAMES:
        known = ", ".join(_BAR_TIMEFRAMES.keys())
        raise ValueError(f"unknown timeframe {timeframe!r}; known: {known}")

    storage = _resolve_storage(data_root)
    dates = _partition_dates_for_window(start, end)
    base = _read_partitioned(
        storage,
        partition_root=_bars_partition_prefix("1m"),
        symbol=symbol,
        dates=dates,
        schema=BARS_1M_SCHEMA,
        columns=None,  # need full set for resampling; project at the end
    )
    base = _filter_table_window(base, schema=BARS_1M_SCHEMA, start=start, end=end)

    if base.num_rows == 0:
        return base.to_pandas() if as_pandas else base

    if timeframe == "1m":
        resampled = base
    else:
        resampled = _resample_bars(base, _BAR_TIMEFRAMES[timeframe])

    if columns is not None:
        keep = [c for c in columns if c in resampled.column_names]
        if BARS_1M_SCHEMA.sort_key in resampled.column_names and (
            BARS_1M_SCHEMA.sort_key not in keep
        ):
            keep = [BARS_1M_SCHEMA.sort_key] + keep
        resampled = resampled.select(keep)

    return resampled.to_pandas() if as_pandas else resampled


def read_bars_trading_day(
    *,
    symbol: str,
    timeframe: str,
    trading_day: str | dt.date,
    columns: list[str] | None = None,
    as_pandas: bool = True,
    data_root: Path | None = None,
):
    """Read bars over the full Globex trading day labeled `trading_day`."""
    period = _globex_period_for_trading_day(trading_day)
    return read_bars(
        symbol=symbol,
        timeframe=timeframe,
        start=period.start_utc,
        end=period.end_utc,
        columns=columns,
        as_pandas=as_pandas,
        data_root=data_root,
    )


# --- Resample ------------------------------------------------------------


def _resample_bars(table: pa.Table, period: dt.timedelta) -> pa.Table:
    """Group 1m OHLCV bars to a coarser timeframe using pandas.

    Pandas' resample is the boring path that always works for OHLCV
    aggregation (open=first, high=max, low=min, close=last, volume=sum).
    For our scale (a few thousand bars per request) the pandas overhead
    is irrelevant.

    VWAP is genuinely volume-weighted, not a plain mean of the source
    bars (codex review 2026-04-29 caught this regression — the docstring
    said weighted, the code summed sub-bar VWAPs and divided by count).
    Pre-multiplying vwap*volume per source bar and dividing the pool by
    pool volume gives the correct rollup.

    Two edge cases:
      - Pool volume == 0 (halt / outage bucket): fall back to close.
      - Source vwap is NaN with non-zero volume (OHLCV-only imports —
        see ingest/parquet_mirror.py:565 and ingest/legacy_ohlcv_import
        .py:156, which intentionally write NaN). Without handling, the
        NaN propagates as 0 through pandas `sum`, yielding a bogus
        resampled VWAP of 0 even though the bar traded real volume.
        Substitute close for NaN VWAP before weighting — for OHLCV
        bars the resampled VWAP becomes the volume-weighted close,
        which is the best single-price proxy we have.
    """
    df = table.to_pandas().set_index("ts_event")
    vwap_filled = df["vwap"].fillna(df["close"])
    df = df.assign(_vwap_x_volume=vwap_filled * df["volume"])
    rule = _timedelta_to_pandas_rule(period)
    grouped = df.groupby([df["symbol"], df.index.floor(rule)]).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        trade_count=("trade_count", "sum"),
        _vwap_x_volume=("_vwap_x_volume", "sum"),
    )
    safe_volume = grouped["volume"].where(grouped["volume"] > 0)
    grouped["vwap"] = (grouped["_vwap_x_volume"] / safe_volume).fillna(
        grouped["close"]
    )
    grouped = grouped.drop(columns=["_vwap_x_volume"])
    grouped = grouped.reset_index()
    # `level_1` is the floored timestamp from the second groupby key.
    grouped = grouped.rename(columns={"level_1": "ts_event"})
    grouped = grouped.sort_values(["symbol", "ts_event"]).reset_index(drop=True)
    # Force types match BARS_1M_SCHEMA expectations (volume uint64 etc.).
    return pa.Table.from_pandas(
        grouped[
            [
                "ts_event",
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "trade_count",
                "vwap",
            ]
        ],
        preserve_index=False,
    )


_PANDAS_RULES = {
    dt.timedelta(minutes=1): "1min",
    dt.timedelta(minutes=2): "2min",
    dt.timedelta(minutes=3): "3min",
    dt.timedelta(minutes=5): "5min",
    dt.timedelta(minutes=10): "10min",
    dt.timedelta(minutes=15): "15min",
    dt.timedelta(minutes=30): "30min",
    dt.timedelta(hours=1): "1h",
    dt.timedelta(minutes=90): "90min",
    dt.timedelta(hours=2): "2h",
    dt.timedelta(hours=4): "4h",
    dt.timedelta(hours=6): "6h",
    dt.timedelta(days=1): "1D",
}


def _timedelta_to_pandas_rule(td: dt.timedelta) -> str:
    rule = _PANDAS_RULES.get(td)
    if rule is None:
        raise ValueError(f"no pandas resample rule for {td}")
    return rule


# --- Convenience: derived columns ---------------------------------------


def add_mid_and_spread(table: pa.Table) -> pa.Table:
    """Append `mid_px` and `spread` columns to a TBBO/MBP-1 table.

    These columns are intentionally NOT stored on disk — the storage
    schema keeps only `bid_px` and `ask_px`. Compute at read time via
    this helper when callers need them.
    """
    if "bid_px" not in table.column_names or "ask_px" not in table.column_names:
        raise ValueError("table missing bid_px/ask_px; can't compute mid/spread")
    bid = table["bid_px"]
    ask = table["ask_px"]
    mid = pc.divide(pc.add(bid, ask), pa.scalar(2.0))
    spread = pc.subtract(ask, bid)
    return table.append_column("mid_px", mid).append_column("spread", spread)
