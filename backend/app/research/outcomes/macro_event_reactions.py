"""Forward reaction labels for scheduled macro-event anchors."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from app.db.models import ResearchEvent
from app.research.outcomes import BarReader, register

UTC = timezone.utc
log = logging.getLogger(__name__)

WINDOWS_MIN: dict[str, int] = {
    "next_1m": 1,
    "next_5m": 5,
    "next_15m": 15,
    "next_60m": 60,
    "next_240m": 240,
    "next_1d": 24 * 60,
}
MAX_HORIZON_MIN = max(WINDOWS_MIN.values())


class MacroEventReactionsComputer:
    feature_name: str = "macro_event_anchor"
    outcome_version: str = "v2"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        ed = event.event_data or {}
        try:
            release_ts = _to_utc(datetime.fromisoformat(str(ed["release_ts_utc"])))
        except (KeyError, TypeError, ValueError):
            return None

        bars = _load_bars(
            bar_reader,
            symbol=event.primary_symbol,
            timeframe="1m",
            start=release_ts - timedelta(minutes=65),
            end=release_ts + timedelta(minutes=MAX_HORIZON_MIN, days=1),
        )
        if bars is None or bars.empty:
            return None
        bars = _ensure_utc_index(bars).sort_index()

        pre = bars[(bars.index < release_ts) & (bars.index >= release_ts - timedelta(minutes=60))]
        post = bars[
            (bars.index >= release_ts)
            & (bars.index < release_ts + timedelta(minutes=MAX_HORIZON_MIN))
        ]
        if post.empty:
            return None

        reference_close = _reference_close(ed, pre)
        if reference_close is None:
            return None

        pre_15 = _pre_metrics(pre[pre.index >= release_ts - timedelta(minutes=15)])
        pre_60 = _pre_metrics(pre)
        outcomes: dict[str, Any] = {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "release_ts_utc": release_ts.isoformat(),
            "reference_close": float(reference_close),
            "max_horizon_minutes": MAX_HORIZON_MIN,
        }

        for name, minutes in WINDOWS_MIN.items():
            window_end = release_ts + timedelta(minutes=minutes)
            window = post[(post.index >= release_ts) & (post.index < window_end)]
            outcomes[name] = _reaction_window(
                window,
                release_ts=release_ts,
                window_end=window_end,
                reference_close=reference_close,
                pre_15=pre_15,
                pre_60=pre_60,
            )
        return outcomes


def _reference_close(ed: dict[str, Any], pre: pd.DataFrame) -> float | None:
    raw = ed.get("pre_release_reference_close")
    try:
        if raw is not None:
            return float(raw)
    except (TypeError, ValueError):
        pass
    if pre.empty:
        return None
    return float(pre["close"].astype(float).iloc[-1])


def _pre_metrics(window: pd.DataFrame) -> dict[str, Any] | None:
    if window.empty:
        return None
    highs = window["high"].astype(float)
    lows = window["low"].astype(float)
    closes = window["close"].astype(float)
    high = float(highs.max())
    low = float(lows.min())
    return {
        "n_bars": int(len(window)),
        "high": high,
        "low": low,
        "close": float(closes.iloc[-1]),
        "range_pts": float(high - low),
    }


def _reaction_window(
    window: pd.DataFrame,
    *,
    release_ts: datetime,
    window_end: datetime,
    reference_close: float,
    pre_15: dict[str, Any] | None,
    pre_60: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if window.empty:
        return None

    opens = window["open"].astype(float)
    highs = window["high"].astype(float)
    lows = window["low"].astype(float)
    closes = window["close"].astype(float)
    high = float(highs.max())
    low = float(lows.min())
    close = float(closes.iloc[-1])
    first_open = float(opens.iloc[0])
    first_close = float(closes.iloc[0])
    first_return_pts = first_close - reference_close
    range_pts = high - low
    return_pts = close - reference_close
    body_pts = close - first_open
    first_direction = _direction(first_return_pts)
    final_direction = _direction(return_pts)
    out: dict[str, Any] = {
        "window_start_utc": release_ts.isoformat(),
        "window_end_utc": window_end.isoformat(),
        "n_bars": int(len(window)),
        "open": first_open,
        "high": high,
        "low": low,
        "close": close,
        "range_pts": float(range_pts),
        "body_pts": float(body_pts),
        "return_pts": float(return_pts),
        "abs_return_pts": float(abs(return_pts)),
        "direction": final_direction,
        "first_bar_close": first_close,
        "first_bar_return_pts": float(first_return_pts),
        "first_bar_direction": first_direction,
        "first_bar_up_then_final_down": bool(first_return_pts > 0 and return_pts < 0),
        "first_bar_down_then_final_up": bool(first_return_pts < 0 and return_pts > 0),
        "direction_reversed_from_first_bar": bool(
            first_direction != "flat" and final_direction != "flat" and first_direction != final_direction
        ),
        "mfe_up_pts": float(high - reference_close),
        "mfe_down_pts": float(reference_close - low),
        "close_above_release_ref": bool(close > reference_close),
        "close_below_release_ref": bool(close < reference_close),
        "wicked_above_ref_closed_below_ref": bool(high > reference_close and close < reference_close),
        "wicked_below_ref_closed_above_ref": bool(low < reference_close and close > reference_close),
    }
    _add_pre_comparisons(out, pre_15, prefix="pre_15m")
    _add_pre_comparisons(out, pre_60, prefix="pre_60m")
    return out


def _direction(value: float) -> str:
    return "up" if value > 0 else "down" if value < 0 else "flat"


def _add_pre_comparisons(
    out: dict[str, Any],
    pre: dict[str, Any] | None,
    *,
    prefix: str,
) -> None:
    if not pre:
        out[f"range_vs_{prefix}"] = None
        out[f"close_location_vs_{prefix}"] = None
        out[f"range_expanded_1x_{prefix}"] = False
        out[f"range_expanded_2x_{prefix}"] = False
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

    pre_range = float(pre.get("range_pts") or 0.0)
    pre_high = float(pre["high"])
    pre_low = float(pre["low"])
    close = float(out["close"])
    took_high = bool(out["high"] > pre_high)
    took_low = bool(out["low"] < pre_low)
    closed_above = bool(close > pre_high)
    closed_below = bool(close < pre_low)
    closed_inside = bool(pre_low <= close <= pre_high)
    out[f"range_vs_{prefix}"] = float(out["range_pts"] / pre_range) if pre_range > 0 else None
    out[f"close_location_vs_{prefix}"] = (
        float((close - pre_low) / pre_range) if pre_range > 0 else None
    )
    out[f"range_expanded_1x_{prefix}"] = bool(pre_range > 0 and out["range_pts"] >= pre_range)
    out[f"range_expanded_2x_{prefix}"] = bool(pre_range > 0 and out["range_pts"] >= 2.0 * pre_range)
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


def _load_bars(
    bar_reader: BarReader,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame | None:
    try:
        # The warehouse reader accepts dates for partition selection; exact
        # intraday filtering happens after the partition read.
        df = bar_reader(
            symbol=symbol,
            timeframe=timeframe,
            start=start.date(),
            end=end.date() + timedelta(days=1),
        )
    except (FileNotFoundError, ValueError) as exc:
        log.info("macro_event_reactions: bar_reader missing %s %s: %s", symbol, timeframe, exc)
        return None
    if df is None or len(df) == 0:
        return None
    df = _ensure_utc_index(df).sort_index()
    return df[(df.index >= start) & (df.index < end)].copy()


def _ensure_utc_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


register("macro_event_reactions_v1", MacroEventReactionsComputer())
