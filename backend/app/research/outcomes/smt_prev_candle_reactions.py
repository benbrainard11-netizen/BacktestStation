"""Forward reactions for previous-candle SMT divergence."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import pandas as pd

from app.db.models import ResearchEvent
from app.research.outcomes import BarReader, register

UTC = timezone.utc
log = logging.getLogger(__name__)

WINDOWS_MIN = {
    "next_15m": 15,
    "next_30m": 30,
    "next_60m": 60,
    "next_240m": 240,
    "next_1d": 24 * 60,
}
MAX_HORIZON_MIN = max(WINDOWS_MIN.values())


class SmtPrevCandleReactionsComputer:
    feature_name: str = "smt_prev_candle_divergence"
    outcome_version: str = "v1"

    def compute(self, event: ResearchEvent, bar_reader: BarReader) -> dict[str, Any] | None:
        side: Literal["high", "low"]
        if event.side not in ("high", "low"):
            return None
        side = event.side  # type: ignore[assignment]
        ed = event.event_data or {}
        per_symbol = ed.get("per_symbol_states", {})
        primary_state = per_symbol.get(event.primary_symbol, {})
        try:
            reference_close = float(primary_state["current_close"])
            current_high = float(primary_state["current_high"])
            current_low = float(primary_state["current_low"])
        except (KeyError, TypeError, ValueError):
            return None

        event_ts = _ensure_utc(event.bar_end_utc)
        bars = _load_bars(
            bar_reader,
            symbol=event.primary_symbol,
            start=event_ts,
            end=event_ts + timedelta(minutes=MAX_HORIZON_MIN + 5),
        )
        if bars is None or bars.empty:
            return None

        outcomes: dict[str, Any] = {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "event_ts_utc": event_ts.isoformat(),
            "thesis_direction": "down" if side == "high" else "up",
            "reference_close": reference_close,
            "current_candle_high": current_high,
            "current_candle_low": current_low,
            "close_confirmed_at_close": bool(ed.get("close_confirmed_at_close")),
            "primary_close_confirmed": bool(ed.get("primary_close_confirmed")),
        }
        for name, minutes in WINDOWS_MIN.items():
            window = bars[(bars.index >= event_ts) & (bars.index < event_ts + timedelta(minutes=minutes))]
            outcomes[name] = _reaction_window(
                window,
                event_ts=event_ts,
                minutes=minutes,
                side=side,
                reference_close=reference_close,
                current_high=current_high,
                current_low=current_low,
            )
        return outcomes


def _reaction_window(
    window: pd.DataFrame,
    *,
    event_ts: datetime,
    minutes: int,
    side: Literal["high", "low"],
    reference_close: float,
    current_high: float,
    current_low: float,
) -> dict[str, Any] | None:
    window_end = event_ts + timedelta(minutes=minutes)
    if window.empty:
        return None
    highs = window["high"].astype(float)
    lows = window["low"].astype(float)
    closes = window["close"].astype(float)
    high = float(highs.max())
    low = float(lows.min())
    close = float(closes.iloc[-1])
    if side == "high":
        mfe = reference_close - low
        mae = high - reference_close
        thesis_confirmed = low <= current_low
        close_moved_with_thesis = close < reference_close
    else:
        mfe = high - reference_close
        mae = reference_close - low
        thesis_confirmed = high >= current_high
        close_moved_with_thesis = close > reference_close
    took_current_high = high > current_high
    took_current_low = low < current_low
    return {
        "window_start_utc": event_ts.isoformat(),
        "window_end_utc": window_end.isoformat(),
        "n_bars": int(len(window)),
        "high": high,
        "low": low,
        "close": close,
        "return_pts": float(close - reference_close),
        "abs_return_pts": float(abs(close - reference_close)),
        "mfe_pts_in_thesis": float(mfe),
        "mae_pts_against_thesis": float(mae),
        "thesis_confirmed": bool(thesis_confirmed),
        "close_moved_with_thesis": bool(close_moved_with_thesis),
        "took_current_candle_high": bool(took_current_high),
        "took_current_candle_low": bool(took_current_low),
        "swept_both_current_candle_sides": bool(took_current_high and took_current_low),
        "closed_above_current_candle_high": bool(close > current_high),
        "closed_below_current_candle_low": bool(close < current_low),
        "closed_inside_current_candle_range": bool(current_low <= close <= current_high),
    }


def _load_bars(
    bar_reader: BarReader,
    *,
    symbol: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(symbol=symbol, timeframe="1m", start=start.date(), end=end.date() + timedelta(days=1))
    except (FileNotFoundError, ValueError) as exc:
        log.info("smt_prev_candle_reactions: missing bars for %s: %s", symbol, exc)
        return None
    if df is None or len(df) == 0:
        return None
    df = _normalize_index(df).sort_index()
    return df[(df.index >= start) & (df.index < end)].copy()


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


register("smt_prev_candle_reactions_v1", SmtPrevCandleReactionsComputer())
