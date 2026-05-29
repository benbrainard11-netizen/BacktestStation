from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research.final_15m_session_close import globex_day_periods
from app.research.nq_session_sweep_reaction_v1 import SweepReactionConfig
from app.research.nq_session_sweep_reaction_v1_1 import run_backtest

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


def _short_reaction_rows(
    *,
    overnight_ts: dt.datetime | None = None,
    overnight_price: float = 100.25,
    overnight_bid: float = 100.00,
    overnight_ask: float = 100.25,
    rth_price: float = 100.25,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if overnight_ts is not None:
        rows.append(
            _event(
                overnight_ts,
                action="T",
                price=overnight_price,
                bid=overnight_bid,
                ask=overnight_ask,
                bid_sz=10,
                ask_sz=30,
                sequence=1,
            )
        )
    rows.extend(
        [
            _event(
                dt.datetime(2026, 5, 6, 13, 36, 5, tzinfo=UTC),
                action="T",
                price=rth_price,
                bid=100.00,
                ask=100.25,
                bid_sz=10,
                ask_sz=30,
                sequence=2,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 36, 20, tzinfo=UTC),
                price=100.00,
                bid=99.75,
                ask=100.00,
                bid_sz=10,
                ask_sz=30,
                sequence=3,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 36, 35, tzinfo=UTC),
                price=99.75,
                bid=99.50,
                ask=99.75,
                bid_sz=8,
                ask_sz=32,
                sequence=4,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 37, 1, tzinfo=UTC),
                price=99.50,
                bid=99.50,
                ask=99.75,
                bid_sz=8,
                ask_sz=32,
                sequence=5,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 45, tzinfo=UTC),
                action="T",
                price=97.50,
                bid=97.50,
                ask=97.75,
                bid_sz=8,
                ask_sz=20,
                sequence=6,
            ),
        ]
    )
    return rows


def _bullish_anchor_bars() -> pd.DataFrame:
    return _bar_frame(
        [
            *_anchor_bars(label_date=dt.date(2026, 5, 5), close=98.0),
            _reclaim_bar(start=dt.datetime(2026, 5, 6, 13, 36, tzinfo=UTC), close=99.75),
        ]
    )


def _run(rows: list[dict[str, object]]) -> dict[str, pd.DataFrame | dict[str, object]]:
    label = dt.date(2026, 5, 5)
    return run_backtest(
        bars=_bullish_anchor_bars(),
        mbp1=_mbp(rows),
        start=label,
        end=label + dt.timedelta(days=1),
        config=_config(),
    )


def test_overnight_armed_sweep_is_context_and_rth_sweep_can_trade() -> None:
    result = _run(
        _short_reaction_rows(
            overnight_ts=dt.datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
        )
    )

    trades = result["trades"]
    sessions = result["sessions"]

    assert len(trades) == 1
    assert trades.iloc[0]["side"] == "short"
    assert trades.iloc[0]["overnight_sweep_direction"] == "high"
    assert trades.iloc[0]["rth_first_sweep_direction"] == "high"
    assert trades.iloc[0]["overnight_rth_sweep_relationship"] == "aligned"
    assert sessions.iloc[0]["status"] == "traded"
    assert sessions.iloc[0]["overnight_sweep_vs_armed"] == "aligned"
    assert sessions.iloc[0]["rth_first_sweep_vs_armed"] == "aligned"


def test_overnight_opposite_sweep_is_context_not_invalidation() -> None:
    result = _run(
        _short_reaction_rows(
            overnight_ts=dt.datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
            overnight_price=89.75,
            overnight_bid=89.75,
            overnight_ask=90.00,
        )
    )

    trades = result["trades"]
    sessions = result["sessions"]

    assert len(trades) == 1
    assert trades.iloc[0]["overnight_sweep_direction"] == "low"
    assert trades.iloc[0]["rth_first_sweep_direction"] == "high"
    assert trades.iloc[0]["overnight_rth_sweep_relationship"] == "conflicted"
    assert sessions.iloc[0]["overnight_sweep_vs_armed"] == "opposite"


def test_rth_opposite_side_first_still_skips_session() -> None:
    result = _run(
        [
            _event(
                dt.datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
                action="T",
                price=100.25,
                bid=100.00,
                ask=100.25,
                bid_sz=10,
                ask_sz=30,
                sequence=1,
            ),
            _event(
                dt.datetime(2026, 5, 6, 13, 36, 5, tzinfo=UTC),
                action="T",
                price=89.75,
                bid=89.75,
                ask=90.00,
                bid_sz=30,
                ask_sz=10,
                sequence=2,
            ),
        ]
    )

    sessions = result["sessions"]

    assert len(result["trades"]) == 0
    assert sessions.iloc[0]["skip_reason"] == "opposite_side_first"
    assert sessions.iloc[0]["overnight_sweep_direction"] == "high"
    assert sessions.iloc[0]["rth_first_sweep_direction"] == "low"
    assert sessions.iloc[0]["overnight_rth_sweep_relationship"] == "conflicted"


def test_overnight_sweep_without_rth_sweep_is_context_only_skip() -> None:
    result = _run(
        [
            _event(
                dt.datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
                action="T",
                price=100.25,
                bid=100.00,
                ask=100.25,
                bid_sz=10,
                ask_sz=30,
                sequence=1,
            )
        ]
    )

    sessions = result["sessions"]

    assert len(result["trades"]) == 0
    assert sessions.iloc[0]["skip_reason"] == "no_actionable_sweep_before_cutoff"
    assert sessions.iloc[0]["overnight_sweep_direction"] == "high"
    assert pd.isna(sessions.iloc[0]["rth_first_sweep_direction"])
    assert sessions.iloc[0]["overnight_rth_sweep_relationship"] == "overnight_only"
