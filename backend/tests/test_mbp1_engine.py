from __future__ import annotations

import datetime as dt

import pytest

from app.backtest.mbp1_engine import (
    Mbp1Context,
    Mbp1Event,
    Mbp1RunConfig,
    Mbp1Strategy,
    events_from_rows,
    run,
)
from app.backtest.orders import BracketOrder, OrderIntent, Side

UTC = dt.UTC


def _event(
    idx: int,
    *,
    bid: float,
    ask: float,
    symbol: str = "NQ.c.0",
) -> Mbp1Event:
    return Mbp1Event(
        ts_event=dt.datetime(2026, 4, 24, 13, 30, idx, tzinfo=UTC),
        symbol=symbol,
        bid_px=bid,
        ask_px=ask,
        bid_sz=10,
        ask_sz=10,
        sequence=idx,
    )


class SubmitOnceBracket(Mbp1Strategy):
    name = "submit_once_bracket"

    def __init__(
        self,
        *,
        side: Side = Side.LONG,
        stop_price: float = 99.75,
        target_price: float = 101.0,
    ) -> None:
        self.side = side
        self.stop_price = stop_price
        self.target_price = target_price
        self.submitted = False

    def on_event(
        self, event: Mbp1Event, context: Mbp1Context
    ) -> list[OrderIntent]:
        if self.submitted:
            return []
        self.submitted = True
        return [
            BracketOrder(
                side=self.side,
                qty=1,
                stop_price=self.stop_price,
                target_price=self.target_price,
            )
        ]


def _config(**kwargs) -> Mbp1RunConfig:
    return Mbp1RunConfig(
        strategy_name="submit_once_bracket",
        symbol="NQ.c.0",
        start="2026-04-24",
        end="2026-04-25",
        commission_per_contract=0.0,
        slippage_ticks=0,
        tick_size=0.25,
        contract_value=20.0,
        **kwargs,
    )


def test_mbp1_engine_resolves_target_before_later_stop() -> None:
    events = [
        _event(0, bid=100.00, ask=100.25),  # strategy submits
        _event(1, bid=100.00, ask=100.25),  # entry buys ask 100.25
        _event(2, bid=101.00, ask=101.25),  # target marketable first
        _event(3, bid=99.75, ask=100.00),   # later stop should not matter
    ]

    result = run(SubmitOnceBracket(), events, _config())

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason == "target"
    assert trade.entry_price == 100.25
    assert trade.exit_price == 101.00
    assert trade.pnl == pytest.approx(15.0)
    assert result.metrics["ambiguous_fill_count"] == 0


def test_mbp1_engine_resolves_stop_before_later_target() -> None:
    events = [
        _event(0, bid=100.00, ask=100.25),  # strategy submits
        _event(1, bid=100.00, ask=100.25),  # entry buys ask 100.25
        _event(2, bid=99.75, ask=100.00),   # stop executable first
        _event(3, bid=101.00, ask=101.25),  # later target should not matter
    ]

    result = run(SubmitOnceBracket(), events, _config())

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason == "stop"
    assert trade.entry_price == 100.25
    assert trade.exit_price == 99.75
    assert trade.pnl == pytest.approx(-10.0)
    assert result.metrics["ambiguous_fill_count"] == 0


def test_mbp1_engine_uses_ask_for_short_stop_and_target_sequence() -> None:
    events = [
        _event(0, bid=100.00, ask=100.25),  # strategy submits
        _event(1, bid=100.00, ask=100.25),  # entry sells bid 100.00
        _event(2, bid=98.75, ask=99.00),    # short target buy limit first
        _event(3, bid=101.00, ask=101.25),  # later stop should not matter
    ]

    result = run(
        SubmitOnceBracket(
            side=Side.SHORT,
            stop_price=101.00,
            target_price=99.00,
        ),
        events,
        _config(),
    )

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason == "target"
    assert trade.entry_price == 100.00
    assert trade.exit_price == 99.00
    assert trade.pnl == pytest.approx(20.0)


def test_mbp1_engine_flatten_uses_executable_liquidation_side() -> None:
    events = [
        _event(0, bid=100.00, ask=100.25),
        _event(1, bid=100.00, ask=100.25),
        _event(2, bid=100.50, ask=100.75),
    ]

    result = run(
        SubmitOnceBracket(stop_price=95.0, target_price=110.0),
        events,
        _config(flatten_on_last_event=True),
    )

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason == "eod_flatten"
    assert trade.entry_price == 100.25
    assert trade.exit_price == 100.50
    assert trade.pnl == pytest.approx(5.0)


def test_mbp1_engine_rejects_naive_timestamps() -> None:
    events = [
        Mbp1Event(
            ts_event=dt.datetime(2026, 4, 24, 13, 30),
            symbol="NQ.c.0",
            bid_px=100.0,
            ask_px=100.25,
            bid_sz=10,
            ask_sz=10,
        )
    ]

    with pytest.raises(ValueError, match="tz-aware"):
        run(SubmitOnceBracket(), events, _config())


def test_events_from_rows_accepts_dicts() -> None:
    rows = [
        {
            "ts_event": dt.datetime(2026, 4, 24, 13, 30, tzinfo=UTC),
            "symbol": "NQ.c.0",
            "bid_px": 100.0,
            "ask_px": 100.25,
            "bid_sz": 10,
            "ask_sz": 8,
            "action": "T",
            "side": "A",
            "price": 100.25,
            "size": 2,
        }
    ]

    events = events_from_rows(rows)

    assert len(events) == 1
    assert events[0].symbol == "NQ.c.0"
    assert events[0].bid_px == 100.0
    assert events[0].action == "T"
