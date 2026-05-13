"""Time profile detector — fractal H/L sub-period classifier.

For each parent period (Globex day / Globex week / calendar month),
subdivide into sub-periods and record:
  - Per-sub-period OHLC + range
  - Which sub-period contained the parent's overall HIGH and LOW
  - Order: was the parent high or low made FIRST chronologically
  - Open-reference flags: did each sub-period close above/below parent_open
  - Computed profile_class string (e.g., "asia_low_ny_high_low_first")

This is Ben's "fractal time alignment" framing — the same H/L sub-period
classifier applied at multiple timeframes.

Modes:
  - daily_3session  → sub_periods = asia / london / ny
  - daily_4session  → sub_periods = asia / london / ny_am / ny_pm
  - weekly          → sub_periods = monday / tuesday / wednesday / thursday / friday
                                    (Globex days within Globex week)
  - monthly         → sub_periods = week_1 / week_2 / .. (Globex weeks within
                                    calendar month, by start_utc.month)

Wide-reach data: full OHLC of every sub-period preserved so downstream
re-bucketing (e.g., "what if we split NY at 12:00 ET differently?") is
analysis-time only.

bar_end_utc = parent_period_start_utc (when the period began)
knowable_ts = parent_period_end_utc (when fully classifiable)
side = "bullish" | "bearish" | "doji" (parent close vs parent open)
"""

from __future__ import annotations

import calendar as _calendar
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.research.sessions import (
    GlobexPeriod,
    globex_day_for,
    globex_week_for,
    session_for,
)
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SubPeriod:
    label: str
    start_utc: datetime
    end_utc: datetime


_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "daily_3session":  {"parent": "globex_day"},
    "daily_4session":  {"parent": "globex_day"},
    "weekly":          {"parent": "globex_week"},
    "monthly":         {"parent": "calendar_month"},
}


class TimeProfileDetector:
    feature_name: str = "time_profile"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_CONFIG.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                f"time_profile requires --mode {{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_CONFIG:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("time_profile requires at least one symbol")
        events: list[ResearchEventCreate] = []
        for symbol in ctx.symbols:
            events.extend(self._scan_symbol(ctx, symbol))
        return events

    def _scan_symbol(
        self, ctx: DetectorContext, symbol: str,
    ) -> list[ResearchEventCreate]:
        events: list[ResearchEventCreate] = []
        for parent in _iter_parent_periods(ctx.start, ctx.end, ctx.mode):
            ev = self._scan_one_parent(ctx, symbol, parent)
            if ev is not None:
                events.append(ev)
        return events

    def _scan_one_parent(
        self, ctx: DetectorContext, symbol: str, parent: GlobexPeriod,
    ) -> ResearchEventCreate | None:
        sub_periods = _build_sub_periods(parent, ctx.mode)
        if not sub_periods:
            return None
        # Load 1m bars covering the full parent period + 1-day buffer.
        bars = _safe_load(
            ctx.bar_reader,
            symbol=symbol, timeframe="1m",
            start=parent.start_utc,
            end=parent.end_utc + timedelta(days=1),
        )
        if bars is None or bars.empty:
            return None
        bars = _ensure_utc_index(bars)
        # Filter to the parent period strictly.
        bars = bars[(bars.index >= parent.start_utc) & (bars.index < parent.end_utc)]
        if bars.empty:
            return None

        parent_open = float(bars["open"].iloc[0])
        parent_close = float(bars["close"].iloc[-1])
        parent_high = float(bars["high"].max())
        parent_low = float(bars["low"].min())
        parent_high_ts = bars["high"].idxmax()
        parent_low_ts = bars["low"].idxmin()
        if not isinstance(parent_high_ts, pd.Timestamp):
            parent_high_ts = pd.Timestamp(parent_high_ts)
        if not isinstance(parent_low_ts, pd.Timestamp):
            parent_low_ts = pd.Timestamp(parent_low_ts)

        if parent_close > parent_open:
            side = "bullish"
        elif parent_close < parent_open:
            side = "bearish"
        else:
            side = "doji"

        sub_period_blocks: list[dict[str, Any]] = []
        high_sub_period: str | None = None
        low_sub_period: str | None = None
        for sp in sub_periods:
            sl = bars[(bars.index >= sp.start_utc) & (bars.index < sp.end_utc)]
            if sl.empty:
                # Still record an empty sub-period (e.g., session had no data).
                sub_period_blocks.append({
                    "label": sp.label,
                    "start_utc": sp.start_utc.isoformat(),
                    "end_utc": sp.end_utc.isoformat(),
                    "open": None, "high": None, "low": None, "close": None,
                    "range_pts": None,
                    "n_bars": 0,
                    "ts_of_high_utc": None, "ts_of_low_utc": None,
                    "closed_above_parent_open": None,
                    "high_pierced_parent_open": None,
                    "low_pierced_parent_open": None,
                    "high_vs_parent_open_pts": None,
                    "low_vs_parent_open_pts": None,
                    "close_vs_parent_open_pts": None,
                })
                continue
            sp_open = float(sl["open"].iloc[0])
            sp_close = float(sl["close"].iloc[-1])
            sp_high = float(sl["high"].max())
            sp_low = float(sl["low"].min())
            sp_high_ts = sl["high"].idxmax()
            sp_low_ts = sl["low"].idxmin()
            if not isinstance(sp_high_ts, pd.Timestamp):
                sp_high_ts = pd.Timestamp(sp_high_ts)
            if not isinstance(sp_low_ts, pd.Timestamp):
                sp_low_ts = pd.Timestamp(sp_low_ts)
            # Is the parent extreme inside this sub-period?
            if sp_high == parent_high and high_sub_period is None:
                high_sub_period = sp.label
            if sp_low == parent_low and low_sub_period is None:
                low_sub_period = sp.label
            sub_period_blocks.append({
                "label": sp.label,
                "start_utc": sp.start_utc.isoformat(),
                "end_utc": sp.end_utc.isoformat(),
                "open": sp_open, "high": sp_high, "low": sp_low, "close": sp_close,
                "range_pts": sp_high - sp_low,
                "n_bars": int(len(sl)),
                "ts_of_high_utc": sp_high_ts.tz_convert(UTC).isoformat()
                                  if sp_high_ts.tz else sp_high_ts.tz_localize(UTC).isoformat(),
                "ts_of_low_utc": sp_low_ts.tz_convert(UTC).isoformat()
                                 if sp_low_ts.tz else sp_low_ts.tz_localize(UTC).isoformat(),
                "closed_above_parent_open": sp_close > parent_open,
                "high_pierced_parent_open": sp_high > parent_open,
                "low_pierced_parent_open": sp_low < parent_open,
                "high_vs_parent_open_pts": float(sp_high - parent_open),
                "low_vs_parent_open_pts": float(sp_low - parent_open),
                "close_vs_parent_open_pts": float(sp_close - parent_open),
            })

        high_first = parent_high_ts < parent_low_ts
        low_first = parent_low_ts < parent_high_ts
        order = "high_first" if high_first else ("low_first" if low_first else "simultaneous")

        # Compute profile_class.
        hi = high_sub_period or "unk"
        lo = low_sub_period or "unk"
        profile_class = f"{lo}_low_{hi}_high_{order}"

        # Classic Power-of-3 flags.
        is_bullish_classic_po3 = (side == "bullish") and low_first
        is_bearish_classic_po3 = (side == "bearish") and high_first
        is_bullish_trend = (side == "bullish") and high_first
        is_bearish_trend = (side == "bearish") and low_first

        bar_end_utc = parent.start_utc
        et_ts = bar_end_utc.astimezone(ET)
        event_data: dict[str, Any] = {
            "schema_version": 1,
            "detector_version": self.detector_version,
            "mode": ctx.mode,
            "parent_period_label": parent.label,
            "parent_period_start_utc": parent.start_utc.isoformat(),
            "parent_period_end_utc": parent.end_utc.isoformat(),
            "parent_open": parent_open,
            "parent_close": parent_close,
            "parent_high": parent_high,
            "parent_low": parent_low,
            "parent_range_pts": parent_high - parent_low,
            "parent_body_pts": abs(parent_close - parent_open),
            "parent_direction": side,
            "ts_of_parent_high_utc": (
                parent_high_ts.tz_convert(UTC).isoformat()
                if parent_high_ts.tz else parent_high_ts.tz_localize(UTC).isoformat()
            ),
            "ts_of_parent_low_utc": (
                parent_low_ts.tz_convert(UTC).isoformat()
                if parent_low_ts.tz else parent_low_ts.tz_localize(UTC).isoformat()
            ),
            "sub_periods": sub_period_blocks,
            "high_sub_period": high_sub_period,
            "low_sub_period": low_sub_period,
            "order": order,
            "high_first": high_first,
            "low_first": low_first,
            "profile_class": profile_class,
            "is_bullish_classic_po3": is_bullish_classic_po3,
            "is_bearish_classic_po3": is_bearish_classic_po3,
            "is_bullish_trend": is_bullish_trend,
            "is_bearish_trend": is_bearish_trend,
        }
        context: dict[str, Any] = {
            "day_of_week_et": et_ts.weekday(),
            "hour_of_day_et": et_ts.hour,
            "parent_label": parent.label,
        }
        return ResearchEventCreate(
            feature_name=self.feature_name,
            event_type=ctx.mode,
            bar_end_utc=bar_end_utc,
            primary_symbol=symbol,
            symbols=[symbol],
            timeframe=_TIMEFRAME_LABEL[ctx.mode],
            side=side,
            event_data=event_data,
            context=context,
            outcomes=None,
            replay_pointer={
                "primary_symbol": symbol,
                "ts_utc": bar_end_utc.isoformat(),
                "parent_period_label": parent.label,
                "profile_class": profile_class,
            },
            detector_version=self.detector_version,
        )


_TIMEFRAME_LABEL: dict[str, str] = {
    "daily_3session": "1D",
    "daily_4session": "1D",
    "weekly": "1W",
    "monthly": "1MO",
}


# ---------- sub-period builders ----------


def _build_sub_periods(parent: GlobexPeriod, mode: str) -> list[SubPeriod]:
    if mode == "daily_3session":
        return _daily_sessions_3(parent)
    if mode == "daily_4session":
        return _daily_sessions_4(parent)
    if mode == "weekly":
        return _weekly_days(parent)
    if mode == "monthly":
        return _monthly_weeks(parent)
    return []


def _daily_sessions_3(parent: GlobexPeriod) -> list[SubPeriod]:
    """3 ICT sessions within a Globex day."""
    asia = session_for(parent.start_utc + timedelta(hours=1), "asia")
    london = session_for(parent.start_utc + timedelta(hours=1), "london")
    ny = session_for(parent.start_utc + timedelta(hours=1), "ny")
    return [
        SubPeriod("asia", asia.start_utc, asia.end_utc),
        SubPeriod("london", london.start_utc, london.end_utc),
        SubPeriod("ny", ny.start_utc, ny.end_utc),
    ]


def _daily_sessions_4(parent: GlobexPeriod) -> list[SubPeriod]:
    """4 sub-periods: asia / london / ny_am / ny_pm. NY split at 12:00 ET."""
    asia = session_for(parent.start_utc + timedelta(hours=1), "asia")
    london = session_for(parent.start_utc + timedelta(hours=1), "london")
    ny = session_for(parent.start_utc + timedelta(hours=1), "ny")
    ny_start_et = ny.start_utc.astimezone(ET)
    ny_split_et = datetime.combine(
        ny_start_et.date(), time(12, 0), tzinfo=ET,
    )
    ny_split_utc = ny_split_et.astimezone(UTC)
    return [
        SubPeriod("asia", asia.start_utc, asia.end_utc),
        SubPeriod("london", london.start_utc, london.end_utc),
        SubPeriod("ny_am", ny.start_utc, ny_split_utc),
        SubPeriod("ny_pm", ny_split_utc, ny.end_utc),
    ]


def _weekly_days(parent: GlobexPeriod) -> list[SubPeriod]:
    """5 Globex days within a Globex week (Mon-Fri sessions)."""
    out: list[SubPeriod] = []
    # Walk Globex days within the week.
    cur_day = globex_day_for(parent.start_utc + timedelta(hours=1))
    day_labels = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    for label in day_labels:
        # cur_day might extend beyond parent.end_utc on the last day; clip.
        start_utc = max(cur_day.start_utc, parent.start_utc)
        end_utc = min(cur_day.end_utc, parent.end_utc)
        if end_utc > start_utc:
            out.append(SubPeriod(label, start_utc, end_utc))
        # Advance.
        nxt = globex_day_for(cur_day.end_utc + timedelta(seconds=1))
        if nxt.start_utc >= parent.end_utc:
            break
        cur_day = nxt
    return out


def _monthly_weeks(parent: GlobexPeriod) -> list[SubPeriod]:
    """Globex weeks whose start_utc.month matches the parent month.
    Sub-period labels: week_1 / week_2 / ... in chronological order."""
    out: list[SubPeriod] = []
    cur_week = globex_week_for(parent.start_utc + timedelta(hours=1))
    week_idx = 0
    while cur_week.start_utc < parent.end_utc:
        # Clip to parent bounds.
        start_utc = max(cur_week.start_utc, parent.start_utc)
        end_utc = min(cur_week.end_utc, parent.end_utc)
        if end_utc > start_utc:
            week_idx += 1
            out.append(SubPeriod(f"week_{week_idx}", start_utc, end_utc))
        nxt = globex_week_for(cur_week.end_utc + timedelta(seconds=1))
        if nxt.start_utc >= parent.end_utc:
            break
        cur_week = nxt
    return out


# ---------- parent iterators ----------


def _iter_parent_periods(start_d, end_d, mode: str):
    start_dt = datetime(start_d.year, start_d.month, start_d.day, tzinfo=UTC)
    end_dt = datetime(end_d.year, end_d.month, end_d.day, tzinfo=UTC) + timedelta(days=1)
    parent = _MODE_CONFIG[mode]["parent"]
    if parent == "globex_day":
        cur = globex_day_for(start_dt)
        while cur.start_utc < end_dt:
            yield cur
            cur = globex_day_for(cur.end_utc + timedelta(seconds=1))
    elif parent == "globex_week":
        cur = globex_week_for(start_dt)
        while cur.start_utc < end_dt:
            yield cur
            cur = globex_week_for(cur.end_utc + timedelta(seconds=1))
    elif parent == "calendar_month":
        # Iterate calendar months from start to end.
        y, m = start_dt.year, start_dt.month
        while True:
            month_start = datetime(y, m, 1, tzinfo=UTC)
            if month_start >= end_dt:
                break
            last_day = _calendar.monthrange(y, m)[1]
            month_end = datetime(y, m, last_day, 23, 59, 59, tzinfo=UTC) + timedelta(seconds=1)
            yield GlobexPeriod(
                start_utc=month_start,
                end_utc=month_end,
                label="calendar_month",
            )
            # advance one month
            if m == 12:
                y, m = y + 1, 1
            else:
                m += 1
    else:
        raise ValueError(f"unknown parent type: {parent}")


# ---------- helpers ----------


def _safe_load(
    bar_reader: BarReader,
    *, symbol: str, timeframe: str, start: datetime, end: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(symbol=symbol, timeframe=timeframe, start=start, end=end)
    except (FileNotFoundError, ValueError) as exc:
        log.info("time_profile: bar_reader missing %s %s: %s", symbol, timeframe, exc)
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


# ---------- registration ----------

register("time_profile", TimeProfileDetector())
