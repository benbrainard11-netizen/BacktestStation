"""Opening Range Breakout (ORB) detector.

Captures the high/low of the first N minutes of a session open. The
range is fully knowable at session_open + N. The "breakout" question
is tested by the outcomes computer (did price break high/low later
in the session, when, post-break MFE/MAE).

Modes:
  - ny_5m, ny_15m, ny_30m   — opening range of N minutes after 09:30 ET
  - asia_60m                — opening range of 60 min after 18:00 ET (Globex day open)

This detector emits ONE event per session-open per symbol. The event
fires AT session_open + N (when the range is fully knowable). For
zero look-ahead use: don't trade off the range until knowable_ts.
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.research.sessions import (
    GlobexPeriod,
    globex_day_for,
)
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)


# Each mode: open_hour_et, open_minute_et, range_minutes.
_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "ny_5m":   {"open_hour_et": 9,  "open_min_et": 30, "range_minutes": 5},
    "ny_15m":  {"open_hour_et": 9,  "open_min_et": 30, "range_minutes": 15},
    "ny_30m":  {"open_hour_et": 9,  "open_min_et": 30, "range_minutes": 30},
    "asia_60m": {"open_hour_et": 18, "open_min_et": 0,  "range_minutes": 60},
}


class OpeningRangeBreakoutDetector:
    feature_name: str = "opening_range_breakout"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_CONFIG.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                f"opening_range_breakout requires --mode {{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_CONFIG:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("opening_range_breakout requires at least one symbol")
        cfg = _MODE_CONFIG[ctx.mode]
        events: list[ResearchEventCreate] = []
        for symbol in ctx.symbols:
            events.extend(self._scan_symbol(ctx, symbol, cfg))
        return events

    def _scan_symbol(
        self, ctx: DetectorContext, symbol: str, cfg: dict[str, Any],
    ) -> list[ResearchEventCreate]:
        events: list[ResearchEventCreate] = []
        # Iterate Globex days; each day has one session-open at the
        # configured ET hour:minute.
        for day in _iter_globex_days(ctx.start, ctx.end):
            ev = self._scan_one_day(ctx, symbol, cfg, day, ctx.mode)
            if ev is not None:
                events.append(ev)
        return events

    def _scan_one_day(
        self,
        ctx: DetectorContext, symbol: str,
        cfg: dict[str, Any], day: GlobexPeriod, mode: str,
    ) -> ResearchEventCreate | None:
        # Compute session open time in UTC for THIS Globex day.
        day_start_et = day.start_utc.astimezone(ET)  # 18:00 ET (or Sun 18:00)
        # The session open hour is on day_start.date() (for asia 18:00) OR
        # day_start.date() + 1 (for ny 09:30 next morning).
        if cfg["open_hour_et"] >= 18:
            # Asia 18:00 ET — same calendar date as day_start_et.
            open_date_et = day_start_et.date()
        else:
            # NY (or earlier-hour) — next calendar day.
            open_date_et = day_start_et.date() + timedelta(days=1)
        open_et = datetime.combine(
            open_date_et,
            time(cfg["open_hour_et"], cfg["open_min_et"]),
            tzinfo=ET,
        )
        open_utc = open_et.astimezone(UTC)
        range_end_utc = open_utc + timedelta(minutes=cfg["range_minutes"])
        # Skip if open is outside the Globex day.
        if not (day.start_utc <= open_utc < day.end_utc):
            return None

        # Load 1m bars for opening range, padded for date partition.
        bars = _safe_load(
            ctx.bar_reader,
            symbol=symbol, timeframe="1m",
            start=open_utc, end=range_end_utc + timedelta(days=1),
        )
        if bars is None or bars.empty:
            return None
        bars = _ensure_utc_index(bars)
        rng = bars[(bars.index >= open_utc) & (bars.index < range_end_utc)]
        if rng.empty or len(rng) < 1:
            return None

        rng_high = float(rng["high"].max())
        rng_low = float(rng["low"].min())
        rng_open = float(rng["open"].iloc[0])
        rng_close = float(rng["close"].iloc[-1])
        range_pts = rng_high - rng_low
        rng_mid = (rng_high + rng_low) / 2.0
        if rng_close > rng_open:
            direction = "bullish"
        elif rng_close < rng_open:
            direction = "bearish"
        else:
            direction = "doji"

        bar_end_utc = range_end_utc  # event fires AT range close
        et_ts = bar_end_utc.astimezone(ET)
        event_data: dict[str, Any] = {
            "schema_version": 1,
            "detector_version": self.detector_version,
            "mode": mode,
            "session_open_utc": open_utc.isoformat(),
            "session_open_et": open_et.isoformat(),
            "range_end_utc": range_end_utc.isoformat(),
            "range_minutes": cfg["range_minutes"],
            "or_high": rng_high,
            "or_low": rng_low,
            "or_mid": rng_mid,
            "or_range_pts": range_pts,
            "or_open": rng_open,
            "or_close": rng_close,
            "or_direction": direction,
            "ext_above_high_05x": rng_high + 0.5 * range_pts,
            "ext_above_high_1x": rng_high + 1.0 * range_pts,
            "ext_below_low_05x": rng_low - 0.5 * range_pts,
            "ext_below_low_1x": rng_low - 1.0 * range_pts,
            "globex_day_start_utc": day.start_utc.isoformat(),
            "globex_day_end_utc": day.end_utc.isoformat(),
            "n_bars_in_range": int(len(rng)),
        }
        context: dict[str, Any] = {
            "day_of_week_et": et_ts.weekday(),
            "hour_of_day_et": et_ts.hour,
        }
        return ResearchEventCreate(
            feature_name=self.feature_name,
            event_type=mode,
            bar_end_utc=bar_end_utc,
            primary_symbol=symbol,
            symbols=[symbol],
            timeframe=f"{cfg['range_minutes']}M",
            side=direction,
            event_data=event_data,
            context=context,
            outcomes=None,
            replay_pointer={
                "primary_symbol": symbol,
                "ts_utc": bar_end_utc.isoformat(),
                "or_high": rng_high,
                "or_low": rng_low,
            },
            detector_version=self.detector_version,
        )


# ---------- helpers ----------


def _safe_load(
    bar_reader: BarReader,
    *, symbol: str, timeframe: str, start: datetime, end: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(symbol=symbol, timeframe=timeframe, start=start, end=end)
    except (FileNotFoundError, ValueError) as exc:
        log.info("orb: bar_reader missing %s %s: %s", symbol, timeframe, exc)
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


def _iter_globex_days(start_d, end_d):
    start_dt = datetime(start_d.year, start_d.month, start_d.day, tzinfo=UTC)
    end_dt = datetime(end_d.year, end_d.month, end_d.day, tzinfo=UTC) + timedelta(days=1)
    cur = globex_day_for(start_dt)
    while cur.start_utc < end_dt:
        yield cur
        cur = globex_day_for(cur.end_utc + timedelta(seconds=1))


# ---------- registration ----------

register("opening_range_breakout", OpeningRangeBreakoutDetector())
