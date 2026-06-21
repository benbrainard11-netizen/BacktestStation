"""HAC/Newey-West significance for overlapping straddle windows.

Variable DTE in [1,7] means holding windows overlap, so the per-entry P&L series is autocorrelated.
LOCKED: HAC lag = 7 (max DTE). Report MDE before any verdict.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HAC_LAG = 7


def newey_west_se(x: pd.Series, lag: int = HAC_LAG) -> float:
    """HAC standard error of the MEAN of x (Bartlett kernel)."""
    v = pd.Series(x).dropna().to_numpy(dtype=float)
    n = len(v)
    if n < 2:
        return float("nan")
    d = v - v.mean()
    s = float(d @ d) / n
    for k in range(1, min(lag, n - 1) + 1):
        s += 2.0 * (1.0 - k / (lag + 1.0)) * float(d[k:] @ d[:-k]) / n
    return float(np.sqrt(max(s, 0.0) / n))


def summarize(x: pd.Series, lag: int = HAC_LAG) -> dict:
    """mean, HAC SE/t, MDE_95/80 for a per-entry metric series (e.g. pnl_pct)."""
    v = pd.Series(x).dropna()
    n = len(v)
    mean = float(v.mean()) if n else float("nan")
    se = newey_west_se(v, lag)
    return {
        "n": n,
        "mean": mean,
        "hac_se": se,
        "hac_t": mean / se if se else float("nan"),
        "mde_95": 1.96 * se if se == se else float("nan"),
        "mde_80_power": (1.96 + 0.84) * se if se == se else float("nan"),
    }
