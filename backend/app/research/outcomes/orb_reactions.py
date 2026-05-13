"""Opening Range Breakout reactions outcome computer (v1).

For each ORB event, captures what price did over the rest of the
trading session (until end of Globex day, capped at +6h forward
window for ny modes / +12h for asia).

Tracks:
  - break_high / break_low (wick + close past OR range)
  - break extensions at 0.5× and 1× range multiplier
  - rest_window high/low/close
  - direction summaries (parent vs OR direction)
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


# Per-mode forward horizon in minutes.
_HORIZON_MIN: dict[str, int] = {
    "ny_5m":   8 * 60,    # rest of NY session ~7.5h
    "ny_15m":  8 * 60,
    "ny_30m":  8 * 60,
    "asia_60m": 12 * 60,  # rest of Asia + into London
}


class OrbReactionsComputer:
    feature_name: str = "opening_range_breakout"
    outcome_version: str = "v1"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        if event.event_type not in _HORIZON_MIN:
            log.warning(
                "orb_reactions: unknown mode %s (id=%s)",
                event.event_type, event.id,
            )
            return None

        ed = event.event_data or {}
        try:
            or_high = float(ed["or_high"])
            or_low = float(ed["or_low"])
            or_close = float(ed["or_close"])
            or_open = float(ed["or_open"])
            or_range = float(ed["or_range_pts"])
            range_end_utc = datetime.fromisoformat(ed["range_end_utc"])
            day_end_utc = datetime.fromisoformat(ed["globex_day_end_utc"])
        except (KeyError, TypeError, ValueError):
            return None
        if or_range <= 0:
            return None

        horizon_min = _HORIZON_MIN[event.event_type]
        horizon_end = min(
            range_end_utc + timedelta(minutes=horizon_min),
            day_end_utc,
        )

        rest = _load_bars(
            bar_reader,
            symbol=event.primary_symbol, timeframe="1m",
            start=range_end_utc, end=horizon_end + timedelta(days=1),
        )
        if rest is None or rest.empty:
            return None
        rest = rest[(rest.index >= range_end_utc) & (rest.index < horizon_end)]
        if rest.empty:
            return None

        ext_high_05 = or_high + 0.5 * or_range
        ext_high_1 = or_high + 1.0 * or_range
        ext_low_05 = or_low - 0.5 * or_range
        ext_low_1 = or_low - 1.0 * or_range

        break_high = _first_breach(rest, level=or_high, direction="up")
        break_high_05 = _first_breach(rest, level=ext_high_05, direction="up")
        break_high_1 = _first_breach(rest, level=ext_high_1, direction="up")
        break_low = _first_breach(rest, level=or_low, direction="down")
        break_low_05 = _first_breach(rest, level=ext_low_05, direction="down")
        break_low_1 = _first_breach(rest, level=ext_low_1, direction="down")

        rest_high = float(rest["high"].max())
        rest_low = float(rest["low"].min())
        rest_close = float(rest["close"].iloc[-1])

        # Direction of "rest of session" relative to or_close.
        if rest_close > or_close:
            rest_direction = "bullish"
        elif rest_close < or_close:
            rest_direction = "bearish"
        else:
            rest_direction = "doji"

        # Did the session take both sides? (= "ranging day" pattern)
        broke_both = break_high["wick_breached"] and break_low["wick_breached"]
        broke_only_high = break_high["wick_breached"] and not break_low["wick_breached"]
        broke_only_low = break_low["wick_breached"] and not break_high["wick_breached"]

        return {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "reference_close": or_close,
            "or_direction": ed.get("or_direction"),
            "rest_direction": rest_direction,
            "rest_window_high": rest_high,
            "rest_window_low": rest_low,
            "rest_window_close": rest_close,
            "rest_n_bars": int(len(rest)),
            "horizon_minutes": int((horizon_end - range_end_utc).total_seconds() / 60),
            "break_high": break_high,
            "break_high_05ext": break_high_05,
            "break_high_1ext": break_high_1,
            "break_low": break_low,
            "break_low_05ext": break_low_05,
            "break_low_1ext": break_low_1,
            "broke_both_sides": broke_both,
            "broke_only_high": broke_only_high,
            "broke_only_low": broke_only_low,
            "deepest_above_pts": float(max(0.0, rest_high - or_high)),
            "deepest_below_pts": float(max(0.0, or_low - rest_low)),
            "deepest_above_range_mult": (
                float((rest_high - or_high) / or_range)
                if rest_high > or_high else 0.0
            ),
            "deepest_below_range_mult": (
                float((or_low - rest_low) / or_range)
                if rest_low < or_low else 0.0
            ),
        }


# ---------- helpers ----------


def _first_breach(
    bars: pd.DataFrame, *, level: float, direction: str,
) -> dict[str, Any]:
    bar_idx_wick: int | None = None
    bar_idx_close: int | None = None
    ts_wick = None
    ts_close = None
    for idx, (ts, bar) in enumerate(bars.iterrows(), start=1):
        h = float(bar["high"]); l = float(bar["low"]); c = float(bar["close"])
        if direction == "up":
            if bar_idx_wick is None and h > level:
                bar_idx_wick, ts_wick = idx, ts
            if bar_idx_close is None and c > level:
                bar_idx_close, ts_close = idx, ts
        else:
            if bar_idx_wick is None and l < level:
                bar_idx_wick, ts_wick = idx, ts
            if bar_idx_close is None and c < level:
                bar_idx_close, ts_close = idx, ts
        if bar_idx_wick is not None and bar_idx_close is not None:
            break
    return {
        "wick_breached": bar_idx_wick is not None,
        "close_past": bar_idx_close is not None,
        "bar_index_wick": bar_idx_wick,
        "bar_index_close": bar_idx_close,
        "ts_wick": ts_wick.isoformat() if ts_wick is not None and hasattr(ts_wick, "isoformat") else None,
        "ts_close": ts_close.isoformat() if ts_close is not None and hasattr(ts_close, "isoformat") else None,
    }


def _load_bars(
    bar_reader: BarReader,
    *, symbol: str, timeframe: str, start: datetime, end: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(symbol=symbol, timeframe=timeframe,
                        start=start, end=end + timedelta(days=1))
    except (FileNotFoundError, ValueError) as exc:
        log.info("orb_reactions: bar_reader missing %s %s: %s",
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

register("orb_reactions_v1", OrbReactionsComputer())
