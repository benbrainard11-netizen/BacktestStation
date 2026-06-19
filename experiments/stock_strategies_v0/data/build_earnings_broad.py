"""Extend the earnings calendar to the liquid universe (data/liquid_universe.txt), MERGING
with the existing calendar (only pulls names not already present). yfinance, 2010+, limit=100.
Run: backend\\.venv\\Scripts\\python.exe experiments\\stock_strategies_v0\\data\\build_earnings_broad.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import yfinance as yf

import common as C  # noqa: E402

SINCE = pd.Timestamp("2010-01-01", tz="America/New_York")
uni = (Path(__file__).resolve().parent / "liquid_universe.txt").read_text().split()
existing = pd.read_parquet(C.EARNINGS_CAL)
have = set(existing["ticker"].unique())
need = [t for t in uni if t not in have]
print(f"liquid universe {len(uni)} | have {len(have)} | pulling {len(need)} new", flush=True)


def when(ts: pd.Timestamp) -> str:
    ms = ts.hour * 3600 + ts.minute * 60
    return "AMC" if ms >= 16 * 3600 else ("BMO" if ms < int(9.5 * 3600) else "INTRADAY")


rows, fails = [], []
for i, t in enumerate(need):
    try:
        ed = yf.Ticker(t).get_earnings_dates(limit=100)
    except Exception as ex:
        fails.append((t, type(ex).__name__))
        continue
    if ed is None or not len(ed):
        fails.append((t, "empty"))
        continue
    ed = ed.reset_index()
    ed.columns = [str(c) for c in ed.columns]
    tscol = ed.columns[0]
    for _, r in ed.iterrows():
        ts = pd.Timestamp(r[tscol])
        ts = ts.tz_localize("America/New_York") if ts.tzinfo is None else ts.tz_convert("America/New_York")
        if ts < SINCE:
            continue
        rows.append(
            {
                "ticker": t,
                "earnings_dt_et": ts,
                "date": ts.date(),
                "when": when(ts),
                "eps_estimate": r.get("EPS Estimate"),
                "reported_eps": r.get("Reported EPS"),
                "surprise_pct": r.get("Surprise(%)"),
            }
        )
    if (i + 1) % 100 == 0:
        print(f"  ...{i+1}/{len(need)}  rows={len(rows)}", flush=True)

new = pd.DataFrame(rows)
out = pd.concat([existing, new], ignore_index=True).drop_duplicates(["ticker", "earnings_dt_et"])
out = out.sort_values(["ticker", "earnings_dt_et"]).reset_index(drop=True)
out.to_parquet(C.EARNINGS_CAL)
print(f"\nMERGED -> {C.EARNINGS_CAL}  total rows={len(out)}  tickers={out['ticker'].nunique()}")
print(f"new tickers pulled: {new['ticker'].nunique() if len(new) else 0} | failed/empty: {len(fails)}")
