"""Volume-profile-based features.

Two registered features:

  vp_zone     — pass when current bar's close is in a configured zone
                (above_va / at_vah / in_va / at_poc / at_val / below_va)
                of the rolling-window volume profile.

  vp_in_va    — narrower convenience: pass when close is strictly inside
                the value area. Same as vp_zone with zone='in_va', kept
                separate so the Builder UI can offer it as a one-click
                "range-bound" filter without exposing the zone enum.

Both compute the profile from a rolling window of `lookback_bars`
ending at `current_idx`. We don't try to detect session boundaries by
timestamp — for now the user picks a lookback that approximates one
session for their timeframe (78 bars ≈ one 6.5-hour ETH session at 5m).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.features import FeatureResult, FeatureSpec, register
from app.features._volume_profile import (
    BarTuple,
    compute_profile,
    find_poc,
    find_value_area,
    position_vs_value_area,
)

if TYPE_CHECKING:
    from app.backtest.strategy import Bar


VP_ZONES = ("above_va", "at_vah", "in_va", "at_poc", "at_val", "below_va")


def _build_profile_from_bars(
    bars: "list[Bar]", *, start_idx: int, end_idx: int, tick_size: float
) -> dict[float, float]:
    """Convert Bars → BarTuples and pass to compute_profile.

    Inclusive on `end_idx`, exclusive on `start_idx`-style — actually,
    inclusive of both, but caller should pass `end_idx = current_idx + 1`.
    No: simpler — slice `[start_idx:end_idx]` Python convention.
    """
    sl = bars[start_idx:end_idx]
    return compute_profile(
        (BarTuple(b.high, b.low, float(b.volume)) for b in sl),
        tick_size=tick_size,
    )


def vp_zone(
    *,
    bars: "list[Bar]",
    aux: "dict[str, list[Bar]]",
    current_idx: int,
    zone: str = "in_va",
    lookback_bars: int = 78,
    tick_size: float = 0.25,
    tolerance_ticks: int = 1,
    target_pct: float = 0.7,
    **_: Any,
) -> FeatureResult:
    """Pass when the current bar's close sits in the requested zone."""
    if zone not in VP_ZONES:
        return FeatureResult(passed=False, metadata={"error": f"unknown zone {zone!r}"})
    if current_idx < 0 or current_idx >= len(bars):
        return FeatureResult(passed=False)
    if lookback_bars < 1:
        return FeatureResult(passed=False)

    start = max(0, current_idx - lookback_bars + 1)
    end = current_idx + 1
    if end - start < 2:
        return FeatureResult(passed=False)

    profile = _build_profile_from_bars(
        bars, start_idx=start, end_idx=end, tick_size=tick_size
    )
    poc = find_poc(profile)
    va = find_value_area(profile, target_pct=target_pct)
    if poc is None or va is None:
        return FeatureResult(passed=False)

    val, vah = va
    close = bars[current_idx].close
    tolerance = tolerance_ticks * tick_size
    here = position_vs_value_area(close, val=val, vah=vah, poc=poc, tolerance=tolerance)

    return FeatureResult(
        passed=(here == zone),
        metadata={
            "zone_observed": here,
            "poc": poc,
            "val": val,
            "vah": vah,
            "close": close,
            "lookback_bars_used": end - start,
        },
    )


def vp_in_va(
    *,
    bars: "list[Bar]",
    aux: "dict[str, list[Bar]]",
    current_idx: int,
    lookback_bars: int = 78,
    tick_size: float = 0.25,
    target_pct: float = 0.7,
    **_: Any,
) -> FeatureResult:
    """Range filter — pass when close is inside [VAL, VAH] inclusive.

    NOT a thin wrapper around vp_zone(zone='in_va') because the zone
    classifier returns 'at_poc' / 'at_vah' / 'at_val' on exact-edge
    matches, which would fail the in_va filter even though those points
    ARE inside the value area. Direct interval check matches user intent.
    """
    if current_idx < 0 or current_idx >= len(bars):
        return FeatureResult(passed=False)
    if lookback_bars < 1:
        return FeatureResult(passed=False)
    start = max(0, current_idx - lookback_bars + 1)
    end = current_idx + 1
    if end - start < 2:
        return FeatureResult(passed=False)

    profile = _build_profile_from_bars(
        bars, start_idx=start, end_idx=end, tick_size=tick_size
    )
    poc = find_poc(profile)
    va = find_value_area(profile, target_pct=target_pct)
    if poc is None or va is None:
        return FeatureResult(passed=False)

    val, vah = va
    close = bars[current_idx].close
    return FeatureResult(
        passed=(val <= close <= vah),
        metadata={
            "poc": poc,
            "val": val,
            "vah": vah,
            "close": close,
            "lookback_bars_used": end - start,
        },
    )


register(
    "vp_zone",
    FeatureSpec(
        fn=vp_zone,
        roles=("trigger", "filter"),
        label="Volume profile zone",
        description=(
            "Computes a rolling volume profile over `lookback_bars` and "
            "passes when the current bar's close sits in the configured "
            "zone (above_va / at_vah / in_va / at_poc / at_val / "
            "below_va). 'at_*' zones use `tolerance_ticks * tick_size` "
            "as the proximity band. Profile uses the standard expand-"
            "from-POC algorithm with target_pct (default 70%) for the "
            "value area."
        ),
        param_schema={
            "zone": {
                "type": "string",
                "label": "Zone",
                "enum": list(VP_ZONES),
            },
            "lookback_bars": {
                "type": "integer",
                "label": "Lookback bars",
                "min": 5,
                "max": 1000,
                "description": (
                    "How many recent bars to build the profile from. "
                    "78 bars ≈ one 6.5-hour ETH session at 5m."
                ),
            },
            "tick_size": {
                "type": "number",
                "label": "Tick size",
                "min": 0.0001,
                "step": 0.01,
                "description": "Price granularity for bucketing.",
            },
            "tolerance_ticks": {
                "type": "integer",
                "label": "Edge tolerance (ticks)",
                "min": 0,
                "max": 50,
                "description": (
                    "How close 'at_poc' / 'at_vah' / 'at_val' must be. "
                    "Set to 0 to require exact bucket match."
                ),
            },
            "target_pct": {
                "type": "number",
                "label": "Value area %",
                "min": 0.4,
                "max": 0.95,
                "step": 0.05,
            },
        },
    ),
)

register(
    "vp_in_va",
    FeatureSpec(
        fn=vp_in_va,
        roles=("filter",),
        label="In value area",
        description=(
            "Range filter: pass when the current bar's close is strictly "
            "inside the rolling value area (between VAL and VAH). Use to "
            "scope a strategy to range-bound conditions; pair with "
            "vp_zone='above_va' / 'below_va' to scope to breakouts."
        ),
        param_schema={
            "lookback_bars": {
                "type": "integer",
                "label": "Lookback bars",
                "min": 5,
                "max": 1000,
            },
            "tick_size": {
                "type": "number",
                "label": "Tick size",
                "min": 0.0001,
                "step": 0.01,
            },
            "target_pct": {
                "type": "number",
                "label": "Value area %",
                "min": 0.4,
                "max": 0.95,
                "step": 0.05,
            },
        },
    ),
)
