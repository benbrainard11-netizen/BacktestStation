"""Pull stock EOD + 1-min bars for a ticker list from ThetaData (equities sub confirmed 2026-06-14).
Writes D:\\data\\processed\\stocks\\eod\\<T>.parquet and \\m1\\<T>.parquet (theta_store-cached, so
re-runs resume). hist/stock/eod 475s on long ranges -> chunk EOD quarterly; 1-min is heavier -> chunk
monthly. Times are ET market clock (ms_of_day).

Run: THETA_PORT=25511 python pull_stock_bars.py NVDA,AAPL,MSFT,TSLA 20230101 20261231
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theta_store as TS  # noqa: E402

OUT = Path(r"D:\data\processed\stocks")
TICKERS = (sys.argv[1].split(",") if len(sys.argv) > 1 else ["NVDA", "AAPL", "MSFT", "TSLA"])
START = int(sys.argv[2]) if len(sys.argv) > 2 else 20230101
END = int(sys.argv[3]) if len(sys.argv) > 3 else 20261231


def chunks(start: int, end: int, months: int):
    cur, endts = pd.Timestamp(str(start)), pd.Timestamp(str(end))
    while cur <= endts:
        ce = min(endts, cur + pd.DateOffset(months=months) - pd.Timedelta(days=1))
        yield int(cur.strftime("%Y%m%d")), int(ce.strftime("%Y%m%d"))
        cur = ce + pd.Timedelta(days=1)


def pull(ep: str, t: str, months: int, **kw) -> pd.DataFrame:
    parts = []
    for a, b in chunks(START, END, months):
        try:
            c = TS.fetch_flat(ep, root=t, start_date=a, end_date=b, **kw)
        except Exception as ex:
            print(f"  {t} {ep.split('/')[-1]} {a}-{b} FAIL {type(ex).__name__}", flush=True)
            continue
        if len(c):
            parts.append(c)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


for t in TICKERS:
    eod = pull("hist/stock/eod", t, 3)                      # quarterly (475 on big ranges)
    if len(eod):
        eod = eod[["date", "open", "high", "low", "close", "volume"]].drop_duplicates("date").sort_values("date")
        (OUT / "eod").mkdir(parents=True, exist_ok=True)
        eod.to_parquet(OUT / "eod" / f"{t}.parquet")
    m1 = pull("hist/stock/ohlc", t, 1, ivl=60000)           # monthly (1-min is heavier)
    if len(m1):
        d = pd.to_datetime(m1["date"].astype(int).astype(str), format="%Y%m%d")
        m1["ts_et"] = d + pd.to_timedelta(m1["ms_of_day"].astype("int64"), unit="ms")
        m1 = m1[["ts_et", "date", "ms_of_day", "open", "high", "low", "close", "volume"]].drop_duplicates(
            ["date", "ms_of_day"]).sort_values("ts_et")
        (OUT / "m1").mkdir(parents=True, exist_ok=True)
        m1.to_parquet(OUT / "m1" / f"{t}.parquet")
    print(f"{t}: eod={len(eod)} rows, 1m={len(m1)} rows  ({START}..{END})", flush=True)
