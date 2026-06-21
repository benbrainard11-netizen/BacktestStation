"""Diagnostic: daily 5m-SMT event coverage across the train window (Feb 6 - May 20).
Confirms the repo meta.sqlite 5m scan has no gap days inside the window."""
import sqlite3

c = sqlite3.connect(r"C:\Users\benbr\BacktestStation\data\meta.sqlite")
rows = c.execute(
    """select substr(bar_end_utc,1,10) d, count(*) from research_events
       where feature_name in ('smt_prev_candle_divergence','smt_htf_reference_divergence')
       and event_type like '5m_%' and bar_end_utc >= '2026-02-01' and bar_end_utc < '2026-06-01'
       group by d order by d"""
).fetchall()
c.close()
days = {d: n for d, n in rows}
print(f"days with 5m SMT: {len(days)}  first={min(days)}  last={max(days)}")
import datetime as dt

d = dt.date(2026, 2, 6)
gaps = []
while d <= dt.date(2026, 5, 20):
    if d.weekday() < 5 and d.isoformat() not in days:
        gaps.append(d.isoformat())
    d += dt.timedelta(days=1)
print(f"weekday gap days in train window: {len(gaps)}")
for g in gaps:
    print(" ", g)
