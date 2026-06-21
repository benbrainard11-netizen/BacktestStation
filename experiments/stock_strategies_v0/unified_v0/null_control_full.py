"""Decisive test for breakout_v0: does the breakout TIMING beat a RANDOM day in the same stock?
Same daily let-run mechanic (enter next open, 1xATR stop, 3xATR chandelier, 40d, R-capped +/-10) on
(a) breakout days (close>20d-high, liquid) vs (b) random non-breakout days in the SAME liquid universe.
If breakout >> random => real breakout edge (the +0.676 is earned). If breakout ~= random => the let-run
R is generic momentum geometry, not a breakout edge (capturable on any day). Full universe 2019-2026.
Run with backend\\.venv\\Scripts\\python.exe -u.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
K_ATR, CHAND, HOLD, FRIC, RCAP = 1.0, 3.0, 40, 0.0015, 10.0
RNG = np.random.default_rng(0)


def letrun(o, h, l, c, i, atr):
    """enter open[i+1], 1xATR stop, chandelier let-run, max HOLD; return R capped +/-10."""
    if i + 1 >= len(c) or atr <= 0:
        return None
    entry = o[i + 1] * (1 + FRIC)
    stop = entry - K_ATR * atr
    risk = entry - stop
    if risk <= 0:
        return None
    cost_R = 2 * FRIC * entry / risk
    cur, run_hi = stop, entry
    end = min(i + 1 + HOLD, len(c))
    R = (c[end - 1] - entry) / risk
    for j in range(i + 1, end):
        if o[j] <= cur:
            R = (o[j] - entry) / risk; break
        if l[j] <= cur:
            R = (cur - entry) / risk; break
        run_hi = max(run_hi, h[j]); cur = max(cur, run_hi - CHAND * atr)
    return float(np.clip(R - cost_R, -RCAP, RCAP))


def main():
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    cs = set(pd.read_parquet(POLY / "meta.parquet")["ticker"])
    df = df[(df["ticker"].isin(cs)) & (df["date"] >= 20190101)].sort_values(["ticker", "date"])
    brk_rows, rnd_rows = [], []
    for t, g in df.groupby("ticker", sort=False):
        o = g["open"].to_numpy(float); h = g["high"].to_numpy(float)
        l = g["low"].to_numpy(float); c = g["close"].to_numpy(float); v = g["volume"].to_numpy(float)
        dts = g["date"].to_numpy().astype(int); n = len(c)
        if n < 60:
            continue
        pc = np.roll(c, 1)
        tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
        atr = pd.Series(tr).rolling(14).mean().to_numpy()
        hi20 = pd.Series(h).rolling(20).max().shift(1).to_numpy()
        dvol = pd.Series(c * v).rolling(20).mean().shift(1).to_numpy()
        elig = np.arange(21, n - HOLD - 1)
        elig = elig[(c[elig] >= 5) & (dvol[elig] >= 1e6) & np.isfinite(atr[elig]) & (atr[elig] > 0)]
        if not len(elig):
            continue
        is_brk = (c > hi20)
        brk = elig[is_brk[elig]]
        non = elig[~is_brk[elig]]
        for i in brk:
            r = letrun(o, h, l, c, i, atr[i])
            if r is not None:
                brk_rows.append((int(dts[i]) // 10000, r))
        # matched random non-breakout days (same count as breakouts for this ticker)
        if len(non) and len(brk):
            pick = RNG.choice(non, size=min(len(brk), len(non)), replace=False)
            for j in pick:
                r = letrun(o, h, l, c, j, atr[j])
                if r is not None:
                    rnd_rows.append((int(dts[j]) // 10000, r))
    B = pd.DataFrame(brk_rows, columns=["yr", "R"]); Rn = pd.DataFrame(rnd_rows, columns=["yr", "R"])
    print(f"breakout trades {len(B):,} | random-day trades {len(Rn):,}\n")
    print(f"=== NULL CONTROL: breakout days vs random non-breakout days (same mechanic, +/-10 cap) ===")
    print(f"  BREAKOUT  meanR {B['R'].mean():+.3f}  median {B['R'].median():+.2f}")
    print(f"  RANDOM    meanR {Rn['R'].mean():+.3f}  median {Rn['R'].median():+.2f}")
    print(f"  DELTA (breakout - random): {B['R'].mean()-Rn['R'].mean():+.3f}\n")
    print("  by year (breakout / random / delta):")
    for y in sorted(set(B['yr']) & set(Rn['yr'])):
        b = B[B.yr == y]['R'].mean(); r = Rn[Rn.yr == y]['R'].mean()
        print(f"    {y}: brk {b:+.3f}  rnd {r:+.3f}  delta {b-r:+.3f}")
    print("\nREAD: delta > 0 across years => breakout TIMING adds real edge (the +0.676 is earned).")
    print("delta ~0 / negative => the let-run R is generic geometry; the breakout selection adds nothing.")


if __name__ == "__main__":
    main()
