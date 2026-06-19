"""Delisted-inclusive (survivorship) daily EOD + splits from ThetaData (Standard stock sub).

Writes raw EOD -> D:\\data\\processed\\stocks\\daily_pit\\<T>.parquet  (date,open,high,low,close,volume)
and split history -> D:\\data\\processed\\stocks\\corp_actions\\<T>.parquet (for split-adjustment).
ThetaData stock EOD is RAW + range-capped (~1yr) so EOD is chunked quarterly; splits pull in one call.
Resumable (skips tickers already written). Standard floor = 2016-01.
Run: THETA_PORT=25510 python pull_eod_pit.py SIVB,FRC,ATVI 20160101 20261231
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "options_signals_v0"))
import theta_store as TS  # noqa: E402

DP = Path(r"D:\data\processed\stocks\daily_pit")
CA = Path(r"D:\data\processed\stocks\corp_actions")
TICK = sys.argv[1].split(",") if len(sys.argv) > 1 else ["SIVB"]
START = int(sys.argv[2]) if len(sys.argv) > 2 else 20160101
END = int(sys.argv[3]) if len(sys.argv) > 3 else 20261231


def chunks(s: int, e: int, months: int):
    cur, end = pd.Timestamp(str(s)), pd.Timestamp(str(e))
    while cur <= end:
        ce = min(end, cur + pd.DateOffset(months=months) - pd.Timedelta(days=1))
        yield int(cur.strftime("%Y%m%d")), int(ce.strftime("%Y%m%d"))
        cur = ce + pd.Timedelta(days=1)


def main() -> int:
    DP.mkdir(parents=True, exist_ok=True)
    CA.mkdir(parents=True, exist_ok=True)
    for t in TICK:
        span = "exists"
        if not (DP / f"{t}.parquet").exists():
            parts = []
            for a, b in chunks(START, END, 3):  # quarterly (EOD range-capped)
                try:
                    c = TS.fetch_flat("hist/stock/eod", root=t, start_date=a, end_date=b)
                except Exception:
                    continue
                if len(c):
                    parts.append(c)
            if parts:
                d = (
                    pd.concat(parts, ignore_index=True)[["date", "open", "high", "low", "close", "volume"]]
                    .drop_duplicates("date")
                    .sort_values("date")
                )
                d.to_parquet(DP / f"{t}.parquet")
                span = f"{int(d['date'].min())}..{int(d['date'].max())} ({len(d)} rows)"
            else:
                span = "NO DATA"
        if not (CA / f"{t}.parquet").exists():
            try:
                sp = TS.fetch_flat("hist/stock/split", root=t, start_date=20100101, end_date=END)
                if len(sp):
                    sp.to_parquet(CA / f"{t}.parquet")
            except Exception:
                pass
        print(f"{t}: eod {span}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
