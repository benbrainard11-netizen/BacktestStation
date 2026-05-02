"""Public reader API for the bsdata client.

Wraps `app.data.reader` from the BacktestStation backend so collaborator
code can call `load_bars(...)` with the same signature it would use on
ben-247, but data flows R2 → local cache → reader instead of from local
disk directly.

Tier 1 design note: this module imports `app.data.reader` directly. That
means collaborators need the BacktestStation repo on their machine to
install bsdata (`pip install -e ./backend ./client/bsdata`). It's
deliberate — a single parquet-reading codepath everywhere makes schema
drift between Ben's machine and Husky's machine impossible. Tier 2
(when productizing) would publish bsdata standalone with vendored schema
definitions.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from bsdata.cache import ensure_cached


def _bars_partition_root(timeframe: str) -> str:
    return f"processed/bars/timeframe={timeframe}"


def _raw_partition_root(schema: str) -> str:
    return f"raw/databento/{schema}"


def _date_range(start: str | dt.date, end: str | dt.date) -> list[dt.date]:
    """Half-open [start, end). Mirrors app.data.reader._date_range."""
    s = _parse_date(start)
    e = _parse_date(end)
    out: list[dt.date] = []
    cur = s
    while cur < e:
        out.append(cur)
        cur = cur + dt.timedelta(days=1)
    return out


def _parse_date(value: str | dt.date | dt.datetime) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(value)


def load_bars(
    *,
    symbol: str,
    start: str | dt.date,
    end: str | dt.date,
    timeframe: str = "1m",
    columns: list[str] | None = None,
    as_pandas: bool = True,
) -> Any:
    """Load OHLCV bars for `symbol` over [start, end). R2 + local cache."""
    from app.data.reader import read_bars

    dates = _date_range(start, end)
    cache_root = ensure_cached(
        partition_root=_bars_partition_root("1m"),
        symbol=symbol,
        dates=dates,
    )
    return read_bars(
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        columns=columns,
        as_pandas=as_pandas,
        data_root=cache_root,
    )


def load_tbbo(
    *,
    symbol: str,
    start: str | dt.date,
    end: str | dt.date,
    columns: list[str] | None = None,
    as_pandas: bool = True,
) -> Any:
    """Load TBBO records for `symbol` over [start, end). R2 + local cache."""
    from app.data.reader import read_tbbo

    dates = _date_range(start, end)
    cache_root = ensure_cached(
        partition_root=_raw_partition_root("tbbo"),
        symbol=symbol,
        dates=dates,
    )
    return read_tbbo(
        symbol=symbol,
        start=start,
        end=end,
        columns=columns,
        as_pandas=as_pandas,
        data_root=cache_root,
    )


def load_mbp1(
    *,
    symbol: str,
    start: str | dt.date,
    end: str | dt.date,
    columns: list[str] | None = None,
    as_pandas: bool = True,
) -> Any:
    """Load MBP-1 records for `symbol` over [start, end). R2 + local cache."""
    from app.data.reader import read_mbp1

    dates = _date_range(start, end)
    cache_root = ensure_cached(
        partition_root=_raw_partition_root("mbp-1"),
        symbol=symbol,
        dates=dates,
    )
    return read_mbp1(
        symbol=symbol,
        start=start,
        end=end,
        columns=columns,
        as_pandas=as_pandas,
        data_root=cache_root,
    )
