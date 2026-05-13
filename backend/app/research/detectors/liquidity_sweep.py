"""Liquidity sweep detector.

Fires on EVERY sweep of a reference level (PDH/PDL/PWH/PWL) on a
chosen tracking timeframe — regardless of whether an order block
confirmation follows. This is the failure-tracking layer Ben asked
about: of all sweeps, what fraction produced an OB? How fast do OBs
form when they do?

Per `feedback_database_first.md`: track failure modes, not just
successes.

Companion to `order_block`. The order_block detector emits ONLY when
confirmation fires; this one emits for ALL sweeps. Joining the two
event sets yields:

  - sweep → confirmation rate (per ref/timeframe)
  - distribution of bars_to_first_ob_confirmation
  - sweeps that never produced an OB (failure events)

Modes are `<ref>_<timeframe>`:
  - ref ∈ {pdl, pdh, pwl, pwh}
  - timeframe ∈ {1h, 4h, daily}

Detection rule:
  1. Compute reference high/low from prior Globex period (day or week).
  2. Walk current period's tracking-timeframe candles in order.
  3. The FIRST candle whose wick takes the reference fires a sweep
     event. (We do NOT fire on subsequent retests of the same level
     within the same period — one sweep event per (period, ref).)

`bar_end_utc` = the manipulation candle's bucket-start.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.research.reference_levels import compute_reference_level
from app.research.sessions import (
    GlobexPeriod,
    globex_day_for,
    globex_week_for,
    previous_globex_day,
    previous_globex_week,
    previous_session,
    session_for,
)
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)


_MODE_CONFIG: dict[str, dict[str, Any]] = {
    # Day-scope: previous Globex day's high/low.
    "pdl_1h": {"ref": "pdl", "tf": "1h", "tf_minutes": 60, "side": "low",
               "scope": "day", "thesis": "bullish"},
    "pdl_4h": {"ref": "pdl", "tf": "4h", "tf_minutes": 240, "side": "low",
               "scope": "day", "thesis": "bullish"},
    "pdh_1h": {"ref": "pdh", "tf": "1h", "tf_minutes": 60, "side": "high",
               "scope": "day", "thesis": "bearish"},
    "pdh_4h": {"ref": "pdh", "tf": "4h", "tf_minutes": 240, "side": "high",
               "scope": "day", "thesis": "bearish"},
    # Week-scope: previous Globex week's high/low.
    "pwl_4h": {"ref": "pwl", "tf": "4h", "tf_minutes": 240, "side": "low",
               "scope": "week", "thesis": "bullish"},
    "pwl_daily": {"ref": "pwl", "tf": "1d", "tf_minutes": 24 * 60, "side": "low",
                  "scope": "week", "thesis": "bullish"},
    "pwh_4h": {"ref": "pwh", "tf": "4h", "tf_minutes": 240, "side": "high",
               "scope": "week", "thesis": "bearish"},
    "pwh_daily": {"ref": "pwh", "tf": "1d", "tf_minutes": 24 * 60, "side": "high",
                  "scope": "week", "thesis": "bearish"},
    # Session-scope: previous session's high/low. Detection runs on
    # the CURRENT session's bars, looking for sweeps of the prior
    # session's extreme. Modes use 1h tracking; session_*_low fires
    # on bullish thesis, session_*_high on bearish.
    "asia_low_1h": {"ref": "prev_asia_low", "tf": "1h", "tf_minutes": 60,
                    "side": "low", "scope": "session_asia", "thesis": "bullish"},
    "asia_high_1h": {"ref": "prev_asia_high", "tf": "1h", "tf_minutes": 60,
                     "side": "high", "scope": "session_asia", "thesis": "bearish"},
    "london_low_1h": {"ref": "prev_london_low", "tf": "1h", "tf_minutes": 60,
                      "side": "low", "scope": "session_london", "thesis": "bullish"},
    "london_high_1h": {"ref": "prev_london_high", "tf": "1h", "tf_minutes": 60,
                       "side": "high", "scope": "session_london", "thesis": "bearish"},
    "ny_low_1h": {"ref": "prev_ny_low", "tf": "1h", "tf_minutes": 60,
                  "side": "low", "scope": "session_ny", "thesis": "bullish"},
    "ny_high_1h": {"ref": "prev_ny_high", "tf": "1h", "tf_minutes": 60,
                   "side": "high", "scope": "session_ny", "thesis": "bearish"},
}


class LiquiditySweepDetector:
    feature_name: str = "liquidity_sweep"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_CONFIG.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                f"liquidity_sweep requires --mode {{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_CONFIG:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("liquidity_sweep requires at least one symbol")
        cfg = _MODE_CONFIG[ctx.mode]
        events: list[ResearchEventCreate] = []
        for symbol in ctx.symbols:
            events.extend(self._scan_symbol(ctx, symbol, cfg))
        return events

    def _scan_symbol(
        self, ctx: DetectorContext, symbol: str, cfg: dict[str, Any],
    ) -> list[ResearchEventCreate]:
        events: list[ResearchEventCreate] = []
        scope = cfg["scope"]
        if scope == "day":
            iterator = _iter_globex_days(ctx.start, ctx.end)
        elif scope == "week":
            iterator = _iter_globex_weeks(ctx.start, ctx.end)
        elif scope.startswith("session_"):
            session_name = scope.split("_", 1)[1]
            iterator = _iter_sessions(ctx.start, ctx.end, session_name)
        else:
            raise ValueError(f"unknown scope {scope!r}")
        for period in iterator:
            ev = self._scan_one_period(ctx, symbol, cfg, period)
            if ev is not None:
                events.append(ev)
        return events

    def _scan_one_period(
        self, ctx: DetectorContext, symbol: str,
        cfg: dict[str, Any], period: GlobexPeriod,
    ) -> ResearchEventCreate | None:
        # Reference from prior period.
        scope = cfg["scope"]
        if scope == "day":
            prior = previous_globex_day(period.start_utc + timedelta(seconds=1))
        elif scope == "week":
            prior = previous_globex_week(period.start_utc + timedelta(seconds=1))
        elif scope.startswith("session_"):
            session_name = scope.split("_", 1)[1]
            prior = previous_session(period.start_utc + timedelta(seconds=1), session_name)
        else:
            raise ValueError(f"unknown scope {scope!r}")
        # read_bars partitions by calendar date; if start.date() ==
        # end.date(), the [start, end) date range is empty. Pad the load
        # to span at least 2 calendar days, then filter inside the
        # period's exact bounds.
        prior_bars = _safe_load(
            ctx.bar_reader,
            symbol=symbol, timeframe="1m",
            start=prior.start_utc, end=prior.end_utc + timedelta(days=1),
        )
        if prior_bars is None or prior_bars.empty:
            return None
        prior_bars = _ensure_utc_index(prior_bars)
        ref_side: Literal["high", "low"] = cfg["side"]
        ref = compute_reference_level(
            prior_bars, side=ref_side,
            start_utc=prior.start_utc, end_utc=prior.end_utc,
        )
        if ref is None:
            return None

        # Detection-timeframe bars over the current period. Load with a
        # buffer past period.end_utc so the warehouse's resample anchors
        # produce clean 4h/daily buckets, AND ensure load spans ≥ 2
        # calendar days so date-partitioned read_bars doesn't return
        # empty for intraday (session-scope) periods.
        min_buffer = max(
            cfg["tf_minutes"] * 5 + 60,
            24 * 60 + 60,  # at least one calendar day past period end
        )
        load_end = period.end_utc + timedelta(minutes=min_buffer)
        bars = _safe_load(
            ctx.bar_reader,
            symbol=symbol, timeframe=cfg["tf"],
            start=period.start_utc, end=load_end,
        )
        if bars is None or bars.empty:
            return None
        bars = _ensure_utc_index(bars)
        in_period = bars.loc[
            (bars.index >= period.start_utc) & (bars.index < period.end_utc)
        ]
        if in_period.empty:
            return None
        if ref_side == "low":
            sweep_mask = in_period["low"] < ref.value
        else:
            sweep_mask = in_period["high"] > ref.value
        if not sweep_mask.any():
            return None

        manip_ts = in_period.index[sweep_mask][0]
        manip_bar = in_period.loc[manip_ts]
        manip_ts_utc = _ts_to_utc(manip_ts)

        et_ts = manip_ts_utc.astimezone(ET)
        event_data: dict[str, Any] = {
            "schema_version": 1,
            "detector_version": self.detector_version,
            "mode": ctx.mode,
            "ref_type": cfg["ref"],
            "ref_side": ref_side,
            "thesis": cfg["thesis"],
            "tracking_timeframe": cfg["tf"],
            "swept_reference": {
                "type": cfg["ref"],
                "side": ref_side,
                "level_price": float(ref.value),
                "level_set_ts_utc": ref.ts_utc.isoformat(),
                "prior_period_label": prior.label,
                "prior_period_start_utc": prior.start_utc.isoformat(),
                "prior_period_end_utc": prior.end_utc.isoformat(),
            },
            "manipulation_candle": _bar_dict(manip_bar, manip_ts_utc),
            "sweep_depth_pts": (
                float(ref.value - manip_bar["low"]) if ref_side == "low"
                else float(manip_bar["high"] - ref.value)
            ),
        }
        context: dict[str, Any] = {
            "tracking_timeframe": cfg["tf"],
            "day_of_week_et": et_ts.weekday(),
            "hour_of_day_et": et_ts.hour,
            "scope_period_label": period.label,
            "scope_period_start_utc": period.start_utc.isoformat(),
            "scope_period_end_utc": period.end_utc.isoformat(),
        }
        return ResearchEventCreate(
            feature_name=self.feature_name,
            event_type=ctx.mode,
            bar_end_utc=manip_ts_utc,
            primary_symbol=symbol,
            symbols=[symbol],
            timeframe=cfg["tf"].upper(),
            side=ref_side,
            event_data=event_data,
            context=context,
            outcomes=None,
            replay_pointer={
                "primary_symbol": symbol,
                "ts_utc": manip_ts_utc.isoformat(),
                "tracking_timeframe": cfg["tf"],
                "ref_level": float(ref.value),
            },
            detector_version=self.detector_version,
        )


# ---------- helpers (shared with order_block; minor duplication acceptable) ----------


def _bar_dict(bar: pd.Series, ts) -> dict[str, Any]:
    return {
        "ts_utc": _ts_to_utc(ts).isoformat(),
        "open": float(bar["open"]),
        "high": float(bar["high"]),
        "low": float(bar["low"]),
        "close": float(bar["close"]),
    }


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
        log.info("liquidity_sweep: bar_reader missing %s %s: %s",
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


def _ts_to_utc(ts) -> datetime:
    if isinstance(ts, pd.Timestamp):
        ts = ts.to_pydatetime()
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _iter_globex_days(start_d, end_d):
    start_dt = datetime(start_d.year, start_d.month, start_d.day, tzinfo=UTC)
    end_dt = datetime(end_d.year, end_d.month, end_d.day, tzinfo=UTC) + timedelta(days=1)
    cur = globex_day_for(start_dt)
    while cur.start_utc < end_dt:
        yield cur
        cur = globex_day_for(cur.end_utc + timedelta(seconds=1))


def _iter_globex_weeks(start_d, end_d):
    start_dt = datetime(start_d.year, start_d.month, start_d.day, tzinfo=UTC)
    end_dt = datetime(end_d.year, end_d.month, end_d.day, tzinfo=UTC) + timedelta(days=1)
    cur = globex_week_for(start_dt)
    while cur.start_utc < end_dt:
        yield cur
        cur = globex_week_for(cur.end_utc + timedelta(seconds=1))


def _iter_sessions(start_d, end_d, session_name: str):
    """Yield (asia | london | ny) session periods that overlap the
    [start_d, end_d] range. Each Globex day has one of each."""
    start_dt = datetime(start_d.year, start_d.month, start_d.day, tzinfo=UTC)
    end_dt = datetime(end_d.year, end_d.month, end_d.day, tzinfo=UTC) + timedelta(days=1)
    cur_day = globex_day_for(start_dt)
    while cur_day.start_utc < end_dt:
        # Get the named session for this Globex day.
        sess = session_for(cur_day.start_utc + timedelta(hours=1), session_name)
        if sess.end_utc > start_dt:
            yield sess
        cur_day = globex_day_for(cur_day.end_utc + timedelta(seconds=1))


# ---------- registration ----------

register("liquidity_sweep", LiquiditySweepDetector())
