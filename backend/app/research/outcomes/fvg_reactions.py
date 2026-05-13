"""FVG reactions outcome computer (v2).

Populates `outcomes` for events written by the `fvg_formation`
detector.

What v2 captures
----------------

For each FVG event, computes:

1. **mitigation** — wick AND close penetration:
   - `tapped` — any bar's wick entered the gap.
   - `mid_filled` / `fully_filled` — wick at midpoint / full fill.
   - `bars_to_tap` / `bars_to_mid` / `bars_to_full` — when (1-based).
   - `deepest_wick_frac` (0.0–1.0) — deepest wick penetration as
     fraction of fvg_width. (v1 was named `deepest_fill_frac`.)
   - `wick_quartiles_hit` — list of 25/50/75/100 thresholds the wick
     crossed (e.g. [25, 50] means wick reached 50% but not 75%).
   - `closed_inside` — any bar's close fell inside the gap zone.
   - `closed_through` — any bar's close went beyond the far edge
     (bullish: bar.close < fvg_low; bearish: bar.close > fvg_high).
   - `bars_to_close_inside` / `bars_to_close_through` — when.
   - `deepest_close_frac` — deepest CLOSE-based penetration. >1.0 if
     a close went past the far edge (capped at 1.0 in `wick_*` since
     wick can't extend the gap; close-frac caps at 1.0 too — beyond
     that we just record `closed_through`).
   - `tap_bar_classification` — for the FIRST bar that tapped:
     `wick_reject` | `close_inside` | `close_through` (None if untapped).

2. **forward_3 / forward_10 / forward_50 candles** — MFE/MAE measured
   from the c3 close (the bar that confirmed the FVG), oriented to
   FVG thesis (bullish → up, bearish → down). Same as v1.

3. **post_tap_reaction** — NEW in v2. MFE/MAE measured from the FIRST
   tap bar's close, oriented to FVG thesis. Captures "what did price
   do after the entry signal?" for traders who wait for tap before
   acting. Null if FVG never tapped within horizon. Sub-blocks:
   `forward_3_after_tap`, `forward_10_after_tap`, `forward_50_after_tap`
   (capped at remaining bars).

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


_TIMEFRAME_FOR_TYPE: dict[str, tuple[str, int]] = {
    "1h_fvg": ("1h", 60),
    "4h_fvg": ("4h", 240),
    "daily_fvg": ("1d", 24 * 60),
    "15m_fvg": ("15m", 15),
}

_FORWARD_WINDOWS: tuple[int, ...] = (3, 10, 50)
_MAX_FORWARD = max(_FORWARD_WINDOWS)
_QUARTILE_THRESHOLDS: tuple[int, ...] = (25, 50, 75, 100)


class FvgReactionsComputer:
    feature_name: str = "fvg_formation"
    outcome_version: str = "v2"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        if event.event_type not in _TIMEFRAME_FOR_TYPE:
            log.warning(
                "fvg_reactions: unknown event_type %s (id=%s); skipping",
                event.event_type, event.id,
            )
            return None
        if event.side not in ("bullish", "bearish"):
            log.warning(
                "fvg_reactions: bad side %r (id=%s)", event.side, event.id,
            )
            return None

        ed = event.event_data or {}
        try:
            fvg_high = float(ed["fvg_high"])
            fvg_low = float(ed["fvg_low"])
            fvg_mid = float(ed.get("fvg_mid", (fvg_high + fvg_low) / 2.0))
            ref_close = float(ed["candle_3"]["close"])
        except (KeyError, TypeError, ValueError):
            return None
        fvg_width = fvg_high - fvg_low
        direction: Literal["bullish", "bearish"] = event.side  # type: ignore[assignment]

        timeframe_native, minutes_per_candle = _TIMEFRAME_FOR_TYPE[event.event_type]

        c3_bucket_start = _ensure_utc(event.bar_end_utc)
        forward_start = c3_bucket_start + timedelta(minutes=minutes_per_candle)

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

        mitigation_block = _compute_mitigation(
            forward,
            direction=direction,
            fvg_high=fvg_high,
            fvg_low=fvg_low,
            fvg_mid=fvg_mid,
            fvg_width=fvg_width,
        )

        out: dict[str, Any] = {
            "schema_version": 2,
            "outcome_version": self.outcome_version,
            "thesis_direction": "up" if direction == "bullish" else "down",
            "reference_close": ref_close,
            "fvg_high": fvg_high,
            "fvg_low": fvg_low,
            "fvg_mid": fvg_mid,
            "fvg_width_pts": fvg_width,
            "mitigation": mitigation_block,
        }
        for n in _FORWARD_WINDOWS:
            out[f"forward_{n}_candles"] = _excursion(
                forward.iloc[:n],
                reference_close=ref_close,
                direction=direction,
            )

        # post_tap_reaction — only computed when tap occurred
        tap_idx = mitigation_block["bars_to_tap"]
        if tap_idx is not None:
            tap_bar = forward.iloc[tap_idx - 1]  # bars_to_tap is 1-based
            tap_close = float(tap_bar["close"])
            out["post_tap_reaction"] = {
                "tap_bar_index": int(tap_idx),
                "tap_bar_close": tap_close,
                "tap_bar_classification": mitigation_block["tap_bar_classification"],
            }
            # Forward windows measured FROM the tap bar onward (exclusive of tap bar itself —
            # if you "entered" on the tap bar's close, what happened on bars after?)
            after_tap = forward.iloc[tap_idx:]
            for n in _FORWARD_WINDOWS:
                out["post_tap_reaction"][f"forward_{n}_after_tap"] = _excursion(
                    after_tap.iloc[:n],
                    reference_close=tap_close,
                    direction=direction,
                )
        else:
            out["post_tap_reaction"] = None

        return out


# ---------- helpers ----------


def _compute_mitigation(
    forward: pd.DataFrame,
    *,
    direction: Literal["bullish", "bearish"],
    fvg_high: float,
    fvg_low: float,
    fvg_mid: float,
    fvg_width: float,
) -> dict[str, Any]:
    """Walk forward bars in order. Track wick AND close penetration."""
    bars_to_tap: int | None = None
    bars_to_mid: int | None = None
    bars_to_full: int | None = None
    bars_to_close_inside: int | None = None
    bars_to_close_through: int | None = None
    deepest_wick_frac: float = 0.0
    deepest_close_frac: float = 0.0
    tap_bar_classification: str | None = None

    for idx, (_, bar) in enumerate(forward.iterrows(), start=1):
        bar_high = float(bar["high"])
        bar_low = float(bar["low"])
        bar_close = float(bar["close"])

        if direction == "bullish":
            # Wick penetrates by going DOWN from above.
            wick_in_zone = bar_low <= fvg_high
            wick_depth_pts = max(0.0, fvg_high - bar_low)
            close_in_zone = (bar_close <= fvg_high) and (bar_close >= fvg_low)
            close_through = bar_close < fvg_low
            close_depth_pts = max(0.0, fvg_high - bar_close)
        else:
            # Bearish: wick penetrates by going UP from below.
            wick_in_zone = bar_high >= fvg_low
            wick_depth_pts = max(0.0, bar_high - fvg_low)
            close_in_zone = (bar_close >= fvg_low) and (bar_close <= fvg_high)
            close_through = bar_close > fvg_high
            close_depth_pts = max(0.0, bar_close - fvg_low)

        if not wick_in_zone:
            continue

        # First-tap bar: classify it.
        if bars_to_tap is None:
            bars_to_tap = idx
            if close_through:
                tap_bar_classification = "close_through"
            elif close_in_zone:
                tap_bar_classification = "close_inside"
            else:
                tap_bar_classification = "wick_reject"

        if bars_to_mid is None:
            if direction == "bullish" and bar_low <= fvg_mid:
                bars_to_mid = idx
            elif direction == "bearish" and bar_high >= fvg_mid:
                bars_to_mid = idx
        if bars_to_full is None:
            if direction == "bullish" and bar_low <= fvg_low:
                bars_to_full = idx
            elif direction == "bearish" and bar_high >= fvg_high:
                bars_to_full = idx
        if bars_to_close_inside is None and close_in_zone:
            bars_to_close_inside = idx
        if bars_to_close_through is None and close_through:
            bars_to_close_through = idx

        if fvg_width > 0:
            wick_frac = min(1.0, wick_depth_pts / fvg_width)
            close_frac = min(1.0, close_depth_pts / fvg_width)
            if wick_frac > deepest_wick_frac:
                deepest_wick_frac = wick_frac
            if close_frac > deepest_close_frac:
                deepest_close_frac = close_frac

        # Continue scanning for the deepest close-through after first tap.
        # (Don't break on bars_to_full — we still want to know if a later
        # bar closed through.)

    wick_quartiles_hit = [
        q for q in _QUARTILE_THRESHOLDS if deepest_wick_frac >= q / 100.0
    ]
    close_quartiles_hit = [
        q for q in (25, 50, 75) if deepest_close_frac >= q / 100.0
    ]

    return {
        "tapped": bars_to_tap is not None,
        "mid_filled": bars_to_mid is not None,
        "fully_filled": bars_to_full is not None,
        "closed_inside": bars_to_close_inside is not None,
        "closed_through": bars_to_close_through is not None,
        "bars_to_tap": bars_to_tap,
        "bars_to_mid": bars_to_mid,
        "bars_to_full": bars_to_full,
        "bars_to_close_inside": bars_to_close_inside,
        "bars_to_close_through": bars_to_close_through,
        "deepest_wick_frac": float(deepest_wick_frac),
        "deepest_close_frac": float(deepest_close_frac),
        "wick_quartiles_hit": wick_quartiles_hit,
        "close_quartiles_hit": close_quartiles_hit,
        "tap_bar_classification": tap_bar_classification,
        "horizon_bars": int(len(forward)),
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
        "last_close_vs_reference_pts": float(last_close - reference_close),
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
            end=end_utc + timedelta(days=1),  # pad for date-partitioned reader
        )
    except (FileNotFoundError, ValueError) as exc:
        log.info("fvg_reactions: bar_reader missing %s %s: %s",
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

register("fvg_reactions_v1", FvgReactionsComputer())
