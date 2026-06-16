"""One-shot census of the ThetaData greeks cache: classify every cached greeks file by
(year, underlying-price band) so we KNOW, per index, exactly what history exists.

Resolves the RUT/DJX coverage conflict (map agent said RUT 2017+, builders say 2024+):
the only way RUT 2017-2020 exists is greeks files with year<2024 AND median in the clean
Russell band [1000,1800] (SPX never traded that low, so that band is unambiguous RUT).
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

GREEKS = Path(r"D:\data\raw\thetadata\bulk_hist_option_eod_greeks")

# Unambiguous-ish bands by the indices we care about (2024-26 ranges; overlaps flagged).
def band(med: float) -> str:
    if med < 250:            return "sub250"          # SPY/QQQ etc proxies
    if med < 600:            return "DJX[250,600)"     # Dow/100
    if med < 1000:           return "gap[600,1000)"
    if med < 1800:           return "RUT_clean[1000,1800)"   # SPX never this low -> pure Russell
    if med < 3000:           return "RUT|SPX17[1800,3000)"   # RUT-2024+ OR SPX-2017 (year breaks tie)
    if med < 8500:           return "SPX[3000,8500)"
    return "NDX[8500+)"

rows = []
files = sorted(GREEKS.glob("*.parquet"))
print(f"scanning {len(files)} greeks files...", flush=True)
for i, fp in enumerate(files):
    try:
        d = pd.read_parquet(fp, columns=["date", "underlying_price"])
    except Exception:
        continue
    if d.empty:
        continue
    med = float(d["underlying_price"].median())
    yr = int(d["date"].iloc[0]) // 10000
    rows.append((yr, band(med), len(d)))
    if (i + 1) % 500 == 0:
        print(f"  ..{i+1}/{len(files)}", flush=True)

df = pd.DataFrame(rows, columns=["year", "band", "n"])
print("\n=== FILE COUNTS by year x band ===")
ct = df.pivot_table(index="year", columns="band", values="n", aggfunc="count", fill_value=0)
print(ct.to_string())

print("\n=== CRUX: pre-2024 files in the clean Russell band [1000,1800) ===")
rc = df[(df.band == "RUT_clean[1000,1800)")]
print(rc.groupby("year").size().to_dict() or "NONE")
print("If years <2024 appear here -> genuine pre-2024 RUT exists and builders under-cover it.")

print("\n=== DJX band [250,600) by year ===")
print(df[df.band == "DJX[250,600)"].groupby("year").size().to_dict() or "NONE")
