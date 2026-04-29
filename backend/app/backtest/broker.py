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

    def resolve_pending_entries(
        self, current_bar: Bar, bar_index: int | None = None
    ) -> list[Fill]:
        """Fill orders submitted on the previous bar at THIS bar's open.

        Slippage: market orders fill `slippage_ticks` worse than open
        (above for buys, below for sells). Commission charged once per
        contract on the entry.

        `bar_index` is the engine's bar counter for `current_bar`. When
        provided, it's stamped onto the order so `resolve_active_brackets`
        can compute bars-held for `BracketOrder.max_hold_bars` timeouts.
        Defaulted to `None` to keep the older single-arg call sites
        green; existing tests don't drive max_hold so the absence is fine.
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
                order.entry_bar_index = bar_index
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
                order.entry_bar_index = bar_index
                order.state = "active"
                self.active_brackets.append(order)

        # Everything pending is now either filled or active.
        self.pending_entries.clear()
        return fills

    def fill_immediate_brackets(
        self, current_bar: Bar, bar_index: int
    ) -> list[Fill]:
        """Fill any pending brackets with `fill_immediately=True` at THIS
        bar's open. Called by the engine right after `strategy.on_bar`
        returns intents — lets a strategy decide based on this bar's
        full data and have the order fill at this bar's open instead of
        next bar's. Mirrors trusted Fractal AMD's "decide on bar T+1's
        open with prior touch knowledge from T, enter at T+1.open"
        pattern.

        Slippage applied identically to next-bar fills. The bracket is
        added to `active_brackets`; stop/target watching starts on the
        NEXT bar — `resolve_active_brackets` skips orders whose
        entry_bar_index equals the current bar_index, so the entry bar
        itself isn't checked against the bracket levels (which would be
        same-bar look-ahead with OHLC-only data).
        """
        fills: list[Fill] = []
        if not self.pending_entries:
            return fills
        slippage = self.config.slippage_ticks * self.config.tick_size
        remaining: list[Order] = []
        for order in self.pending_entries:
            if not (
                isinstance(order.intent, BracketOrder)
                and order.intent.fill_immediately
            ):
                remaining.append(order)
                continue
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
            order.entry_bar_index = bar_index
            order.state = "active"
            self.active_brackets.append(order)
        self.pending_entries = remaining
        return fills

    def resolve_active_brackets(
        self, current_bar: Bar, bar_index: int | None = None
    ) -> list[Fill]:
        """Check live brackets against the current bar's range.

        For each bracket: did the bar touch the stop, the target, both,
        or neither? Both = ambiguous, conservative -> stop wins.

        Also enforces `BracketOrder.max_hold_bars` timeouts when
        `bar_index` is provided: a bracket whose position has been held
        for `max_hold_bars` bars (i.e., `bar_index - entry_bar_index >=
        max_hold_bars`) and hasn't hit stop or target on this bar
        force-closes at the bar's close with `reason="timeout"`. Mirrors
        the trusted Fractal AMD `MAX_HOLD=120` exit. `bar_index=None`
        keeps existing tests green by skipping the timeout check
        entirely.
        """
        fills: list[Fill] = []
        if not self.active_brackets:
            return fills

        for order in list(self.active_brackets):
            assert isinstance(order.intent, BracketOrder)
            entry = order.entry_fill
            assert entry is not None

            # Skip same-bar range check on the entry bar of an
            # immediate-fill bracket. The order filled at this bar's
            # open; checking this bar's high/low for stop/target hit
            # would be same-bar look-ahead. Standard next-bar-fill
            # brackets keep their existing behavior (entry on bar N's
            # open, stop/target check on bar N's range happens because
            # the strategy already had bar N-1's full info when
            # submitting; the engine has always done it this way).
            if (
                order.intent.fill_immediately
                and order.entry_bar_index == bar_index
            ):
                continue

            stop = order.intent.stop_price
            target = order.intent.target_price

            stop_touched = current_bar.low <= stop <= current_bar.high
            target_touched = current_bar.low <= target <= current_bar.high

            # MAX_HOLD timeout check. If the bracket has been held for
            # `max_hold_bars` bars and neither stop nor target touched
            # on this bar, force-close at the bar's close. Stop/target
            # checks above still take precedence on the timeout bar
            # itself — if either hit, that's the exit reason.
            if not stop_touched and not target_touched:
                max_hold = order.intent.max_hold_bars
                if (
                    max_hold is not None
                    and bar_index is not None
                    and order.entry_bar_index is not None
                    and bar_index - order.entry_bar_index >= max_hold
                ):
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
                        reason="timeout",
                    )
                    fills.append(fill)
                    order.state = "filled"
                    self.active_brackets.remove(order)
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
