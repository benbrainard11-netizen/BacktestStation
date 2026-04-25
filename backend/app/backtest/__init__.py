"""BacktestStation backtest engine.

Pure event-driven engine that takes bars in, runs a Strategy plugin,
and produces trades + equity + events + metrics. No DB or filesystem
side effects inside `engine.py` — those belong in `runner.py`.

Key entrypoints:

    from app.backtest import run, RunConfig
    from app.backtest.strategy import Strategy

See `docs/BACKTEST_ENGINE.md` for architecture and how to add a new
strategy.
"""

from app.backtest.engine import BacktestResult, RunConfig, run
from app.backtest.events import Event, EventType
from app.backtest.metrics import compute_metrics
from app.backtest.orders import (
    BracketOrder,
    CancelOrder,
    Fill,
    MarketEntry,
    OrderIntent,
    Side,
    Trade,
)
from app.backtest.strategy import Bar, Context, Position, Strategy

ENGINE_VERSION = "1"

__all__ = [
    "Bar",
    "BacktestResult",
    "BracketOrder",
    "CancelOrder",
    "Context",
    "ENGINE_VERSION",
    "Event",
    "EventType",
    "Fill",
    "MarketEntry",
    "OrderIntent",
    "Position",
    "RunConfig",
    "Side",
    "Strategy",
    "Trade",
    "compute_metrics",
    "run",
]
