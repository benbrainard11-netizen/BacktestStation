"""Build + cache CLEAN 5m bars from local MBP-1 mid -- the trustworthy foundation after clean_bar_check showed
the legacy read_bars 5m are contaminated (trade-OHLC wick noise). Everything intraday must rebuild on these.

Mid = (bid+ask)/2 resampled to 5m OHLC, read month-by-month to bound memory. Cached to out/clean_bars/{sym}.parquet.
MBP-1 covers ~1yr (2025-05+), so this is a ~1yr trustworthy window (shorter than the 3.3yr legacy bars, but real).
Energy first (tractable: ~0.2-1.5M rows/day); index/rates MBP-1 are far heavier and come later.

Run (background): backend/.venv/Scripts/python.exe experiments/asset_profiles_v0/build_clean_bars.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.core.paths import warehouse_root  # noqa: E402
from app.data.reader import read_mbp1  # noqa: E402

OUT = Path(__file__).resolve().parent / "out" / "clean_bars"
OUT.mkdir(parents=True, exist_ok=True)
SYMS = ["RB.c.0", "HO.c.0", "BZ.c.0", "CL.c.0", "NG.c.0"]


def build(sym: str) -> int:
    p = warehouse_root() / "raw/databento/mbp-1" / f"symbol={sym}"
    if not p.exists():
        print(f"  {sym}: no MBP-1"); return 0
    dates = sorted(d.name.split("=")[1] for d in p.iterdir() if d.is_dir())
    months = sorted({d[:7] for d in dates})
    out = []
    for m in months:
        s = pd.Timestamp(m + "-01")
        e = (s + pd.offsets.MonthBegin(1)).date().isoformat()
        try:
            t = read_mbp1(symbol=sym, start=s.date().isoformat(), end=e, columns=["ts_event", "bid_px", "ask_px"])
        except Exception:  # noqa: BLE001
            continue
        if len(t) == 0:
            continue
        t = t.dropna(subset=["bid_px", "ask_px"])
        mid = pd.Series(((t["bid_px"] + t["ask_px"]) / 2.0).to_numpy(),
                        index=pd.to_datetime(t["ts_event"].to_numpy(), utc=True))
        out.append(mid.resample("5min").ohlc().dropna())
    if not out:
        print(f"  {sym}: no bars"); return 0
    b = pd.concat(out)
    b.columns = ["open", "high", "low", "close"]
    b.to_parquet(OUT / f"{sym}.parquet")
    return len(b)


def main() -> int:
    for sym in SYMS:
        t0 = time.time()
        n = build(sym)
        print(f"  {sym:8} {n:7,} clean 5m bars ({time.time()-t0:.0f}s)")
    print(f"\nwrote -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
