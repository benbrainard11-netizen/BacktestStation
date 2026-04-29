"""The bar-based backtest engine.

Pure: takes a Strategy, bars, and a config; returns a result. No
filesystem or DB writes happen here — that's `runner.py`'s job.
Determinism: same inputs -> byte-identical trades + equity output
sequences.

Event flow per bar:

    1. Update context (now, bar_index, history)
    2. Resolve any pending entries against this bar (market orders
       submitted on the previous bar fill at THIS bar's open)
    3. Resolve any active bracket stops/targets against this bar's
       [low, high] range
    4. Update the position's unrealized PnL and the equity curve
    5. Strategy.on_fill for each fill produced
    6. Strategy.on_bar -> new order intents
    7. Submit intents to the broker
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from app.backtest.broker import Broker, BrokerConfig
from app.backtest.events import Event, EventType
from app.backtest.metrics import (
    EquityPoint,
    build_equity_curve,
    compute_metrics,
)
from app.backtest.orders import (
    BracketOrder,
    Fill,
    Side,
    Trade,
)
from app.backtest.strategy import Bar, Context, Position, Strategy


@dataclass
class RunConfig:
    """Inputs to a single backtest run.

    Reproducibility: every field that affects the output sits here.
    The runner serializes this to config.json next to the run outputs.

    `aux_symbols` lists additional instruments the strategy can read
    via `context.aux[symbol]`. Used for cross-instrument signals like
    SMT divergence (NQ vs ES). Aux instruments do NOT drive the event
    loop — only the primary `symbol` does. Aux bars are aligned by
    `ts_event`; missing minutes show up as None.
    """

    strategy_name: str
    symbol: str
    timeframe: str  # currently always "1m"
    start: str  # ISO date YYYY-MM-DD
    end: str  # ISO date YYYY-MM-DD
    initial_equity: float = 25_000.0
    qty: int = 1
    commission_per_contract: float = 2.00
    slippage_ticks: int = 1
    tick_size: float = 0.25
    contract_value: float = 20.0
    flatten_on_last_bar: bool = True
    history_max: int = 1000
    aux_symbols: list[str] = field(default_factory=list)
    # Strategy-specific params; the strategy class is responsible for
    # interpreting them. Kept here so the run is fully reproducible
    # from the config.
    params: dict = field(default_factory=dict)
    # Engine-enforced trading-hours window. When `session_start_hour` is
    # set, the engine skips `strategy.on_bar()` for any bar whose
    # local-time hour (in `session_tz`) is outside [start, end). Fills,
    # equity, and history still update normally — only strategy
    # decisions are gated. This pulls market-hours filtering out of
    # individual plugins so two strategies on the same data are bound
    # by the same window. Default `None` = 24/5 (each plugin owns its
    # own filter, current behavior).
    session_start_hour: int | None = None
    session_end_hour: int | None = None
    session_tz: str = "America/New_York"


@dataclass
class BacktestResult:
    """What `run()` returns. Pure data; the runner persists it."""

    config: RunConfig
    trades: list[Trade]
    equity_points: list[EquityPoint]
    events: list[Event]
    metrics: dict
    final_position: Position | None  # always None if flatten_on_last_bar=True


def run(
    strategy: Strategy,
    bars: list[Bar],
    config: RunConfig,
    *,
    aux_bars: dict[str, dict[dt.datetime, Bar]] | None = None,
) -> BacktestResult:
    """Run one backtest. Returns trades, equity, events, metrics.

    `aux_bars` is a per-symbol dict of (ts_event -> Bar) lookups. The
    engine refreshes `context.aux` per primary bar by looking up each
    aux symbol's bar at the same ts_event. Missing minute = None.
    """
    aux_bars = aux_bars or {}
    # Validate every configured aux symbol has been provided (even if
    # the dict is empty for that symbol — the runner / caller must
    # decide what "no data at all" means).
    for sym in config.aux_symbols:
        if sym not in aux_bars:
            aux_bars[sym] = {}

    # Tz-aware bar invariant. Engine uses `astimezone()` for HTF candle
    # bounds and session gating; that needs tz-aware timestamps but
    # works regardless of the source tz. Reject naive datetimes (the
    # silent bug class — they look fine but compare incorrectly across
    # DST and aux-bar joins). The runner's canonical loader produces
    # UTC; tests sometimes use ET — both are accepted.
    if bars:
        first_ts = bars[0].ts_event
        if first_ts.tzinfo is None:
            raise ValueError(
                f"engine.run: bars must be tz-aware; bars[0].ts_event="
                f"{first_ts!r} has no tzinfo. Localize to UTC (canonical) "
                f"or another tz before passing — see app.backtest.runner."
                f"_read_symbol_bars for the canonical pattern."
            )

    # Pre-resolve session window timezone once (avoids ZoneInfo lookup
    # in the hot loop). `session_tz` is a string for serializability;
    # we instantiate the ZoneInfo here and reuse.
    session_tz_obj: ZoneInfo | None = None
    if config.session_start_hour is not None:
        session_tz_obj = ZoneInfo(config.session_tz)

    broker = Broker(
        BrokerConfig(
            tick_size=config.tick_size,
            contract_value=config.contract_value,
            commission_per_contract=config.commission_per_contract,
            slippage_ticks=config.slippage_ticks,
        )
    )
    context = Context(
        now=bars[0].ts_event if bars else _epoch(),
        bar_index=-1,
        equity=config.initial_equity,
        initial_equity=config.initial_equity,
        position=None,
        history=[],
        history_max=config.history_max,
        aux={},
    )

    events: list[Event] = []
    trades: list[Trade] = []
    equity_curve_inputs: list[tuple[dt.datetime, float]] = []
    realized_equity = config.initial_equity

    strategy.on_start(context)

    for i, bar in enumerate(bars):
        context.now = bar.ts_event
        context.bar_index = i
        # Refresh aux bars aligned to this primary ts_event. Missing
        # minute -> None. We rebuild the dict each bar so strategies
        # never see a stale aux row.
        if config.aux_symbols:
            context.aux = {
                sym: aux_bars[sym].get(bar.ts_event)
                for sym in config.aux_symbols
            }

        # 1. Resolve pending entry orders submitted on the prior bar.
        for fill in broker.resolve_pending_entries(bar, bar_index=i):
            events.append(_fill_event(fill, i))
            context.position = _apply_entry_fill(fill, bar, context, broker)
            realized_equity -= fill.commission
            events.append(
                Event(
                    ts=fill.ts,
                    type=EventType.POSITION_OPENED,
                    bar_index=i,
                    payload={
                        "side": context.position.side.value,
                        "qty": context.position.qty,
                        "entry_price": context.position.entry_price,
                    },
                )
            )
            strategy.on_fill(fill, context)

        # 2. Resolve active brackets against this bar's range.
        for fill in broker.resolve_active_brackets(bar, bar_index=i):
            trade, realized_pnl = _close_position_with_fill(
                context.position, fill, config
            )
            assert trade is not None
            trades.append(trade)
            realized_equity += realized_pnl - fill.commission
            events.append(_fill_event(fill, i))
            events.append(_close_event(fill, trade, i))
            if fill.fill_confidence == "conservative":
                events.append(
                    Event(
                        ts=fill.ts,
                        type=EventType.AMBIGUOUS_FILL,
                        bar_index=i,
                        payload={"reason": fill.reason},
                    )
                )
            context.position = None
            strategy.on_fill(fill, context)

        # 3. Mark equity for this bar (realized + open MTM).
        if context.position is not None:
            mtm = _mark_to_market(context.position, bar, config)
            equity = realized_equity + mtm
        else:
            equity = realized_equity
        context.equity = equity
        equity_curve_inputs.append((bar.ts_event, equity))

        # 4. History BEFORE asking the strategy. Strategy sees this bar
        # as the head of history; never any future bar.
        _push_history(context, bar)

        # 4b. Engine-enforced session window. When configured, skip
        # `strategy.on_bar()` (and any of its same-bar immediate-fill
        # brackets) for bars outside [session_start_hour, session_end_hour)
        # in `session_tz`. Pulls market-hours filtering out of plugins so
        # two strategies on the same bars are bound by the same window.
        if (
            session_tz_obj is not None
            and config.session_start_hour is not None
            and config.session_end_hour is not None
        ):
            local_hour = bar.ts_event.astimezone(session_tz_obj).hour
            if not (
                config.session_start_hour
                <= local_hour
                < config.session_end_hour
            ):
                continue

        # 5. Strategy decides what to do this bar.
        intents = strategy.on_bar(bar, context) or []
        for intent in intents:
            order = broker.submit(intent, bar.ts_event, i)
            if order is not None:
                events.append(
                    Event(
                        ts=bar.ts_event,
                        type=EventType.ORDER_SUBMITTED,
                        bar_index=i,
                        payload={
                            "order_id": order.id,
                            "intent_type": type(intent).__name__,
                        },
                    )
                )

        # 6. Process any newly-submitted brackets with `fill_immediately=True`.
        # These fill at THIS bar's open + slippage and become active for
        # next-bar-onwards stop/target watch. Used by the trusted Fractal
        # AMD plugin to match the script's "decide on bar T+1's open"
        # semantics — see `BracketOrder.fill_immediately` docstring.
        for fill in broker.fill_immediate_brackets(bar, bar_index=i):
            events.append(_fill_event(fill, i))
            context.position = _apply_entry_fill(fill, bar, context, broker)
            realized_equity -= fill.commission
            events.append(
                Event(
                    ts=fill.ts,
                    type=EventType.POSITION_OPENED,
                    bar_index=i,
                    payload={
                        "side": context.position.side.value,
                        "qty": context.position.qty,
                        "entry_price": context.position.entry_price,
                    },
                )
            )
            strategy.on_fill(fill, context)

    # 6. Final-bar flatten if requested and a position is still open.
    if (
        bars
        and config.flatten_on_last_bar
        and broker.active_brackets
    ):
        last_bar = bars[-1]
        for fill in broker.force_close_at(last_bar, reason="eod_flatten"):
            trade, realized_pnl = _close_position_with_fill(
                context.position, fill, config
            )
            assert trade is not None
            trades.append(trade)
            realized_equity += realized_pnl - fill.commission
            events.append(
                Event(
                    ts=fill.ts,
                    type=EventType.EOD_FLATTEN,
                    bar_index=len(bars) - 1,
                    payload={"price": fill.price},
                )
            )
            events.append(_fill_event(fill, len(bars) - 1))
            events.append(_close_event(fill, trade, len(bars) - 1))
            context.position = None
            strategy.on_fill(fill, context)
        # Update final equity point to reflect the flatten.
        if equity_curve_inputs:
            equity_curve_inputs[-1] = (last_bar.ts_event, realized_equity)
        context.equity = realized_equity

    strategy.on_end(context)

    equity_points = build_equity_curve(equity_curve_inputs, config.initial_equity)
    metrics = compute_metrics(trades, equity_points, config.initial_equity)

    return BacktestResult(
        config=config,
        trades=trades,
        equity_points=equity_points,
        events=events,
        metrics=metrics,
        final_position=context.position,
    )


# --- Helpers ------------------------------------------------------------


def _push_history(context: Context, bar: Bar) -> None:
    context.history.append(bar)
    overflow = len(context.history) - context.history_max
    if overflow > 0:
        del context.history[:overflow]


def _apply_entry_fill(
    fill: Fill, bar: Bar, context: Context, broker: Broker
) -> Position:
    """Build a Position from an entry Fill. Resolves stop/target +
    per-order contract_value override from the matching active bracket
    if there is one (for non-bracket market entries the position has
    no stop/target and inherits the run config's contract_value)."""
    stop_price = None
    target_price = None
    contract_value: float | None = None
    for order in broker.active_brackets:
        if order.id == fill.order_id and isinstance(order.intent, BracketOrder):
            stop_price = order.intent.stop_price
            target_price = order.intent.target_price
            contract_value = order.intent.contract_value
            break
    return Position(
        side=fill.side,
        qty=fill.qty,
        entry_price=fill.price,
        entry_ts=fill.ts,
        stop_price=stop_price,
        target_price=target_price,
        contract_value=contract_value,
    )


def _position_contract_value(position: Position, config: RunConfig) -> float:
    return (
        position.contract_value
        if position.contract_value is not None
        else config.contract_value
    )


def _mark_to_market(
    position: Position, bar: Bar, config: RunConfig
) -> float:
    """Open-position PnL in dollar terms at the bar's close."""
    diff = (bar.close - position.entry_price) * position.side.sign
    return diff * position.qty * _position_contract_value(position, config)


def _close_position_with_fill(
    position: Position | None, fill: Fill, config: RunConfig
) -> tuple[Trade | None, float]:
    """Realize the trade. Returns (trade, dollar_pnl_excluding_commission)."""
    if position is None:
        return None, 0.0
    cv = _position_contract_value(position, config)
    diff = (fill.price - position.entry_price) * position.side.sign
    realized_pnl_dollars = diff * position.qty * cv

    # r_multiple: dollar PnL / dollar risk per the position's stop.
    r_multiple = None
    if position.stop_price is not None:
        risk_per_contract = (
            abs(position.entry_price - position.stop_price) * cv
        )
        if risk_per_contract > 0:
            r_multiple = realized_pnl_dollars / (risk_per_contract * position.qty)

    trade = Trade(
        entry_ts=position.entry_ts,
        exit_ts=fill.ts,
        side=position.side,
        qty=position.qty,
        entry_price=position.entry_price,
        exit_price=fill.price,
        stop_price=position.stop_price,
        target_price=position.target_price,
        pnl=realized_pnl_dollars,
        r_multiple=r_multiple,
        exit_reason=fill.reason or "manual",
        fill_confidence=fill.fill_confidence,
    )
    return trade, realized_pnl_dollars


def _fill_event(fill: Fill, bar_index: int) -> Event:
    et = EventType.STOP_HIT if fill.reason == "stop" else (
        EventType.TARGET_HIT if fill.reason == "target" else EventType.FILL
    )
    return Event(
        ts=fill.ts,
        type=et,
        bar_index=bar_index,
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


def _close_event(fill: Fill, trade: Trade, bar_index: int) -> Event:
    return Event(
        ts=fill.ts,
        type=EventType.POSITION_CLOSED,
        bar_index=bar_index,
        payload={
            "exit_reason": trade.exit_reason,
            "pnl": trade.pnl,
            "r_multiple": trade.r_multiple,
            "fill_confidence": trade.fill_confidence,
        },
    )


def _epoch() -> dt.datetime:
    return dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
