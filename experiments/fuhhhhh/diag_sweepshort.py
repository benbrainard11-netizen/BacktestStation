"""Stability battery on the standout event cell: sweep-solo SHORT.

A sliced cell found after looking, so hold it to the same bar as everything else:
months+, drop-best/worst days, delayed entry, gross, day concentration.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
OUT = Path(__file__).resolve().parent / "out"


def battery(df: pd.DataFrame, label: str) -> None:
    t = df.dropna(subset=["r_signed"]).copy()
    cost_r = C.COST_PTS / t["stop_dist_pts"]
    bymonth = t.groupby(t["date"].str.slice(0, 7))["r_signed"].agg(["mean", "count"])
    daily = t.groupby("date")["r_signed"].sum().sort_values()
    best5, worst5 = list(daily.index[-5:]), list(daily.index[:5])
    d1 = t["r_signed_d1"].dropna()
    print(f"\n== {label} ==  n={len(t)}  meanR={t['r_signed'].mean():+.4f}  "
          f"gross={(t['r_signed'] + cost_r).mean():+.4f}  reach={t['reached'].mean():.0%}")
    print(f"  months+ {int((bymonth['mean'] > 0).sum())}/{len(bymonth)}: "
          f"{[f'{i[2:]}:{m:+.2f}' for i, m in bymonth['mean'].items()]}")
    print(f"  drop_best5={t[~t['date'].isin(best5)]['r_signed'].mean():+.4f}  "
          f"drop_worst5={t[~t['date'].isin(worst5)]['r_signed'].mean():+.4f}  "
          f"drop_both={t[~t['date'].isin(best5 + worst5)]['r_signed'].mean():+.4f}")
    print(f"  delayed_entry={d1.mean():+.4f} (n={len(d1)})  "
          f"top3-day share of total: {daily.iloc[-3:].sum() / max(t['r_signed'].sum(), 1e-9):+.0%}")


for tag in ("v3", "v3_s025"):
    df = pd.read_parquet(OUT / f"events_{tag}.parquet")
    ss = df[df["fired_sweep"] & (df["confluence"] == 1) & (df["dir"] == -1)]
    battery(ss, f"{tag} sweep-solo SHORT")
