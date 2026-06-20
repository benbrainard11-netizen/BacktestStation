"""Sector-rotation gate test: take a breakout only if the stock's SECTOR is leading (its SPDR
sector ETF is outperforming SPY over the trailing 3 months, measured causally as of the prior day).

Map: ticker -> SIC (Polygon detail, ticker_sic.parquet) -> 11 GICS-ish sectors -> SPDR ETF.
Sector RS: ETF 63-day return vs SPY 63-day return. Gate: keep trade iff its sector ETF was
outperforming SPY at the setup date (prior-day signal). Applied to the full-window volume-breakout
per-trade results; reports by-year + retention + uplift, plus combos with the market gates.
Run with backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\Users\benbr\BacktestStation")
from data_io import load_polygon_daily  # noqa: E402

POLY = Path(r"D:\data\processed\stocks\polygon")
RES = Path(
    r"C:\Users\benbr\BacktestStation\experiments\stock_strategies_v0\unified_v0\out\intraday_entry_results_full.parquet"
)
ETF = {
    "Technology": "XLK",
    "Health Care": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}


def sic_sector(sic) -> str:
    if sic is None or (isinstance(sic, float) and np.isnan(sic)):
        return "Unknown"
    s = int(sic)
    rng = [
        (100, 1299, "Materials"),
        (1300, 1399, "Energy"),
        (1400, 1499, "Materials"),
        (1500, 1799, "Industrials"),
        (2000, 2199, "Consumer Staples"),
        (2200, 2399, "Consumer Discretionary"),
        (2400, 2499, "Materials"),
        (2500, 2599, "Consumer Discretionary"),
        (2600, 2699, "Materials"),
        (2700, 2799, "Communication Services"),
        (2800, 2829, "Materials"),
        (2830, 2836, "Health Care"),
        (2840, 2899, "Materials"),
        (2900, 2999, "Energy"),
        (3000, 3399, "Materials"),
        (3400, 3499, "Industrials"),
        (3500, 3569, "Industrials"),
        (3570, 3579, "Technology"),
        (3580, 3629, "Industrials"),
        (3630, 3669, "Consumer Discretionary"),
        (3670, 3699, "Technology"),
        (3700, 3713, "Consumer Discretionary"),
        (3714, 3799, "Industrials"),
        (3800, 3829, "Technology"),
        (3830, 3859, "Health Care"),
        (3860, 3899, "Technology"),
        (3900, 3999, "Consumer Discretionary"),
        (4000, 4799, "Industrials"),
        (4800, 4899, "Communication Services"),
        (4900, 4999, "Utilities"),
        (5000, 5199, "Industrials"),
        (5200, 5399, "Consumer Discretionary"),
        (5400, 5499, "Consumer Staples"),
        (5500, 5999, "Consumer Discretionary"),
        (6000, 6499, "Financials"),
        (6500, 6599, "Real Estate"),
        (6700, 6799, "Financials"),
        (7000, 7299, "Consumer Discretionary"),
        (7300, 7369, "Industrials"),
        (7370, 7379, "Technology"),
        (7380, 7399, "Industrials"),
        (7400, 7799, "Consumer Discretionary"),
        (7800, 7999, "Communication Services"),
        (8000, 8099, "Health Care"),
    ]
    for lo, hi, sec in rng:
        if lo <= s <= hi:
            return sec
    return "Industrials"


def ret63_map(tkr):
    d = load_polygon_daily(tkr).sort_values("date")
    d["r63"] = d["close"] / d["close"].shift(63) - 1
    s = d.set_index("date")["r63"].shift(1)  # causal: as of prior day
    return s


def main():
    R = pd.read_parquet(RES)
    R["yr"] = R["date"] // 10000
    sic = pd.read_parquet(POLY / "ticker_sic.parquet")
    sic["sector"] = sic["sic"].map(sic_sector)
    t2sec = dict(zip(sic["ticker"], sic["sector"]))
    cov = R["tkr"].map(t2sec)
    print(
        f"sector coverage: {cov.notna().mean()*100:.1f}% of trades mapped; "
        f"{(cov=='Unknown').mean()*100:.1f}% Unknown"
    )
    print("sector mix:", cov.value_counts().head(12).to_dict())

    spy = ret63_map("SPY")
    etf_r = {sec: ret63_map(e) for sec, e in ETF.items()}
    # leading[sector][date] = etf_3m > spy_3m
    R["sector"] = R["tkr"].map(t2sec)
    R["spy63"] = R["date"].map(spy)

    def etf63(row):
        m = etf_r.get(row["sector"])
        return m.get(row["date"]) if m is not None else np.nan

    R["etf63"] = R.apply(etf63, axis=1)
    R["leading"] = R["etf63"] > R["spy63"]

    bm = R["R"].mean()
    ally = sorted(R.yr.unique())
    print(f"\nBASELINE n={len(R):,} meanR {bm:+.3f}")

    def show(mask, label):
        s = R[mask]
        by = " ".join(f"{s[s.yr==y]['R'].mean():+5.2f}" if len(s[s.yr == y]) else "  -  " for y in ally)
        print(f"{label:20s} {100*len(s)/len(R):4.0f}% {s['R'].mean():+5.2f}  {by}")

    print(f"{'gate':20s} keep%  meanR  " + " ".join(f"{y%100:>5}" for y in ally))
    show(R["leading"] == True, "sector-leading")  # noqa: E712
    show(R["leading"] != True, "sector-LAGGING")  # noqa: E712

    R.to_parquet(POLY / "_xregime_with_sector.parquet")
    return R


if __name__ == "__main__":
    main()
