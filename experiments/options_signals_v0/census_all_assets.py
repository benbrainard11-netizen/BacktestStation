"""Full local-cache census for ALL 4 index options: greeks + raw EOD prices + open interest,
classified by asset x year. Tells us, per asset, the MAX walls history buildable from what is
already on disk (no vendor pull). Greeks -> walls for SPX/RUT/DJX; raw prices -> self-computed
walls for NDX (and SPX fallback). Vendor ceiling beyond this is a separate probe.

Asset banding by a file's central level (greeks: median underlying_price; eod/OI: median strike;
both cluster near spot). Bands: DJX<600, RUT[1000,3000), SPX[3000,8500), NDX>=8500. The RUT/SPX
overlap [1800,3000) is split by YEAR (SPX pre-2021 traded there; RUT only 2024+).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW = Path(r"D:\data\raw\thetadata")
CACHES = {
    "greeks": (RAW / "bulk_hist_option_eod_greeks", "underlying_price"),
    "rawpx":  (RAW / "bulk_hist_option_eod",        "strike"),
    "oi":     (RAW / "bulk_hist_option_open_interest", "strike"),
}


def asset_of(level: float, year: int) -> str:
    if level < 600:    return "DJX"
    if level < 1800:   return "RUT"           # clean Russell (SPX never this low)
    if level < 3000:   return "RUT" if year >= 2024 else "SPX"   # overlap: year breaks tie
    if level < 8500:   return "SPX"
    return "NDX"


def census(cache: Path, level_col: str) -> pd.DataFrame:
    files = sorted(cache.glob("*.parquet"))
    rows = []
    for fp in files:
        try:
            cols = ["date", level_col] if level_col != "strike" else ["date", "strike"]
            d = pd.read_parquet(fp, columns=cols)
        except Exception:
            try:
                d = pd.read_parquet(fp, columns=["date", "strike"]); level_col_eff = "strike"
            except Exception:
                continue
        else:
            level_col_eff = level_col
        if d.empty:
            continue
        lvl = float(d[level_col_eff].median())
        yr = int(d["date"].iloc[0]) // 10000
        rows.append((asset_of(lvl, yr), yr, len(d)))
    return pd.DataFrame(rows, columns=["asset", "year", "n"])


summary = {}
for nm, (cache, lvl) in CACHES.items():
    if not cache.exists():
        print(f"{nm}: cache missing {cache}"); continue
    df = census(cache, lvl)
    print(f"\n=== {nm}  ({cache.name}) — files by asset x year ===")
    ct = df.pivot_table(index="asset", columns="year", values="n", aggfunc="count", fill_value=0)
    print(ct.to_string())
    summary[nm] = df.groupby("asset")["year"].agg(lambda s: f"{s.min()}..{s.max()} ({s.nunique()}y)")

print("\n========== PER-ASSET: years present in each cache ==========")
s = pd.DataFrame(summary).fillna("-")
print(s.to_string())
