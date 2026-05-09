"""FVG (Fair Value Gap) formation detector.

Detects the classic 3-candle gap pattern: a candle whose move is so
decisive that the candle before it and the candle after it don't
overlap. The unfilled space between candle 1 and candle 3 is the
"fair value gap" — price is expected to come back and "mitigate" it.

Definition (per Ben's vocabulary 2026-05-09):

  Bullish FVG: candle 1 high < candle 3 low
               → unfilled gap above candle 1
               → measures rejection of lower prices
  Bearish FVG: candle 1 low > candle 3 high
               → unfilled gap below candle 1
               → measures rejection of higher prices

Detection runs PER SYMBOL — each of NQ/ES/YM gets its own FVG events.
Unlike SMT/PSP which compare across symbols, FVG is a single-symbol
pattern. The composite layer can later ask "did an FVG fire near an
SMT/PSP" via SQL joins on `bar_end_utc`.

Modes (v1):
  - daily_fvg: 1d bucket — UTC calendar day. NOT Globex-aligned.
  - 4h_fvg:    4h bucket — UTC 00/04/08/12/16/20.
  - 1h_fvg:    1h bucket — UTC clock hours.

event_type = mode; side = "bullish" | "bearish".
primary_symbol = the symbol the FVG formed on.
bar_end_utc = candle-3's bucket-start timestamp (the bar that
              confirmed the gap on close).

idempotency: feature_name + primary_symbol + bar_end_utc + event_type
hashed to event_id. Same as other detectors.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)


_MODE_TIMEFRAME: dict[str, str] = {
    "daily_fvg": "1d",
    "4h_fvg": "4h",
    "1h_fvg": "1h",
}


class FvgFormationDetector:
    feature_name: str = "fvg_formation"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_TIMEFRAME.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                "fvg_formation requires --mode "
                f"{{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_TIMEFRAME:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("FVG detector requires at least one symbol")

        timeframe = _MODE_TIMEFRAME[ctx.mode]
        start_dt = datetime(ctx.start.year, ctx.start.month, ctx.start.day, tzinfo=UTC)
        end_dt = datetime(ctx.end.year, ctx.end.month, ctx.end.day, tzinfo=UTC)

        events: list[ResearchEventCreate] = []
        for symbol in ctx.symbols:
            df = _safe_load(
                ctx.bar_reader,
                symbol=symbol, timeframe=timeframe,
                start=start_dt, end=end_dt,
            )
            if df is None or df.empty:
                log.info("fvg: missing %s %s bars; skipping", symbol, timeframe)
                continue
            df = _ensure_utc_index(df)
            events.extend(
                self._scan_symbol(
                    df=df, symbol=symbol, mode=ctx.mode, timeframe=timeframe,
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
    ) -> list[ResearchEventCreate]:
        if len(df) < 3:
            return []
        events: list[ResearchEventCreate] = []
        # Iterate by integer position so we can index i-2, i-1, i.
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        opens = df["open"].to_numpy()
        closes = df["close"].to_numpy()
        idx = df.index

        for i in range(2, len(df)):
            c1_high = float(highs[i - 2])
            c1_low = float(lows[i - 2])
            c3_high = float(highs[i])
            c3_low = float(lows[i])

            if c1_high < c3_low:
                direction: Literal["bullish", "bearish"] = "bullish"
                fvg_high = c3_low
                fvg_low = c1_high
            elif c1_low > c3_high:
                direction = "bearish"
                fvg_high = c1_low
                fvg_low = c3_high
            else:
                continue

            ts_c1 = idx[i - 2]
            ts_c2 = idx[i - 1]
            ts_c3 = idx[i]
            ts_c3_utc = _ts_to_utc(ts_c3)

            event_data: dict[str, Any] = {
                "schema_version": 1,
                "detector_version": self.detector_version,
                "tracking_timeframe": timeframe,
                "direction": direction,
                "fvg_high": float(fvg_high),
                "fvg_low": float(fvg_low),
                "fvg_mid": float((fvg_high + fvg_low) / 2.0),
                "fvg_width_pts": float(fvg_high - fvg_low),
                "candle_1": {
                    "ts_utc": _ts_to_utc(ts_c1).isoformat(),
                    "open": float(opens[i - 2]),
                    "high": float(highs[i - 2]),
                    "low": float(lows[i - 2]),
                    "close": float(closes[i - 2]),
                },
                "candle_2": {
                    "ts_utc": _ts_to_utc(ts_c2).isoformat(),
                    "open": float(opens[i - 1]),
                    "high": float(highs[i - 1]),
                    "low": float(lows[i - 1]),
                    "close": float(closes[i - 1]),
                },
                "candle_3": {
                    "ts_utc": ts_c3_utc.isoformat(),
                    "open": float(opens[i]),
                    "high": float(highs[i]),
                    "low": float(lows[i]),
                    "close": float(closes[i]),
                },
            }

            et_ts = ts_c3_utc.astimezone(ET)
            context: dict[str, Any] = {
                "day_of_week_et": et_ts.weekday(),
                "hour_of_day_et": et_ts.hour,
                "tracking_timeframe": timeframe,
            }

            events.append(ResearchEventCreate(
                feature_name=self.feature_name,
                event_type=mode,
                bar_end_utc=ts_c3_utc,
                primary_symbol=symbol,
                symbols=[symbol],
                timeframe=timeframe.upper(),
                side=direction,
                event_data=event_data,
                context=context,
                outcomes=None,
                replay_pointer={
                    "primary_symbol": symbol,
                    "ts_utc": ts_c3_utc.isoformat(),
                    "tracking_timeframe": timeframe,
                    "fvg_high": float(fvg_high),
                    "fvg_low": float(fvg_low),
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
        log.info("bar_reader missing for %s %s: %s", symbol, timeframe, exc)
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

register("fvg_formation", FvgFormationDetector())
