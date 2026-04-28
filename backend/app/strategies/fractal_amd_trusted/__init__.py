"""Fractal AMD trusted strategy plugin (in progress).

Destination for the engine-plugin port of the trusted multi-year strategy
that produced +274R / 40.8% WR over 2024-2026 (586 trades). Reference
implementation: `C:/Fractal-AMD/scripts/trusted_multiyear_bt.py` —
verified to reproduce `samples/fractal_trusted_multiyear/trades.csv`
exactly when re-run 2026-04-28 PM.

What's done so far:
- `orderflow.py` — list[Bar] port of compute_continuation_of (verified
  bit-identical to the pandas original on smoke window).

What's not done — see README.md:
- Strategy plugin (config.py, strategy.py) mirroring trusted's
  HTF-once-per-day scan + find_nearest_unfilled_fvg selection +
  next-bar-open entry semantics.
- Regression test asserting the plugin reproduces +274R / 586 trades.

Until the plugin lands, use `backend/scripts/run_trusted_backtest.py`
to reproduce the trusted backtest on demand.
"""

from app.strategies.fractal_amd_trusted.orderflow import compute_continuation_of

__all__ = ["compute_continuation_of"]
