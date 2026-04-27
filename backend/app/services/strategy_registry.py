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
                    "description": "Hard cap on stop distance in points, regardless of dollars.",
                },
                "min_risk_pts": {
                    "type": "number",
                    "label": "Min risk (pts)",
                    "min": 1,
                    "max": 100,
                    "step": 0.5,
                    "description": "Skip if stop is too tight to survive bid/ask noise.",
                },
                "target_r": {
                    "type": "number",
                    "label": "Target R-multiple",
                    "min": 0.5,
                    "max": 10,
                    "step": 0.5,
                },
                "max_trades_per_day": {
                    "type": "integer",
                    "label": "Max trades/day",
                    "min": 1,
                    "max": 10,
                },
                "rth_open_hour": {
                    "type": "integer",
                    "label": "Entry window open (hour, ET)",
                    "min": 0,
                    "max": 23,
                },
                "rth_open_min": {
                    "type": "integer",
                    "label": "Entry window open (minute)",
                    "min": 0,
                    "max": 59,
                },
                "max_entry_hour": {
                    "type": "integer",
                    "label": "Entry window close (hour, ET, exclusive)",
                    "min": 1,
                    "max": 24,
                },
                "stop_buffer_pts": {
                    "type": "number",
                    "label": "Stop buffer (pts beyond FVG)",
                    "min": 0,
                    "max": 5,
                    "step": 0.25,
                },
                "entry_max_bars_after_touch": {
                    "type": "integer",
                    "label": "Max bars after touch before reset",
                    "min": 1,
                    "max": 30,
                },
                "entry_dedup_minutes": {
                    "type": "integer",
                    "label": "Direction dedup window (min)",
                    "min": 1,
                    "max": 60,
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


STRATEGY_DEFINITIONS: list[dict[str, Any]] = [
    _fractal_amd_definition(),
    _moving_average_crossover_definition(),
]
