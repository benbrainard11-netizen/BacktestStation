"""Probability → contract count translation.

Methods (config-selectable in strategy YAML):
  fixed_1            v1 default — 1 contract per trade always
  kelly_fractional   v1.5 — kelly_fraction × (edge / variance)
  vol_targeted       v1.5 — scale inverse to predicted volatility
  confidence_scaled  v1.5 — base × (max_prob - threshold)

See PLAN.md §6 for the size-calculation step and config/strategy_v0.yaml
for the parameters.

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError("sizing.py is a stub.")


if __name__ == "__main__":
    raise SystemExit(main())
