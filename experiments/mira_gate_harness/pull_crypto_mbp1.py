"""Pull ETH/BTC/MBT MBP-1 (top-of-book) into the standard warehouse layout so r2_upload
catches it. Matches the existing futures MBP-1 window (2025-05-01 .. 2026-06-10). $9.43 quoted.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/pull_crypto_mbp1.py
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import databento as db
import pandas as pd

sys.path.insert(0, r"C:\Users\benbr\BacktestStation\backend")
from app.core.paths import warehouse_root  # noqa: E402

DATASET, SCHEMA, STYPE = "GLBX.MDP3", "mbp-1", "continuous"
SYMS = ["ETH.c.0", "BTC.c.0", "MBT.c.0"]
START, END = dt.date(2025, 5, 1), dt.date(2026, 6, 10)  # end exclusive
RENAME = {f"{b}_00": b for b in ("bid_px", "ask_px", "bid_sz", "ask_sz", "bid_ct", "ask_ct")}


def outp(root: Path, day: dt.date, sym: str) -> Path:
    return root / "raw" / "databento" / "mbp-1" / f"symbol={sym}" / f"date={day.isoformat()}" / "part-000.parquet"


def main() -> int:
    root = warehouse_root()
    client = db.Historical(key=os.environ["DATABENTO_API_KEY"])
    days = pd.date_range(START, END - dt.timedelta(days=1), freq="D")
    pulled = skipped = empty = errs = 0
    for d in days:
        for sym in SYMS:
            p = outp(root, d.date(), sym)
            if p.exists() and p.stat().st_size > 0:
                skipped += 1
                continue
            d0 = dt.datetime.combine(d.date(), dt.time.min, tzinfo=dt.timezone.utc)
            d1 = d0 + dt.timedelta(days=1)
            try:
                store = client.timeseries.get_range(dataset=DATASET, schema=SCHEMA, symbols=[sym],
                                                    stype_in=STYPE, start=d0.isoformat(), end=d1.isoformat())
                df = store.to_df()
            except Exception as exc:
                print(f"  ERR {sym} {d.date()}: {type(exc).__name__}: {exc}", flush=True)
                errs += 1
                continue
            if df is None or len(df) == 0:
                empty += 1
                continue
            df = df.reset_index().rename(columns=RENAME)
            if "ts_event" not in df.columns:
                df = df.rename(columns={df.columns[0]: "ts_event"})
            p.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(p, index=False)
            pulled += 1
            if pulled % 50 == 0:
                print(f"  ...{pulled} days pulled", flush=True)
    print(f"DONE: pulled={pulled} skipped={skipped} empty={empty} errors={errs}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
