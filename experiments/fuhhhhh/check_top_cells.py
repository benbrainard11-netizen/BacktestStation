"""2A follow-up: apply the minimum-sample battery to the POSITIVE top-quantile cells.

The 2A gate ("stable positive selective cell?") turns on whether top5%/top2% EV cells
survive: per-fold spread, per-month spread, drop-best-days, delayed entry, gross.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\check_top_cells.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calib_lib as CL
import common as C
from model_v2a import MODELS, calibrate_folds

OUT = Path(__file__).resolve().parent / "out"
CAP = 1.5
METHOD = "isotonic"


def battery(t: pd.DataFrame, label: str) -> None:
    t = t.dropna(subset=["r"]).copy()
    edd, edu = t["entry"] - t["obj_dn"], t["obj_up"] - t["entry"]
    cost_r = np.where(t["side_long"], C.COST_PTS / edd, C.COST_PTS / edu)
    d1 = pd.Series(np.where(t["side_long"], t["r_long_net_d1"], t["r_short_net_d1"]),
                   index=t.index).dropna()
    dd = CL.drop_days(t)
    byfold = t.groupby("fold")["r"].agg(["mean", "count"])
    bymonth = t.groupby(t["date"].str.slice(0, 7))["r"].agg(["mean", "count"])
    daily = t.groupby("date")["r"].sum().sort_values()
    print(f"\n== {label} ==")
    print(f"  n={len(t)}  meanR={t['r'].mean():+.4f}  gross={(t['r'] + cost_r).mean():+.4f}  "
          f"win={(t['r'] > 0).mean():.0%}  days={t['date'].nunique()}")
    print(f"  folds+ {int((byfold['mean'] > 0).sum())}/{len(byfold)}  "
          f"months+ {int((bymonth['mean'] > 0).sum())}/{len(bymonth)}")
    print(f"  by fold: {[f'{m:+.3f}({int(n)})' for m, n in byfold.itertuples(index=False)]}")
    print(f"  by month: {[f'{i}:{m:+.2f}' for i, m in bymonth['mean'].items()]}")
    print(f"  drop_best5={dd['drop_best5']:+.4f}  drop_both5={dd['drop_both5']:+.4f}  "
          f"delayed_entry={d1.mean():+.4f} (n={len(d1)})")
    print(f"  top3 days share: {daily.iloc[-3:].sum() / max(t['r'].sum(), 1e-9):+.2f} "
          f"of total {t['r'].sum():+.1f}R" if t["r"].sum() > 0 else
          f"  total {t['r'].sum():+.1f}R (negative total)")


def main() -> int:
    df = pd.read_parquet(OUT / "dataset_v0.parquet").reset_index(drop=True)
    mbp = pd.read_parquet(OUT / "mbp_features_v0.parquet")
    df = df.merge(mbp, on=["date", "ms"], how="left")
    y = df["y"].to_numpy()
    feats = {p: [c for c in df.columns if c.startswith(p)] for p in ("geo_", "fut_", "mbp_")}
    for mname, prefixes in MODELS.items():
        cols = [c for p in prefixes for c in feats[p]]
        folds = CL.fold_predictions(df, cols, y)
        fc, te_pool, _ = calibrate_folds(folds, METHOD)
        r = CL.ev_frame(te_pool, CAP)
        r["r"] = CL.chosen_r(r)
        for q, tag in ((0.95, "top5%"), (0.98, "top2%")):
            thr = r.groupby("fold")["edge"].transform(lambda s: s.quantile(q))
            battery(r[r["edge"] >= thr], f"{mname} {METHOD}/cap{CAP} {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
