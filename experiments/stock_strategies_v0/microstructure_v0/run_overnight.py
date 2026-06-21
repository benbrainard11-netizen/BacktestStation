"""Fresh less-crowded lane #1: the OVERNIGHT vs INTRADAY return decomposition (a documented structural
effect, not a directional pattern). Per stock-day: overnight = open[t]/close[t-1]-1, intraday =
close[t]/open[t]-1. Tests on the clean 9yr survivorship-free universe: (1) is overnight systematically
> intraday, and persistent by year? (2) where is it concentrated (price/liquidity tier)? (3) is there a
LOWER-TURNOVER cross-sectional way to harvest it (sort by trailing overnight return)? Honest on costs.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
MIN_PRICE, MIN_DVOL = 5.0, 5e6


def main():
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    cs = set(pd.read_parquet(POLY / "meta.parquet")["ticker"])
    df = df[df["ticker"].isin(cs)].sort_values(["ticker", "date"])
    rows = []
    for t, g in df.groupby("ticker", sort=False):
        o = g["open"].to_numpy(); c = g["close"].to_numpy(); v = g["volume"].to_numpy()
        dts = g["date"].to_numpy().astype(int); n = len(c)
        if n < 60:
            continue
        pc = np.roll(c, 1)
        on = o / pc - 1                      # overnight (close[t-1]->open[t])
        intr = c / o - 1                     # intraday (open[t]->close[t])
        dvol = pd.Series(c * v).rolling(20).mean().shift(1).to_numpy()
        liq = (c >= MIN_PRICE) & (dvol >= MIN_DVOL)
        on_tr = pd.Series(on).rolling(20).mean().shift(1).to_numpy()   # trailing overnight (causal)
        for i in range(21, n):
            if not liq[i] or not np.isfinite(on[i]) or not np.isfinite(intr[i]) or abs(on[i]) > 0.5:
                continue
            rows.append((t, dts[i], on[i], intr[i], c[i] / pc[i] - 1, on_tr[i], c[i], dvol[i]))
    R = pd.DataFrame(rows, columns=["ticker", "date", "on", "intr", "tot", "on_tr", "price", "dvol"])
    R["yr"] = R["date"] // 10000
    ann = 252
    print(f"stock-days: {len(R):,} | tickers {R['ticker'].nunique():,} | {R['date'].min()}..{R['date'].max()}\n")
    print("=== (1) OVERNIGHT vs INTRADAY (equal-weight stock-day mean, annualized) ===")
    print(f"  overnight: {R['on'].mean()*ann*100:+.1f}%/yr   intraday: {R['intr'].mean()*ann*100:+.1f}%/yr   "
          f"total: {R['tot'].mean()*ann*100:+.1f}%/yr")
    print("  by year (overnight / intraday, %/yr):")
    for y in sorted(R["yr"].unique()):
        s = R[R.yr == y]
        print(f"    {y}: ON {s['on'].mean()*ann*100:+6.1f}  INTRA {s['intr'].mean()*ann*100:+6.1f}")

    print("\n=== (2) where is it concentrated? (by price tier) ===")
    R["ptier"] = pd.cut(R["price"], [0, 10, 30, 100, 1e9], labels=["<$10", "$10-30", "$30-100", ">$100"])
    for p in ["<$10", "$10-30", "$30-100", ">$100"]:
        s = R[R.ptier == p]
        print(f"  {p:8s} n={len(s):8d}  ON {s['on'].mean()*ann*100:+6.1f}%/yr  INTRA {s['intr'].mean()*ann*100:+6.1f}%/yr")

    print("\n=== (3) lower-turnover harvest: sort by TRAILING overnight return -> next-day overnight? ===")
    Rt = R.dropna(subset=["on_tr"]).copy()
    Rt["dec"] = Rt.groupby("date")["on_tr"].transform(lambda x: pd.qcut(x.rank(method="first"), 5, labels=False) if len(x) >= 25 else np.nan)
    g = Rt.dropna(subset=["dec"]).groupby("dec")["on"].mean() * ann * 100
    print("  next-day overnight by trailing-overnight quintile (Q4=highest): " + " ".join(f"Q{int(d)}:{v:+.1f}" for d, v in g.items()))
    print(f"  long top - short bottom quintile (overnight): {(g.iloc[-1]-g.iloc[0]):+.1f}%/yr (gross, pre-cost)")
    print("\n  COST REALITY: capturing overnight = 1 round-trip/day (~252/yr). At ~10bps RT that's ~25%/yr cost ->")
    print("  the broad overnight premium is real but turnover-killed; only a low-turnover tilt could harvest it.")
    print("\nREAD: overnight >> intraday + persistent by year => the effect is real (fresh, structural). Then the")
    print("question is a low-turnover way to harvest it (cross-sectional tilt) net of the heavy trade-at-open/close cost.")


if __name__ == "__main__":
    main()
