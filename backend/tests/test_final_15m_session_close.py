from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from app.research.final_15m_session_close import (
    build_final_15m_session_close_study,
    close_bias,
    close_bucket,
    close_position,
    final_15m_candle,
    globex_day_periods,
    next_globex_day,
    summarize_study,
)

UTC = dt.UTC
NQ = "NQ.c.0"


def _session_bars(
    *,
    start_utc: dt.datetime,
    base: float,
    final: tuple[float, float, float, float] | None = None,
    first_bar: tuple[float, float, float, float] | None = None,
) -> list[tuple[dt.datetime, float, float, float, float]]:
    rows = []
    cur = start_utc
    for i in range(92):  # 23 hours of 15m bars
        open_v = base + i * 0.1
        high = open_v + 1.0
        low = open_v - 1.0
        close = open_v + 0.25
        if i == 0 and first_bar is not None:
            open_v, high, low, close = first_bar
        if i == 91 and final is not None:
            open_v, high, low, close = final
        rows.append((cur, open_v, high, low, close))
        cur += dt.timedelta(minutes=15)
    return rows


def _bars(rows: list[tuple[dt.datetime, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c} for _, o, h, low, c in rows],
        index=pd.DatetimeIndex([row[0] for row in rows], tz=UTC),
    )


def test_close_position_and_categories() -> None:
    assert close_position(109.0, high=110.0, low=100.0) == pytest.approx(0.9)
    assert close_bucket(0.1) == "strong_bearish"
    assert close_bucket(0.35) == "bearish"
    assert close_bucket(0.5) == "middle"
    assert close_bucket(0.7) == "bullish"
    assert close_bucket(0.9) == "strong_bullish"
    assert close_bias(0.35) == "bearish"
    assert close_bias(0.5) == "neutral"
    assert close_bias(0.7) == "bullish"
    assert close_position(100.0, high=100.0, low=100.0) is None
    assert close_bucket(None) == "undefined"


def test_globex_periods_and_final_candle_are_objective() -> None:
    periods = globex_day_periods(
        start=dt.date(2026, 5, 5),
        end=dt.date(2026, 5, 6),
    )
    assert len(periods) == 1
    period = periods[0]
    assert period.start_utc == dt.datetime(2026, 5, 4, 22, 0, tzinfo=UTC)
    assert period.end_utc == dt.datetime(2026, 5, 5, 21, 0, tzinfo=UTC)

    bars = _bars(
        _session_bars(
            start_utc=period.start_utc,
            base=100.0,
            final=(108.0, 110.0, 100.0, 109.0),
        )
    )

    final = final_15m_candle(bars, period)

    assert final is not None
    assert final.name.to_pydatetime() == dt.datetime(2026, 5, 5, 20, 45, tzinfo=UTC)
    assert float(final["close"]) == pytest.approx(109.0)


def test_build_study_labels_next_session_without_using_same_day_future() -> None:
    period = globex_day_periods(
        start=dt.date(2026, 5, 5),
        end=dt.date(2026, 5, 6),
    )[0]
    next_period = next_globex_day(period)
    rows = []
    rows.extend(
        _session_bars(
            start_utc=period.start_utc,
            base=100.0,
            final=(108.0, 110.0, 100.0, 109.0),
        )
    )
    rows.extend(
        _session_bars(
            start_utc=next_period.start_utc,
            base=105.0,
            first_bar=(105.0, 112.0, 104.0, 111.0),  # takes prior high first
            final=(116.0, 118.0, 115.0, 117.0),
        )
    )
    study = build_final_15m_session_close_study(
        _bars(rows),
        symbol=NQ,
        start=dt.date(2026, 5, 5),
        end=dt.date(2026, 5, 6),
    )

    assert len(study) == 1
    row = study.iloc[0]
    assert row["final_close_position"] == pytest.approx(0.9)
    assert row["final_close_bucket"] == "strong_bullish"
    assert row["final_close_bias"] == "bullish"
    assert row["next_direction"] == "bullish"
    assert bool(row["next_took_prior_session_high"]) is True
    assert row["next_first_break"] == "prior_high_first"
    assert row["next_first_liquidity_sweep"] == "prior_high_swept_first"
    assert row["next_overnight_direction"] == "bullish"
    assert bool(row["next_overnight_continues_final_bias"]) is True
    assert row["next_or30_first_break"] == "opening_range_high_first"
    assert row["next_rth_first_60m_direction"] == "bullish"
    assert row["next_return_pts"] > 0


def test_prior_context_columns_use_only_completed_prior_sessions() -> None:
    periods = globex_day_periods(
        start=dt.date(2026, 5, 5),
        end=dt.date(2026, 5, 8),
    )
    rows = []
    for i, period in enumerate(periods):
        rows.extend(
            _session_bars(
                start_utc=period.start_utc,
                base=100.0 + i * 10.0,
                final=(
                    108.0 + i * 10.0,
                    110.0 + i * 10.0,
                    100.0 + i * 10.0,
                    109.0 + i * 10.0,
                ),
            )
        )

    study = build_final_15m_session_close_study(
        _bars(rows),
        symbol=NQ,
        start=dt.date(2026, 5, 5),
        end=dt.date(2026, 5, 7),
    )

    assert len(study) == 2
    assert study.iloc[0]["prior_session_direction"] == "unknown"
    assert study.iloc[1]["prior_session_direction"] == study.iloc[0]["session_direction"]
    assert pd.isna(study.iloc[0]["prior_session_range_pts"])
    assert study.iloc[1]["prior_session_range_pts"] == pytest.approx(
        study.iloc[0]["session_range_pts"]
    )


def test_summary_tables_include_distribution_and_stats() -> None:
    study = pd.DataFrame(
        [
            {
                "symbol": NQ,
                "session_date": "2026-05-05",
                "final_close_bucket": "strong_bullish",
                "final_close_bias": "bullish",
                "next_direction": "bullish",
                "next_return_pts": 10.0,
                "next_close_position": 0.9,
                "next_close_bucket": "strong_bullish",
                "next_took_prior_session_high": True,
                "next_took_prior_session_low": False,
                "next_first_break": "prior_high_first",
                "next_mfe_up_pts": 12.0,
                "next_mae_down_pts": 2.0,
            },
            {
                "symbol": NQ,
                "session_date": "2026-05-06",
                "final_close_bucket": "strong_bearish",
                "final_close_bias": "bearish",
                "next_direction": "bearish",
                "next_return_pts": -8.0,
                "next_close_position": 0.1,
                "next_close_bucket": "strong_bearish",
                "next_took_prior_session_high": False,
                "next_took_prior_session_low": True,
                "next_first_break": "prior_low_first",
                "next_mfe_up_pts": 1.0,
                "next_mae_down_pts": 9.0,
            },
        ]
    )

    summary = summarize_study(study)
    stats = summary["bucket_stats"]

    assert summary["overview"]["rows"] == 2
    assert len(summary["close_bucket_distribution"]) == 2
    assert len(stats) == 2
    assert len(summary["targeted_effect_stats"]) == 2
    assert stats.loc[
        stats["final_close_bucket"] == "strong_bullish",
        "next_bullish_rate",
    ].iloc[0] == pytest.approx(1.0)
