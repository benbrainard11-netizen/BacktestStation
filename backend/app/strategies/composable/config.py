"""Composable strategy spec — typed dataclasses + JSON parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class FeatureCall:
    """One entry in the entry_long / entry_short / filters list."""

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


@dataclass
class ComposableSpec:
    """Parsed, typed strategy spec."""

    entry_long: list[FeatureCall] = field(default_factory=list)
    entry_short: list[FeatureCall] = field(default_factory=list)
    stop: StopRule = field(default_factory=lambda: StopRule(type="fixed_pts"))
    target: TargetRule = field(default_factory=lambda: TargetRule(type="r_multiple"))
    qty: int = 1
    max_trades_per_day: int = 2
    entry_dedup_minutes: int = 15
    max_hold_bars: int = 120
    # Hard risk caps applied AFTER stop/target math. Keep loose by default.
    max_risk_pts: float = 150.0
    min_risk_pts: float = 0.0

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ComposableSpec":
        """Parse a JSON dict into the typed spec.

        Raises ValueError on unknown keys / bad shapes — surfaces
        early rather than at first bar.
        """
        long_calls = [_parse_call(c, "entry_long") for c in raw.get("entry_long", [])]
        short_calls = [_parse_call(c, "entry_short") for c in raw.get("entry_short", [])]
        stop_raw = raw.get("stop", {"type": "fixed_pts"})
        target_raw = raw.get("target", {"type": "r_multiple"})
        return cls(
            entry_long=long_calls,
            entry_short=short_calls,
            stop=_parse_stop(stop_raw),
            target=_parse_target(target_raw),
            qty=int(raw.get("qty", 1)),
            max_trades_per_day=int(raw.get("max_trades_per_day", 2)),
            entry_dedup_minutes=int(raw.get("entry_dedup_minutes", 15)),
            max_hold_bars=int(raw.get("max_hold_bars", 120)),
            max_risk_pts=float(raw.get("max_risk_pts", 150.0)),
            min_risk_pts=float(raw.get("min_risk_pts", 0.0)),
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
