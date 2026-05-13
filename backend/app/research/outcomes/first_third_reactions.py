"""First-third range reactions outcome computer (v1).

For each first_third_range event, captures what price did during the
REMAINING 2/3 of the parent candle period:

1. **break_high** — did a 1m bar's high go above first_third_high?
   When? Did a 1m bar CLOSE above? Deepest extension (in pts and as
   1× / 0.5× range multiplier).

2. **break_low** — symmetric for below first_third_low.

3. **rest_of_candle** — direction of the parent candle as a whole
   (close vs first_third_open) and as the rest-of-candle (close vs
   first_third_close). Did the rest of the candle CONFIRM the
   first-third direction or REVERSE it?

4. **excursion_extensions** — track whether wick or close went past
   the 0.5× and 1× range extensions (Ben's "1sd above 1/3 range"
   style flags).

Reference price for excursion = first_third_close (the price you'd
"see" at the moment the first-third range is knowable).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from app.db.models import ResearchEvent
from app.research.outcomes import BarReader, register

UTC = timezone.utc
log = logging.getLogger(__name__)


_TIMEFRAME = "1m"


class FirstThirdReactionsComputer:
    feature_name: str = "first_third_range"
    outcome_version: str = "v1"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        ed = event.event_data or {}
        try:
            ft_high = float(ed["first_third_high"])
            ft_low = float(ed["first_third_low"])
            ft_open = float(ed["first_third_open"])
            ft_close = float(ed["first_third_close"])
            ft_range = float(ed["first_third_range_pts"])
            parent_end = datetime.fromisoformat(ed["parent_period_end_utc"])
            ft_end = datetime.fromisoformat(ed["first_third_end_utc"])
        except (KeyError, TypeError, ValueError):
            return None
        if ft_range <= 0:
            return None

        # The "rest of candle" window = [first_third_end, parent_end).
        # Load 1m bars over that window, padded for date-partition.
        rest = _load_bars(
            bar_reader,
            symbol=event.primary_symbol,
            timeframe=_TIMEFRAME,
            start=ft_end,
            end=parent_end + timedelta(days=1),
        )
        if rest is None or rest.empty:
            return None
        rest = rest[(rest.index >= ft_end) & (rest.index < parent_end)]
        if rest.empty:
            return None

        ext_high_05 = ft_high + 0.5 * ft_range
        ext_high_1 = ft_high + 1.0 * ft_range
        ext_low_05 = ft_low - 0.5 * ft_range
        ext_low_1 = ft_low - 1.0 * ft_range

        # Break above first_third_high: when did bar.high go above? when did bar.close?
        break_high = _first_breach(rest, level=ft_high, direction="up")
        break_high_05ext = _first_breach(rest, level=ext_high_05, direction="up")
        break_high_1ext = _first_breach(rest, level=ext_high_1, direction="up")
        break_low = _first_breach(rest, level=ft_low, direction="down")
        break_low_05ext = _first_breach(rest, level=ext_low_05, direction="down")
        break_low_1ext = _first_breach(rest, level=ext_low_1, direction="down")

        rest_high = float(rest["high"].max())
        rest_low = float(rest["low"].min())
        rest_close = float(rest["close"].iloc[-1])

        # Direction summaries.
        # parent_direction = close vs first_third_open
        if rest_close > ft_open:
            parent_direction = "bullish"
        elif rest_close < ft_open:
            parent_direction = "bearish"
        else:
            parent_direction = "doji"
        # rest_direction = close vs first_third_close
        if rest_close > ft_close:
            rest_direction = "bullish"
        elif rest_close < ft_close:
            rest_direction = "bearish"
        else:
            rest_direction = "doji"
        ft_direction = ed.get("first_third_direction", "doji")
        rest_confirms_ft = (
            rest_direction == ft_direction
            and ft_direction in ("bullish", "bearish")
        )
        rest_reverses_ft = (
            rest_direction != ft_direction
            and rest_direction in ("bullish", "bearish")
            and ft_direction in ("bullish", "bearish")
        )

        return {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "reference_close": ft_close,
            "first_third_direction": ft_direction,
            "parent_direction": parent_direction,
            "rest_direction": rest_direction,
            "rest_confirms_first_third": rest_confirms_ft,
            "rest_reverses_first_third": rest_reverses_ft,
            "rest_window_high": rest_high,
            "rest_window_low": rest_low,
            "rest_window_close": rest_close,
            "rest_n_bars": int(len(rest)),
            "break_high": break_high,
            "break_high_05ext": break_high_05ext,
            "break_high_1ext": break_high_1ext,
            "break_low": break_low,
            "break_low_05ext": break_low_05ext,
            "break_low_1ext": break_low_1ext,
            "deepest_above_pts": float(max(0.0, rest_high - ft_high)),
            "deepest_below_pts": float(max(0.0, ft_low - rest_low)),
            "deepest_above_range_mult": (
                float((rest_high - ft_high) / ft_range) if rest_high > ft_high else 0.0
            ),
            "deepest_below_range_mult": (
                float((ft_low - rest_low) / ft_range) if rest_low < ft_low else 0.0
            ),
        }


# ---------- helpers ----------


def _first_breach(
    bars: pd.DataFrame,
    *,
    level: float,
    direction: str,  # "up" or "down"
) -> dict[str, Any]:
    """Find first bar whose wick crossed the level, and first that closed past it."""
    bar_idx_wick: int | None = None
    bar_idx_close: int | None = None
    ts_wick: datetime | None = None
    ts_close: datetime | None = None
    for idx, (ts, bar) in enumerate(bars.iterrows(), start=1):
        h = float(bar["high"])
        low_v = float(bar["low"])
        c = float(bar["close"])
        if direction == "up":
            if bar_idx_wick is None and h > level:
                bar_idx_wick = idx
                ts_wick = ts
            if bar_idx_close is None and c > level:
                bar_idx_close = idx
                ts_close = ts
        else:
            if bar_idx_wick is None and low_v < level:
                bar_idx_wick = idx
                ts_wick = ts
            if bar_idx_close is None and c < level:
                bar_idx_close = idx
                ts_close = ts
        if bar_idx_wick is not None and bar_idx_close is not None:
            break
    return {
        "wick_breached": bar_idx_wick is not None,
        "close_past": bar_idx_close is not None,
        "bar_index_wick": bar_idx_wick,
        "bar_index_close": bar_idx_close,
        "ts_wick": ts_wick.isoformat() if isinstance(ts_wick, (datetime, pd.Timestamp)) else None,
        "ts_close": ts_close.isoformat() if isinstance(ts_close, (datetime, pd.Timestamp)) else None,
    }


def _load_bars(
    bar_reader: BarReader,
    *, symbol: str, timeframe: str,
    start: datetime, end: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(symbol=symbol, timeframe=timeframe,
                        start=start, end=end + timedelta(days=1))
    except (FileNotFoundError, ValueError) as exc:
        log.info("first_third_react: bar_reader missing %s %s: %s",
                 symbol, timeframe, exc)
        return None
    if df is None or len(df) == 0:
        return None
    df = _normalize_index(df)
    return df


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


# ---------- registration ----------

register("first_third_reactions_v1", FirstThirdReactionsComputer())
