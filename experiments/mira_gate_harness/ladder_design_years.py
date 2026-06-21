"""Confirmation ladder on DESIGN YEARS ONLY (odd: 2015/17/19/21/23/25). PROTOCOL (frozen before
mining): mine freely here; the chosen 1-2 rules get ONE validation shot on even years, separately.
Base population = the universal combo (depth>8tk, wait>=5m, |R|<=5): 12yr meanR -0.049.

Layers: (a) cross-asset decision-bar PSP (LEGAL: decision bar is closed at decision; partner
closes same bar), (b) family, (c) entry hour, (d) deeper depth, (e) day-of-week.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/ladder_design_years.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
import smt_bench as SB  # noqa: E402

SYMS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
DESIGN = {2015, 2017, 2019, 2021, 2023, 2025}

df = pd.read_parquet(HERE / "runs" / "legal_bars_full.parquet")
df = df[(df["status"] == "entered") & (df["trail_2R"].abs() <= 5) & (df["fixed_3R"].abs() <= 5)].copy()
df = df[(df["depth_tk"] > 8) & (df["wait_s"] >= 300)].copy()
df["decision_ts_utc"] = pd.to_datetime(df["decision_ts_utc"], utc=True)
df["yr"] = df["decision_ts_utc"].dt.year
df = df[df["yr"].isin(DESIGN)].copy()
print(f"design-years combo population: {len(df)}")

# cross-asset decision-bar direction (bar ENDING at decision_ts -> open-label = decision_ts - 1m)
dirs = {}
for s in SYMS:
    b = SB.load_1m(s, "2015-01-01", "2026-06-09")
    dirs[s] = np.sign(b["close"] - b["open"])
D = pd.DataFrame(dirs)
bar_open = df["decision_ts_utc"] - pd.Timedelta(minutes=1)
aligned = D.reindex(bar_open)
mine = np.array([aligned.iloc[i][df["symbol"].iloc[i]] for i in range(len(df))])
want = np.where(df["side"].to_numpy() == "low", 1, -1)
others = np.stack([np.where([s != df["symbol"].iloc[i] for s in SYMS],
                            aligned.iloc[i][SYMS].to_numpy(float), np.nan)
                   for i in range(len(df))])
any_opp = np.nansum(others == -want[:, None], axis=1) > 0
any_with = np.nansum(others == want[:, None], axis=1) > 0
df["psp"] = np.select(
    [(mine == want) & any_opp, (mine == -want) & any_with, (mine == want) & ~any_opp],
    ["supportive_psp", "contrary_psp", "all_aligned"], default="other")


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):5d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():4.1f}%" if len(x) else "n=    0"


def ladder(title, col_or_masks):
    print(f"\n=== {title} (DESIGN YEARS ONLY) ===")
    for lbl, m in col_or_masks:
        print(f"  {lbl:24s} trail {st(df.loc[m, 'trail_2R'])}   fix3 {st(df.loc[m, 'fixed_3R'])}")


ladder("cross-asset decision-bar PSP", [(v, df["psp"] == v) for v in
                                        ("supportive_psp", "contrary_psp", "all_aligned", "other")])
ladder("family", [(f, df["level_family"] == f) for f in sorted(df["level_family"].unique())])
h = df["entry_hour_et"]
ladder("entry hour ET", [("9:30-10:30", (h >= 9.5) & (h < 10.5)), ("10:30-12", (h >= 10.5) & (h < 12)),
                         ("12-14:30", (h >= 12) & (h < 14.5)), ("14:30+", h >= 14.5), ("<9:30", h < 9.5)])
d = df["depth_tk"]
ladder("deeper depth", [("8-16", (d > 8) & (d <= 16)), ("16-32", (d > 16) & (d <= 32)), (">32", d > 32)])
ladder("day of week", [(str(x), df["entry_dow_et"] == x) for x in sorted(df["entry_dow_et"].unique())])
