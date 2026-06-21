"""LONG-REVERSAL scout (Ben's idea): instead of buying breakout HIGHS (dead), buy the LOW of a
pullback. Two flavors: (A) 'low of a continuation' = STRONG/uptrending stock pulls back to a
short-term low -> buy the bounce; (B) 'bottom' = beaten-down stock turning. Clean 9yr Polygon
(delisted incl), market-relative forward returns, honest (enter next-day open), by-year + CI.
Question: does dip-buying conditioned on STRENGTH have an edge (unlike chasing breakouts)?
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
OUT = Path(__file__).resolve().parent / "out"; OUT.mkdir(parents=True, exist_ok=True)
MIN_PRICE, MIN_DVOL = 5.0, 5e6


def main():
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    cs = set(pd.read_parquet(POLY / "meta.parquet")["ticker"])
    meta_active = dict(zip(pd.read_parquet(POLY / "meta.parquet")["ticker"], pd.read_parquet(POLY / "meta.parquet")["active"]))
    spy = df[df["ticker"] == "SPY"].sort_values("date")
    spy_c = dict(zip(spy["date"].astype(int), spy["close"]))
    spy_s = pd.Series(spy["close"].to_numpy(), index=spy["date"].astype(int))
    spy_ret6 = (spy_s / spy_s.shift(126) - 1).to_dict()
    g = df[df["ticker"].isin(cs)].sort_values(["ticker", "date"])

    rows = []
    for t, d in g.groupby("ticker", sort=False):
        if len(d) < 200:
            continue
        c = d["close"].to_numpy(); o = d["open"].to_numpy(); h = d["high"].to_numpy()
        lo = d["low"].to_numpy(); v = d["volume"].to_numpy(); dts = d["date"].to_numpy().astype(int)
        n = len(c)
        ma50 = pd.Series(c).rolling(50).mean().to_numpy()
        low10 = pd.Series(c).rolling(10).min().to_numpy()
        high20 = pd.Series(h).rolling(20).max().to_numpy()
        dvol = pd.Series(c * v).rolling(20).mean().shift(1).to_numpy()
        ret6 = c / np.roll(c, 126) - 1
        act = bool(meta_active.get(t, False))
        for i in range(130, n - 21):
            if c[i] > low10[i] + 1e-9:                  # trigger: NEW 10-day low close (oversold)
                continue
            if c[i] < MIN_PRICE or np.isnan(dvol[i]) or dvol[i] < MIN_DVOL or np.isnan(ma50[i]):
                continue
            di = dts[i]
            s0 = spy_c.get(di)
            d5, d10, d20 = spy_c.get(dts[i + 5]), spy_c.get(dts[i + 10]), spy_c.get(dts[i + 20])
            if not (s0 and d5 and d10 and d20):
                continue
            entry = o[i + 1]
            if entry <= 0:
                continue
            rows.append({
                "ticker": t, "date": int(di), "active": act,
                "ret6": ret6[i], "rs6": ret6[i] - (spy_ret6.get(di) or 0),
                "above_ma50": int(c[i] > ma50[i]),
                "pullback": c[i] / high20[i] - 1 if high20[i] else np.nan,   # depth below recent high
                "x5": (c[i + 5] / entry - 1) - (d5 / s0 - 1),
                "x10": (c[i + 10] / entry - 1) - (d10 / s0 - 1),
                "x20": (c[i + 20] / entry - 1) - (d20 / s0 - 1),
            })
    S = pd.DataFrame(rows).dropna(subset=["x10"])
    S.to_parquet(OUT / "reversal_events.parquet")
    S["yr"] = S["date"] // 10000
    print(f"oversold (10d-low) events: {len(S):,} | tickers {S['ticker'].nunique():,} | active {S['active'].mean()*100:.0f}%")

    def boot(x, n=2000):
        x = x.dropna().to_numpy(); idx = np.random.default_rng(0).integers(0, len(x), (n, len(x)))
        return np.percentile(x[idx].mean(1) * 100, [2.5, 97.5])

    def show(sub, lbl):
        if len(sub) < 50:
            print(f"  {lbl:32s} n={len(sub)} (few)"); return
        ci = boot(sub["x10"])
        print(f"  {lbl:32s} n={len(sub):6d}  x5 {sub.x5.mean()*100:+.2f}%  x10 {sub.x10.mean()*100:+.2f}% "
              f"CI[{ci[0]:+.2f},{ci[1]:+.2f}]  x20 {sub.x20.mean()*100:+.2f}%  win10 {(sub.x10>0).mean()*100:.0f}%")

    print("\n=== does the oversold dip bounce? (market-relative) ===")
    show(S, "ALL oversold dips")
    print("\n  -- A) LOW OF A CONTINUATION (strong context) --")
    strong = S[(S.above_ma50 == 1) & (S.rs6 > 0)]
    show(strong, "strong (above MA50 + RS>0)")
    show(strong[strong.pullback > -0.15], "  strong + shallow dip (>-15%)")
    show(strong[strong.pullback <= -0.15], "  strong + deep dip (<=-15%)")
    print("\n  -- B) BOTTOM FISH (weak/downtrend context) --")
    weak = S[(S.above_ma50 == 0) | (S.rs6 <= 0)]
    show(weak, "weak (below MA50 or RS<=0)")
    print("\n  -- strong-dip by year (the live cell) --")
    for y in sorted(strong["yr"].unique()):
        s = strong[strong.yr == y]
        if len(s) > 20:
            print(f"    {y}: x10 {s.x10.mean()*100:+5.2f}%  n={len(s):4d}  win {(s.x10>0).mean()*100:.0f}%")
    print("\nREAD: strong+dip x10 CI>0 and beats ALL/weak => buying the low of a continuation is a real edge.")


if __name__ == "__main__":
    main()
