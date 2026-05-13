"""New Day / New Week Opening Gap level detector.

Creates persistent gap level events:

  - NDOG: current Globex day open vs previous Globex day close
  - NWOG: current Globex week open vs previous Globex week close

The event is knowable at the new day/week open. Future fills, touches,
rejections, and acceptances are outcomes, not event_data.
"""

from __future__ import annotations

import logging
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.research.sessions import (
    GlobexPeriod,
    globex_day_for,
    globex_week_for,
    previous_globex_day,
    previous_globex_week,
)
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)

_MODE_CONFIG = {
    "ndog": {"period": "globex_day", "timeframe": "1D_GAP"},
    "nwog": {"period": "globex_week", "timeframe": "1W_GAP"},
}


class OpeningGapLevelsDetector:
    feature_name: str = "opening_gap_levels"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_CONFIG.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError("opening_gap_levels requires --mode {ndog|nwog}")
        if ctx.mode not in _MODE_CONFIG:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("opening_gap_levels requires at least one symbol")

        min_gap_pts = float(ctx.params.get("min_gap_pts", 0.0))
        events: list[ResearchEventCreate] = []
        for symbol in ctx.symbols:
            events.extend(self._scan_symbol(ctx, symbol, min_gap_pts=min_gap_pts))
        return events

    def _scan_symbol(
        self,
        ctx: DetectorContext,
        symbol: str,
        *,
        min_gap_pts: float,
    ) -> list[ResearchEventCreate]:
        events: list[ResearchEventCreate] = []
        periods = (
            _iter_globex_days(ctx.start, ctx.end)
            if ctx.mode == "ndog"
            else _iter_globex_weeks(ctx.start, ctx.end)
        )
        for current in periods:
            previous = (
                previous_globex_day(current.start_utc + timedelta(seconds=1))
                if ctx.mode == "ndog"
                else previous_globex_week(current.start_utc + timedelta(seconds=1))
            )
            ev = self._scan_one_gap(
                ctx,
                symbol=symbol,
                current=current,
                previous=previous,
                min_gap_pts=min_gap_pts,
            )
            if ev is not None:
                events.append(ev)
        return events

    def _scan_one_gap(
        self,
        ctx: DetectorContext,
        *,
        symbol: str,
        current: GlobexPeriod,
        previous: GlobexPeriod,
        min_gap_pts: float,
    ) -> ResearchEventCreate | None:
        bars = _safe_load(
            ctx.bar_reader,
            symbol=symbol,
            timeframe="1m",
            start=previous.end_utc - timedelta(hours=2),
            end=current.start_utc + timedelta(hours=2),
        )
        if bars is None or bars.empty:
            return None
        bars = _ensure_utc_index(bars).sort_index()

        prev_bars = bars[(bars.index >= previous.start_utc) & (bars.index < previous.end_utc)]
        open_bars = bars[(bars.index >= current.start_utc) & (bars.index < current.end_utc)]
        if prev_bars.empty or open_bars.empty:
            return None

        prev_close_ts = prev_bars.index[-1].to_pydatetime()
        prev_close = float(prev_bars["close"].iloc[-1])
        open_ts = open_bars.index[0].to_pydatetime()
        current_open = float(open_bars["open"].iloc[0])
        gap_size = abs(current_open - prev_close)
        if gap_size <= min_gap_pts:
            return None

        gap_high = max(prev_close, current_open)
        gap_low = min(prev_close, current_open)
        gap_mid = (gap_high + gap_low) / 2.0
        direction = "gap_up" if current_open > prev_close else "gap_down"
        et_ts = open_ts.astimezone(ET)

        event_data: dict[str, Any] = {
            "schema_version": 1,
            "detector_version": self.detector_version,
            "gap_type": ctx.mode,
            "previous_period_label": previous.label,
            "previous_period_start_utc": previous.start_utc.isoformat(),
            "previous_period_end_utc": previous.end_utc.isoformat(),
            "current_period_label": current.label,
            "current_period_start_utc": current.start_utc.isoformat(),
            "current_period_end_utc": current.end_utc.isoformat(),
            "gap_open_ts_utc": open_ts.isoformat(),
            "previous_close_ts_utc": prev_close_ts.isoformat(),
            "previous_close_price": prev_close,
            "current_open_price": current_open,
            "gap_high": float(gap_high),
            "gap_low": float(gap_low),
            "gap_mid": float(gap_mid),
            "gap_size_pts": float(gap_size),
            "gap_direction": direction,
        }
        context = {
            "day_of_week_et": et_ts.weekday(),
            "hour_of_day_et": et_ts.hour,
            "gap_type": ctx.mode,
        }
        return ResearchEventCreate(
            feature_name=self.feature_name,
            event_type=ctx.mode or "",
            bar_end_utc=open_ts,
            primary_symbol=symbol,
            symbols=[symbol],
            timeframe=str(_MODE_CONFIG[ctx.mode or ""]["timeframe"]),
            side=direction,
            event_data=event_data,
            context=context,
            outcomes=None,
            replay_pointer={
                "primary_symbol": symbol,
                "ts_utc": open_ts.isoformat(),
                "gap_high": gap_high,
                "gap_low": gap_low,
                "gap_mid": gap_mid,
            },
            detector_version=self.detector_version,
        )


def _iter_globex_days(start_d: date_type, end_d: date_type):
    start_dt = datetime(start_d.year, start_d.month, start_d.day, tzinfo=UTC)
    end_dt = datetime(end_d.year, end_d.month, end_d.day, tzinfo=UTC) + timedelta(days=1)
    cur = globex_day_for(start_dt)
    while cur.start_utc < end_dt:
        yield cur
        cur = globex_day_for(cur.end_utc + timedelta(seconds=1))


def _iter_globex_weeks(start_d: date_type, end_d: date_type):
    start_dt = datetime(start_d.year, start_d.month, start_d.day, tzinfo=UTC)
    end_dt = datetime(end_d.year, end_d.month, end_d.day, tzinfo=UTC) + timedelta(days=1)
    cur = globex_week_for(start_dt)
    while cur.start_utc < end_dt:
        yield cur
        cur = globex_week_for(cur.end_utc + timedelta(seconds=1))


def _safe_load(
    bar_reader: BarReader,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(symbol=symbol, timeframe=timeframe, start=start, end=end)
    except (FileNotFoundError, ValueError) as exc:
        log.info("opening_gap_levels: bar_reader missing %s %s: %s", symbol, timeframe, exc)
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


register("opening_gap_levels", OpeningGapLevelsDetector())
