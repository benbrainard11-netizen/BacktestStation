"""Bulk-pull the Benzinga earnings calendar (via Polygon Developer) for the WHOLE universe,
2016-01 -> 2026-06, DELISTED INCLUDED -> closes the survivorship gap that capped the earnings edge.
Exact announcement dates + BMO/AMC time + EPS surprise. By-month windows with pagination.
Reads env POLYGON_API_KEY. Run with backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import requests

KEY = os.environ["POLYGON_API_KEY"]
HOST = "https://api.polygon.io"
OUT = Path(r"D:\data\processed\stocks\polygon")
OUT.mkdir(parents=True, exist_ok=True)
FIELDS = [
    "ticker",
    "date",
    "time",
    "eps",
    "eps_est",
    "eps_surprise",
    "revenue",
    "revenue_est",
    "revenue_surprise",
    "fiscal_period",
    "fiscal_year",
    "importance",
]
sess = requests.Session()


def pull_window(gte, lte):
    rows, url = [], f"{HOST}/benzinga/v1/earnings"
    params = {"date.gte": gte, "date.lte": lte, "limit": 1000, "order": "asc", "sort": "date", "apiKey": KEY}
    while True:
        for _ in range(4):
            try:
                j = sess.get(url, params=params, timeout=40).json()
                break
            except Exception:
                time.sleep(1.5)
        else:
            break
        for r in j.get("results", []) or []:
            rows.append({k: r.get(k) for k in FIELDS})
        nxt = j.get("next_url")
        if not nxt:
            break
        url, params = nxt, {"apiKey": KEY}
    return rows


def main():
    all_rows = []
    for m in pd.date_range("2016-01-01", "2026-06-01", freq="MS"):
        gte = m.strftime("%Y-%m-%d")
        lte = (m + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d")
        r = pull_window(gte, lte)
        all_rows += r
        if m.month == 1 or len(r) > 0 and m.month in (2, 5, 8, 11):
            print(f"  {gte[:7]}: {len(r):,} events (cum {len(all_rows):,})", flush=True)
    df = pd.DataFrame(all_rows).drop_duplicates(["ticker", "date", "fiscal_period", "fiscal_year"])
    df.to_parquet(OUT / "earnings_benzinga.parquet")
    print(
        f"\nDONE: {len(df):,} earnings events | {df['ticker'].nunique():,} tickers | "
        f"{df['date'].min()}..{df['date'].max()}"
    )
    print(
        f"  has eps_surprise: {df['eps_surprise'].notna().mean()*100:.0f}%  | "
        f"BMO/AMC time present: {df['time'].notna().mean()*100:.0f}%"
    )
    print(f"  time values (top): {df['time'].value_counts().head(4).to_dict()}")


if __name__ == "__main__":
    main()
