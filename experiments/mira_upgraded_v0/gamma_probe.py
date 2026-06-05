"""Gamma-signal probe (SPX 2025): does dealer gamma REGIME (pos_gamma sign) or WALL PROXIMITY move the ES reclaim
edge? A free de-risk before buying full multi-asset GEX. Reads events_es_tf.parquet + gamma_walls_2025.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import boot, seq_r  # noqa: E402

EV = Path(__file__).resolve().parent / "out" / "events_es_tf.parquet"
GAMMA = RT / "experiments" / "options_signals_v0" / "out" / "gamma_walls_2025.parquet"
TARGET = 3.0


def main() -> int:
    df = pd.read_parquet(EV)
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].copy()
    gw = pd.read_parquet(GAMMA)
    gw.index = pd.to_datetime(gw.index).date
    for c in ("spot", "wall", "pos_gamma"):
        df[c] = df["day"].map(gw[c].to_dict())
    df = df[df["pos_gamma"].notna()].reset_index(drop=True)
    df["r"] = seq_r(df, TARGET)
    print(f"ES reclaim events in the gamma window (2025): n={len(df)}")
    print(f"pos_gamma: min {df['pos_gamma'].min():.3g}  max {df['pos_gamma'].max():.3g}  "
          f"median {df['pos_gamma'].median():.3g}  frac>0 {(df['pos_gamma'] > 0).mean():.2f}")
    bm, bl, bh = boot(df["r"].to_numpy(), df["day"].to_numpy())
    print(f"\nbaseline reclaim R (2025 gamma window): {bm:+.2f} [{bl:+.2f},{bh:+.2f}]\n")

    print("by GAMMA REGIME (pos_gamma sign):")
    for name, m in [("long-gamma (>0)", df["pos_gamma"] > 0), ("short-gamma (<=0)", df["pos_gamma"] <= 0)]:
        sub = df[m.to_numpy()]
        if len(sub) < 20:
            print(f"  {name:18} n<20 ({len(sub)})")
            continue
        mm, ll, hh = boot(sub["r"].to_numpy(), sub["day"].to_numpy())
        print(f"  {name:18} {mm:+.2f} [{ll:+.2f},{hh:+.2f}]  n{len(sub)}")

    df["wall_dist"] = (df["level_price"] - df["wall"]).abs()
    df["prox"] = pd.qcut(df["wall_dist"].rank(method="first"), 3, labels=["near", "mid", "far"])
    print("\nby WALL PROXIMITY (|level - wall|):")
    for lab in ("near", "mid", "far"):
        sub = df[df["prox"] == lab]
        mm, ll, hh = boot(sub["r"].to_numpy(), sub["day"].to_numpy())
        print(f"  {lab:5} {mm:+.2f} [{ll:+.2f},{hh:+.2f}]  n{len(sub)}")
    print("\nREAD: a regime or proximity split with clearly different R = gamma carries signal -> worth the full-GEX buy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
