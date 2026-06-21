"""Tail accounting for short-vol P&L -- mandatory in v1 (it's a risk premium, not alpha).

A short-vol series can be mean-positive and still un-harvestable if the left tail is fat. So we report
CVaR (expected loss in the worst alpha%), worst loss, and big-loss probabilities, plus the
mean/|CVaR| ratio the pass/fail gates on.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def cvar(x: pd.Series, alpha: float = 0.05) -> float:
    """Conditional VaR: mean of the worst alpha-fraction of outcomes (a NEGATIVE number for losses)."""
    v = pd.Series(x).dropna().to_numpy(dtype=float)
    if len(v) == 0:
        return float("nan")
    q = np.quantile(v, alpha)
    tail = v[v <= q]
    return float(tail.mean()) if len(tail) else float(q)


def prob_worse_than(x: pd.Series, threshold: float) -> float:
    """P(value < threshold) -- e.g. prob_worse_than(pnl_R, -3)."""
    v = pd.Series(x).dropna()
    return float((v < threshold).mean()) if len(v) else float("nan")


def tail_report(pnl_pct: pd.Series, pnl_R: pd.Series, alpha: float = 0.05) -> dict:
    """The frozen v1 tail bundle for one bucket."""
    cvar_pct = cvar(pnl_pct, alpha)
    mean_pct = float(pd.Series(pnl_pct).dropna().mean())
    return {
        "mean_pnl_pct": mean_pct,
        "cvar5_pct": cvar_pct,
        "cvar5_R": cvar(pnl_R, alpha),
        "worst_loss_R": float(pd.Series(pnl_R).dropna().min()),
        "p_R_lt_-3": prob_worse_than(pnl_R, -3),
        "p_R_lt_-5": prob_worse_than(pnl_R, -5),
        "mean_over_abs_cvar5": mean_pct / abs(cvar_pct) if cvar_pct not in (0, float("nan")) and np.isfinite(cvar_pct) and cvar_pct != 0 else float("nan"),
    }
