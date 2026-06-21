"""Clean re-validation: run BOTH setups (sweep-reclaim + FVG), BOTH sides, on the CLEAN MBP-1 bars.
Does anything survive real mid-price data? both-sides-+ = real alpha; one-side-+ matching drift = beta; else dead.

Run: backend/.venv/Scripts/python.exe experiments/asset_profiles_v0/clean_revalidate.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out" / "clean_bars"
TICK = {"RB.c.0": 0.0001, "HO.c.0": 0.0001, "BZ.c.0": 0.01, "CL.c.0": 0.01, "NG.c.0": 0.001}
LB, K, MAXWAIT, HOLD, TRAIL = 48, 6, 48, 48, 1.0


def trail_exit(h, l, c, e, end, entry, stop, risk, side):
    peak, tstop = entry, stop
    for t in range(e + 1, end + 1):
        if (l[t] <= tstop) if side == 1 else (h[t] >= tstop):
            return (tstop - entry) / risk if side == 1 else (entry - tstop) / risk
        if side == 1:
            peak = max(peak, h[t]); tstop = max(tstop, peak - TRAIL * risk)
        else:
            peak = min(peak, l[t]); tstop = min(tstop, peak + TRAIL * risk)
    return (c[end] - entry) / risk if side == 1 else (entry - c[end]) / risk


def sweep(b, side):
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    ts, n = b.index, len(b)
    lvl = (b["low"].rolling(LB, min_periods=LB // 2).min() if side == 1
           else b["high"].rolling(LB, min_periods=LB // 2).max()).shift(1).to_numpy()
    pen = (l < lvl) if side == 1 else (h > lvl)
    starts = np.where((pen & ~np.r_[False, pen[:-1]]) & ~np.isnan(lvl))[0]
    rows = []
    for t0 in starts:
        L = lvl[t0]
        t_r = next((t for t in range(t0, min(t0 + K, n - 1) + 1)
                    if (c[t] > L if side == 1 else c[t] < L)), -1)
        if t_r < 0:
            continue
        entry = c[t_r]
        stop = l[t0:t_r + 1].min() if side == 1 else h[t0:t_r + 1].max()
        risk = (entry - stop) if side == 1 else (stop - entry)
        if risk <= 0:
            continue
        r = trail_exit(h, l, c, t_r, min(t_r + HOLD, n - 1), entry, stop, risk, side)
        rows.append((ts[t_r], r, risk))
    return pd.DataFrame(rows, columns=["date", "r", "risk"])


def fvg(b, side):
    h, l, c = b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy()
    ts, n = b.index, len(b)
    rows = []
    for i in range(2, n):
        if (side == 1 and not (l[i] > h[i - 2])) or (side == -1 and not (h[i] < l[i - 2])):
            continue
        ztrig = l[i] if side == 1 else h[i]
        zbreak = h[i - 2] if side == 1 else l[i - 2]
        fired, tap, e = False, None, -1
        for t in range(i + 1, min(i + MAXWAIT, n - 1) + 1):
            fired = fired or ((l[t] <= ztrig) if side == 1 else (h[t] >= ztrig))
            if not fired:
                continue
            tap = (l[t] if side == 1 else h[t]) if tap is None else (min(tap, l[t]) if side == 1 else max(tap, h[t]))
            if (l[t] < zbreak) if side == 1 else (h[t] > zbreak):
                break
            if (c[t] > ztrig) if side == 1 else (c[t] < ztrig):
                e = t
                break
        if e < 0:
            continue
        entry = c[e]
        risk = (entry - tap) if side == 1 else (tap - entry)
        if risk <= 0:
            continue
        r = trail_exit(h, l, c, e, min(e + HOLD, n - 1), entry, tap, risk, side)
        rows.append((ts[e], r, risk))
    return pd.DataFrame(rows, columns=["date", "r", "risk"])


def cell(tr, tick):
    if len(tr) < 30:
        return f"{'n<30':>14}"
    nr = tr["r"] - 2 * tick / tr["risk"]
    m = nr.groupby(tr["date"].dt.tz_localize(None).dt.to_period("M")).mean()
    return f"{nr.mean():+.3f}/{(m > 0).sum():2}of{len(m):2}"


def main() -> int:
    print(f"{'sym':8} {'drift%':>7} | {'SWEEP Long':>14} {'SWEEP Short':>14} | {'FVG Long':>14} {'FVG Short':>14}")
    for sym in TICK:
        f = OUT / f"{sym}.parquet"
        if not f.exists():
            continue
        b = pd.read_parquet(f).sort_index()
        tick = TICK[sym]
        drift = float(np.log(b["close"].iloc[-1] / b["close"].iloc[0]) * 100)
        print(f"{sym:8} {drift:+7.0f} | {cell(sweep(b, 1), tick):>14} {cell(sweep(b, -1), tick):>14} | "
              f"{cell(fvg(b, 1), tick):>14} {cell(fvg(b, -1), tick):>14}")
    print("\n(E[R net@2tk] / months-positive.  both-sides-+ = real; one-side-+ ~ drift = beta; else dead)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
