"""Bulk-pull the survivorship-clean US stock universe from Polygon/Massive grouped-daily
(every ticker per day, delisted INCLUDED), 2021-06 -> 2026-06, split-adjusted. Plus the
reference-tickers endpoint (type=CS) to tag common-stock vs ETF/warrant/SPAC -> the junk
filter that the ThetaData approach lacked. Writes yearly parquets (resumable) +
meta.parquet. Needs env POLYGON_API_KEY. Run with backend\\.venv\\Scripts\\python.exe.
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
START, END = pd.Timestamp("2021-06-20"), pd.Timestamp("2026-06-19")
sess = requests.Session()


def grouped(date_str: str):
    for _ in range(4):
        try:
            r = sess.get(
                f"{HOST}/v2/aggs/grouped/locale/us/market/stocks/{date_str}",
                params={"adjusted": "true", "apiKey": KEY},
                timeout=30,
            )
            if r.status_code == 200:
                return r.json().get("results") or []
            if r.status_code == 429:
                time.sleep(2)
                continue
            return []
        except Exception:
            time.sleep(1)
    return []


for yr in range(2021, 2027):
    f = OUT / f"daily_{yr}.parquet"
    if f.exists():
        print(f"{yr}: exists, skip", flush=True)
        continue
    s = max(pd.Timestamp(f"{yr}-01-01"), START)
    e = min(pd.Timestamp(f"{yr}-12-31"), END)
    if s > e:
        continue
    rows = []
    for d in pd.bdate_range(s, e):
        di = int(d.strftime("%Y%m%d"))
        for it in grouped(d.strftime("%Y-%m-%d")):
            rows.append((it["T"], di, it.get("o"), it.get("h"), it.get("l"), it.get("c"), it.get("v")))
    if rows:
        pd.DataFrame(rows, columns=["ticker", "date", "open", "high", "low", "close", "volume"]).to_parquet(f)
        print(
            f"{yr}: {len(rows):,} rows, {pd.Series([r[0] for r in rows]).nunique()} tickers -> {f.name}",
            flush=True,
        )

# reference: common-stock tickers (active + delisted) -> security-type filter
meta = []
for active in ("true", "false"):
    url = f"{HOST}/v3/reference/tickers"
    params = {"market": "stocks", "type": "CS", "active": active, "limit": 1000, "apiKey": KEY}
    while True:
        j = sess.get(url, params=params, timeout=30).json()
        for t in j.get("results", []):
            meta.append((t["ticker"], t.get("type"), active == "true"))
        nxt = j.get("next_url")
        if not nxt:
            break
        url, params = nxt, {"apiKey": KEY}
pd.DataFrame(meta, columns=["ticker", "type", "active"]).drop_duplicates("ticker").to_parquet(
    OUT / "meta.parquet"
)
print(f"meta: {len(meta)} common-stock tickers (active+delisted)", flush=True)
print("DONE", flush=True)
