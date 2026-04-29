"""Composable strategy — assemble a strategy from feature primitives.

The plugin reads a JSON spec (`RunConfig.params`), evaluates the
configured feature list per direction every bar, and emits a bracket
order when ALL features in an entry list pass simultaneously.

Spec shape:
    {
      "entry_long":  [ {"feature": "...", "params": {...}}, ... ],
      "entry_short": [ {"feature": "...", "params": {...}}, ... ],
      "stop":   {"type": "fixed_pts",  "stop_pts": 10},
      "target": {"type": "r_multiple", "r": 3},
      "qty": 1,
      "max_trades_per_day": 2,
      "entry_dedup_minutes": 15
    }
"""

from app.strategies.composable.strategy import ComposableStrategy

__all__ = ["ComposableStrategy"]
