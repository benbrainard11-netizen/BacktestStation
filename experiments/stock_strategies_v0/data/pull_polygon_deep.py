"""Deep-history extension of the Polygon stock pull: grouped-daily 2016->2021 (split-adjusted,
delisted included) to add the 2016-2021 history (incl the 2018 Q4 + 2020 COVID/momentum crashes)
that the 5yr Starter plan couldn't reach. Requires the Developer (10yr) upgrade to be ACTIVE -
it probes authorization first and aborts cleanly if not. Re-pulls 2016-2021 (overwrites the
partial 2021 we have), keeps 2022-2026, refreshes meta (full delisted list).
Needs env POLYGON_API_KEY. Run with backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

KEY = os.environ["POLYGON_API_KEY"]
HOST = "https://api.polygon.io"
OUT = Path(r"D:\data\processed\stocks\polygon")
OUT.mkdir(parents=True, exist_ok=True)
START = pd.Timestamp("2016-07-01")  # ~10yr floor on the Developer upgrade (pre-2016-07 = 403)
sess = requests.Session()


def grouped(date_str: str):
    for _ in range(5):
        try:
            r = sess.get(
                f"{HOST}/v2/aggs/grouped/locale/us/market/stocks/{date_str}",
                params={"adjusted": "true", "apiKey": KEY},
                timeout=30,
            )
            if r.status_code == 200:
                return 200, r.json().get("results") or []
            if r.status_code == 429:
                time.sleep(2)
                continue
            return r.status_code, []
        except Exception:
            time.sleep(1)
    return 0, []


# --- auth guard: is the deep history actually authorized now? ---
sc, _ = grouped("2018-06-01")
if sc != 200:
    print(
        f"NOT AUTHORIZED for 2018 (HTTP {sc}) -> the Developer upgrade isn't active yet. "
        f"Activate it, then re-run this. Aborting (nothing written)."
    )
    sys.exit(0)
print("auth OK for deep history -> pulling 2016-2021...", flush=True)

for yr in range(2016, 2022):  # re-pull 2016..2021 (fixes partial 2021)
    f = OUT / f"daily_{yr}.parquet"
    s = max(pd.Timestamp(f"{yr}-01-01"), START)
    e = pd.Timestamp(f"{yr}-12-31")
    rows = []
    for d in pd.bdate_range(s, e):
        di = int(d.strftime("%Y%m%d"))
        code, res = grouped(d.strftime("%Y-%m-%d"))
        for it in res:
            rows.append((it["T"], di, it.get("o"), it.get("h"), it.get("l"), it.get("c"), it.get("v")))
    if rows:
        pd.DataFrame(rows, columns=["ticker", "date", "open", "high", "low", "close", "volume"]).to_parquet(f)
        print(
            f"{yr}: {len(rows):,} rows, {pd.Series([r[0] for r in rows]).nunique()} tickers -> {f.name}",
            flush=True,
        )

# refresh meta (full active+delisted common-stock list, now incl pre-2021 delistings)
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
print(f"meta refreshed: {len(meta)} common-stock tickers (active+delisted)", flush=True)
print("DONE", flush=True)
