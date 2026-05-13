"""First-third-of-candle range detector (Ben's idea, 2026-05-10).

For each higher-timeframe candle (weekly / daily), compute the
high/low range over its FIRST 1/3 of time. This range becomes a
level set early in the candle's life — the question being tested:
does breaking out of (or reversing past) this 1/3-range have
predictive value for the rest of the candle?

Concept (Ben):
  "Take the first 1/3 of a candle and mark out that range and see if
  it has any importance. like oh ig it drops 1sd below 1/3 range with
  smt active there's 70% chance price reverses idek"

Modes (start HTF, can go down later):
  - first_third_weekly  (weekly candle, first ~28h of the Globex week)
  - first_third_daily   (daily/Globex candle, first ~8h)

Detection emits ONE event per parent candle, fired at the END of the
first-third (when the range is fully knowable). bar_end_utc = the
last 1m bar timestamp inside the first third. knowable_ts =
first_third_end + 1 minute.

Wide-reach event_data:
  - parent_candle_start/end_utc (period)
  - first_third_start/end_utc
  - first_third_high, first_third_low, first_third_mid, range_pts
  - first_third_open, first_third_close
  - 1sd, 0.5sd of the range (pre-computed quartile-flavored levels)

Outcomes (separate computer): track break above/below first-third
levels for the REST of the parent candle period.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.research.sessions import (
    GlobexPeriod,
    globex_day_for,
    globex_week_for,
)
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)


_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "first_third_daily": {
        "scope": "globex_day",
        "iter": "day",
    },
    "first_third_weekly": {
        "scope": "globex_week",
        "iter": "week",
    },
}


class FirstThirdRangeDetector:
    feature_name: str = "first_third_range"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_CONFIG.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                f"first_third_range requires --mode {{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_CONFIG:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("first_third_range requires at least one symbol")

        cfg = _MODE_CONFIG[ctx.mode]
        events: list[ResearchEventCreate] = []
        for symbol in ctx.symbols:
            events.extend(self._scan_symbol(ctx, symbol, cfg))
        return events

    def _scan_symbol(
        self, ctx: DetectorContext, symbol: str, cfg: dict[str, Any],
    ) -> list[ResearchEventCreate]:
        events: list[ResearchEventCreate] = []
        if cfg["iter"] == "day":
            iterator = _iter_globex_days(ctx.start, ctx.end)
        else:
            iterator = _iter_globex_weeks(ctx.start, ctx.end)
        for period in iterator:
            ev = self._scan_one_period(ctx, symbol, period, ctx.mode)
            if ev is not None:
                events.append(ev)
        return events

    def _scan_one_period(
        self, ctx: DetectorContext, symbol: str,
        period: GlobexPeriod, mode: str,
    ) -> ResearchEventCreate | None:
        # First 1/3 of the period, by wall-clock time.
        period_total = (period.end_utc - period.start_utc)
        first_third_end = period.start_utc + period_total / 3
        # Load 1m bars covering the first third + 1 day buffer (read_bars
        # is date-partitioned, intraday loads need calendar-day spans).
        bars = _safe_load(
            ctx.bar_reader,
            symbol=symbol, timeframe="1m",
            start=period.start_utc,
            end=first_third_end + timedelta(days=1),
        )
        if bars is None or bars.empty:
            return None
        bars = _ensure_utc_index(bars)
        # Strict slice [period.start, first_third_end).
        ft = bars.loc[
            (bars.index >= period.start_utc) & (bars.index < first_third_end)
        ]
        if ft.empty or len(ft) < 2:
            return None
        ft_high = float(ft["high"].max())
        ft_low = float(ft["low"].min())
        ft_open = float(ft["open"].iloc[0])
        ft_close = float(ft["close"].iloc[-1])
        range_pts = ft_high - ft_low
        ft_mid = (ft_high + ft_low) / 2.0

        # Pre-compute level "extensions" beyond the range — useful
        # downstream for "1sd above/below" style checks:
        #   ext_above_high_1x = ft_high + range_pts (1× range above)
        #   ext_below_low_1x  = ft_low - range_pts
        ext_above_high_1x = ft_high + range_pts
        ext_below_low_1x = ft_low - range_pts
        ext_above_high_05x = ft_high + 0.5 * range_pts
        ext_below_low_05x = ft_low - 0.5 * range_pts

        # Direction of the first-third candle itself.
        if ft_close > ft_open:
            direction = "bullish"
        elif ft_close < ft_open:
            direction = "bearish"
        else:
            direction = "doji"

        bar_end_utc = ft.index[-1]
        bar_end_utc = _ts_to_utc(bar_end_utc)
        et_ts = bar_end_utc.astimezone(ET)
        event_data: dict[str, Any] = {
            "schema_version": 1,
            "detector_version": self.detector_version,
            "mode": mode,
            "parent_period_label": period.label,
            "parent_period_start_utc": period.start_utc.isoformat(),
            "parent_period_end_utc": period.end_utc.isoformat(),
            "first_third_start_utc": period.start_utc.isoformat(),
            "first_third_end_utc": first_third_end.isoformat(),
            "first_third_high": ft_high,
            "first_third_low": ft_low,
            "first_third_mid": ft_mid,
            "first_third_range_pts": range_pts,
            "first_third_open": ft_open,
            "first_third_close": ft_close,
            "first_third_direction": direction,
            "ext_above_high_05x_range": ext_above_high_05x,
            "ext_above_high_1x_range": ext_above_high_1x,
            "ext_below_low_05x_range": ext_below_low_05x,
            "ext_below_low_1x_range": ext_below_low_1x,
            "n_1m_bars_in_first_third": int(len(ft)),
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
            timeframe="1D" if "daily" in mode else "1W",
            side=direction,
            event_data=event_data,
            context=context,
            outcomes=None,
            replay_pointer={
                "primary_symbol": symbol,
                "ts_utc": bar_end_utc.isoformat(),
                "first_third_high": ft_high,
                "first_third_low": ft_low,
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
        log.info("first_third: bar_reader missing %s %s: %s", symbol, timeframe, exc)
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


def _ts_to_utc(ts) -> datetime:
    if isinstance(ts, pd.Timestamp):
        ts = ts.to_pydatetime()
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _iter_globex_days(start_d, end_d):
    start_dt = datetime(start_d.year, start_d.month, start_d.day, tzinfo=UTC)
    end_dt = datetime(end_d.year, end_d.month, end_d.day, tzinfo=UTC) + timedelta(days=1)
    cur = globex_day_for(start_dt)
    while cur.start_utc < end_dt:
        yield cur
        cur = globex_day_for(cur.end_utc + timedelta(seconds=1))


def _iter_globex_weeks(start_d, end_d):
    start_dt = datetime(start_d.year, start_d.month, start_d.day, tzinfo=UTC)
    end_dt = datetime(end_d.year, end_d.month, end_d.day, tzinfo=UTC) + timedelta(days=1)
    cur = globex_week_for(start_dt)
    while cur.start_utc < end_dt:
        yield cur
        cur = globex_week_for(cur.end_utc + timedelta(seconds=1))


# ---------- registration ----------

register("first_third_range", FirstThirdRangeDetector())
