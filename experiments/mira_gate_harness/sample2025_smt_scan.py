"""A3 step 1: SMT scan (vendored, incl 5m) for the 2025 sample week used by the MBO
window-backfill viability quote. Clean process — import ONLY live_engine/engine (the
backend-app-first import poisons sys.modules with the no-5m detector; see june_smt_scan.py).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/sample2025_smt_scan.py
"""
from __future__ import annotations

import collections
import datetime as dt
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import detect_live as DL  # noqa: E402

DB = Path(__file__).resolve().parent / "data" / "sample2025_smt5m.sqlite"
START, END = dt.date(2025, 3, 10), dt.date(2025, 3, 15)  # Mon-Fri sample week


def main() -> int:
    if DB.exists():
        DB.unlink()
    url = f"sqlite:///{DB.as_posix()}"
    print(f"recompute_smt -> {DB} for {START}..{END} ...", flush=True)
    DL.recompute_smt(DL.SMT_INDEX_SYMBOLS, START, END, smt_db_url=url, live_root=None)
    c = sqlite3.connect(DB)
    cnt = collections.Counter()
    for (et,) in c.execute("select event_type from research_events where feature_name='smt_prev_candle_divergence'"):
        m = re.match(r"^(\d+m|\d+h)_", str(et))
        cnt[m.group(1) if m else "?"] += 1
    c.close()
    print(f"sample SMT by timeframe: {dict(sorted(cnt.items()))}")
    print(f"5m present: {'5m' in cnt}")
    return 0 if "5m" in cnt else 1


if __name__ == "__main__":
    raise SystemExit(main())
