"""SMT HTF reactions outcome computer.

Populates `outcomes` for events written by the
`smt_htf_reference_divergence` detector.

What it captures
----------------

For each SMT event, computes three blocks:

1. **period_close**: the state at end of period N.
   - Did the primary symbol stay on the swept side, or pull back?
   - Which laggers eventually confirmed by close, which never did?
   - Was the SMT divergence still active for this side at close?

2. **intra_period**: the move from the event bucket close to period
   N close, for the primary symbol.
   - MFE in thesis direction (manipulation reversed = expansion)
   - MAE against thesis (manipulation continued = breakout)

3. **next_period** (N+1) and **n_plus_2** (N+2): forward reaction.
   - Primary's return from N close to N+1 close (and N+2 close)
   - Did N+1 (or N+2) take out N's high? N's low?
   - thesis_confirmed: strict test = did N+1 take N's opposite
     extreme? (For high-side SMT: did N+1 low <= N low?)
   - MFE/MAE in thesis direction during N+1 (and N+2)

Thesis direction
----------------

The SMT trader's reading of a high-side SMT is: "manipulation grabbed
buy-side liquidity above prev high; price should expand DOWN." So:

  side == "high"  →  thesis_direction = "down"
  side == "low"   →  thesis_direction = "up"

"thesis_confirmed_n1" = did the primary symbol take N's opposite
extreme during N+1 (high-side: took N's low; low-side: took N's high).

What it does NOT capture
------------------------

- "Both-side active at close" requires sibling-event lookup (the same
  period might have a high-side AND a low-side event). That's a
  derived view via SQL, not a per-event outcome. Documented in
  docs/RESEARCH_DETECTORS.md as a post-hoc analysis pattern.
- News / volatility regime / session — context-only fields belong on
  the event itself, not its outcome.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

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


# Tracking timeframe per mode → minutes after event bucket starts that
# the bucket actually closes (= when we "knew" SMT was real).
_BUCKET_MINUTES = {"weekly_smt": 4 * 60, "previous_day_smt": 60}

# Period lookup function per event_type.
_PERIOD_FOR = {
    "weekly_smt": globex_week_for,
    "previous_day_smt": globex_day_for,
}


@dataclass(slots=True)
class _PeriodBounds:
    n: GlobexPeriod
    n_plus_1: GlobexPeriod
    n_plus_2: GlobexPeriod


class SmtHtfReactionsComputer:
    feature_name: str = "smt_htf_reference_divergence"
    # v2 (2026-05-09): added primary_period_high_ts + primary_period_low_ts
    # to period_close block so the marks-the-extreme v2 analysis can
    # compute time-gap from PSPs to the exact extreme bar without
    # re-loading 1m data per query.
    outcome_version: str = "v2"

    def compute(
        self,
        event: ResearchEvent,
        bar_reader: BarReader,
    ) -> dict[str, Any] | None:
        if event.event_type not in _PERIOD_FOR:
            log.warning(
                "smt_htf_reactions: unknown event_type %s (id=%s); skipping",
                event.event_type, event.id,
            )
            return None

        period_for = _PERIOD_FOR[event.event_type]
        bounds = _resolve_period_bounds(event.bar_end_utc, period_for)

        primary = event.primary_symbol
        side: Literal["high", "low"] = event.side  # type: ignore[assignment]
        if side not in ("high", "low"):
            log.warning(
                "smt_htf_reactions: bad side %r (id=%s)", side, event.id,
            )
            return None

        # Bucket close = event.bar_end_utc (which is bucket START per
        # pandas floor labeling) + tracking_interval. After this point
        # the SMT was knowable.
        bucket_minutes = _BUCKET_MINUTES[event.event_type]
        bucket_close_utc = _ensure_utc(event.bar_end_utc) + timedelta(
            minutes=bucket_minutes
        )

        primary_n = _load_primary_period(
            bar_reader, symbol=primary, period=bounds.n,
        )
        if primary_n is None or primary_n.empty:
            return None

        # Period close = last bar's close in period N.
        n_close_price = float(primary_n["close"].iloc[-1])
        n_high = float(primary_n["high"].max())
        n_low = float(primary_n["low"].min())
        # Extreme-bar timestamps — added v2 so marks-the-extreme analysis
        # can ask "how far in time was the PSP from the actual extreme?"
        # without re-loading 1m bars per query. ties broken by first-seen
        # (idxmax/idxmin).
        n_high_ts = primary_n["high"].idxmax()
        n_low_ts = primary_n["low"].idxmin()
        if isinstance(n_high_ts, pd.Timestamp):
            n_high_ts_iso = n_high_ts.isoformat()
        else:
            n_high_ts_iso = str(n_high_ts)
        if isinstance(n_low_ts, pd.Timestamp):
            n_low_ts_iso = n_low_ts.isoformat()
        else:
            n_low_ts_iso = str(n_low_ts)

        # Reference price for intra-period MFE/MAE: primary's close at
        # bucket close (i.e. when SMT became knowable). If the event
        # fired in the very last bucket of the period, fall back to
        # the close of the event bucket itself.
        intra_start_close = _close_at_or_after(primary_n, bucket_close_utc)
        if intra_start_close is None:
            intra_start_close = _close_at_or_after(
                primary_n, _ensure_utc(event.bar_end_utc)
            )

        intra_period_block = _compute_window_excursion(
            primary_n,
            window_start=bucket_close_utc,
            window_end=bounds.n.end_utc,
            reference_close=intra_start_close,
            side=side,
        )

        # ---- period_close block (state at end of period N) ----
        symbol_states = (event.event_data or {}).get("symbol_states", {})
        ref_for_primary = symbol_states.get(primary, {}).get(
            f"reference_{side}"
        )
        if ref_for_primary is None:
            log.info(
                "smt_htf_reactions: missing reference_%s for primary %s "
                "(id=%s); skipping",
                side, primary, event.id,
            )
            return None
        ref_for_primary = float(ref_for_primary)
        primary_close_vs_ref = n_close_price - ref_for_primary
        # "Still swept" = primary closed beyond its reference in the
        # SMT direction. high-side: close > ref_high. low-side: close < ref_low.
        if side == "high":
            primary_still_swept = n_close_price > ref_for_primary
        else:
            primary_still_swept = n_close_price < ref_for_primary

        lagging_swept, lagging_unswept = _split_laggers_by_resolution(
            event=event, side=side, symbol_states=symbol_states,
        )
        smt_active_for_side_at_close = len(lagging_unswept) > 0

        period_close_block: dict[str, Any] = {
            "ts_utc": bounds.n.end_utc.isoformat(),
            "primary_close_price": n_close_price,
            "primary_period_high": n_high,
            "primary_period_low": n_low,
            "primary_period_high_ts": n_high_ts_iso,
            "primary_period_low_ts": n_low_ts_iso,
            "primary_close_vs_reference_pts": primary_close_vs_ref,
            "primary_still_swept_at_close": bool(primary_still_swept),
            "lagging_swept_at_close": lagging_swept,
            "lagging_unswept_at_close": lagging_unswept,
            "n_lagging_unswept_at_close": len(lagging_unswept),
            "smt_active_for_side_at_close": bool(smt_active_for_side_at_close),
        }

        # ---- next_period block (N+1) ----
        next_period_block = _compute_period_reaction(
            bar_reader=bar_reader,
            symbol=primary,
            period=bounds.n_plus_1,
            n_close_price=n_close_price,
            n_high=n_high,
            n_low=n_low,
            side=side,
            label="n_plus_1",
        )

        # ---- n_plus_2 block ----
        n_plus_2_block = _compute_period_reaction(
            bar_reader=bar_reader,
            symbol=primary,
            period=bounds.n_plus_2,
            n_close_price=n_close_price,
            n_high=n_high,
            n_low=n_low,
            side=side,
            label="n_plus_2",
        )

        return {
            "schema_version": 1,
            "outcome_version": self.outcome_version,
            "thesis_direction": "down" if side == "high" else "up",
            "period_close": period_close_block,
            "intra_period": intra_period_block,
            "next_period": next_period_block,
            "n_plus_2": n_plus_2_block,
        }


# ---------- helpers ----------


def _resolve_period_bounds(
    event_ts: datetime,
    period_for,
) -> _PeriodBounds:
    n = period_for(event_ts)
    n_plus_1 = period_for(n.end_utc + timedelta(seconds=1))
    n_plus_2 = period_for(n_plus_1.end_utc + timedelta(seconds=1))
    return _PeriodBounds(n=n, n_plus_1=n_plus_1, n_plus_2=n_plus_2)


def _load_primary_period(
    bar_reader: BarReader,
    *,
    symbol: str,
    period: GlobexPeriod,
) -> pd.DataFrame | None:
    """Load 1m bars for one symbol in the given period, return a frame
    indexed by tz-aware UTC. None on missing data."""
    try:
        df = bar_reader(
            symbol=symbol,
            timeframe="1m",
            start=period.start_utc,
            end=period.end_utc,
        )
    except (FileNotFoundError, ValueError) as exc:
        log.info(
            "outcome bar_reader missing for %s in %s: %s",
            symbol, period.label, exc,
        )
        return None
    if df is None or len(df) == 0:
        return None
    df = _normalize_index(df)
    # Strict half-open slice [start, end)
    mask = (df.index >= period.start_utc) & (df.index < period.end_utc)
    sliced = df.loc[mask]
    return sliced if not sliced.empty else None


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    """Whatever shape `read_bars` returns, end up with a tz-aware UTC
    DatetimeIndex. The warehouse reader returns `ts_event` as a column."""
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


def _close_at_or_after(
    df: pd.DataFrame, ts: datetime,
) -> float | None:
    """Return the close of the first bar at-or-after ts. None if no
    such bar exists."""
    after = df[df.index >= ts]
    if after.empty:
        return None
    return float(after["close"].iloc[0])


def _compute_window_excursion(
    df: pd.DataFrame,
    *,
    window_start: datetime,
    window_end: datetime,
    reference_close: float | None,
    side: Literal["high", "low"],
) -> dict[str, Any]:
    """MFE/MAE of `df` over [window_start, window_end), measured from
    `reference_close`, oriented to the SMT thesis direction.

    Returns a dict with mfe_pts/mae_pts plus n_bars and the actual
    window endpoints (None if no data in window)."""
    if reference_close is None:
        return _empty_excursion()
    mask = (df.index >= window_start) & (df.index < window_end)
    win = df.loc[mask]
    if win.empty:
        return _empty_excursion()
    win_high = float(win["high"].max())
    win_low = float(win["low"].min())
    if side == "high":
        # Thesis direction = DOWN
        mfe_pts = reference_close - win_low  # how far down it went
        mae_pts = win_high - reference_close  # how far up against thesis
    else:
        # Thesis direction = UP
        mfe_pts = win_high - reference_close
        mae_pts = reference_close - win_low
    return {
        "n_bars": int(len(win)),
        "reference_close": float(reference_close),
        "window_high": win_high,
        "window_low": win_low,
        "mfe_pts_in_thesis": float(mfe_pts),
        "mae_pts_against_thesis": float(mae_pts),
    }


def _empty_excursion() -> dict[str, Any]:
    return {
        "n_bars": 0,
        "reference_close": None,
        "window_high": None,
        "window_low": None,
        "mfe_pts_in_thesis": None,
        "mae_pts_against_thesis": None,
    }


def _compute_period_reaction(
    *,
    bar_reader: BarReader,
    symbol: str,
    period: GlobexPeriod,
    n_close_price: float,
    n_high: float,
    n_low: float,
    side: Literal["high", "low"],
    label: str,
) -> dict[str, Any]:
    """Forward reaction over one Globex period (N+1 or N+2)."""
    primary_period = _load_primary_period(
        bar_reader, symbol=symbol, period=period,
    )
    if primary_period is None or primary_period.empty:
        return {
            "ts_utc_start": period.start_utc.isoformat(),
            "ts_utc_close": period.end_utc.isoformat(),
            "n_bars": 0,
            "primary_close_price": None,
            "primary_return_pts": None,
            "primary_return_pct": None,
            "primary_period_high": None,
            "primary_period_low": None,
            "primary_took_period_n_high": None,
            "primary_took_period_n_low": None,
            "thesis_confirmed_strict": None,
            "n1_close_moved_with_thesis": None,
            "mfe_pts_in_thesis": None,
            "mae_pts_against_thesis": None,
        }
    period_close_price = float(primary_period["close"].iloc[-1])
    period_high = float(primary_period["high"].max())
    period_low = float(primary_period["low"].min())

    return_pts = period_close_price - n_close_price
    return_pct = return_pts / n_close_price * 100.0 if n_close_price else None

    took_n_high = period_high > n_high
    took_n_low = period_low < n_low

    if side == "high":
        # Thesis = DOWN. Strict confirmation = took N's low.
        thesis_confirmed_strict = took_n_low
        close_moved_with_thesis = period_close_price < n_close_price
        mfe_pts_in_thesis = n_close_price - period_low
        mae_pts_against_thesis = period_high - n_close_price
    else:
        # Thesis = UP. Strict confirmation = took N's high.
        thesis_confirmed_strict = took_n_high
        close_moved_with_thesis = period_close_price > n_close_price
        mfe_pts_in_thesis = period_high - n_close_price
        mae_pts_against_thesis = n_close_price - period_low

    return {
        "ts_utc_start": period.start_utc.isoformat(),
        "ts_utc_close": period.end_utc.isoformat(),
        "n_bars": int(len(primary_period)),
        "primary_close_price": period_close_price,
        "primary_return_pts": float(return_pts),
        "primary_return_pct": float(return_pct) if return_pct is not None else None,
        "primary_period_high": period_high,
        "primary_period_low": period_low,
        "primary_took_period_n_high": bool(took_n_high),
        "primary_took_period_n_low": bool(took_n_low),
        "thesis_confirmed_strict": bool(thesis_confirmed_strict),
        "close_moved_with_thesis": bool(close_moved_with_thesis),
        "mfe_pts_in_thesis": float(mfe_pts_in_thesis),
        "mae_pts_against_thesis": float(mae_pts_against_thesis),
    }


def _split_laggers_by_resolution(
    *,
    event: ResearchEvent,
    side: Literal["high", "low"],
    symbol_states: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """For the laggers at break, split into (eventually swept by close)
    and (never swept by close). Reads from symbol_states.broke_<side>
    which the detector populates by walking ALL tracking candles in the
    period."""
    laggers_at_break = (event.event_data or {}).get(
        "lagging_symbols_at_break", []
    ) or []
    lagging_swept: list[str] = []
    lagging_unswept: list[str] = []
    for sym in laggers_at_break:
        st = symbol_states.get(sym, {})
        if st.get(f"broke_{side}"):
            lagging_swept.append(sym)
        else:
            lagging_unswept.append(sym)
    return lagging_swept, lagging_unswept


def _ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


# ---------- registration ----------

register("smt_htf_reactions_v1", SmtHtfReactionsComputer())
