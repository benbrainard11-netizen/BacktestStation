"""PSP reactions outcome computer.

Populates `outcomes` for events written by the
`psp_candle_divergence` detector.

What it captures
----------------

For each PSP event, computes three blocks:

1. **next_candle**: did the diverger CONTINUE its minority direction
   on the very next candle, or REVERSE? "Continued" is what the SMT
   trader's read predicts — the lone diverger that closed bullish
   (against a bearish majority) keeps going bullish.

2. **forward_3_candles** / **forward_5_candles**: MFE/MAE of the
   diverger over the next 3 / 5 candles, oriented toward the
   minority direction (so positive MFE = move continued; negative
   = reversed).

3. **majority_reaction**: did the majority symbols ROLL OVER on the
   next candle (flip to the minority's direction), HOLD their
   direction, or print mixed? The classic SMT-trader hypothesis
   here is that a strong PSP gets the majority to "follow" the
   diverger.

Reference price for excursion math: the diverger's CLOSE on the
PSP candle itself (i.e. what was visible at the moment the PSP
became confirmed).

Idempotent on outcome_version. Re-runs skip already-current rows
unless `--force`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import pandas as pd

from app.db.models import ResearchEvent
from app.research.outcomes import BarReader, register

UTC = timezone.utc
log = logging.getLogger(__name__)


# event_type → 1m/native timeframe + per-candle minute span. The
# computer loads bars at the SAME timeframe the detector ran on, so
# "next candle" means one bucket later at that timeframe.
_TIMEFRAME_FOR_TYPE: dict[str, tuple[str, int]] = {
    "1h_psp": ("1h", 60),
    "4h_psp": ("4h", 240),
    "daily_psp": ("1d", 24 * 60),
}


class PspReactionsComputer:
    feature_name: str = "psp_candle_divergence"
    outcome_version: str = "v1"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        if event.event_type not in _TIMEFRAME_FOR_TYPE:
            log.warning(
                "psp_reactions: unknown event_type %s (id=%s); skipping",
                event.event_type, event.id,
            )
            return None
        if event.side not in ("bullish", "bearish"):
            log.warning(
                "psp_reactions: bad side %r (id=%s)", event.side, event.id,
            )
            return None

        timeframe_native, minutes_per_candle = _TIMEFRAME_FOR_TYPE[event.event_type]
        minority_dir: Literal["bullish", "bearish"] = event.side  # type: ignore[assignment]
        primary = event.primary_symbol

        # event.bar_end_utc is the bucket START (per pandas floor labels).
        psp_bucket_start = _ensure_utc(event.bar_end_utc)
        psp_bucket_end = psp_bucket_start + timedelta(minutes=minutes_per_candle)

        # Pull the next 6 candles after the PSP for the primary
        # symbol (forward_5 + 1 buffer). 6 buckets = 6 *
        # minutes_per_candle. For daily that's 6 days; for 1h, 6 hours.
        # Use a generous lookforward in date units to cover weekend
        # gaps (read_bars filters by date partition, not by timestamp).
        forward_window_minutes = minutes_per_candle * 8 + 60  # tiny pad
        primary_forward = _load_forward_bars(
            bar_reader,
            symbol=primary,
            timeframe=timeframe_native,
            start_utc=psp_bucket_end,
            end_utc=psp_bucket_end + timedelta(minutes=forward_window_minutes),
        )
        if primary_forward is None or primary_forward.empty:
            return None

        # Reference close = diverger's close on the PSP candle itself.
        # That's stored in event_data.per_symbol_states[primary].close,
        # written by the detector. Fall back to loading the bar if the
        # field is missing on legacy rows.
        per_symbol = (event.event_data or {}).get("per_symbol_states") or {}
        ref_close_raw = per_symbol.get(primary, {}).get("close")
        if ref_close_raw is None:
            return None
        reference_close = float(ref_close_raw)

        # Take exactly the next 5 candles (whatever they are; if
        # markets were closed, the slice is shorter).
        forward = primary_forward.iloc[:5]
        if forward.empty:
            return None

        # next_candle block — only the first candle
        nc = forward.iloc[0]
        nc_open = float(nc["open"])
        nc_close = float(nc["close"])
        if nc_close > nc_open:
            nc_dir = "bullish"
        elif nc_close < nc_open:
            nc_dir = "bearish"
        else:
            nc_dir = "doji"
        if nc_dir == minority_dir:
            nc_relative = "continued"
        elif nc_dir == "doji":
            nc_relative = "doji"
        else:
            nc_relative = "reversed"
        nc_return_pts = nc_close - reference_close
        next_candle_block: dict[str, Any] = {
            "ts_utc": nc.name.isoformat() if hasattr(nc.name, "isoformat") else str(nc.name),
            "open": nc_open,
            "close": nc_close,
            "high": float(nc["high"]),
            "low": float(nc["low"]),
            "direction": nc_dir,
            "relative_to_minority": nc_relative,
            "return_pts_from_psp_close": nc_return_pts,
        }

        # forward_N_candles blocks
        forward_3_block = _excursion(
            forward.iloc[:3], reference_close=reference_close, side=minority_dir,
        )
        forward_5_block = _excursion(
            forward, reference_close=reference_close, side=minority_dir,
        )

        # majority_reaction block — same logic but for each majority symbol
        majority_symbols: list[str] = (event.event_data or {}).get(
            "majority_symbols", []
        ) or []
        majority_reaction: dict[str, Any] = {"per_symbol": {}}
        held = 0
        rolled = 0
        for sym in majority_symbols:
            sym_forward = _load_forward_bars(
                bar_reader,
                symbol=sym,
                timeframe=timeframe_native,
                start_utc=psp_bucket_end,
                end_utc=psp_bucket_end + timedelta(minutes=forward_window_minutes),
            )
            if sym_forward is None or sym_forward.empty:
                continue
            first = sym_forward.iloc[0]
            o, c = float(first["open"]), float(first["close"])
            if c > o:
                d = "bullish"
            elif c < o:
                d = "bearish"
            else:
                d = "doji"
            # majority "rolled over" means it flipped to the minority
            # direction on the next candle. "held" = stayed opposite
            # to the minority (i.e. matched its prior majority dir).
            if d == minority_dir:
                state = "rolled"
                rolled += 1
            elif d == "doji":
                state = "doji"
            else:
                state = "held"
                held += 1
            majority_reaction["per_symbol"][sym] = {
                "direction": d,
                "state": state,
            }
        majority_reaction["n_held"] = held
        majority_reaction["n_rolled"] = rolled
        majority_reaction["all_rolled"] = (
            len(majority_symbols) > 0 and rolled == len(majority_symbols)
        )

        return {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "minority_direction": minority_dir,
            "next_candle": next_candle_block,
            "forward_3_candles": forward_3_block,
            "forward_5_candles": forward_5_block,
            "majority_reaction": majority_reaction,
        }


# ---------- helpers ----------


def _excursion(
    bars: pd.DataFrame,
    *,
    reference_close: float,
    side: Literal["bullish", "bearish"],
) -> dict[str, Any]:
    """MFE/MAE oriented to minority direction, measured from
    `reference_close` over the given bar slice."""
    if bars.empty:
        return _empty_excursion()
    win_high = float(bars["high"].max())
    win_low = float(bars["low"].min())
    last_close = float(bars["close"].iloc[-1])
    if side == "bullish":
        mfe_pts = win_high - reference_close
        mae_pts = reference_close - win_low
    else:
        mfe_pts = reference_close - win_low
        mae_pts = win_high - reference_close
    return {
        "n_bars": int(len(bars)),
        "reference_close": reference_close,
        "window_high": win_high,
        "window_low": win_low,
        "last_close": last_close,
        "mfe_pts_in_minority": float(mfe_pts),
        "mae_pts_against_minority": float(mae_pts),
        "last_close_vs_reference_pts": float(last_close - reference_close),
    }


def _empty_excursion() -> dict[str, Any]:
    return {
        "n_bars": 0,
        "reference_close": None,
        "window_high": None,
        "window_low": None,
        "last_close": None,
        "mfe_pts_in_minority": None,
        "mae_pts_against_minority": None,
        "last_close_vs_reference_pts": None,
    }


def _load_forward_bars(
    bar_reader: BarReader,
    *,
    symbol: str,
    timeframe: str,
    start_utc: datetime,
    end_utc: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(
            symbol=symbol,
            timeframe=timeframe,
            start=start_utc,
            end=end_utc,
        )
    except (FileNotFoundError, ValueError) as exc:
        log.info("psp_reactions: bar_reader missing %s %s: %s",
                 symbol, timeframe, exc)
        return None
    if df is None or len(df) == 0:
        return None
    df = _normalize_index(df)
    # Strict cutoff: keep bars whose index >= start_utc (exclusive of
    # the PSP bucket itself; psp_bucket_end is inclusive of the next
    # bucket's start).
    sliced = df.loc[df.index >= start_utc]
    return sliced if not sliced.empty else None


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


def _ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


# ---------- registration ----------

register("psp_reactions_v1", PspReactionsComputer())
