"""Time-window filter feature.

Pure boolean filter: passes if the current bar's local time (in the
configured timezone) is within `[start_hour, end_hour)`. Hours are
fractional (9.5 == 9:30).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from app.features import FeatureResult, FeatureSpec, register

if TYPE_CHECKING:
    from app.backtest.strategy import Bar


def time_window(
    *,
    bars: "list[Bar]",
    aux: "dict[str, list[Bar]]",
    current_idx: int,
    start_hour: float = 9.5,
    end_hour: float = 14.0,
    tz: str = "America/New_York",
    **_: Any,
) -> FeatureResult:
    """Pass if `current bar's local hour+minute/60 ∈ [start_hour, end_hour)`."""
    if current_idx < 0 or current_idx >= len(bars):
        return FeatureResult(passed=False)
    ts = bars[current_idx].ts_event
    local = ts.astimezone(ZoneInfo(tz))
    hour_frac = local.hour + local.minute / 60.0
    return FeatureResult(
        passed=(start_hour <= hour_frac < end_hour),
        metadata={"local_hour_frac": hour_frac, "tz": tz},
    )


register(
    "time_window",
    FeatureSpec(
        fn=time_window,
        label="Time window filter",
        description=(
            "Only fire entries when the current bar's local time is in "
            "[start_hour, end_hour). Hours are fractional (9.5 = 9:30)."
        ),
        param_schema={
            "start_hour": {
                "type": "number",
                "label": "Start hour (local)",
                "min": 0,
                "max": 24,
                "step": 0.25,
            },
            "end_hour": {
                "type": "number",
                "label": "End hour (local, exclusive)",
                "min": 0,
                "max": 24,
                "step": 0.25,
            },
            "tz": {
                "type": "string",
                "label": "Timezone (IANA)",
                "description": 'Default "America/New_York".',
            },
        },
    ),
)
