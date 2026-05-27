from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from app.research.final_15m_session_close import globex_day_periods
from app.research.nq_session_sweep_reaction_v1 import (
    SweepReactionConfig,
    run_backtest,
)

UTC = dt.UTC
NQ = "NQ.c.0"


def _config(**kwargs) -> SweepReactionConfig:
    return SweepReactionConfig(
        commission_per_contract=0.0,
        slippage_ticks=0,
        prior_range_min_sessions=0,
        min_stop_pts=0.0,
        max_stop_pts=10.0,
        **kwargs,
    )


def _bar_frame(rows: list[tuple[dt.datetime, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c} for _, o, h, low, c in rows],
        index=pd.DatetimeIndex([row[0] for row in rows], tz=UTC),
    )


def _anchor_bars(
    *,
    label_date: dt.date,
    close: float,
    high: float = 100.0,
    low: float = 90.0,
) -> list[tuple[dt.datetime, float, float, float, float]]:
    period = globex_day_periods(start=label_date, end=label_date + dt.timedelta(days=1))[0]
    return [
        (period.start_utc, 95.0, high, low, 95.0),
        (period.end_utc - dt.timedelta(minutes=1), 95.0, high, low, close),
    ]


def _reclaim_bar(
    *,
    start: dt.datetime,
    close: float,
) -> tuple[dt.datetime, float, float, float, float]:
    return (start, close, close + 0.5, close - 0.5, close)


def _mbp(rows: list[dict[str, object]]) -> pd.DataFrame:
    out = pd.DataFrame(rows)
    out["symbol"] = NQ
    out["side"] = out.get("side", "")
    out["size"] = out.get("size", 1)
    return out


def _event(
    ts: dt.datetime,
    *,
    action: str = "M",
    price: float,
    bid: float,
    ask: float,
    bid_sz: int,
    ask_sz: int,
    sequence: int,
) -> dict[str, object]:
    return {
        "ts_event": ts,
        "action": action,
        "price": price,
        "bid_px": bid,
        "ask_px": ask,
        "bid_sz": bid_sz,
        "ask_sz": ask_sz,
        "sequence": sequence,
    }


def test_high_sweep_rejection_short_hits_target_with_mbp_confirmation() -> None:
    label = dt.date(2026, 5, 5)
    bars = _bar_frame(
        [
            *_anchor_bars(label_date=label, close=98.0),
            _reclaim_bar(start=dt.datetime(2026, 5, 6, 13, 36, tzinfo=UTC), close=99.75),
        ]
    )
    mbp1 = _mbp(
        [
            _event(
                dt.datetime(2026, 5, 6, 13, 36, 5, tzinfo=UTC),
                action="T",
                price=100.25,
                bid=100.00,
                ask=100.25,
                bid_sz=10,
                ask_sz=30,
                sequence=1,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 36, 20, tzinfo=UTC),
                price=100.00,
                bid=99.75,
                ask=100.00,
                bid_sz=10,
                ask_sz=30,
                sequence=2,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 36, 35, tzinfo=UTC),
                price=99.75,
                bid=99.50,
                ask=99.75,
                bid_sz=8,
                ask_sz=32,
                sequence=3,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 37, 1, tzinfo=UTC),
                price=99.50,
                bid=99.50,
                ask=99.75,
                bid_sz=8,
                ask_sz=32,
                sequence=4,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 45, tzinfo=UTC),
                action="T",
                price=97.50,
                bid=97.50,
                ask=97.75,
                bid_sz=8,
                ask_sz=20,
                sequence=5,
            ),
        ]
    )

    result = run_backtest(
        bars=bars,
        mbp1=mbp1,
        start=label,
        end=label + dt.timedelta(days=1),
        config=_config(),
    )
    trades = result["trades"]

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["side"] == "short"
    assert trade["exit_reason"] == "target"
    assert trade["entry_ts"] > trade["confirmation_end"]
    assert trade["entry_ts"] > trade["reclaim_bar_end"]
    assert trade["post_sweep_30s_mean_imbalance"] <= -0.20
    assert trade["r_multiple"] == pytest.approx(1.5)


def test_low_sweep_rejection_long_can_stop_out() -> None:
    label = dt.date(2026, 5, 5)
    bars = _bar_frame(
        [
            *_anchor_bars(label_date=label, close=92.0),
            _reclaim_bar(start=dt.datetime(2026, 5, 6, 13, 36, tzinfo=UTC), close=90.25),
        ]
    )
    mbp1 = _mbp(
        [
            _event(
                dt.datetime(2026, 5, 6, 13, 36, 5, tzinfo=UTC),
                action="T",
                price=89.75,
                bid=89.75,
                ask=90.00,
                bid_sz=30,
                ask_sz=10,
                sequence=1,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 36, 35, tzinfo=UTC),
                price=90.25,
                bid=90.25,
                ask=90.50,
                bid_sz=35,
                ask_sz=10,
                sequence=2,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 37, 1, tzinfo=UTC),
                price=90.50,
                bid=90.25,
                ask=90.50,
                bid_sz=30,
                ask_sz=10,
                sequence=3,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 45, tzinfo=UTC),
                action="T",
                price=89.25,
                bid=89.00,
                ask=89.25,
                bid_sz=10,
                ask_sz=30,
                sequence=4,
            ),
        ]
    )

    result = run_backtest(
        bars=bars,
        mbp1=mbp1,
        start=label,
        end=label + dt.timedelta(days=1),
        config=_config(),
    )
    trade = result["trades"].iloc[0]

    assert trade["side"] == "long"
    assert trade["exit_reason"] == "stop"
    assert trade["post_sweep_30s_mean_imbalance"] >= 0.20
    assert trade["r_multiple"] < 0


def test_opposite_side_first_skips_session() -> None:
    label = dt.date(2026, 5, 5)
    bars = _bar_frame(
        [
            *_anchor_bars(label_date=label, close=98.0),
            _reclaim_bar(start=dt.datetime(2026, 5, 6, 13, 36, tzinfo=UTC), close=99.75),
        ]
    )
    mbp1 = _mbp(
        [
            _event(
                dt.datetime(2026, 5, 6, 13, 36, 5, tzinfo=UTC),
                action="T",
                price=89.75,
                bid=89.75,
                ask=90.00,
                bid_sz=30,
                ask_sz=10,
                sequence=1,
            )
        ]
    )

    result = run_backtest(
        bars=bars,
        mbp1=mbp1,
        start=label,
        end=label + dt.timedelta(days=1),
        config=_config(),
    )

    assert len(result["trades"]) == 0
    assert result["sessions"].iloc[0]["skip_reason"] == "opposite_side_first"


def test_mbp_confirmation_failure_skips_without_entry() -> None:
    label = dt.date(2026, 5, 5)
    bars = _bar_frame(
        [
            *_anchor_bars(label_date=label, close=98.0),
            _reclaim_bar(start=dt.datetime(2026, 5, 6, 13, 36, tzinfo=UTC), close=99.75),
        ]
    )
    mbp1 = _mbp(
        [
            _event(
                dt.datetime(2026, 5, 6, 13, 36, 5, tzinfo=UTC),
                action="T",
                price=100.25,
                bid=100.00,
                ask=100.25,
                bid_sz=30,
                ask_sz=10,
                sequence=1,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 36, 35, tzinfo=UTC),
                price=100.00,
                bid=99.75,
                ask=100.00,
                bid_sz=30,
                ask_sz=10,
                sequence=2,
            ),
        ]
    )

    result = run_backtest(
        bars=bars,
        mbp1=mbp1,
        start=label,
        end=label + dt.timedelta(days=1),
        config=_config(),
    )

    assert len(result["trades"]) == 0
    assert result["sessions"].iloc[0]["skip_reason"] == "mbp_confirmation_failed"
