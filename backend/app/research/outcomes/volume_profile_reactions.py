"""Volume profile + VWAP reactions outcome computer (v2).

For each volume_profile event, captures whether the NEXT period (or
forward 1m window for sessions) interacted with the POC, VAH, VAL,
VWAP, and σ-band levels.

For daily/weekly periods: N+1 = next Globex day / week.
For session periods (asia/london/ny): forward window = rest of the
Globex day after the session ended (up to next-period start), since
sessions don't have a natural "N+1" within the same conceptual unit.
For session profiles, we use a 24h forward window in 1m bars instead.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from app.db.models import ResearchEvent
from app.research.outcomes import BarReader, register
from app.research.sessions import (
    GlobexPeriod,
    globex_day_for,
    globex_week_for,
)

UTC = timezone.utc
log = logging.getLogger(__name__)
HOLD_BARS = 3


_PARENT_FOR_MODE: dict[str, str] = {
    "daily_volume_profile":  "globex_day",
    "weekly_volume_profile": "globex_week",
    "asia_volume_profile":   "forward_24h",
    "london_volume_profile": "forward_24h",
    "ny_volume_profile":     "forward_24h",
}


class VolumeProfileReactionsComputer:
    feature_name: str = "volume_profile"
    outcome_version: str = "v2"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        if event.event_type not in _PARENT_FOR_MODE:
            log.warning(
                "volume_profile_reactions: unknown mode %s (id=%s)",
                event.event_type, event.id,
            )
            return None

        ed = event.event_data or {}
        try:
            poc = float(ed["poc_price"])
            vah = float(ed["vah_price"])
            val = float(ed["val_price"])
            vwap = float(ed["vwap"])
            sd = float(ed["vwap_sd"])
            period_close = float(ed["period_close"])
            period_high = float(ed["period_high"])
            period_low = float(ed["period_low"])
            parent_end = datetime.fromisoformat(ed["parent_period_end_utc"])
        except (KeyError, TypeError, ValueError):
            return None

        parent_type = _PARENT_FOR_MODE[event.event_type]
        # Determine forward window.
        if parent_type == "globex_day":
            forward_period = globex_day_for(parent_end + timedelta(seconds=1))
            forward_start = forward_period.start_utc
            forward_end = forward_period.end_utc
        elif parent_type == "globex_week":
            forward_period = globex_week_for(parent_end + timedelta(seconds=1))
            forward_start = forward_period.start_utc
            forward_end = forward_period.end_utc
        else:  # forward_24h for sessions
            forward_start = parent_end
            forward_end = parent_end + timedelta(hours=24)

        bars = _load_bars(
            bar_reader,
            symbol=event.primary_symbol, timeframe="1m",
            start=forward_start, end=forward_end + timedelta(days=1),
        )
        if bars is None or bars.empty:
            return None
        bars = _ensure_utc_index(bars)
        bars = bars[(bars.index >= forward_start) & (bars.index < forward_end)]
        if bars.empty:
            return None

        fwd_high = float(bars["high"].max())
        fwd_low = float(bars["low"].min())
        fwd_close = float(bars["close"].iloc[-1])

        return {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "reference_close": period_close,
            "forward_window_start_utc": forward_start.isoformat(),
            "forward_window_end_utc": forward_end.isoformat(),
            "forward_high": fwd_high,
            "forward_low": fwd_low,
            "forward_close": fwd_close,
            "forward_n_bars": int(len(bars)),
            # Level interactions
            "poc_touch": level_reaction(bars, poc, reference_close=period_close),
            "vah_touch": level_reaction(bars, vah, reference_close=period_close),
            "val_touch": level_reaction(bars, val, reference_close=period_close),
            "vwap_touch": level_reaction(bars, vwap, reference_close=period_close),
            "vwap_1sd_high_touch": (
                level_reaction(bars, vwap + sd, reference_close=period_close)
                if sd > 0 else None
            ),
            "vwap_1sd_low_touch": (
                level_reaction(bars, vwap - sd, reference_close=period_close)
                if sd > 0 else None
            ),
            "vwap_2sd_high_touch": (
                level_reaction(bars, vwap + 2 * sd, reference_close=period_close)
                if sd > 0 else None
            ),
            "vwap_2sd_low_touch": (
                level_reaction(bars, vwap - 2 * sd, reference_close=period_close)
                if sd > 0 else None
            ),
            # Did forward take period extremes?
            "took_period_high": fwd_high > period_high,
            "took_period_low": fwd_low < period_low,
            # Forward close relative to period levels
            "forward_close_vs_poc_pts": float(fwd_close - poc),
            "forward_close_vs_vwap_pts": float(fwd_close - vwap),
            "forward_close_above_vah": fwd_close > vah,
            "forward_close_below_val": fwd_close < val,
            "forward_close_in_value_area": val <= fwd_close <= vah,
        }


# ---------- helpers ----------


def level_reaction(
    bars: pd.DataFrame,
    level: float,
    *,
    reference_close: float,
    hold_bars: int = HOLD_BARS,
) -> dict[str, Any]:
    """Forward reaction labels for one VP/VWAP level.

    The old labels only asked whether the forward window ever crossed a level.
    These stricter labels ask whether price accepted above/below the level or
    rejected it after first touch.
    """
    highs = bars["high"].astype(float)
    lows = bars["low"].astype(float)
    closes = bars["close"].astype(float)

    wicked_up = bool((highs > level).any())
    wicked_down = bool((lows < level).any())
    closed_above = bool((closes > level).any())
    closed_below = bool((closes < level).any())

    touch_mask = (highs >= level) & (lows <= level)
    first_touch_bars: int | None = None
    first_touch_from_above = False
    first_touch_from_below = False
    held_above_after_touch = False
    held_below_after_touch = False

    if bool(touch_mask.any()):
        first_pos = int(touch_mask.to_numpy().nonzero()[0][0])
        first_touch_bars = first_pos + 1
        prior_close = reference_close if first_pos == 0 else float(closes.iloc[first_pos - 1])
        first_touch_from_above = bool(prior_close > level)
        first_touch_from_below = bool(prior_close < level)

        touch_window = closes.iloc[first_pos:first_pos + hold_bars]
        if len(touch_window) >= hold_bars:
            held_above_after_touch = bool((touch_window > level).all())
            held_below_after_touch = bool((touch_window < level).all())

    accepted_above = _has_consecutive_closes(closes, level, side="above", n=hold_bars)
    accepted_below = _has_consecutive_closes(closes, level, side="below", n=hold_bars)

    return {
        # Legacy broad touch/cross labels.
        "wicked_into": bool(wicked_up and wicked_down),
        "wicked_above": wicked_up,
        "wicked_below": wicked_down,
        "closed_above": closed_above,
        "closed_below": closed_below,
        # Stricter reaction labels.
        "first_touch_bars": first_touch_bars,
        "first_touch_from_above": first_touch_from_above,
        "first_touch_from_below": first_touch_from_below,
        "held_above_3bar_after_touch": held_above_after_touch,
        "held_below_3bar_after_touch": held_below_after_touch,
        "accepted_above_3bar": accepted_above,
        "accepted_below_3bar": accepted_below,
        "support_rejection_3bar": bool(first_touch_from_above and held_above_after_touch),
        "resistance_rejection_3bar": bool(first_touch_from_below and held_below_after_touch),
        "support_break_acceptance_3bar": bool(first_touch_from_above and held_below_after_touch),
        "resistance_break_acceptance_3bar": bool(first_touch_from_below and held_above_after_touch),
    }


def _has_consecutive_closes(
    closes: pd.Series,
    level: float,
    *,
    side: str,
    n: int,
) -> bool:
    if len(closes) < n:
        return False
    mask = closes > level if side == "above" else closes < level
    return bool(mask.astype(int).rolling(n).sum().ge(n).any())


def _load_bars(
    bar_reader: BarReader,
    *, symbol: str, timeframe: str, start: datetime, end: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(symbol=symbol, timeframe=timeframe,
                        start=start, end=end + timedelta(days=1))
    except (FileNotFoundError, ValueError) as exc:
        log.info("volume_profile_react: bar_reader missing %s %s: %s",
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


# ---------- registration ----------

register("volume_profile_reactions_v2", VolumeProfileReactionsComputer())
