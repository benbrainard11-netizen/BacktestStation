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


# --- BracketOrder.fill_immediately ---


def test_immediate_bracket_fills_at_this_bar_open() -> None:
    """A bracket with fill_immediately=True fills at the same bar's open
    (not next bar's). Mirrors trusted Fractal AMD's "decide on T+1's
    open" pattern."""
    broker = _broker()
    ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    bar = _bar(ts, open_=21000.0, high=21010.0, low=20995.0, close=21005.0)
    order = broker.submit(
        BracketOrder(
            side=Side.LONG,
            qty=1,
            stop_price=20990.0,
            target_price=21030.0,
            fill_immediately=True,
        ),
        ts,
        bar_index=5,
    )
    assert order is not None
    assert order.state == "pending"

    fills = broker.fill_immediate_brackets(bar, bar_index=5)
    assert len(fills) == 1
    fill = fills[0]
    # 1 tick slippage above open for a LONG.
    assert fill.price == 21000.0 + 0.25
    assert fill.is_entry is True
    assert fill.reason == "market"
    assert order.state == "active"
    assert order.entry_bar_index == 5
    assert broker.pending_entries == []
    assert order in broker.active_brackets


def test_immediate_bracket_skips_same_bar_range_check() -> None:
    """An immediate-fill bracket is in active_brackets after filling on
    bar N, but resolve_active_brackets on bar N must NOT check stop /
    target against bar N's high/low — that would be same-bar look-ahead.
    The next bar IS checked normally.
    """
    broker = _broker()
    ts1 = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    bar1 = _bar(ts1, open_=21000.0, high=21050.0, low=20985.0, close=21030.0)
    broker.submit(
        BracketOrder(
            side=Side.LONG,
            qty=1,
            stop_price=20990.0,  # in bar1's range
            target_price=21030.0,  # in bar1's range
            fill_immediately=True,
        ),
        ts1,
        bar_index=5,
    )
    broker.fill_immediate_brackets(bar1, bar_index=5)
    # Same bar — must NOT exit even though both stop and target are in range.
    same_bar_fills = broker.resolve_active_brackets(bar1, bar_index=5)
    assert same_bar_fills == []
    assert broker.active_brackets, "bracket should still be active"

    # Next bar — normal resolution.
    ts2 = ts1 + dt.timedelta(minutes=1)
    bar2 = _bar(ts2, open_=21015.0, high=21035.0, low=21010.0, close=21030.0)
    next_fills = broker.resolve_active_brackets(bar2, bar_index=6)
    assert len(next_fills) == 1
    assert next_fills[0].reason == "target"
    assert next_fills[0].price == 21030.0


def test_immediate_bracket_max_hold_timeout_uses_entry_bar() -> None:
    """max_hold_bars on an immediate-fill bracket counts from the entry
    bar (the bar the order filled on), not from submit + 1."""
    broker = _broker()
    ts = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    bar0 = _bar(ts, open_=21000.0, high=21005.0, low=20998.0, close=21002.0)
    broker.submit(
        BracketOrder(
            side=Side.LONG,
            qty=1,
            stop_price=20900.0,
            target_price=21100.0,
            fill_immediately=True,
            max_hold_bars=3,
        ),
        ts,
        bar_index=0,
    )
    broker.fill_immediate_brackets(bar0, bar_index=0)
    # Bars 1 + 2 within hold; no fills.
    for k in (1, 2):
        bar_k = _bar(
            ts + dt.timedelta(minutes=k),
            open_=21002.0, high=21004.0, low=21000.0, close=21001.0,
        )
        fills = broker.resolve_active_brackets(bar_k, bar_index=k)
        assert fills == [], f"unexpected fill on bar {k}"
    # Bar 3: bar_index - entry_bar_index = 3 >= max_hold_bars; force-close.
    bar3 = _bar(
        ts + dt.timedelta(minutes=3),
        open_=21003.0, high=21006.0, low=21001.0, close=21005.0,
    )
    timeout_fills = broker.resolve_active_brackets(bar3, bar_index=3)
    assert len(timeout_fills) == 1
    assert timeout_fills[0].reason == "timeout"
    assert timeout_fills[0].price == 21005.0  # bar's close
    assert broker.active_brackets == []


def test_normal_bracket_unaffected_by_fill_immediately_flag() -> None:
    """Default fill_immediately=False keeps existing behavior:
    submit on bar N, fill on bar N+1's open, range-check on bar N+1.
    Pin this so the engine extension doesn't accidentally change
    next-bar-fill semantics for the existing fractal_amd plugin."""
    broker = _broker()
    ts1 = dt.datetime(2026, 4, 24, 13, 30, tzinfo=dt.timezone.utc)
    bar1 = _bar(ts1, open_=21000.0, high=21010.0, low=20995.0, close=21005.0)
    broker.submit(
        BracketOrder(
            side=Side.LONG,
            qty=1,
            stop_price=20990.0,
            target_price=21030.0,
            # fill_immediately omitted -> default False
        ),
        ts1,
        bar_index=0,
    )
    # Should NOT fill via immediate path.
    immediate = broker.fill_immediate_brackets(bar1, bar_index=0)
    assert immediate == []
    assert len(broker.pending_entries) == 1

    # Standard next-bar fill on bar 1.
    ts2 = ts1 + dt.timedelta(minutes=1)
    bar2 = _bar(ts2, open_=21006.0, high=21010.0, low=21000.0, close=21008.0)
    fills = broker.resolve_pending_entries(bar2, bar_index=1)
    assert len(fills) == 1
    assert fills[0].price == 21006.0 + 0.25
