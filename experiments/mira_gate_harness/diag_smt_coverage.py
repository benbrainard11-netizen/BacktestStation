"""Diagnostic: SMT event coverage by month x timeframe across candidate SMT DBs.
Decides whether the train-window (Feb6-May20) rebuild can use meta.sqlite or needs a 5m re-scan."""
import collections
import re
import sqlite3
from pathlib import Path

DBS = {
    "repo meta.sqlite": Path(r"C:\Users\benbr\BacktestStation\data\meta.sqlite"),
    "holdout_smt5m": Path(r"C:\Users\benbr\BacktestStation\experiments\mira_gate_harness\data\holdout_smt5m.sqlite"),
    "live_engine meta (detect default)": Path(r"C:\Users\benbr\BacktestStation\live_engine\data\meta.sqlite"),
}

for name, db in DBS.items():
    print(f"\n=== {name} -> {db}")
    if not db.exists():
        print("  MISSING (this is what _load_smt_events silently turns into 0 rows)")
        continue
    c = sqlite3.connect(db)
    q = """select substr(bar_end_utc,1,7) mo, event_type from research_events
           where feature_name in ('smt_prev_candle_divergence','smt_htf_reference_divergence')
           and bar_end_utc >= '2026-01-01'"""
    cnt = collections.defaultdict(collections.Counter)
    try:
        for mo, et in c.execute(q):
            m = re.match(r"^(\d+m|\d+h)_", str(et))
            cnt[mo][m.group(1) if m else "?"] += 1
    except sqlite3.OperationalError as e:
        print(f"  query failed: {e}")
        c.close()
        continue
    c.close()
    if not cnt:
        print("  no SMT rows >= 2026-01-01")
    for mo in sorted(cnt):
        total = sum(cnt[mo].values())
        has5m = "5m" in cnt[mo]
        print(f"  {mo} total={total:6d} 5m={'YES' if has5m else 'NO ':3s} {dict(sorted(cnt[mo].items()))}")
