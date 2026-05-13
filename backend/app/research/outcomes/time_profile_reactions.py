"""Time profile reactions outcome computer (v1).

For each time_profile event, captures forward-period (N+1) behavior:
  - Did the NEXT parent period take this parent's high?
  - Take this parent's low?
  - Forward MFE/MAE measured from this parent's close, in close-direction thesis
  - For weekly/monthly: also track N+2

The forward window is one full parent period for daily and weekly, and
one calendar month for monthly. Loads 1m bars at parent-period
granularity; the parent period's CLOSE is the reference price.
"""

from __future__ import annotations

import calendar as _calendar
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import pandas as pd

from app.db.models import ResearchEvent
from app.research.outcomes import BarReader, register
from app.research.sessions import (
    GlobexPeriod,
    globex_day_for,
    globex_week_for,
)

UTC = timezone.utc
log = logging.getLogger(__name__)


_PARENT_FOR_MODE: dict[str, str] = {
    "daily_3session":  "globex_day",
    "daily_4session":  "globex_day",
    "weekly":          "globex_week",
    "monthly":         "calendar_month",
}


class TimeProfileReactionsComputer:
    feature_name: str = "time_profile"
    outcome_version: str = "v1"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        if event.event_type not in _PARENT_FOR_MODE:
            log.warning(
                "time_profile_reactions: unknown mode %s (id=%s)",
                event.event_type, event.id,
            )
            return None

        ed = event.event_data or {}
        try:
            parent_close = float(ed["parent_close"])
            parent_high = float(ed["parent_high"])
            parent_low = float(ed["parent_low"])
            parent_end = datetime.fromisoformat(ed["parent_period_end_utc"])
            direction = ed["parent_direction"]
        except (KeyError, TypeError, ValueError):
            return None

        # Determine N+1 (and N+2 for weekly/monthly) period bounds.
        parent_type = _PARENT_FOR_MODE[event.event_type]
        n_plus_1 = _next_period(parent_end, parent_type)
        if n_plus_1 is None:
            return None

        # Load forward bars covering N+1 (and N+2 for non-daily).
        load_end = n_plus_1.end_utc
        compute_n_plus_2 = parent_type in ("globex_week", "calendar_month")
        n_plus_2: GlobexPeriod | None = None
        if compute_n_plus_2:
            n_plus_2 = _next_period(n_plus_1.end_utc, parent_type)
            if n_plus_2 is not None:
                load_end = n_plus_2.end_utc

        bars = _load_bars(
            bar_reader,
            symbol=event.primary_symbol, timeframe="1m",
            start=n_plus_1.start_utc, end=load_end + timedelta(days=1),
        )
        if bars is None or bars.empty:
            return None
        bars = _ensure_utc_index(bars)

        thesis: Literal["bullish", "bearish"] = (
            "bullish" if direction == "bullish" else "bearish"
        )

        n1_block = _period_reaction(
            bars, period=n_plus_1, parent_close=parent_close,
            parent_high=parent_high, parent_low=parent_low,
            thesis=thesis,
        )
        result: dict[str, Any] = {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "thesis_direction": "up" if thesis == "bullish" else "down",
            "reference_close": parent_close,
            "parent_high": parent_high,
            "parent_low": parent_low,
            "next_period": n1_block,
        }
        if n_plus_2 is not None:
            n2_block = _period_reaction(
                bars, period=n_plus_2, parent_close=parent_close,
                parent_high=parent_high, parent_low=parent_low,
                thesis=thesis,
            )
            result["n_plus_2"] = n2_block
        return result


def _next_period(after_utc: datetime, parent_type: str) -> GlobexPeriod | None:
    """Return the next parent period of the given type AFTER `after_utc`."""
    after_utc = _ensure_utc(after_utc)
    if parent_type == "globex_day":
        return globex_day_for(after_utc + timedelta(seconds=1))
    if parent_type == "globex_week":
        return globex_week_for(after_utc + timedelta(seconds=1))
    if parent_type == "calendar_month":
        # Next calendar month.
        m, y = after_utc.month, after_utc.year
        nxt_month = (m % 12) + 1
        nxt_year = y + (1 if m == 12 else 0)
        last_day = _calendar.monthrange(nxt_year, nxt_month)[1]
        start = datetime(nxt_year, nxt_month, 1, tzinfo=UTC)
        end = datetime(nxt_year, nxt_month, last_day, 23, 59, 59, tzinfo=UTC) + timedelta(seconds=1)
        return GlobexPeriod(start_utc=start, end_utc=end, label="calendar_month")
    return None


def _period_reaction(
    bars: pd.DataFrame,
    *,
    period: GlobexPeriod,
    parent_close: float,
    parent_high: float,
    parent_low: float,
    thesis: Literal["bullish", "bearish"],
) -> dict[str, Any]:
    sliced = bars[(bars.index >= period.start_utc) & (bars.index < period.end_utc)]
    if sliced.empty:
        return _empty_period_reaction(period)
    period_high = float(sliced["high"].max())
    period_low = float(sliced["low"].min())
    period_close = float(sliced["close"].iloc[-1])
    period_open = float(sliced["open"].iloc[0])
    took_parent_high = period_high > parent_high
    took_parent_low = period_low < parent_low
    # Confirmation in thesis direction = took the opposite extreme.
    if thesis == "bullish":
        # Bullish: parent close > open. "Continuation" = took parent_high.
        thesis_confirmed = took_parent_high
        mfe_pts = period_high - parent_close
        mae_pts = parent_close - period_low
    else:
        thesis_confirmed = took_parent_low
        mfe_pts = parent_close - period_low
        mae_pts = period_high - parent_close
    return {
        "ts_utc_start": period.start_utc.isoformat(),
        "ts_utc_end": period.end_utc.isoformat(),
        "n_bars": int(len(sliced)),
        "period_open": period_open,
        "period_close": period_close,
        "period_high": period_high,
        "period_low": period_low,
        "took_parent_high": bool(took_parent_high),
        "took_parent_low": bool(took_parent_low),
        "thesis_confirmed": bool(thesis_confirmed),
        "return_pts_from_parent_close": float(period_close - parent_close),
        "mfe_pts_in_thesis": float(mfe_pts),
        "mae_pts_against_thesis": float(mae_pts),
    }


def _empty_period_reaction(period: GlobexPeriod) -> dict[str, Any]:
    return {
        "ts_utc_start": period.start_utc.isoformat(),
        "ts_utc_end": period.end_utc.isoformat(),
        "n_bars": 0,
        "period_open": None, "period_close": None,
        "period_high": None, "period_low": None,
        "took_parent_high": None, "took_parent_low": None,
        "thesis_confirmed": None,
        "return_pts_from_parent_close": None,
        "mfe_pts_in_thesis": None,
        "mae_pts_against_thesis": None,
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
        log.info("time_profile_react: bar_reader missing %s %s: %s",
                 symbol, timeframe, exc)
        return None
    if df is None or len(df) == 0:
        return None
    return df


def _ensure_utc_index(df: pd.DataFrame) -> pd.DataFrame:
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

register("time_profile_reactions_v1", TimeProfileReactionsComputer())
