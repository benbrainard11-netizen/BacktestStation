"""Phase 1 of the holdout fix: re-scan the recent-window SMT WITH the 5m mode (vendored 5m-capable
detector via detect_live.recompute_smt) into a FRESH sqlite, so the harness holdout rebuild gets the
~60% of setups the no-5m BacktestStation-side scan dropped. Additive — does not touch meta.sqlite.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/fix_holdout_5m.py
Then rebuild: MIRA_SMT_DB=<this db> harness.py --build oos_holdout (after deleting the cached parquet).
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

DB = Path(__file__).resolve().parent / "data" / "holdout_smt5m.sqlite"


def main() -> int:
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    url = f"sqlite:///{DB.as_posix()}"
    print(f"recompute_smt (vendored, all modes incl 5m) -> {DB} for 2026-05-21..2026-06-06 ...", flush=True)
    res = DL.recompute_smt(DL.SMT_INDEX_SYMBOLS, dt.date(2026, 5, 21), dt.date(2026, 6, 6),
                           smt_db_url=url, live_root=None)
    print(f"scan results: {len(res)} (detector x mode)", flush=True)
    c = sqlite3.connect(DB)
    cnt = collections.Counter()
    for (et,) in c.execute("select event_type from research_events where feature_name='smt_prev_candle_divergence'"):
        m = re.match(r"^(\d+m|\d+h)_", str(et))
        cnt[m.group(1) if m else "?"] += 1
    c.close()
    print(f"recent SMT by timeframe: {dict(sorted(cnt.items()))}")
    print(f"5m present: {'5m' in cnt}  (total smt_prev={sum(cnt.values())})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
