"""Reference price levels over a time period.

A "reference level" is a high or low computed over a bounded period —
e.g. previous-week high, previous-day low. Used by SMT detectors and
any future detector that triggers on price taking out a known prior
level.

Pure functions; pandas DataFrame input.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import pandas as pd

Side = Literal["high", "low"]


@dataclass(frozen=True, slots=True)
class ReferenceLevel:
    """A high or low observed over a period.

    `value` is the price (max for high side, min for low side).
    `ts_utc` is the timestamp of the bar that set the level — useful
    for downstream "did price retest the SAME bar that made the high"
    questions.
    `n_bars` is how many bars went into the calculation; lets callers
    detect under-sampled periods.
    """

    side: Side
    value: float
    ts_utc: datetime
    n_bars: int


def compute_reference_level(
    bars: pd.DataFrame,
    *,
    side: Side,
    start_utc: datetime,
    end_utc: datetime,
    high_col: str = "high",
    low_col: str = "low",
    ts_col: str | None = None,
) -> ReferenceLevel | None:
    """Compute the high or low of `bars` within `[start_utc, end_utc)`.

    Args:
        bars: DataFrame of OHLCV bars. Index must be tz-aware UTC
            DatetimeIndex unless `ts_col` is provided (in which case
            that column is used as the timestamp).
        side: "high" picks max(`high_col`), "low" picks min(`low_col`).
        start_utc / end_utc: half-open interval `[start, end)`.
        high_col, low_col: column names. Default "high" / "low".
        ts_col: name of an explicit timestamp column. If None, the
            DataFrame's index is used.

    Returns:
        A `ReferenceLevel` with `value`, `ts_utc` (the bar that set
        it), and `n_bars` (slice size). Returns None if no bars fall
        in the period.

    Edge cases:
        - Tie: if multiple bars share the extreme value, the FIRST
          one (earliest ts) wins. Stable + deterministic.
        - Empty period: returns None. Caller decides whether that
          means "no reference yet" or "data gap."
    """
    if bars.empty:
        return None

    if ts_col is not None:
        ts = bars[ts_col]
    else:
        ts = bars.index

    # Half-open mask
    mask = (ts >= start_utc) & (ts < end_utc)
    sliced = bars.loc[mask]
    if sliced.empty:
        return None

    if side == "high":
        col = sliced[high_col]
        idx_of_extreme = col.idxmax()
        value = float(col.loc[idx_of_extreme])
    else:
        col = sliced[low_col]
        idx_of_extreme = col.idxmin()
        value = float(col.loc[idx_of_extreme])

    if ts_col is not None:
        ts_of_extreme = sliced.loc[idx_of_extreme, ts_col]
    else:
        ts_of_extreme = idx_of_extreme

    if not isinstance(ts_of_extreme, pd.Timestamp):
        ts_of_extreme = pd.Timestamp(ts_of_extreme)

    return ReferenceLevel(
        side=side,
        value=value,
        ts_utc=ts_of_extreme.to_pydatetime(),
        n_bars=int(len(sliced)),
    )
