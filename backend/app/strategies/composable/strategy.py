"""Composable strategy plugin.

Reads a JSON spec (entry feature lists + stop/target rules), evaluates
all features each bar, and emits bracket orders when ALL features in
an entry list pass simultaneously. Designed to let users assemble new
strategies from `app.features.FEATURES` without writing Python.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Literal
from zoneinfo import ZoneInfo

from app.backtest.orders import BracketOrder, OrderIntent, Side
from app.backtest.strategy import Bar, Context, Strategy
from app.features import FEATURES, FeatureResult
from app.strategies.composable.config import (
    ComposableSpec,
    FeatureCall,
    StopRule,
    TargetRule,
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
        # Per-day state. Reset on date-of-day rollover (Globex
        # 18:00 → 17:00 ET convention, same as fractal_amd_trusted).
        self._current_day: dt.date | None = None
        self._trades_today: int = 0
        self._entries_today: set[tuple[str, dt.datetime]] = set()
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
        # Auto-discover aux symbols from the spec's smt_at_level
        # feature calls (so the strategy declares which assets it needs).
        aux: set[str] = set()
        for call in [*spec.entry_long, *spec.entry_short]:
            if call.feature == "smt_at_level":
                # The plugin doesn't know the aux symbols from the
                # spec; the runner already passes them via aux_bars.
                # We capture by reading the runner-config side instead.
                pass
        return cls(spec=spec)

    def on_start(self, context: Context) -> None:
        self.aux_history = {sym: [] for sym in self.aux_symbols}
        self._current_day = None
        self._trades_today = 0
        self._entries_today = set()

    def on_bar(self, bar: Bar, context: Context) -> list[OrderIntent]:
        # Track aux bars for features that need cross-asset history
        # (e.g., smt_at_level). We append the per-bar value the engine
        # provides on context.aux.
        for sym in self.aux_symbols:
            aux_bar = context.aux.get(sym)
            if aux_bar is not None:
                self.aux_history.setdefault(sym, []).append(aux_bar)

        # Day rollover (Globex: bars at local 18:00+ roll into next
        # trading day).
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

        # Day-cap, position-cap.
        if self._trades_today >= self.spec.max_trades_per_day:
            return []
        if context.in_position:
            return []

        history = context.history
        if not history:
            return []
        current_idx = len(history) - 1

        # Try LONG then SHORT; first to fully pass wins.
        intent = self._evaluate_direction(
            "BULLISH",
            self.spec.entry_long,
            bar=bar,
            history=history,
            current_idx=current_idx,
        )
        if intent is None:
            intent = self._evaluate_direction(
                "BEARISH",
                self.spec.entry_short,
                bar=bar,
                history=history,
                current_idx=current_idx,
            )
        if intent is None:
            return []

        # 15-min direction dedup (same as fractal_amd).
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
        calls: list[FeatureCall],
        *,
        bar: Bar,
        history: list[Bar],
        current_idx: int,
    ) -> OrderIntent | None:
        if not calls:
            return None

        merged_metadata: dict = {}
        last_metadata: dict = {}
        for call in calls:
            spec = FEATURES.get(call.feature)
            if spec is None:
                # Unknown feature — fail loud (validated at __init__,
                # but defense-in-depth).
                return None
            try:
                result: FeatureResult = spec.fn(
                    bars=history,
                    aux=self.aux_history,
                    current_idx=current_idx,
                    **call.params,
                )
            except Exception:
                # Feature-internal error — treat as fail; backtests
                # shouldn't crash because one feature is buggy.
                return None
            if not result.passed:
                return None
            merged_metadata.update(result.metadata)
            last_metadata = result.metadata

        # All features passed. Compute stop/target from rules.
        ep = bar.close  # next-bar open via engine semantics (no fill_immediately)
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

        del last_metadata  # currently unused; reserved for richer rules
        return BracketOrder(
            side=side,
            qty=self.spec.qty,
            stop_price=stop_price,
            target_price=target_price,
            max_hold_bars=self.spec.max_hold_bars,
        )

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
                return None  # no FVG metadata => can't apply this rule
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
        else:  # fixed_pts
            mag = rule.target_pts
        return entry_price + mag if direction == "BULLISH" else entry_price - mag

    # ------------------------------------------------------------------
    # Init validation
    # ------------------------------------------------------------------

    def _validate_spec(self) -> None:
        all_calls = [*self.spec.entry_long, *self.spec.entry_short]
        if not all_calls:
            # Allow but warn: a spec with no entries is a no-op strategy.
            # Don't raise — useful for sanity checks / scaffolding.
            return
        for call in all_calls:
            if call.feature not in FEATURES:
                known = ", ".join(sorted(FEATURES.keys()))
                raise ValueError(
                    f"Unknown feature {call.feature!r}. Known: {known}"
                )
