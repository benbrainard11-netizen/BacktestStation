"""Modeled options-expression test for the breakout. Instead of buying shares (1-ATR stop +
chandelier), express each breakout as a long CALL and value it off the realized forward path via
Black-Scholes. A call has NO stop -- you hold to a fixed horizon -- so this uses the unstopped
forward return, not the stock strategy's stop-based exit.

No options data needed: entry = setup-day close; forward price = the daily close h trading-days out;
IV = a realized-vol proxy (atr_pct * sqrt(252) * VRP); a round-trip spread haircut is applied. Tested
across several structures (moneyness x DTE x hold) and 2 VRP (IV) levels. Restricted to the LIQUID
subset (price>=$10, $20M+ dvol) -- the only names with tradeable options. Compared to the share
expression's per-trade expectancy at a matched risk budget. Approximate (IV constant = no crush/
expansion; spread/liquidity assumed) -- a concept test, not a fill-accurate backtest.
Run with backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

OUT = Path(__file__).resolve().parent / "out"
POLY = Path(r"D:\data\processed\stocks\polygon")
SPREAD = 0.06  # round-trip option spread haircut (fraction of premium)
RISK = 0.005  # per-trade account budget (0.5%): stock risk OR option premium allocation
STRUCTS = [  # name, moneyness(K/S), DTE(trading days), hold(trading days)
    ("ITM-10% 45d/h20", 0.90, 45, 20),
    ("ATM 30d/h20", 1.00, 30, 20),
    ("ATM 45d/h30", 1.00, 45, 30),
    ("ATM 14d/h10", 1.00, 14, 10),
    ("OTM+5% 30d/h20", 1.05, 30, 20),
    ("OTM+10% 45d/h30", 1.10, 45, 30),
]


def bs_call(S, K, T, vol):
    S, K, T, vol = np.broadcast_arrays(*(np.asarray(x, float) for x in (S, K, T, vol)))
    out = np.maximum(S - K, 0.0).astype(float)
    m = (T > 0) & (vol > 0)
    sq = vol[m] * np.sqrt(T[m])
    d1 = (np.log(S[m] / K[m]) + 0.5 * vol[m] ** 2 * T[m]) / sq
    out[m] = S[m] * norm.cdf(d1) - K[m] * norm.cdf(d1 - sq)
    return out


def main():
    S = pd.read_parquet(OUT / "setups.parquet")
    S = S[S["is_breakout"] == 1].copy()
    R = pd.read_parquet(OUT / "intraday_entry_results_full.parquet")[["tkr", "date", "R"]]

    # forward raw returns from daily (entry = setup-day close; close h trading-days out)
    d = POLY
    daily = pd.concat(
        [pd.read_parquet(f, columns=["ticker", "date", "close"]) for f in sorted(d.glob("daily_*.parquet"))],
        ignore_index=True,
    )
    daily = daily.sort_values(["ticker", "date"])
    for h in (10, 20, 30, 40):
        daily[f"fwd{h}"] = daily.groupby("ticker")["close"].shift(-h) / daily["close"] - 1.0
    S = S.merge(
        daily[["ticker", "date", "close", "fwd10", "fwd20", "fwd30", "fwd40"]],
        on=["ticker", "date"],
        how="left",
    )

    # liquid / optionable subset
    liq = S[(S["close"] >= 10) & (S["log_dvol"] >= np.log(20e6))].copy()
    liq = liq.dropna(subset=["fwd20", "atr_pct"])
    print(f"liquid optionable breakouts: {len(liq):,} of {len(S):,}\n")

    # stock expression on the SAME liquid subset
    st = liq.merge(R, left_on=["ticker", "date"], right_on=["tkr", "date"], how="inner")
    stockR = st["R"].clip(upper=10).mean()
    print(
        f"STOCK expression (1-ATR stop+chandelier): meanR {stockR:+.3f} -> "
        f"{stockR*RISK*100:+.3f}%/trade @ {RISK*100:.1f}% risk  (n={len(st):,})\n"
    )

    entry = liq["close"].to_numpy(float)
    annvol = (liq["atr_pct"].to_numpy(float) * np.sqrt(252)).clip(0.2, 2.5)
    fwd = {h: liq[f"fwd{h}"].to_numpy(float) for h in (10, 20, 30, 40)}

    for VRP in (1.0, 1.25):
        iv = annvol * VRP
        print(f"=== OPTION expressions, IV = realized x {VRP} (median IV {np.median(iv)*100:.0f}%) ===")
        print(
            f"  {'structure':18s} {'meanRet':>8} {'medRet':>8} {'win%':>6} {'p95':>7}  {'%/trade@0.5%':>12}"
        )
        for name, mny, dte, hold in STRUCTS:
            K = entry * mny
            T0, T1 = dte / 252.0, max(dte - hold, 0) / 252.0
            v0 = bs_call(entry, K, T0, iv)
            Sx = entry * (1.0 + fwd[hold])
            v1 = bs_call(Sx, K, np.full_like(entry, T1), iv)
            ok = v0 > 1e-6
            ret = np.full_like(entry, np.nan)
            ret[ok] = (v1[ok] * (1 - SPREAD) - v0[ok]) / v0[ok]  # spread on exit; entry at mid
            ret = ret[~np.isnan(ret)]
            ret = np.clip(ret, -1.0, None)  # can't lose more than the premium
            per = ret.mean() * RISK
            print(
                f"  {name:18s} {ret.mean()*100:+7.1f}% {np.median(ret)*100:+7.1f}% "
                f"{(ret>0).mean()*100:5.1f}% {np.percentile(ret,95)*100:+6.0f}%  {per*100:+11.3f}%"
            )
        print()
    print(
        "READ: compare each option %/trade@0.5% to the STOCK %/trade above. Higher = options win "
        "at matched risk (premium alloc = stock risk); but watch win% (premium burn) + the IV assumption."
    )


if __name__ == "__main__":
    main()
