"""SMT HTF reference-level divergence detector.

Captures the canonical Smart Money Technique pattern:

  > One index takes a higher-timeframe reference high/low. The other
  > correlated indexes do not (yet). The divergence is the signal.

Two modes:

  - **weekly_smt**:        previous-week reference, 4H tracking candles
  - **previous_day_smt**:  previous-day reference, 1H tracking candles

Detection rule (precise):

  1. For each scan window (Globex week for weekly, Globex day for
     previous-day), look up the prior Globex period as the reference.
  2. For each symbol, compute the reference high (max) and reference
     low (min) over all 1m bars in the prior period.
  3. Walk the current period's tracking candles in order.
  4. On each tracking candle, identify which symbols have broken
     their reference high (low side: broken low) on or before that
     candle's close.
  5. The instant exactly ONE symbol's break-set first contains a
     side that no other symbol's break-set has yet → fire one event.
     The breaking symbol becomes `first_break_symbol`. Other symbols
     in the same break_set on the same candle (a "co-break") are
     listed as `confirming_symbols_at_break`. Symbols not yet in
     the break_set are `lagging_symbols_at_break`.
  6. Tie-breaker: if ALL symbols break on the same tracking candle,
     do NOT fire — that's a correlated breakout, not divergence.
  7. After firing, walk forward through remaining candles in the
     period to record `later_confirmations` for laggers (when, if
     ever, they each break too).
  8. One event per (mode, side, period). If no symbol breaks the
     reference at all in the period, no event.

Event identity is via `make_event_id(feature_name, primary_symbol,
bar_end_utc, event_type)`. Re-running the scan is idempotent.

This is a research-event detector, NOT a trading signal. The scan
writes ResearchEvent rows for analysis. No order placement, no live
behavior.

Cross-link: docs/RESEARCH_KNOWLEDGE_LAYER.md (taxonomy),
docs/RESEARCH_DETECTORS.md (how to add another).
"""

from __future__ import annotations

import logging
from datetime import date as date_type, datetime, timedelta, timezone
from typing import Any, Literal

import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.research.reference_levels import compute_reference_level
from app.research.sessions import (
    GlobexPeriod,
    globex_day_for,
    globex_week_for,
    previous_globex_day,
    previous_globex_week,
)
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
log = logging.getLogger(__name__)

Mode = Literal["weekly_smt", "previous_day_smt"]


_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "weekly_smt": {
        "tracking_timeframe": "4h",
        "reference_label": "previous_week",
        "period_for": globex_week_for,
        "previous_period": previous_globex_week,
        "step_advance": timedelta(days=7),
    },
    "previous_day_smt": {
        "tracking_timeframe": "1h",
        "reference_label": "previous_day",
        "period_for": globex_day_for,
        "previous_period": previous_globex_day,
        "step_advance": timedelta(days=1),
    },
}


class SmtHtfReferenceDivergenceDetector:
    """First registered detector — see module docstring."""

    feature_name: str = "smt_htf_reference_divergence"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = ("weekly_smt", "previous_day_smt")

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                "smt_htf_reference_divergence requires --mode "
                f"{{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_CONFIG:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if len(ctx.symbols) < 2:
            raise ValueError(
                "SMT requires at least 2 symbols (got "
                f"{len(ctx.symbols)})"
            )

        cfg = _MODE_CONFIG[ctx.mode]
        events: list[ResearchEventCreate] = []

        for period in _iterate_periods(
            start=ctx.start,
            end=ctx.end,
            period_for=cfg["period_for"],
            step=cfg["step_advance"],
        ):
            prev_period: GlobexPeriod = cfg["previous_period"](period.start_utc)
            for side in ("high", "low"):
                event = self._scan_one_period(
                    ctx=ctx,
                    mode=ctx.mode,
                    cfg=cfg,
                    current_period=period,
                    prev_period=prev_period,
                    side=side,  # type: ignore[arg-type]
                )
                if event is not None:
                    events.append(event)

        return events

    def _scan_one_period(
        self,
        *,
        ctx: DetectorContext,
        mode: str,
        cfg: dict[str, Any],
        current_period: GlobexPeriod,
        prev_period: GlobexPeriod,
        side: Literal["high", "low"],
    ) -> ResearchEventCreate | None:
        """Detect at most one SMT event for one (period, side)."""
        # --- 1) Reference levels per symbol from prev_period 1m bars ---
        symbol_states: dict[str, dict[str, Any]] = {}
        for symbol in ctx.symbols:
            ref_bars = _safe_load(
                ctx.bar_reader,
                symbol=symbol,
                timeframe="1m",
                start=prev_period.start_utc,
                end=prev_period.end_utc,
            )
            if ref_bars is None or ref_bars.empty:
                # Missing data for the reference period → can't compute
                # reference levels for this symbol. Skip the period
                # (would produce a false "broke" event otherwise).
                log.info(
                    "smt_htf: missing prev-period 1m bars for %s in %s — "
                    "skipping period %s",
                    symbol,
                    prev_period.label,
                    current_period.start_utc.isoformat(),
                )
                return None
            ref_high = compute_reference_level(
                ref_bars,
                side="high",
                start_utc=prev_period.start_utc,
                end_utc=prev_period.end_utc,
            )
            ref_low = compute_reference_level(
                ref_bars,
                side="low",
                start_utc=prev_period.start_utc,
                end_utc=prev_period.end_utc,
            )
            if ref_high is None or ref_low is None:
                return None
            symbol_states[symbol] = {
                "reference_high": ref_high.value,
                "reference_high_ts_utc": ref_high.ts_utc,
                "reference_low": ref_low.value,
                "reference_low_ts_utc": ref_low.ts_utc,
                "broke_high": False,
                "high_break_time_utc": None,
                "high_break_price": None,
                "broke_low": False,
                "low_break_time_utc": None,
                "low_break_price": None,
            }

        # --- 2) Tracking candles per symbol from current_period ---
        tracking_bars: dict[str, pd.DataFrame] = {}
        for symbol in ctx.symbols:
            df = _safe_load(
                ctx.bar_reader,
                symbol=symbol,
                timeframe=cfg["tracking_timeframe"],
                start=current_period.start_utc,
                end=current_period.end_utc,
            )
            if df is None or df.empty:
                log.info(
                    "smt_htf: missing tracking bars for %s in %s — "
                    "skipping period %s",
                    symbol,
                    cfg["tracking_timeframe"],
                    current_period.start_utc.isoformat(),
                )
                return None
            tracking_bars[symbol] = _ensure_utc_index(df)

        # --- 3) Per-symbol break detection for the requested side ---
        breaks: dict[str, dict[str, Any] | None] = {}
        for symbol in ctx.symbols:
            df = tracking_bars[symbol]
            ref_value = symbol_states[symbol][f"reference_{side}"]
            if side == "high":
                # First candle whose HIGH exceeds the reference high
                hits = df[df["high"] > ref_value]
            else:
                hits = df[df["low"] < ref_value]
            if hits.empty:
                breaks[symbol] = None
                continue
            first = hits.iloc[0]
            ts = hits.index[0]
            if not isinstance(ts, pd.Timestamp):
                ts = pd.Timestamp(ts)
            ts_utc = ts.to_pydatetime()
            if ts_utc.tzinfo is None:
                ts_utc = ts_utc.replace(tzinfo=UTC)
            breaks[symbol] = {
                "candle_ts_utc": ts_utc,
                "price": float(first["high"] if side == "high" else first["low"]),
            }
            symbol_states[symbol][f"broke_{side}"] = True
            symbol_states[symbol][f"{side}_break_time_utc"] = ts_utc.isoformat()
            symbol_states[symbol][f"{side}_break_price"] = float(
                first["high"] if side == "high" else first["low"]
            )

        # --- 4) Find first-break symbol(s) ---
        breakers = {s: b for s, b in breaks.items() if b is not None}
        if not breakers:
            return None  # nothing broke this side → no event
        # Earliest break ts wins; co-break ties get bucketed together
        earliest_ts = min(b["candle_ts_utc"] for b in breakers.values())
        co_breakers = [
            s for s, b in breakers.items() if b["candle_ts_utc"] == earliest_ts
        ]
        laggers_at_break = [
            s
            for s in ctx.symbols
            if s not in breakers
            or (breakers[s] is not None and breakers[s]["candle_ts_utc"] > earliest_ts)
        ]

        # --- 5) Tie-breaker: skip if EVERY symbol broke in the same candle ---
        if not laggers_at_break:
            log.debug(
                "smt_htf: all symbols broke %s in same candle %s — "
                "skipping (correlated breakout, not divergence)",
                side,
                earliest_ts.isoformat(),
            )
            return None

        # By convention, primary_symbol is the alphabetically-first
        # co-breaker — stable, deterministic, doesn't change between
        # runs. Tests rely on this.
        co_breakers_sorted = sorted(co_breakers)
        first_break_symbol = co_breakers_sorted[0]
        confirming_at_break = co_breakers_sorted[1:]

        # --- 6) Later confirmations (laggers that broke later in window) ---
        later_confirmations: list[dict[str, Any]] = []
        for lagger in laggers_at_break:
            b = breaks.get(lagger)
            if b is None:
                continue
            later_confirmations.append(
                {
                    "symbol": lagger,
                    "confirm_time_utc": b["candle_ts_utc"].isoformat(),
                    "confirm_price": b["price"],
                }
            )

        n_unconfirmed = len(laggers_at_break) - len(later_confirmations)
        did_all_confirm = n_unconfirmed == 0
        if did_all_confirm and later_confirmations:
            last_confirm = max(
                datetime.fromisoformat(c["confirm_time_utc"])
                for c in later_confirmations
            )
            divergence_duration_seconds = int(
                (last_confirm - earliest_ts).total_seconds()
            )
        else:
            divergence_duration_seconds = None

        # --- 7) Build the ResearchEventCreate payload ---
        event_data: dict[str, Any] = {
            "detector_version": self.detector_version,
            "reference_type": cfg["reference_label"],
            "reference_start_utc": prev_period.start_utc.isoformat(),
            "reference_end_utc": prev_period.end_utc.isoformat(),
            "tracking_timeframe": cfg["tracking_timeframe"],
            "side": side,
            "first_break_symbol": first_break_symbol,
            "first_break_time_utc": earliest_ts.isoformat(),
            "first_break_price": breakers[first_break_symbol]["price"],
            "lagging_symbols_at_break": list(laggers_at_break),
            "confirming_symbols_at_break": confirming_at_break,
            "symbol_states": _serialize_symbol_states(symbol_states),
            "later_confirmations": later_confirmations,
            "divergence_duration_seconds": divergence_duration_seconds,
            "did_all_confirm_by_window_end": did_all_confirm,
        }

        et_break = earliest_ts.astimezone(_ET)
        context: dict[str, Any] = {
            "day_of_week_et": et_break.weekday(),
            "hour_of_day_et": et_break.hour,
            "current_period_label": current_period.label,
            "current_period_start_utc": current_period.start_utc.isoformat(),
            "current_period_end_utc": current_period.end_utc.isoformat(),
        }

        event_type: str = ctx.mode  # "weekly_smt" | "previous_day_smt"
        return ResearchEventCreate(
            feature_name=self.feature_name,
            event_type=event_type,
            bar_end_utc=earliest_ts,
            primary_symbol=first_break_symbol,
            symbols=list(ctx.symbols),
            timeframe=cfg["tracking_timeframe"].upper(),  # "4H" / "1H"
            side=side,
            event_data=event_data,
            context=context,
            outcomes=None,  # v1: outcomes deferred to a forward-window post-processor
            replay_pointer={
                "primary_symbol": first_break_symbol,
                "ts_utc": earliest_ts.isoformat(),
                "tracking_timeframe": cfg["tracking_timeframe"],
            },
            detector_version=self.detector_version,
        )


# ---------- helpers ----------


from zoneinfo import ZoneInfo  # noqa: E402

_ET = ZoneInfo("America/New_York")


def _safe_load(
    bar_reader: BarReader,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame | None:
    """Call the bar_reader, swallow / log a missing-data style error.

    The existing `app.data.reader.read_bars` raises FileNotFoundError /
    similar when partitions are missing; we treat that as "no data
    here, skip" rather than a fatal scan error.
    """
    try:
        df = bar_reader(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
        )
    except (FileNotFoundError, ValueError) as exc:
        log.info("bar_reader missing/invalid for %s %s: %s", symbol, timeframe, exc)
        return None
    if df is None or len(df) == 0:
        return None
    return df


def _ensure_utc_index(df: pd.DataFrame) -> pd.DataFrame:
    """Whatever the reader gave us, return a frame indexed by tz-aware
    UTC timestamps. Tolerates both DatetimeIndex and a `ts_event`
    column."""
    if isinstance(df.index, pd.DatetimeIndex):
        if df.index.tz is None:
            return df.tz_localize("UTC")
        return df.tz_convert("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        if out.index.tz is None:
            return out.tz_localize("UTC")
        return out.tz_convert("UTC")
    raise ValueError("bar_reader returned a frame with no usable timestamp")


def _iterate_periods(
    *,
    start: date_type,
    end: date_type,
    period_for,
    step: timedelta,
):
    """Walk Globex periods that overlap [start, end). Step is a
    coarse hop (one week or one day) — slight imprecision on DST
    boundaries is tolerated since `period_for(probe)` always
    re-anchors."""
    start_dt = datetime(start.year, start.month, start.day, tzinfo=UTC)
    end_dt = datetime(end.year, end.month, end.day, tzinfo=UTC)
    seen: set[tuple[datetime, datetime]] = set()
    cursor = start_dt
    while cursor < end_dt:
        period: GlobexPeriod = period_for(cursor)
        key = (period.start_utc, period.end_utc)
        if key not in seen and period.end_utc > start_dt:
            seen.add(key)
            yield period
        cursor = max(cursor + step, period.end_utc)


def _serialize_symbol_states(
    states: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Convert datetime objects in symbol_states to ISO strings so the
    JSON column stores them losslessly."""
    out: dict[str, dict[str, Any]] = {}
    for symbol, st in states.items():
        out[symbol] = {
            k: (v.isoformat() if isinstance(v, datetime) else v)
            for k, v in st.items()
        }
    return out


# ---------- registration ----------

register(
    "smt_htf_reference_divergence",
    SmtHtfReferenceDivergenceDetector(),
)
