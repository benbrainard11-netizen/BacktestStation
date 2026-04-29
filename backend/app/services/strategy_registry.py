"""Static catalogue of strategies the engine resolver knows about.

The engine resolver in `app.backtest.runner._resolve_strategy` is the
source of truth for which strategies can run. This module mirrors that
list with metadata the frontend needs to render a dynamic form: a label,
a description, default params, and a small param schema (JSON-Schema-
like) per strategy.

We intentionally do NOT introduce a registry/plugin system here — per
CLAUDE.md "no premature abstractions until 3 strategies." Once a third
runnable strategy lands, fold the lookups together.

Param schema shape (light, frontend-friendly — not full JSON Schema):

    {
      "type": "object",
      "properties": {
        "max_risk_dollars": {
          "type": "number",        # number | integer
          "label": "Max risk ($)",
          "min": 50, "max": 5000, "step": 50,
          "description": "Optional one-line hint surfaced under the field."
        },
        ...
      }
    }
"""

from __future__ import annotations

from typing import Any

from app.strategies.fractal_amd.config import FractalAMDConfig


def _fractal_amd_definition() -> dict[str, Any]:
    cfg = FractalAMDConfig()
    return {
        "name": "fractal_amd",
        "label": "Fractal AMD",
        "description": (
            "Multi-instrument SMT divergence + Fair Value Gap setup with "
            "stop+target bracket entries. Mirrors the live bot's behavior; "
            "MNQ auto-downshift is built in."
        ),
        "default_params": {
            "max_risk_pts": cfg.max_risk_pts,
            "min_risk_pts": cfg.min_risk_pts,
            "target_r": cfg.target_r,
            "max_trades_per_day": cfg.max_trades_per_day,
            "max_risk_dollars": cfg.max_risk_dollars,
            "rth_open_hour": cfg.rth_open_hour,
            "rth_open_min": cfg.rth_open_min,
            "max_entry_hour": cfg.max_entry_hour,
            "stop_buffer_pts": cfg.stop_buffer_pts,
            "entry_max_bars_after_touch": cfg.entry_max_bars_after_touch,
            "entry_dedup_minutes": cfg.entry_dedup_minutes,
        },
        "param_schema": {
            "type": "object",
            "properties": {
                "max_risk_dollars": {
                    "type": "number",
                    "label": "Max risk ($)",
                    "min": 50,
                    "max": 5000,
                    "step": 50,
                    "group": "risk",
                    "description": (
                        "Per-trade dollar risk cap. Setups whose stop on NQ "
                        "would breach this auto-downshift to MNQ; if even "
                        "MNQ would breach, the trade is rejected."
                    ),
                },
                "max_risk_pts": {
                    "type": "number",
                    "label": "Max risk (pts)",
                    "min": 1,
                    "max": 500,
                    "step": 1,
                    "group": "risk",
                    "description": "Hard cap on stop distance in points, regardless of dollars.",
                },
                "min_risk_pts": {
                    "type": "number",
                    "label": "Min risk (pts)",
                    "min": 1,
                    "max": 100,
                    "step": 0.5,
                    "group": "risk",
                    "description": "Skip if stop is too tight to survive bid/ask noise.",
                },
                "target_r": {
                    "type": "number",
                    "label": "Target R-multiple",
                    "min": 0.5,
                    "max": 10,
                    "step": 0.5,
                    "group": "risk",
                },
                "max_trades_per_day": {
                    "type": "integer",
                    "label": "Max trades/day",
                    "min": 1,
                    "max": 10,
                    "group": "session",
                },
                "rth_open_hour": {
                    "type": "integer",
                    "label": "Entry window open (hour, ET)",
                    "min": 0,
                    "max": 23,
                    "group": "session",
                },
                "rth_open_min": {
                    "type": "integer",
                    "label": "Entry window open (minute)",
                    "min": 0,
                    "max": 59,
                    "group": "session",
                },
                "max_entry_hour": {
                    "type": "integer",
                    "label": "Entry window close (hour, ET, exclusive)",
                    "min": 1,
                    "max": 24,
                    "group": "session",
                },
                "stop_buffer_pts": {
                    "type": "number",
                    "label": "Stop buffer (pts beyond FVG)",
                    "min": 0,
                    "max": 5,
                    "step": 0.25,
                    "group": "risk",
                },
                "entry_max_bars_after_touch": {
                    "type": "integer",
                    "label": "Max bars after touch before reset",
                    "min": 1,
                    "max": 30,
                    "group": "signal",
                },
                "entry_dedup_minutes": {
                    "type": "integer",
                    "label": "Direction dedup window (min)",
                    "min": 1,
                    "max": 60,
                    "group": "session",
                },
            },
        },
    }


def _moving_average_crossover_definition() -> dict[str, Any]:
    return {
        "name": "moving_average_crossover",
        "label": "Moving Average Crossover",
        "description": (
            "Classic two-MA crossover with fixed-tick stop and target. "
            "Built primarily as the engine's smoke-test strategy."
        ),
        "default_params": {
            "fast_period": 5,
            "slow_period": 20,
            "stop_ticks": 8,
            "target_ticks": 16,
        },
        "param_schema": {
            "type": "object",
            "properties": {
                "fast_period": {
                    "type": "integer",
                    "label": "Fast MA period (bars)",
                    "min": 1,
                    "max": 200,
                },
                "slow_period": {
                    "type": "integer",
                    "label": "Slow MA period (bars)",
                    "min": 1,
                    "max": 500,
                },
                "stop_ticks": {
                    "type": "integer",
                    "label": "Stop distance (ticks)",
                    "min": 1,
                    "max": 100,
                },
                "target_ticks": {
                    "type": "integer",
                    "label": "Target distance (ticks)",
                    "min": 1,
                    "max": 200,
                },
            },
        },
    }


def _composable_definition() -> dict[str, Any]:
    """User-assembled strategy. The full spec lives in `params` as a
    JSON object; the form surfaces a few top-level knobs and a hint
    that the rest is edited via the Advanced JSON drawer."""
    return {
        "name": "composable",
        "label": "Composable strategy (feature builder)",
        "description": (
            "Build a strategy by listing pre-made features. Each feature "
            "is a pure-function predicate (PDH sweep, SMT divergence, "
            "FVG touch, time filter, CO score). All features in an "
            "entry list must pass for a trade to fire. Edit the full "
            "spec via the Advanced JSON drawer."
        ),
        "default_params": {
            "entry_long": [],
            "entry_short": [],
            "stop": {"type": "fixed_pts", "stop_pts": 10.0},
            "target": {"type": "r_multiple", "r": 3.0},
            "qty": 1,
            "max_trades_per_day": 2,
            "entry_dedup_minutes": 15,
            "max_hold_bars": 120,
            "max_risk_pts": 150.0,
            "min_risk_pts": 0.0,
        },
        "param_schema": {
            "type": "object",
            "properties": {
                "qty": {
                    "type": "integer",
                    "label": "Contracts per trade",
                    "min": 1,
                    "max": 50,
                    "group": "risk",
                },
                "max_trades_per_day": {
                    "type": "integer",
                    "label": "Max trades/day",
                    "min": 1,
                    "max": 20,
                    "group": "session",
                },
                "entry_dedup_minutes": {
                    "type": "integer",
                    "label": "Direction dedup window (min)",
                    "min": 1,
                    "max": 60,
                    "group": "session",
                },
                "max_hold_bars": {
                    "type": "integer",
                    "label": "Max hold (1m bars)",
                    "min": 5,
                    "max": 600,
                    "group": "risk",
                },
                "max_risk_pts": {
                    "type": "number",
                    "label": "Max risk (pts)",
                    "min": 1,
                    "max": 500,
                    "step": 1,
                    "group": "risk",
                },
                "min_risk_pts": {
                    "type": "number",
                    "label": "Min risk (pts)",
                    "min": 0,
                    "max": 50,
                    "step": 0.5,
                    "group": "risk",
                },
            },
        },
    }


STRATEGY_DEFINITIONS: list[dict[str, Any]] = [
    _fractal_amd_definition(),
    _composable_definition(),
    _moving_average_crossover_definition(),
]
