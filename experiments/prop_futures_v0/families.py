"""families — pre-registered DAY-FLAT intraday families for the prop_futures_v0 bake-off.

Each family reuses orb_engine.simulate_trade (the verified honest fill core: rule-8 stop-wins,
adverse slip, EOD flatten). All are MARKET/taker entries (no resting limits -> sidesteps the maker
adverse-selection that killed level_scalp_v0). One entry per day max. Pre-registered BEFORE any
design result is read; the grid + survivor rule live in screen_families.py.

Families (all day-flat, flat by session close):
  gap_fade        — RTH opens with a gap > g*ATR vs prior RTH close -> FADE toward prior close (target=prior close)
  gap_cont        — same gap -> trade WITH the gap, t*ATR target / s*ATR stop
  vwap_revert     — intraday price stretched > k*ATR from session VWAP (after warmup) -> fade back to VWAP
  afternoon_trend — at 14:00 ET, take the day's direction (move>m*ATR) and ride to the close (momentum continuation)
  pre_rth_break   — breakout of the 00:00-09:30 ET pre-RTH range during RTH (ride to close or R-target)

Causality: every signal uses only data <= its decision bar; entries that need a "next bar" fill at the
next bar's open (+slip); gap/afternoon entries act at the bar whose open/level they observe. ATR and
prior-close are prior-day (shifted). VWAP is cumulative within RTH up to the signal bar only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orb_engine import Spec, build_dataset, simulate_trade  # noqa: E402


def _hhmm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


# --------------------------------------------------------------------------- per-day context

def _context(df: pd.DataFrame, open_m: int, close_m: int):
    """prior_close (prior RTH last close) + atr (prior 14-day mean RTH range), keyed by date_et."""
    rth = df[(df["mod"] >= open_m) & (df["mod"] < close_m)]
    g = rth.groupby("date_et")
    last_close = g["close"].last()
    day_range = g["high"].max() - g["low"].min()
    prior_close = last_close.shift(1)
    atr = day_range.shift(1).rolling(14, min_periods=5).mean()
    return prior_close.to_dict(), atr.to_dict()


# --------------------------------------------------------------------------- families
# Each returns (is_long, entry_idx, entry_price, stop, target, use_target) or None.
# day arrays: m,o,hi,lo,cl,vol (numpy, one ET date). pc=prior_close, atr=ATR(price). slip=price.

def fam_gap_fade(m, o, hi, lo, cl, vol, pc, atr, slip, open_m, close_m, cutoff_m, p):
    if np.isnan(pc) or np.isnan(atr) or atr <= 0:
        return None
    ri = np.flatnonzero(m == open_m)
    if not len(ri):
        return None
    ei = int(ri[0]); op = o[ei]
    gap = op - pc
    if abs(gap) < p["g"] * atr:
        return None
    is_long = gap < 0  # fade toward prior close
    entry = op + slip * (1 if is_long else -1)
    stop = entry - p["s"] * atr if is_long else entry + p["s"] * atr
    target = pc
    if (is_long and target <= entry) or ((not is_long) and target >= entry):
        return None  # degenerate (open already past prior close)
    return (is_long, ei, entry, stop, target, True)


def fam_gap_cont(m, o, hi, lo, cl, vol, pc, atr, slip, open_m, close_m, cutoff_m, p):
    if np.isnan(pc) or np.isnan(atr) or atr <= 0:
        return None
    ri = np.flatnonzero(m == open_m)
    if not len(ri):
        return None
    ei = int(ri[0]); op = o[ei]
    gap = op - pc
    if abs(gap) < p["g"] * atr:
        return None
    is_long = gap > 0  # continue with the gap
    entry = op + slip * (1 if is_long else -1)
    stop = entry - p["s"] * atr if is_long else entry + p["s"] * atr
    target = entry + p["t"] * atr if is_long else entry - p["t"] * atr
    return (is_long, ei, entry, stop, target, True)


def fam_vwap_revert(m, o, hi, lo, cl, vol, pc, atr, slip, open_m, close_m, cutoff_m, p):
    if np.isnan(atr) or atr <= 0:
        return None
    rth = (m >= open_m) & (m < close_m)
    idx = np.flatnonzero(rth)
    if len(idx) < 30:
        return None
    typ = (hi[idx] + lo[idx] + cl[idx]) / 3.0
    v = np.where(vol[idx] > 0, vol[idx], 1.0)
    vwap = np.cumsum(typ * v) / np.cumsum(v)
    warm = open_m + 30  # no entries in the first 30 min (VWAP unstable)
    for k_local, gi in enumerate(idx):
        if m[gi] < warm or m[gi] >= cutoff_m:
            continue
        dev = cl[gi] - vwap[k_local]
        if abs(dev) < p["k"] * atr:
            continue
        if gi + 1 > idx[-1]:
            return None
        ei = gi + 1  # enter next bar open (causal)
        is_long = dev < 0  # below VWAP -> revert up
        entry = o[ei] + slip * (1 if is_long else -1)
        stop = entry - p["s"] * atr if is_long else entry + p["s"] * atr
        target = vwap[k_local]  # frozen VWAP at signal
        if (is_long and target <= entry) or ((not is_long) and target >= entry):
            return None
        return (is_long, ei, entry, stop, target, True)
    return None


def fam_afternoon_trend(m, o, hi, lo, cl, vol, pc, atr, slip, open_m, close_m, cutoff_m, p):
    if np.isnan(atr) or atr <= 0:
        return None
    ri = np.flatnonzero(m == open_m)
    si = np.flatnonzero((m >= p["hour_m"]) & (m < close_m))
    if not len(ri) or not len(si):
        return None
    open930 = o[int(ri[0])]
    sig = int(si[0])
    move = cl[sig] - open930
    if abs(move) < p["m"] * atr:
        return None
    if sig + 1 > np.flatnonzero(m < close_m)[-1]:
        return None
    ei = sig + 1
    is_long = move > 0
    entry = o[ei] + slip * (1 if is_long else -1)
    stop = entry - p["s"] * atr if is_long else entry + p["s"] * atr
    return (is_long, ei, entry, stop, np.nan, False)  # ride to close


def fam_pre_rth_break(m, o, hi, lo, cl, vol, pc, atr, slip, open_m, close_m, cutoff_m, p):
    pre = m < open_m
    if pre.sum() < 30:
        return None
    pre_high = hi[pre].max(); pre_low = lo[pre].min()
    tick_buf = p["buf_atr"] * atr if (not np.isnan(atr) and atr > 0) else 0.0
    win = np.flatnonzero((m >= open_m) & (m < cutoff_m))
    long_trig = pre_high + tick_buf; short_trig = pre_low - tick_buf
    li = next((i for i in win if hi[i] >= long_trig), None)
    si = next((i for i in win if lo[i] <= short_trig), None)
    if li is None and si is None:
        return None
    if li is not None and si is not None:
        if li == si:
            return None
        is_long = li < si
    else:
        is_long = li is not None
    ei = li if is_long else si
    trig = long_trig if is_long else short_trig
    entry = (max(o[ei], trig) + slip) if is_long else (min(o[ei], trig) - slip)
    stop = pre_low if is_long else pre_high
    risk = (entry - stop) if is_long else (stop - entry)
    if risk <= 0:
        return None
    use_target = p["target_R"] > 0
    target = (entry + p["target_R"] * risk) if is_long else (entry - p["target_R"] * risk)
    return (is_long, int(ei), entry, stop, target, use_target)


def fam_accum_poc_break(m, o, hi, lo, cl, vol, pc, atr, slip, open_m, close_m, cutoff_m, p):
    """Accumulation -> breakout -> retest of the accumulation's volume POC -> continuation.

    Accumulation = the initial balance (first ib_min of RTH). Its volume profile POC (n_bins, volume
    spread across each bar's [low,high]) is the magnet. After price breaks the IB by buf_atr*ATR, wait
    for a pullback that touches the POC, then ENTER on the resume (price re-crosses the broken IB edge).
    Stop = the pullback extreme +/- stop_buf_atr*ATR; target = target_R (0 = ride to close). Day-flat.
    All causal: POC from IB only; break/retest/resume scanned forward; stop excludes the entry bar.
    """
    if np.isnan(atr) or atr <= 0:
        return None
    A = p["ib_min"]; nb = p["n_bins"]
    ib_end = open_m + A
    ib = (m >= open_m) & (m < ib_end)
    if ib.sum() < max(5, A // 2):
        return None
    ib_hi = hi[ib].max(); ib_lo = lo[ib].min()
    if ib_hi <= ib_lo:
        return None
    rth_idx = np.flatnonzero(m < close_m)
    if not len(rth_idx):
        return None
    last_rth = int(rth_idx[-1])
    # volume profile of the IB (accumulation) -> POC
    centers = (np.linspace(ib_lo, ib_hi, nb + 1)[:-1] + np.linspace(ib_lo, ib_hi, nb + 1)[1:]) / 2
    vp = np.zeros(nb)
    span_px = ib_hi - ib_lo
    for bl, bh, bv in zip(lo[ib], hi[ib], vol[ib]):
        lo_k = min(nb - 1, max(0, int((bl - ib_lo) / span_px * nb)))
        hi_k = min(nb - 1, max(0, int((bh - ib_lo) / span_px * nb)))
        vp[lo_k:hi_k + 1] += bv / (hi_k - lo_k + 1)
    poc = float(centers[int(np.argmax(vp))])
    buf = p["buf_atr"] * atr
    long_trig = ib_hi + buf; short_trig = ib_lo - buf
    win = [i for i in range(len(m)) if ib_end <= m[i] < cutoff_m]
    # 1) breakout
    bk = None; is_long = None
    for i in win:
        if hi[i] >= long_trig:
            bk, is_long = i, True; break
        if lo[i] <= short_trig:
            bk, is_long = i, False; break
    if bk is None:
        return None
    # 2) retest of POC
    rt = next((j for j in range(bk + 1, last_rth + 1) if lo[j] <= poc <= hi[j]), None)
    if rt is None:
        return None
    # 3) resume: re-cross the broken IB edge
    resume_trig = long_trig if is_long else short_trig
    ei = next((k for k in range(rt + 1, last_rth + 1)
               if (is_long and hi[k] >= resume_trig) or ((not is_long) and lo[k] <= resume_trig)), None)
    if ei is None:
        return None
    entry = (max(o[ei], resume_trig) + slip) if is_long else (min(o[ei], resume_trig) - slip)
    sbuf = p["stop_buf_atr"] * atr
    seg_lo = lo[bk:ei].min(); seg_hi = hi[bk:ei].max()   # pullback extreme, excludes entry bar (causal)
    stop = (seg_lo - sbuf) if is_long else (seg_hi + sbuf)
    risk = (entry - stop) if is_long else (stop - entry)
    if risk <= 0:
        return None
    use_target = p["target_R"] > 0
    target = (entry + p["target_R"] * risk) if is_long else (entry - p["target_R"] * risk)
    return (is_long, ei, entry, stop, target, use_target)


def fam_accum_detect_break(m, o, hi, lo, cl, vol, pc, atr, slip, open_m, close_m, cutoff_m, p):
    """DETECTED accumulation -> breakout (direction-agnostic detection; direction from the break).

    Models 'accumulating orders' as a window where heavy volume trades in a TIGHT range = absorption
    (distinct from quiet drift: tight range but LIGHT volume). Scans RTH for the first W-bar window with
    range <= c_range*ATR (contraction) AND window volume >= c_vol * causal-baseline (the expanding mean
    per-bar volume so far * W) = elevated participation. That box is the accumulation zone. Trade its
    breakout (either side), stop = opposite box edge (tight), target = target_R (0 = ride to close).
    Causal: box uses only bars up to its end; baseline is expanding (<= t); breakout scanned forward.
    """
    if np.isnan(atr) or atr <= 0:
        return None
    W = p["win"]; c_range = p["c_range"]; c_vol = p["c_vol"]; buf = p["buf_atr"] * atr
    rth = np.flatnonzero((m >= open_m) & (m < close_m))
    if len(rth) < W + 5:
        return None
    H = hi[rth]; L = lo[rth]; V = vol[rth]; MM = m[rth]
    cum = np.cumsum(V)
    box = None
    for ti in range(W - 1, len(rth)):
        if MM[ti] >= cutoff_m:
            break  # box must close before the cutoff so a breakout can still happen
        whi = H[ti - W + 1:ti + 1].max(); wlo = L[ti - W + 1:ti + 1].min()
        rng = whi - wlo
        volw = V[ti - W + 1:ti + 1].sum()
        baseline = (cum[ti] / (ti + 1)) * W  # expanding mean per-bar volume * W (causal)
        if 0 < rng <= c_range * atr and volw >= c_vol * baseline:
            box = (int(rth[ti]), whi, wlo); break
    if box is None:
        return None
    g0, whi, wlo = box
    long_trig = whi + buf; short_trig = wlo - buf
    last_rth = int(rth[-1])
    is_long = None; bki = None
    for k in range(g0 + 1, last_rth + 1):
        if hi[k] >= long_trig:
            is_long, bki = True, k; break
        if lo[k] <= short_trig:
            is_long, bki = False, k; break
    if bki is None:
        return None
    ei = bki
    entry = (max(o[ei], long_trig) + slip) if is_long else (min(o[ei], short_trig) - slip)
    stop = wlo if is_long else whi  # opposite accumulation-box edge
    risk = (entry - stop) if is_long else (stop - entry)
    if risk <= 0:
        return None
    use_target = p["target_R"] > 0
    target = (entry + p["target_R"] * risk) if is_long else (entry - p["target_R"] * risk)
    return (is_long, ei, entry, stop, target, use_target)


FAMILIES = {
    "gap_fade": fam_gap_fade,
    "accum_detect_break": fam_accum_detect_break,
    "gap_cont": fam_gap_cont,
    "vwap_revert": fam_vwap_revert,
    "afternoon_trend": fam_afternoon_trend,
    "pre_rth_break": fam_pre_rth_break,
    "accum_poc_break": fam_accum_poc_break,
}


# --------------------------------------------------------------------------- runner

def run_family(df: pd.DataFrame, spec: Spec, fam: str, params: dict,
               session_open="09:30", session_close="16:00", cutoff_min=150, slip_ticks=1) -> pd.DataFrame:
    open_m = _hhmm(session_open); close_m = _hhmm(session_close); cutoff_m = open_m + cutoff_min
    slip = slip_ticks * spec.tick_size
    fn = FAMILIES[fam]
    pc_map, atr_map = _context(df, open_m, close_m)
    rows = []
    for date, day in df.groupby("date_et", sort=True):
        m = day["mod"].to_numpy(); o = day["open"].to_numpy(); hi = day["high"].to_numpy()
        lo = day["low"].to_numpy(); cl = day["close"].to_numpy(); vol = day["volume"].to_numpy()
        pc = pc_map.get(date, np.nan); atr = atr_map.get(date, np.nan)
        sig = fn(m, o, hi, lo, cl, vol, pc, atr, slip, open_m, close_m, cutoff_m, params)
        if sig is None:
            continue
        is_long, ei, entry, stop, target, use_target = sig
        tr = simulate_trade(m, o, hi, lo, cl, ei, is_long, entry, stop, target,
                            use_target, slip, spec, close_m)
        if tr is None:
            continue
        tr.update({"date": pd.Timestamp(date).date(), "year": pd.Timestamp(date).year,
                   "side": "long" if is_long else "short", "family": fam})
        rows.append(tr)
    return pd.DataFrame(rows)
