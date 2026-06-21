"""Random-day minute pull for the overnight-realism check (the gap/breakout sample was biased).
Sample ~6k RANDOM liquid stock-days (2022-2026, where Polygon minute is available), pull entry-day
1-min into the shared cache. Lets us compare daily-open vs the actual 09:30 tradeable open on
unbiased days and re-measure the overnight premium with real prices. Reads env POLYGON_API_KEY.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

KEY = os.environ["POLYGON_API_KEY"]
HOST = "https://api.polygon.io"
POLY = Path(r"D:\data\processed\stocks\polygon")
MIN = POLY / "minute"; MIN.mkdir(parents=True, exist_ok=True)
COLS = ["t", "o", "h", "l", "c", "v"]
_SESS = requests.Session()


def ymd(d):
    s = str(int(d)); return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def fetch(tkr, d):
    fp = MIN / f"{tkr}__{int(d)}.parquet"
    if fp.exists():
        return "skip"
    url = f"{HOST}/v2/aggs/ticker/{tkr}/range/1/minute/{ymd(d)}/{ymd(d)}"
    for a in range(4):
        try:
            r = _SESS.get(url, params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": KEY}, timeout=30)
            if r.status_code == 429:
                time.sleep(1.5 * (a + 1)); continue
            r.raise_for_status()
            res = r.json().get("results") or []
            (pd.DataFrame(res)[COLS] if len(res) else pd.DataFrame(columns=COLS)).to_parquet(fp)
            return "ok" if len(res) else "empty"
        except Exception:
            if a == 3:
                return "err"
            time.sleep(1.0 * (a + 1))
    return "err"


def main():
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_2022.parquet")) +
                    sorted(POLY.glob("daily_2023.parquet")) + sorted(POLY.glob("daily_2024.parquet")) +
                    sorted(POLY.glob("daily_2025.parquet")) + sorted(POLY.glob("daily_2026.parquet"))], ignore_index=True)
    cs = set(pd.read_parquet(POLY / "meta.parquet")["ticker"])
    df = df[df["ticker"].isin(cs)].sort_values(["ticker", "date"])
    df["dvol"] = df["close"] * df["volume"]
    liq = df[(df["close"] >= 5) & (df["dvol"] >= 5e6)]
    samp = liq.sample(6000, random_state=7)[["ticker", "date"]].drop_duplicates().reset_index(drop=True)
    samp.to_parquet(POLY / "random_minute_manifest.parquet")
    jobs = list(zip(samp["ticker"], samp["date"].astype(int)))
    print(f"random liquid stock-days: {len(jobs):,}")
    c = {"ok": 0, "empty": 0, "skip": 0, "err": 0}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(fetch, t, d) for t, d in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            c[f.result()] += 1
            if i % 2000 == 0:
                print(f"  {i:,}/{len(jobs):,} {c}")
    print(f"DONE {c}")


if __name__ == "__main__":
    main()
