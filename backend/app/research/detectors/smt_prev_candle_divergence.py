"""Previous-candle SMT divergence across correlated symbols.

This is the lower-timeframe SMT complement to
`smt_htf_reference_divergence`.

For each timeframe candle, compare every symbol against its own previous
candle high/low. A high-side SMT fires when at least one symbol wicks above
its previous candle high while at least one peer does not. A low-side SMT is
the mirror against previous candle lows.

Events are confirmed only after the current candle closes. The detector still
records wick-based SMTs, then tags whether the divergence was close-confirmed
(`close_confirmed_at_close`) so research can compare wick-only vs close-confirmed
SMT without rescanning.
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

Side = Literal["high", "low"]

_MODE_TIMEFRAME: dict[str, str] = {
    "15m_prev_candle_smt": "15m",
    "30m_prev_candle_smt": "30m",
    "1h_prev_candle_smt": "1h",
    "90m_prev_candle_smt": "90m",
    "4h_prev_candle_smt": "4h",
    "6h_prev_candle_smt": "6h",
}
_TIMEFRAME_MINUTES = {
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "90m": 90,
    "4h": 4 * 60,
    "6h": 6 * 60,
}


class SmtPrevCandleDivergenceDetector:
    feature_name: str = "smt_prev_candle_divergence"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_TIMEFRAME)

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                "smt_prev_candle_divergence requires --mode "
                f"{{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_TIMEFRAME:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if len(ctx.symbols) < 2:
            raise ValueError(f"SMT requires at least 2 symbols (got {len(ctx.symbols)})")

        timeframe = _MODE_TIMEFRAME[ctx.mode]
        start_dt = datetime(ctx.start.year, ctx.start.month, ctx.start.day, tzinfo=UTC)
        end_dt = datetime(ctx.end.year, ctx.end.month, ctx.end.day, tzinfo=UTC)

        symbol_frames: dict[str, pd.DataFrame] = {}
        for symbol in ctx.symbols:
            df = _safe_load(
                ctx.bar_reader,
                symbol=symbol,
                timeframe=timeframe,
                start=start_dt,
                end=end_dt,
            )
            if df is None or df.empty:
                log.info("smt_prev_candle: missing bars for %s %s", symbol, timeframe)
                return []
            symbol_frames[symbol] = _ensure_utc_index(df).sort_index()

        common_index = _intersect_indices(list(symbol_frames.values()))
        if len(common_index) < 2:
            return []

        events: list[ResearchEventCreate] = []
        for i in range(1, len(common_index)):
            prev_ts = common_index[i - 1]
            cur_ts = common_index[i]
            for side in ("high", "low"):
                event = self._scan_one_candle(
                    mode=ctx.mode,
                    timeframe=timeframe,
                    symbols=ctx.symbols,
                    symbol_frames=symbol_frames,
                    prev_ts=prev_ts,
                    cur_ts=cur_ts,
                    side=side,  # type: ignore[arg-type]
                )
                if event is not None:
                    events.append(event)
        return events

    def _scan_one_candle(
        self,
        *,
        mode: str,
        timeframe: str,
        symbols: list[str],
        symbol_frames: dict[str, pd.DataFrame],
        prev_ts: pd.Timestamp,
        cur_ts: pd.Timestamp,
        side: Side,
    ) -> ResearchEventCreate | None:
        per_symbol: dict[str, dict[str, Any]] = {}
        swept_symbols: list[str] = []
        close_confirmed_symbols: list[str] = []
        closed_back_inside_symbols: list[str] = []

        for symbol in symbols:
            prev = _row_at(symbol_frames[symbol], prev_ts)
            cur = _row_at(symbol_frames[symbol], cur_ts)
            ref_high = float(prev["high"])
            ref_low = float(prev["low"])
            cur_high = float(cur["high"])
            cur_low = float(cur["low"])
            cur_close = float(cur["close"])
            if side == "high":
                swept = cur_high > ref_high
                close_confirmed = cur_close > ref_high
                sweep_price = cur_high
                reference_price = ref_high
            else:
                swept = cur_low < ref_low
                close_confirmed = cur_close < ref_low
                sweep_price = cur_low
                reference_price = ref_low

            if swept:
                swept_symbols.append(symbol)
                if close_confirmed:
                    close_confirmed_symbols.append(symbol)
                else:
                    closed_back_inside_symbols.append(symbol)

            per_symbol[symbol] = {
                "previous_open": float(prev["open"]),
                "previous_high": ref_high,
                "previous_low": ref_low,
                "previous_close": float(prev["close"]),
                "current_open": float(cur["open"]),
                "current_high": cur_high,
                "current_low": cur_low,
                "current_close": cur_close,
                "reference_price": reference_price,
                "swept": bool(swept),
                "close_confirmed": bool(close_confirmed),
                "sweep_price": sweep_price if swept else None,
                "sweep_distance_pts": float(abs(sweep_price - reference_price)) if swept else 0.0,
            }

        if not swept_symbols or len(swept_symbols) == len(symbols):
            return None

        holding_symbols = sorted(set(symbols) - set(swept_symbols))
        close_holding_symbols = sorted(set(symbols) - set(close_confirmed_symbols))
        close_confirmed_at_close = 0 < len(close_confirmed_symbols) < len(symbols)
        primary = sorted(swept_symbols)[0]
        primary_close_confirmed = primary in close_confirmed_symbols

        cur_start = cur_ts.to_pydatetime()
        if cur_start.tzinfo is None:
            cur_start = cur_start.replace(tzinfo=UTC)
        cur_close_ts = cur_start + pd.Timedelta(minutes=_TIMEFRAME_MINUTES[timeframe]).to_pytimedelta()
        et_close = cur_close_ts.astimezone(ET)
        prev_start = prev_ts.to_pydatetime()
        if prev_start.tzinfo is None:
            prev_start = prev_start.replace(tzinfo=UTC)

        event_data: dict[str, Any] = {
            "schema_version": 1,
            "detector_version": self.detector_version,
            "reference_mode": "previous_candle",
            "base_event_type": mode,
            "tracking_timeframe": timeframe,
            "timeframe_minutes": _TIMEFRAME_MINUTES[timeframe],
            "side": side,
            "thesis_direction": "down" if side == "high" else "up",
            "current_candle_start_utc": cur_start.isoformat(),
            "current_candle_close_utc": cur_close_ts.isoformat(),
            "previous_candle_start_utc": prev_start.isoformat(),
            "swept_symbols": sorted(swept_symbols),
            "holding_symbols": holding_symbols,
            "close_confirmed_symbols": sorted(close_confirmed_symbols),
            "close_holding_symbols": close_holding_symbols,
            "closed_back_inside_symbols": sorted(closed_back_inside_symbols),
            "first_break_symbol": primary,
            "primary_sweep_symbol": primary,
            "primary_close_confirmed": bool(primary_close_confirmed),
            "close_confirmed_at_close": bool(close_confirmed_at_close),
            "n_swept_symbols": len(swept_symbols),
            "n_holding_symbols": len(holding_symbols),
            "n_close_confirmed_symbols": len(close_confirmed_symbols),
            "per_symbol_states": per_symbol,
        }
        context = {
            "day_of_week_et": et_close.weekday(),
            "hour_of_day_et": et_close.hour,
            "tracking_timeframe": timeframe,
            "confirmed_at_close": True,
        }
        return ResearchEventCreate(
            feature_name=self.feature_name,
            # ResearchEvent ids do not include `side`; include it in the
            # persisted event_type so high+low SMT on the same candle do not
            # collide while the CLI mode remains timeframe-only.
            event_type=f"{mode}_{side}",
            bar_end_utc=cur_close_ts,
            primary_symbol=primary,
            symbols=list(symbols),
            timeframe=timeframe.upper(),
            side=side,
            event_data=event_data,
            context=context,
            outcomes=None,
            replay_pointer={
                "primary_symbol": primary,
                "ts_utc": cur_close_ts.isoformat(),
                "current_candle_start_utc": cur_start.isoformat(),
                "tracking_timeframe": timeframe,
            },
            detector_version=self.detector_version,
        )


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
        log.info("smt_prev_candle: bar_reader missing for %s %s: %s", symbol, timeframe, exc)
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
    if not frames:
        return pd.DatetimeIndex([], tz=UTC)
    common = frames[0].index
    for frame in frames[1:]:
        common = common.intersection(frame.index)
    return common.sort_values()


def _row_at(df: pd.DataFrame, ts: pd.Timestamp) -> pd.Series:
    row = df.loc[ts]
    if isinstance(row, pd.DataFrame):
        return row.iloc[0]
    return row


register("smt_prev_candle_divergence", SmtPrevCandleDivergenceDetector())
