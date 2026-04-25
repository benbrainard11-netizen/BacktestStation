"""Strategy interface + bar/context dataclasses.

Strategies receive bars + a context object and return order intents.
That's the entire contract. Keeping it that small forces the engine
to own everything else (fills, positions, equity, metrics, timing).

To add a new strategy: subclass `Strategy`, implement `on_bar`, drop
the file under `backend/app/strategies/`. See
`docs/BACKTEST_ENGINE.md` for the full how-to.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.backtest.orders import Fill, OrderIntent, Side


@dataclass(frozen=True)
class Bar:
    """One OHLCV bar. The Strategy only ever sees the current bar.

    Frozen so strategies can't mutate it. Fields mirror the bar parquet
    written by `app.ingest.parquet_mirror`.
    """

    ts_event: dt.datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    trade_count: int
    vwap: float


@dataclass
class Position:
    """An open position the engine is tracking."""

    side: "Side"
    qty: int
    entry_price: float
    entry_ts: dt.datetime
    stop_price: float | None
    target_price: float | None
    unrealized_pnl: float = 0.0


@dataclass
class Context:
    """The runtime view a Strategy sees on each bar.

    Read-only from the strategy's perspective (we don't enforce this
    via Frozen but the convention is: never mutate `context.*` from
    the strategy). The engine updates it before each `on_bar` call.

    `history` is a *suffix* of bars seen so far, capped at
    `history_max` so memory doesn't blow up over long backtests. Use
    it for indicators (moving averages, etc.). It NEVER contains the
    current bar's future or any later bar — that's what prevents
    lookahead.
    """

    now: dt.datetime
    bar_index: int  # zero-indexed bar number
    equity: float
    initial_equity: float
    position: Position | None
    history: list[Bar] = field(default_factory=list)
    history_max: int = 1000

    @property
    def in_position(self) -> bool:
        return self.position is not None


class Strategy:
    """Base class for backtest strategies.

    The interface is intentionally tiny:

      - on_start(context):   called once before the first bar
      - on_bar(bar, context):  called for each bar; return order intents
      - on_fill(fill, context):  called when one of your orders fills
      - on_end(context):     called once after the last bar

    Subclasses override `name` and `on_bar` at minimum. The default
    implementations of the other methods are no-ops.

    Strategies must NOT:
      - read the database
      - read the filesystem (other than their own state)
      - make HTTP / network calls
      - import time-of-day from `datetime.now()` (use context.now)
      - look at any bar past `bar.ts_event` (use context.history)

    Following these rules keeps strategies deterministic, reproducible,
    and lookahead-safe.
    """

    name: str = "unnamed_strategy"

    def on_start(self, context: Context) -> None:
        """Called once before the first bar. Use to initialize state."""

    def on_bar(self, bar: Bar, context: Context) -> "list[OrderIntent]":
        """Called for each bar. Return any orders you want to submit."""
        return []

    def on_fill(self, fill: "Fill", context: Context) -> None:
        """Called when one of your orders fills (entry or exit)."""

    def on_end(self, context: Context) -> None:
        """Called once after the last bar. Use to clean up state."""
