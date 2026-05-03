"""Composable strategy plugin.

Reads a JSON spec (role-tagged feature buckets + stop/target rules)
and emits bracket orders. Per bar, per direction, the engine runs:

    setup features all pass  → arm setup window (refresh if armed)
    setup currently armed?
    trigger features all pass
    global filter + per-direction filter all pass
                             → enter

Empty `setup_<dir>` is shorthand for "always armed" — the simple,
old-shape, trigger-only flow. Day rollover (Globex 18:00→17:00 ET)
clears all armed state.
"""

from __future__ import annotations

import datetime as dt
import sys
from typing import TYPE_CHECKING, Literal
from zoneinfo import ZoneInfo

# Sentinel for "setup armed until end of trading day" (window=None case).
# Day-rollover always clears armed state, so this is bounded in practice.
_PERSISTENT_ARMED: int = sys.maxsize

from app.backtest.orders import BracketOrder, OrderIntent, Side
from app.backtest.strategy import Bar, Context, Strategy
from app.features import FEATURES, FeatureResult
from app.strategies.composable.config import (
    ComposableSpec,
    FeatureCall,
)

if TYPE_CHECKING:
    pass

ET = ZoneInfo("America/New_York")
Direction = Literal["BULLISH", "BEARISH"]


class ComposableStrategy(Strategy):
    """User-assembled strategy. See `app.strategies.composable.config`
    for the spec shape; `app.features.FEATURES` for the catalogue of
    available primitives."""

    name: str = "composable"

    def __init__(
        self,
        spec: ComposableSpec,
        *,
        aux_symbols: tuple[str, ...] = (),
    ) -> None:
        self.spec = spec
        self.aux_symbols = tuple(aux_symbols)
        self.aux_history: dict[str, list[Bar]] = {sym: [] for sym in aux_symbols}
        # Per-day state. Reset on Globex (18:00 ET roll-forward) day change.
        self._current_day: dt.date | None = None
        self._trades_today: int = 0
        self._entries_today: set[tuple[str, dt.datetime]] = set()
        # Per-direction setup-armed state. None = never armed (or expired).
        # An int means "armed through bar with this index" (inclusive).
        self._setup_armed_long_until_idx: int | None = None
        self._setup_armed_short_until_idx: int | None = None
        self._validate_spec()

    # ------------------------------------------------------------------
    # Engine lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def from_config(
        cls,
        params: dict,
        *,
        tick_size: float,
        qty: int,
    ) -> "ComposableStrategy":
        del tick_size  # composable doesn't depend on it directly
        spec = ComposableSpec.from_dict(params)
        if qty != spec.qty:
            # User passed run-level qty; spec's qty wins for clarity.
            pass
        return cls(spec=spec)

    def on_start(self, context: Context) -> None:
        self.aux_history = {sym: [] for sym in self.aux_symbols}
        self._current_day = None
        self._trades_today = 0
        self._entries_today = set()
        self._setup_armed_long_until_idx = None
        self._setup_armed_short_until_idx = None

    def on_bar(self, bar: Bar, context: Context) -> list[OrderIntent]:
        for sym in self.aux_symbols:
            aux_bar = context.aux.get(sym)
            if aux_bar is not None:
                self.aux_history.setdefault(sym, []).append(aux_bar)

        bar_et = bar.ts_event.astimezone(ET)
        trading_day = (
            (bar_et + dt.timedelta(days=1)).date()
            if bar_et.hour >= 18
            else bar_et.date()
        )
        if self._current_day is None or trading_day != self._current_day:
            self._current_day = trading_day
            self._trades_today = 0
            self._entries_today = set()
            # Setup arming is per-trading-day. A sweep that armed at the
            # previous session's close should not still arm a fresh open.
            self._setup_armed_long_until_idx = None
            self._setup_armed_short_until_idx = None

        if self._trades_today >= self.spec.max_trades_per_day:
            return []
        if context.in_position:
            return []

        history = context.history
        if not history:
            return []
        current_idx = len(history) - 1

        intent = self._evaluate_direction(
            "BULLISH",
            self.spec.setup_long,
            self.spec.trigger_long,
            self.spec.setup_window.long,
            bar=bar,
            history=history,
            current_idx=current_idx,
        )
        if intent is None:
            intent = self._evaluate_direction(
                "BEARISH",
                self.spec.setup_short,
                self.spec.trigger_short,
                self.spec.setup_window.short,
                bar=bar,
                history=history,
                current_idx=current_idx,
            )
        if intent is None:
            return []

        bucket_min = (
            bar_et.minute // self.spec.entry_dedup_minutes
        ) * self.spec.entry_dedup_minutes
        bucket = bar_et.replace(minute=bucket_min, second=0, microsecond=0)
        side_key = "BULLISH" if intent.side == Side.LONG else "BEARISH"
        if (side_key, bucket) in self._entries_today:
            return []
        self._entries_today.add((side_key, bucket))
        self._trades_today += 1
        return [intent]

    # ------------------------------------------------------------------
    # Per-direction evaluation
    # ------------------------------------------------------------------

    def _evaluate_direction(
        self,
        direction: Direction,
        setup_calls: list[FeatureCall],
        trigger_calls: list[FeatureCall],
        window_bars: int | None,
        *,
        bar: Bar,
        history: list[Bar],
        current_idx: int,
    ) -> OrderIntent | None:
        # If the recipe has nothing to fire on, no entries this direction.
        if not trigger_calls:
            return None

        merged_metadata: dict = {}

        # Step 1: setup. Empty setup = always armed (the trigger-only
        # case, which is also what an old-shape spec migrates to).
        if setup_calls:
            setup_passed, setup_meta = self._evaluate_features(
                setup_calls,
                history=history,
                current_idx=current_idx,
            )
            if setup_passed:
                # Arm the window. window_bars=None → persistent (cleared
                # at day rollover). int window_bars → inclusive bars from
                # the firing bar. Re-fires while armed refresh the window
                # to the further-out expiry (don't accumulate).
                new_until = (
                    _PERSISTENT_ARMED
                    if window_bars is None
                    else current_idx + int(window_bars)
                )
                existing = self._armed_until(direction)
                if existing is None or new_until > existing:
                    self._set_armed_until(direction, new_until)
                merged_metadata.update(setup_meta)

            armed_until = self._armed_until(direction)
            if armed_until is None or current_idx > armed_until:
                # Never armed, or window expired and setup didn't re-fire.
                return None

        # Step 2: triggers.
        trig_passed, trig_meta = self._evaluate_features(
            trigger_calls,
            history=history,
            current_idx=current_idx,
        )
        if not trig_passed:
            return None
        merged_metadata.update(trig_meta)

        # Step 3: filters (global first, then per-direction).
        if self.spec.filter:
            ok, _ = self._evaluate_features(
                self.spec.filter, history=history, current_idx=current_idx
            )
            if not ok:
                return None
        per_dir_filter = (
            self.spec.filter_long if direction == "BULLISH" else self.spec.filter_short
        )
        if per_dir_filter:
            ok, _ = self._evaluate_features(
                per_dir_filter, history=history, current_idx=current_idx
            )
            if not ok:
                return None

        # All gates passed. Compute stop/target.
        ep = bar.close
        side = Side.LONG if direction == "BULLISH" else Side.SHORT
        stop_price = self._compute_stop(direction, ep, merged_metadata)
        if stop_price is None:
            return None
        risk = abs(ep - stop_price)
        if risk <= 0 or risk > self.spec.max_risk_pts:
            return None
        if risk < self.spec.min_risk_pts:
            return None
        target_price = self._compute_target(direction, ep, risk)

        return BracketOrder(
            side=side,
            qty=self.spec.qty,
            stop_price=stop_price,
            target_price=target_price,
            max_hold_bars=self.spec.max_hold_bars,
        )

    def _evaluate_features(
        self,
        calls: list[FeatureCall],
        *,
        history: list[Bar],
        current_idx: int,
    ) -> tuple[bool, dict]:
        """Run every feature; return (all_passed, merged_metadata)."""
        merged: dict = {}
        for call in calls:
            spec = FEATURES.get(call.feature)
            if spec is None:
                return False, merged
            try:
                result: FeatureResult = spec.fn(
                    bars=history,
                    aux=self.aux_history,
                    current_idx=current_idx,
                    **call.params,
                )
            except Exception:
                return False, merged
            if not result.passed:
                return False, merged
            merged.update(result.metadata)
        return True, merged

    def _armed_until(self, direction: Direction) -> int | None:
        """Per-direction armed-until index. None = not armed.
        ``_PERSISTENT_ARMED`` (sys.maxsize) = persistent until day rollover."""
        if direction == "BULLISH":
            return self._setup_armed_long_until_idx
        return self._setup_armed_short_until_idx

    def _set_armed_until(self, direction: Direction, value: int | None) -> None:
        if direction == "BULLISH":
            self._setup_armed_long_until_idx = value
        else:
            self._setup_armed_short_until_idx = value

    # ------------------------------------------------------------------
    # Stop / target rule resolution
    # ------------------------------------------------------------------

    def _compute_stop(
        self,
        direction: Direction,
        entry_price: float,
        metadata: dict,
    ) -> float | None:
        rule = self.spec.stop
        if rule.type == "fixed_pts":
            offset = rule.stop_pts
            return entry_price - offset if direction == "BULLISH" else entry_price + offset
        if rule.type == "fvg_buffer":
            fh = metadata.get("fvg_high")
            fl = metadata.get("fvg_low")
            if fh is None or fl is None:
                return None
            if direction == "BULLISH":
                return float(fl) - rule.buffer_pts
            return float(fh) + rule.buffer_pts
        return None

    def _compute_target(
        self,
        direction: Direction,
        entry_price: float,
        risk: float,
    ) -> float:
        rule = self.spec.target
        if rule.type == "r_multiple":
            mag = risk * rule.r
        else:
            mag = rule.target_pts
        return entry_price + mag if direction == "BULLISH" else entry_price - mag

    # ------------------------------------------------------------------
    # Init validation
    # ------------------------------------------------------------------

    def _validate_spec(self) -> None:
        all_calls = [
            *self.spec.setup_long,
            *self.spec.trigger_long,
            *self.spec.setup_short,
            *self.spec.trigger_short,
            *self.spec.filter,
            *self.spec.filter_long,
            *self.spec.filter_short,
        ]
        if not all_calls:
            return
        for call in all_calls:
            if call.feature not in FEATURES:
                known = ", ".join(sorted(FEATURES.keys()))
                raise ValueError(
                    f"Unknown feature {call.feature!r}. Known: {known}"
                )
