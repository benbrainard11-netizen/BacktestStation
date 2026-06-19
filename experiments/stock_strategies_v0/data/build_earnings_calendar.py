"""Build an earnings calendar for the local stock universe via yfinance (free).
Writes D:\\data\\processed\\stocks\\earnings_calendar.parquet with one row per
(ticker, earnings_datetime): the ET timestamp, the date, AMC/BMO timing, and the
EPS estimate/reported/surprise when yfinance has them.

AMC (after market close, ts >= 16:00 ET) → the GAP happens the NEXT session.
BMO (before open, ts < 09:30 ET)        → the gap happens the SAME session.

Run: backend\\.venv\\Scripts\\python.exe experiments\\stock_strategies_v0\\data\\build_earnings_calendar.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

EOD_DIR = Path(r"D:\data\processed\stocks\eod")
OUT = Path(r"D:\data\processed\stocks\earnings_calendar.parquet")
SINCE = pd.Timestamp("2010-01-01", tz="America/New_York")  # match the daily-bar history floor

tickers = sorted(f.stem for f in EOD_DIR.glob("*.parquet"))
print(f"{len(tickers)} tickers")


def when(ts: pd.Timestamp) -> str:
    ms = ts.hour * 3600 + ts.minute * 60
    if ms >= 16 * 3600:
        return "AMC"
    if ms < int(9.5 * 3600):
        return "BMO"
    return "INTRADAY"


rows, fails = [], []
for i, t in enumerate(tickers):
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
    tscol = ed.columns[0]  # "Earnings Date"
    for _, r in ed.iterrows():
        ts = pd.Timestamp(r[tscol])
        if ts.tzinfo is None:
            ts = ts.tz_localize("America/New_York")
        else:
            ts = ts.tz_convert("America/New_York")
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
    if (i + 1) % 25 == 0:
        print(f"  ...{i+1}/{len(tickers)}", flush=True)

df = pd.DataFrame(rows).sort_values(["ticker", "earnings_dt_et"]).reset_index(drop=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(OUT)

print(f"\nWROTE {OUT}  rows={len(df)}  tickers_with_data={df['ticker'].nunique()}")
print(f"failed/empty: {len(fails)}", fails[:20])
if len(df):
    print("date span:", df["date"].min(), "->", df["date"].max())
    print("timing mix:\n", df["when"].value_counts().to_string())
    print("avg earnings/ticker:", round(len(df) / df["ticker"].nunique(), 1))
