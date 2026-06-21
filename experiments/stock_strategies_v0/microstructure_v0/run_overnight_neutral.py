"""Market-NEUTRAL overnight: each day rank liquid stocks by TRAILING overnight return, go long the top
quintile / short the bottom quintile, capture that day's overnight (close->open). Strips the overnight
market beta that gave the long-only capture its -31% / 2022 -20% crash. Honest cost: long-short = 2
round-trips/day (buy+short at close, exit both at open) + borrow on the short. Reports net by year,
Sharpe, maxDD, and correlation to SPY (should be ~0 if truly neutral). Run w/ backend\\.venv\\Scripts\\python.exe.
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
    parts = []
    for t, g in df.groupby("ticker", sort=False):
        o = g["open"].to_numpy(); c = g["close"].to_numpy(); v = g["volume"].to_numpy()
        if len(c) < 60:
            continue
        pc = np.roll(c, 1)
        dvol = pd.Series(c * v).rolling(20).mean().shift(1).to_numpy()
        liq = (c >= MIN_PRICE) & (dvol >= MIN_DVOL)
        on = o / pc - 1
        on = np.where(np.isfinite(on) & (np.abs(on) < 0.5), on, np.nan)
        on_tr = pd.Series(on).rolling(20).mean().shift(1).to_numpy()    # causal trailing-overnight signal
        parts.append(pd.DataFrame({"date": g["date"].to_numpy().astype(int), "on": on,
                                   "sig": on_tr, "liq": liq}))
    A = pd.concat(parts, ignore_index=True)
    A = A[A["liq"]].dropna(subset=["on", "sig"])

    rows = []
    for d, g in A.groupby("date"):
        if len(g) < 50:
            continue
        q = g["sig"].rank(pct=True)
        top = g["on"][q >= 0.8].mean(); bot = g["on"][q <= 0.2].mean()
        rows.append((d, top - bot, top))             # long-short overnight ; long-only top
    L = pd.DataFrame(rows, columns=["date", "ls", "longtop"]).set_index("date")
    L.index = pd.to_datetime(L.index.astype(str), format="%Y%m%d")
    spy = df[df["ticker"] == "SPY"].copy()
    spy["dt"] = pd.to_datetime(spy["date"].astype(int).astype(str), format="%Y%m%d")
    spy_on = (spy.set_index("dt")["open"] / spy.set_index("dt")["close"].shift(1) - 1).reindex(L.index)

    def metrics(x, label):
        x = x.dropna()
        ann = (1 + x).prod() ** (252 / len(x)) - 1
        shp = x.mean() / x.std() * np.sqrt(252) if x.std() else 0
        eq = (1 + x).cumprod(); dd = (eq / eq.cummax() - 1).min()
        cr = np.corrcoef(x, spy_on.reindex(x.index).fillna(0))[0, 1]
        print(f"  {label:30s} CAGR {ann*100:+6.1f}%  Sharpe {shp:+.2f}  maxDD {dd*100:5.0f}%  corr(SPY-on) {cr:+.2f}")

    print(f"days {len(L)}\n=== market-NEUTRAL overnight long-short, cost sweep (2 round-trips/day + borrow) ===")
    for rt in (1, 2, 3):
        cost = 2 * rt / 1e4 + 0.5 / 1e4                # 2 RT + ~0.5bp borrow/day
        metrics(L["ls"] - cost, f"long-short @ {rt}bps/leg")
    print("\n=== by year (long-short net @2bps/leg) ===")
    net = L["ls"] - (2 * 2 / 1e4 + 0.5 / 1e4)
    for y in sorted(set(L.index.year)):
        s = net[net.index.year == y]
        if len(s) > 50:
            print(f"    {y}: {((1+s).prod()-1)*100:+6.1f}%  Sharpe {s.mean()/s.std()*np.sqrt(252):+.2f}")
    print("\n=== vs the long-only-top (high-overnight names, carries beta) @2bps ===")
    metrics(L["longtop"] - 0.0002, "long-only top quintile")
    print("\nREAD: long-short corr(SPY)~0 + NO 2022 crash + net>0 => market-neutral overnight alpha (the fix works).")
    print("net<=0 after 2x cost / still crashes => the cross-sectional alpha too small vs double cost.")


if __name__ == "__main__":
    main()
