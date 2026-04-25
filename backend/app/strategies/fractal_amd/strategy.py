"""Fractal AMD Strategy class -- engine plug-in entry point (scaffold).

Scaffold only. The strategy is wired up correctly (resolves via
`runner._resolve_strategy("fractal_amd")`, runs without crashing,
respects the engine's bar-event flow) but emits no orders. The signal
functions in `signals.py` are stubs that return None / [] / False --
filling them in is the multi-session port.

What's already correct here:
- Multi-instrument: declares NQ as primary, ES + YM as aux. The engine
  refreshes `context.aux` per primary bar (added in commit b14770a).
- Setup state machine: list of `Setup` objects survives across bars
  via `self.setups` so future port can implement WATCHING -> TOUCHED
  -> FILLED transitions without restructuring the class.
- Entry-window gate: the only piece of real logic that's wired today,
  via `is_in_entry_window`. Pure function, lookahead-safe.

What's NOT here yet:
- Setup detection (HTF candles + SMT divergence). Stubbed in
  `signals.detect_smt_rejection`.
- FVG detection on resampled LTF bars (5m/15m). Stubbed in
  `signals.detect_fvg`.
- Touch-based entry. Stubbed in `signals.check_touch`.
- Risk sizing (stop placement at FVG edge, target = entry +/- TARGET_R * risk).
- Daily state persistence (trades_today counter, dedup set).

Each gap maps to a numbered TODO below so the port can be tracked
chunk by chunk.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from app.backtest.strategy import Bar, Context, Strategy
from app.strategies.fractal_amd.config import FractalAMDConfig
from app.strategies.fractal_amd.signals import (
    Setup,
    is_in_entry_window,
)

if TYPE_CHECKING:
    from app.backtest.orders import Fill, OrderIntent


class FractalAMD(Strategy):
    """Fractal AMD multi-instrument strategy plugin.

    Engine resolves this via `runner._resolve_strategy("fractal_amd")`.
    """

    name: str = "fractal_amd"

    def __init__(self, config: FractalAMDConfig):
        self.config = config
        # Setup state survives across bars; the eventual port mutates
        # this list as setups transition WATCHING -> TOUCHED -> FILLED.
        self.setups: list[Setup] = []
        # Per-day counters. Reset by `_maybe_roll_day` on the first bar
        # of each new ET trading day.
        self.today: dt.date | None = None
        self.trades_today: int = 0
        # Dedup: same FVG = one setup per day. Live bot uses a set keyed
        # by (direction, fvg_low, fvg_high); mirror that here.
        self.entries_today: set[tuple[str, float, float]] = set()

    # ------------------------------------------------------------------
    # Engine lifecycle
    # ------------------------------------------------------------------

    def on_start(self, context: Context) -> None:
        """Called once before the first bar."""
        self.setups = []
        self.today = None
        self.trades_today = 0
        self.entries_today = set()

    def on_bar(self, bar: Bar, context: Context) -> "list[OrderIntent]":
        """Called for each primary (NQ) bar.

        Aux bars (ES, YM) are available via `context.aux[symbol]`.
        Returns OrderIntents to submit this bar.
        """
        self._maybe_roll_day(bar.ts_event)

        # Hard caps before any signal work.
        if self.trades_today >= self.config.max_trades_per_day:
            return []

        # TODO #1: scan_for_setups (HTF + SMT detection)
        # TODO #2: validate_pending_setups (LTF FVG resolution)
        # TODO #3: check_touch on watching setups
        # TODO #4: emit BracketOrder when a TOUCHED setup is confirmed
        #          and inside the entry window.

        # The only real check that's safe to wire today: the entry-window
        # gate. Stays as a no-op until setups exist to gate.
        _ = is_in_entry_window(
            bar.ts_event,
            open_hour=self.config.rth_open_hour,
            open_min=self.config.rth_open_min,
            close_hour=self.config.max_entry_hour,
        )

        return []

    def on_fill(self, fill: "Fill", context: Context) -> None:
        """Called when one of our orders fills (entry or exit)."""
        # TODO #5: when a fill closes a position, increment
        #          `trades_today` and update setup status.
        if not fill.is_entry:
            self.trades_today += 1

    def on_end(self, context: Context) -> None:
        """Called once after the last bar."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _maybe_roll_day(self, now: dt.datetime) -> None:
        """Reset per-day state on the first bar of a new trading day.

        Day boundary is the bar's UTC date for now. The trusted live
        bot uses ET; switching is a TODO for when we wire session
        boundaries correctly.
        """
        today = now.date()
        if self.today != today:
            self.today = today
            self.trades_today = 0
            self.entries_today = set()
            # Setups carry over: HTF candles formed yesterday are still
            # valid scaffolding for today's entries (live bot keeps a
            # 25-hour buffer for exactly this reason).

    # ------------------------------------------------------------------
    # Constructor compatibility with runner._resolve_strategy
    # ------------------------------------------------------------------

    @classmethod
    def from_config(
        cls, params: dict, *, tick_size: float, qty: int
    ) -> "FractalAMD":
        """Build a FractalAMD instance from a RunConfig.params dict.

        `tick_size` and `qty` are accepted for parity with
        MovingAverageCrossover.from_config. They aren't used yet --
        the port will use them for stop placement and contract sizing.
        """
        del tick_size, qty
        return cls(FractalAMDConfig.from_params(params))
