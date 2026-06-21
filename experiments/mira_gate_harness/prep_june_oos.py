"""Prep the fresh June 8-9 trading days as a true-OOS window for the harness.

1. Build 1m bars for UTC dates 2026-06-08/09 from the pulled MBP-1 raw parquet, using the
   mirror's OWN _compute_1m_bars (same trades-only semantics as the existing bars layer).
   Caveats: RTY 2026-06-08 MBP-1 is missing (Databento server fault, 3 attempts) -> no RTY
   bars that day; Sunday-evening Globex (6/7 UTC) returned no data (known Databento gap,
   same as trading_day 2026-05-18 precedent).
2. Re-scan SMT WITH 5m for 2026-06-08..06-10 into data/june_smt5m.sqlite (fix_holdout_5m
   pattern; repo meta.sqlite has no 5m after 2026-05-22).

After this: harness window "june_oos" (registered in harness.py) builds from these.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/prep_june_oos.py
"""
from __future__ import annotations

import collections
import datetime as dt
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, r"C:\Users\benbr\BacktestStation\backend")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
from app.ingest.parquet_mirror import _compute_1m_bars  # noqa: E402
import detect_live as DL  # noqa: E402

RAW = Path(r"D:\data\raw\databento\mbp-1")
BARS = Path(r"D:\data\processed\bars\timeframe=1m")
SYMS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
DAYS = ["2026-06-08", "2026-06-09"]
SMT_DB = Path(__file__).resolve().parent / "data" / "june_smt5m.sqlite"


def build_bars() -> None:
    for day in DAYS:
        for sym in SYMS:
            src = RAW / f"symbol={sym}" / f"date={day}" / "part-000.parquet"
            dst = BARS / f"symbol={sym}" / f"date={day}" / "part-000.parquet"
            if dst.exists():
                print(f"  bars exist {sym} {day}", flush=True)
                continue
            if not src.exists():
                print(f"  NO SOURCE {sym} {day} (known: RTY 06-08 pull failed)", flush=True)
                continue
            df = pd.read_parquet(src, columns=["ts_event", "action", "price", "size"])
            df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
            bars = _compute_1m_bars(df, sym)
            if bars.empty:
                print(f"  EMPTY bars {sym} {day}", flush=True)
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            bars.to_parquet(dst, index=False)
            print(f"  wrote bars {sym} {day}: {len(bars)} minutes", flush=True)


def scan_smt() -> None:
    if SMT_DB.exists():
        SMT_DB.unlink()
    url = f"sqlite:///{SMT_DB.as_posix()}"
    print(f"recompute_smt (vendored, incl 5m) -> {SMT_DB} for 2026-06-08..2026-06-10 ...", flush=True)
    res = DL.recompute_smt(DL.SMT_INDEX_SYMBOLS, dt.date(2026, 6, 8), dt.date(2026, 6, 10),
                           smt_db_url=url, live_root=None)
    print(f"scan results: {len(res)} (detector x mode)", flush=True)
    c = sqlite3.connect(SMT_DB)
    cnt = collections.Counter()
    for (et,) in c.execute("select event_type from research_events where feature_name='smt_prev_candle_divergence'"):
        m = re.match(r"^(\d+m|\d+h)_", str(et))
        cnt[m.group(1) if m else "?"] += 1
    c.close()
    print(f"June SMT by timeframe: {dict(sorted(cnt.items()))}")
    print(f"5m present: {'5m' in cnt}  (total smt_prev={sum(cnt.values())})")


def main() -> int:
    print("[1/2] bars from MBP-1", flush=True)
    build_bars()
    print("[2/2] SMT 5m re-scan", flush=True)
    scan_smt()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
