"""Fractal AMD Strategy class -- engine plug-in entry point.

Chunks 1+2+3 of the port. Detects HTF stage signals + LTF FVG zones,
flags WATCHING setups as TOUCHED on bar intersection, then validates
TOUCHED setups (entry window + risk gate + dedup) and emits
BracketOrders. End-to-end: bars -> setup -> FVG -> touch -> trade.

Continuation-OF gate is config-controlled; defaults to off until
the OHLCV-delta proxy is implemented (live_bot computes it from
order-flow data we don't have at bar level).
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from app.backtest.orders import BracketOrder, OrderIntent, Side
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
    from app.backtest.orders import Fill


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
        # Candles we no longer need to re-scan because their entire
        # expansion window is in the past. Keyed by (tf, cur_start_iso).
        self._fully_scanned: set[tuple[str, str]] = set()

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
        self._fully_scanned = set()

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

        # 6. Entry validation + BracketOrder emission. Only one entry
        # per bar (live bot serializes too); the trades_today cap +
        # entry_dedup gate already enforce most of the cardinality
        # we want.
        bar_et = bar.ts_event.astimezone(ET)
        if not is_in_entry_window(
            bar_et,
            open_hour=self.config.rth_open_hour,
            open_min=self.config.rth_open_min,
            close_hour=self.config.max_entry_hour,
        ):
            return []

        if context.position is not None:
            return []  # one position at a time

        intent = self._try_emit_entry(bar)
        return [intent] if intent is not None else []

    def on_fill(self, fill: "Fill", context: Context) -> None:
        # trades_today is incremented in _try_emit_entry on intent emit
        # (mirrors live bot: counter bumps when the entry is committed,
        # not when it later fills/exits). Nothing to do here yet --
        # future chunks may track per-fill stats for performance metrics.
        return None

    def on_end(self, context: Context) -> None:
        pass

    # ------------------------------------------------------------------
    # Setup detection
    # ------------------------------------------------------------------

    def _scan_for_setups(self, bar: Bar, context: Context) -> None:
        """Scan completed HTF candles for new stage signals + LTF setups.

        Re-scans every HTF candle pair whose **expansion window is still
        active**. Live bot's `scan_for_setups` re-scans everything every
        minute; we trim the work to "candles whose expansion window
        could still yield new setups."

        Two reasons re-scan is load-bearing (vs. the original
        scan-once-on-close):

        1. When an HTF candle CLOSES, its LTF expansion window has not
           yet closed -- so building setups would find no FVGs. Live bot
           returns to that HTF candle on later bars when more LTF
           candles have completed.
        2. FVG zones can shift as more LTF data fills in.

        Once expansion is fully behind us
        (`exp_end + small_buffer <= bar.ts_event`), the candle is
        recorded as `_fully_scanned` and skipped on subsequent bars.
        """
        bars_by_asset = self._bars_by_asset(context)
        if any(len(b) == 0 for b in bars_by_asset.values()):
            return

        # Globex trading day in ET. Day boundary is 18:00 ET prior day
        # -> 17:00 ET current day.
        bar_et = bar.ts_event.astimezone(ET)
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
                # Only inspect closed HTF candles.
                if cur_end > bar.ts_event:
                    continue  # not closed yet

                # Skip if expansion window is fully behind us.
                key = (tf, cur_start.isoformat())
                if key in self._fully_scanned:
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

                # Compute expansion window end for the perf gate.
                exp_end = cur_end + (cur_end - cur_start) * 2

                if signal is not None:
                    if not self._stage_signal_seen(signal):
                        self.stage_signals.append(signal)
                    new_setups = self._build_setups_from_ltf(
                        signal=signal,
                        bar_now=bar,
                        bars_by_asset=bars_by_asset,
                        day_et=day_et,
                    )
                    for s in new_setups:
                        if not self._is_duplicate_setup(s):
                            self.setups.append(s)

                # Once the entire expansion window is in the past, we'll
                # never produce a new setup from this candle -- record
                # it so we stop re-scanning.
                if exp_end <= bar.ts_event:
                    self._fully_scanned.add(key)

    def _stage_signal_seen(self, signal: StageSignal) -> bool:
        """Idempotent stage-signal recording. Identity = (tf, cur_start,
        direction). Same identity twice = same logical signal."""
        for existing in self.stage_signals:
            if (
                existing.timeframe == signal.timeframe
                and existing.candle_start == signal.candle_start
                and existing.direction == signal.direction
            ):
                return True
        return False

    def _try_emit_entry(self, bar: Bar) -> OrderIntent | None:
        """Pick the best TOUCHED setup and emit a BracketOrder.

        Validation:
        - Setup status == TOUCHED
        - Touched within `entry_max_bars_after_touch` bars
        - Risk in [min_risk_pts, max_risk_pts]
        - 15-min direction dedup (entries_today)

        On a successful emit, the setup is marked FILLED (won't re-fire)
        and `entries_today` is updated. On a failure that's terminal
        (out-of-window touch / risk fail / dedup hit), the setup is
        reset to WATCHING so the same FVG can re-touch.
        """
        # Find candidate touched setups.
        touched = [s for s in self.setups if s.status == "TOUCHED"]
        if not touched:
            return None

        # Pick the most recently touched (live bot semantics: fire on the
        # bar after the touch).
        touched.sort(key=lambda s: s.touch_bar_time or dt.datetime.min, reverse=True)

        for setup in touched:
            outcome = self._validate_and_build_intent(setup, bar)
            if outcome is None:
                # Validation failed terminally -> reset to WATCHING and try the next.
                setup.status = "WATCHING"
                setup.touch_bar_time = None
                continue
            intent, dedup_key = outcome
            setup.status = "FILLED"
            self.entries_today.add(dedup_key)
            self.trades_today += 1
            return intent
        return None

    def _validate_and_build_intent(
        self, setup: Setup, bar: Bar
    ) -> tuple[OrderIntent, tuple[str, dt.datetime]] | None:
        """Validate one TOUCHED setup; build a BracketOrder if it passes.

        Returns (intent, dedup_key) on success, None on terminal fail
        (caller resets setup to WATCHING).
        """
        # Touch-age cap: if the touch bar is too far behind, treat the
        # setup as stale and reset.
        if setup.touch_bar_time is None:
            return None
        bars_since_touch = max(
            0,
            int(
                (bar.ts_event - setup.touch_bar_time).total_seconds() // 60
            ),
        )
        if bars_since_touch > self.config.entry_max_bars_after_touch:
            return None
        # Don't fire on the touch bar itself -- entry happens on the
        # NEXT bar (mirrors live bot's bar-after-touch semantics, and
        # avoids look-ahead within the touch bar).
        if bars_since_touch < 1:
            return None

        # Compute entry / stop / target.
        # Entry approximates the bar.open since the engine will fill
        # the bracket order at next bar's open + slippage anyway.
        if setup.direction == "BEARISH":
            side = Side.SHORT
            entry_price = bar.open
            stop = setup.fvg_high + self.config.stop_buffer_pts
            risk = stop - entry_price
            target = entry_price - risk * self.config.target_r
        else:
            side = Side.LONG
            entry_price = bar.open
            stop = setup.fvg_low - self.config.stop_buffer_pts
            risk = entry_price - stop
            target = entry_price + risk * self.config.target_r

        # Risk validation in points.
        if risk <= 0 or risk > self.config.max_risk_pts:
            return None
        if risk < self.config.min_risk_pts:
            return None

        # 15-min direction dedup.
        bar_et = bar.ts_event.astimezone(ET)
        bucket_minute = (
            bar_et.minute // self.config.entry_dedup_minutes
        ) * self.config.entry_dedup_minutes
        bucket = bar_et.replace(minute=bucket_minute, second=0, microsecond=0)
        dedup_key = (setup.direction, bucket)
        if dedup_key in self.entries_today:
            return None

        intent = BracketOrder(
            side=side,
            qty=1,
            stop_price=stop,
            target_price=target,
        )
        return intent, dedup_key

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
