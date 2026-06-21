"""Generalized 5m SMT scan for the OOS ledger (engine-only imports — the no-5m gotcha).
Usage: ledger_smt_scan.py <start> <end_exclusive> <db_path>"""
from __future__ import annotations

import datetime as dt
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import detect_live as DL  # noqa: E402

start, end, db = dt.date.fromisoformat(sys.argv[1]), dt.date.fromisoformat(sys.argv[2]), Path(sys.argv[3])
if db.exists():
    db.unlink()
DL.recompute_smt(DL.SMT_INDEX_SYMBOLS, start, end, smt_db_url=f"sqlite:///{db.as_posix()}", live_root=None)
n5 = sqlite3.connect(db).execute(
    "select count(*) from research_events where event_type like '5m_%'").fetchone()[0]
print(f"scan {start}..{end}: 5m events={n5}")
raise SystemExit(0 if n5 > 0 else 1)
