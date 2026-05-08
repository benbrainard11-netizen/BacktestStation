"""PSP (Precision Swing Point) candle divergence detector.

Detects when correlated index futures (NQ, ES, YM) print candles of
DIFFERENT directions on the same time bucket. The classic SMT-trader
read: when the indices disagree on direction within the same candle,
the lone diverger is the "PSP" and is informative on its own AND
when it lines up with a swept level (an SMT event).

Definition (per Ben's reading 2026-05-08):

  > A PSP is just a candle that's at the same time but has a different
  > close. So if week 1 on NQ closes bullish and that same week closes
  > bearish on ES or YM, that's a PSP. Confirmed only after close. Just
  > one asset needs to be diverged for it to be true.

Detection rule:

  For each candle in the scan window (per `mode`'s tracking timeframe):
    direction[sym] = "bullish"  if close > open
                     "bearish"  if close < open
                     "doji"     if close == open
    Skip if any symbol is a doji (v1 — keep the rule clean).
    Skip if all symbols share the same direction.
    Otherwise, the minority direction wins.
      With 3 symbols and 0 dojis, the split is always 1-vs-2 or 3-0.
    Fire one event with primary_symbol = alphabetically-first minority
    (stable + deterministic, mirrors SMT detector's tie-breaker).

Modes (v1):

  - daily_psp:  1d bucket  — UTC calendar day. NOT Globex-aligned.
                            v2 will use anchored Globex day.
  - 4h_psp:     4h bucket  — floors to UTC 00/04/08/12/16/20.
  - 1h_psp:     1h bucket  — floors to UTC clock hours.

Modes deferred to v2:

  - 6h_psp / weekly_psp: app.data.reader.read_bars doesn't
    natively support these timeframes; would need either an
    extension to read_bars or anchored 1m aggregation.

Composability with SMT:

  PSPs are interesting on their own and (per Ben's reading) more
  interesting when they line up with an SMT event — e.g. a
  previous_day_smt that fires AND a 4h_psp confirming the same
  side within the same window. Cross-detector queries are SQL
  joins on `bar_end_utc` proximity in the unified
  `research_events` table.

See `docs/RESEARCH_KNOWLEDGE_LAYER.md` for the surrounding taxonomy
and `docs/RESEARCH_DETECTORS.md` for how detectors are added.
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


# Mode → tracking timeframe string for read_bars
_MODE_TIMEFRAME: dict[str, str] = {
    "daily_psp": "1d",
    "4h_psp": "4h",
    "1h_psp": "1h",
}


class PspCandleDivergenceDetector:
    feature_name: str = "psp_candle_divergence"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_TIMEFRAME.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                "psp_candle_divergence requires --mode "
                f"{{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_TIMEFRAME:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if len(ctx.symbols) < 2:
            raise ValueError(
                "PSP requires at least 2 symbols (got "
                f"{len(ctx.symbols)})"
            )

        timeframe = _MODE_TIMEFRAME[ctx.mode]
        start_dt = datetime(ctx.start.year, ctx.start.month, ctx.start.day, tzinfo=UTC)
        end_dt = datetime(ctx.end.year, ctx.end.month, ctx.end.day, tzinfo=UTC)

        # Load tracking bars for every symbol. None = skip the whole
        # scan (we need ALL symbols to compare directions).
        symbol_frames: dict[str, pd.DataFrame] = {}
        for sym in ctx.symbols:
            df = _safe_load(
                ctx.bar_reader,
                symbol=sym,
                timeframe=timeframe,
                start=start_dt,
                end=end_dt,
            )
            if df is None or df.empty:
                log.info(
                    "psp: missing bars for %s in %s — skipping scan",
                    sym, timeframe,
                )
                return []
            symbol_frames[sym] = _ensure_utc_index(df)

        # Inner join on bucket timestamps — only candles where all
        # symbols printed get evaluated.
        common_index = _intersect_indices(list(symbol_frames.values()))
        if len(common_index) == 0:
            return []

        events: list[ResearchEventCreate] = []
        for ts in common_index:
            event = self._scan_one_candle(
                ts=ts,
                symbol_frames=symbol_frames,
                symbols=ctx.symbols,
                mode=ctx.mode,
                timeframe=timeframe,
            )
            if event is not None:
                events.append(event)

        return events

    def _scan_one_candle(
        self,
        *,
        ts: pd.Timestamp,
        symbol_frames: dict[str, pd.DataFrame],
        symbols: list[str],
        mode: str,
        timeframe: str,
    ) -> ResearchEventCreate | None:
        per_symbol: dict[str, dict[str, Any]] = {}
        directions: dict[str, str] = {}

        for sym in symbols:
            row = symbol_frames[sym].loc[ts]
            # If duplicated index (shouldn't happen but defensively),
            # iloc[0] picks the first.
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            open_p = float(row["open"])
            close_p = float(row["close"])
            if close_p > open_p:
                d = "bullish"
            elif close_p < open_p:
                d = "bearish"
            else:
                d = "doji"
            directions[sym] = d
            per_symbol[sym] = {
                "open": open_p,
                "close": close_p,
                "high": float(row["high"]),
                "low": float(row["low"]),
                "direction": d,
                "body_pts": float(close_p - open_p),
            }

        # v1 rule: skip if any doji. Keeps the rule clean. v2 can
        # branch on doji-vs-non-doji distribution.
        if any(d == "doji" for d in directions.values()):
            return None

        bull_syms = sorted(s for s, d in directions.items() if d == "bullish")
        bear_syms = sorted(s for s, d in directions.items() if d == "bearish")

        if not bull_syms or not bear_syms:
            return None  # 3-0 split — no PSP

        # Minority direction — for ties (e.g. 2-vs-2 with 4 symbols),
        # bullish wins by convention. Document this if scaling to more
        # than 3 symbols.
        if len(bull_syms) <= len(bear_syms):
            minority_direction: Literal["bullish", "bearish"] = "bullish"
            minority_symbols = bull_syms
            majority_symbols = bear_syms
        else:
            minority_direction = "bearish"
            minority_symbols = bear_syms
            majority_symbols = bull_syms

        # Stable primary_symbol — alphabetical lone-diverger
        primary = minority_symbols[0]

        ts_utc = ts.to_pydatetime() if isinstance(ts, pd.Timestamp) else ts
        if ts_utc.tzinfo is None:
            ts_utc = ts_utc.replace(tzinfo=UTC)
        et_ts = ts_utc.astimezone(ET)

        event_data: dict[str, Any] = {
            "schema_version": 1,
            "detector_version": self.detector_version,
            "tracking_timeframe": timeframe,
            "minority_direction": minority_direction,
            "minority_symbols": minority_symbols,
            "majority_symbols": majority_symbols,
            "bullish_symbols": bull_syms,
            "bearish_symbols": bear_syms,
            "per_symbol_states": per_symbol,
        }
        context: dict[str, Any] = {
            "day_of_week_et": et_ts.weekday(),
            "hour_of_day_et": et_ts.hour,
            "tracking_timeframe": timeframe,
        }
        return ResearchEventCreate(
            feature_name=self.feature_name,
            event_type=mode,
            bar_end_utc=ts_utc,
            primary_symbol=primary,
            symbols=list(symbols),
            timeframe=timeframe.upper(),
            side=minority_direction,
            event_data=event_data,
            context=context,
            outcomes=None,
            replay_pointer={
                "primary_symbol": primary,
                "ts_utc": ts_utc.isoformat(),
                "tracking_timeframe": timeframe,
            },
            detector_version=self.detector_version,
        )


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
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
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


def _intersect_indices(frames: list[pd.DataFrame]) -> pd.DatetimeIndex:
    """Inner-join the indices of all frames. We only score candles
    that printed on every symbol — comparing direction requires data
    for all of them at the same bucket."""
    if not frames:
        return pd.DatetimeIndex([], tz=UTC)
    common = frames[0].index
    for f in frames[1:]:
        common = common.intersection(f.index)
    return common.sort_values()


# ---------- registration ----------

register("psp_candle_divergence", PspCandleDivergenceDetector())
