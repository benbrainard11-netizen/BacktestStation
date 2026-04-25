"""Fractal AMD Strategy class -- engine plug-in entry point.

Chunk 1 of the port. Detects HTF stage signals (SMT divergence +
rejection candles at session/1H granularity) and accumulates
`self.setups`. Does NOT yet emit orders -- FVG detection (chunk 2)
+ check_touch + entry validation (chunk 3) come next.

Multi-instrument is wired: NQ primary, ES + YM aux. Per-bar aux
history is accumulated in `self.aux_history` because the engine
only exposes the CURRENT aux bar via `context.aux`. SMT detection
needs HISTORY across all three.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from app.backtest.strategy import Bar, Context, Strategy
from app.strategies.fractal_amd.config import FractalAMDConfig
from app.strategies.fractal_amd.signals import (
    ET,
    Setup,
    StageSignal,
    candle_bounds,
    check_candle_pair,
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
        # Detected setups (HTF stage confirmations). Chunk 2 promotes
        # these to TOUCHED, chunk 3 emits BracketOrders.
        self.setups: list[Setup] = []
        # Raw stage signals (debug + downstream FVG search root).
        self.stage_signals: list[StageSignal] = []
        # Per-day counters.
        self.today: dt.date | None = None
        self.trades_today: int = 0
        self.entries_today: set[tuple[str, float, float]] = set()
        # Per-aux-symbol bar history. The engine only exposes the
        # current bar via context.aux; SMT detection needs prior
        # bars too, so we accumulate here.
        self.aux_history: dict[str, list[Bar]] = {}
        # High-water mark per HTF tf so we don't re-scan completed
        # candles every bar. Maps tf -> end_ts of the last scanned
        # candle.
        self._last_scanned: dict[str, dt.datetime] = {}

    # ------------------------------------------------------------------
    # Engine lifecycle
    # ------------------------------------------------------------------

    def on_start(self, context: Context) -> None:
        self.setups = []
        self.stage_signals = []
        self.today = None
        self.trades_today = 0
        self.entries_today = set()
        self.aux_history = {sym: [] for sym in self.config.aux_symbols}
        self._last_scanned = {}

    def on_bar(self, bar: Bar, context: Context) -> "list[OrderIntent]":
        # 1. Accumulate aux history.
        for sym in self.config.aux_symbols:
            aux_bar = context.aux.get(sym)
            if aux_bar is not None:
                self.aux_history.setdefault(sym, []).append(aux_bar)

        # 2. Roll day counters if we crossed a trading-day boundary.
        self._maybe_roll_day(bar.ts_event)

        # 3. Hard cap.
        if self.trades_today >= self.config.max_trades_per_day:
            return []

        # 4. Scan completed HTF candles for new stage signals.
        self._scan_for_setups(bar, context)

        # 5. Entry-window gate is wired but not yet acted on -- the
        # strategy still emits no orders this chunk. Acted on in
        # chunk 3.
        _ = is_in_entry_window(
            bar.ts_event,
            open_hour=self.config.rth_open_hour,
            open_min=self.config.rth_open_min,
            close_hour=self.config.max_entry_hour,
        )

        return []

    def on_fill(self, fill: "Fill", context: Context) -> None:
        # Increment daily counter on exit fills (entries don't count
        # toward the cap until they close per trusted-bot semantics).
        if not fill.is_entry:
            self.trades_today += 1

    def on_end(self, context: Context) -> None:
        pass

    # ------------------------------------------------------------------
    # Setup detection
    # ------------------------------------------------------------------

    def _scan_for_setups(self, bar: Bar, context: Context) -> None:
        """Scan completed HTF candles for new stage signals.

        Runs every primary bar but only inspects HTF candles whose
        end <= current bar's ts_event (so we never look ahead). For
        each new completed HTF candle, check the (current, prior)
        pair via `check_candle_pair`; on a confirmed signal, record
        a StageSignal. Setup objects (with FVG fields) get built in
        chunk 2 once we know how to detect the FVG zone within the
        confirmed candle.
        """
        bars_by_asset = self._bars_by_asset(context)
        # Need at least two HTF candles' worth of bars on every asset.
        if any(len(b) == 0 for b in bars_by_asset.values()):
            return

        # The current trading day in ET.
        bar_et = bar.ts_event.astimezone(ET)
        # Globex day boundary: 18:00 ET prior day -> 17:00 ET current
        # day. If bar is before 18:00 ET, the trading day is "today
        # (ET calendar)"; if at/after 18:00 ET, the trading day is
        # tomorrow.
        if bar_et.hour >= 18:
            day_et = (bar_et + dt.timedelta(days=1)).replace(
                hour=12, minute=0, second=0, microsecond=0
            )
        else:
            day_et = bar_et.replace(hour=12, minute=0, second=0, microsecond=0)

        for tf in ("session", "1H"):
            all_candles = candle_bounds(day_et, tf)
            for i, (cur_start, cur_end) in enumerate(all_candles):
                if i == 0:
                    continue  # need a prior candle for ref
                # Only act on completed candles (end <= now).
                if cur_end > bar.ts_event:
                    break
                # Skip if already scanned.
                last = self._last_scanned.get(tf)
                if last is not None and cur_end <= last:
                    continue

                ref_start, ref_end = all_candles[i - 1]
                signal = check_candle_pair(
                    bars_by_asset,
                    cur_start=cur_start,
                    cur_end=cur_end,
                    ref_start=ref_start,
                    ref_end=ref_end,
                    timeframe=tf,
                )
                if signal is not None:
                    self.stage_signals.append(signal)
                    # Record a Setup placeholder. FVG fields stay 0 --
                    # filled in chunk 2 when we add FVG detection on
                    # resampled LTF bars within the confirmed candle.
                    self.setups.append(
                        Setup(
                            direction=signal.direction,
                            htf_tf=tf,
                            htf_candle_start=cur_start,
                            htf_candle_end=cur_end,
                            ltf_tf="",  # chunk 2
                            ltf_candle_end=cur_end,
                            fvg_high=0.0,
                            fvg_low=0.0,
                            fvg_mid=0.0,
                        )
                    )
                self._last_scanned[tf] = cur_end

    def _bars_by_asset(self, context: Context) -> dict[str, list[Bar]]:
        """Build the per-asset history dict the signal helpers expect.

        Primary symbol: from context.history. Aux symbols: from the
        accumulator we maintain in on_bar.
        """
        out: dict[str, list[Bar]] = {self.config.primary_symbol: list(context.history)}
        for sym in self.config.aux_symbols:
            out[sym] = list(self.aux_history.get(sym, []))
        return out

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _maybe_roll_day(self, now: dt.datetime) -> None:
        """Reset per-day state on the first bar of a new ET trading day.

        Trading day rolls at 18:00 ET (Globex open).
        """
        et_now = now.astimezone(ET)
        # Trading day = the calendar day of the 17:00 ET close.
        if et_now.hour >= 18:
            trading_day = (et_now + dt.timedelta(days=1)).date()
        else:
            trading_day = et_now.date()
        if self.today != trading_day:
            self.today = trading_day
            self.trades_today = 0
            self.entries_today = set()

    @classmethod
    def from_config(
        cls, params: dict, *, tick_size: float, qty: int
    ) -> "FractalAMD":
        """Build a FractalAMD instance from a RunConfig.params dict.

        `tick_size` and `qty` are accepted for parity with
        MovingAverageCrossover.from_config. Used by chunk 3's stop /
        target placement.
        """
        del tick_size, qty
        return cls(FractalAMDConfig.from_params(params))
