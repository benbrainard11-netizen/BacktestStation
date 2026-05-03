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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Sentinel for "setup armed until end of trading day" (window=None case).
# Day-rollover always clears armed state, so this is bounded in practice.
_PERSISTENT_ARMED: int = sys.maxsize

from app.backtest.orders import BracketOrder, OrderIntent, Side
from app.backtest.strategy import Bar, Context, Strategy
from app.features import FEATURES, FeatureResult
from app.strategies.composable.config import (
    ComposableSpec,
    FeatureCall,
    WindowSpec,
)


@dataclass(frozen=True)
class ArmedUntil:
    """Per-direction setup-armed expiry.

    `kind="bar_idx"` → expires when `current_idx > idx`. Used for bars
    windows and the persistent sentinel (idx == sys.maxsize).
    `kind="clock"` → expires when `bar.ts_event >= deadline_ts` (UTC).
    """

    kind: Literal["bar_idx", "clock"]
    idx: int = 0
    deadline_ts: dt.datetime | None = None

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
        self._armed_until_long: ArmedUntil | None = None
        self._armed_until_short: ArmedUntil | None = None
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
        self._armed_until_long = None
        self._armed_until_short = None

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
            self._armed_until_long = None
            self._armed_until_short = None

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
        window: WindowSpec | None,
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
                bar=bar,
                history=history,
                current_idx=current_idx,
            )
            if setup_passed:
                # Arm the window. Re-fires while armed extend the window
                # to the further-out expiry (don't accumulate).
                new_until = _compute_arm_deadline(
                    window,
                    current_idx=current_idx,
                    firing_bar_ts=bar.ts_event,
                )
                existing = self._armed_until(direction)
                if existing is None or _is_further(new_until, existing):
                    self._set_armed_until(direction, new_until)
                merged_metadata.update(setup_meta)

            armed = self._armed_until(direction)
            if armed is None or not _armed_is_active(
                armed, current_idx=current_idx, bar_ts=bar.ts_event
            ):
                # Never armed, or window expired and setup didn't re-fire.
                return None

        # Step 2: triggers.
        trig_passed, trig_meta = self._evaluate_features(
            trigger_calls,
            bar=bar,
            history=history,
            current_idx=current_idx,
        )
        if not trig_passed:
            return None
        merged_metadata.update(trig_meta)

        # Step 3: filters (global first, then per-direction).
        if self.spec.filter:
            ok, _ = self._evaluate_features(
                self.spec.filter, bar=bar, history=history, current_idx=current_idx
            )
            if not ok:
                return None
        per_dir_filter = (
            self.spec.filter_long if direction == "BULLISH" else self.spec.filter_short
        )
        if per_dir_filter:
            ok, _ = self._evaluate_features(
                per_dir_filter, bar=bar, history=history, current_idx=current_idx
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
        bar: Bar,
        history: list[Bar],
        current_idx: int,
    ) -> tuple[bool, dict]:
        """Run every feature; return (all_passed, merged_metadata).

        Per-call `gate` (CallGate) is checked BEFORE invoking the
        feature: outside the window, the call is treated as failed
        without running. This is what makes a gated setup not arm
        outside its time window.
        """
        merged: dict = {}
        for call in calls:
            if call.gate is not None and not _gate_admits(call.gate, bar.ts_event):
                return False, merged
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

    def _armed_until(self, direction: Direction) -> ArmedUntil | None:
        """Per-direction armed-until handle. None = not armed."""
        if direction == "BULLISH":
            return self._armed_until_long
        return self._armed_until_short

    def _set_armed_until(self, direction: Direction, value: ArmedUntil | None) -> None:
        if direction == "BULLISH":
            self._armed_until_long = value
        else:
            self._armed_until_short = value

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
            if call.gate is not None:
                # Defense in depth — `from_dict` already validates gates,
                # but specs constructed directly in code skip the parser.
                if call.gate.end_hour <= call.gate.start_hour:
                    raise ValueError(
                        f"{call.feature}: gate end_hour ({call.gate.end_hour}) "
                        f"must be > start_hour ({call.gate.start_hour})"
                    )
                try:
                    ZoneInfo(call.gate.tz)
                except ZoneInfoNotFoundError as exc:
                    raise ValueError(
                        f"{call.feature}: unknown gate tz {call.gate.tz!r}"
                    ) from exc


def _gate_admits(gate, bar_ts: dt.datetime) -> bool:
    """True iff the bar's local time in `gate.tz` is in [start, end)."""
    local = bar_ts.astimezone(ZoneInfo(gate.tz))
    hour_frac = local.hour + local.minute / 60.0 + local.second / 3600.0
    return gate.start_hour <= hour_frac < gate.end_hour


def _compute_arm_deadline(
    window: WindowSpec | None,
    *,
    current_idx: int,
    firing_bar_ts: dt.datetime,
) -> ArmedUntil:
    """Translate a WindowSpec into an ArmedUntil rooted at the firing bar."""
    if window is None:
        # Persistent — armed until day rollover clears it.
        return ArmedUntil(kind="bar_idx", idx=_PERSISTENT_ARMED)
    if window.kind == "bars":
        assert window.n is not None
        return ArmedUntil(kind="bar_idx", idx=current_idx + window.n)
    if window.kind == "minutes":
        assert window.n is not None
        return ArmedUntil(
            kind="clock",
            deadline_ts=firing_bar_ts + dt.timedelta(minutes=window.n),
        )
    if window.kind == "until_clock":
        assert window.end_hour is not None
        deadline = _resolve_clock_deadline(
            firing_bar_ts=firing_bar_ts,
            end_hour=window.end_hour,
            tz=window.tz,
        )
        return ArmedUntil(kind="clock", deadline_ts=deadline)
    raise ValueError(f"unknown window kind: {window.kind!r}")


def _resolve_clock_deadline(
    *,
    firing_bar_ts: dt.datetime,
    end_hour: float,
    tz: str,
) -> dt.datetime:
    """Anchor `end_hour` to the firing bar's *trading day* in `tz`.

    Trading day uses the Globex roll convention (firing bar past 18:00
    ET belongs to the next calendar day) so an arming bar at 17:55 with
    end_hour=10 isn't ambiguous: it points at tomorrow's 10:00.
    """
    zi = ZoneInfo(tz)
    local = firing_bar_ts.astimezone(zi)
    # Globex roll uses ET; for non-ET tzs the roll convention still
    # applies because day-rollover in `on_bar` is in ET. We compute
    # trading_day in ET then map the time-of-day into the requested tz.
    bar_et = firing_bar_ts.astimezone(ET)
    trading_day = (
        (bar_et + dt.timedelta(days=1)).date() if bar_et.hour >= 18 else bar_et.date()
    )
    h = int(end_hour)
    m = int(round((end_hour - h) * 60))
    if h == 24:
        # 24:00 means end-of-day → midnight of trading_day + 1
        deadline_local = dt.datetime.combine(
            trading_day + dt.timedelta(days=1),
            dt.time(0, 0),
            tzinfo=zi,
        )
    else:
        deadline_local = dt.datetime.combine(
            trading_day, dt.time(h, m), tzinfo=zi
        )
    # If the resolved deadline is at or before the firing bar (e.g.
    # firing at 11:00 with end_hour=10 on the same trading day),
    # roll forward one trading day so the window is at least valid
    # in the immediate future.
    if deadline_local <= local:
        deadline_local = deadline_local + dt.timedelta(days=1)
    return deadline_local


def _armed_is_active(armed: ArmedUntil, *, current_idx: int, bar_ts: dt.datetime) -> bool:
    """True iff the current bar is still inside the armed window."""
    if armed.kind == "bar_idx":
        return current_idx <= armed.idx
    # clock
    assert armed.deadline_ts is not None
    return bar_ts < armed.deadline_ts


def _is_further(new: ArmedUntil, existing: ArmedUntil) -> bool:
    """True iff `new` extends the armed window past `existing`.

    Cross-kind comparison: a clock deadline is treated as further than
    any bar_idx deadline EXCEPT _PERSISTENT_ARMED, and vice versa.
    Same-kind comparison uses the obvious ordering.
    """
    if new.kind == existing.kind == "bar_idx":
        return new.idx > existing.idx
    if new.kind == existing.kind == "clock":
        assert new.deadline_ts is not None and existing.deadline_ts is not None
        return new.deadline_ts > existing.deadline_ts
    # Cross-kind: persistent (idx == _PERSISTENT_ARMED) wins; otherwise
    # the new one wins to keep the freshly fired setup arming the
    # window even if the existing was a different kind.
    if existing.kind == "bar_idx" and existing.idx == _PERSISTENT_ARMED:
        return False
    if new.kind == "bar_idx" and new.idx == _PERSISTENT_ARMED:
        return True
    return True
