"""Swing pivot reactions outcome computer (v1).

For each swing pivot event, captures:

1. **breakout** — did a forward bar wick BEYOND the pivot price?
   When? How deep? (= "swing got taken / liquidity grabbed")
     - wick_taken: any bar wicked past pivot
     - close_taken: any bar closed past pivot (cleaner break)
     - bars_to_wick / bars_to_close

2. **forward_3/10/50_candles** — MFE/MAE measured FROM the pivot bar's
   close, oriented AGAINST pivot direction (the trade idea: swing high
   → expect price to retrace down; swing low → expect retrace up).
   Bullish thesis (swing low) — same as previous outcomes computers.

3. **bars_to_extreme** — how many bars later did price reach its
   farthest move in the AGAINST-pivot direction (i.e., the "thesis"
   direction)? Useful for distinguishing fast vs slow rotations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import pandas as pd

from app.db.models import ResearchEvent
from app.research.outcomes import BarReader, register

UTC = timezone.utc
log = logging.getLogger(__name__)


_TIMEFRAME_FOR_MODE: dict[str, tuple[str, int]] = {
    "pivot_3_1h":   ("1h", 60),
    "pivot_5_1h":   ("1h", 60),
    "pivot_3_4h":   ("4h", 240),
    "pivot_5_4h":   ("4h", 240),
    "pivot_5_daily": ("1d", 24 * 60),
}

_FORWARD_WINDOWS: tuple[int, ...] = (3, 10, 50)
_MAX_FORWARD = max(_FORWARD_WINDOWS)


class SwingPivotReactionsComputer:
    feature_name: str = "swing_pivot"
    outcome_version: str = "v1"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        if event.event_type not in _TIMEFRAME_FOR_MODE:
            log.warning(
                "swing_reactions: unknown event_type %s (id=%s)",
                event.event_type, event.id,
            )
            return None
        if event.side not in ("high", "low"):
            log.warning(
                "swing_reactions: bad side %r (id=%s)", event.side, event.id,
            )
            return None

        ed = event.event_data or {}
        try:
            n = int(ed["n"])
            pivot_price = float(ed["pivot_price"])
            pivot_close = float(ed["pivot_bar"]["close"])
        except (KeyError, TypeError, ValueError):
            return None

        side: Literal["high", "low"] = event.side  # type: ignore[assignment]

        timeframe_native, minutes_per_candle = _TIMEFRAME_FOR_MODE[event.event_type]
        # The pivot is "knowable" only after N bars to the right have closed.
        # Forward bars = AFTER the right-confirmation period.
        bucket_start = _ensure_utc(event.bar_end_utc)
        forward_start = bucket_start + timedelta(minutes=minutes_per_candle * (n + 1))
        forward_window_minutes = minutes_per_candle * (_MAX_FORWARD + 25) + 60

        forward = _load_forward_bars(
            bar_reader,
            symbol=event.primary_symbol,
            timeframe=timeframe_native,
            start_utc=forward_start,
            end_utc=forward_start + timedelta(minutes=forward_window_minutes),
        )
        if forward is None or forward.empty:
            return None
        forward = forward.iloc[:_MAX_FORWARD]

        # Thesis direction: swing high → expect down; swing low → expect up.
        thesis: Literal["bullish", "bearish"] = "bearish" if side == "high" else "bullish"

        # Breakout: wick / close past pivot in PIVOT direction (against thesis).
        # Swing high broken = bar.high > pivot_price (close > pivot_price = clean break).
        # Swing low broken  = bar.low < pivot_price (close < pivot_price).
        breakout = _compute_breakout(forward, pivot_price=pivot_price, side=side)

        forward_blocks: dict[str, dict[str, Any]] = {}
        for w in _FORWARD_WINDOWS:
            forward_blocks[f"forward_{w}_candles"] = _excursion(
                forward.iloc[:w],
                reference_close=pivot_close,
                direction=thesis,
            )

        # bars_to_extreme: bar index of the MFE-in-thesis-direction high
        # within the 50-bar window.
        extreme = _bars_to_extreme(forward, pivot_close=pivot_close, thesis=thesis)

        return {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "thesis_direction": "up" if thesis == "bullish" else "down",
            "pivot_price": pivot_price,
            "reference_close": pivot_close,
            "breakout": breakout,
            "extreme": extreme,
            **forward_blocks,
        }


# ---------- helpers ----------


def _compute_breakout(
    forward: pd.DataFrame,
    *,
    pivot_price: float,
    side: Literal["high", "low"],
) -> dict[str, Any]:
    """Did a forward bar wick / close past the pivot price?
    Swing high: wick_taken = bar.high > pivot. close_taken = bar.close > pivot.
    Swing low: wick_taken = bar.low < pivot. close_taken = bar.close < pivot.
    """
    bars_to_wick: int | None = None
    bars_to_close: int | None = None
    deepest_breakout_pts: float = 0.0
    for idx, (_, bar) in enumerate(forward.iterrows(), start=1):
        bar_high = float(bar["high"])
        bar_low = float(bar["low"])
        bar_close = float(bar["close"])
        if side == "high":
            if bar_high > pivot_price:
                if bars_to_wick is None:
                    bars_to_wick = idx
                depth = bar_high - pivot_price
                if depth > deepest_breakout_pts:
                    deepest_breakout_pts = depth
            if bars_to_close is None and bar_close > pivot_price:
                bars_to_close = idx
        else:
            if bar_low < pivot_price:
                if bars_to_wick is None:
                    bars_to_wick = idx
                depth = pivot_price - bar_low
                if depth > deepest_breakout_pts:
                    deepest_breakout_pts = depth
            if bars_to_close is None and bar_close < pivot_price:
                bars_to_close = idx
    return {
        "wick_taken": bars_to_wick is not None,
        "close_taken": bars_to_close is not None,
        "bars_to_wick": bars_to_wick,
        "bars_to_close": bars_to_close,
        "deepest_breakout_pts": float(deepest_breakout_pts),
    }


def _bars_to_extreme(
    forward: pd.DataFrame,
    *,
    pivot_close: float,
    thesis: Literal["bullish", "bearish"],
) -> dict[str, Any]:
    if forward.empty:
        return {"bars_to_extreme": None, "extreme_pts": None}
    if thesis == "bullish":
        extremes = forward["high"].to_numpy()
        diffs = extremes - pivot_close
    else:
        extremes = forward["low"].to_numpy()
        diffs = pivot_close - extremes
    if len(diffs) == 0:
        return {"bars_to_extreme": None, "extreme_pts": None}
    max_idx = int(diffs.argmax())
    return {
        "bars_to_extreme": int(max_idx + 1),
        "extreme_pts": float(diffs[max_idx]),
    }


def _excursion(
    bars: pd.DataFrame,
    *,
    reference_close: float,
    direction: Literal["bullish", "bearish"],
) -> dict[str, Any]:
    if bars.empty:
        return _empty_excursion()
    win_high = float(bars["high"].max())
    win_low = float(bars["low"].min())
    last_close = float(bars["close"].iloc[-1])
    if direction == "bullish":
        mfe_pts = win_high - reference_close
        mae_pts = reference_close - win_low
    else:
        mfe_pts = reference_close - win_low
        mae_pts = win_high - reference_close
    return {
        "n_bars": int(len(bars)),
        "reference_close": reference_close,
        "window_high": win_high,
        "window_low": win_low,
        "last_close": last_close,
        "mfe_pts_in_thesis": float(mfe_pts),
        "mae_pts_against_thesis": float(mae_pts),
    }


def _empty_excursion() -> dict[str, Any]:
    return {
        "n_bars": 0,
        "reference_close": None,
        "window_high": None,
        "window_low": None,
        "last_close": None,
        "mfe_pts_in_thesis": None,
        "mae_pts_against_thesis": None,
    }


def _load_forward_bars(
    bar_reader: BarReader,
    *, symbol: str, timeframe: str,
    start_utc: datetime, end_utc: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(symbol=symbol, timeframe=timeframe,
                        start=start_utc, end=end_utc + timedelta(days=1))
    except (FileNotFoundError, ValueError) as exc:
        log.info("swing_reactions: bar_reader missing %s %s: %s", symbol, timeframe, exc)
        return None
    if df is None or len(df) == 0:
        return None
    df = _normalize_index(df)
    sliced = df.loc[df.index >= start_utc]
    return sliced if not sliced.empty else None


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


def _ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


# ---------- registration ----------

register("swing_pivot_reactions_v1", SwingPivotReactionsComputer())
