"""Order intents, orders, fills, and trades.

Strategies emit `OrderIntent`s. The engine converts them into
materialized `Order`s, attempts to fill them against subsequent
bars, and records `Fill`s. Closed positions become `Trade`s.

The split between intent (what the strategy wants) and order (what
the engine is tracking) lets us keep strategies dumb and the engine
the only thing that knows about fills, slippage, and timing.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from enum import Enum


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"

    @property
    def opposite(self) -> "Side":
        return Side.SHORT if self is Side.LONG else Side.LONG

    @property
    def sign(self) -> int:
        """+1 for long, -1 for short. Used for PnL math."""
        return 1 if self is Side.LONG else -1


# --- Strategy-emitted intents -------------------------------------------


@dataclass(frozen=True)
class MarketEntry:
    """Open a market position next bar at the open + slippage."""

    side: Side
    qty: int


@dataclass(frozen=True)
class BracketOrder:
    """Market entry + atomic OCO stop and target.

    The engine fills the entry on the next bar's open, then watches
    subsequent bars for stop or target. Per CLAUDE.md §8, when a bar
    contains both stop and target levels, the conservative default is
    that the stop wins and `Fill.fill_confidence = "conservative"`.

    `contract_value` overrides the run-wide `RunConfig.contract_value`
    for this order's PnL math. Set this when a strategy wants to
    downshift to a different contract on a per-trade basis (e.g.
    Fractal AMD switching from NQ at $20/pt to MNQ at $2/pt for
    wide-stop setups so dollar risk stays inside the configured cap).
    `None` means use the run config's value.

    `max_hold_bars`: if set, the bracket force-closes at the bar's close
    once `bar_index - entry_bar_index >= max_hold_bars` (i.e., the
    position has been held for `max_hold_bars` complete bars after the
    entry-fill bar). The exit fill is recorded with `reason="timeout"`
    and `fill_confidence="exact"`. Mirrors `MAX_HOLD=120` in the trusted
    Fractal AMD backtest. `None` (default) = no timeout.

    `fill_immediately`: when True, the broker fills the entry on the
    SAME bar the order is submitted (at that bar's open + slippage)
    rather than next bar. Stop/target watch starts from the NEXT bar
    onward — the entry bar itself is excluded from the bracket-resolve
    range check because bar.open is the entry price and you can't
    legitimately stop or target on the same bar with OHLC-only data.
    Mirrors trusted Fractal AMD's "wait for touch on bar T, decide+enter
    on bar T+1's open" pattern, where the strategy decides during
    on_bar(T+1) using prior touch + this bar's full data and enters at
    T+1.open. `False` (default) = standard next-bar fill.
    """

    side: Side
    qty: int
    stop_price: float
    target_price: float
    contract_value: float | None = None
    max_hold_bars: int | None = None
    fill_immediately: bool = False


@dataclass(frozen=True)
class CancelOrder:
    """Cancel a pending order by id."""

    order_id: str


# Discriminated union the strategy may return.
OrderIntent = MarketEntry | BracketOrder | CancelOrder


# --- Engine-tracked orders (post-materialization) -----------------------


@dataclass
class Order:
    """An intent that the engine has accepted and is tracking.

    Has a stable id, the bar at which it was submitted, and progresses
    through pending -> filled (or cancelled). Bracket orders track
    their entry fill separately so the stop/target legs can stay
    pending until the entry actually fills.
    """

    id: str
    intent: OrderIntent
    submitted_at: dt.datetime
    submitted_bar_index: int
    state: str = "pending"  # pending | active | filled | cancelled
    entry_fill: "Fill | None" = None
    # Bar index at which the entry fill happened (the bar where the
    # market open was used as the fill price). Set by `resolve_pending_entries`
    # so that `resolve_active_brackets` can compute bars-held for the
    # `BracketOrder.max_hold_bars` timeout. None until the entry fills.
    entry_bar_index: int | None = None

    @staticmethod
    def new(
        intent: OrderIntent, ts: dt.datetime, bar_index: int
    ) -> "Order":
        return Order(
            id=uuid.uuid4().hex[:12],
            intent=intent,
            submitted_at=ts,
            submitted_bar_index=bar_index,
        )


# --- Fills + trades -----------------------------------------------------


@dataclass(frozen=True)
class Fill:
    """One fill event. Either the entry leg of a position or its exit."""

    order_id: str
    ts: dt.datetime
    side: Side
    qty: int
    price: float
    commission: float
    is_entry: bool  # True for opening fills, False for closing
    fill_confidence: str = "exact"  # exact | conservative | ambiguous
    reason: str = ""  # "market", "stop", "target", "eod_flatten", "manual"


@dataclass(frozen=True)
class Trade:
    """A round-trip: entry fill + exit fill on the same position.

    The engine constructs this when a position closes. PnL is in
    contract-currency-units (raw price diff * qty - commissions);
    risk_unit is the per-contract dollar risk used to compute r_multiple.
    """

    entry_ts: dt.datetime
    exit_ts: dt.datetime
    side: Side
    qty: int
    entry_price: float
    exit_price: float
    stop_price: float | None
    target_price: float | None
    pnl: float
    r_multiple: float | None
    exit_reason: str  # "stop" | "target" | "eod" | "manual" | "opposite_signal"
    fill_confidence: str
    tags: list[str] = field(default_factory=list)
