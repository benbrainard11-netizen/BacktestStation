"""Ben's idea: do edges live where institutions AREN'T (neglected/less-occupied names), and is there a
retail sweet spot (neglected enough for a bigger edge, liquid enough to trade small)? Proxy 'institutional
occupation' by dollar-volume tier (low dvol = less occupied). Re-run cross-sectional 12-1 momentum (which
tied SPY in liquid names) BY TIER -- including the neglected $0.5-10M zone we filtered out -- GROSS and
NET of tier-appropriate spread costs. If the neglected tier's NET long-short >> the liquid tier, the
idea works. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
# dollar-volume tiers (proxy for institutional occupation) + assumed round-trip spread cost
TIERS = [("micro $0.3-1M", 0.3e6, 1e6, 0.030), ("small $1-5M", 1e6, 5e6, 0.012),
         ("mid $5-25M", 5e6, 25e6, 0.004), ("liq $25-100M", 25e6, 100e6, 0.0015),
         ("mega >$100M", 100e6, 1e15, 0.0008)]


def main():
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    cs = set(pd.read_parquet(POLY / "meta.parquet")["ticker"])
    df = df[df["ticker"].isin(cs)].copy()
    df["dt"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d")
    df["dvol"] = df["close"] * df["volume"]
    me = df.groupby("ticker").resample("ME", on="dt").agg(close=("close", "last"), dvol=("dvol", "mean"))
    close = me["close"].unstack(0); dvol = me["dvol"].unstack(0)
    trail = close.shift(1) / close.shift(12) - 1            # 12-1 momentum (causal)
    fwd = close.shift(-1) / close - 1                       # next-month return
    px_ok = close >= 1.0                                    # exclude sub-$1 junk

    print(f"{close.shape[1]} names x {close.shape[0]} months ({close.index[0].date()}..{close.index[-1].date()})")
    print("\n=== cross-sectional 12-1 momentum long-short BY occupation tier (monthly %) ===")
    print(f"  {'tier':14s} {'avg names':>9s} {'gross L-S':>9s} {'spread':>7s} {'NET L-S':>8s} {'NET/yr':>8s} {'top-dec':>8s}")
    for name, lo, hi, cost in TIERS:
        inb = (dvol >= lo) & (dvol < hi) & px_ok
        ls, td, ns = [], [], []
        for t in close.index:
            tr, fr, ok = trail.loc[t], fwd.loc[t], inb.loc[t]
            m = tr.notna() & fr.notna() & ok
            if m.sum() < 30:
                continue
            x, y = tr[m], fr[m]; q = x.rank(pct=True)
            top, bot = y[q >= 0.9], y[q <= 0.1]
            ls.append(top.mean() - bot.mean()); td.append(top.mean()); ns.append(m.sum())
        if len(ls) < 12:
            print(f"  {name:14s}  (too few months)"); continue
        gross = np.nanmean(ls); net = gross - 2 * cost      # long-short = 2 legs traded
        print(f"  {name:14s} {int(np.mean(ns)):9d} {gross*100:+8.2f}% {cost*100:6.1f}% {net*100:+7.2f}% "
              f"{net*12*100:+7.1f}% {np.nanmean(td)*100:+7.2f}%")

    print("\nNOTE: long-only top-decile (no shorting the junk) is the realistic retail version -> see 'top-dec'.")
    print("READ: if a NEGLECTED tier (micro/small) has NET L-S (or top-dec) >> the liquid tiers, edges DO live")
    print("where institutions aren't AND survive small-book costs. If spreads eat it (NET ~0/neg), the trap holds.")


if __name__ == "__main__":
    main()
