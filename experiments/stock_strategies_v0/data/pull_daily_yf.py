"""Pull split+dividend-adjusted daily bars from yfinance into the project's daily format.
Reproduces / extends the broad `stocks\\daily\\` set (same columns + YYYYMMDD int date).
Use for ETFs, small-cap extensions, or backfilling the universe — all from one free source
so adjustments stay consistent across the daily layer.

  date(int YYYYMMDD), open, high, low, close, volume   (auto_adjust=True)

Run: backend\\.venv\\Scripts\\python.exe experiments\\stock_strategies_v0\\data\\pull_daily_yf.py SPY,QQQ,IWM,DIA,XLB,XLC,XLE,XLF,XLI,XLK,XLP,XLRE,XLU,XLV,XLY,SMH  D:\\data\\processed\\stocks\\etf  2010-01-01
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

tickers = sys.argv[1].split(",") if len(sys.argv) > 1 else ["SPY", "QQQ"]
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(r"D:\data\processed\stocks\etf")
start = sys.argv[3] if len(sys.argv) > 3 else "2010-01-01"
out.mkdir(parents=True, exist_ok=True)

ok, fail = [], []
for t in tickers:
    try:
        df = yf.download(t, start=start, auto_adjust=True, progress=False, threads=False)
    except Exception as ex:
        fail.append((t, type(ex).__name__))
        continue
    if df is None or not len(df):
        fail.append((t, "empty"))
        continue
    if isinstance(df.columns, pd.MultiIndex):  # yfinance sometimes returns MultiIndex
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    # the (former) index holds the dates; find it by dtype, don't assume the name
    datecol = next((c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])), df.columns[0])
    df["date"] = pd.to_datetime(df[datecol]).dt.strftime("%Y%m%d").astype(int)
    df = df.rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )
    df = df[["date", "open", "high", "low", "close", "volume"]].dropna()
    df.to_parquet(out / f"{t}.parquet")
    ok.append((t, len(df), int(df["date"].iloc[0]), int(df["date"].iloc[-1])))

print(f"wrote {len(ok)} -> {out}")
for t, n, a, b in ok:
    print(f"  {t:6s} rows={n:5d} {a}..{b}")
if fail:
    print("FAILED:", fail)
