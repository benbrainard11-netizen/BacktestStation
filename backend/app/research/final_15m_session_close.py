"""Final 15-minute session-close study.

Research question:

    Does the closing position of the final 15-minute candle of the
    Globex session predict next-session bullish or bearish behavior?

This is a research study, not a strategy. Feature columns use only the
current completed session. Outcome columns use the following completed
session and must never be fed back into a live entry decision.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Literal
from zoneinfo import ZoneInfo

import pandas as pd
from scipy import stats

from app.research.sessions import GlobexPeriod, globex_day_for

ET = ZoneInfo("America/New_York")
UTC = dt.UTC

FINAL_CANDLE_MINUTES = 15
RTH_OPEN_ET = dt.time(9, 30)
OPENING_RANGE_MINUTES = 30
EARLY_GLOBEX_MINUTES = 120
EARLY_RTH_MINUTES = 60
ROLLING_RANGE_LOOKBACK = 20
ROLLING_RANGE_MIN_PERIODS = 10

CloseBucket = Literal[
    "strong_bearish",
    "bearish",
    "middle",
    "bullish",
    "strong_bullish",
    "undefined",
]
CloseBias = Literal["bearish", "neutral", "bullish", "undefined"]

_CLOSE_BUCKET_ORDER = [
    "strong_bearish",
    "bearish",
    "middle",
    "bullish",
    "strong_bullish",
    "undefined",
]
_CLOSE_BIAS_ORDER = ["bearish", "neutral", "bullish", "undefined"]


@dataclass(frozen=True)
class SessionStudyConfig:
    """Study settings that define labels and keep runs reproducible."""

    symbol: str
    start: dt.date
    end: dt.date
    timeframe: str = "15m"
    session: str = "globex_day"
    final_candle_minutes: int = FINAL_CANDLE_MINUTES
    direction_deadzone_pts: float = 0.0
    prior_break_buffer_pts: float = 0.0


@dataclass(frozen=True)
class SessionSummary:
    """OHLC summary for one Globex session."""

    period: GlobexPeriod
    label_date: dt.date
    open: float
    high: float
    low: float
    close: float
    bar_count: int

    @property
    def range_pts(self) -> float:
        return self.high - self.low


@dataclass(frozen=True)
class WindowSummary:
    """OHLC summary for a smaller intraday window inside a session."""

    open: float
    high: float
    low: float
    close: float
    bar_count: int

    @property
    def range_pts(self) -> float:
        return self.high - self.low

    @property
    def return_pts(self) -> float:
        return self.close - self.open


def build_final_15m_session_close_study(
    bars: pd.DataFrame,
    *,
    symbol: str,
    start: dt.date,
    end: dt.date,
    direction_deadzone_pts: float = 0.0,
    prior_break_buffer_pts: float = 0.0,
) -> pd.DataFrame:
    """Build one row per completed Globex session with next-session outcomes.

    `start` and `end` are ET Globex label dates. The label date is the
    calendar date on which the session closes at 17:00 ET.
    """

    if start >= end:
        raise ValueError("start must be before end")
    if direction_deadzone_pts < 0:
        raise ValueError("direction_deadzone_pts must be >= 0")
    if prior_break_buffer_pts < 0:
        raise ValueError("prior_break_buffer_pts must be >= 0")

    df = _normalize_bars(bars)
    periods = globex_day_periods(start=start, end=end)
    rows: list[dict[str, object]] = []

    for period in periods:
        final_bar = final_15m_candle(df, period)
        if final_bar is None:
            continue
        session = summarize_session(df, period)
        if session is None:
            continue
        next_period = next_globex_day(period)
        next_session = summarize_session(df, next_period)
        if next_session is None:
            continue
        next_bars = slice_session(df, next_period)
        if next_bars.empty:
            continue
        rows.append(
            _build_row(
                symbol=symbol,
                session=session,
                final_bar=final_bar,
                next_session=next_session,
                next_bars=next_bars,
                direction_deadzone_pts=direction_deadzone_pts,
                prior_break_buffer_pts=prior_break_buffer_pts,
            )
        )

    return _add_prior_context_columns(pd.DataFrame(rows))


def globex_day_periods(*, start: dt.date, end: dt.date) -> list[GlobexPeriod]:
    """Return Globex day periods whose ET label date is in [start, end)."""

    periods: list[GlobexPeriod] = []
    cur = start
    while cur < end:
        # Globex sessions close Monday-Friday at 17:00 ET. Saturday and
        # Sunday have no session close label.
        if cur.weekday() < 5:
            ref = dt.datetime.combine(cur, dt.time(12, 0), tzinfo=ET)
            period = globex_day_for(ref)
            if _period_label_date(period) == cur:
                periods.append(period)
        cur += dt.timedelta(days=1)
    return periods


def next_globex_day(period: GlobexPeriod) -> GlobexPeriod:
    """Return the next tradable Globex day after `period`."""

    return globex_day_for(period.end_utc + dt.timedelta(hours=2))


def final_15m_candle(
    bars: pd.DataFrame,
    period: GlobexPeriod,
) -> pd.Series | None:
    """Return the 16:45-17:00 ET candle for the Globex day."""

    df = _normalize_bars(bars)
    final_start = period.end_utc - dt.timedelta(minutes=FINAL_CANDLE_MINUTES)
    matches = df.loc[df.index == pd.Timestamp(final_start)]
    if matches.empty:
        return None
    return matches.iloc[-1]


def slice_session(bars: pd.DataFrame, period: GlobexPeriod) -> pd.DataFrame:
    df = _normalize_bars(bars)
    return df.loc[
        (df.index >= pd.Timestamp(period.start_utc))
        & (df.index < pd.Timestamp(period.end_utc))
    ].copy()


def summarize_session(
    bars: pd.DataFrame,
    period: GlobexPeriod,
) -> SessionSummary | None:
    window = slice_session(bars, period)
    if window.empty:
        return None
    return SessionSummary(
        period=period,
        label_date=_period_label_date(period),
        open=float(window["open"].iloc[0]),
        high=float(window["high"].max()),
        low=float(window["low"].min()),
        close=float(window["close"].iloc[-1]),
        bar_count=int(len(window)),
    )


def close_position(close: float, high: float, low: float) -> float | None:
    """Return where the close sits inside a candle/session range.

    0.0 means the close is at the low. 1.0 means the close is at the
    high. Values between those two tell us how strong/weak the close was.
    """

    range_pts = high - low
    if not math.isfinite(range_pts) or range_pts <= 0:
        return None
    return float((close - low) / range_pts)


def close_bucket(value: float | None) -> CloseBucket:
    if value is None or not math.isfinite(value):
        return "undefined"
    if value <= 0.20:
        return "strong_bearish"
    if value <= 0.40:
        return "bearish"
    if value < 0.60:
        return "middle"
    if value < 0.80:
        return "bullish"
    return "strong_bullish"


def close_bias(value: float | None) -> CloseBias:
    if value is None or not math.isfinite(value):
        return "undefined"
    if value <= 0.40:
        return "bearish"
    if value >= 0.60:
        return "bullish"
    return "neutral"


def summarize_study(study: pd.DataFrame) -> dict[str, pd.DataFrame | dict[str, object]]:
    """Build distributions, descriptive stats, and significance tests."""

    if study.empty:
        empty = pd.DataFrame()
        return {
            "overview": {"rows": 0},
            "close_bucket_distribution": empty,
            "close_bias_distribution": empty,
            "bucket_stats": empty,
            "targeted_effect_stats": empty,
            "context_effects": empty,
            "categorical_tests": empty,
            "numeric_tests": empty,
        }

    overview = {
        "rows": int(len(study)),
        "symbol": str(study["symbol"].iloc[0]),
        "first_session_date": str(study["session_date"].min()),
        "last_session_date": str(study["session_date"].max()),
        "bullish_next_day_rate": float((study["next_direction"] == "bullish").mean()),
        "bearish_next_day_rate": float((study["next_direction"] == "bearish").mean()),
        "flat_next_day_rate": float((study["next_direction"] == "flat").mean()),
    }
    return {
        "overview": overview,
        "close_bucket_distribution": distribution(study, "final_close_bucket"),
        "close_bias_distribution": distribution(study, "final_close_bias"),
        "bucket_stats": bucket_stats(study),
        "targeted_effect_stats": targeted_effect_stats(study),
        "context_effects": context_effects(study),
        "categorical_tests": categorical_tests(study),
        "numeric_tests": numeric_tests(study),
    }


def distribution(study: pd.DataFrame, column: str) -> pd.DataFrame:
    counts = study[column].value_counts(dropna=False).rename_axis(column)
    out = counts.reset_index(name="count")
    out["pct"] = out["count"] / len(study)
    return _sort_category(out, column)


def bucket_stats(study: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for bucket in _CLOSE_BUCKET_ORDER:
        group = study.loc[study["final_close_bucket"] == bucket]
        if group.empty:
            continue
        rows.append(
            {
                "final_close_bucket": bucket,
                "count": int(len(group)),
                "pct": float(len(group) / len(study)),
                "next_bullish_rate": _rate(group["next_direction"] == "bullish"),
                "next_bearish_rate": _rate(group["next_direction"] == "bearish"),
                "next_flat_rate": _rate(group["next_direction"] == "flat"),
                "mean_next_return_pts": _mean(group["next_return_pts"]),
                "median_next_return_pts": _median(group["next_return_pts"]),
                "mean_next_close_position": _mean(group["next_close_position"]),
                "took_prior_high_rate": _rate(group["next_took_prior_session_high"]),
                "took_prior_low_rate": _rate(group["next_took_prior_session_low"]),
                "prior_high_first_rate": _rate(
                    group["next_first_break"] == "prior_high_first"
                ),
                "prior_low_first_rate": _rate(
                    group["next_first_break"] == "prior_low_first"
                ),
                "mean_next_mfe_up_pts": _mean(group["next_mfe_up_pts"]),
                "mean_next_mae_down_pts": _mean(group["next_mae_down_pts"]),
            }
        )
    return pd.DataFrame(rows)


def targeted_effect_stats(study: pd.DataFrame) -> pd.DataFrame:
    """Summarize the more targeted next-session effects by final close bucket."""

    rows: list[dict[str, object]] = []
    for bucket in _CLOSE_BUCKET_ORDER:
        group = study.loc[study["final_close_bucket"] == bucket]
        if group.empty:
            continue
        rows.append(
            {
                "final_close_bucket": bucket,
                "count": int(len(group)),
                "overnight_bullish_rate": _rate(
                    _col(group, "next_overnight_direction") == "bullish"
                ),
                "overnight_bearish_rate": _rate(
                    _col(group, "next_overnight_direction") == "bearish"
                ),
                "overnight_continuation_rate": _rate(
                    _col(group, "next_overnight_continues_final_bias")
                ),
                "mean_overnight_return_pts": _mean(
                    _col(group, "next_overnight_return_pts")
                ),
                "early_globex_2h_bullish_rate": _rate(
                    _col(group, "next_early_globex_2h_direction") == "bullish"
                ),
                "early_globex_2h_continuation_rate": _rate(
                    _col(group, "next_early_globex_2h_continues_final_bias")
                ),
                "mean_early_globex_2h_return_pts": _mean(
                    _col(group, "next_early_globex_2h_return_pts")
                ),
                "rth_first_60m_bullish_rate": _rate(
                    _col(group, "next_rth_first_60m_direction") == "bullish"
                ),
                "rth_first_60m_continuation_rate": _rate(
                    _col(group, "next_rth_first_60m_continues_final_bias")
                ),
                "mean_rth_first_60m_return_pts": _mean(
                    _col(group, "next_rth_first_60m_return_pts")
                ),
                "prior_high_swept_first_rate": _rate(
                    _col(group, "next_first_liquidity_sweep")
                    == "prior_high_swept_first"
                ),
                "prior_low_swept_first_rate": _rate(
                    _col(group, "next_first_liquidity_sweep")
                    == "prior_low_swept_first"
                ),
                "or30_high_first_rate": _rate(
                    _col(group, "next_or30_first_break")
                    == "opening_range_high_first"
                ),
                "or30_low_first_rate": _rate(
                    _col(group, "next_or30_first_break")
                    == "opening_range_low_first"
                ),
            }
        )
    return pd.DataFrame(rows)


def context_effects(study: pd.DataFrame, *, min_count: int = 20) -> pd.DataFrame:
    """Find regimes where final-candle bias has a larger targeted effect.

    Context columns must be known by the current session close. This table is
    descriptive only; promising rows still need separate validation.
    """

    context_cols = [
        "day_name_et",
        "final_body_direction",
        "session_direction",
        "session_close_bias",
        "prior_session_direction",
        "prior20_range_regime",
    ]
    rows: list[dict[str, object]] = []
    for context_col in context_cols:
        if context_col not in study.columns:
            continue
        grouped = study.groupby([context_col, "final_close_bias"], dropna=False)
        for (context_value, final_bias), group in grouped:
            if len(group) < min_count:
                continue
            rows.append(
                {
                    "context": context_col,
                    "context_value": str(context_value),
                    "final_close_bias": str(final_bias),
                    "count": int(len(group)),
                    "pct_of_study": float(len(group) / len(study)),
                    "overnight_continuation_rate": _rate(
                        _col(group, "next_overnight_continues_final_bias")
                    ),
                    "early_globex_2h_continuation_rate": _rate(
                        _col(group, "next_early_globex_2h_continues_final_bias")
                    ),
                    "rth_first_60m_continuation_rate": _rate(
                        _col(group, "next_rth_first_60m_continues_final_bias")
                    ),
                    "mean_overnight_return_pts": _mean(
                        _col(group, "next_overnight_return_pts")
                    ),
                    "mean_early_globex_2h_return_pts": _mean(
                        _col(group, "next_early_globex_2h_return_pts")
                    ),
                    "mean_rth_first_60m_return_pts": _mean(
                        _col(group, "next_rth_first_60m_return_pts")
                    ),
                    "prior_high_swept_first_rate": _rate(
                        _col(group, "next_first_liquidity_sweep")
                        == "prior_high_swept_first"
                    ),
                    "prior_low_swept_first_rate": _rate(
                        _col(group, "next_first_liquidity_sweep")
                        == "prior_low_swept_first"
                    ),
                    "or30_high_first_rate": _rate(
                        _col(group, "next_or30_first_break")
                        == "opening_range_high_first"
                    ),
                    "or30_low_first_rate": _rate(
                        _col(group, "next_or30_first_break")
                        == "opening_range_low_first"
                    ),
                }
            )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["context", "context_value", "final_close_bias"]
    )


def categorical_tests(study: pd.DataFrame) -> pd.DataFrame:
    tests = [
        ("final_close_bucket", "next_direction"),
        ("final_close_bias", "next_direction"),
        ("final_close_bucket", "next_first_break"),
        ("final_close_bucket", "next_first_liquidity_sweep"),
        ("final_close_bias", "next_first_liquidity_sweep"),
        ("final_close_bucket", "next_overnight_direction"),
        ("final_close_bias", "next_overnight_continues_final_bias"),
        ("final_close_bucket", "next_or30_first_break"),
        ("final_close_bucket", "next_rth_first_60m_direction"),
        ("final_close_bucket", "next_close_bucket"),
        ("final_close_bias", "next_took_prior_session_high"),
        ("final_close_bias", "next_took_prior_session_low"),
    ]
    rows = [
        _chi_square_test(study, feature, outcome)
        for feature, outcome in tests
        if feature in study.columns and outcome in study.columns
    ]
    return pd.DataFrame([row for row in rows if row is not None])


def numeric_tests(study: pd.DataFrame) -> pd.DataFrame:
    tests = [
        ("final_close_bucket", "next_return_pts"),
        ("final_close_bucket", "next_close_position"),
        ("final_close_bucket", "next_mfe_up_pts"),
        ("final_close_bucket", "next_mae_down_pts"),
        ("final_close_bucket", "next_gap_from_session_close_pts"),
        ("final_close_bucket", "next_overnight_return_pts"),
        ("final_close_bucket", "next_early_globex_2h_return_pts"),
        ("final_close_bucket", "next_or30_return_pts"),
        ("final_close_bucket", "next_rth_first_60m_return_pts"),
    ]
    rows = [
        _kruskal_test(study, feature, outcome)
        for feature, outcome in tests
        if feature in study.columns and outcome in study.columns
    ]
    return pd.DataFrame([row for row in rows if row is not None])


def _build_row(
    *,
    symbol: str,
    session: SessionSummary,
    final_bar: pd.Series,
    next_session: SessionSummary,
    next_bars: pd.DataFrame,
    direction_deadzone_pts: float,
    prior_break_buffer_pts: float,
) -> dict[str, object]:
    final_open = float(final_bar["open"])
    final_high = float(final_bar["high"])
    final_low = float(final_bar["low"])
    final_close = float(final_bar["close"])
    final_range = final_high - final_low
    final_body = final_close - final_open
    final_position = close_position(final_close, final_high, final_low)
    final_bias = close_bias(final_position)
    session_position = close_position(session.close, session.high, session.low)
    session_return = session.close - session.open
    next_position = close_position(next_session.close, next_session.high, next_session.low)
    next_return = next_session.close - next_session.open
    next_first_break = _first_prior_session_break(
        next_bars,
        prior_high=session.high,
        prior_low=session.low,
        buffer_pts=prior_break_buffer_pts,
    )
    next_first_sweep = _liquidity_sweep_label(next_first_break)
    next_took_high = bool(next_session.high > session.high + prior_break_buffer_pts)
    next_took_low = bool(next_session.low < session.low - prior_break_buffer_pts)
    next_gap = next_session.open - session.close
    next_windows = _next_session_windows(
        next_bars,
        next_session=next_session,
        direction_deadzone_pts=direction_deadzone_pts,
        prior_break_buffer_pts=prior_break_buffer_pts,
    )

    return {
        "symbol": symbol,
        "session": "globex_day",
        "session_date": session.label_date.isoformat(),
        "day_of_week_et": session.label_date.weekday(),
        "day_name_et": session.label_date.strftime("%A").lower(),
        "session_start_utc": session.period.start_utc,
        "session_end_utc": session.period.end_utc,
        "session_start_et": session.period.start_utc.astimezone(ET).isoformat(),
        "session_end_et": session.period.end_utc.astimezone(ET).isoformat(),
        "session_open": session.open,
        "session_high": session.high,
        "session_low": session.low,
        "session_close": session.close,
        "session_range_pts": session.range_pts,
        "session_return_pts": session_return,
        "session_direction": _direction(session_return, direction_deadzone_pts),
        "session_close_position": session_position,
        "session_close_bucket": close_bucket(session_position),
        "session_close_bias": close_bias(session_position),
        "session_bar_count": session.bar_count,
        "final_candle_start_utc": _to_utc_datetime(final_bar.name),
        "final_candle_start_et": _to_utc_datetime(final_bar.name).astimezone(ET).isoformat(),
        "final_open": final_open,
        "final_high": final_high,
        "final_low": final_low,
        "final_close": final_close,
        "final_range_pts": final_range,
        "final_body_pts": final_body,
        "final_body_direction": _direction(final_body, 0.0),
        "final_body_frac_of_range": _ratio(abs(final_body), final_range),
        "final_range_frac_of_session": _ratio(final_range, session.range_pts),
        "final_close_position": final_position,
        "final_close_bucket": close_bucket(final_position),
        "final_close_bias": final_bias,
        "next_session_date": next_session.label_date.isoformat(),
        "next_session_open": next_session.open,
        "next_session_high": next_session.high,
        "next_session_low": next_session.low,
        "next_session_close": next_session.close,
        "next_session_range_pts": next_session.range_pts,
        "next_gap_from_session_close_pts": next_gap,
        "next_gap_direction": _direction(next_gap, direction_deadzone_pts),
        "next_return_pts": next_return,
        "next_direction": _direction(next_return, direction_deadzone_pts),
        "next_close_position": next_position,
        "next_close_bucket": close_bucket(next_position),
        "next_close_bias": close_bias(next_position),
        "next_mfe_up_pts": next_session.high - next_session.open,
        "next_mae_down_pts": next_session.open - next_session.low,
        "next_up_down_excursion_ratio": _ratio(
            next_session.high - next_session.open,
            next_session.open - next_session.low,
        ),
        "next_took_prior_session_high": next_took_high,
        "next_took_prior_session_low": next_took_low,
        "next_break_type": _break_type(next_took_high, next_took_low),
        "next_first_break": next_first_break,
        "next_first_liquidity_sweep": next_first_sweep,
        "next_first_sweep_closed_back_inside_prior_range": (
            _sweep_closed_back_inside(
                next_first_sweep=next_first_sweep,
                next_close=next_session.close,
                prior_high=session.high,
                prior_low=session.low,
            )
        ),
        "next_closed_above_prior_session_high": bool(next_session.close > session.high),
        "next_closed_below_prior_session_low": bool(next_session.close < session.low),
        "next_range_vs_current_range": _ratio(next_session.range_pts, session.range_pts),
        **_continuation_fields(
            prefix="next_overnight",
            direction=next_windows["next_overnight_direction"],
            final_bias=final_bias,
        ),
        **_continuation_fields(
            prefix="next_early_globex_2h",
            direction=next_windows["next_early_globex_2h_direction"],
            final_bias=final_bias,
        ),
        **_continuation_fields(
            prefix="next_rth_first_60m",
            direction=next_windows["next_rth_first_60m_direction"],
            final_bias=final_bias,
        ),
        **next_windows,
    }


def _next_session_windows(
    next_bars: pd.DataFrame,
    *,
    next_session: SessionSummary,
    direction_deadzone_pts: float,
    prior_break_buffer_pts: float,
) -> dict[str, object]:
    rth_open = _et_datetime(next_session.label_date, RTH_OPEN_ET)
    or_end = rth_open + dt.timedelta(minutes=OPENING_RANGE_MINUTES)
    early_globex_end = next_session.period.start_utc + dt.timedelta(
        minutes=EARLY_GLOBEX_MINUTES
    )
    early_rth_end = rth_open + dt.timedelta(minutes=EARLY_RTH_MINUTES)

    overnight = _window_summary(next_bars, next_session.period.start_utc, rth_open)
    early_globex = _window_summary(
        next_bars,
        next_session.period.start_utc,
        min(early_globex_end, next_session.period.end_utc),
    )
    opening_range = _window_summary(next_bars, rth_open, or_end)
    early_rth = _window_summary(next_bars, rth_open, early_rth_end)

    or_first_break = "unavailable"
    if opening_range is not None:
        or_first_break = _first_range_break(
            next_bars,
            high=opening_range.high,
            low=opening_range.low,
            start_utc=or_end,
            end_utc=next_session.period.end_utc,
            high_label="opening_range_high_first",
            low_label="opening_range_low_first",
            buffer_pts=prior_break_buffer_pts,
        )

    return {
        "next_overnight_return_pts": _window_return(overnight),
        "next_overnight_direction": _window_direction(
            overnight,
            direction_deadzone_pts,
        ),
        "next_early_globex_2h_return_pts": _window_return(early_globex),
        "next_early_globex_2h_direction": _window_direction(
            early_globex,
            direction_deadzone_pts,
        ),
        "next_or30_open": _window_open(opening_range),
        "next_or30_high": _window_high(opening_range),
        "next_or30_low": _window_low(opening_range),
        "next_or30_close": _window_close(opening_range),
        "next_or30_range_pts": _window_range(opening_range),
        "next_or30_return_pts": _window_return(opening_range),
        "next_or30_direction": _window_direction(opening_range, direction_deadzone_pts),
        "next_or30_close_position": _window_close_position(opening_range),
        "next_or30_first_break": or_first_break,
        "next_rth_first_60m_return_pts": _window_return(early_rth),
        "next_rth_first_60m_direction": _window_direction(
            early_rth,
            direction_deadzone_pts,
        ),
    }


def _first_prior_session_break(
    next_bars: pd.DataFrame,
    *,
    prior_high: float,
    prior_low: float,
    buffer_pts: float,
) -> str:
    for _, bar in next_bars.iterrows():
        broke_high = float(bar["high"]) > prior_high + buffer_pts
        broke_low = float(bar["low"]) < prior_low - buffer_pts
        if broke_high and broke_low:
            return "both_same_bar"
        if broke_high:
            return "prior_high_first"
        if broke_low:
            return "prior_low_first"
    return "none"


def _first_range_break(
    bars: pd.DataFrame,
    *,
    high: float,
    low: float,
    start_utc: dt.datetime,
    end_utc: dt.datetime,
    high_label: str,
    low_label: str,
    buffer_pts: float,
) -> str:
    window = _slice_window(bars, start_utc, end_utc)
    for _, bar in window.iterrows():
        broke_high = float(bar["high"]) > high + buffer_pts
        broke_low = float(bar["low"]) < low - buffer_pts
        if broke_high and broke_low:
            return "both_same_bar"
        if broke_high:
            return high_label
        if broke_low:
            return low_label
    return "none"


def _liquidity_sweep_label(first_break: str) -> str:
    if first_break == "prior_high_first":
        return "prior_high_swept_first"
    if first_break == "prior_low_first":
        return "prior_low_swept_first"
    return first_break


def _sweep_closed_back_inside(
    *,
    next_first_sweep: str,
    next_close: float,
    prior_high: float,
    prior_low: float,
) -> bool | None:
    if next_first_sweep == "prior_high_swept_first":
        return bool(next_close < prior_high)
    if next_first_sweep == "prior_low_swept_first":
        return bool(next_close > prior_low)
    return None


def _window_summary(
    bars: pd.DataFrame,
    start_utc: dt.datetime,
    end_utc: dt.datetime,
) -> WindowSummary | None:
    window = _slice_window(bars, start_utc, end_utc)
    if window.empty:
        return None
    return WindowSummary(
        open=float(window["open"].iloc[0]),
        high=float(window["high"].max()),
        low=float(window["low"].min()),
        close=float(window["close"].iloc[-1]),
        bar_count=int(len(window)),
    )


def _slice_window(
    bars: pd.DataFrame,
    start_utc: dt.datetime,
    end_utc: dt.datetime,
) -> pd.DataFrame:
    return bars.loc[
        (bars.index >= pd.Timestamp(start_utc))
        & (bars.index < pd.Timestamp(end_utc))
    ]


def _window_open(window: WindowSummary | None) -> float | None:
    return None if window is None else window.open


def _window_high(window: WindowSummary | None) -> float | None:
    return None if window is None else window.high


def _window_low(window: WindowSummary | None) -> float | None:
    return None if window is None else window.low


def _window_close(window: WindowSummary | None) -> float | None:
    return None if window is None else window.close


def _window_range(window: WindowSummary | None) -> float | None:
    return None if window is None else window.range_pts


def _window_return(window: WindowSummary | None) -> float | None:
    return None if window is None else window.return_pts


def _window_direction(window: WindowSummary | None, deadzone_pts: float) -> str:
    if window is None:
        return "unavailable"
    return _direction(window.return_pts, deadzone_pts)


def _window_close_position(window: WindowSummary | None) -> float | None:
    if window is None:
        return None
    return close_position(window.close, window.high, window.low)


def _continuation_fields(
    *,
    prefix: str,
    direction: object,
    final_bias: CloseBias,
) -> dict[str, bool | None]:
    value: bool | None
    if final_bias == "bullish":
        value = direction == "bullish"
    elif final_bias == "bearish":
        value = direction == "bearish"
    else:
        value = None
    return {f"{prefix}_continues_final_bias": value}


def _add_prior_context_columns(study: pd.DataFrame) -> pd.DataFrame:
    if study.empty:
        return study
    out = study.sort_values("session_start_utc").reset_index(drop=True).copy()
    ranges = pd.to_numeric(out["session_range_pts"], errors="coerce")

    out["prior_session_direction"] = out["session_direction"].shift(1).fillna("unknown")
    out["prior_session_range_pts"] = ranges.shift(1)
    out["prior_session_return_pts"] = pd.to_numeric(
        out["session_return_pts"], errors="coerce"
    ).shift(1)
    out["prior_session_close_position"] = pd.to_numeric(
        out["session_close_position"], errors="coerce"
    ).shift(1)
    out["prior20_median_session_range_pts"] = (
        ranges.shift(1)
        .rolling(ROLLING_RANGE_LOOKBACK, min_periods=ROLLING_RANGE_MIN_PERIODS)
        .median()
    )
    out["prior20_session_range_percentile"] = _rolling_percentile(
        ranges,
        lookback=ROLLING_RANGE_LOOKBACK,
        min_periods=ROLLING_RANGE_MIN_PERIODS,
    )
    out["prior20_range_regime"] = out["prior20_session_range_percentile"].map(
        _range_regime
    )
    return out


def _rolling_percentile(
    values: pd.Series,
    *,
    lookback: int,
    min_periods: int,
) -> list[float | None]:
    out: list[float | None] = []
    for i, value in enumerate(values):
        prior = values.iloc[max(0, i - lookback) : i].dropna()
        if pd.isna(value) or len(prior) < min_periods:
            out.append(None)
            continue
        below = (prior < value).sum()
        equal = (prior == value).sum()
        out.append(float((below + 0.5 * equal) / len(prior)))
    return out


def _range_regime(percentile: float | None) -> str:
    if percentile is None or pd.isna(percentile):
        return "unknown"
    if percentile <= 0.33:
        return "low_range"
    if percentile >= 0.67:
        return "high_range"
    return "normal_range"


def _direction(value: float, deadzone_pts: float) -> str:
    if value > deadzone_pts:
        return "bullish"
    if value < -deadzone_pts:
        return "bearish"
    return "flat"


def _break_type(took_high: bool, took_low: bool) -> str:
    if took_high and took_low:
        return "both"
    if took_high:
        return "high_only"
    if took_low:
        return "low_only"
    return "none"


def _chi_square_test(
    study: pd.DataFrame,
    feature_col: str,
    outcome_col: str,
) -> dict[str, object] | None:
    table = pd.crosstab(study[feature_col], study[outcome_col])
    if table.shape[0] < 2 or table.shape[1] < 2:
        return None
    chi2, p_value, dof, expected = stats.chi2_contingency(table)
    n = float(table.to_numpy().sum())
    min_dim = min(table.shape[0] - 1, table.shape[1] - 1)
    cramers_v = math.sqrt(chi2 / (n * min_dim)) if n > 0 and min_dim > 0 else None
    return {
        "test": "chi_square",
        "feature": feature_col,
        "outcome": outcome_col,
        "rows": int(n),
        "statistic": float(chi2),
        "p_value": float(p_value),
        "degrees_of_freedom": int(dof),
        "effect_size": float(cramers_v) if cramers_v is not None else None,
        "min_expected_cell_count": float(expected.min()),
    }


def _kruskal_test(
    study: pd.DataFrame,
    feature_col: str,
    outcome_col: str,
) -> dict[str, object] | None:
    groups = []
    for _, group in study.groupby(feature_col, dropna=True):
        values = pd.to_numeric(group[outcome_col], errors="coerce").dropna()
        if len(values) >= 2:
            groups.append(values)
    if len(groups) < 2:
        return None
    statistic, p_value = stats.kruskal(*groups)
    return {
        "test": "kruskal_wallis",
        "feature": feature_col,
        "outcome": outcome_col,
        "groups": int(len(groups)),
        "rows": int(sum(len(g) for g in groups)),
        "statistic": float(statistic),
        "p_value": float(p_value),
        "effect_size": None,
    }


def _normalize_bars(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        raise ValueError("bars frame is None")
    out = df.copy(deep=False)
    if isinstance(out.index, pd.DatetimeIndex):
        idx = pd.to_datetime(out.index, utc=True)
    elif "ts_event" in out.columns:
        idx = pd.to_datetime(out["ts_event"], utc=True)
        out = out.set_index(pd.DatetimeIndex(idx))
    else:
        raise ValueError("bars frame needs a DatetimeIndex or ts_event column")
    out.index = pd.DatetimeIndex(idx)
    out = out.loc[~out.index.isna()].sort_index()
    required = {"open", "high", "low", "close"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"bars missing required columns: {sorted(missing)}")
    for col in required:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def _et_datetime(label_date: dt.date, boundary_time: dt.time) -> dt.datetime:
    return dt.datetime.combine(label_date, boundary_time, tzinfo=ET).astimezone(UTC)


def _sort_category(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if column == "final_close_bucket":
        order = _CLOSE_BUCKET_ORDER
    elif column == "final_close_bias":
        order = _CLOSE_BIAS_ORDER
    else:
        return df
    rank = {value: i for i, value in enumerate(order)}
    out = df.copy()
    out["_rank"] = out[column].map(rank).fillna(len(rank))
    return out.sort_values("_rank").drop(columns=["_rank"]).reset_index(drop=True)


def _period_label_date(period: GlobexPeriod) -> dt.date:
    return period.end_utc.astimezone(ET).date()


def _to_utc_datetime(value) -> dt.datetime:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.to_pydatetime()


def _mean(series: pd.Series) -> float | None:
    value = pd.to_numeric(series, errors="coerce").mean()
    return None if pd.isna(value) else float(value)


def _median(series: pd.Series) -> float | None:
    value = pd.to_numeric(series, errors="coerce").median()
    return None if pd.isna(value) else float(value)


def _rate(series: pd.Series) -> float | None:
    values = pd.Series(series).dropna()
    if len(values) == 0:
        return None
    value = values.astype(float).mean()
    return None if pd.isna(value) else float(value)


def _ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0 or not math.isfinite(denominator):
        return None
    return float(numerator / denominator)


def _col(df: pd.DataFrame, column: str) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series([None] * len(df), index=df.index)
