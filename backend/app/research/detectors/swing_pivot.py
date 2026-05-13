"""Swing pivot detector.

Detects N-bar swing pivots: a candle whose high is greater than N bars
before AND N bars after (swing high), or whose low is less than N bars
before AND N bars after (swing low).

Foundational structure detector. Swing highs and lows form the
backbone of market-structure analysis: HH/HL = uptrend, LH/LL =
downtrend. Each swing pivot creates a level that subsequent price
action either respects (holds) or violates (breaks structure).

Modes:
  - pivot_3_1h, pivot_5_1h           (1h candles, N=3 / N=5)
  - pivot_3_4h, pivot_5_4h           (4h candles)
  - pivot_5_daily                    (daily candles)

bar_end_utc = the pivot bar's bucket-start (when the high/low was made).
knowable_ts = pivot_bar.bar_end_utc + (N+1) × bucket_minutes (when the
right side of N bars closed and the pivot became confirmable).

Wide-reach data: full OHLC of pivot bar + N bars on each side; the N
parameter; bar timestamps. Re-bucketing on different N values would
require re-scan, but within one mode the data is rich.

Side = "high" (swing high) or "low" (swing low). Symbol-by-symbol;
swings are single-symbol patterns.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)


_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "pivot_3_1h":   {"n": 3, "tf": "1h", "tf_minutes": 60},
    "pivot_5_1h":   {"n": 5, "tf": "1h", "tf_minutes": 60},
    "pivot_3_4h":   {"n": 3, "tf": "4h", "tf_minutes": 240},
    "pivot_5_4h":   {"n": 5, "tf": "4h", "tf_minutes": 240},
    "pivot_5_daily": {"n": 5, "tf": "1d", "tf_minutes": 24 * 60},
}


class SwingPivotDetector:
    feature_name: str = "swing_pivot"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_CONFIG.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                f"swing_pivot requires --mode {{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_CONFIG:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("swing_pivot requires at least one symbol")

        cfg = _MODE_CONFIG[ctx.mode]
        n = cfg["n"]
        tf = cfg["tf"]
        tf_min = cfg["tf_minutes"]
        # Pad start to seed N bars before, end to confirm N bars after.
        start_dt = datetime(ctx.start.year, ctx.start.month, ctx.start.day, tzinfo=UTC)
        end_dt = datetime(ctx.end.year, ctx.end.month, ctx.end.day, tzinfo=UTC)
        load_start = start_dt - timedelta(minutes=tf_min * (n + 5) + 60)
        load_end = end_dt + timedelta(minutes=tf_min * (n + 5) + 60)

        events: list[ResearchEventCreate] = []
        for symbol in ctx.symbols:
            df = _safe_load(
                ctx.bar_reader,
                symbol=symbol, timeframe=tf,
                start=load_start, end=load_end,
            )
            if df is None or df.empty:
                continue
            df = _ensure_utc_index(df)
            events.extend(
                self._scan_symbol(
                    df=df, symbol=symbol, mode=ctx.mode, cfg=cfg,
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
        cfg: dict[str, Any],
        scan_start: datetime,
        scan_end: datetime,
    ) -> list[ResearchEventCreate]:
        n = cfg["n"]
        tf = cfg["tf"]
        tf_min = cfg["tf_minutes"]
        if len(df) < 2 * n + 1:
            return []

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        opens = df["open"].to_numpy()
        closes = df["close"].to_numpy()
        idx = df.index

        events: list[ResearchEventCreate] = []
        for i in range(n, len(df) - n):
            ts = idx[i]
            if ts < scan_start or ts >= scan_end:
                continue
            # Swing high: high[i] > all neighbors' highs, strict.
            window = slice(i - n, i + n + 1)
            window_highs = highs[window]
            window_lows = lows[window]
            is_swing_high = float(highs[i]) == float(window_highs.max()) and \
                np.sum(window_highs == highs[i]) == 1
            is_swing_low = float(lows[i]) == float(window_lows.min()) and \
                np.sum(window_lows == lows[i]) == 1
            if not (is_swing_high or is_swing_low):
                continue
            # Both at the same bar is rare but possible (extreme outside bar);
            # emit two events, one per side.
            for side, is_pivot in (("high", is_swing_high), ("low", is_swing_low)):
                if not is_pivot:
                    continue
                pivot_price = float(highs[i] if side == "high" else lows[i])
                ts_utc = _ts_to_utc(ts)
                # knowable_ts = pivot bar close + N more bars closed.
                # = ts + (n+1) * tf_minutes
                knowable_ts = ts_utc + timedelta(minutes=tf_min * (n + 1))
                # Surrounding bars OHLC for context.
                left_bars = []
                right_bars = []
                for j in range(i - n, i):
                    left_bars.append({
                        "ts_utc": _ts_to_utc(idx[j]).isoformat(),
                        "open": float(opens[j]), "high": float(highs[j]),
                        "low": float(lows[j]), "close": float(closes[j]),
                    })
                for j in range(i + 1, i + n + 1):
                    right_bars.append({
                        "ts_utc": _ts_to_utc(idx[j]).isoformat(),
                        "open": float(opens[j]), "high": float(highs[j]),
                        "low": float(lows[j]), "close": float(closes[j]),
                    })
                et_ts = ts_utc.astimezone(ET)
                event_data: dict[str, Any] = {
                    "schema_version": 1,
                    "detector_version": self.detector_version,
                    "n": n,
                    "tracking_timeframe": tf,
                    "side": side,
                    "pivot_price": pivot_price,
                    "pivot_bar": {
                        "ts_utc": ts_utc.isoformat(),
                        "open": float(opens[i]), "high": float(highs[i]),
                        "low": float(lows[i]), "close": float(closes[i]),
                    },
                    "left_bars": left_bars,
                    "right_bars": right_bars,
                    "knowable_ts_utc": knowable_ts.isoformat(),
                }
                context: dict[str, Any] = {
                    "tracking_timeframe": tf,
                    "day_of_week_et": et_ts.weekday(),
                    "hour_of_day_et": et_ts.hour,
                }
                events.append(ResearchEventCreate(
                    feature_name=self.feature_name,
                    event_type=mode,
                    bar_end_utc=ts_utc,
                    primary_symbol=symbol,
                    symbols=[symbol],
                    timeframe=tf.upper(),
                    side=side,
                    event_data=event_data,
                    context=context,
                    outcomes=None,
                    replay_pointer={
                        "primary_symbol": symbol,
                        "ts_utc": ts_utc.isoformat(),
                        "tracking_timeframe": tf,
                        "pivot_price": pivot_price,
                    },
                    detector_version=self.detector_version,
                ))
        return events


# ---------- helpers ----------


def _safe_load(
    bar_reader: BarReader,
    *, symbol: str, timeframe: str, start: datetime, end: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(symbol=symbol, timeframe=timeframe, start=start, end=end)
    except (FileNotFoundError, ValueError) as exc:
        log.info("swing_pivot: bar_reader missing for %s %s: %s", symbol, timeframe, exc)
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

register("swing_pivot", SwingPivotDetector())
