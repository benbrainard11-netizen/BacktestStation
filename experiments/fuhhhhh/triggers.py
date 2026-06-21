"""Iteration 3 trigger detectors — "is the move to the wall starting?"

Three independent, causal detectors, each returning a direction (+1 up / -1 down / 0):
  sweep — price pokes beyond a recent reference extreme then reclaims (liquidity sweep)
  smt   — ES vs NQ swing divergence (one makes a new extreme, the other fails to)
  flow  — MBP-1 signed-volume z-shift toward a side

All operate on bars CLOSED by the decision time (caller passes the last-closed index).
None of them peek forward. SMT swing pivots are fractal and only become known SWING_K
bars after they form, so at index i only pivots with p <= i-SWING_K are visible.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

import common as C


def fractal_pivots(low: np.ndarray, high: np.ndarray, k: int):
    """Confirmed swing-low and swing-high pivot indices (min/max over [i-k, i+k]).

    A pivot at i is only *known* at i+k; callers must filter to p <= idx-k.
    """
    n = len(low)
    lo_piv, hi_piv = [], []
    for i in range(k, n - k):
        win_l = low[i - k : i + k + 1]
        win_h = high[i - k : i + k + 1]
        if low[i] == win_l.min() and (low[i] < low[i - 1] or low[i] < low[i + 1]):
            lo_piv.append(i)
        if high[i] == win_h.max() and (high[i] > high[i - 1] or high[i] > high[i + 1]):
            hi_piv.append(i)
    return np.array(lo_piv, dtype=int), np.array(hi_piv, dtype=int)


@dataclass
class DayCtx:
    """Per-day causal arrays for ES + NQ-aligned, plus precomputed pivots."""
    et: np.ndarray          # ES bar ET timestamps (datetime64)
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    nq_h: np.ndarray        # NQ high aligned to ES timestamps (ffill)
    nq_l: np.ndarray
    es_lo_piv: np.ndarray
    es_hi_piv: np.ndarray

    @classmethod
    def build(cls, es: pd.DataFrame, nq: pd.DataFrame | None) -> "DayCtx":
        es = es.sort_values("et").reset_index(drop=True)
        h, l = es["high"].to_numpy(float), es["low"].to_numpy(float)
        if nq is not None and len(nq):
            al = pd.merge_asof(es[["et"]], nq[["et", "high", "low"]].sort_values("et"),
                               on="et", direction="backward")
            nq_h, nq_l = al["high"].to_numpy(float), al["low"].to_numpy(float)
        else:
            nq_h = nq_l = np.full(len(es), np.nan)
        lo_piv, hi_piv = fractal_pivots(l, h, C.SWING_K)
        return cls(es["et"].to_numpy(), es["open"].to_numpy(float), h, l,
                   es["close"].to_numpy(float), nq_h, nq_l, lo_piv, hi_piv)


def sweep_dir(ctx: DayCtx, idx: int) -> int:
    """Liquidity sweep + reclaim of a recent reference extreme, as of bar idx."""
    lb, rec = C.SWEEP_LOOKBACK_MIN, C.SWEEP_RECENT_MIN
    if idx < lb:
        return 0
    ref = slice(idx - lb, idx - rec + 1)        # older reference window
    recent = slice(idx - rec + 1, idx + 1)      # the poke+reclaim window (incl. idx)
    ref_lo, ref_hi = ctx.l[ref].min(), ctx.h[ref].max()
    buf = C.SWEEP_BUF_TK * C.TICK
    c = ctx.c[idx]
    swept_dn = ctx.l[recent].min() < ref_lo - buf and c > ref_lo   # swept sell-side, reclaimed up
    swept_up = ctx.h[recent].max() > ref_hi + buf and c < ref_hi   # swept buy-side, reclaimed down
    if swept_dn and not swept_up:
        return 1
    if swept_up and not swept_dn:
        return -1
    return 0


def smt_dir(ctx: DayCtx, idx: int, fresh_bars: int = 20) -> int:
    """ES/NQ swing divergence using the two most recent CONFIRMED pivots <= idx-K."""
    if not np.isfinite(ctx.nq_l[idx]):
        return 0
    cutoff = idx - C.SWING_K
    lo = ctx.es_lo_piv[(ctx.es_lo_piv <= cutoff)]
    hi = ctx.es_hi_piv[(ctx.es_hi_piv <= cutoff)]
    out = 0
    if len(lo) >= 2 and (idx - lo[-1]) <= fresh_bars:
        p1, p2 = lo[-2], lo[-1]
        if np.isfinite(ctx.nq_l[p1]) and np.isfinite(ctx.nq_l[p2]):  # review F10: gate at compare
            if ctx.l[p2] < ctx.l[p1] and ctx.nq_l[p2] > ctx.nq_l[p1]:   # ES LL, NQ HL -> bullish
                out = 1
    if len(hi) >= 2 and (idx - hi[-1]) <= fresh_bars:
        p1, p2 = hi[-2], hi[-1]
        if np.isfinite(ctx.nq_h[p1]) and np.isfinite(ctx.nq_h[p2]):
            if ctx.h[p2] > ctx.h[p1] and ctx.nq_h[p2] < ctx.nq_h[p1]:   # ES HH, NQ LH -> bearish
                out = -1 if out == 0 else 0   # conflicting bull+bear -> no signal
    return out


def flow_dir(sv_z: float) -> int:
    """MBP signed-volume z-shift: strong aggressive buying/selling = directional flow."""
    if not np.isfinite(sv_z):
        return 0
    if sv_z >= C.FLOW_Z:
        return 1
    if sv_z <= -C.FLOW_Z:
        return -1
    return 0
