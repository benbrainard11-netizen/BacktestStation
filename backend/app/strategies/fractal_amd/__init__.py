"""Fractal AMD strategy plugin (scaffold).

Skeleton only -- the actual signal logic lives in `signals.py` (currently
stubs) and gets filled in over multiple sessions. The strategy entry
point that the engine resolves is `FractalAMD` in `strategy.py`.

Reference implementation that the eventual port mirrors:
`C:/Users/benbr/FractalAMD-/production/live_bot.py` (1325 lines) +
`production/backtest.py` (754 lines). See `README.md` for the porting
checklist.
"""

from app.strategies.fractal_amd.strategy import FractalAMD

__all__ = ["FractalAMD"]
