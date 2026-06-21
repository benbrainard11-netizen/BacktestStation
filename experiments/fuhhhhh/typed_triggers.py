"""Iteration 3.1 (fixed) — TYPED, multi-timeframe sweep + SMT detection.

Tagged sweep family so the DATA classifies which sweeps work. Each sweep carries:
  swept_type, swept_tf, swept_dist_atr, overshoot_tk, confirm_5m/15m, n_levels_swept.
SMT is detected per swing timeframe, tagged smt_tf.

CAUSALITY: everything gates on ABSOLUTE time (epoch ns), not ms-of-day. A resampled
candle [s, s+tf) is usable only once closed (s+tf <= t). Fractal pivots are known only
SWING_K candles late. SMT compares ES vs NQ candles aligned by ABSOLUTE TIMESTAMP
(NQ reindexed onto ES's bin grid) with a build-time start-array equality assert — this
replaces the earlier integer-index alignment that compared candles hours apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import common as C

SWING_TFS = (5, 15, 60)        # minutes
SWEEP_RECENT_BARS = 10
PROX_MAX_ATR = 1.5
RECENT_SWINGS = 3
NS_MIN = 60_000_000_000


def _fractal(low: np.ndarray, high: np.ndarray, k: int):
    n = len(low)
    lo, hi = [], []
    for i in range(k, n - k):
        if low[i] == low[i - k:i + k + 1].min() and (low[i] < low[i - 1] or low[i] < low[i + 1]):
            lo.append(i)
        if high[i] == high[i - k:i + k + 1].max() and (high[i] > high[i - 1] or high[i] > high[i + 1]):
            hi.append(i)
    return lo, hi


@dataclass
class TfSwings:
    start_abs: np.ndarray   # candle start, epoch ns (absolute)
    close_abs: np.ndarray   # start + tf
    low: np.ndarray
    high: np.ndarray
    close: np.ndarray
    lo_piv: list
    hi_piv: list

    def levels_at(self, t_abs: int, k: int):
        out = []
        n = len(self.close_abs)
        for piv, tag, arr in ((self.lo_piv, "swingLo", self.low), (self.hi_piv, "swingHi", self.high)):
            usable = [i for i in piv if self.close_abs[min(i + k, n - 1)] <= t_abs]
            for i in usable[-RECENT_SWINGS:]:
                if np.isfinite(arr[i]):
                    out.append((float(arr[i]), tag))
        return out


def _resample(bars: pd.DataFrame, tf: int, ref_index=None):
    agg = bars.set_index("et").resample(f"{tf}min", label="left", closed="left").agg(
        {"high": "max", "low": "min", "close": "last"})
    if ref_index is not None:
        agg = agg.reindex(ref_index)
    else:
        agg = agg.dropna()
    return agg


def _tf_from_agg(agg, with_pivots: bool) -> TfSwings:
    start_abs = agg.index.asi8  # epoch ns (UTC), tz-aware index -> absolute
    low, high, close = (agg["low"].to_numpy(float), agg["high"].to_numpy(float),
                        agg["close"].to_numpy(float))
    if with_pivots and len(low) >= 2 * C.SWING_K + 2:
        # pivots need contiguous finite arrays; ES agg is dropna'd so it's fine
        lo, hi = _fractal(low, high, C.SWING_K)
    else:
        lo, hi = [], []
    tf_ns = int((start_abs[1] - start_abs[0])) if len(start_abs) > 1 else NS_MIN
    return TfSwings(start_abs, start_abs + tf_ns, low, high, close, lo, hi)


@dataclass
class TypedDayCtx:
    et_ns: np.ndarray                 # RTH 1m bar start, epoch ns (decision series)
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    swings: dict = field(default_factory=dict)      # tf -> ES TfSwings (with pivots)
    nq_swings: dict = field(default_factory=dict)    # tf -> NQ TfSwings ALIGNED to ES bins
    session: dict = field(default_factory=dict)

    @classmethod
    def build(cls, es_rth, es_full, nq_full, session: dict):
        es_rth = es_rth.sort_values("et").reset_index(drop=True)
        et_ns = pd.DatetimeIndex(es_rth["et"]).asi8
        swings, nq_sw = {}, {}
        for tf in SWING_TFS:
            es_agg = _resample(es_full, tf)
            swings[tf] = _tf_from_agg(es_agg, with_pivots=True)
            if nq_full is not None and len(nq_full):
                nq_agg = _resample(nq_full, tf, ref_index=es_agg.index)  # ALIGN by timestamp
                nq_t = _tf_from_agg(nq_agg, with_pivots=False)
                assert np.array_equal(nq_t.start_abs, swings[tf].start_abs), "NQ/ES bin misalign"
                nq_sw[tf] = nq_t
        return cls(et_ns, es_rth["open"].to_numpy(float), es_rth["high"].to_numpy(float),
                   es_rth["low"].to_numpy(float), es_rth["close"].to_numpy(float),
                   swings, nq_sw, session)


def level_menu(ctx: TypedDayCtx, t_abs: int) -> list[tuple]:
    menu = []
    for typ, tf in (("pdh", "1D"), ("pdl", "1D"), ("onh", "ON"), ("onl", "ON"),
                    ("orh", "OR"), ("orl", "OR")):
        v = ctx.session.get(typ)
        if v is not None and np.isfinite(v):
            menu.append((float(v), typ, tf))
    for tf in SWING_TFS:
        sw = ctx.swings.get(tf)
        if sw is not None and len(sw.start_abs):
            for price, tag in sw.levels_at(t_abs, C.SWING_K):
                menu.append((price, tag, f"{tf}m"))
    return menu


def _confirm_flags(ctx: TypedDayCtx, level: float, bullish: bool, t_abs: int) -> dict:
    """Did the last COMPLETED 5m/15m candle CLOSE back inside (above for bull) the level?"""
    out = {}
    for tf in (5, 15):
        sw = ctx.swings.get(tf)
        ok = False
        if sw is not None and len(sw.close_abs):
            done = np.where(sw.close_abs <= t_abs)[0]
            if len(done):
                cl = sw.close[done[-1]]
                ok = bool(cl > level) if bullish else bool(cl < level)
        out[f"confirm_{tf}m"] = ok
    return out


def detect_sweep(ctx: TypedDayCtx, idx: int, atr: float):
    if idx < SWEEP_RECENT_BARS + 1:
        return None
    t_abs = int(ctx.et_ns[idx] + NS_MIN)        # decision time = close of the idx 1m bar
    rec = slice(idx - SWEEP_RECENT_BARS + 1, idx + 1)
    rec_lo, rec_hi = ctx.l[rec].min(), ctx.h[rec].max()
    price = ctx.c[idx]
    buf = C.SWEEP_BUF_TK * C.TICK
    best, n_lo, n_hi = None, 0, 0
    for lv, typ, tf in level_menu(ctx, t_abs):
        if abs(lv - price) > PROX_MAX_ATR * atr:
            continue
        is_low = typ in ("pdl", "onl", "orl", "swingLo")
        is_high = typ in ("pdh", "onh", "orh", "swingHi")
        if is_low and rec_lo < lv - buf and price > lv:
            overshoot = (lv - rec_lo) / C.TICK
            n_lo += 1
            cand = (1, lv, typ, tf, overshoot)
        elif is_high and rec_hi > lv + buf and price < lv:
            overshoot = (rec_hi - lv) / C.TICK
            n_hi += 1
            cand = (-1, lv, typ, tf, overshoot)
        else:
            continue
        if best is None or cand[4] > best[4]:
            best = cand
    if best is None:
        return None
    direction, lv, typ, tf, overshoot = best
    tags = {"swept_type": typ, "swept_tf": tf, "swept_dist_atr": abs(lv - price) / atr,
            "overshoot_tk": overshoot, "n_levels_swept": (n_lo if direction > 0 else n_hi)}
    tags.update(_confirm_flags(ctx, lv, direction > 0, t_abs))
    return direction, tags


def _smt_one(es_sw: TfSwings, nq_sw: TfSwings, t_abs: int, k: int) -> int:
    """SMT on one TF: ES new extreme NQ fails to confirm. NQ aligned to ES bins (#5 fix)."""
    if not len(es_sw.start_abs) or nq_sw is None:
        return 0
    n = len(es_sw.close_abs)
    out = 0
    lo = [i for i in es_sw.lo_piv if es_sw.close_abs[min(i + k, n - 1)] <= t_abs]
    if len(lo) >= 2:
        p1, p2 = lo[-2], lo[-1]
        if np.isfinite(nq_sw.low[p1]) and np.isfinite(nq_sw.low[p2]):
            if es_sw.low[p2] < es_sw.low[p1] and nq_sw.low[p2] > nq_sw.low[p1]:
                out = 1
    hi = [i for i in es_sw.hi_piv if es_sw.close_abs[min(i + k, n - 1)] <= t_abs]
    if len(hi) >= 2:
        p1, p2 = hi[-2], hi[-1]
        if np.isfinite(nq_sw.high[p1]) and np.isfinite(nq_sw.high[p2]):
            if es_sw.high[p2] > es_sw.high[p1] and nq_sw.high[p2] < nq_sw.high[p1]:
                out = -1 if out == 0 else 0
    return out


def detect_smt(ctx: TypedDayCtx, idx: int):
    t_abs = int(ctx.et_ns[idx] + NS_MIN)
    for tf in SWING_TFS:
        es_sw, nq_sw = ctx.swings.get(tf), ctx.nq_swings.get(tf)
        if es_sw is None or nq_sw is None:
            continue
        d = _smt_one(es_sw, nq_sw, t_abs, C.SWING_K)
        if d != 0:
            return d, {"smt_tf": f"{tf}m"}
    return None
