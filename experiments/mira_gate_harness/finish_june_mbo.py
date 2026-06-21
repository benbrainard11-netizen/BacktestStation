"""Finish the June MBO chain locally (no Databento round-trips):
1. mirror the already-pulled YM 2026-06-09 DBN (was recency-skipped by the pull's mirror pass)
2. materialize clean mbo_trading_day partitions for trading days 2026-06-08..09

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/finish_june_mbo.py
"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

BACKEND = Path(r"C:\Users\benbr\BacktestStation\backend")
sys.path.insert(0, str(BACKEND))
from app.core.paths import warehouse_root  # noqa: E402
from app.ingest import parquet_mirror  # noqa: E402


def main() -> int:
    res = parquet_mirror.mirror_warehouse(
        warehouse_root(), rebuild=False, schemas={"mbo"},
        start=dt.date(2026, 6, 9), end=dt.date(2026, 6, 9),
        symbols={"YM.c.0"}, emit_bars=False)
    print(f"mirror: converted={res.converted_partitions} errors={res.errors}", flush=True)
    if res.errors:
        return 1

    cmd = [str(BACKEND / ".venv" / "Scripts" / "python.exe"),
           str(BACKEND / "scripts" / "materialize_mbo_trading_day_cache.py"),
           "--start", "2026-06-08", "--end", "2026-06-09"]
    print("materializing trading days 2026-06-08..09 ...", flush=True)
    rc = subprocess.call(cmd)
    print(f"materializer rc={rc}", flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
