"""8-year robustness validation of the 5m NQ-vs-ES SMT SHORT edge (2018-2024).

Bar-level fills (MBP-1 doesn't reach this far; the tick check already proved bar~=tick for
this wide ±0.10ATR bracket). Pure cross-asset structure from NQ+ES 1m bars — no options needed.
Per-YEAR R so we see if the edge holds across COVID / 2022 bear / 2023-24 bull, or is recent-only.
Leaves 2025-H1 and the 2026-04+ holdout UNTOUCHED.

Exits: fix1R (±0.10ATR, 15min) and run-it (stop 0.10ATR / target 0.30ATR=3R, to EOD).

Run (background): backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\validate_history.py
Output: out/validate_history.parquet + printed per-year table
"""
from __future__ import annotations

import sys
from datetime import date as Date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D
import triggers as T
import objectives_labels as OL
from build_xasset_dir_ndx import resample_tf
from build_events import GRID_MS, SESSION_END_MS

OUTDIR = Path(__file__).resolve().parent / "out"
RTH_OPEN_MS = 9 * 3600_000 + 30 * 60_000
MOVE_ATR = 0.10


def nq_rth(root, day):
    df = D.load_bars_sym(root, day)
    if df is None:
        return None
    lo, hi = D.et_ts(day, RTH_OPEN_MS), D.et_ts(day, SESSION_END_MS)
    out = df[(df["et"] >= lo) & (df["et"] < hi)]
    return out if len(out) else None


def race_R(fwd_h, fwd_l, entry, up, dn):
    """short R, race down(target=dn) vs up(stop=up) on 1m highs/lows, conservative ambiguity."""
    hit_dn = np.argmax(fwd_l <= dn) if (fwd_l <= dn).any() else None
    hit_up = np.argmax(fwd_h >= up) if (fwd_h >= up).any() else None
    if hit_dn is None and hit_up is None:
        return None                                    # timeout handled by caller
    if hit_up is None:
        y, ce = 0, None
    elif hit_dn is None:
        y, ce = 1, None
    else:
        y, ce = (0, None) if hit_dn < hit_up else (1, None)  # down-first=target(win); tie->stop
        if hit_dn == hit_up:
            y = 1                                       # same bar -> stop (conservative)
    _, rs = OL.realized_r(y, entry, up, dn, ce, C.COST_PTS_NQ)
    return rs


def main() -> int:
    start = sys.argv[1] if len(sys.argv) > 1 else "2018-01-01"
    end = sys.argv[2] if len(sys.argv) > 2 else "2024-12-31"
    days = sorted(p.name.split("=")[1] for p in C.BARS_1M_NQ.glob("date=*"))
    days = [d for d in days if start <= d <= end]
    atr_tr, rows = D.AtrTracker(), []
    print(f"validating 5m-SMT-short over {len(days)} NQ days 2018-2024", flush=True)
    for i, dstr in enumerate(days):
        day = Date.fromisoformat(dstr)
        nq = nq_rth(C.BARS_1M_NQ, day)
        es = nq_rth(C.BARS_1M, day)
        if nq is None:
            continue
        atr = atr_tr.atr()
        if atr is not None and es is not None and len(nq) >= 90:
            nq5, es5 = resample_tf(nq, 5), resample_tf(es, 5)
            if len(nq5) >= 8:
                ctx = T.DayCtx.build(nq5, es5)
                et5 = pd.DatetimeIndex(nq5["et"]).asi8
                nqh = nq["high"].to_numpy(float); nql = nq["low"].to_numpy(float)
                nqo = nq["open"].to_numpy(float); nqet = pd.DatetimeIndex(nq["et"]).asi8
                for ms in GRID_MS:
                    if ms > C.TRIG_LAST_ENTRY_MS:
                        break
                    t = D.et_ts(day, ms).value
                    idx = int(np.searchsorted(et5, t, side="right")) - 1
                    if idx < C.SWING_K + 2 or T.smt_dir(ctx, idx) != -1:
                        continue
                    j = int(np.searchsorted(nqet, t, side="left"))
                    if j >= len(nqo):
                        continue
                    entry = nqo[j]
                    move = MOVE_ATR * atr
                    # fix1R: 15-min window
                    e15 = int(np.searchsorted(nqet, t + 15 * 60 * 10**9, side="right"))
                    rfix = race_R(nqh[j:e15], nql[j:e15], entry, entry + move, entry - move)
                    if rfix is None:
                        rfix = (entry - nqo[min(e15, len(nqo) - 1)]) / move - C.COST_PTS_NQ / move
                    # run-it: stop .10ATR, target .30ATR, to EOD
                    r3 = race_R(nqh[j:], nql[j:], entry, entry + move, entry - 0.30 * atr)
                    if r3 is None:
                        r3 = (entry - nqh[-1]) / move - C.COST_PTS_NQ / move  # approx timeout (last)
                    rows.append({"date": dstr, "yr": dstr[:4], "r_fix": rfix, "r_3R": r3})
        atr_tr.push_day(nq)
        if i and i % 200 == 0:
            print(f"  ...{i}/{len(days)} days, {len(rows)} short signals", flush=True)

    f = pd.DataFrame(rows)
    f.to_parquet(OUTDIR / "validate_history.parquet")
    print(f"\n{len(f)} 5m-SMT-short signals over {f.date.nunique()} days ({f.date.min()}..{f.date.max()})")
    print("\n### per-year (bar-level, net cost)")
    print(f"  {'yr':5s} {'n':>5s} {'r_fix':>8s} {'win%':>5s} {'r_3R':>8s}")
    for yr, g in f.groupby("yr"):
        print(f"  {yr:5s} {len(g):>5d} {g.r_fix.mean():>+8.4f} {(g.r_fix>0).mean()*100:>4.0f}% {g.r_3R.mean():>+8.4f}")
    print(f"\n  OVERALL n={len(f)} r_fix={f.r_fix.mean():+.4f} (win {(f.r_fix>0).mean()*100:.0f}%) "
          f"r_3R={f.r_3R.mean():+.4f}  yrs+_fix={int((f.groupby('yr').r_fix.mean()>0).sum())}/{f.yr.nunique()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
