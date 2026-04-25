"""Tests for app.backtest.orders dataclasses."""

from __future__ import annotations

import datetime as dt

import pytest

from app.backtest.orders import (
    BracketOrder,
    CancelOrder,
    Fill,
    MarketEntry,
    Order,
    Side,
    Trade,
)


def test_side_opposite() -> None:
    assert Side.LONG.opposite is Side.SHORT
    assert Side.SHORT.opposite is Side.LONG


def test_side_sign() -> None:
    assert Side.LONG.sign == 1
    assert Side.SHORT.sign == -1


def test_market_entry_construction() -> None:
    intent = MarketEntry(side=Side.LONG, qty=2)
    assert intent.side is Side.LONG
    assert intent.qty == 2


def test_bracket_order_construction() -> None:
    intent = BracketOrder(
        side=Side.LONG, qty=1, stop_price=21000.0, target_price=21030.0
    )
    assert intent.stop_price < intent.target_price


def test_order_factory_assigns_id() -> None:
    intent = MarketEntry(side=Side.LONG, qty=1)
    ts = dt.datetime(2026, 4, 24, tzinfo=dt.timezone.utc)
    order = Order.new(intent, ts, bar_index=5)
    assert order.id
    assert len(order.id) == 12
    assert order.state == "pending"
    assert order.submitted_bar_index == 5


def test_cancel_order_carries_id() -> None:
    co = CancelOrder(order_id="abc")
    assert co.order_id == "abc"


def test_fill_immutable() -> None:
    f = Fill(
        order_id="x",
        ts=dt.datetime(2026, 4, 24, tzinfo=dt.timezone.utc),
        side=Side.LONG,
        qty=1,
        price=21000.0,
        commission=2.0,
        is_entry=True,
    )
    with pytest.raises(Exception):
        f.price = 99999  # type: ignore[misc]


def test_trade_default_tags() -> None:
    t = Trade(
        entry_ts=dt.datetime(2026, 4, 24, tzinfo=dt.timezone.utc),
        exit_ts=dt.datetime(2026, 4, 24, tzinfo=dt.timezone.utc),
        side=Side.LONG,
        qty=1,
        entry_price=21000.0,
        exit_price=21030.0,
        stop_price=20990.0,
        target_price=21030.0,
        pnl=600.0,
        r_multiple=3.0,
        exit_reason="target",
        fill_confidence="exact",
    )
    assert t.tags == []
