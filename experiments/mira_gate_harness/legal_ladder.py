"""Conditioning ladder on the legal-reclaim Jan DESIGN SET (mine freely here; chosen conditions
get ONE validation shot on a different window later — never promote off this table alone).
Floor: unconditional -0.776R/338. Which legal-at-entry conditions lift it?

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/legal_ladder.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

P = Path(r"C:\Users\benbr\BacktestStation\experiments\mira_gate_harness\runs\legal_reclaim_jan.parquet")
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25}

df = pd.read_parquet(P)
df = df[df["status"] == "entered"].copy()
df["tick"] = df["symbol"].map(TICK)
df["depth_tk"] = df["risk_pts"] / df["tick"] - 2  # risk = adverse distance + 2-tick buffer
df["entry_ts_utc"] = pd.to_datetime(df["entry_ts_utc"], utc=True)
et = df["entry_ts_utc"].dt.tz_convert("America/New_York")
df["hr"] = et.dt.hour + et.dt.minute / 60.0


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=  0"


def ladder(title, series, buckets):
    print(f"\n=== {title} ===")
    for lbl, mask in buckets:
        r = df.loc[mask]
        print(f"  {lbl:22s} trail {st(r['trail_2R'])}   fix3 {st(r['fixed_3R'])}")


print(f"entered={len(df)}  pooled trail {st(df['trail_2R'])}")

d = df["depth_tk"]
ladder("SWEEP DEPTH at entry (ticks)", d, [
    ("<=4", d <= 4), ("5-8", (d > 4) & (d <= 8)), ("9-16", (d > 8) & (d <= 16)),
    ("17-32", (d > 16) & (d <= 32)), (">32", d > 32)])

w = df["wait_s"]
ladder("PATIENCE: touch->entry", w, [
    ("<60s", w < 60), ("1-5m", (w >= 60) & (w < 300)), ("5-15m", (w >= 300) & (w < 900)),
    ("15-60m", w >= 900)])

h = df["hr"]
ladder("ENTRY TIME (ET)", h, [
    ("pre-9:30", h < 9.5), ("9:30-10:30", (h >= 9.5) & (h < 10.5)),
    ("10:30-12", (h >= 10.5) & (h < 12)), ("12-14:30", (h >= 12) & (h < 14.5)), ("14:30+", h >= 14.5)])

ladder("SIDE", df["side"], [("long (low sweep)", df["side"] == "low"), ("short (high sweep)", df["side"] == "high")])

best = (df["depth_tk"] > 8) & (df["wait_s"] >= 300)
ladder("COMBO: depth>8tk AND wait>=5m", best, [("combo", best), ("rest", ~best)])
