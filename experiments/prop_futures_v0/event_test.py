"""event_test — scheduled-event (EIA) day-flat continuation vs reversion on energy.

The last untested day-flat family. EIA Petroleum Status = Wed 10:30 ET (CL); EIA Nat-Gas Storage =
Thu 10:30 ET (NG). After the 10:30 release REACTION (10:30->10:45), does the move CONTINUE or REVERT
into the close (15:55)? Day-flat, automatable. Calendar = modal weekday proxy (holiday weeks shift
+1 day -> noise, not bias); validated by the 10:30 vol spike on the event weekday vs others.

  python event_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orb_engine import build_dataset, get_spec  # noqa: E402

START, DESIGN_END, HOLD_END = "2016-01-01", "2024-12-31", "2025-12-31"
T_REL, T_REACT, T_CLOSE = 630, 645, 955  # 10:30, 10:45, 15:55 ET (minute-of-day)
EVENT_WD = {"CL.c.0": 2, "NG.c.0": 3}     # Wed=2 (petroleum), Thu=3 (nat-gas storage)


def at(day, mod):
    r = day[day["mod"] == mod]
    return float(r["close"].iloc[0]) if len(r) else np.nan


def run(sym):
    spec = get_spec(sym)
    cost_bps = 2 * spec.tick_size / 75.0 * 1e4 if sym == "CL.c.0" else 2 * spec.tick_size / 3.5 * 1e4
    df = build_dataset(sym, START, HOLD_END)
    df = df[(df["mod"] >= 570) & (df["mod"] <= T_CLOSE)]
    rows = []
    for date, day in df.groupby("date_et"):
        wd = pd.Timestamp(date).weekday()
        p_rel, p_react, p_close = at(day, T_REL), at(day, T_REACT), at(day, T_CLOSE)
        if np.isnan(p_rel) or np.isnan(p_react) or np.isnan(p_close):
            continue
        reaction = p_react / p_rel - 1
        outcome = p_close / p_react - 1
        rows.append({"date": int(pd.Timestamp(date).strftime("%Y%m%d")), "wd": wd,
                     "event": int(wd == EVENT_WD[sym]), "reaction": reaction, "outcome": outcome})
    t = pd.DataFrame(rows)
    # validation: is the 10:30 reaction bigger on the event weekday?
    ev_react = t[t.event == 1]["reaction"].abs().mean()
    ot_react = t[t.event == 0]["reaction"].abs().mean()
    print(f"\n== {sym} EIA event-day continuation/reversion (cost~{cost_bps:.1f}bps RT) ==")
    print(f"  10:30 reaction |move|: event-wd {ev_react*1e4:.1f}bps vs other {ot_react*1e4:.1f}bps "
          f"({'VALID spike' if ev_react > 1.15*ot_react else 'weak/none'})")
    de = int(DESIGN_END.replace("-", ""))
    for split, lo, hi in [("design", 0, de), ("holdout", de + 1, 99999999)]:
        ev = t[(t.event == 1) & (t.date >= lo) & (t.date <= hi)]
        if len(ev) < 20:
            print(f"  {split}: n={len(ev)} too few"); continue
        cont = np.sign(ev.reaction) * ev.outcome * 1e4 - cost_bps   # continuation, net bps
        rev = -np.sign(ev.reaction) * ev.outcome * 1e4 - cost_bps   # reversion, net bps
        print(f"  {split:7s} n={len(ev)} | CONTINUE net {cont.mean():+.1f}bps (win {(cont>0).mean():.2f}) "
              f"| REVERT net {rev.mean():+.1f}bps (win {(rev>0).mean():.2f})")


if __name__ == "__main__":
    for s in (sys.argv[1:] or ["CL.c.0", "NG.c.0"]):
        run(s)
