"""Coverage report for the equities-line data layers. Prints an inventory:
names, date spans, overlaps, earnings coverage. Run after any pull to see the state.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


import common as C  # noqa: E402
import loaders as L  # noqa: E402


def span(layer: str, t: str) -> tuple:
    d = L.load_daily(t, layer)
    return d["dt"].min().date(), d["dt"].max().date(), len(d)


daily = L.list_universe("daily")
etf = L.list_universe("etf")
eod = L.list_universe("eod")
m1 = sorted(p.stem for p in C.STOCKS_M1.glob("*.parquet"))

print("=== DAILY (yfinance, detection layer) ===")
print(f"  names: {len(daily)}")
if daily:
    lo, hi, n = span("daily", daily[0])
    print(f"  sample {daily[0]}: {lo} -> {hi} ({n} rows)")

print("\n=== ETF (regime + sector) ===")
print(f"  {len(etf)} files: {', '.join(etf)}")

print("\n=== M1 (ThetaData, intraday entry) ===")
print(f"  names: {len(m1)} | eod(theta): {len(eod)}")
print(f"  daily and m1 (detect+execute ready now): {len(set(daily) & set(m1))}")
print(f"  in daily but NOT m1 (need on-demand 1m pull): {len(set(daily) - set(m1))}")

print("\n=== EARNINGS CALENDAR ===")
e = L.load_earnings()
cov = sorted(e["ticker"].unique())
print(
    f"  events: {len(e)} | tickers: {len(cov)} | span: {e['earnings_dt_et'].min().date()} -> {e['earnings_dt_et'].max().date()}"
)
print(f"  daily names WITHOUT earnings (extend calendar): {len(set(daily) - set(cov))}")
print("  timing:", e["when"].value_counts().to_dict())

print("\n=== WINDOWS ===")
print(f"  daily history from {C.DAILY_HISTORY_START} (models) | tradeable from {C.INTRADAY_START}")
print(f"  dev <= {C.DEV_END} | holdout >= {C.HOLDOUT_START} | data end ~ {C.DATA_END}")
