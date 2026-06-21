"""Long-reversal scout v2 — the RIGHT trigger for Ben's idea. v1's 10d-low was downside momentum
(grind-down, keeps falling). The real 'buy the low of a continuation' = a SHARP pullback / oversold
SPIKE in an UPTREND that snaps back, held SHORT. Triggers: (1) sharp 3-day plunge in a strong stock,
(2) RSI(2) extreme oversold in a strong stock, (3) pullback to a rising MA20. Clean 9yr, market-rel,
honest (next-open entry), short holds (x1/x3/x5). Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
MIN_PRICE, MIN_DVOL = 5.0, 5e6


def rsi2(c):
    d = np.diff(c, prepend=c[0])
    g = pd.Series(np.clip(d, 0, None)).rolling(2).mean()
    l = pd.Series(-np.clip(d, None, 0)).rolling(2).mean()
    rs = g / l.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).to_numpy()


def main():
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    meta = pd.read_parquet(POLY / "meta.parquet")
    cs = set(meta["ticker"]); active = dict(zip(meta["ticker"], meta["active"]))
    spy = df[df["ticker"] == "SPY"].sort_values("date")
    spy_c = dict(zip(spy["date"].astype(int), spy["close"]))
    spy_s = pd.Series(spy["close"].to_numpy(), index=spy["date"].astype(int))
    spy_ret6 = (spy_s / spy_s.shift(126) - 1).to_dict()
    g = df[df["ticker"].isin(cs)].sort_values(["ticker", "date"])

    rows = []
    for t, d in g.groupby("ticker", sort=False):
        if len(d) < 200:
            continue
        c = d["close"].to_numpy(); o = d["open"].to_numpy(); dts = d["date"].to_numpy().astype(int)
        v = d["volume"].to_numpy(); n = len(c)
        ma20 = pd.Series(c).rolling(20).mean().to_numpy()
        ma50 = pd.Series(c).rolling(50).mean().to_numpy()
        dvol = pd.Series(c * v).rolling(20).mean().shift(1).to_numpy()
        ret6 = c / np.roll(c, 126) - 1
        ret3 = c / np.roll(c, 3) - 1
        r2 = rsi2(c)
        act = bool(active.get(t, False))
        for i in range(130, n - 6):
            if c[i] < MIN_PRICE or np.isnan(dvol[i]) or dvol[i] < MIN_DVOL or np.isnan(ma50[i]):
                continue
            strong = (c[i] > ma50[i]) and (ret6[i] - (spy_ret6.get(dts[i]) or 0) > 0)
            if not strong:
                continue
            plunge = ret3[i] <= -0.08
            rsi_os = r2[i] < 10
            ma_pull = (abs(c[i] / ma20[i] - 1) <= 0.03) and (ma20[i] > ma20[i - 5]) if not np.isnan(ma20[i]) else False
            if not (plunge or rsi_os or ma_pull):
                continue
            di = dts[i]; s0 = spy_c.get(di)
            s1, s3, s5 = spy_c.get(dts[i + 1]), spy_c.get(dts[i + 3]), spy_c.get(dts[i + 5])
            entry = o[i + 1]
            if not (s0 and s1 and s3 and s5) or entry <= 0:
                continue
            rows.append({
                "ticker": t, "date": int(di), "active": act,
                "plunge": int(plunge), "rsi_os": int(rsi_os), "ma_pull": int(ma_pull),
                "x1": (c[i + 1] / entry - 1) - (s1 / s0 - 1),
                "x3": (c[i + 3] / entry - 1) - (s3 / s0 - 1),
                "x5": (c[i + 5] / entry - 1) - (s5 / s0 - 1),
            })
    S = pd.DataFrame(rows).dropna(subset=["x3"]); S["yr"] = S["date"] // 10000
    Path(__file__).resolve().parent.joinpath("out").mkdir(exist_ok=True)
    S.to_parquet(Path(__file__).resolve().parent / "out" / "reversal_sharp.parquet")
    print(f"sharp-pullback-in-uptrend events: {len(S):,} | tickers {S['ticker'].nunique():,}")

    def boot(x, n=2000):
        x = x.dropna().to_numpy(); idx = np.random.default_rng(0).integers(0, len(x), (n, len(x)))
        return np.percentile(x[idx].mean(1) * 100, [2.5, 97.5])

    def show(sub, lbl):
        if len(sub) < 50:
            print(f"  {lbl:26s} n={len(sub)} (few)"); return
        ci = boot(sub["x3"])
        print(f"  {lbl:26s} n={len(sub):6d}  x1 {sub.x1.mean()*100:+.2f}%  x3 {sub.x3.mean()*100:+.2f}% "
              f"CI[{ci[0]:+.2f},{ci[1]:+.2f}]  x5 {sub.x5.mean()*100:+.2f}%  win3 {(sub.x3>0).mean()*100:.0f}%")

    print("\n=== sharp pullback in a STRONG stock — does it bounce? (market-rel) ===")
    show(S, "ALL sharp pullbacks")
    show(S[S.plunge == 1], "3-day plunge (<=-8%)")
    show(S[S.rsi_os == 1], "RSI(2) < 10")
    show(S[S.ma_pull == 1], "pullback to rising MA20")
    show(S[(S.plunge == 1) & (S.rsi_os == 1)], "plunge AND RSI(2)<10")
    print("\n  -- best cell (plunge) by year --")
    p = S[S.plunge == 1]
    for y in sorted(p["yr"].unique()):
        s = p[p.yr == y]
        if len(s) > 20:
            print(f"    {y}: x3 {s.x3.mean()*100:+5.2f}%  n={len(s):4d}  win {(s.x3>0).mean()*100:.0f}%")
    print("\nREAD: x3 CI>0 => the sharp dip in an uptrend bounces = the 'low of a continuation' edge is real.")


if __name__ == "__main__":
    main()
