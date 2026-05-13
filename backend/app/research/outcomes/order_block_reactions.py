"""Order Block reactions outcome computer (v1).

Populates `outcomes` for events written by the `order_block` detector.

What we capture
---------------

For each OB event, two complementary perspectives:

1. **CONTINUATION from confirmation close.** Did price keep moving in
   the OB direction without first tapping back? Captured by
   `forward_3/10/50_candles` blocks measured from the confirmation
   candle's close.

2. **RETEST and REACTION.** Did price come back to the OB? At which
   level? What happened from there? Captured by `level_tags`
   (per-level tap/close-past flags + bars_to_*) and
   `post_tap_reactions` (forward MFE/MAE from each tap point).

Levels tracked (in order from entry-edge to far-edge of the body):
  - **open** (body entry edge) = ob.open. Bullish OB: body_top.
    Bearish OB: body_bottom. This is where price first comes back to.
  - **q25 / q50 / q75** = 25% / 50% (mid) / 75% depth into the body
    measured FROM the entry edge.
  - **close** (body far edge) = ob.close. Full body fill.
  - **range_far** = ob.low for bullish / ob.high for bearish. Extends
    to the wick.

For each level we record a wick-tap flag, a close-past flag, and the
bar indices when each first happened.

Reactions are computed off the entry-edge tap (`open_tap`) and the
far-edge tap (`full_tap`) — MFE/MAE in OB thesis from the tap bar
close.

Invalidation = a forward bar's CLOSE goes through the far edge of
the body in the OPPOSING direction (bullish OB: close < ob.close;
bearish: close > ob.close).
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


# Mode → (timeframe, minutes per bar). Matches the detector modes.
_TIMEFRAME_FOR_MODE: dict[str, tuple[str, int]] = {
    "swept_pdl_1h": ("1h", 60),
    "swept_pdl_4h": ("4h", 240),
    "swept_pdh_1h": ("1h", 60),
    "swept_pdh_4h": ("4h", 240),
    "swept_pwl_4h": ("4h", 240),
    "swept_pwl_daily": ("1d", 24 * 60),
    "swept_pwh_4h": ("4h", 240),
    "swept_pwh_daily": ("1d", 24 * 60),
    # Session-scope OBs (1h tracking only).
    "swept_asia_low_1h": ("1h", 60),
    "swept_asia_high_1h": ("1h", 60),
    "swept_london_low_1h": ("1h", 60),
    "swept_london_high_1h": ("1h", 60),
    "swept_ny_low_1h": ("1h", 60),
    "swept_ny_high_1h": ("1h", 60),
}

_FORWARD_WINDOWS: tuple[int, ...] = (3, 10, 50)
_MAX_FORWARD = max(_FORWARD_WINDOWS)


class OrderBlockReactionsComputer:
    feature_name: str = "order_block"
    outcome_version: str = "v1"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        if event.event_type not in _TIMEFRAME_FOR_MODE:
            log.warning(
                "ob_reactions: unknown event_type %s (id=%s); skipping",
                event.event_type, event.id,
            )
            return None
        if event.side not in ("bullish", "bearish"):
            log.warning("ob_reactions: bad side %r (id=%s)", event.side, event.id)
            return None

        ed = event.event_data or {}
        try:
            ob_open = float(ed["ob_candle"]["open"])
            ob_high = float(ed["ob_candle"]["high"])
            ob_low = float(ed["ob_candle"]["low"])
            ob_close = float(ed["ob_candle"]["close"])
            confirm_close = float(ed["confirmation_candle"]["close"])
        except (KeyError, TypeError, ValueError):
            return None

        direction: Literal["bullish", "bearish"] = event.side  # type: ignore[assignment]
        body_top = max(ob_open, ob_close)
        body_bottom = min(ob_open, ob_close)
        body_width = body_top - body_bottom
        range_top = ob_high
        range_bottom = ob_low

        # Compute level prices. "depth_frac" is fraction of body width
        # FROM the entry edge (ob.open) toward the far edge (ob.close).
        # For bullish: entry=top, far=bottom, so depth goes DOWN.
        # For bearish: entry=bottom, far=top, so depth goes UP.
        if direction == "bullish":
            entry_edge = ob_open      # = body_top
            far_edge = ob_close       # = body_bottom
            range_far = ob_low        # full wick extension below body
            depth_sign = -1.0         # going deeper = moving DOWN
        else:
            entry_edge = ob_open      # = body_bottom
            far_edge = ob_close       # = body_top
            range_far = ob_high       # full wick extension above body
            depth_sign = +1.0

        levels: dict[str, float] = {
            "open": entry_edge,
            "q25": entry_edge + depth_sign * 0.25 * body_width,
            "q50": entry_edge + depth_sign * 0.50 * body_width,
            "q75": entry_edge + depth_sign * 0.75 * body_width,
            "close": far_edge,
            "range_far": range_far,
        }

        timeframe_native, minutes_per_candle = _TIMEFRAME_FOR_MODE[event.event_type]
        confirm_bucket_start = _ensure_utc(event.bar_end_utc)
        forward_start = confirm_bucket_start + timedelta(minutes=minutes_per_candle)
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

        level_tags = _compute_level_tags(forward, levels=levels, direction=direction)
        invalidation = _compute_invalidation(
            forward, far_edge=far_edge, direction=direction,
        )
        deepest = _compute_deepest_fracs(
            forward, entry_edge=entry_edge, body_width=body_width, direction=direction,
        )

        post_tap_reactions: dict[str, Any] = {}
        for tap_key in ("open", "q25", "q50", "q75", "close", "range_far"):
            wick_idx = level_tags[tap_key]["bars_to_wick_tap"]
            if wick_idx is None:
                post_tap_reactions[f"{tap_key}_tap"] = None
                continue
            tap_bar = forward.iloc[wick_idx - 1]  # 1-based
            tap_close = float(tap_bar["close"])
            after = forward.iloc[wick_idx:]
            block: dict[str, Any] = {
                "tap_bar_index": int(wick_idx),
                "tap_bar_close": tap_close,
            }
            for n in _FORWARD_WINDOWS:
                block[f"forward_{n}_after_tap"] = _excursion(
                    after.iloc[:n],
                    reference_close=tap_close,
                    direction=direction,
                )
            post_tap_reactions[f"{tap_key}_tap"] = block

        out: dict[str, Any] = {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "thesis_direction": "up" if direction == "bullish" else "down",
            "reference_close": confirm_close,
            "ob_levels": {
                "open": entry_edge,
                "q25": levels["q25"],
                "q50": levels["q50"],
                "q75": levels["q75"],
                "close": far_edge,
                "range_far": range_far,
                "body_top": body_top,
                "body_bottom": body_bottom,
                "body_width": body_width,
                "range_top": range_top,
                "range_bottom": range_bottom,
                "range_width": range_top - range_bottom,
            },
            "level_tags": level_tags,
            "deepest_wick_frac": deepest["wick_frac"],
            "deepest_close_frac": deepest["close_frac"],
            "invalidation": invalidation,
            "post_tap_reactions": post_tap_reactions,
        }
        for n in _FORWARD_WINDOWS:
            out[f"forward_{n}_candles"] = _excursion(
                forward.iloc[:n],
                reference_close=confirm_close,
                direction=direction,
            )
        return out


# ---------- helpers ----------


def _wick_reached(
    bar: pd.Series,
    *,
    level: float,
    direction: Literal["bullish", "bearish"],
) -> bool:
    """For bullish OB (entry from above): wick reached level when low <= level.
    For bearish OB (entry from below): wick reached when high >= level."""
    if direction == "bullish":
        return float(bar["low"]) <= level
    return float(bar["high"]) >= level


def _close_past(
    bar: pd.Series,
    *,
    level: float,
    direction: Literal["bullish", "bearish"],
) -> bool:
    """For bullish OB: close past = close <= level (closing into/below).
    For bearish OB: close past = close >= level."""
    bar_close = float(bar["close"])
    if direction == "bullish":
        return bar_close <= level
    return bar_close >= level


def _compute_level_tags(
    forward: pd.DataFrame,
    *,
    levels: dict[str, float],
    direction: Literal["bullish", "bearish"],
) -> dict[str, Any]:
    """For each named level, record first bar that wicked it and first
    bar that closed past it."""
    out: dict[str, Any] = {}
    for level_name, price in levels.items():
        wick_first: int | None = None
        close_first: int | None = None
        for idx, (_, bar) in enumerate(forward.iterrows(), start=1):
            if wick_first is None and _wick_reached(bar, level=price, direction=direction):
                wick_first = idx
            if close_first is None and _close_past(bar, level=price, direction=direction):
                close_first = idx
            if wick_first is not None and close_first is not None:
                break
        out[level_name] = {
            "price": price,
            "wick_tapped": wick_first is not None,
            "close_past": close_first is not None,
            "bars_to_wick_tap": wick_first,
            "bars_to_close_past": close_first,
        }
    return out


def _compute_deepest_fracs(
    forward: pd.DataFrame,
    *,
    entry_edge: float,
    body_width: float,
    direction: Literal["bullish", "bearish"],
) -> dict[str, float]:
    """Deepest wick / close penetration into the body, as fraction of
    body width FROM the entry edge. Capped at 1.0 — closes past the
    far edge are flagged via `invalidation`, not pushed beyond 1.0
    here."""
    if forward.empty or body_width <= 0:
        return {"wick_frac": 0.0, "close_frac": 0.0}
    if direction == "bullish":
        # Penetration = entry_edge - bar.low, only counted when low <= entry_edge.
        wick_depths = (entry_edge - forward["low"]).clip(lower=0.0)
        close_depths = (entry_edge - forward["close"]).clip(lower=0.0)
    else:
        wick_depths = (forward["high"] - entry_edge).clip(lower=0.0)
        close_depths = (forward["close"] - entry_edge).clip(lower=0.0)
    wick_max = float(wick_depths.max())
    close_max = float(close_depths.max())
    return {
        "wick_frac": min(1.0, wick_max / body_width),
        "close_frac": min(1.0, close_max / body_width),
    }


def _compute_invalidation(
    forward: pd.DataFrame,
    *,
    far_edge: float,
    direction: Literal["bullish", "bearish"],
) -> dict[str, Any]:
    """Invalidation = bar CLOSED past the body's far edge in the
    opposing direction. Bullish OB: close < ob.close (= far edge).
    Bearish: close > ob.close."""
    bars_to_invalid: int | None = None
    for idx, (_, bar) in enumerate(forward.iterrows(), start=1):
        c = float(bar["close"])
        if direction == "bullish" and c < far_edge:
            bars_to_invalid = idx
            break
        if direction == "bearish" and c > far_edge:
            bars_to_invalid = idx
            break
    return {
        "invalidated": bars_to_invalid is not None,
        "bars_to_invalidation": bars_to_invalid,
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
        "last_close_vs_reference_pts": float(last_close - reference_close),
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
        "last_close_vs_reference_pts": None,
    }


def _load_forward_bars(
    bar_reader: BarReader,
    *,
    symbol: str,
    timeframe: str,
    start_utc: datetime,
    end_utc: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(
            symbol=symbol, timeframe=timeframe,
            start=start_utc, end=end_utc + timedelta(days=1),  # pad for date-partitioned reader
        )
    except (FileNotFoundError, ValueError) as exc:
        log.info("ob_reactions: bar_reader missing %s %s: %s",
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

register("order_block_reactions_v1", OrderBlockReactionsComputer())
