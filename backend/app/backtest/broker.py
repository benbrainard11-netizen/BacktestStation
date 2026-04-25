"""Broker simulator: order resolution + fills + slippage + commission.

The engine talks to the broker through three calls per bar:

    broker.submit(intent, ts, bar_index) -> Order
    broker.resolve_pending_entries(prev_bar, current_bar) -> list[Fill]
    broker.resolve_active_brackets(current_bar) -> list[Fill]

Fill conventions:

  - Market entry orders submitted while processing bar N fill at bar
    N+1's open + slippage. This is the standard "next bar open"
    convention that prevents lookahead.
  - Bracket orders' entry leg fills the same way; once filled, the
    stop and target legs become active and are checked against each
    subsequent bar's [low, high] range.
  - When a single bar contains both stop and target levels, fill
    confidence is "conservative" and the stop wins. Per
    `CLAUDE.md` §8 — the engine never lets the backtest pretend to
    know something it doesn't.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.backtest.orders import (
    BracketOrder,
    CancelOrder,
    Fill,
    MarketEntry,
    Order,
    OrderIntent,
    Side,
)
from app.backtest.strategy import Bar


@dataclass
class BrokerConfig:
    """Per-instrument execution config. All values explicit, no
    inline magic numbers per CLAUDE.md."""

    tick_size: float = 0.25  # NQ default
    contract_value: float = 20.0  # NQ: $20 per point
    commission_per_contract: float = 2.00
    slippage_ticks: int = 1


class Broker:
    """Pending + active order state, plus fill resolution."""

    def __init__(self, config: BrokerConfig) -> None:
        self.config = config
        # Orders waiting for their entry to fill on the next bar.
        self.pending_entries: list[Order] = []
        # Bracket orders whose entry has filled; stop/target are live.
        self.active_brackets: list[Order] = []

    # --- Submission ---

    def submit(
        self, intent: OrderIntent, ts: dt.datetime, bar_index: int
    ) -> Order | None:
        """Accept an intent. Returns the materialized Order, or None if
        the intent was a CancelOrder (which is applied immediately and
        doesn't have its own ongoing record)."""
        if isinstance(intent, CancelOrder):
            self._cancel(intent.order_id)
            return None
        order = Order.new(intent, ts, bar_index)
        self.pending_entries.append(order)
        return order

    def _cancel(self, order_id: str) -> None:
        for queue in (self.pending_entries, self.active_brackets):
            for order in queue:
                if order.id == order_id:
                    order.state = "cancelled"
                    queue.remove(order)
                    return

    # --- Fill resolution ---

    def resolve_pending_entries(self, current_bar: Bar) -> list[Fill]:
        """Fill orders submitted on the previous bar at THIS bar's open.

        Slippage: market orders fill `slippage_ticks` worse than open
        (above for buys, below for sells). Commission charged once per
        contract on the entry.
        """
        fills: list[Fill] = []
        if not self.pending_entries:
            return fills

        slippage = self.config.slippage_ticks * self.config.tick_size

        for order in list(self.pending_entries):
            if isinstance(order.intent, MarketEntry):
                side = order.intent.side
                qty = order.intent.qty
                fill_price = current_bar.open + slippage * side.sign
                fill = Fill(
                    order_id=order.id,
                    ts=current_bar.ts_event,
                    side=side,
                    qty=qty,
                    price=fill_price,
                    commission=qty * self.config.commission_per_contract,
                    is_entry=True,
                    fill_confidence="exact",
                    reason="market",
                )
                fills.append(fill)
                order.entry_fill = fill
                order.state = "filled"
            elif isinstance(order.intent, BracketOrder):
                side = order.intent.side
                qty = order.intent.qty
                fill_price = current_bar.open + slippage * side.sign
                fill = Fill(
                    order_id=order.id,
                    ts=current_bar.ts_event,
                    side=side,
                    qty=qty,
                    price=fill_price,
                    commission=qty * self.config.commission_per_contract,
                    is_entry=True,
                    fill_confidence="exact",
                    reason="market",
                )
                fills.append(fill)
                order.entry_fill = fill
                order.state = "active"
                self.active_brackets.append(order)

        # Everything pending is now either filled or active.
        self.pending_entries.clear()
        return fills

    def resolve_active_brackets(self, current_bar: Bar) -> list[Fill]:
        """Check live brackets against the current bar's range.

        For each bracket: did the bar touch the stop, the target, both,
        or neither? Both = ambiguous, conservative -> stop wins.
        """
        fills: list[Fill] = []
        if not self.active_brackets:
            return fills

        for order in list(self.active_brackets):
            assert isinstance(order.intent, BracketOrder)
            entry = order.entry_fill
            assert entry is not None

            stop = order.intent.stop_price
            target = order.intent.target_price

            stop_touched = current_bar.low <= stop <= current_bar.high
            target_touched = current_bar.low <= target <= current_bar.high

            if not stop_touched and not target_touched:
                continue

            qty = order.intent.qty
            exit_side = order.intent.side.opposite

            if stop_touched and target_touched:
                # Conservative: stop wins on ambiguous bar.
                fill_price = stop
                confidence = "conservative"
                reason = "stop"
            elif stop_touched:
                fill_price = stop
                confidence = "exact"
                reason = "stop"
            else:
                fill_price = target
                confidence = "exact"
                reason = "target"

            fill = Fill(
                order_id=order.id,
                ts=current_bar.ts_event,
                side=exit_side,
                qty=qty,
                price=fill_price,
                commission=qty * self.config.commission_per_contract,
                is_entry=False,
                fill_confidence=confidence,
                reason=reason,
            )
            fills.append(fill)
            order.state = "filled"
            self.active_brackets.remove(order)

        return fills

    # --- Forced exits ---

    def force_close_at(
        self, current_bar: Bar, reason: str = "eod_flatten"
    ) -> list[Fill]:
        """Close any active brackets at `current_bar.close`. Used on
        EOD flatten or session close when configured to flatten."""
        fills: list[Fill] = []
        for order in list(self.active_brackets):
            assert isinstance(order.intent, BracketOrder)
            qty = order.intent.qty
            fill = Fill(
                order_id=order.id,
                ts=current_bar.ts_event,
                side=order.intent.side.opposite,
                qty=qty,
                price=current_bar.close,
                commission=qty * self.config.commission_per_contract,
                is_entry=False,
                fill_confidence="exact",
                reason=reason,
            )
            fills.append(fill)
            order.state = "filled"
            self.active_brackets.remove(order)
        return fills
