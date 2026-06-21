"""rv_signal_sheet — the RV model as a DISCRETIONARY decision-support tool.

The systematic RV strat is cost-killed, but the reversion SIGNAL is real. A discretionary prop trader
uses it differently: watch which cointegrated spreads are stretched, and act only on the BIG
dislocations (where even mechanical clears gross), timing/sizing by hand. This shows the 'edge profile'
by how stretched the spread was at entry (|z| bucket) -> so you see where the discretionary sweet spot
is, and how much your timing/selectivity needs to add to clear the 2-leg cost.

  python rv_signal_sheet.py CL.c.0 BZ.c.0
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rv_backtest as R  # noqa: E402

BUCKETS = [(2.0, 2.5), (2.5, 3.0), (3.0, 3.5), (3.5, 4.0), (4.0, 99)]


def sheet(a, b):
    m, sa, sb = R.prepare(a, b)
    t = R.simulate(m, sa, sb, entry=2.0, exit_thr=0.5)
    de = int(R.DESIGN_END.replace("-", ""))
    cost = float(t["cost"].median())
    print(f"\n=== {a}-{b} RV signal sheet (hold to revert |z|<0.5 or close; 2-leg cost ~${cost:.0f}/RT) ===")
    print(f"  {'|z| at entry':>13} {'n/yr':>6} {'P(win)':>7} {'gross$':>8} {'net$':>8} {'hold':>6}  (design | holdout net$)")
    for lo, hi in BUCKETS:
        s = t[(t.entry_z >= lo) & (t.entry_z < hi)]
        if len(s) < 5:
            continue
        d = s[s.date <= de]; h = s[s.date > de]
        yrs = max(1, (t.date.max() // 10000) - (t.date.min() // 10000) + 1)
        dn = d.pnl.mean() if len(d) >= 5 else float("nan")
        hn = h.pnl.mean() if len(h) >= 5 else float("nan")
        print(f"  {lo:>5.1f}-{hi:<5.1f} {len(s)//yrs:>6} {(s.pnl>0).mean():>7.2f} {s.gross.mean():>+8.1f} "
              f"{s.pnl.mean():>+8.1f} {s.held.mean():>5.0f}m   ({dn:+.1f} | {hn:+.1f})")
    print(f"  READ: gross$ rises with |z| (bigger dislocation reverts more); net = gross - ${cost:.0f} cost."
          f" Discretion must add the gap where net<0. Sweet spot = where gross clears cost on BOTH cols.")


if __name__ == "__main__":
    pairs = [("CL.c.0", "BZ.c.0"), ("ZN.c.0", "ZF.c.0")] if len(sys.argv) < 3 else [(sys.argv[1], sys.argv[2])]
    for a, b in pairs:
        sheet(a, b)
