"""Liquidity sweep reactions outcome computer (v1).

For each sweep event (a bar's wick took a reference high/low), records:

1. **forward_3/10/50_candles** — MFE/MAE measured FROM the manipulation
   candle's close, oriented to the THESIS direction (bullish for swept
   lows, bearish for swept highs).

2. **swept_level_recovery** — did price close back past the swept
   level after the manipulation candle? When? This is the "sweep and
   reverse" pattern.

3. **forward_continuation** — did a forward bar wick BEYOND the
   manipulation extreme (deeper sweep)? When? "Continuation" =
   the sweep failed and price kept going.

4. **ob_confirmation** — joins to `order_block` events on the same
   primary, same direction (bullish thesis → bullish OB), within N
   forward bars. Records:
     - did_confirm: bool
     - bars_to_first_ob: int|None (1-based on the sweep timeframe)
     - first_ob_event_id: str|None
   This is the failure-tracking layer Ben asked for.

Note on the OB join: the sweep detector uses one timeframe per mode
(e.g. `pdl_1h` uses 1h bars), but OBs may be confirmed at multiple
timeframes (`swept_pdl_1h`, `swept_pdl_4h`). This computer queries
ALL OB modes for the matching `(ref, side, primary)` and picks the
EARLIEST OB whose knowable_ts > sweep manipulation ts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import pandas as pd
from sqlalchemy import select

from app.db.models import ResearchEvent
from app.research.outcomes import BarReader, register
from app.research.outcomes.reaction_labels import (
    add_first_bar_reaction,
    add_range_reaction,
    add_reference_price_reaction,
    bar_window_summary,
)

UTC = timezone.utc
log = logging.getLogger(__name__)


_TIMEFRAME_FOR_MODE: dict[str, tuple[str, int]] = {
    "pdl_1h": ("1h", 60),
    "pdl_4h": ("4h", 240),
    "pdh_1h": ("1h", 60),
    "pdh_4h": ("4h", 240),
    "pwl_4h": ("4h", 240),
    "pwl_daily": ("1d", 24 * 60),
    "pwh_4h": ("4h", 240),
    "pwh_daily": ("1d", 24 * 60),
    # Session-scope modes (1h tracking only).
    "asia_low_1h": ("1h", 60),
    "asia_high_1h": ("1h", 60),
    "london_low_1h": ("1h", 60),
    "london_high_1h": ("1h", 60),
    "ny_low_1h": ("1h", 60),
    "ny_high_1h": ("1h", 60),
}

# OB modes that match each sweep mode's (ref, timeframe) — for the join.
# A sweep on `pdl_1h` could be confirmed by OBs at any timeframe whose
# ref matches; we look at all OB modes with matching ref.
_OB_MODES_FOR_REF: dict[str, list[str]] = {
    "pdl": ["swept_pdl_1h", "swept_pdl_4h"],
    "pdh": ["swept_pdh_1h", "swept_pdh_4h"],
    "pwl": ["swept_pwl_4h", "swept_pwl_daily"],
    "pwh": ["swept_pwh_4h", "swept_pwh_daily"],
    "prev_asia_low":    ["swept_asia_low_1h"],
    "prev_asia_high":   ["swept_asia_high_1h"],
    "prev_london_low":  ["swept_london_low_1h"],
    "prev_london_high": ["swept_london_high_1h"],
    "prev_ny_low":      ["swept_ny_low_1h"],
    "prev_ny_high":     ["swept_ny_high_1h"],
}

_FORWARD_WINDOWS: tuple[int, ...] = (3, 10, 50)
_MAX_FORWARD = max(_FORWARD_WINDOWS)


# Lag minutes for each OB mode (for computing knowable_ts).
_OB_LAG: dict[str, int] = {
    "swept_pdl_1h": 60, "swept_pdl_4h": 240,
    "swept_pdh_1h": 60, "swept_pdh_4h": 240,
    "swept_pwl_4h": 240, "swept_pwl_daily": 24 * 60,
    "swept_pwh_4h": 240, "swept_pwh_daily": 24 * 60,
    "swept_asia_low_1h": 60, "swept_asia_high_1h": 60,
    "swept_london_low_1h": 60, "swept_london_high_1h": 60,
    "swept_ny_low_1h": 60, "swept_ny_high_1h": 60,
}


class LiquiditySweepReactionsComputer:
    feature_name: str = "liquidity_sweep"
    outcome_version: str = "v2"

    # OB events pre-loaded into a pandas DataFrame on first call,
    # massively faster than per-event SQL join. Cache survives across
    # compute() calls within one runner instance.
    def __init__(self) -> None:
        self._ob_df: pd.DataFrame | None = None

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        if event.event_type not in _TIMEFRAME_FOR_MODE:
            log.warning(
                "sweep_reactions: unknown event_type %s (id=%s)",
                event.event_type, event.id,
            )
            return None

        ed = event.event_data or {}
        try:
            ref_type = ed["ref_type"]
            ref_side = ed["ref_side"]
            thesis = ed["thesis"]
            ref_price = float(ed["swept_reference"]["level_price"])
            manip_high = float(ed["manipulation_candle"]["high"])
            manip_low = float(ed["manipulation_candle"]["low"])
            manip_close = float(ed["manipulation_candle"]["close"])
        except (KeyError, TypeError, ValueError):
            return None

        direction: Literal["bullish", "bearish"] = (
            "bullish" if thesis == "bullish" else "bearish"
        )

        timeframe_native, minutes_per_candle = _TIMEFRAME_FOR_MODE[event.event_type]
        manip_bucket_start = _ensure_utc(event.bar_end_utc)
        forward_start = manip_bucket_start + timedelta(minutes=minutes_per_candle)
        forward_window_minutes = minutes_per_candle * (_MAX_FORWARD + 25) + 60

        forward = _load_forward_bars(
            bar_reader,
            symbol=event.primary_symbol,
            timeframe=timeframe_native,
            start_utc=forward_start,
            end_utc=forward_start + timedelta(minutes=forward_window_minutes),
        )
        if forward is None or forward.empty:
            return None
        forward = forward.iloc[:_MAX_FORWARD]

        # Forward MFE/MAE in thesis from manipulation close.
        forward_blocks: dict[str, dict[str, Any]] = {}
        for n in _FORWARD_WINDOWS:
            forward_blocks[f"forward_{n}_candles"] = _excursion(
                forward.iloc[:n],
                reference_close=manip_close,
                direction=direction,
            )

        # Recovery of the swept level: did a bar CLOSE back past the
        # ref in the thesis direction?
        recovery = _compute_recovery(
            forward, ref_price=ref_price, direction=direction,
        )

        # Continuation: did a wick go DEEPER than the manipulation extreme?
        continuation = _compute_continuation(
            forward, manip_extreme=manip_low if ref_side == "low" else manip_high,
            ref_side=ref_side,
        )

        # OB confirmation join.
        ob_confirmation = self._compute_ob_confirmation(
            event=event,
            ref_type=ref_type,
            direction=direction,
            forward=forward,
            forward_start_utc=forward_start,
            minutes_per_candle=minutes_per_candle,
        )

        return {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "thesis_direction": "up" if direction == "bullish" else "down",
            "manipulation_close": manip_close,
            "ref_price": ref_price,
            "ref_side": ref_side,
            "swept_level_recovery": recovery,
            "forward_continuation": continuation,
            "ob_confirmation": ob_confirmation,
            "swept_reference_reaction": _swept_reference_reaction(
                forward,
                window_start=forward_start,
                window_end=forward_start + timedelta(minutes=minutes_per_candle * len(forward)),
                reference_price=ref_price,
            ),
            "manipulation_range_reaction": _manipulation_range_reaction(
                forward,
                window_start=forward_start,
                window_end=forward_start + timedelta(minutes=minutes_per_candle * len(forward)),
                manipulation_close=manip_close,
                manipulation_high=manip_high,
                manipulation_low=manip_low,
            ),
            **forward_blocks,
        }

    def _load_ob_df(self, session) -> pd.DataFrame:
        """Lazy-load all order_block events into a pandas DataFrame.
        ~50K rows; one SQL query replaces tens of thousands of per-event
        queries. Computes knowable_ts and indexes for fast filtering."""
        import pandas as _pd
        from sqlalchemy import select as _select
        stmt = _select(
            ResearchEvent.event_id, ResearchEvent.primary_symbol,
            ResearchEvent.event_type, ResearchEvent.side,
            ResearchEvent.bar_end_utc,
        ).where(ResearchEvent.feature_name == "order_block")
        rows = session.execute(stmt).all()
        df = _pd.DataFrame(rows, columns=[
            "event_id", "primary_symbol", "event_type", "side", "bar_end_utc",
        ])
        if df.empty:
            df["knowable_ts"] = []
            df["bar_end_utc_ns"] = []
            df["knowable_ts_ns"] = []
            return df
        df["bar_end_utc"] = _pd.to_datetime(df["bar_end_utc"], utc=True)
        df["lag_min"] = df["event_type"].map(_OB_LAG).fillna(60).astype("int64")
        df["knowable_ts"] = df["bar_end_utc"] + _pd.to_timedelta(
            df["lag_min"], unit="m",
        )
        df["bar_end_utc_ns"] = df["bar_end_utc"].astype("int64")
        df["knowable_ts_ns"] = df["knowable_ts"].astype("int64")
        log.info(
            "sweep_reactions: loaded %d order_block events into cache", len(df),
        )
        return df

    def _compute_ob_confirmation(
        self,
        *,
        event: ResearchEvent,
        ref_type: str,
        direction: Literal["bullish", "bearish"],
        forward: pd.DataFrame,
        forward_start_utc: datetime,
        minutes_per_candle: int,
    ) -> dict[str, Any]:
        """Join to order_block events. Optimized: uses an in-memory
        pandas DataFrame populated on first call.
        """
        from sqlalchemy.orm import object_session

        session = object_session(event)
        if session is None:
            return {"did_confirm": False, "bars_to_first_ob": None,
                    "first_ob_event_id": None}

        if self._ob_df is None:
            self._ob_df = self._load_ob_df(session)

        ob_modes = _OB_MODES_FOR_REF.get(ref_type, [])
        if not ob_modes:
            return {"did_confirm": False, "bars_to_first_ob": None,
                    "first_ob_event_id": None}

        manip_ts = _ensure_utc(event.bar_end_utc)
        manip_ts_ns = int(pd.Timestamp(manip_ts).value)
        horizon_end = forward_start_utc + timedelta(
            minutes=minutes_per_candle * (_MAX_FORWARD + 1) + 60,
        )
        horizon_end_ns = int(pd.Timestamp(horizon_end).value)

        # In-memory filter on the OB DataFrame.
        df = self._ob_df
        mask = (
            (df["primary_symbol"] == event.primary_symbol)
            & (df["event_type"].isin(ob_modes))
            & (df["side"] == direction)
            & (df["bar_end_utc_ns"] > manip_ts_ns)
            & (df["bar_end_utc_ns"] <= horizon_end_ns)
            & (df["knowable_ts_ns"] > manip_ts_ns)  # earliest valid
        )
        sub = df[mask]
        if sub.empty:
            return {"did_confirm": False, "bars_to_first_ob": None,
                    "first_ob_event_id": None}

        # Pick row with earliest knowable_ts.
        best_idx = sub["knowable_ts_ns"].idxmin()
        best_row = sub.loc[best_idx]
        ob_be = best_row["bar_end_utc"].to_pydatetime()
        delta_min = (ob_be - manip_ts).total_seconds() / 60.0
        bars_to = max(1, int(round(delta_min / minutes_per_candle)))

        return {
            "did_confirm": True,
            "bars_to_first_ob": bars_to,
            "first_ob_event_id": best_row["event_id"],
            "first_ob_mode": best_row["event_type"],
            "first_ob_knowable_ts": best_row["knowable_ts"].isoformat(),
        }


# ---------- helpers ----------


def _compute_recovery(
    forward: pd.DataFrame,
    *,
    ref_price: float,
    direction: Literal["bullish", "bearish"],
) -> dict[str, Any]:
    """Did a forward bar CLOSE back past the swept reference in the
    thesis direction? Bullish thesis: close > ref_price.
    Bearish thesis: close < ref_price."""
    bars_to: int | None = None
    for idx, (_, bar) in enumerate(forward.iterrows(), start=1):
        c = float(bar["close"])
        if direction == "bullish" and c > ref_price:
            bars_to = idx
            break
        if direction == "bearish" and c < ref_price:
            bars_to = idx
            break
    return {
        "level_recovered": bars_to is not None,
        "bars_to_recovery": bars_to,
    }


def _swept_reference_reaction(
    forward: pd.DataFrame,
    *,
    window_start: datetime,
    window_end: datetime,
    reference_price: float,
) -> dict[str, Any] | None:
    out = bar_window_summary(forward, window_start=window_start, window_end=window_end)
    if out is None:
        return None
    high = float(out["high"])
    low = float(out["low"])
    close = float(out["close"])
    add_reference_price_reaction(
        out,
        high=high,
        low=low,
        close=close,
        reference_price=reference_price,
    )
    add_first_bar_reaction(
        out,
        first_close=float(forward["close"].astype(float).iloc[0]),
        final_close=close,
        reference_price=reference_price,
    )
    return out


def _manipulation_range_reaction(
    forward: pd.DataFrame,
    *,
    window_start: datetime,
    window_end: datetime,
    manipulation_close: float,
    manipulation_high: float,
    manipulation_low: float,
) -> dict[str, Any] | None:
    out = bar_window_summary(forward, window_start=window_start, window_end=window_end)
    if out is None:
        return None
    high = float(out["high"])
    low = float(out["low"])
    close = float(out["close"])
    add_reference_price_reaction(
        out,
        high=high,
        low=low,
        close=close,
        reference_price=manipulation_close,
    )
    add_first_bar_reaction(
        out,
        first_close=float(forward["close"].astype(float).iloc[0]),
        final_close=close,
        reference_price=manipulation_close,
    )
    add_range_reaction(
        out,
        high=high,
        low=low,
        close=close,
        range_pts=float(out["range_pts"]),
        anchor_high=manipulation_high,
        anchor_low=manipulation_low,
        prefix="manipulation",
    )
    return out


def _compute_continuation(
    forward: pd.DataFrame,
    *,
    manip_extreme: float,
    ref_side: Literal["high", "low"],
) -> dict[str, Any]:
    """Did a forward bar wick DEEPER than the manipulation extreme?
    Low-side: bar.low < manip.low.
    High-side: bar.high > manip.high."""
    bars_to: int | None = None
    deepest_extension_pts: float = 0.0
    for idx, (_, bar) in enumerate(forward.iterrows(), start=1):
        if ref_side == "low":
            depth = max(0.0, manip_extreme - float(bar["low"]))
        else:
            depth = max(0.0, float(bar["high"]) - manip_extreme)
        if depth > 0:
            if bars_to is None:
                bars_to = idx
            if depth > deepest_extension_pts:
                deepest_extension_pts = depth
    return {
        "continued": bars_to is not None,
        "bars_to_first_extension": bars_to,
        "deepest_extension_pts": float(deepest_extension_pts),
    }


def _excursion(
    bars: pd.DataFrame,
    *,
    reference_close: float,
    direction: Literal["bullish", "bearish"],
) -> dict[str, Any]:
    if bars.empty:
        return _empty_excursion()
    win_high = float(bars["high"].max())
    win_low = float(bars["low"].min())
    last_close = float(bars["close"].iloc[-1])
    if direction == "bullish":
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
        "mfe_pts_in_thesis": float(mfe_pts),
        "mae_pts_against_thesis": float(mae_pts),
    }


def _empty_excursion() -> dict[str, Any]:
    return {
        "n_bars": 0,
        "reference_close": None,
        "window_high": None,
        "window_low": None,
        "last_close": None,
        "mfe_pts_in_thesis": None,
        "mae_pts_against_thesis": None,
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
            symbol=symbol, timeframe=timeframe,
            start=start_utc, end=end_utc + timedelta(days=1),  # pad for date-partitioned reader
        )
    except (FileNotFoundError, ValueError) as exc:
        log.info("sweep_reactions: bar_reader missing %s %s: %s",
                 symbol, timeframe, exc)
        return None
    if df is None or len(df) == 0:
        return None
    df = _normalize_index(df)
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

register("liquidity_sweep_reactions_v2", LiquiditySweepReactionsComputer())
