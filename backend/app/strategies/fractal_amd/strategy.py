"""Fractal AMD Strategy class -- engine plug-in entry point.

Chunks 1+2 of the port. Detects HTF stage signals + LTF FVG zones
+ flags WATCHING setups as TOUCHED when a primary bar enters the
zone. Does NOT yet emit orders -- chunk 3 adds entry validation
and BracketOrder emission.

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
    check_touch,
    detect_fvgs,
    detect_smt_at_level,
    get_ohlc,
    is_in_entry_window,
    resample_bars,
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

        # 4. Scan completed HTF candles for new stage signals + LTF FVGs.
        self._scan_for_setups(bar, context)

        # 5. Touch detection on WATCHING setups.
        check_touch(self.setups, bar)

        # 6. Entry-window gate is wired but not yet acted on -- the
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
                    # Walk the LTF expansion window for FVG-bearing
                    # entry candidates. Each unfilled FVG => one Setup.
                    new_setups = self._build_setups_from_ltf(
                        signal=signal,
                        bar_now=bar,
                        bars_by_asset=bars_by_asset,
                        day_et=day_et,
                    )
                    for s in new_setups:
                        if not self._is_duplicate_setup(s):
                            self.setups.append(s)
                self._last_scanned[tf] = cur_end

    def _build_setups_from_ltf(
        self,
        *,
        signal: StageSignal,
        bar_now: Bar,
        bars_by_asset: dict[str, list[Bar]],
        day_et: dt.datetime,
    ) -> list[Setup]:
        """Walk the LTF expansion window for FVG-bearing setups.

        Mirrors `live_bot.SignalEngine.scan_for_setups:395-473` --
        after an HTF stage closes, the strategy gives itself an
        expansion window of `2 * htf_duration` to look for LTF
        confirmation. Within each LTF candle pair that has same-
        direction LTF SMT, resample the underlying 1m bars and
        run FVG detection. Each unfilled FVG -> one Setup.
        """
        primary = bars_by_asset[self.config.primary_symbol]
        cs, ce = signal.candle_start, signal.candle_end
        exp_s = ce
        exp_e = exp_s + (ce - cs) * 2

        new_setups: list[Setup] = []

        for ltf_tf, ltf_min in (("15m", 15), ("5m", 5)):
            ltf_candles = candle_bounds(day_et, ltf_tf)
            # Restrict to expansion window AND completed candles.
            rel = [
                (s, e) for s, e in ltf_candles
                if s >= exp_s
                and e <= exp_e + dt.timedelta(minutes=1)
                and e <= bar_now.ts_event
            ]
            for li in range(1, len(rel)):
                lcs, lce = rel[li]
                lrs, lre = rel[li - 1]

                # LTF SMT: same direction as the HTF stage
                ref_ohlc = {
                    sym: get_ohlc(bars, lrs, lre)
                    for sym, bars in bars_by_asset.items()
                }
                if any(v is None for v in ref_ohlc.values()):
                    continue
                if signal.direction == "BEARISH":
                    levels = {sym: ref_ohlc[sym].high for sym in bars_by_asset}
                    smt = detect_smt_at_level(
                        bars_by_asset, levels, "high", lcs, lce
                    )
                    if not (smt.has_smt and smt.direction == "BEARISH"):
                        continue
                else:
                    levels = {sym: ref_ohlc[sym].low for sym in bars_by_asset}
                    smt = detect_smt_at_level(
                        bars_by_asset, levels, "low", lcs, lce
                    )
                    if not (smt.has_smt and smt.direction == "BULLISH"):
                        continue

                # FVG detection on RESAMPLED LTF bars (the 2026-04-10 fix).
                fvg_window_start = lrs
                fvg_window_end = min(
                    lce + dt.timedelta(minutes=ltf_min * 5),
                    bar_now.ts_event,
                )
                primary_window = [
                    b for b in primary
                    if fvg_window_start <= b.ts_event < fvg_window_end
                ]
                if len(primary_window) < ltf_min * 3:
                    continue
                ltf_bars = resample_bars(primary_window, ltf_min)
                if len(ltf_bars) < 3:
                    continue
                fvgs = detect_fvgs(
                    ltf_bars, signal.direction, min_gap_pct=0.3, expiry_bars=60
                )
                for fvg in fvgs:
                    if fvg.filled:
                        continue
                    new_setups.append(
                        Setup(
                            direction=signal.direction,
                            htf_tf=signal.timeframe,
                            htf_candle_start=cs,
                            htf_candle_end=ce,
                            ltf_tf=ltf_tf,
                            ltf_candle_end=lce,
                            fvg_high=fvg.high,
                            fvg_low=fvg.low,
                            fvg_mid=fvg.mid,
                        )
                    )
        return new_setups

    def _is_duplicate_setup(self, s: Setup) -> bool:
        """Same FVG zone (rounded) per direction + tf+ltf = one setup
        per day -- mirrors live_bot.scan_for_setups:479-489 dedupe.
        """
        key = (
            s.direction,
            s.htf_tf,
            s.ltf_tf,
            round(s.fvg_low, 4),
            round(s.fvg_high, 4),
        )
        for existing in self.setups:
            ekey = (
                existing.direction,
                existing.htf_tf,
                existing.ltf_tf,
                round(existing.fvg_low, 4),
                round(existing.fvg_high, 4),
            )
            if key == ekey:
                return True
        return False

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
