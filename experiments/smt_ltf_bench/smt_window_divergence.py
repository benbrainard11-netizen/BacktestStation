"""ADDITIVE window/N-bar cross-asset SMT detector (fresh name; does NOT touch the live detector).

Companion to the live `smt_prev_candle_divergence` (adjacent-candle). This one references the
**max-high / min-low over the prior N candles** instead of only the immediately-previous candle, so it
catches non-adjacent divergences (the motivating gap). New feature_name `smt_window_divergence`, new
mode names `{tf}_window{N}_smt`. Lives in the bench dir so importing it registers it for a RESEARCH
process only — it is NOT in `app/research/detectors/` and is NOT picked up by the live recompute_smt.

NOTE (see REPORT.md): Phase-1 shows this adds COVERAGE but LOWERS per-setup edge at 15m/30m
(adjacency is a quality filter). Provided for reproducibility / the optional coverage path — NOT
recommended for live adoption on edge grounds.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
log = logging.getLogger(__name__)
Side = Literal["high", "low"]

_TF_MIN = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "90m": 90, "4h": 240, "6h": 360}
# modes: {tf}_window{N}_smt  -> (timeframe, lookback_n)
_MODES: dict[str, tuple[str, int]] = {
    f"{tf}_window{n}_smt": (tf, n)
    for tf in ("5m", "15m", "30m", "1h")
    for n in (3, 6)
}


class SmtWindowDivergenceDetector:
    feature_name: str = "smt_window_divergence"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODES)

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode not in _MODES:
            raise ValueError(f"smt_window_divergence requires --mode {{{ '|'.join(self.supported_modes) }}}")
        if len(ctx.symbols) < 2:
            raise ValueError("SMT requires >= 2 symbols")
        timeframe, n = _MODES[ctx.mode]
        start_dt = datetime(ctx.start.year, ctx.start.month, ctx.start.day, tzinfo=UTC)
        end_dt = datetime(ctx.end.year, ctx.end.month, ctx.end.day, tzinfo=UTC)

        frames: dict[str, pd.DataFrame] = {}
        for s in ctx.symbols:
            df = _safe_load(ctx.bar_reader, symbol=s, timeframe=timeframe, start=start_dt, end=end_dt)
            if df is None or df.empty:
                return []
            frames[s] = _ensure_utc_index(df).sort_index()

        idx = frames[ctx.symbols[0]].index
        for s in ctx.symbols[1:]:
            idx = idx.intersection(frames[s].index)
        idx = idx.sort_values()
        if len(idx) < n + 1:
            return []

        # per-symbol cur high/low + prior-N-bar reference (shift(1) so cur is excluded)
        ref: dict[str, dict[str, Any]] = {}
        for s in ctx.symbols:
            sub = frames[s].reindex(idx)
            h = sub["high"]; l = sub["low"]
            ref[s] = {
                "h": h.to_numpy(float), "l": l.to_numpy(float),
                "rh": h.shift(1).rolling(n, min_periods=n).max().to_numpy(),
                "rl": l.shift(1).rolling(n, min_periods=n).min().to_numpy(),
            }

        events: list[ResearchEventCreate] = []
        for i in range(n, len(idx)):
            for side in ("high", "low"):
                ev = self._one(ctx.mode, timeframe, n, ctx.symbols, ref, idx, i, side)  # type: ignore[arg-type]
                if ev is not None:
                    events.append(ev)
        return events

    def _one(self, mode, timeframe, n, symbols, ref, idx, i, side) -> ResearchEventCreate | None:
        swept, extremes, per_symbol = [], {}, {}
        for s in symbols:
            r = ref[s]
            ch, cl, rh, rl = r["h"][i], r["l"][i], r["rh"][i], r["rl"][i]
            if not all(pd.notna(x) for x in (ch, cl, rh, rl)):
                return None
            if side == "high":
                is_swept = ch > rh; sweep_price, reference_price = ch, rh
            else:
                is_swept = cl < rl; sweep_price, reference_price = cl, rl
            if is_swept:
                swept.append(s); extremes[s] = float(sweep_price)
            per_symbol[s] = {"current_high": float(ch), "current_low": float(cl),
                             "window_ref_high": float(rh), "window_ref_low": float(rl),
                             "swept": bool(is_swept),
                             "sweep_price": float(sweep_price) if is_swept else None}
        if not swept or len(swept) == len(symbols):
            return None

        cur_start = idx[i].to_pydatetime()
        if cur_start.tzinfo is None:
            cur_start = cur_start.replace(tzinfo=UTC)
        cur_close = cur_start + pd.Timedelta(minutes=_TF_MIN[timeframe]).to_pytimedelta()
        primary = sorted(swept)[0]
        event_data = {
            "schema_version": 1, "detector_version": self.detector_version,
            "reference_mode": "window_lookback", "lookback_n": n, "base_event_type": mode,
            "tracking_timeframe": timeframe, "timeframe_minutes": _TF_MIN[timeframe], "side": side,
            "thesis_direction": "down" if side == "high" else "up",
            "current_candle_start_utc": cur_start.isoformat(),
            "current_candle_close_utc": cur_close.isoformat(),
            "swept_symbols": sorted(swept),
            "holding_symbols": sorted(set(symbols) - set(swept)),
            "first_break_symbol": primary, "primary_sweep_symbol": primary,
            "n_swept_symbols": len(swept), "n_holding_symbols": len(symbols) - len(swept),
            "per_symbol_states": per_symbol,
        }
        return ResearchEventCreate(
            feature_name=self.feature_name, event_type=f"{mode}_{side}",
            bar_end_utc=cur_close, primary_symbol=primary, symbols=list(symbols),
            timeframe=timeframe.upper(), side=side, event_data=event_data,
            context={"tracking_timeframe": timeframe, "confirmed_at_close": True},
            outcomes=None,
            replay_pointer={"primary_symbol": primary, "ts_utc": cur_close.isoformat(),
                            "current_candle_start_utc": cur_start.isoformat(),
                            "tracking_timeframe": timeframe},
            detector_version=self.detector_version,
        )


def _safe_load(bar_reader: BarReader, *, symbol, timeframe, start, end):
    try:
        df = bar_reader(symbol=symbol, timeframe=timeframe, start=start, end=end)
    except (FileNotFoundError, ValueError) as exc:
        log.info("smt_window: missing %s %s: %s", symbol, timeframe, exc)
        return None
    return df if df is not None and len(df) else None


def _ensure_utc_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


register("smt_window_divergence", SmtWindowDivergenceDetector())
