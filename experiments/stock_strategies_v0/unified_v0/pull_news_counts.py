"""Final breakout-selector lever: a news-CATALYST proxy. For each breakout setup, count Polygon news
articles in the 5 days up to and including the breakout day (does the move have a REAL reason behind it,
vs pure technical noise?). Free + covers delisted. Output out/news_counts.parquet.
Reads env POLYGON_API_KEY. Run with backend\\.venv\\Scripts\\python.exe.
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
HERE = Path(__file__).resolve().parent
_SESS = requests.Session()


def iso(d, end=False):
    s = str(int(d)); base = f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return base + ("T23:59:59Z" if end else "T00:00:00Z")


def count_news(tkr, date):
    g = (pd.Timestamp(iso(date)) - pd.Timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for a in range(4):
        try:
            r = _SESS.get(f"{HOST}/v2/reference/news", params={
                "ticker": tkr, "published_utc.gte": g, "published_utc.lte": iso(date, end=True),
                "limit": 50, "apiKey": KEY}, timeout=30)
            if r.status_code == 429:
                time.sleep(1.5 * (a + 1)); continue
            r.raise_for_status()
            return tkr, int(date), len(r.json().get("results", []) or [])
        except Exception:
            if a == 3:
                return tkr, int(date), -1
            time.sleep(1.0 * (a + 1))
    return tkr, int(date), -1


def main():
    res = pd.read_parquet(HERE / "out" / "intraday_entry_results.parquet")[["tkr", "date"]].drop_duplicates()
    jobs = list(zip(res["tkr"], res["date"].astype(int)))
    print(f"news counts for {len(jobs):,} setups...")
    rows, done = [], 0
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(count_news, t, d) for t, d in jobs]
        for f in as_completed(futs):
            rows.append(f.result()); done += 1
            if done % 3000 == 0:
                print(f"  {done:,}/{len(jobs):,}")
    F = pd.DataFrame(rows, columns=["tkr", "date", "news_5d"])
    F["news_5d"] = F["news_5d"].clip(lower=0)
    F.to_parquet(HERE / "out" / "news_counts.parquet")
    print(f"DONE {len(F):,} | mean {F.news_5d.mean():.1f} | 0-news {(F.news_5d==0).mean()*100:.0f}% | "
          f"capped-50 {(F.news_5d>=50).mean()*100:.0f}%")


if __name__ == "__main__":
    main()
