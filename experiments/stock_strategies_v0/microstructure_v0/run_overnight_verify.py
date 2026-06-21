"""Overnight premium — robustness + execution verification (realism already passed: daily open = real
09:30 open, 100% match). Capture = long liquid-universe close->open daily, equal-weight. Tests: by-year
NET at 2bps, EX-2020/21 (the huge overnight years), execution-cost sweep, Sharpe/maxDD, breadth.
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
    on, dts, cnt = [], [], []
    for t, g in df.groupby("ticker", sort=False):
        o = g["open"].to_numpy(); c = g["close"].to_numpy(); v = g["volume"].to_numpy()
        if len(c) < 40:
            continue
        pc = np.roll(c, 1)
        dvol = pd.Series(c * v).rolling(20).mean().shift(1).to_numpy()
        liq = (c >= MIN_PRICE) & (dvol >= MIN_DVOL)
        ov = o / pc - 1
        ok = liq & np.isfinite(ov) & (np.abs(ov) < 0.5)
        d = g["date"].to_numpy().astype(int)
        on.append(ov[ok]); dts.append(d[ok])
    A = pd.DataFrame({"date": np.concatenate(dts), "on": np.concatenate(on)})
    day = A.groupby("date")["on"].agg(["mean", "size"])
    day.index = pd.to_datetime(day.index.astype(str), format="%Y%m%d")
    r = day["mean"]                                   # daily overnight-capture (equal-weight liquid universe)

    def metrics(x, label, ppy=252):
        x = x.dropna()
        ann = (1 + x).prod() ** (ppy / len(x)) - 1
        shp = x.mean() / x.std() * np.sqrt(ppy) if x.std() else 0
        eq = (1 + x).cumprod(); dd = (eq / eq.cummax() - 1).min()
        print(f"  {label:28s} CAGR {ann*100:+6.1f}%  Sharpe {shp:+.2f}  maxDD {dd*100:5.0f}%")

    print(f"daily obs {len(r)} | avg {int(day['size'].mean()):,} liquid names/day\n")
    print("=== overnight capture, NET @ 2bps round-trip/day ===")
    net2 = r - 0.0002
    metrics(net2, "ALL (2016-2026)")
    metrics(net2[net2.index.year.isin([2020, 2021]) == False], "EX-2020/21")
    metrics(net2[net2.index.year >= 2023], "2023-2026 (recent)")
    print("\n  by year (NET @2bps):")
    for y in sorted(set(r.index.year)):
        s = net2[net2.index.year == y]
        if len(s) > 50:
            print(f"    {y}: {((1+s).prod()-1)*100:+6.1f}%  Sharpe {s.mean()/s.std()*np.sqrt(252):+.2f}")
    print("\n=== execution-cost sensitivity (CAGR / Sharpe, full period) ===")
    for bps in (1, 2, 3, 5):
        metrics(r - bps / 1e4, f"@ {bps}bps round-trip")
    print("\nREAD: NET positive ex-2020/21 + most years + survives ~2-3bps => robust, tradeable overnight edge.")
    print("only 2020/21 / dies <2bps => regime-bound or execution-impossible.")


if __name__ == "__main__":
    main()
