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
    """

    side: Side
    qty: int
    stop_price: float
    target_price: float


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
