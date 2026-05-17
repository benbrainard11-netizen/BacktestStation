"""Displacement candle reactions outcome computer (v1).

For each displacement candle event, captures:

1. **forward_3/10/50_candles** — MFE/MAE measured FROM the displacement
   candle's close, oriented to displacement direction (bullish disp →
   thesis = up).

2. **retracement** — did price come back to the displacement candle's
   body? When? How deep?
     - tapped_close: any forward bar wicked back to disp.close (the
       far edge of the body in disp direction)
     - tapped_mid: wicked back to disp body midpoint
     - tapped_open: wicked back to disp body open (retraced fully
       into the body)
     - tapped_full: wicked back to the FAR side of the disp body
       (= invalidation edge in displacement direction)
     - bars_to_each + deepest_retracement_frac

3. **invalidation** — did a forward bar CLOSE past the displacement
   open in the opposing direction (bullish disp → close < disp.open
   means displacement got reclaimed)? When?
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
    "15m_disp": ("15m", 15),
    "30m_disp": ("30m", 30),
    "1h_disp": ("1h", 60),
    "4h_disp": ("4h", 240),
    "daily_disp": ("1d", 24 * 60),
}

_FORWARD_WINDOWS: tuple[int, ...] = (3, 10, 50)
_MAX_FORWARD = max(_FORWARD_WINDOWS)


class DisplacementReactionsComputer:
    feature_name: str = "displacement_candle"
    outcome_version: str = "v1"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        if event.event_type not in _TIMEFRAME_FOR_MODE:
            log.warning(
                "disp_reactions: unknown event_type %s (id=%s)",
                event.event_type, event.id,
            )
            return None
        if event.side not in ("bullish", "bearish"):
            log.warning(
                "disp_reactions: bad side %r (id=%s)", event.side, event.id,
            )
            return None

        ed = event.event_data or {}
        try:
            d_open = float(ed["candle"]["open"])
            d_high = float(ed["candle"]["high"])
            d_low = float(ed["candle"]["low"])
            d_close = float(ed["candle"]["close"])
        except (KeyError, TypeError, ValueError):
            return None

        direction: Literal["bullish", "bearish"] = event.side  # type: ignore[assignment]
        body_top = max(d_open, d_close)
        body_bottom = min(d_open, d_close)
        body_width = body_top - body_bottom
        body_mid = (body_top + body_bottom) / 2.0

        timeframe_native, minutes_per_candle = _TIMEFRAME_FOR_MODE[event.event_type]
        bucket_start = _ensure_utc(event.bar_end_utc)
        forward_start = bucket_start + timedelta(minutes=minutes_per_candle)
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

        # Forward continuation MFE/MAE from disp close.
        forward_blocks: dict[str, dict[str, Any]] = {}
        for n in _FORWARD_WINDOWS:
            forward_blocks[f"forward_{n}_candles"] = _excursion(
                forward.iloc[:n],
                reference_close=d_close,
                direction=direction,
            )

        # Retracement levels (reading depth from disp.close = entry edge):
        #   For bullish disp (close > open): close is body TOP.
        #   tap_close = bar.low <= d.close = close to body top from above.
        #   tap_open = bar.low <= d.open = retraced to body bottom.
        #   tap_full = bar.low <= d.low = wicked below the entire candle.
        # For bearish disp (close < open): close is body BOTTOM.
        #   tap_close = bar.high >= d.close = entered body from below.
        #   tap_open = bar.high >= d.open = retraced to body top.
        #   tap_full = bar.high >= d.high = wicked above entire candle.
        retracement = _compute_retracement(
            forward, direction=direction,
            d_open=d_open, d_close=d_close, d_high=d_high, d_low=d_low,
            body_mid=body_mid, body_width=body_width,
        )

        # Invalidation: bar closed past d.open in opposing direction.
        invalidation = _compute_invalidation(
            forward, d_open=d_open, direction=direction,
        )

        return {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "thesis_direction": "up" if direction == "bullish" else "down",
            "reference_close": d_close,
            "displacement_levels": {
                "open": d_open, "close": d_close,
                "high": d_high, "low": d_low,
                "body_top": body_top, "body_bottom": body_bottom,
                "body_mid": body_mid, "body_width_pts": body_width,
            },
            "retracement": retracement,
            "invalidation": invalidation,
            **forward_blocks,
        }


# ---------- helpers ----------


def _compute_retracement(
    forward: pd.DataFrame,
    *,
    direction: Literal["bullish", "bearish"],
    d_open: float, d_close: float, d_high: float, d_low: float,
    body_mid: float, body_width: float,
) -> dict[str, Any]:
    """Track when forward bars retrace back to displacement body levels."""
    bars_to_close: int | None = None     # entered body via close edge
    bars_to_mid: int | None = None       # entered body to mid
    bars_to_open: int | None = None      # retraced fully through body
    bars_to_full: int | None = None      # wicked beyond candle entirely
    deepest_frac: float = 0.0  # fraction of body retraced (0 = none, 1.0 = open reached)

    if direction == "bullish":
        # Bullish disp: close is body top, open is body bottom.
        # Retracement = price coming DOWN. Levels (top to bottom):
        #   close (body top), mid, open (body bottom), low (full).
        for idx, (_, bar) in enumerate(forward.iterrows(), start=1):
            low = float(bar["low"])
            if low > d_close:
                continue  # didn't reach body top
            if bars_to_close is None:
                bars_to_close = idx
            if bars_to_mid is None and low <= body_mid:
                bars_to_mid = idx
            if bars_to_open is None and low <= d_open:
                bars_to_open = idx
            if bars_to_full is None and low <= d_low:
                bars_to_full = idx
            depth_pts = max(0.0, d_close - low)
            frac = (
                min(1.0, depth_pts / body_width) if body_width > 0 else 0.0
            )
            if frac > deepest_frac:
                deepest_frac = frac
            if bars_to_full is not None:
                break
    else:
        # Bearish: close is body bottom, open is body top.
        # Retracement = price coming UP.
        for idx, (_, bar) in enumerate(forward.iterrows(), start=1):
            high = float(bar["high"])
            if high < d_close:
                continue
            if bars_to_close is None:
                bars_to_close = idx
            if bars_to_mid is None and high >= body_mid:
                bars_to_mid = idx
            if bars_to_open is None and high >= d_open:
                bars_to_open = idx
            if bars_to_full is None and high >= d_high:
                bars_to_full = idx
            depth_pts = max(0.0, high - d_close)
            frac = (
                min(1.0, depth_pts / body_width) if body_width > 0 else 0.0
            )
            if frac > deepest_frac:
                deepest_frac = frac
            if bars_to_full is not None:
                break

    return {
        "tapped_close": bars_to_close is not None,
        "tapped_mid": bars_to_mid is not None,
        "tapped_open": bars_to_open is not None,
        "tapped_full": bars_to_full is not None,
        "bars_to_close": bars_to_close,
        "bars_to_mid": bars_to_mid,
        "bars_to_open": bars_to_open,
        "bars_to_full": bars_to_full,
        "deepest_retracement_frac": float(deepest_frac),
        "horizon_bars": int(len(forward)),
    }


def _compute_invalidation(
    forward: pd.DataFrame,
    *,
    d_open: float,
    direction: Literal["bullish", "bearish"],
) -> dict[str, Any]:
    """Bar CLOSED past d.open in opposing direction (reclaim)."""
    bars_to: int | None = None
    for idx, (_, bar) in enumerate(forward.iterrows(), start=1):
        c = float(bar["close"])
        if direction == "bullish" and c < d_open:
            bars_to = idx
            break
        if direction == "bearish" and c > d_open:
            bars_to = idx
            break
    return {
        "invalidated": bars_to is not None,
        "bars_to_invalidation": bars_to,
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
        log.info("disp_reactions: bar_reader missing %s %s: %s",
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

register("displacement_reactions_v1", DisplacementReactionsComputer())
