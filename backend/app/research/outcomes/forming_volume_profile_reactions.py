"""Forward reactions for forming volume profile snapshots.

The input levels are as-of VP/VWAP levels. Labels look forward from the
snapshot cutoff, never from the completed parent profile.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from app.db.models import ResearchEvent
from app.research.outcomes import BarReader, register
from app.research.outcomes.volume_profile_reactions import level_reaction

UTC = timezone.utc
log = logging.getLogger(__name__)

WINDOWS_MIN: dict[str, int | None] = {
    "next_60m": 60,
    "next_240m": 240,
    "rest_of_day": None,
}


class FormingVolumeProfileReactionsComputer:
    feature_name: str = "forming_volume_profile"
    outcome_version: str = "v1"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        ed = event.event_data or {}
        try:
            asof_ts = _to_utc(datetime.fromisoformat(ed["asof_ts_utc"]))
            parent_end = _to_utc(datetime.fromisoformat(ed["parent_period_end_utc"]))
            reference_close = float(ed["asof_close"])
            profile_high = float(ed["profile_high_so_far"])
            profile_low = float(ed["profile_low_so_far"])
            poc = float(ed["poc_price"])
            vah = float(ed["vah_price"])
            val = float(ed["val_price"])
            vwap = float(ed["vwap"])
            sd = float(ed["vwap_sd"])
        except (KeyError, TypeError, ValueError):
            return None

        if asof_ts >= parent_end:
            return None

        bars = _load_bars(
            bar_reader,
            symbol=event.primary_symbol,
            timeframe="1m",
            start=asof_ts,
            end=parent_end + timedelta(days=1),
        )
        if bars is None or bars.empty:
            return None
        bars = _ensure_utc_index(bars).sort_index()
        bars = bars[(bars.index >= asof_ts) & (bars.index < parent_end)]
        if bars.empty:
            return None

        levels = {
            "poc_touch": poc,
            "vah_touch": vah,
            "val_touch": val,
            "vwap_touch": vwap,
        }
        if sd > 0:
            levels.update(
                {
                    "vwap_1sd_high_touch": vwap + sd,
                    "vwap_1sd_low_touch": vwap - sd,
                    "vwap_2sd_high_touch": vwap + 2 * sd,
                    "vwap_2sd_low_touch": vwap - 2 * sd,
                }
            )

        outcomes: dict[str, Any] = {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "reference_close": reference_close,
            "forward_window_start_utc": asof_ts.isoformat(),
            "forward_window_end_utc": parent_end.isoformat(),
        }
        for name, minutes in WINDOWS_MIN.items():
            window_end = parent_end if minutes is None else min(parent_end, asof_ts + timedelta(minutes=minutes))
            window = bars[(bars.index >= asof_ts) & (bars.index < window_end)]
            outcomes[name] = _window_outcome(
                window,
                window_start=asof_ts,
                window_end=window_end,
                reference_close=reference_close,
                profile_high=profile_high,
                profile_low=profile_low,
                levels=levels,
            )
        return outcomes


def _window_outcome(
    bars: pd.DataFrame,
    *,
    window_start: datetime,
    window_end: datetime,
    reference_close: float,
    profile_high: float,
    profile_low: float,
    levels: dict[str, float],
) -> dict[str, Any] | None:
    if bars.empty:
        return None

    fwd_high = float(bars["high"].max())
    fwd_low = float(bars["low"].min())
    fwd_close = float(bars["close"].iloc[-1])
    out: dict[str, Any] = {
        "window_start_utc": window_start.isoformat(),
        "window_end_utc": window_end.isoformat(),
        "n_bars": int(len(bars)),
        "forward_high": fwd_high,
        "forward_low": fwd_low,
        "forward_close": fwd_close,
        "return_pts": float(fwd_close - reference_close),
        "mfe_up_pts": float(fwd_high - reference_close),
        "mfe_down_pts": float(reference_close - fwd_low),
        "took_profile_high_so_far": fwd_high > profile_high,
        "took_profile_low_so_far": fwd_low < profile_low,
    }
    for key, level in levels.items():
        out[key] = level_reaction(bars, level, reference_close=reference_close)
    return out


def _load_bars(
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
        log.info("forming_volume_profile_react: bar_reader missing %s %s: %s", symbol, timeframe, exc)
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


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


register("forming_volume_profile_reactions_v1", FormingVolumeProfileReactionsComputer())
