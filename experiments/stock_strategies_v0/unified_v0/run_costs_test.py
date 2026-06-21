"""Honest costs test on breakout_v0's DEPLOYABLE trades (ml_selected_results = the ML-filtered pred>0
breakouts, the +0.676). The R already nets 0.15%/side; real small/mid-cap intraday fills are 0.3-0.5%+.
Convert cost% -> cost-R via the per-trade risk (risk=1xATR, so risk/entry=atr_pct => extra cost_R =
2*(f-0.0015)/atr_pct). Sweep friction, split by liquidity tier, find breakeven, rough annualized.
Run with backend\\.venv\\Scripts\\python.exe -u.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
OUT = Path(__file__).resolve().parent / "out"
RCAP, BASE_FRIC = 10.0, 0.0015


def main():
    sel = pd.read_parquet(OUT / "ml_selected_results.parquet")[["tkr", "date", "R"]]
    # recompute atr_pct (risk fraction) + dvol per (tkr,date) from daily
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    df = df[df["ticker"].isin(set(sel["tkr"]))].sort_values(["ticker", "date"])
    info = {}
    for t, g in df.groupby("ticker", sort=False):
        c = g["close"].to_numpy(float); h = g["high"].to_numpy(float); l = g["low"].to_numpy(float)
        v = g["volume"].to_numpy(float); dts = g["date"].to_numpy().astype(int); pc = np.roll(c, 1)
        tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
        atr = pd.Series(tr).rolling(14).mean().shift(1).to_numpy()
        dvol = pd.Series(c * v).rolling(20).mean().shift(1).to_numpy()
        for i, d in enumerate(dts):
            if i and c[i] and not np.isnan(atr[i]):
                info[(t, int(d))] = (atr[i] / c[i], dvol[i])
    sel["atr_pct"] = [info.get((t, d), (np.nan, np.nan))[0] for t, d in zip(sel["tkr"], sel["date"])]
    sel["dvol"] = [info.get((t, d), (np.nan, np.nan))[1] for t, d in zip(sel["tkr"], sel["date"])]
    sel = sel.dropna(subset=["atr_pct", "dvol"])
    sel["R"] = sel["R"].clip(-RCAP, RCAP)
    sel["atr_pct"] = sel["atr_pct"].clip(lower=0.005)
    print(f"deployable (ML-filtered) trades: {len(sel):,} | median atr_pct {sel['atr_pct'].median()*100:.1f}% "
          f"| median $dvol {sel['dvol'].median()/1e6:.0f}M\n")

    def net(f):
        return sel["R"] - 2 * (f - BASE_FRIC) / sel["atr_pct"]

    print("=== net meanR by cost (per side) + rough annual @0.25% risk, ~360 trades/yr ===")
    for f in (0.0015, 0.003, 0.005, 0.0075, 0.01):
        m = net(f).mean()
        ann = ((1 + 0.0025 * np.clip(net(f), -RCAP, RCAP)).pow(1)).mean()  # per-trade growth factor
        ann_pct = ((1 + 0.0025 * m) ** 360 - 1) * 100
        print(f"  {f*100:.2f}%/side: meanR {m:+.3f}   ~{ann_pct:+.0f}%/yr")
    # breakeven
    lo, hi = 0.0015, 0.05
    for _ in range(40):
        mid = (lo + hi) / 2
        if net(mid).mean() > 0:
            lo = mid
        else:
            hi = mid
    print(f"\n  breakeven friction ~ {lo*100:.2f}%/side")

    print("\n=== by liquidity tier (net @0.30%/side -- realistic for the tier) ===")
    sel["tier"] = pd.qcut(sel["dvol"], 4, labels=["thin", "q2", "q3", "liquid"])
    for tlab in ["thin", "q2", "q3", "liquid"]:
        s = sel[sel["tier"] == tlab]
        n3 = (s["R"] - 2 * (0.003 - BASE_FRIC) / s["atr_pct"]).mean()
        print(f"  {tlab:7s} median $dvol {s['dvol'].median()/1e6:5.0f}M  net meanR {n3:+.3f}  (n={len(s):,})")

    print("\n=== net @0.30%/side by year ===")
    sel["yr"] = sel["date"] // 10000
    for y in sorted(sel["yr"].unique()):
        s = sel[sel["yr"] == y]
        n3 = (s["R"] - 2 * (0.003 - BASE_FRIC) / s["atr_pct"]).mean()
        print(f"  {y}: net meanR {n3:+.3f}  n={len(s):,}")
    print("\nREAD: net>0 at ~0.3-0.5%/side AND in the liquid tier AND most years => a real deployable edge.")
    print("dies by ~0.3%/side or only thin tier => costs eat it (the +0.676 was a low-cost-assumption number).")


if __name__ == "__main__":
    main()
