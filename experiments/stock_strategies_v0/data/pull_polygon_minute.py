"""Targeted, resumable 1-min pull from Polygon for the ENTRY DAY of breakout setups.
Survivorship-CLEAN: pulls delisted tickers too (probe confirmed minute history is retained).
We only need entry-day minute (to model the intraday breakout-level cross + tight stop + same-day
stop check); the multi-day hold is tracked on the daily bars we already have. One parquet per
(ticker, date) under D:\\data\\processed\\stocks\\polygon\\minute\\, so re-runs skip what exists
and a scout sample can be extended to the full universe later. Reads env POLYGON_API_KEY.
Run with backend\\.venv\\Scripts\\python.exe.   Optional arg: sample size mode.
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

KEY = os.environ["POLYGON_API_KEY"]
HOST = "https://api.polygon.io"
OUT = Path(r"D:\data\processed\stocks\polygon\minute")
OUT.mkdir(parents=True, exist_ok=True)
SETUPS = Path(__file__).resolve().parents[1] / "unified_v0" / "out" / "setups.parquet"

MODE = sys.argv[1] if len(sys.argv) > 1 else "scout"  # "scout" (~18k) | "full" (all breakouts)
N_ACT, N_DL = 12000, 6000
WORKERS = 12
COLS = ["t", "o", "h", "l", "c", "v"]


def build_sample() -> pd.DataFrame:
    S = pd.read_parquet(SETUPS)
    brk = S[S["is_breakout"] == 1].copy()
    if MODE == "full":
        samp = brk
    else:
        act, dl = brk[brk["active"]], brk[~brk["active"]]
        samp = pd.concat(
            [
                act.sample(min(N_ACT, len(act)), random_state=0),
                dl.sample(min(N_DL, len(dl)), random_state=0),
            ],
            ignore_index=True,
        )
    samp = samp.drop_duplicates(["ticker", "date"]).reset_index(drop=True)
    samp.to_parquet(OUT.parent / "minute_sample_manifest.parquet")
    return samp


def ymd(d: int) -> str:
    s = str(int(d))
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def fpath(t: str, d: int) -> Path:
    return OUT / f"{t}__{int(d)}.parquet"


_SESS = requests.Session()


def fetch(tkr: str, d: int):
    fp = fpath(tkr, d)
    if fp.exists():
        return ("skip", 0)
    url = f"{HOST}/v2/aggs/ticker/{tkr}/range/1/minute/{ymd(d)}/{ymd(d)}"
    for attempt in range(4):
        try:
            r = _SESS.get(
                url, params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": KEY}, timeout=30
            )
            if r.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            r.raise_for_status()
            res = r.json().get("results") or []
            df = pd.DataFrame(res)
            df = df[COLS] if len(df) else pd.DataFrame(columns=COLS)
            df.to_parquet(fp)  # empty file => "pulled, no bars" (don't re-fetch)
            return ("ok", len(df))
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                return ("err", str(e)[:50])
            time.sleep(1.0 * (attempt + 1))
    return ("err", "retries")


def main():
    samp = build_sample()
    jobs = list(zip(samp["ticker"], samp["date"].astype(int)))
    print(f"MODE={MODE}  setups={len(jobs):,}  workers={WORKERS}  out={OUT}")
    t0 = time.time()
    ok = empty = skip = err = bars = 0
    errs = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch, t, d): (t, d) for t, d in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            st, n = f.result()
            if st == "skip":
                skip += 1
            elif st == "err":
                err += 1
                if len(errs) < 10:
                    errs.append((futs[f], n))
            elif n == 0:
                empty += 1
            else:
                ok += 1
                bars += n
            if i % 1000 == 0 or i == len(jobs):
                el = time.time() - t0
                print(
                    f"  {i:,}/{len(jobs):,}  ok={ok:,} empty={empty:,} skip={skip:,} err={err}  "
                    f"{i/el:.1f}/s  {el/60:.1f}min"
                )
    print(f"\nDONE  ok={ok:,} empty={empty:,} skip={skip:,} err={err}  total_bars={bars:,}")
    if errs:
        print("  sample errors:", errs)


if __name__ == "__main__":
    main()
