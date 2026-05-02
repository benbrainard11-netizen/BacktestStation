"""Composable strategy spec — typed dataclasses + JSON parsing."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeatureCall:
    """One entry in any of the role buckets."""

    feature: str  # registered name in app.features.FEATURES
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StopRule:
    """How to compute the stop price for a triggered entry."""

    type: Literal["fixed_pts", "fvg_buffer"]
    stop_pts: float = 10.0  # used by fixed_pts
    buffer_pts: float = 5.0  # used by fvg_buffer (extra past FVG far edge)


@dataclass(frozen=True)
class TargetRule:
    """How to compute the take-profit price."""

    type: Literal["r_multiple", "fixed_pts"]
    r: float = 3.0  # used by r_multiple
    target_pts: float = 30.0  # used by fixed_pts


@dataclass(frozen=True)
class SetupWindow:
    """How long a fired setup arms the trigger window, per direction.

    None = persistent until end of session (the safe default — a setup
    arms the rest of the session unless the user opts into a tighter
    bars-based expiry).
    """

    long: int | None = None
    short: int | None = None


@dataclass
class ComposableSpec:
    """Parsed, typed strategy spec."""

    # Role-tagged buckets. AND-within-bucket. Engine eval order per bar:
    # setup → arm window → trigger (within window) → filters all pass → enter.
    setup_long: list[FeatureCall] = field(default_factory=list)
    trigger_long: list[FeatureCall] = field(default_factory=list)
    setup_short: list[FeatureCall] = field(default_factory=list)
    trigger_short: list[FeatureCall] = field(default_factory=list)
    filter: list[FeatureCall] = field(default_factory=list)  # global, both directions
    filter_long: list[FeatureCall] = field(default_factory=list)
    filter_short: list[FeatureCall] = field(default_factory=list)
    setup_window: SetupWindow = field(default_factory=SetupWindow)

    # Deprecated — read at deserialization for backward compat with old
    # specs that only know the flat entry_long/entry_short shape. New
    # callers should use trigger_long/trigger_short instead.
    entry_long: list[FeatureCall] = field(default_factory=list)
    entry_short: list[FeatureCall] = field(default_factory=list)

    stop: StopRule = field(default_factory=lambda: StopRule(type="fixed_pts"))
    target: TargetRule = field(default_factory=lambda: TargetRule(type="r_multiple"))
    qty: int = 1
    max_trades_per_day: int = 2
    entry_dedup_minutes: int = 15
    max_hold_bars: int = 120
    max_risk_pts: float = 150.0
    min_risk_pts: float = 0.0
    aux_symbols: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ComposableSpec":
        """Parse a JSON dict into the typed spec.

        Raises ValueError on unknown keys / bad shapes — surfaces
        early rather than at first bar.

        Backward compat: an input with only ``entry_long``/``entry_short``
        (the pre-2026-05-02 shape) is migrated into ``trigger_long``/
        ``trigger_short`` automatically. If both old and new keys are
        present, the new keys win and a warning is logged.
        """
        has_old_long = "entry_long" in raw
        has_old_short = "entry_short" in raw
        has_new_long = "trigger_long" in raw
        has_new_short = "trigger_short" in raw

        if (has_old_long or has_old_short) and (has_new_long or has_new_short):
            logger.warning(
                "ComposableSpec: both old (entry_long/entry_short) and new "
                "(trigger_long/trigger_short) keys present; using new keys"
            )

        # Resolve trigger sources with old-shape fallback.
        long_src = raw.get("trigger_long") if has_new_long else raw.get("entry_long", [])
        short_src = raw.get("trigger_short") if has_new_short else raw.get("entry_short", [])

        trigger_long = [_parse_call(c, "trigger_long") for c in (long_src or [])]
        trigger_short = [_parse_call(c, "trigger_short") for c in (short_src or [])]
        setup_long = [_parse_call(c, "setup_long") for c in raw.get("setup_long", [])]
        setup_short = [_parse_call(c, "setup_short") for c in raw.get("setup_short", [])]
        filt = [_parse_call(c, "filter") for c in raw.get("filter", [])]
        filt_long = [_parse_call(c, "filter_long") for c in raw.get("filter_long", [])]
        filt_short = [_parse_call(c, "filter_short") for c in raw.get("filter_short", [])]

        return cls(
            setup_long=setup_long,
            trigger_long=trigger_long,
            setup_short=setup_short,
            trigger_short=trigger_short,
            filter=filt,
            filter_long=filt_long,
            filter_short=filt_short,
            setup_window=_parse_setup_window(raw.get("setup_window", {})),
            # Mirror triggers into the deprecated fields so the pre-rewrite
            # engine (which still reads entry_long/entry_short) keeps working
            # between this chunk and the engine state-machine rewrite.
            entry_long=list(trigger_long),
            entry_short=list(trigger_short),
            stop=_parse_stop(raw.get("stop", {"type": "fixed_pts"})),
            target=_parse_target(raw.get("target", {"type": "r_multiple"})),
            qty=int(raw.get("qty", 1)),
            max_trades_per_day=int(raw.get("max_trades_per_day", 2)),
            entry_dedup_minutes=int(raw.get("entry_dedup_minutes", 15)),
            max_hold_bars=int(raw.get("max_hold_bars", 120)),
            max_risk_pts=float(raw.get("max_risk_pts", 150.0)),
            min_risk_pts=float(raw.get("min_risk_pts", 0.0)),
            aux_symbols=_parse_aux_symbols(raw.get("aux_symbols", [])),
        )


def _parse_call(raw: Any, where: str) -> FeatureCall:
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: each entry must be an object, got {type(raw).__name__}")
    name = raw.get("feature")
    if not isinstance(name, str) or not name:
        raise ValueError(f"{where}: missing 'feature' name")
    params = raw.get("params", {})
    if not isinstance(params, dict):
        raise ValueError(f"{where}: 'params' must be an object, got {type(params).__name__}")
    return FeatureCall(feature=name, params=dict(params))


def _parse_stop(raw: Any) -> StopRule:
    if not isinstance(raw, dict):
        raise ValueError(f"stop must be an object, got {type(raw).__name__}")
    typ = raw.get("type", "fixed_pts")
    if typ not in ("fixed_pts", "fvg_buffer"):
        raise ValueError(f"stop.type must be 'fixed_pts' or 'fvg_buffer', got {typ!r}")
    return StopRule(
        type=typ,
        stop_pts=float(raw.get("stop_pts", 10.0)),
        buffer_pts=float(raw.get("buffer_pts", 5.0)),
    )


def _parse_target(raw: Any) -> TargetRule:
    if not isinstance(raw, dict):
        raise ValueError(f"target must be an object, got {type(raw).__name__}")
    typ = raw.get("type", "r_multiple")
    if typ not in ("r_multiple", "fixed_pts"):
        raise ValueError(f"target.type must be 'r_multiple' or 'fixed_pts', got {typ!r}")
    return TargetRule(
        type=typ,
        r=float(raw.get("r", 3.0)),
        target_pts=float(raw.get("target_pts", 30.0)),
    )


def _parse_aux_symbols(raw: Any) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(
            f"aux_symbols must be a list of strings, got {type(raw).__name__}"
        )
    out: list[str] = []
    for i, sym in enumerate(raw):
        if not isinstance(sym, str) or not sym:
            raise ValueError(
                f"aux_symbols[{i}] must be a non-empty string, got {sym!r}"
            )
        out.append(sym)
    return out


def _parse_setup_window(raw: Any) -> SetupWindow:
    if raw is None:
        return SetupWindow()
    if not isinstance(raw, dict):
        raise ValueError(
            f"setup_window must be an object, got {type(raw).__name__}"
        )
    return SetupWindow(
        long=_parse_window_value(raw.get("long"), "setup_window.long"),
        short=_parse_window_value(raw.get("short"), "setup_window.short"),
    )


def _parse_window_value(raw: Any, where: str) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError(f"{where} must be an int (bars) or null, got {type(raw).__name__}")
    if raw < 1:
        raise ValueError(f"{where} must be >= 1 bar (got {raw}) or null for persistent")
    return raw
