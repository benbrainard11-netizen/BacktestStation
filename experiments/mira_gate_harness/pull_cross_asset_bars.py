"""Cross-asset expansion data: 1m bars 2015-2026 for BTC/FX/metals/energy/rates futures
(Databento GLBX, $0 quoted under sub). Writes the standard bars layout so every existing
tool (legal_reclaim_bars, smt_bench.load_1m) works on the new symbols unchanged.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/pull_cross_asset_bars.py
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import databento as db
import numpy as np
import pandas as pd

SYMS = ["BTC.c.0", "6E.c.0", "6J.c.0", "6B.c.0", "GC.c.0", "SI.c.0", "CL.c.0", "ZN.c.0", "ZB.c.0",
        "ETH.c.0", "MBT.c.0"]  # maturity-thesis test: ETH listed 2021 (3yr younger than BTC)
BARS = Path(r"D:\data\processed\bars\timeframe=1m")
client = db.Historical(key=os.environ["DATABENTO_API_KEY"])

for sym in SYMS:
    done_marker = BARS / f"symbol={sym}" / "_pull_complete.txt"
    if done_marker.exists():
        print(f"{sym}: already complete, skip", flush=True)
        continue
    print(f"{sym}: pulling 2015-2026 ohlcv-1m ...", flush=True)
    df = None
    for attempt in range(4):
        try:
            store = client.timeseries.get_range(dataset="GLBX.MDP3", schema="ohlcv-1m",
                                                symbols=[sym], stype_in="continuous",
                                                start="2015-01-01", end="2026-06-10")
            df = store.to_df().reset_index()
            break
        except Exception as e:
            print(f"  attempt {attempt}: {type(e).__name__}: {e}", flush=True)
            time.sleep(30 * (attempt + 1))
    if df is None or not len(df):
        print(f"  {sym}: FAILED/empty", flush=True)
        continue
    tscol = "ts_event" if "ts_event" in df.columns else df.columns[0]
    df = df.rename(columns={tscol: "ts_event"})
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    df["symbol"] = sym
    df["trade_count"] = np.uint32(0)
    df["vwap"] = np.nan
    out_cols = ["ts_event", "symbol", "open", "high", "low", "close", "volume", "trade_count", "vwap"]
    df["_d"] = df["ts_event"].dt.date
    n_days = 0
    for d, g in df.groupby("_d"):
        p = BARS / f"symbol={sym}" / f"date={d.isoformat()}" / "part-000.parquet"
        if p.exists():
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        g[out_cols].to_parquet(p, index=False)
        n_days += 1
    done_marker.write_text(f"{len(df)} rows, {n_days} new days")
    print(f"  {sym}: {len(df)} bars -> {n_days} new day partitions", flush=True)
print("DONE", flush=True)
