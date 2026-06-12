"""Per-touch reaction outcomes in the FADE frame (PLAN Phase 0, rules 15/A2).

Frame: a touch is scored as the FADE of the level — approach from below = short at the
level, from above = long. Everything is measured on the EXIT-side quote (short exits by
buying the ask, long by selling the bid), never mid: on a 3-tick-spread symbol a 4-tick
mid bounce is not a 4-tick capture.

g = profit-ticks of the fade on the exit-side quote. Per touch we store FIRST-PASSAGE
TIMES to every win level k (g >= k) and loss level j (g <= -j) in the spec GRID — the
full P(revert k before through j) grid is derived in analysis by comparing times, and
"neither within horizon" keeps its denominator seat via g_end (time-stop value).
Truncation at the horizon, the level's valid_to, or day end is flagged, never dropped.

Importable; no CLI; synthetic-testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from spec import GRID_TICKS

HORIZONS_S = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800}
REJECT_K = 8  # "first rejection" = fade reaches +8 ticks (retest/overshoot anchor)


def touch_outcomes(
    ts: pd.DatetimeIndex,
    bid: np.ndarray,
    ask: np.ndarray,
    mid: np.ndarray,
    i0: int,
    i_hi: int,
    level: float,
    from_below: bool,
    tick: float,
    horizon_s: int = 1800,
) -> dict | None:
    """Outcome fields for one touch; None if the forward window is degenerate."""
    t0 = ts[i0]
    hz = int(ts.searchsorted(t0 + pd.Timedelta(seconds=horizon_s)))
    i1 = min(hz, i_hi)
    n = i1 - i0
    if n < 2:
        return None
    q = ask[i0:i1] if from_below else bid[i0:i1]  # exit-side quote of the fade
    g = (level - q) / tick if from_below else (q - level) / tick
    gm = (level - mid[i0:i1]) / tick if from_below else (mid[i0:i1] - level) / tick
    cmax = np.maximum.accumulate(g)
    cmin = np.minimum.accumulate(g)
    rel = np.asarray((ts[i0:i1] - t0).total_seconds(), dtype=float)

    out: dict = {"truncated": bool(hz > i_hi), "g_end": float(g[-1])}
    for k in GRID_TICKS:
        idx = int(np.searchsorted(cmax, float(k)))
        out[f"t_win_{k}"] = float(rel[idx]) if idx < n else np.nan
    for j in GRID_TICKS:
        idx = int(np.searchsorted(-cmin, float(j)))
        out[f"t_loss_{j}"] = float(rel[idx]) if idx < n else np.nan
    for name, s in HORIZONS_S.items():
        ih = int(np.searchsorted(rel, float(s), side="right")) - 1
        out[f"mfe_{name}"] = float(cmax[ih]) if ih >= 0 else np.nan
        out[f"mae_{name}"] = float(cmin[ih]) if ih >= 0 else np.nan

    # stop-offset + retest anchors (PLAN retest table; external_research upgrade #4):
    # overshoot = how far mid went THROUGH the level before the first 8-tick rejection;
    # retest = after rejecting 8 ticks, does mid come back within 2 ticks of the level?
    k8 = int(np.searchsorted(cmax, float(REJECT_K)))
    rejected = k8 < n
    out["rejected_8"] = bool(rejected)
    out["overshoot_ticks"] = float(
        max(0.0, -float(np.min(gm[: max(k8 if rejected else n, 1)])))
    )
    out["retest_after_8"] = bool((np.abs(gm[k8:]) <= 2.0).any()) if rejected else None
    return out
