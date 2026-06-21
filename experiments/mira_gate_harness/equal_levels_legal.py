"""EQUAL HIGHS / LOWS as a liquidity-pool level family (Ben's idea). Unlike stacked_failure_legal
(4 CONSECUTIVE 30m candles), this finds NON-ADJACENT swing pivots at ~the same price = the classic
ICT liquidity pool (a high from hours ago matched by one now; stops rest just beyond). Two+ pivot
highs within tol -> equal_highs level (side=high, short the failed sweep); mirror for lows. Injected
into the honest reclaim engine. LEGAL: a pivot at bar i is confirmed only at close of bar i+W; the
equal level is KNOWN at the 2nd pivot's confirmation (when two equal highs actually exist).

Lookback = current + prior LOOKBACK_DAYS sessions (catches overnight/prior-day pools). Output ->
runs/equal_levels_full.parquet, then flow_mbp1_stack --universe for the drift x zone test.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend"))
import legal_reclaim_bars as LB  # noqa: E402

SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
START, END = dt.date(2025, 5, 1), dt.date(2026, 6, 9)  # MBP-1 window (for the drift x zone test)
SWING_TF = 15        # swing-candle TF (min)
PIVOT_W = 2          # bars each side for a pivot
TOL_FRAC = 0.30      # "equal" if |price diff| <= TOL_FRAC * median candle range
LOOKBACK_DAYS = 2    # swings from current + prior N sessions
_NS = 1_000_000_000
_ORIG = LB.day_levels
FAMS = ["equal_highs", "equal_lows"]


def _pivots(h, l, starts):
    """Return (pivot_highs, pivot_lows) as lists of (price, confirm_ns). confirm = close of bar i+W."""
    W = PIVOT_W
    hi, lo = [], []
    for i in range(W, len(h) - W):
        confirm_ns = int(starts[i + W]) + SWING_TF * 60 * _NS
        win_h, win_l = h[i - W:i + W + 1], l[i - W:i + W + 1]
        if h[i] == win_h.max() and h[i] > win_h.min():
            hi.append((float(h[i]), confirm_ns))
        if l[i] == win_l.min() and l[i] < win_l.max():
            lo.append((float(l[i]), confirm_ns))
    return hi, lo


def patched_day_levels(b, daily, day, tick):
    out = _ORIG(b, daily, day, tick)
    rth_end_ns = LB.et_ns(day, LB.RTH_END)
    lo_date = day - dt.timedelta(days=LOOKBACK_DAYS)
    m = (b.et_date >= lo_date) & (b.et_date <= day) & (b.ts <= rth_end_ns)
    if m.sum() < 30:
        return out
    idx = pd.DatetimeIndex(pd.to_datetime(b.ts[m], utc=True))
    df = pd.DataFrame({"high": b.h[m], "low": b.l[m]}, index=idx)
    c = df.resample(f"{SWING_TF}min", label="left", closed="left").agg(
        {"high": "max", "low": "min"}).dropna()
    if len(c) < 2 * PIVOT_W + 2:
        return out
    tol = TOL_FRAC * float((c["high"] - c["low"]).median())
    piv_hi, piv_lo = _pivots(c["high"].to_numpy(float), c["low"].to_numpy(float), c.index.asi8)

    def emit(pivs, side, fam, ltype):
        seen = set()
        for j in range(1, len(pivs)):
            px_j, cn_j = pivs[j]
            if cn_j > rth_end_ns:
                continue
            matches = [p for p in pivs[:j] if abs(p[0] - px_j) <= tol and p[1] <= cn_j]
            if not matches:
                continue
            prices = [p[0] for p in matches] + [px_j]
            lvl = max(prices) if side == "high" else min(prices)  # stops rest just BEYOND the pool
            k = round(lvl / tick)
            if k in seen:
                continue
            seen.add(k)
            out.append(dict(level_family=fam, level_type=ltype, side=side,
                            level_price=float(lvl), known_ns=cn_j, search_ns=cn_j))

    emit(piv_hi, "high", "equal_highs", "eqhigh_sw")
    emit(piv_lo, "low", "equal_lows", "eqlow_sw")
    return out


LB.day_levels = patched_day_levels


def main() -> int:
    parts = []
    for sym in SYMBOLS:
        res = LB.run_symbol_year(sym, START, END)
        if len(res):
            res = res[res["level_family"].isin(FAMS)].copy()
            parts.append(res)
        n = len(res) if len(res) else 0
        print(f"  {sym}: {n} equal-level attempts", flush=True)
    df = pd.concat(parts, ignore_index=True)
    out = LB.RUNS / "equal_levels_full.parquet"
    df.to_parquet(out, index=False)
    ent = df[df["status"] == "entered"]
    print(f"\nwrote {out}: {len(df)} attempts, {len(ent)} entered")
    for fam, g in ent.groupby("level_family"):
        x = pd.to_numeric(g["trail_2R"], errors="coerce").dropna()
        print(f"  {fam:13s} entered={len(g):5d}  raw meanR={x.mean():+.3f} win={100*(x>0).mean():.0f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
