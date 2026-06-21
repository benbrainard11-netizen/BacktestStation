"""June 8-10 SMT re-scan WITH 5m — standalone process, vendored detector ONLY.

GOTCHA (hit 2026-06-10 by prep_june_oos.py): importing anything from the repo backend's `app`
package BEFORE detect_live caches the no-5m `app` in sys.modules, and recompute_smt then scans
without 5m even though detect.py put the vendor on sys.path. This script therefore imports ONLY
live_engine/engine (detect's own import pulls the vendored `app`), mirroring fix_holdout_5m.py.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/june_smt_scan.py
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

DB = Path(__file__).resolve().parent / "data" / "june_smt5m.sqlite"


def main() -> int:
    if DB.exists():
        DB.unlink()
    url = f"sqlite:///{DB.as_posix()}"
    print(f"recompute_smt (vendored, incl 5m) -> {DB} for 2026-06-08..2026-06-10 ...", flush=True)
    res = DL.recompute_smt(DL.SMT_INDEX_SYMBOLS, dt.date(2026, 6, 8), dt.date(2026, 6, 10),
                           smt_db_url=url, live_root=None)
    print(f"scan results: {len(res)} (detector x mode)", flush=True)
    c = sqlite3.connect(DB)
    cnt = collections.Counter()
    for (et,) in c.execute("select event_type from research_events where feature_name='smt_prev_candle_divergence'"):
        m = re.match(r"^(\d+m|\d+h)_", str(et))
        cnt[m.group(1) if m else "?"] += 1
    c.close()
    print(f"June SMT by timeframe: {dict(sorted(cnt.items()))}")
    ok = "5m" in cnt
    print(f"5m present: {ok}  (total smt_prev={sum(cnt.values())})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
