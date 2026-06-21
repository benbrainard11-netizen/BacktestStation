"""Pull recent Databento MBP-1 (top-of-book) for the holdout window so realized_r has bid/ask.

Narrow + safe: schema=mbp-1 on GLBX.MDP3, Mira index universe, continuous symbology. Prints the
Databento cost quote and ABORTS if it exceeds --cost-threshold-usd. Writes parquet in the exact
layout realized_r.py reads: raw/databento/mbp-1/symbol=<S>/date=<D>/part-000.parquet with bid_px/ask_px.
Skips days already on disk.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/pull_mbp1.py --start 2026-05-28 --end 2026-06-06
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import databento as db
import pandas as pd

sys.path.insert(0, r"C:\Users\benbr\BacktestStation\backend")
from app.core.paths import warehouse_root  # noqa: E402
from app.ingest import cost_estimator  # noqa: E402

DATASET, SCHEMA, STYPE = "GLBX.MDP3", "mbp-1", "continuous"
SYMS = ["ES.c.0", "NQ.c.0", "RTY.c.0", "YM.c.0"]
RENAME = {f"{b}_00": b for b in ("bid_px", "ask_px", "bid_sz", "ask_sz", "bid_ct", "ask_ct")}


def outp(root: Path, day: dt.date, sym: str) -> Path:
    return root / "raw" / "databento" / "mbp-1" / f"symbol={sym}" / f"date={day.isoformat()}" / "part-000.parquet"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True, help="exclusive UTC date")
    ap.add_argument("--cost-threshold-usd", type=float, default=50.0)
    args = ap.parse_args()
    root = warehouse_root()
    s_date = dt.date.fromisoformat(args.start)
    e_date = dt.date.fromisoformat(args.end)
    start_iso = dt.datetime.combine(s_date, dt.time.min, tzinfo=dt.timezone.utc).isoformat()
    end_iso = dt.datetime.combine(e_date, dt.time.min, tzinfo=dt.timezone.utc).isoformat()

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        print("DATABENTO_API_KEY not set"); return 1
    client = db.Historical(key=key)
    cost = cost_estimator.estimate(client, SYMS, SCHEMA, start_iso, end_iso)
    print(f"COST QUOTE: mbp-1 {args.start}..{args.end} {SYMS} = ${cost:.4f}", flush=True)
    if cost > args.cost_threshold_usd:
        print(f"ABORT: ${cost:.4f} exceeds guard ${args.cost_threshold_usd:.2f}"); return 2

    days = pd.date_range(s_date, e_date - dt.timedelta(days=1), freq="D")
    pulled = skipped = 0
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
                continue
            if df is None or len(df) == 0:
                print(f"  empty {sym} {d.date()}", flush=True)
                continue
            df = df.reset_index().rename(columns=RENAME)
            if "ts_event" not in df.columns:
                df = df.rename(columns={df.columns[0]: "ts_event"})
            p.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(p, index=False)
            pulled += 1
            print(f"  wrote {sym} {d.date()} ({len(df)} rows, bid_px={'bid_px' in df.columns})", flush=True)
    print(f"\ndone: pulled={pulled} skipped={skipped} cost=${cost:.4f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
