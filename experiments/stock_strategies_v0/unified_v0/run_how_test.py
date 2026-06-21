"""Test the HOW (intraday-strength entry + 1xATR stop + chandelier let-run) WITHOUT the breakout filter.
Trigger = intraday cross of the PRIOR-DAY high (generic 'showing strength today', NOT a 20d-high breakout),
on the RANDOM liquid-day minute sample. Same mechanic + R-cap +/-10 as breakout_v0. Question: does the
geometry earn on a broad/random selection (=> the edge is the mechanic, not breakouts), and survive honest
costs? Also split out the subset that ALSO happened to be 20d-high breakouts. Run w/ backend\\.venv\\Scripts\\python.exe -u.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import run_intraday_entry as rie   # minute_rth, forward_daily, BUF_ENTRY, FRICTION, K_ATR

POLY = Path(r"D:\data\processed\stocks\polygon")
RCAP = 10.0
man = pd.read_parquet(POLY / "random_minute_manifest.parquet")


def main():
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    df = df[df["ticker"].isin(set(man["ticker"]))].sort_values(["ticker", "date"])
    D = {}
    for t, g in df.groupby("ticker", sort=False):
        o, h, l, c = (g[x].to_numpy(float) for x in ("open", "high", "low", "close"))
        dts = g["date"].to_numpy().astype(int); pc = np.roll(c, 1)
        tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
        atr = pd.Series(tr).rolling(14).mean().to_numpy()
        hi20 = pd.Series(h).rolling(20).max().shift(1).to_numpy()
        D[t] = dict(o=o, h=h, l=l, c=c, atr=atr, hi20=hi20, idx={int(x): i for i, x in enumerate(dts)})

    rows = []
    for r in man.itertuples(index=False):
        d = D.get(r.ticker)
        if d is None:
            continue
        i = d["idx"].get(int(r.date))
        if i is None or i < 21 or i >= len(d["c"]) - 1:
            continue
        atr = d["atr"][i - 1]
        if np.isnan(atr) or atr <= 0:
            continue
        level = d["h"][i - 1]                                 # prior-day high (generic intraday strength)
        bars = rie.minute_rth(r.ticker, int(r.date), d["o"][i])
        if bars is None:
            continue
        trig = level * (1 + rie.BUF_ENTRY)
        cr = np.where(bars[:, 1] >= trig)[0]
        if not len(cr):
            continue                                          # didn't show strength today -> no trade
        k = cr[0]
        entry = max(trig, bars[k, 0]) * (1 + rie.FRICTION)
        stop = entry - rie.K_ATR * atr
        risk = entry - stop
        if risk <= 0:
            continue
        cost_R = 2 * rie.FRICTION * entry / risk
        was_brk = int(d["c"][i] > d["hi20"][i]) if not np.isnan(d["hi20"][i]) else 0
        # same-day minute stop, else daily let-run
        stopped = False
        for rr in range(k + 1, len(bars)):
            if bars[rr, 2] <= stop:
                R = (min(stop, bars[rr, 0]) - entry) / risk - cost_R; stopped = True; break
        if not stopped:
            R, *_ = rie.forward_daily(d, i, entry, stop, atr, None)
            R -= cost_R
        rows.append((int(r.date) // 10000, float(np.clip(R, -RCAP, RCAP)), was_brk))

    A = pd.DataFrame(rows, columns=["yr", "R", "was_brk"])
    print(f"prior-day-high-cross trades on random days: {len(A):,}  ({A['was_brk'].mean()*100:.0f}% also 20d-high breakouts)\n")
    print(f"=== the HOW (intraday strength + 1xATR stop + let-run), NO breakout filter ===")
    print(f"  ALL: meanR {A['R'].mean():+.3f}  median {A['R'].median():+.2f}  win {(A['R']>0).mean()*100:.0f}%  "
          f"drop-top1% {A['R'][A['R']<=A['R'].quantile(.99)].mean():+.3f}")
    nb = A[A.was_brk == 0]; bb = A[A.was_brk == 1]
    print(f"  NON-breakout strength : meanR {nb['R'].mean():+.3f}  n={len(nb):,}")
    print(f"  ALSO-breakout subset  : meanR {bb['R'].mean():+.3f}  n={len(bb):,}")
    print("\n  by year (ALL):")
    for y in sorted(A.yr.unique()):
        s = A[A.yr == y]
        if len(s) > 30:
            print(f"    {y}: {s['R'].mean():+.3f} n={len(s):4d}")
    print("\n  (R already nets 0.15%/side; these are often small/mid names where 0.3-0.5%/side is realistic,")
    print("   so the deployable number is lower than shown.)")
    print("\nREAD: NON-breakout meanR ~ breakout meanR => the edge is the HOW (mechanic), breakout label irrelevant.")
    print("NON-breakout <= 0 => the mechanic needs SOME selection; breakout just isn't the right one.")


if __name__ == "__main__":
    main()
