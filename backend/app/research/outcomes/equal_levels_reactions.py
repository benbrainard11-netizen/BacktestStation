"""Equal Levels reactions outcome computer (v1).

For each equal_levels event, captures whether the level got TAKEN
(price wicked or closed past it) and the reaction afterward.

The level price = the cluster extreme (max for equal highs, min for
equal lows). After the cluster forms, ICT thesis is that price will
draw to this level as a target.

Outcomes:
  - take_status: did wick / close go past the level
  - bars_to_take_wick / bars_to_take_close (in 1h bars)
  - post_take_reaction (forward MFE/MAE FROM the take bar's close, in
    DIRECTION OPPOSITE the level — equal highs taken → expect down)
  - rejection: did the take wick happen with a same-bar reversal close?
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


# Tracking timeframe = 1h regardless of parent pivot timeframe.
# After the equal-level cluster forms, we want to know "when did price
# come back to this level" on a relatively granular tf.
_TIMEFRAME = "1h"
_FORWARD_BARS = 250  # ~10 days at 1h — equal levels can take a while to be taken
_FORWARD_WINDOWS: tuple[int, ...] = (5, 25, 100, 250)


class EqualLevelsReactionsComputer:
    feature_name: str = "equal_levels"
    outcome_version: str = "v1"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        ed = event.event_data or {}
        try:
            level_price = float(ed["level_price"])
            side = ed["side"]
        except (KeyError, TypeError, ValueError):
            return None

        bucket_start = _ensure_utc(event.bar_end_utc)
        forward_window_minutes = 60 * (_FORWARD_BARS + 25) + 60
        forward = _load_forward_bars(
            bar_reader,
            symbol=event.primary_symbol, timeframe=_TIMEFRAME,
            start_utc=bucket_start + timedelta(minutes=60),  # next 1h bar
            end_utc=bucket_start + timedelta(minutes=forward_window_minutes),
        )
        if forward is None or forward.empty:
            return None
        forward = forward.iloc[:_FORWARD_BARS]

        take = _compute_take(forward, level_price=level_price, side=side)

        # Post-take reaction: from the take bar's close, measured AGAINST
        # the level direction (equal highs → expect down; equal lows → up).
        thesis: Literal["bullish", "bearish"] = (
            "bearish" if side == "high" else "bullish"
        )
        post_take_blocks: dict[str, Any] = {}
        if take["bars_to_wick"] is not None:
            tap_idx = take["bars_to_wick"]
            tap_bar = forward.iloc[tap_idx - 1]
            tap_close = float(tap_bar["close"])
            after = forward.iloc[tap_idx:]
            for n in _FORWARD_WINDOWS:
                post_take_blocks[f"forward_{n}_after_take"] = _excursion(
                    after.iloc[:n],
                    reference_close=tap_close,
                    direction=thesis,
                )
            post_take_block = {
                "tap_bar_close": tap_close,
                **post_take_blocks,
            }
        else:
            post_take_block = None

        return {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "level_price": level_price,
            "side": side,
            "thesis_direction": "down" if side == "high" else "up",
            "take": take,
            "post_take_reaction": post_take_block,
            "horizon_bars": int(len(forward)),
        }


# ---------- helpers ----------


def _compute_take(
    forward: pd.DataFrame,
    *, level_price: float, side: str,
) -> dict[str, Any]:
    """Did a forward bar wick / close past the level?"""
    bars_to_wick: int | None = None
    bars_to_close: int | None = None
    deepest_pts: float = 0.0
    same_bar_reversal: bool | None = None  # set if take happened
    for idx, (_, bar) in enumerate(forward.iterrows(), start=1):
        h = float(bar["high"]); l = float(bar["low"])
        c = float(bar["close"]); o = float(bar["open"])
        if side == "high":
            wicked = h > level_price
            closed_past = c > level_price
            depth = max(0.0, h - level_price)
            # Reversal: wicked above but closed below the LEVEL.
            reversal = wicked and not closed_past
        else:
            wicked = l < level_price
            closed_past = c < level_price
            depth = max(0.0, level_price - l)
            reversal = wicked and not closed_past
        if wicked:
            if bars_to_wick is None:
                bars_to_wick = idx
                same_bar_reversal = reversal
            if depth > deepest_pts:
                deepest_pts = depth
        if closed_past and bars_to_close is None:
            bars_to_close = idx
        if bars_to_wick is not None and bars_to_close is not None:
            break
    return {
        "wick_taken": bars_to_wick is not None,
        "close_past": bars_to_close is not None,
        "bars_to_wick": bars_to_wick,
        "bars_to_close": bars_to_close,
        "deepest_pts_past": float(deepest_pts),
        "first_take_was_reversal": same_bar_reversal,
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
        "n_bars": 0, "reference_close": None,
        "window_high": None, "window_low": None,
        "last_close": None, "mfe_pts_in_thesis": None,
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
        log.info("eq_levels_react: bar_reader missing %s %s: %s",
                 symbol, timeframe, exc)
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

register("equal_levels_reactions_v1", EqualLevelsReactionsComputer())
