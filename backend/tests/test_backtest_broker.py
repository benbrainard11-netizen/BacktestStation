"""Tests for the Broker — entry fills, bracket resolution, ambiguous bars."""

from __future__ import annotations

import datetime as dt

from app.backtest.broker import Broker, BrokerConfig
from app.backtest.orders import BracketOrder, CancelOrder, MarketEntry, Side
from app.backtest.strategy import Bar


def _bar(
    ts: dt.datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
) -> Bar:
    return Bar(
        ts_event=ts,
        symbol="NQ.c.0",
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=100,
        trade_count=10,
        vwap=(open_ + high + low + close) / 4,
    )


def _broker() -> Broker:
    return Broker(
        BrokerConfig(
            tick_size=0.25,
            contract_value=20.0,
            commission_per_contract=2.0,
            slippage_ticks=1,
        )
    )


def test_market_entry_fills_at_next_bar_open_with_slippage_long() -> None:
    broker = _broker()
    ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    broker.submit(MarketEntry(side=Side.LONG, qty=1), ts, bar_index=0)

    next_bar = _bar(ts + dt.timedelta(minutes=1), 21000.0, 21010.0, 20995.0, 21005.0)
    fills = broker.resolve_pending_entries(next_bar)

    assert len(fills) == 1
    f = fills[0]
    # Long fills at open + slippage (1 tick = 0.25 above)
    assert f.price == 21000.25
    assert f.side is Side.LONG
    assert f.qty == 1
    assert f.is_entry is True
    assert f.fill_confidence == "exact"
    assert f.commission == 2.0
    assert broker.pending_entries == []


def test_market_entry_short_slippage_below_open() -> None:
    broker = _broker()
    ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    broker.submit(MarketEntry(side=Side.SHORT, qty=2), ts, bar_index=0)

    next_bar = _bar(ts + dt.timedelta(minutes=1), 21000.0, 21010.0, 20995.0, 21005.0)
    fills = broker.resolve_pending_entries(next_bar)

    assert fills[0].price == 20999.75  # below open by 1 tick
    assert fills[0].qty == 2
    assert fills[0].commission == 4.0


def test_bracket_entry_then_target_fill() -> None:
    broker = _broker()
    ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    broker.submit(
        BracketOrder(side=Side.LONG, qty=1, stop_price=20990.0, target_price=21030.0),
        ts,
        bar_index=0,
    )

    # Bar 1: entry fills at open + slippage = 21000.25
    bar_1 = _bar(ts + dt.timedelta(minutes=1), 21000.0, 21010.0, 20998.0, 21005.0)
    entry_fills = broker.resolve_pending_entries(bar_1)
    assert len(entry_fills) == 1
    assert len(broker.active_brackets) == 1

    # Bar 2: high reaches 21031 — target hit at 21030
    bar_2 = _bar(ts + dt.timedelta(minutes=2), 21010.0, 21031.0, 21008.0, 21025.0)
    exit_fills = broker.resolve_active_brackets(bar_2)
    assert len(exit_fills) == 1
    assert exit_fills[0].price == 21030.0
    assert exit_fills[0].reason == "target"
    assert exit_fills[0].fill_confidence == "exact"
    assert exit_fills[0].is_entry is False
    assert broker.active_brackets == []


def test_bracket_stop_hit_long() -> None:
    broker = _broker()
    ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    broker.submit(
        BracketOrder(side=Side.LONG, qty=1, stop_price=20990.0, target_price=21030.0),
        ts,
        0,
    )
    bar_1 = _bar(ts + dt.timedelta(minutes=1), 21000.0, 21010.0, 20998.0, 21005.0)
    broker.resolve_pending_entries(bar_1)

    # Bar 2: low reaches 20985 — stop hit at 20990
    bar_2 = _bar(ts + dt.timedelta(minutes=2), 21000.0, 21005.0, 20985.0, 20992.0)
    fills = broker.resolve_active_brackets(bar_2)
    assert len(fills) == 1
    assert fills[0].price == 20990.0
    assert fills[0].reason == "stop"


def test_bracket_ambiguous_bar_stop_wins_per_claude_md() -> None:
    """CLAUDE.md §8: bar contains both stop and target -> stop wins, conservative."""
    broker = _broker()
    ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    broker.submit(
        BracketOrder(side=Side.LONG, qty=1, stop_price=20990.0, target_price=21030.0),
        ts,
        0,
    )
    bar_1 = _bar(ts + dt.timedelta(minutes=1), 21000.0, 21010.0, 20998.0, 21005.0)
    broker.resolve_pending_entries(bar_1)

    # Bar 2: range covers BOTH stop and target — ambiguous
    bar_2 = _bar(ts + dt.timedelta(minutes=2), 21005.0, 21035.0, 20985.0, 21010.0)
    fills = broker.resolve_active_brackets(bar_2)
    assert len(fills) == 1
    assert fills[0].price == 20990.0  # stop wins
    assert fills[0].reason == "stop"
    assert fills[0].fill_confidence == "conservative"


def test_bracket_neither_hit_stays_active() -> None:
    broker = _broker()
    ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    broker.submit(
        BracketOrder(side=Side.LONG, qty=1, stop_price=20990.0, target_price=21030.0),
        ts,
        0,
    )
    bar_1 = _bar(ts + dt.timedelta(minutes=1), 21000.0, 21010.0, 20998.0, 21005.0)
    broker.resolve_pending_entries(bar_1)

    bar_2 = _bar(ts + dt.timedelta(minutes=2), 21005.0, 21015.0, 21000.0, 21010.0)
    fills = broker.resolve_active_brackets(bar_2)
    assert fills == []
    assert len(broker.active_brackets) == 1


def test_force_close_at_uses_close_price() -> None:
    broker = _broker()
    ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    broker.submit(
        BracketOrder(side=Side.LONG, qty=1, stop_price=20990.0, target_price=21030.0),
        ts,
        0,
    )
    bar_1 = _bar(ts + dt.timedelta(minutes=1), 21000.0, 21010.0, 20998.0, 21005.0)
    broker.resolve_pending_entries(bar_1)

    last_bar = _bar(ts + dt.timedelta(minutes=10), 21010.0, 21015.0, 21008.0, 21012.0)
    fills = broker.force_close_at(last_bar, reason="eod_flatten")
    assert len(fills) == 1
    assert fills[0].price == 21012.0  # close
    assert fills[0].reason == "eod_flatten"
    assert broker.active_brackets == []


def test_cancel_pending_entry() -> None:
    broker = _broker()
    ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    order = broker.submit(MarketEntry(side=Side.LONG, qty=1), ts, 0)
    assert order is not None

    broker.submit(CancelOrder(order_id=order.id), ts, 0)
    assert order.state == "cancelled"
    assert broker.pending_entries == []
