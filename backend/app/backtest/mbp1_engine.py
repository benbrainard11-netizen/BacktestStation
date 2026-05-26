"""Pure MBP-1 event-level backtest engine.

This engine is intentionally separate from the existing bar engine. The
bar engine answers "what happened inside this candle?" conservatively
when OHLC cannot know the sequence. This engine consumes ordered MBP-1
top-of-book events, so stop/target resolution follows the actual event
order we feed it.

Scope for v1:

- single symbol
- single open position
- market entries and bracket orders
- top-of-book execution: buys lift ask, sells hit bid
- target limits fill at the target price once marketable
- stop/flatten market exits fill at current executable top plus slippage

Still out of scope: queue position, partial fills, hidden liquidity, and
multi-level book depth. Those require MBO/queue modeling rather than MBP-1.
"""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from app.backtest.events import Event, EventType
from app.backtest.metrics import EquityPoint, build_equity_curve, compute_metrics
from app.backtest.orders import (
    BracketOrder,
    CancelOrder,
    Fill,
    MarketEntry,
    Order,
    OrderIntent,
    Side,
    Trade,
)


@dataclass(frozen=True)
class Mbp1Event:
    """One normalized MBP-1 row.

    The important execution fields are the top-of-book quote:
    `bid_px`, `ask_px`, `bid_sz`, `ask_sz`. Other Databento fields are
    preserved because MBP-1 strategies often need action/side/price/size
    to build order-flow features.
    """

    ts_event: dt.datetime
    symbol: str
    bid_px: float
    ask_px: float
    bid_sz: int
    ask_sz: int
    action: str = ""
    side: str = ""
    depth: int = 0
    price: float | None = None
    size: int | None = None
    sequence: int | None = None
    ts_recv: dt.datetime | None = None
    ts_in_delta: int | None = None
    flags: int | None = None
    publisher_id: int | None = None
    instrument_id: int | None = None

    @property
    def has_valid_quote(self) -> bool:
        return (
            _finite_positive(self.bid_px)
            and _finite_positive(self.ask_px)
            and self.ask_px >= self.bid_px
        )

    @property
    def mid(self) -> float:
        return (self.bid_px + self.ask_px) / 2.0

    @property
    def spread(self) -> float:
        return self.ask_px - self.bid_px


@dataclass(frozen=True)
class Mbp1RunConfig:
    """Inputs that make an MBP-1 run reproducible."""

    strategy_name: str
    symbol: str
    start: str
    end: str
    initial_equity: float = 25_000.0
    qty: int = 1
    commission_per_contract: float = 2.00
    slippage_ticks: int = 0
    tick_size: float = 0.25
    contract_value: float = 20.0
    flatten_on_last_event: bool = True
    history_max: int = 10_000
    equity_sample_every: int = 1
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Mbp1OpenPosition:
    """Open position state tracked by the MBP-1 engine."""

    side: Side
    qty: int
    entry_price: float
    entry_ts: dt.datetime
    entry_event_index: int
    entry_commission: float
    order_id: str
    stop_price: float | None = None
    target_price: float | None = None
    contract_value: float | None = None


@dataclass
class Mbp1Context:
    """Runtime view an MBP-1 strategy sees on each event."""

    now: dt.datetime
    event_index: int
    equity: float
    initial_equity: float
    position: Mbp1OpenPosition | None = None
    history: list[Mbp1Event] = field(default_factory=list)
    history_max: int = 10_000

    @property
    def in_position(self) -> bool:
        return self.position is not None

    @property
    def best_bid(self) -> float | None:
        return self.history[-1].bid_px if self.history else None

    @property
    def best_ask(self) -> float | None:
        return self.history[-1].ask_px if self.history else None

    @property
    def spread(self) -> float | None:
        return self.history[-1].spread if self.history else None

    def spread_ticks(self, tick_size: float) -> float | None:
        if not self.history or tick_size <= 0:
            return None
        return self.history[-1].spread / tick_size


class Mbp1Strategy:
    """Base class for MBP-1 event strategies."""

    name: str = "unnamed_mbp1_strategy"

    def on_start(self, context: Mbp1Context) -> None:
        """Called once before the first event."""

    def on_event(
        self, event: Mbp1Event, context: Mbp1Context
    ) -> list[OrderIntent]:
        """Called for each MBP-1 event. Return orders to submit."""
        return []

    def on_fill(self, fill: Fill, context: Mbp1Context) -> None:
        """Called when an entry or exit fills."""

    def on_end(self, context: Mbp1Context) -> None:
        """Called once after the last event."""


@dataclass
class Mbp1BacktestResult:
    config: Mbp1RunConfig
    trades: list[Trade]
    equity_points: list[EquityPoint]
    events: list[Event]
    metrics: dict
    final_position: Mbp1OpenPosition | None


def events_from_rows(rows: Iterable[Any]) -> list[Mbp1Event]:
    """Normalize dicts, namedtuples, or dataframe rows into Mbp1Events."""

    out: list[Mbp1Event] = []
    for row in rows:
        out.append(
            Mbp1Event(
                ts_event=_to_datetime(_row_get(row, "ts_event")),
                ts_recv=(
                    _to_datetime(_row_get(row, "ts_recv"))
                    if _row_get(row, "ts_recv") is not None
                    else None
                ),
                ts_in_delta=_row_get(row, "ts_in_delta"),
                symbol=str(_row_get(row, "symbol")),
                action=str(_row_get(row, "action", "") or ""),
                side=str(_row_get(row, "side", "") or ""),
                depth=int(_row_get(row, "depth", 0) or 0),
                price=_optional_float(_row_get(row, "price")),
                size=_optional_int(_row_get(row, "size")),
                flags=_optional_int(_row_get(row, "flags")),
                bid_px=float(_row_get(row, "bid_px")),
                ask_px=float(_row_get(row, "ask_px")),
                bid_sz=int(_row_get(row, "bid_sz", 0) or 0),
                ask_sz=int(_row_get(row, "ask_sz", 0) or 0),
                publisher_id=_optional_int(_row_get(row, "publisher_id")),
                instrument_id=_optional_int(_row_get(row, "instrument_id")),
                sequence=_optional_int(_row_get(row, "sequence")),
            )
        )
    return out


def events_from_dataframe(df: Any) -> list[Mbp1Event]:
    """Normalize a pandas/Polars-like dataframe into Mbp1Events."""

    return events_from_rows(df.itertuples(index=False))


def run(
    strategy: Mbp1Strategy,
    events_in: Iterable[Mbp1Event],
    config: Mbp1RunConfig,
) -> Mbp1BacktestResult:
    """Run an MBP-1 event-level backtest."""

    if config.equity_sample_every < 1:
        raise ValueError("equity_sample_every must be >= 1")
    if config.history_max < 1:
        raise ValueError("history_max must be >= 1")

    events_list = list(events_in)
    _validate_events(events_list, config)

    context = Mbp1Context(
        now=events_list[0].ts_event if events_list else _epoch(),
        event_index=-1,
        equity=config.initial_equity,
        initial_equity=config.initial_equity,
        position=None,
        history=[],
        history_max=config.history_max,
    )

    pending_entries: list[Order] = []
    active_bracket: Order | None = None
    realized_equity = config.initial_equity
    event_log: list[Event] = []
    trades: list[Trade] = []
    equity_inputs: list[tuple[dt.datetime, float]] = []

    strategy.on_start(context)

    for i, event in enumerate(events_list):
        context.now = event.ts_event
        context.event_index = i

        # 1. Fill orders submitted on an earlier event at this event's
        # executable top-of-book.
        for order in list(pending_entries):
            if order.submitted_bar_index >= i:
                continue
            fill = _fill_entry_order(order, event, config)
            if fill is None:
                continue
            pending_entries.remove(order)
            event_log.append(_fill_event(fill, i))
            position = _open_position_from_fill(order, fill, config, i)
            context.position = position
            if isinstance(order.intent, BracketOrder):
                active_bracket = order
                order.state = "active"
            else:
                order.state = "filled"
            event_log.append(_position_opened_event(position, i))
            strategy.on_fill(fill, context)

        # 2. Resolve active bracket against the actual event sequence.
        if (
            context.position is not None
            and active_bracket is not None
            and context.position.entry_event_index < i
        ):
            exit_fill = _resolve_bracket_exit(
                context.position, active_bracket, event, config
            )
            if exit_fill is not None:
                trade = _close_position(context.position, exit_fill, config)
                trades.append(trade)
                realized_equity += trade.pnl
                event_log.append(_fill_event(exit_fill, i))
                event_log.append(_position_closed_event(exit_fill, trade, i))
                if exit_fill.fill_confidence == "conservative":
                    event_log.append(
                        Event(
                            ts=exit_fill.ts,
                            type=EventType.AMBIGUOUS_FILL,
                            bar_index=i,
                            payload={"reason": exit_fill.reason},
                        )
                    )
                active_bracket.state = "filled"
                active_bracket = None
                context.position = None
                strategy.on_fill(exit_fill, context)

        # 3. Mark-to-market using liquidation side of the top-of-book.
        if context.position is not None:
            context.equity = realized_equity + _mark_to_market(
                context.position, event, config
            )
        else:
            context.equity = realized_equity
        if i % config.equity_sample_every == 0 or i == len(events_list) - 1:
            equity_inputs.append((event.ts_event, context.equity))

        # 4. Strategy sees current event in history, never future events.
        _push_history(context, event)
        intents = strategy.on_event(event, context) or []
        _submit_intents(
            intents,
            pending_entries=pending_entries,
            context=context,
            event=event,
            event_index=i,
            event_log=event_log,
        )

    # 5. Flatten any open position at the final event.
    if (
        config.flatten_on_last_event
        and context.position is not None
        and events_list
    ):
        i = len(events_list) - 1
        final_event = events_list[-1]
        fill = _force_close_fill(context.position, final_event, config)
        trade = _close_position(context.position, fill, config)
        trades.append(trade)
        realized_equity += trade.pnl
        event_log.append(
            Event(
                ts=fill.ts,
                type=EventType.EOD_FLATTEN,
                bar_index=i,
                payload={"price": fill.price},
            )
        )
        event_log.append(_fill_event(fill, i))
        event_log.append(_position_closed_event(fill, trade, i))
        context.position = None
        context.equity = realized_equity
        if equity_inputs:
            equity_inputs[-1] = (final_event.ts_event, realized_equity)
        else:
            equity_inputs.append((final_event.ts_event, realized_equity))
        strategy.on_fill(fill, context)

    strategy.on_end(context)

    equity_points = build_equity_curve(equity_inputs, config.initial_equity)
    metrics = compute_metrics(trades, equity_points, config.initial_equity)
    return Mbp1BacktestResult(
        config=config,
        trades=trades,
        equity_points=equity_points,
        events=event_log,
        metrics=metrics,
        final_position=context.position,
    )


def _submit_intents(
    intents: list[OrderIntent],
    *,
    pending_entries: list[Order],
    context: Mbp1Context,
    event: Mbp1Event,
    event_index: int,
    event_log: list[Event],
) -> None:
    for intent in intents:
        if isinstance(intent, CancelOrder):
            for order in list(pending_entries):
                if order.id == intent.order_id:
                    order.state = "cancelled"
                    pending_entries.remove(order)
                    event_log.append(
                        Event(
                            ts=event.ts_event,
                            type=EventType.ORDER_CANCELLED,
                            bar_index=event_index,
                            payload={"order_id": order.id},
                        )
                    )
                    break
            continue

        # v1 is intentionally single-position/single-pending-order. Ignore
        # duplicate entries while capital is already committed.
        if context.position is not None or pending_entries:
            continue
        order = Order.new(intent, event.ts_event, event_index)
        pending_entries.append(order)
        event_log.append(
            Event(
                ts=event.ts_event,
                type=EventType.ORDER_SUBMITTED,
                bar_index=event_index,
                payload={
                    "order_id": order.id,
                    "intent_type": type(intent).__name__,
                },
            )
        )


def _fill_entry_order(
    order: Order,
    event: Mbp1Event,
    config: Mbp1RunConfig,
) -> Fill | None:
    if not event.has_valid_quote:
        return None
    if isinstance(order.intent, MarketEntry):
        side = order.intent.side
        qty = order.intent.qty
    elif isinstance(order.intent, BracketOrder):
        side = order.intent.side
        qty = order.intent.qty
    else:
        return None
    price = _market_fill_price(event, side, config)
    fill = Fill(
        order_id=order.id,
        ts=event.ts_event,
        side=side,
        qty=qty,
        price=price,
        commission=qty * config.commission_per_contract,
        is_entry=True,
        fill_confidence="exact",
        reason="market",
    )
    order.entry_fill = fill
    order.entry_bar_index = None
    return fill


def _open_position_from_fill(
    order: Order,
    fill: Fill,
    config: Mbp1RunConfig,
    event_index: int,
) -> Mbp1OpenPosition:
    stop_price = None
    target_price = None
    contract_value = None
    if isinstance(order.intent, BracketOrder):
        stop_price = order.intent.stop_price
        target_price = order.intent.target_price
        contract_value = order.intent.contract_value
    return Mbp1OpenPosition(
        side=fill.side,
        qty=fill.qty,
        entry_price=fill.price,
        entry_ts=fill.ts,
        entry_event_index=event_index,
        entry_commission=fill.commission,
        order_id=fill.order_id,
        stop_price=stop_price,
        target_price=target_price,
        contract_value=contract_value or config.contract_value,
    )


def _resolve_bracket_exit(
    position: Mbp1OpenPosition,
    order: Order,
    event: Mbp1Event,
    config: Mbp1RunConfig,
) -> Fill | None:
    if not event.has_valid_quote:
        return None
    assert isinstance(order.intent, BracketOrder)
    if position.stop_price is None or position.target_price is None:
        return None

    if position.side is Side.LONG:
        stop_touched = event.bid_px <= position.stop_price
        target_touched = event.bid_px >= position.target_price
        stop_price = _market_fill_price(event, Side.SHORT, config)
        target_price = position.target_price
        exit_side = Side.SHORT
    else:
        stop_touched = event.ask_px >= position.stop_price
        target_touched = event.ask_px <= position.target_price
        stop_price = _market_fill_price(event, Side.LONG, config)
        target_price = position.target_price
        exit_side = Side.LONG

    if not stop_touched and not target_touched:
        return None

    if stop_touched and target_touched:
        price = stop_price
        reason = "stop"
        confidence = "conservative"
    elif stop_touched:
        price = stop_price
        reason = "stop"
        confidence = "exact"
    else:
        price = target_price
        reason = "target"
        confidence = "exact"

    return Fill(
        order_id=order.id,
        ts=event.ts_event,
        side=exit_side,
        qty=position.qty,
        price=price,
        commission=position.qty * config.commission_per_contract,
        is_entry=False,
        fill_confidence=confidence,
        reason=reason,
    )


def _force_close_fill(
    position: Mbp1OpenPosition,
    event: Mbp1Event,
    config: Mbp1RunConfig,
) -> Fill:
    exit_side = position.side.opposite
    return Fill(
        order_id=position.order_id,
        ts=event.ts_event,
        side=exit_side,
        qty=position.qty,
        price=_market_fill_price(event, exit_side, config),
        commission=position.qty * config.commission_per_contract,
        is_entry=False,
        fill_confidence="exact",
        reason="eod_flatten",
    )


def _close_position(
    position: Mbp1OpenPosition,
    fill: Fill,
    config: Mbp1RunConfig,
) -> Trade:
    contract_value = position.contract_value or config.contract_value
    gross = (
        (fill.price - position.entry_price)
        * position.side.sign
        * position.qty
        * contract_value
    )
    net = gross - position.entry_commission - fill.commission
    r_multiple = None
    if position.stop_price is not None:
        risk = abs(position.entry_price - position.stop_price) * contract_value * position.qty
        if risk > 0:
            r_multiple = net / risk
    return Trade(
        entry_ts=position.entry_ts,
        exit_ts=fill.ts,
        side=position.side,
        qty=position.qty,
        entry_price=position.entry_price,
        exit_price=fill.price,
        stop_price=position.stop_price,
        target_price=position.target_price,
        pnl=net,
        r_multiple=r_multiple,
        exit_reason=fill.reason,
        fill_confidence=fill.fill_confidence,
    )


def _mark_to_market(
    position: Mbp1OpenPosition,
    event: Mbp1Event,
    config: Mbp1RunConfig,
) -> float:
    if not event.has_valid_quote:
        return 0.0
    exit_price = event.bid_px if position.side is Side.LONG else event.ask_px
    contract_value = position.contract_value or config.contract_value
    gross = (
        (exit_price - position.entry_price)
        * position.side.sign
        * position.qty
        * contract_value
    )
    return gross - position.entry_commission


def _market_fill_price(
    event: Mbp1Event,
    side: Side,
    config: Mbp1RunConfig,
) -> float:
    slippage = config.slippage_ticks * config.tick_size
    if side is Side.LONG:
        return event.ask_px + slippage
    return event.bid_px - slippage


def _fill_event(fill: Fill, event_index: int) -> Event:
    if fill.reason == "stop":
        event_type = EventType.STOP_HIT
    elif fill.reason == "target":
        event_type = EventType.TARGET_HIT
    else:
        event_type = EventType.FILL
    return Event(
        ts=fill.ts,
        type=event_type,
        bar_index=event_index,
        payload={
            "order_id": fill.order_id,
            "side": fill.side.value,
            "qty": fill.qty,
            "price": fill.price,
            "commission": fill.commission,
            "is_entry": fill.is_entry,
            "reason": fill.reason,
            "fill_confidence": fill.fill_confidence,
        },
    )


def _position_opened_event(position: Mbp1OpenPosition, event_index: int) -> Event:
    return Event(
        ts=position.entry_ts,
        type=EventType.POSITION_OPENED,
        bar_index=event_index,
        payload={
            "side": position.side.value,
            "qty": position.qty,
            "entry_price": position.entry_price,
            "stop_price": position.stop_price,
            "target_price": position.target_price,
        },
    )


def _position_closed_event(fill: Fill, trade: Trade, event_index: int) -> Event:
    return Event(
        ts=fill.ts,
        type=EventType.POSITION_CLOSED,
        bar_index=event_index,
        payload={
            "exit_reason": trade.exit_reason,
            "pnl": trade.pnl,
            "r_multiple": trade.r_multiple,
            "fill_confidence": trade.fill_confidence,
        },
    )


def _push_history(context: Mbp1Context, event: Mbp1Event) -> None:
    context.history.append(event)
    overflow = len(context.history) - context.history_max
    if overflow > 0:
        del context.history[:overflow]


def _validate_events(events: list[Mbp1Event], config: Mbp1RunConfig) -> None:
    prev_key: tuple[dt.datetime, int] | None = None
    for i, event in enumerate(events):
        if event.ts_event.tzinfo is None:
            raise ValueError(
                f"mbp1_engine.run: events must be tz-aware; "
                f"events[{i}].ts_event={event.ts_event!r}"
            )
        if event.symbol != config.symbol:
            raise ValueError(
                f"mbp1_engine.run: event symbol {event.symbol!r} does not "
                f"match config.symbol {config.symbol!r}"
            )
        key = (event.ts_event, event.sequence or 0)
        if prev_key is not None and key < prev_key:
            raise ValueError("mbp1_engine.run: events must be sorted by ts_event/sequence")
        prev_key = key


def _to_datetime(value: Any) -> dt.datetime:
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    if isinstance(value, dt.datetime):
        return value
    raise TypeError(f"expected datetime-like value, got {type(value).__name__}")


def _row_get(row: Any, name: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _finite_positive(value: float) -> bool:
    return math.isfinite(value) and value > 0


def _epoch() -> dt.datetime:
    return dt.datetime(1970, 1, 1, tzinfo=dt.UTC)
