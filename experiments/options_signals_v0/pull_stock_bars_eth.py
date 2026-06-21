"""Extended-hours (incl PREMARKET) 1-min stock bars from ThetaData -> stocks\\m1_eth\\.

Copy of pull_stock_bars.py with rth=false (verified 2026-06-18: returns pre-09:30 bars) and m1-only.
Keeps the tradeable extended session 04:00-20:00 ET (premarket + RTH + after-hours; drops dead
overnight). Resumable (skips tickers already written). Cols: ts_et,date,ms_of_day,o,h,l,c,volume.
Run: THETA_PORT=25511 python pull_stock_bars_eth.py NVDA,AAPL 20230601 20261231
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theta_store as TS  # noqa: E402

OUT = Path(r"D:\data\processed\stocks") / "m1_eth"
TICKERS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["AAPL"]
START = int(sys.argv[2]) if len(sys.argv) > 2 else 20230601
END = int(sys.argv[3]) if len(sys.argv) > 3 else 20261231
ETH_LO, ETH_HI = 14400000, 72000000        # 04:00, 20:00 ET (ms-of-day) — the extended trading session


def chunks(start: int, end: int, months: int):
    cur, endts = pd.Timestamp(str(start)), pd.Timestamp(str(end))
    while cur <= endts:
        ce = min(endts, cur + pd.DateOffset(months=months) - pd.Timedelta(days=1))
        yield int(cur.strftime("%Y%m%d")), int(ce.strftime("%Y%m%d"))
        cur = ce + pd.Timedelta(days=1)


def pull(t: str) -> pd.DataFrame:
    parts = []
    for a, b in chunks(START, END, 1):                 # monthly (1-min is heavy)
        try:
            c = TS.fetch_flat("hist/stock/ohlc", root=t, start_date=a, end_date=b, ivl=60000, rth="false")
        except Exception as ex:
            print(f"  {t} {a}-{b} FAIL {type(ex).__name__}", flush=True)
            continue
        if len(c):
            parts.append(c)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for t in TICKERS:
        if (OUT / f"{t}.parquet").exists():            # resumable
            print(f"{t}: exists, skip", flush=True)
            continue
        m1 = pull(t)
        if len(m1):
            m1 = m1[(m1["ms_of_day"] >= ETH_LO) & (m1["ms_of_day"] <= ETH_HI)].copy()
            d = pd.to_datetime(m1["date"].astype(int).astype(str), format="%Y%m%d")
            m1["ts_et"] = d + pd.to_timedelta(m1["ms_of_day"].astype("int64"), unit="ms")
            m1 = (m1[["ts_et", "date", "ms_of_day", "open", "high", "low", "close", "volume"]]
                  .drop_duplicates(["date", "ms_of_day"]).sort_values("ts_et"))
            m1.to_parquet(OUT / f"{t}.parquet")
        pre = int((m1["ms_of_day"] < 34200000).sum()) if len(m1) else 0
        print(f"{t}: {len(m1)} eth bars ({pre} pre-09:30)  ({START}..{END})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
