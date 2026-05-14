"""Shared forward-reaction label helpers.

These functions only consume bars after an anchor is knowable. They are safe
for outcome generation, but their outputs are labels and must not be used as
model features.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


def direction_from_delta(value: float) -> str:
    """Return a stable direction label for close/reference deltas."""
    return "up" if value > 0 else "down" if value < 0 else "flat"


def add_reference_price_reaction(
    out: dict[str, Any],
    *,
    high: float,
    low: float,
    close: float,
    reference_price: float,
    direction_key: str = "direction",
) -> None:
    """Add close and wick behavior relative to a single reference price."""
    return_pts = close - reference_price
    out["return_pts"] = float(return_pts)
    out["abs_return_pts"] = float(abs(return_pts))
    out[direction_key] = direction_from_delta(return_pts)
    out["mfe_up_pts"] = float(high - reference_price)
    out["mfe_down_pts"] = float(reference_price - low)
    out["close_above_reference"] = bool(close > reference_price)
    out["close_below_reference"] = bool(close < reference_price)
    out["wicked_above_ref_closed_below_ref"] = bool(high > reference_price and close < reference_price)
    out["wicked_below_ref_closed_above_ref"] = bool(low < reference_price and close > reference_price)


def add_first_bar_reaction(
    out: dict[str, Any],
    *,
    first_close: float,
    final_close: float,
    reference_price: float,
) -> None:
    """Add first-bar impulse/reversal labels relative to the anchor reference."""
    first_return_pts = first_close - reference_price
    final_return_pts = final_close - reference_price
    first_direction = direction_from_delta(first_return_pts)
    final_direction = direction_from_delta(final_return_pts)
    out["first_bar_close"] = float(first_close)
    out["first_bar_return_pts"] = float(first_return_pts)
    out["first_bar_direction"] = first_direction
    out["first_bar_up_then_final_down"] = bool(first_return_pts > 0 and final_return_pts < 0)
    out["first_bar_down_then_final_up"] = bool(first_return_pts < 0 and final_return_pts > 0)
    out["direction_reversed_from_first_bar"] = bool(
        first_direction != "flat" and final_direction != "flat" and first_direction != final_direction
    )


def add_range_reaction(
    out: dict[str, Any],
    *,
    high: float,
    low: float,
    close: float,
    range_pts: float,
    anchor_high: float,
    anchor_low: float,
    prefix: str,
) -> None:
    """Add standardized labels for reacting to a prior range/zone."""
    anchor_range = float(anchor_high - anchor_low)
    if anchor_range <= 0:
        out[f"range_vs_{prefix}"] = None
        out[f"close_location_vs_{prefix}"] = None
        for suffix in _RANGE_BOOL_SUFFIXES:
            out[f"{suffix}_{prefix}"] = False
        out[f"took_{prefix}_high"] = False
        out[f"took_{prefix}_low"] = False
        out[f"swept_both_{prefix}_sides"] = False
        out[f"closed_above_{prefix}_high"] = False
        out[f"closed_below_{prefix}_low"] = False
        out[f"closed_inside_{prefix}_range"] = False
        out[f"closed_outside_{prefix}_range"] = False
        out[f"one_sided_took_{prefix}_high"] = False
        out[f"one_sided_took_{prefix}_low"] = False
        out[f"took_{prefix}_high_held_above"] = False
        out[f"took_{prefix}_low_held_below"] = False
        out[f"took_{prefix}_high_rejected_inside"] = False
        out[f"took_{prefix}_low_rejected_inside"] = False
        out[f"swept_both_{prefix}_closed_inside"] = False
        out[f"swept_both_{prefix}_closed_above"] = False
        out[f"swept_both_{prefix}_closed_below"] = False
        return

    took_high = bool(high > anchor_high)
    took_low = bool(low < anchor_low)
    closed_above = bool(close > anchor_high)
    closed_below = bool(close < anchor_low)
    closed_inside = bool(anchor_low <= close <= anchor_high)
    out[f"range_vs_{prefix}"] = float(range_pts / anchor_range)
    out[f"close_location_vs_{prefix}"] = float((close - anchor_low) / anchor_range)
    out[f"range_expanded_1x_{prefix}"] = bool(range_pts >= anchor_range)
    out[f"range_expanded_2x_{prefix}"] = bool(range_pts >= 2.0 * anchor_range)
    out[f"took_{prefix}_high"] = took_high
    out[f"took_{prefix}_low"] = took_low
    out[f"swept_both_{prefix}_sides"] = bool(took_high and took_low)
    out[f"closed_above_{prefix}_high"] = closed_above
    out[f"closed_below_{prefix}_low"] = closed_below
    out[f"closed_inside_{prefix}_range"] = closed_inside
    out[f"closed_outside_{prefix}_range"] = bool(closed_above or closed_below)
    out[f"one_sided_took_{prefix}_high"] = bool(took_high and not took_low)
    out[f"one_sided_took_{prefix}_low"] = bool(took_low and not took_high)
    out[f"took_{prefix}_high_held_above"] = bool(took_high and closed_above)
    out[f"took_{prefix}_low_held_below"] = bool(took_low and closed_below)
    out[f"took_{prefix}_high_rejected_inside"] = bool(took_high and closed_inside)
    out[f"took_{prefix}_low_rejected_inside"] = bool(took_low and closed_inside)
    out[f"swept_both_{prefix}_closed_inside"] = bool(took_high and took_low and closed_inside)
    out[f"swept_both_{prefix}_closed_above"] = bool(took_high and took_low and closed_above)
    out[f"swept_both_{prefix}_closed_below"] = bool(took_high and took_low and closed_below)


def bar_window_summary(
    bars: pd.DataFrame,
    *,
    window_start: datetime,
    window_end: datetime,
) -> dict[str, Any] | None:
    """Return common OHLC window fields for nested outcome labels."""
    if bars.empty:
        return None
    opens = bars["open"].astype(float)
    highs = bars["high"].astype(float)
    lows = bars["low"].astype(float)
    closes = bars["close"].astype(float)
    high = float(highs.max())
    low = float(lows.min())
    close = float(closes.iloc[-1])
    first_open = float(opens.iloc[0])
    return {
        "window_start_utc": window_start.isoformat(),
        "window_end_utc": window_end.isoformat(),
        "n_bars": int(len(bars)),
        "open": first_open,
        "high": high,
        "low": low,
        "close": close,
        "range_pts": float(high - low),
        "body_pts": float(close - first_open),
    }


_RANGE_BOOL_SUFFIXES = (
    "range_expanded_1x",
    "range_expanded_2x",
)
