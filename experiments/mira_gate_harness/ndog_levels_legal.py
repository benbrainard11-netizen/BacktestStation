"""NON-HIGH/LOW barrier levels (Ben's ICT set): NDOG (New Day Opening Gap), NWOG (New Week Opening
Gap), and prior-day CLOSE. Each gap contributes 3 levels — gap HIGH, gap LOW, gap MID (50% / CE).
All legal (close + open known by the session open), injected into the reclaim engine on the indices.

NDOG = gap between prior RTH close and today's RTH open. NWOG = prior week's last RTH close to this
week's first RTH open. Side set by level-vs-today's-open (causal, like daily_gap).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/ndog_levels_legal.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend"))
import legal_reclaim_bars as LB  # noqa: E402

SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0"]
START, END = dt.date(2025, 5, 1), dt.date(2026, 6, 9)
_ORIG = LB.day_levels
FAMS = ["ndog", "nwog", "prior_close"]


def _gap_levels(fam, prior_close, today_open, topen, rth_ns):
    """3 levels for a close->open gap: high / low / mid, sided by position vs today's open."""
    out = []
    gi, glo, gm = max(prior_close, today_open), min(prior_close, today_open), 0.5 * (prior_close + today_open)
    for px, lt in ((gi, "hi"), (glo, "lo"), (gm, "mid")):
        side = "low" if px <= topen else "high"  # below today's open => support
        out.append(dict(level_family=fam, level_type=f"{fam}_{lt}", side=side,
                        level_price=float(px), known_ns=rth_ns, search_ns=rth_ns))
    return out


def patched_day_levels(b, daily, day, tick):
    out = _ORIG(b, daily, day, tick)
    days = daily.index
    if day not in days:
        return out
    pos = days.get_loc(day)
    rth_ns = LB.et_ns(day, LB.RTH_START)
    topen = float(daily.loc[day, "open"])
    if pos > 0:  # NDOG: prior RTH close -> today's open
        pc = float(daily.iloc[pos - 1]["close"])
        out += _gap_levels("ndog", pc, topen, topen, rth_ns)
        out.append(dict(level_family="prior_close", level_type="pclose",
                        side=("low" if pc <= topen else "high"), level_price=pc,
                        known_ns=rth_ns, search_ns=rth_ns))
    # NWOG: prior week's last close -> this week's first open
    wk_start = day - dt.timedelta(days=day.weekday())
    this_wk = [d for d in days if wk_start <= d <= day]
    prev_wk = [d for d in days if d < wk_start]
    if this_wk and prev_wk and this_wk[0] == day:  # only on the week's first session (when NWOG forms)
        pwc = float(daily.loc[prev_wk[-1], "close"])
        out += _gap_levels("nwog", pwc, topen, topen, rth_ns)
    return out


LB.day_levels = patched_day_levels


def main() -> int:
    parts = []
    for sym in SYMBOLS:
        res = LB.run_symbol_year(sym, START, END)
        if len(res):
            res = res[res["level_family"].isin(FAMS)].copy()
            parts.append(res)
        print(f"  {sym}: {len(res) if len(res) else 0} ndog/nwog/pclose attempts", flush=True)
    df = pd.concat(parts, ignore_index=True)
    out = LB.RUNS / "ndog_levels_full.parquet"
    df.to_parquet(out, index=False)
    ent = df[df["status"] == "entered"]
    print(f"\nwrote {out}: {len(df)} attempts, {len(ent)} entered")
    for fam, g in ent.groupby("level_family"):
        x = pd.to_numeric(g["trail_2R"], errors="coerce").dropna()
        print(f"  {fam:12s} entered={len(g):4d}  raw meanR={x.mean():+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
