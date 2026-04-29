"""Feature library — pure-function signal primitives.

Each feature is a stateless predicate (with optional metadata) that
takes:
  - `bars`: primary symbol bar history up to and including current
  - `aux`:  per-asset bar history (e.g., {"ES.c.0": [...], "YM.c.0": [...]})
  - `current_idx`: position of the current bar within `bars`
  - per-feature params (kwargs)

…and returns a `FeatureResult` with `passed: bool`, optional
`direction`, and a `metadata` dict that downstream features (and
stop/target rules) can consume.

Features power the `composable` strategy plugin: a strategy spec
lists features by name and params; the plugin evaluates them every
bar and emits trades when ALL listed features pass.

Adding a feature:

  1. Write a pure function `def my_feature(*, bars, aux, current_idx,
     **params) -> FeatureResult` in a new module under this package.
  2. Register it in `FEATURES` below with a `FeatureSpec` (label,
     description, param schema for the form).

Most features are thin wrappers around helpers already in
`app/strategies/fractal_amd/signals.py` and
`app/strategies/fractal_amd_trusted/orderflow.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal


Direction = Literal["BULLISH", "BEARISH"]


@dataclass
class FeatureResult:
    """What every feature returns.

    `passed` is the only gate — composable strategies AND all features
    in their entry list. `direction` is optional: features that detect
    a directional bias (SMT, prior_level_sweep) populate it; features
    that are pure filters (time_window, co_score) leave it None.
    `metadata` lets downstream features chain off prior detections
    (e.g., `smt_at_level` reads `metadata.swept_level` written by
    `prior_level_sweep`).
    """

    passed: bool
    direction: Direction | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# Feature signature: keyword-only args for safety, **params for the
# user-supplied config block.
FeatureFn = Callable[..., FeatureResult]


@dataclass
class FeatureSpec:
    """Frontend-renderable description of one feature."""

    fn: FeatureFn
    label: str
    description: str
    # JSON-Schema-ish shape, same convention as strategy_registry's
    # param_schema. Each property has type/label/min/max/step/enum.
    param_schema: dict[str, Any]


# Registry. Populated by side-effect imports below.
FEATURES: dict[str, FeatureSpec] = {}


def register(name: str, spec: FeatureSpec) -> None:
    """Register a feature. Called from each module's import."""
    if name in FEATURES:
        raise ValueError(f"feature {name!r} already registered")
    FEATURES[name] = spec


# Side-effect imports populate FEATURES. Each module calls
# `register(...)` at import time.
from app.features import (  # noqa: E402,F401
    co_score,
    fvg_touch_recent,
    prior_level_sweep,
    smt_at_level,
    time_window,
)
