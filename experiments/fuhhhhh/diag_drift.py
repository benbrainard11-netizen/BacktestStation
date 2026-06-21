"""2B drift autopsy: are the positive v2 cells model edge or just long-drift?

Checks, per v2 dataset: (1) uninformed baselines — always-long / always-short mean
net R over ALL rows and over timeout rows only; (2) the candidate's selected trades:
side split, per-side mean R, and the same-rows always-long counterfactual.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\diag_drift.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calib_lib as CL
from model_v2a import calibrate_folds, run_cell
from model_v2b import METHOD, CAP, load_v2

OUT = Path(__file__).resolve().parent / "out"


def main() -> int:
    for tag in ("v2_c006", "v2_c004"):
        df = load_v2(tag)
        y = df["y"].to_numpy()
        to = df[df["y"] == 2]
        print(f"\n=== {tag} ===")
        print(f"ALL rows: always-long {df['r_long_net'].mean():+.4f}  "
              f"always-short {df['r_short_net'].mean():+.4f}  (n={len(df)})")
        print(f"timeout rows: always-long {to['r_long_net'].mean():+.4f}  "
              f"always-short {to['r_short_net'].mean():+.4f}  (n={len(to)})")
        bym = df.groupby(df["date"].str.slice(0, 7))["r_long_net"].mean()
        print(f"always-long by month: {[f'{i}:{v:+.3f}' for i, v in bym.items()]}")

        feats = {p: [c for c in df.columns if c.startswith(p)] for p in ("geo_", "fut_", "mbp_")}
        cols = [c for p in ("geo_", "fut_", "mbp_") for c in feats[p]]
        fc, te_pool, _ = calibrate_folds(CL.fold_predictions(df, cols, y), METHOD)
        trades, _ = run_cell(fc, CAP)
        t = trades.dropna(subset=["r"])
        longs, shorts = t[t["side_long"]], t[~t["side_long"]]
        print(f"candidate selected trades: n={len(t)}  long {len(longs)/len(t):.0%}  "
              f"meanR {t['r'].mean():+.4f}")
        print(f"  longs meanR {longs['r'].mean():+.4f} (n={len(longs)})   "
              f"shorts meanR {shorts['r'].mean():+.4f} (n={len(shorts)})")
        print(f"  same-rows always-long counterfactual: {t['r_long_net'].mean():+.4f}")
        print(f"  model-vs-counterfactual delta: {t['r'].mean() - t['r_long_net'].mean():+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
