"""Fractal AMD trusted strategy plugin.

Engine-plugin port of `C:/Fractal-AMD/scripts/trusted_multiyear_bt.py`
which produced +274R / 40.8% WR over 2024-2026 (586 trades). Reference
output: `samples/fractal_trusted_multiyear/trades.csv` — verified to be
bit-equivalent to a fresh re-run of the script on 2026-04-28 PM.

Components:
- `config.py` — knobs (BUFFER, MAX_HOLD, target_r, gates, dedup).
- `strategy.py` — `FractalAMDTrusted` Strategy plugin. Incremental
  port of trusted's per-day batch logic.
- `orderflow.py` — list[Bar] port of compute_continuation_of (the
  cont_of >= 3 entry gate). Bit-identical to the pandas original on
  test windows.

Use `backend/scripts/run_trusted_backtest.py` to run the canonical
script directly. Use `FractalAMDTrusted` via the engine for in-app
backtests + (after Phase 3) for live execution on ben-247.
"""

from app.strategies.fractal_amd_trusted.config import FractalAMDTrustedConfig
from app.strategies.fractal_amd_trusted.orderflow import compute_continuation_of
from app.strategies.fractal_amd_trusted.strategy import FractalAMDTrusted

__all__ = [
    "FractalAMDTrusted",
    "FractalAMDTrustedConfig",
    "compute_continuation_of",
]
