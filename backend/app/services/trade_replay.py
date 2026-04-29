"""Service for the /trade-replay feature.

Two responsibilities:
1. `tbbo_partition_exists` — check if the on-disk TBBO partition for a
   (symbol, date) pair exists. Used by the picker to flag which trades
   are replayable today.
2. `load_trade_window` — load TBBO ticks for one trade's date and slice
   to a [entry_ts - lead, exit_ts + trail] window. Caps lead/trail to
   30 minutes each side so payloads stay bounded.

The reader (`read_tbbo`) loads a full day's partition — there's no
sub-day filtering at the parquet layer. We slice in pandas after load.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

LEAD_DEFAULT_SECONDS = 300
TRAIL_DEFAULT_SECONDS = 300
LEAD_MAX_SECONDS = 1800
TRAIL_MAX_SECONDS = 1800


def _data_root_default() -> Path:
    """Backwards-compat alias for `app.core.paths.warehouse_root`."""
    from app.core.paths import warehouse_root
    return warehouse_root()


def _tbbo_partition_path(data_root: Path, symbol: str, date: dt.date) -> Path:
    return (
        data_root
        / "raw"
        / "databento"
        / "tbbo"
        / f"symbol={symbol}"
        / f"date={date.isoformat()}"
    )


def tbbo_partition_exists(
    *,
    symbol: str,
    date: dt.date,
    data_root: Path | None = None,
) -> bool:
    """True if the TBBO partition directory for (symbol, date) exists and
    has at least one parquet file in it.

    Used by the picker: a trade with `tbbo_available=False` is rendered
    disabled. Cheap directory check — no parquet read.
    """
    root = data_root or _data_root_default()
    part_dir = _tbbo_partition_path(root, symbol, date)
    if not part_dir.is_dir():
        return False
    return any(part_dir.glob("*.parquet"))


def clamp_lead(lead_seconds: int) -> int:
    if lead_seconds < 0:
        return 0
    return min(lead_seconds, LEAD_MAX_SECONDS)


def clamp_trail(trail_seconds: int) -> int:
    if trail_seconds < 0:
        return 0
    return min(trail_seconds, TRAIL_MAX_SECONDS)


def compute_window(
    entry_ts: dt.datetime,
    exit_ts: dt.datetime | None,
    lead_seconds: int,
    trail_seconds: int,
) -> tuple[dt.datetime, dt.datetime]:
    """Return (window_start, window_end) for a trade.

    If `exit_ts` is None (open trade), trail extends from entry_ts.
    """
    lead = clamp_lead(lead_seconds)
    trail = clamp_trail(trail_seconds)
    window_start = entry_ts - dt.timedelta(seconds=lead)
    anchor_end = exit_ts if exit_ts is not None else entry_ts
    window_end = anchor_end + dt.timedelta(seconds=trail)
    return window_start, window_end


def load_trade_window(
    *,
    symbol: str,
    entry_ts: dt.datetime,
    exit_ts: dt.datetime | None,
    lead_seconds: int = LEAD_DEFAULT_SECONDS,
    trail_seconds: int = TRAIL_DEFAULT_SECONDS,
    data_root: Path | None = None,
) -> tuple[dt.datetime, dt.datetime, "pd.DataFrame"]:
    """Load TBBO ticks for the trade's date(s) and slice to the window.

    Returns (window_start, window_end, ticks_df). Empty DataFrame if the
    partition has no rows in the window. Caller is responsible for
    checking `tbbo_partition_exists` first — this function will return
    an empty df rather than 404 on missing partitions, since
    cross-midnight windows may legitimately straddle a missing date.

    The reader returns timestamps as tz-aware UTC pandas Timestamps;
    `entry_ts`/`exit_ts` from the DB are tz-naive UTC. We localize the
    naive timestamps to UTC for comparison so we don't get a tz-mismatch
    error inside pandas.
    """
    from app.data import read_tbbo  # local import: keeps tests import-light

    window_start, window_end = compute_window(
        entry_ts, exit_ts, lead_seconds, trail_seconds
    )

    # read_tbbo's `end` is exclusive at day granularity. Add 1 day to make
    # sure cross-midnight windows are covered.
    start_date = window_start.date()
    end_date_exclusive = window_end.date() + dt.timedelta(days=1)

    df = read_tbbo(
        symbol=symbol,
        start=start_date,
        end=end_date_exclusive,
        as_pandas=True,
        data_root=data_root,
    )

    if df is None or len(df) == 0:
        import pandas as pd

        return window_start, window_end, pd.DataFrame()

    # `ts_event` from the parquet schema is `timestamp[ns, UTC]` →
    # tz-aware UTC pandas Timestamps. DB timestamps are tz-naive UTC.
    # Localize the bounds for direct comparison.
    import pandas as pd

    ws_pd = pd.Timestamp(window_start).tz_localize("UTC")
    we_pd = pd.Timestamp(window_end).tz_localize("UTC")

    mask = (df["ts_event"] >= ws_pd) & (df["ts_event"] <= we_pd)
    return window_start, window_end, df.loc[mask].reset_index(drop=True)
