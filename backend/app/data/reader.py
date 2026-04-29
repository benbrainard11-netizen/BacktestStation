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
import os
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from app.data.schema import (
    BARS_1M_SCHEMA,
    MBP1_SCHEMA,
    SCHEMA_BY_NAME,
    TBBO_SCHEMA,
    DataSchema,
)

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
    "2h": dt.timedelta(hours=2),
    "4h": dt.timedelta(hours=4),
    "1d": dt.timedelta(days=1),
}


# --- Path helpers --------------------------------------------------------


def _data_root() -> Path:
    default = "C:/data" if os.name == "nt" else "./data"
    return Path(os.environ.get("BS_DATA_ROOT", default))


def _raw_partition_root(data_root: Path, schema: str) -> Path:
    return data_root / "raw" / "databento" / schema


def _bars_partition_root(data_root: Path, timeframe: str) -> Path:
    return data_root / "processed" / "bars" / f"timeframe={timeframe}"


# --- Date helpers --------------------------------------------------------


def _parse_date(value: str | dt.date | dt.datetime) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(value)


def _date_range(start: dt.date, end: dt.date) -> list[dt.date]:
    """Half-open [start, end). Empty list if end <= start."""
    out: list[dt.date] = []
    cur = start
    while cur < end:
        out.append(cur)
        cur = cur + dt.timedelta(days=1)
    return out


# --- Core reader ---------------------------------------------------------


def _read_partitioned(
    root: Path,
    *,
    symbol: str,
    dates: list[dt.date],
    schema: DataSchema,
    columns: list[str] | None,
) -> pa.Table:
    """Read all matching partition files into one pyarrow Table."""
    paths = []
    for d in dates:
        candidate = (
            root
            / f"symbol={symbol}"
            / f"date={d.isoformat()}"
            / "part-000.parquet"
        )
        if candidate.exists():
            paths.append(candidate)
        else:
            logger.info(
                f"missing partition: symbol={symbol} date={d} "
                f"(expected {candidate})"
            )

    if not paths:
        return schema.pa_schema.empty_table()

    dataset = ds.dataset(paths, format="parquet")
    if columns is not None:
        # Always include the sort key so users can filter even if they
        # didn't request it — common ergonomic surprise otherwise.
        if schema.sort_key not in columns:
            columns = [schema.sort_key] + list(columns)
    table = dataset.to_table(columns=columns)
    return table


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
    root = data_root or _data_root()
    start_d = _parse_date(start)
    end_d = _parse_date(end)
    dates = _date_range(start_d, end_d)
    table = _read_partitioned(
        _raw_partition_root(root, "tbbo"),
        symbol=symbol,
        dates=dates,
        schema=TBBO_SCHEMA,
        columns=columns,
    )
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
    root = data_root or _data_root()
    dates = _date_range(_parse_date(start), _parse_date(end))
    table = _read_partitioned(
        _raw_partition_root(root, "mbp-1"),
        symbol=symbol,
        dates=dates,
        schema=MBP1_SCHEMA,
        columns=columns,
    )
    return table.to_pandas() if as_pandas else table


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

    Supported timeframes: 1m, 2m, 3m, 5m, 10m, 15m, 30m, 1h, 2h, 4h, 1d.
    """
    if timeframe not in _BAR_TIMEFRAMES:
        known = ", ".join(_BAR_TIMEFRAMES.keys())
        raise ValueError(f"unknown timeframe {timeframe!r}; known: {known}")

    root = data_root or _data_root()
    dates = _date_range(_parse_date(start), _parse_date(end))
    base = _read_partitioned(
        _bars_partition_root(root, "1m"),
        symbol=symbol,
        dates=dates,
        schema=BARS_1M_SCHEMA,
        columns=None,  # need full set for resampling; project at the end
    )

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
    dt.timedelta(hours=2): "2h",
    dt.timedelta(hours=4): "4h",
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
