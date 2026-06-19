"""Concurrent delisted-inclusive daily EOD + splits from ThetaData Standard -> daily_pit\\ + corp_actions\\.

ThetaData stock EOD is raw + range-capped (~6mo) with no bulk endpoint, so this maxes throughput:
a thread pool over symbols (each symbol = sequential 6-month EOD chunks), sharded across the 3
terminals (run one process per THETA_PORT). Resumable (skips symbols already in daily_pit). EOD is
raw -> also pulls splits for split-adjustment. Standard floor = 2016-01.
Run: THETA_PORT=25510 WORKERS=7 python pull_survivorship.py <SHARD> <NSHARDS> [start] [end]
"""

from __future__ import annotations

import io
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

PORT = os.environ.get("THETA_PORT", "25510")
BASE = f"http://127.0.0.1:{PORT}/v2"
WORKERS = int(os.environ.get("WORKERS", "7"))
SHARD = int(sys.argv[1]) if len(sys.argv) > 1 else 0
NSHARDS = int(sys.argv[2]) if len(sys.argv) > 2 else 1
START = int(sys.argv[3]) if len(sys.argv) > 3 else 20160101
END = int(sys.argv[4]) if len(sys.argv) > 4 else 20261231
LIST = Path(__file__).resolve().parent / "survivorship_symbols.txt"
DP = Path(r"D:\data\processed\stocks\daily_pit")
CA = Path(r"D:\data\processed\stocks\corp_actions")
EOD_COLS = ["date", "open", "high", "low", "close", "volume"]


def chunks(s: int, e: int, months: int = 6):
    cur, end = pd.Timestamp(str(s)), pd.Timestamp(str(e))
    while cur <= end:
        ce = min(end, cur + pd.DateOffset(months=months) - pd.Timedelta(days=1))
        yield int(cur.strftime("%Y%m%d")), int(ce.strftime("%Y%m%d"))
        cur = ce + pd.Timedelta(days=1)


def get_csv(ep: str, **p) -> str | None:
    for _ in range(2):  # retry once: terminals are flaky under load
        try:
            r = requests.get(f"{BASE}/{ep}", params={**p, "use_csv": "true"}, timeout=45)
            if r.status_code == 200:
                return r.text
            if r.status_code in (471, 472, 474, 476):  # permission/no-data: real empty, don't retry
                return ""
        except Exception:
            pass
    return None


def pull_one(t: str) -> int:
    outf = DP / f"{t}.parquet"
    if outf.exists():
        return 0
    frames = []
    found = False
    empties = 0
    for a, b in chunks(START, END):
        txt = get_csv("hist/stock/eod", root=t, start_date=a, end_date=b)
        ok = False
        if txt and len(txt.strip().splitlines()) >= 2:
            try:
                frames.append(pd.read_csv(io.StringIO(txt)))
                found, empties, ok = True, 0, True
            except Exception:
                ok = False
        if not ok and found:
            empties += 1
            if empties >= 2:  # data has ended (delisted/long halt) -> skip the dead tail
                break
    if not frames:
        return 0
    d = pd.concat(frames, ignore_index=True)
    cols = [c for c in EOD_COLS if c in d.columns]
    if "date" not in cols:
        return 0
    d = d[cols].drop_duplicates("date").sort_values("date")
    DP.mkdir(parents=True, exist_ok=True)
    tmp = outf.with_suffix(".tmp.parquet")
    d.to_parquet(tmp)
    tmp.replace(outf)
    sp = get_csv("hist/stock/split", root=t, start_date=20100101, end_date=END)
    if sp and len(sp.strip().splitlines()) > 1:
        try:
            CA.mkdir(parents=True, exist_ok=True)
            pd.read_csv(io.StringIO(sp)).to_parquet(CA / f"{t}.parquet")
        except Exception:
            pass
    return 1


def main() -> int:
    syms = [s.strip() for s in LIST.read_text().splitlines() if s.strip()][SHARD::NSHARDS]
    print(f"[s{SHARD}/{NSHARDS}] {len(syms)} symbols, WORKERS={WORKERS}, {START}..{END}", flush=True)
    wrote = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for i, r in enumerate(pool.map(pull_one, syms)):
            wrote += r
            if (i + 1) % 500 == 0:
                print(f"[s{SHARD}] {i+1}/{len(syms)}, {wrote} written", flush=True)
    print(f"[s{SHARD}] DONE: {wrote} written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
