"""Pull SIC code per ticker (Polygon detail endpoint) for the breakout-setup universe -> sector map.

The list endpoint (/v3/reference/tickers) omits sic_code; only the DETAIL endpoint
(/v3/reference/tickers/{T}) returns it. Threaded, retry on 429/timeout, resumable (skips tickers
already in the output). Reads env POLYGON_API_KEY. Writes ticker_sic.parquet (ticker, sic, sic_desc).
Run with backend\\.venv\\Scripts\\python.exe -u.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

KEY = os.environ["POLYGON_API_KEY"]
POLY = Path(r"D:\data\processed\stocks\polygon")
SETUPS = Path(r"C:\Users\benbr\BacktestStation\experiments\stock_strategies_v0\unified_v0\out\setups.parquet")
OUT = POLY / "ticker_sic.parquet"
WORKERS = 16
_S = requests.Session()


def fetch(t: str):
    url = f"https://api.polygon.io/v3/reference/tickers/{t}"
    for attempt in range(4):
        try:
            r = _S.get(url, params={"apiKey": KEY}, timeout=30)
            if r.status_code == 429:
                time.sleep(1.0 * (attempt + 1))
                continue
            res = r.json().get("results") or {}
            return (t, res.get("sic_code"), res.get("sic_description"))
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return (t, None, None)


def main():
    S = pd.read_parquet(SETUPS)
    tickers = sorted(set(S[S["is_breakout"] == 1]["ticker"]))
    done = {}
    if OUT.exists():
        prev = pd.read_parquet(OUT)
        done = dict(zip(prev["ticker"], prev["sic"]))
        tickers = [t for t in tickers if t not in done]
    print(f"{len(tickers):,} tickers to fetch (have {len(done):,})", flush=True)
    rows = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(fetch, t) for t in tickers]
        for i, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if i % 500 == 0 or i == len(tickers):
                print(f"  {i}/{len(tickers)}  {i/(time.time()-t0):.0f}/s", flush=True)
    df = pd.DataFrame(rows, columns=["ticker", "sic", "sic_desc"])
    if OUT.exists():
        df = pd.concat([pd.read_parquet(OUT), df], ignore_index=True).drop_duplicates("ticker")
    df.to_parquet(OUT)
    print(f"DONE: {len(df):,} tickers, with sic {df['sic'].notna().sum():,} -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
