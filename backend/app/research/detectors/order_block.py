"""Order Block detector v1.

Detects the simple ICT/SMT order block setup:

  1. A reference high or low (PDH/PDL/PWH/PWL) gets SWEPT — a bar's
     wick takes the level on the chosen tracking timeframe.
  2. Walk back from the manipulation candle (max 10 bars) to find the
     OB candle:
       - bullish OB (swept-low setup): most recent DOWN-close candle
         (close < open) at or before the sweep candle.
       - bearish OB (swept-high setup): most recent UP-close candle.
  3. Walk forward from the manipulation candle (cap 50 bars) until a
     candle CLOSES past the OB body bottom (laxest rule):
       - bullish: bar.close > ob.close
       - bearish: bar.close < ob.close
     This is the LAXEST of three confirmation rules. Stricter rules
     (close > ob.open, close > ob.high) are recorded as flags so
     analysis can filter without re-scanning.
  4. Emit one event per (mode, symbol, period). bar_end_utc = the
     confirmation candle's bucket-start.

Modes are `swept_<ref>_<timeframe>`, where:
  - ref ∈ {pdl, pdh, pwl, pwh}
  - timeframe ∈ {1h, 4h, daily}

Sessions and prior-swing references are deferred to v2.

Wide-reach data: event_data stores full OHLC of manipulation/OB/
confirmation candles plus all three confirmation flags. Analysis
picks the cuts; the detector doesn't pre-bake a single rule.

Reference-level computation uses prior Globex period (day or week)
1m bars to find the high/low, mirroring the SMT detector.

Cross-link: docs/RESEARCH_DETECTORS.md.
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


# Per-mode configuration. Period scope is what bounds the manipulation
# search; confirmation can extend beyond the period (capped by
# MAX_CONFIRMATION_BARS).
_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "swept_pdl_1h": {
        "ref": "pdl", "tf": "1h", "tf_minutes": 60, "side": "bullish",
        "scope": "day",
    },
    "swept_pdl_4h": {
        "ref": "pdl", "tf": "4h", "tf_minutes": 240, "side": "bullish",
        "scope": "day",
    },
    "swept_pdh_1h": {
        "ref": "pdh", "tf": "1h", "tf_minutes": 60, "side": "bearish",
        "scope": "day",
    },
    "swept_pdh_4h": {
        "ref": "pdh", "tf": "4h", "tf_minutes": 240, "side": "bearish",
        "scope": "day",
    },
    "swept_pwl_4h": {
        "ref": "pwl", "tf": "4h", "tf_minutes": 240, "side": "bullish",
        "scope": "week",
    },
    "swept_pwl_daily": {
        "ref": "pwl", "tf": "1d", "tf_minutes": 24 * 60, "side": "bullish",
        "scope": "week",
    },
    "swept_pwh_4h": {
        "ref": "pwh", "tf": "4h", "tf_minutes": 240, "side": "bearish",
        "scope": "week",
    },
    "swept_pwh_daily": {
        "ref": "pwh", "tf": "1d", "tf_minutes": 24 * 60, "side": "bearish",
        "scope": "week",
    },
    # Session-scope: previous session's high/low. 1h tracking only —
    # session windows are too short for 4h/daily OBs to be meaningful.
    "swept_asia_low_1h": {
        "ref": "prev_asia_low", "tf": "1h", "tf_minutes": 60,
        "side": "bullish", "scope": "session_asia",
    },
    "swept_asia_high_1h": {
        "ref": "prev_asia_high", "tf": "1h", "tf_minutes": 60,
        "side": "bearish", "scope": "session_asia",
    },
    "swept_london_low_1h": {
        "ref": "prev_london_low", "tf": "1h", "tf_minutes": 60,
        "side": "bullish", "scope": "session_london",
    },
    "swept_london_high_1h": {
        "ref": "prev_london_high", "tf": "1h", "tf_minutes": 60,
        "side": "bearish", "scope": "session_london",
    },
    "swept_ny_low_1h": {
        "ref": "prev_ny_low", "tf": "1h", "tf_minutes": 60,
        "side": "bullish", "scope": "session_ny",
    },
    "swept_ny_high_1h": {
        "ref": "prev_ny_high", "tf": "1h", "tf_minutes": 60,
        "side": "bearish", "scope": "session_ny",
    },
    # Session-scope at finer tracking timeframes (15m + 30m).
    # Adds 12 new mode variants for intraday-tighter session sweeps + OB
    # confirmation. Reference level is still "previous SAME session"
    # (yesterday's asia/london/ny). The fine-grained tracking lets OB
    # candles + confirmation candles fit inside a single session window
    # (8h asia, 7.5h london, 7.5h ny). See docs/RESEARCH_EVENTS_DICTIONARY.md.
    "swept_asia_low_15m": {
        "ref": "prev_asia_low", "tf": "15m", "tf_minutes": 15,
        "side": "bullish", "scope": "session_asia",
    },
    "swept_asia_high_15m": {
        "ref": "prev_asia_high", "tf": "15m", "tf_minutes": 15,
        "side": "bearish", "scope": "session_asia",
    },
    "swept_asia_low_30m": {
        "ref": "prev_asia_low", "tf": "30m", "tf_minutes": 30,
        "side": "bullish", "scope": "session_asia",
    },
    "swept_asia_high_30m": {
        "ref": "prev_asia_high", "tf": "30m", "tf_minutes": 30,
        "side": "bearish", "scope": "session_asia",
    },
    "swept_london_low_15m": {
        "ref": "prev_london_low", "tf": "15m", "tf_minutes": 15,
        "side": "bullish", "scope": "session_london",
    },
    "swept_london_high_15m": {
        "ref": "prev_london_high", "tf": "15m", "tf_minutes": 15,
        "side": "bearish", "scope": "session_london",
    },
    "swept_london_low_30m": {
        "ref": "prev_london_low", "tf": "30m", "tf_minutes": 30,
        "side": "bullish", "scope": "session_london",
    },
    "swept_london_high_30m": {
        "ref": "prev_london_high", "tf": "30m", "tf_minutes": 30,
        "side": "bearish", "scope": "session_london",
    },
    "swept_ny_low_15m": {
        "ref": "prev_ny_low", "tf": "15m", "tf_minutes": 15,
        "side": "bullish", "scope": "session_ny",
    },
    "swept_ny_high_15m": {
        "ref": "prev_ny_high", "tf": "15m", "tf_minutes": 15,
        "side": "bearish", "scope": "session_ny",
    },
    "swept_ny_low_30m": {
        "ref": "prev_ny_low", "tf": "30m", "tf_minutes": 30,
        "side": "bullish", "scope": "session_ny",
    },
    "swept_ny_high_30m": {
        "ref": "prev_ny_high", "tf": "30m", "tf_minutes": 30,
        "side": "bearish", "scope": "session_ny",
    },
}

MAX_LOOKBACK_BARS: int = 10
MAX_CONFIRMATION_BARS: int = 50


class OrderBlockDetector:
    feature_name: str = "order_block"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_CONFIG.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                f"order_block requires --mode {{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_CONFIG:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("order_block requires at least one symbol")

        cfg = _MODE_CONFIG[ctx.mode]
        events: list[ResearchEventCreate] = []
        for symbol in ctx.symbols:
            events.extend(self._scan_symbol(ctx, symbol, cfg))
        return events

    def _scan_symbol(
        self,
        ctx: DetectorContext,
        symbol: str,
        cfg: dict[str, Any],
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
        self,
        ctx: DetectorContext,
        symbol: str,
        cfg: dict[str, Any],
        period: GlobexPeriod,
    ) -> ResearchEventCreate | None:
        # Compute the reference level from the PRIOR period.
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
        # read_bars partitions by calendar date; pad load to span ≥2
        # calendar days for intraday session windows. compute_reference_level
        # filters to exact period bounds internally.
        prior_bars = _safe_load(
            ctx.bar_reader,
            symbol=symbol, timeframe="1m",
            start=prior.start_utc, end=prior.end_utc + timedelta(days=1),
        )
        if prior_bars is None or prior_bars.empty:
            return None
        prior_bars = _ensure_utc_index(prior_bars)
        # Bullish OB setup → swept LOW; bearish setup → swept HIGH.
        ref_side: Literal["high", "low"] = (
            "low" if cfg["side"] == "bullish" else "high"
        )
        ref = compute_reference_level(
            prior_bars, side=ref_side,
            start_utc=prior.start_utc, end_utc=prior.end_utc,
        )
        if ref is None:
            return None

        # Load detection-timeframe bars for current period + a buffer so
        # the OB and confirmation candles can extend past period close.
        # Buffer = MAX_CONFIRMATION_BARS * tf_minutes plus padding.
        tf_minutes = cfg["tf_minutes"]
        buffer_minutes = (MAX_CONFIRMATION_BARS + 5) * tf_minutes + 60
        load_end = period.end_utc + timedelta(minutes=buffer_minutes)
        bars = _safe_load(
            ctx.bar_reader,
            symbol=symbol, timeframe=cfg["tf"],
            start=period.start_utc, end=load_end,
        )
        if bars is None or bars.empty:
            return None
        bars = _ensure_utc_index(bars)

        # Find manipulation candle: first candle in the CURRENT period
        # whose wick takes the reference level.
        in_period = bars.loc[
            (bars.index >= period.start_utc) & (bars.index < period.end_utc)
        ]
        if in_period.empty:
            return None
        if ref_side == "low":
            # Bullish setup: candle low pierces below the reference low.
            sweep_mask = in_period["low"] < ref.value
        else:
            sweep_mask = in_period["high"] > ref.value
        if not sweep_mask.any():
            return None
        manipulation_ts = in_period.index[sweep_mask][0]
        # Integer position in the FULL bars frame for back-walk + forward-walk.
        manip_iloc = bars.index.get_loc(manipulation_ts)
        if not isinstance(manip_iloc, int):
            return None
        manipulation_bar = bars.iloc[manip_iloc]

        # Walk back ≤ MAX_LOOKBACK_BARS to find the OB candle.
        ob_iloc = _find_ob_candle(
            bars, manip_iloc=manip_iloc, max_lookback=MAX_LOOKBACK_BARS,
            ob_side=cfg["side"],
        )
        if ob_iloc is None:
            return None
        ob_bar = bars.iloc[ob_iloc]
        ob_open = float(ob_bar["open"])
        ob_high = float(ob_bar["high"])
        ob_low = float(ob_bar["low"])
        ob_close = float(ob_bar["close"])
        if cfg["side"] == "bullish":
            ob_body_top = ob_open
            ob_body_bottom = ob_close
        else:
            ob_body_top = ob_close
            ob_body_bottom = ob_open

        # Walk forward from manipulation candle (next bar onwards) to find
        # confirmation. LAXEST emission rule (symmetric across direction):
        #   - bullish: close > body_bottom (= ob.close for down-close OB)
        #   - bearish: close < body_top    (= ob.close for up-close OB)
        # Both mean "close has reclaimed PAST the OB candle in the OB-thesis
        # direction." Earlier versions of this detector used a stricter
        # asymmetric rule for bearish (close < body_bottom = ob.open) which
        # made bearish OBs ~50% rarer than bullish; fixed 2026-05-09.
        if cfg["side"] == "bullish":
            confirmation_level = ob_body_bottom  # close > this
        else:
            confirmation_level = ob_body_top     # close < this
        confirm_iloc = _find_confirmation(
            bars,
            start_iloc=manip_iloc + 1,
            max_forward=MAX_CONFIRMATION_BARS,
            confirmation_level=confirmation_level,
            side=cfg["side"],
        )
        if confirm_iloc is None:
            return None
        confirm_bar = bars.iloc[confirm_iloc]
        confirm_close = float(confirm_bar["close"])
        confirm_ts = bars.index[confirm_iloc]
        confirm_ts_utc = _ts_to_utc(confirm_ts)

        # Confirmation flags — LAXEST is True by construction; stricter
        # rules may or may not have fired by this candle. Symmetric semantics:
        #   *_gt_ob_close: close has passed body's near edge      (LAXEST)
        #   *_gt_ob_open:  close has passed body's far edge       (MEDIUM)
        #   *_gt_ob_high:  close has passed range edge (incl wick) (STRICTEST)
        if cfg["side"] == "bullish":
            confirms_close_gt_ob_close = confirm_close > ob_close   # laxest
            confirms_close_gt_ob_open = confirm_close > ob_open     # medium
            confirms_close_gt_ob_high = confirm_close > ob_high     # strict
        else:
            confirms_close_gt_ob_close = confirm_close < ob_close   # laxest (bearish: below body_top)
            confirms_close_gt_ob_open = confirm_close < ob_open     # medium (below body_bottom)
            confirms_close_gt_ob_high = confirm_close < ob_low      # strict (below range)

        ob_zone_high = max(ob_high, ob_body_top)
        ob_zone_low = min(ob_low, ob_body_bottom)
        ob_mid = (ob_body_top + ob_body_bottom) / 2.0

        et_ts = confirm_ts_utc.astimezone(ET)
        event_data: dict[str, Any] = {
            "schema_version": 1,
            "detector_version": self.detector_version,
            "mode": ctx.mode,
            "direction": cfg["side"],
            "tracking_timeframe": cfg["tf"],
            "swept_reference": {
                "type": cfg["ref"],
                "level_price": float(ref.value),
                "level_set_ts_utc": ref.ts_utc.isoformat(),
                "prior_period_label": prior.label,
                "prior_period_start_utc": prior.start_utc.isoformat(),
                "prior_period_end_utc": prior.end_utc.isoformat(),
            },
            "manipulation_candle": _bar_dict(manipulation_bar, manipulation_ts),
            "ob_candle": _bar_dict(ob_bar, bars.index[ob_iloc]),
            "ob_body_top": float(ob_body_top),
            "ob_body_bottom": float(ob_body_bottom),
            "ob_body_mid": float(ob_mid),
            "ob_body_width_pts": float(ob_body_top - ob_body_bottom),
            "ob_range_top": float(ob_zone_high),
            "ob_range_bottom": float(ob_zone_low),
            "ob_range_width_pts": float(ob_zone_high - ob_zone_low),
            "bars_back_to_ob": int(manip_iloc - ob_iloc),
            "confirmation_candle": _bar_dict(confirm_bar, confirm_ts),
            "bars_to_confirm": int(confirm_iloc - manip_iloc),
            "confirms_close_gt_ob_close": bool(confirms_close_gt_ob_close),
            "confirms_close_gt_ob_open": bool(confirms_close_gt_ob_open),
            "confirms_close_gt_ob_high": bool(confirms_close_gt_ob_high),
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
            bar_end_utc=confirm_ts_utc,
            primary_symbol=symbol,
            symbols=[symbol],
            timeframe=cfg["tf"].upper(),
            side=cfg["side"],
            event_data=event_data,
            context=context,
            outcomes=None,
            replay_pointer={
                "primary_symbol": symbol,
                "ts_utc": confirm_ts_utc.isoformat(),
                "tracking_timeframe": cfg["tf"],
                "ob_body_top": float(ob_body_top),
                "ob_body_bottom": float(ob_body_bottom),
            },
            detector_version=self.detector_version,
        )


# ---------- helpers ----------


def _find_ob_candle(
    bars: pd.DataFrame,
    *,
    manip_iloc: int,
    max_lookback: int,
    ob_side: Literal["bullish", "bearish"],
) -> int | None:
    """Walk back from the manipulation candle (inclusive) up to
    `max_lookback` bars. Return the iloc of the first opposite-close
    candle found.

    Bullish setup: looking for the most recent DOWN-close (close < open).
    Bearish setup: looking for the most recent UP-close (close > open).

    If the manipulation candle itself qualifies, return manip_iloc.
    """
    earliest = max(0, manip_iloc - max_lookback)
    for i in range(manip_iloc, earliest - 1, -1):
        bar = bars.iloc[i]
        o = float(bar["open"])
        c = float(bar["close"])
        if ob_side == "bullish" and c < o:
            return i
        if ob_side == "bearish" and c > o:
            return i
    return None


def _find_confirmation(
    bars: pd.DataFrame,
    *,
    start_iloc: int,
    max_forward: int,
    confirmation_level: float,
    side: Literal["bullish", "bearish"],
) -> int | None:
    """First bar at or after `start_iloc` whose close passes the
    confirmation level (laxest rule).

    Bullish: close > confirmation_level (= ob.body_bottom = ob.close for down-close OB).
    Bearish: close < confirmation_level (= ob.body_top    = ob.close for up-close OB).

    Both correspond to "close has reclaimed past the OB candle in the
    OB-thesis direction."
    """
    end = min(len(bars), start_iloc + max_forward)
    for i in range(start_iloc, end):
        bar = bars.iloc[i]
        c = float(bar["close"])
        if side == "bullish" and c > confirmation_level:
            return i
        if side == "bearish" and c < confirmation_level:
            return i
    return None


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
        log.info("order_block: bar_reader missing %s %s: %s",
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
    """Yield Globex days that overlap [start_d, end_d] (date inputs)."""
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
    start_dt = datetime(start_d.year, start_d.month, start_d.day, tzinfo=UTC)
    end_dt = datetime(end_d.year, end_d.month, end_d.day, tzinfo=UTC) + timedelta(days=1)
    cur_day = globex_day_for(start_dt)
    while cur_day.start_utc < end_dt:
        sess = session_for(cur_day.start_utc + timedelta(hours=1), session_name)
        if sess.end_utc > start_dt:
            yield sess
        cur_day = globex_day_for(cur_day.end_utc + timedelta(seconds=1))


# ---------- registration ----------

register("order_block", OrderBlockDetector())
