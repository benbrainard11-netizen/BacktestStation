"""Displacement candle detector.

Fires on candles whose body is unusually large vs the recent average —
the classic ICT "displacement" / impulse candle, indicating
institutional participation. These candles often:
  - Create FVGs in their wake (3-candle gap pattern)
  - Break market structure
  - Mark the start of a new leg

Detection rule (per-symbol, per-timeframe):
  1. Compute body_pts = abs(close - open) for each bar.
  2. Compute rolling mean of body_pts over the previous N bars (default 20).
  3. Fire when body_pts >= k × rolling_mean (default k=2.0).

Modes are timeframes:
  - 15m_disp / 30m_disp / 1h_disp / 4h_disp / daily_disp

Wide-reach data: store body_pts, range_pts, body/range ratio, the
multiplier vs recent average, plus quartile flags so analysis can
re-bucket on stricter thresholds (3x, 4x, 5x) without re-scanning.

`bar_end_utc` = the displacement candle's bucket-start.
`side` = "bullish" (close > open) or "bearish" (close < open).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)


_MODE_TIMEFRAME: dict[str, str] = {
    "15m_disp": "15m",
    "30m_disp": "30m",
    "1h_disp": "1h",
    "4h_disp": "4h",
    "daily_disp": "1d",
}

LOOKBACK_BARS: int = 20            # rolling-mean window
EMIT_THRESHOLD_RATIO: float = 2.0  # body must be >= 2× recent mean to emit
QUARTILE_RATIOS: tuple[float, ...] = (2.0, 3.0, 4.0, 5.0)


class DisplacementCandleDetector:
    feature_name: str = "displacement_candle"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_TIMEFRAME.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                f"displacement_candle requires --mode {{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_TIMEFRAME:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("displacement_candle requires at least one symbol")

        timeframe = _MODE_TIMEFRAME[ctx.mode]
        # Load extra bars before the start to seed the rolling mean.
        # tf_minutes lookup matches detection timeframe.
        tf_min = {"15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 24 * 60}[timeframe]
        # Pad start by LOOKBACK_BARS * tf_minutes plus a generous extra
        # to handle weekends/holidays.
        start_dt = datetime(ctx.start.year, ctx.start.month, ctx.start.day, tzinfo=UTC)
        end_dt = datetime(ctx.end.year, ctx.end.month, ctx.end.day, tzinfo=UTC)
        load_start = start_dt - timedelta(minutes=tf_min * (LOOKBACK_BARS + 5) + 60)

        events: list[ResearchEventCreate] = []
        for symbol in ctx.symbols:
            df = _safe_load(
                ctx.bar_reader,
                symbol=symbol, timeframe=timeframe,
                start=load_start, end=end_dt,
            )
            if df is None or df.empty:
                log.info("displacement: missing %s %s bars", symbol, timeframe)
                continue
            df = _ensure_utc_index(df)
            events.extend(
                self._scan_symbol(
                    df=df, symbol=symbol, mode=ctx.mode, timeframe=timeframe,
                    scan_start=start_dt, scan_end=end_dt,
                )
            )
        return events

    def _scan_symbol(
        self,
        *,
        df: pd.DataFrame,
        symbol: str,
        mode: str,
        timeframe: str,
        scan_start: datetime,
        scan_end: datetime,
    ) -> list[ResearchEventCreate]:
        if len(df) < LOOKBACK_BARS + 1:
            return []
        body_pts = (df["close"] - df["open"]).abs()
        # Rolling mean of body_pts over the PREVIOUS N bars (exclude current).
        rolling = body_pts.rolling(LOOKBACK_BARS, min_periods=LOOKBACK_BARS).mean()
        rolling_prev = rolling.shift(1)  # exclude the current bar from its own mean

        events: list[ResearchEventCreate] = []
        for i in range(LOOKBACK_BARS, len(df)):
            ts = df.index[i]
            if ts < scan_start or ts >= scan_end:
                continue
            body = float(body_pts.iloc[i])
            mean_prev = rolling_prev.iloc[i]
            if pd.isna(mean_prev) or mean_prev == 0:
                continue
            ratio = body / float(mean_prev)
            if ratio < EMIT_THRESHOLD_RATIO:
                continue

            o = float(df["open"].iloc[i])
            h = float(df["high"].iloc[i])
            low_v = float(df["low"].iloc[i])
            c = float(df["close"].iloc[i])
            range_pts = h - low_v
            direction: Literal["bullish", "bearish"] = (
                "bullish" if c > o else ("bearish" if c < o else "doji")
            )
            if direction == "doji":
                # body == 0 means ratio is technically infinite; we
                # already filter on body / mean ≥ threshold, but a
                # zero-body candle isn't a displacement candle.
                continue

            quartiles_hit = [
                q for q in QUARTILE_RATIOS if ratio >= q
            ]
            ts_utc = _ts_to_utc(ts)
            et_ts = ts_utc.astimezone(ET)
            event_data: dict[str, Any] = {
                "schema_version": 1,
                "detector_version": self.detector_version,
                "tracking_timeframe": timeframe,
                "direction": direction,
                "candle": {
                    "ts_utc": ts_utc.isoformat(),
                    "open": o, "high": h, "low": low_v, "close": c,
                },
                "body_pts": float(body),
                "range_pts": float(range_pts),
                "body_to_range_ratio": (
                    float(body / range_pts) if range_pts > 0 else None
                ),
                "rolling_mean_body_pts": float(mean_prev),
                "ratio_vs_recent_mean": float(ratio),
                "ratio_quartiles_hit": quartiles_hit,
                "is_2x": ratio >= 2.0,
                "is_3x": ratio >= 3.0,
                "is_4x": ratio >= 4.0,
                "is_5x": ratio >= 5.0,
                "lookback_bars": LOOKBACK_BARS,
            }
            context: dict[str, Any] = {
                "tracking_timeframe": timeframe,
                "day_of_week_et": et_ts.weekday(),
                "hour_of_day_et": et_ts.hour,
            }
            events.append(ResearchEventCreate(
                feature_name=self.feature_name,
                event_type=mode,
                bar_end_utc=ts_utc,
                primary_symbol=symbol,
                symbols=[symbol],
                timeframe=timeframe.upper(),
                side=direction,
                event_data=event_data,
                context=context,
                outcomes=None,
                replay_pointer={
                    "primary_symbol": symbol,
                    "ts_utc": ts_utc.isoformat(),
                    "tracking_timeframe": timeframe,
                },
                detector_version=self.detector_version,
            ))
        return events


# ---------- helpers ----------


def _safe_load(
    bar_reader: BarReader,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(
            symbol=symbol, timeframe=timeframe, start=start, end=end,
        )
    except (FileNotFoundError, ValueError) as exc:
        log.info("displacement: bar_reader missing for %s %s: %s",
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


def _ts_to_utc(ts) -> datetime:
    if isinstance(ts, pd.Timestamp):
        ts = ts.to_pydatetime()
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


# ---------- registration ----------

register("displacement_candle", DisplacementCandleDetector())
