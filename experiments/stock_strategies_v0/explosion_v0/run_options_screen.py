"""$0 OPTIONS SCREEN (scout before any ThetaData pull). The explosion model finds big moves (AUC
0.88) but stock+stop wasn't tradeable ex-2020 (stop-out chop). Options remove the stop-out -> does
buying CONVEXITY on the top-explosion names pay? Price a THEORETICAL ATM/OTM call off the stock's OWN
vol (atr_pct -> annualized), value held-to-~expiry on the realized 60d price, modest spread. This is
OPTIMISTIC (real market IV > realized vol, so real calls cost MORE): if cheap theoretical calls don't
pay (esp EX-2020), real options are dead -> skip the pull. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

POLY = Path(r"D:\data\processed\stocks\polygon")
HERE = Path(__file__).resolve().parent
oos = pd.read_parquet(HERE / "out" / "explosion_oos.parquet")
oos["spot"] = np.exp(oos["log_price"])
T_DAYS, R, SPREAD = 60, 0.04, 0.05         # ~3mo expiry, 4% rate, pay 5% over mid (optimistic spread)


def bs_call(S, K, T, vol, r=R):
    vol = np.clip(vol, 0.05, 4.0)
    d1 = (np.log(S / K) + (r + vol * vol / 2) * T) / (vol * np.sqrt(T))
    d2 = d1 - vol * np.sqrt(T)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


# realized close at +60 trading days (held-to-expiry exit) from daily
print("loading daily for forward exit prices...")
df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
keep = set(oos["ticker"])
df = df[df["ticker"].isin(keep)].sort_values(["ticker", "date"])
fwd = {}
for t, g in df.groupby("ticker", sort=False):
    c = g["close"].to_numpy(); dts = g["date"].to_numpy().astype(int)
    idx = {int(x): i for i, x in enumerate(dts)}
    fwd[t] = (c, idx)


def exit_close(t, d):
    c, idx = fwd.get(t, (None, None))
    if idx is None:
        return np.nan
    i = idx.get(int(d))
    if i is None or i + T_DAYS >= len(c):
        return np.nan
    return c[i + T_DAYS]


oos["s_exit"] = [exit_close(t, d) for t, d in zip(oos["ticker"], oos["date"])]
oos = oos.dropna(subset=["s_exit"]).copy()
oos["vol_ann"] = (oos["atr_pct"] * np.sqrt(252)).clip(0.2, 4.0)   # ATR-based IV proxy
T = T_DAYS / 252
oos["yr"] = oos["date"] // 10000


def call_pnl(moneyness):
    K = oos["spot"] * moneyness
    prem = bs_call(oos["spot"].to_numpy(), K.to_numpy(), T, oos["vol_ann"].to_numpy()) * (1 + SPREAD)
    payoff = np.clip(oos["s_exit"] - K, 0, None)
    return (payoff - prem) / prem                     # return on premium


for mny, lbl in [(1.00, "ATM"), (1.10, "10% OTM"), (1.25, "25% OTM")]:
    oos[f"ret_{lbl}"] = call_pnl(mny)
    top = oos[oos["dec"] == 9]
    allr, topr = oos[f"ret_{lbl}"].mean(), top[f"ret_{lbl}"].mean()
    print(f"\n=== buy {lbl} call (theoretical, cheap) ===")
    print(f"  ALL thrusts: mean {allr*100:+.0f}% on premium | TOP-decile: mean {topr*100:+.0f}%  win {(top[f'ret_{lbl}']>0).mean()*100:.0f}%")
    by = top.groupby("yr")[f"ret_{lbl}"].mean() * 100
    print("  top-decile by year: " + " ".join(f"{y}:{v:+.0f}%" for y, v in by.items()))
    ex20 = top[top["yr"] != 2020][f"ret_{lbl}"].mean() * 100
    print(f"  TOP-decile EX-2020: {ex20:+.0f}% on premium")

print("\nREAD: top-decile EX-2020 call return > 0 (on CHEAP theoretical calls) => worth pulling real options")
print("to check vs actual IV. EX-2020 <= 0 even on cheap calls => real (pricier) options are dead too.")
