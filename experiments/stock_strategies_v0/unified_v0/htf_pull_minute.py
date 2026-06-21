"""Pull entry-day 1-min bars for the HTF ladder candidates into the shared minute cache
(skips what's already there). Reads env POLYGON_API_KEY. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

KEY = os.environ["POLYGON_API_KEY"]
HOST = "https://api.polygon.io"
MIN = Path(r"D:\data\processed\stocks\polygon\minute")
MIN.mkdir(parents=True, exist_ok=True)
CAND = Path(__file__).resolve().parent / "out" / "htf_candidates.parquet"
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
            df = pd.DataFrame(res)
            (df[COLS] if len(df) else pd.DataFrame(columns=COLS)).to_parquet(fp)
            return "ok" if len(df) else "empty"
        except Exception:
            if a == 3:
                return "err"
            time.sleep(1.0 * (a + 1))
    return "err"


def main():
    S = pd.read_parquet(CAND).drop_duplicates(["ticker", "date"])
    jobs = list(zip(S["ticker"], S["date"].astype(int)))
    print(f"HTF candidate days: {len(jobs):,}")
    c = {"ok": 0, "empty": 0, "skip": 0, "err": 0}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(fetch, t, d) for t, d in jobs]
        for f in as_completed(futs):
            c[f.result()] += 1
    print(f"DONE {c}")


if __name__ == "__main__":
    main()
