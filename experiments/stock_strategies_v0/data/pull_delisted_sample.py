"""Pull EOD for an UNBIASED random sample of NON-survivor ThetaData symbols (= in ThetaData's
list but not in our yfinance survivors) -> a representative delisted/dead set for the
survivorship probe. 2-year chunks (dodge the HTTP 475 long-range bug), 8s timeout (skip dead
symbols fast), keep only those with real history (>=250 rows). Resumable (skips existing).
Writes D:\\data\\processed\\stocks\\delisted\\<T>.parquet. Run with backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
import requests

BASE = "http://127.0.0.1:25511/v2"
OUT = Path(r"D:\data\processed\stocks\delisted")
OUT.mkdir(parents=True, exist_ok=True)
SURV = {p.stem for p in Path(r"D:\data\processed\stocks\daily").glob("*.parquet")}
SYMS = [
    s.strip()
    for s in open(
        r"C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\thetadata_stock_symbols.txt"
    )
    if s.strip()
]
# non-survivors, drop preferreds/units/warrants (dot tickers) and odd-length
non = [s for s in SYMS if s not in SURV and "." not in s and 1 <= len(s) <= 5]
random.seed(7)
sample = random.sample(non, min(800, len(non)))
CHUNKS = [
    (20160101, 20171231),
    (20180101, 20191231),
    (20200101, 20211231),
    (20220101, 20231231),
    (20240101, 20260619),
]
print(f"non-survivor pool {len(non)} | sampling {len(sample)}", flush=True)


def pull(sym):
    parts = []
    for a, b in CHUNKS:
        try:
            r = requests.get(
                f"{BASE}/hist/stock/eod", params={"root": sym, "start_date": a, "end_date": b}, timeout=8
            )
        except Exception:
            continue
        if r.status_code != 200:
            continue
        j = r.json()
        resp = j.get("response") or []
        if not resp:
            continue
        parts.append(pd.DataFrame(resp, columns=j["header"]["format"]))
    if not parts:
        return None
    d = pd.concat(parts, ignore_index=True)
    keep = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in d.columns]
    if "date" not in keep or "close" not in keep:
        return None
    return d[keep].drop_duplicates("date").sort_values("date").reset_index(drop=True)


done = {p.stem for p in OUT.glob("*.parquet")}
ok = 0
for i, s in enumerate(sample):
    if s in done:
        ok += 1
        continue
    d = pull(s)
    if d is not None and len(d) >= 250:
        d.to_parquet(OUT / f"{s}.parquet")
        ok += 1
    if (i + 1) % 50 == 0:
        print(f"  ...{i+1}/{len(sample)}  kept={ok}", flush=True)
print(f"DONE: kept {ok} delisted-with-history of {len(sample)} sampled -> {OUT}", flush=True)
