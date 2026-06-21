"""SURVIVORSHIP-CLEAN earnings-gap dataset: Benzinga earnings calendar (delisted INCLUDED, exact
dates + BMO/AMC) x clean 9yr Polygon daily (delisted prices). For each earnings event we find the
REACTION day (BMO -> same session, AMC -> next session), measure the gap, the doc setup (gap>=7.5%
above prior 20d high + liquidity), causal features (gap, surprise, extension, regime, squeeze-ready),
and forward MARKET-RELATIVE continuation. Then the headline test: FULL (delisted-incl) vs SURVIVORS-
only drift -> how much of the earnings edge was survivorship? Run w/ backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
MIN_PRICE, MIN_DVOL, GAP_MIN = 5.0, 5e6, 0.075


def load():
    earn = pd.read_parquet(POLY / "earnings_benzinga.parquet")
    earn["d"] = pd.to_datetime(earn["date"]).dt.strftime("%Y%m%d").astype(int)
    earn["hr"] = earn["time"].fillna("16:00:00").str.slice(0, 2).astype(int)
    tk = set(earn["ticker"])
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    meta = pd.read_parquet(POLY / "meta.parquet")
    active = dict(zip(meta["ticker"], meta["active"]))
    spy = df[df["ticker"] == "SPY"].sort_values("date")
    spy_c = dict(zip(spy["date"].astype(int), spy["close"]))
    spy_ma = dict(zip(spy["date"].astype(int), spy["close"].rolling(50).mean()))
    df = df[df["ticker"].isin(tk)].sort_values(["ticker", "date"])
    D = {}
    for t, g in df.groupby("ticker", sort=False):
        o, h, l, c, v = (g[x].to_numpy() for x in ("open", "high", "low", "close", "volume"))
        dts = g["date"].to_numpy().astype(int)
        pc = np.roll(c, 1)
        tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
        atr = pd.Series(tr).rolling(14).mean().to_numpy()
        ma50 = pd.Series(c).rolling(50).mean().to_numpy()
        hi20 = pd.Series(h).rolling(20).max().shift(1).to_numpy()
        dvol = (pd.Series(c * v).rolling(20).mean().shift(1)).to_numpy()
        D[t] = dict(o=o, h=h, l=l, c=c, v=v, dts=dts, atr=atr, ma50=ma50, hi20=hi20, dvol=dvol,
                    avgv=pd.Series(v).rolling(20).mean().shift(1).to_numpy())
    return earn, D, active, spy_c, spy_ma


def main():
    earn, D, active, spy_c, spy_ma = load()
    rows = []
    for e in earn.itertuples(index=False):
        d = D.get(e.ticker)
        if d is None:
            continue
        dts = d["dts"]
        # reaction day: AMC (hr>=12) -> next session; BMO -> same/next session
        if e.hr >= 12:
            gi = int(np.searchsorted(dts, e.d, side="right"))
        else:
            gi = int(np.searchsorted(dts, e.d, side="left"))
        if gi < 64 or gi >= len(dts) - 41:
            continue
        c, o, h = d["c"], d["o"], d["h"]
        pcl = c[gi - 1]
        if pcl <= 0:
            continue
        gap = o[gi] / pcl - 1
        di = int(dts[gi])
        s0, s20, s40 = spy_c.get(di), spy_c.get(int(dts[gi + 20])), spy_c.get(int(dts[gi + 40]))
        if not (s0 and s20 and s40):
            continue
        prior_high = d["hi20"][gi]
        rows.append({
            "ticker": e.ticker, "date": di, "active": bool(active.get(e.ticker, False)),
            "gap": gap, "gap_close": c[gi] / pcl - 1,
            "above_high": int(o[gi] > prior_high) if not np.isnan(prior_high) else 0,
            "eps_surprise": e.eps_surprise, "importance": e.importance,
            "ret_3m": c[gi - 1] / c[gi - 63] - 1, "ret_6m": c[gi - 1] / c[gi - 126] - 1 if gi >= 126 else np.nan,
            "atr_pct": d["atr"][gi - 1] / pcl if d["atr"][gi - 1] else np.nan,
            "dist_ma50": pcl / d["ma50"][gi - 1] - 1 if d["ma50"][gi - 1] else np.nan,
            "vol_spike": d["v"][gi] / d["avgv"][gi] if d["avgv"][gi] else np.nan,
            "dvol": d["dvol"][gi], "log_price": np.log(pcl),
            "regime_up": int(spy_c.get(di, 0) > (spy_ma.get(di) or 1e18)),
            # forward MARKET-RELATIVE continuation from the reaction-day CLOSE
            "x20": (c[gi + 20] / c[gi] - 1) - (s20 / s0 - 1),
            "x40": (c[gi + 40] / c[gi] - 1) - (s40 / s0 - 1),
        })
    S = pd.DataFrame(rows).dropna(subset=["x20", "x40"])
    S.to_parquet(OUT / "earnings_clean.parquet")
    print(f"earnings events mapped: {len(S):,} | tickers {S['ticker'].nunique():,} | "
          f"{S['date'].min()}..{S['date'].max()} | active {S['active'].mean()*100:.0f}%")

    doc = S[(S["gap"] >= GAP_MIN) & (S["above_high"] == 1) & (np.exp(S["log_price"]) >= MIN_PRICE) & (S["dvol"] >= MIN_DVOL)]
    print(f"\n=== DOC SETUP (gap>={GAP_MIN:.0%} above prior high + liquid): n={len(doc):,} ===")

    def boot(x, n=3000):
        x = x.to_numpy(); idx = np.random.default_rng(0).integers(0, len(x), (n, len(x)))
        return np.percentile(x[idx].mean(1) * 100, [2.5, 97.5])

    for lbl, sub in [("FULL (delisted-incl)", doc), ("SURVIVORS only", doc[doc["active"]]),
                     ("DELISTED only", doc[~doc["active"]])]:
        if len(sub) < 30:
            print(f"  {lbl:22s} n={len(sub)} (too few)"); continue
        ci20 = boot(sub["x20"])
        print(f"  {lbl:22s} n={len(sub):6d}  x20 {sub['x20'].mean()*100:+.2f}% CI[{ci20[0]:+.2f},{ci20[1]:+.2f}]  "
              f"x40 {sub['x40'].mean()*100:+.2f}%  win {(sub['x20']>0).mean()*100:.0f}%")
    surv = doc[doc['active']]['x20'].mean(); full = doc['x20'].mean()
    print(f"\n  SURVIVORSHIP INFLATION (survivors - full): {(surv-full)*100:+.2f}pp "
          f"-> TRUE clean edge = full = {full*100:+.2f}%")
    print("\n  -- by year (full, delisted-incl) --")
    doc = doc.copy(); doc["yr"] = doc["date"] // 10000
    for y in sorted(doc["yr"].unique()):
        s = doc[doc.yr == y]
        print(f"    {y}: x20 {s['x20'].mean()*100:+5.2f}%  n={len(s):4d}  win {(s['x20']>0).mean()*100:.0f}%")


if __name__ == "__main__":
    main()
