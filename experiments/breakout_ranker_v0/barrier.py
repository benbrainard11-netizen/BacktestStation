"""The trade construction from the advice, as one honest mechanic shared by the gated
setups AND the null control: arm a stop-buy at pivot+0.10*ATR for TRIG_WIN sessions; on
trigger, run the +2R-before-(-1R) triple barrier over BARRIER_DAYS.

Honest-fill rules (CLAUDE.md #8): gap-through the stop fills at the open (can be worse than
-1R); the target is capped at exactly +2R (never better); stop wins same-bar ties; timeouts
mark to the close. R is gross; `netR` charges one round-trip of FRIC.
"""
from __future__ import annotations

import numpy as np

from common import (
    BARRIER_DAYS, FRIC, RCAP, STOP_ATR, STOP_BUF, STOP_R, TARGET_R, TRIG_ATR, TRIG_WIN,
)


def arm_and_resolve(o, h, l, c, i, pivot, atr_i):
    """Arm a stop-buy at pivot+0.10*ATR; stop = pivot - 1*ATR (advice's tradeable R).
    Returns None if the geometry is unusable, {'triggered':0} if the stop-buy never fired
    in TRIG_WIN, else the resolved trade dict."""
    n = len(c)
    if not (np.isfinite(pivot) and np.isfinite(atr_i) and atr_i > 0):
        return None
    trigger = pivot + TRIG_ATR * atr_i
    arm_end = min(i + 1 + TRIG_WIN, n)
    j = None
    entry = np.nan
    for k in range(i + 1, arm_end):
        if h[k] >= trigger:
            j = k
            entry = max(trigger, o[k])  # gap-up opens fill worse, at the open
            break
    if j is None:
        return {"triggered": 0}
    stop = (pivot - STOP_ATR * atr_i) * (1 - STOP_BUF)
    risk = entry - stop
    if risk <= 0:
        return {"triggered": 0}
    target = entry + TARGET_R * risk
    cost_R = 2 * FRIC * entry / risk
    end = min(j + BARRIER_DAYS, n)
    grossR = None
    win = 0
    outcome = "timeout"
    for k in range(j, end):
        if k > j:  # post-entry bars can gap through either barrier at the open
            if o[k] <= stop:
                grossR, outcome = (o[k] - entry) / risk, "stop"
                break
            if o[k] >= target:
                grossR, win, outcome = TARGET_R, 1, "target"
                break
        hit_stop = l[k] <= stop
        hit_tgt = h[k] >= target
        if hit_stop:  # stop wins same-bar ties (conservative)
            grossR, outcome = -STOP_R, "stop"
            break
        if hit_tgt:
            grossR, win, outcome = TARGET_R, 1, "target"
            break
    if grossR is None:
        grossR = (c[end - 1] - entry) / risk
    grossR = float(np.clip(grossR, -RCAP, RCAP))
    return {
        "triggered": 1,
        "entry_idx": int(j),
        "grossR": grossR,
        "netR": float(np.clip(grossR - cost_R, -RCAP, RCAP)),
        "win": int(win),
        "outcome": outcome,
        "risk_pct": float(risk / entry),
    }
