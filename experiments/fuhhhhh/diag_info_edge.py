"""Diagnostic (reads existing v1 OOS preds, no new model): information-vs-geometry.

Under drift-free geometry P(up first) = dd/(du+dd). A model only adds value through
DEVIATION from that prior. Bucket OOS rows by |p_dir - prior| decile, trade the
deviation's direction, report realized net R per decile. If high-deviation buckets
are positive, the model has information and the EV layer (not the features) is the
failing component of Iteration 1.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\diag_info_edge.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT = Path(__file__).resolve().parent / "out"


def info_table(res: pd.DataFrame) -> pd.DataFrame:
    r = res.copy()
    du, dd = r["obj_up"] - r["price"], r["price"] - r["obj_dn"]
    r["prior"] = dd / (du + dd)
    r["p_dir"] = r["p_up"] / (r["p_up"] + r["p_dn"])
    r["dev"] = r["p_dir"] - r["prior"]
    r["r"] = np.where(r["dev"] > 0, r["r_long_net"], r["r_short_net"])
    r = r.dropna(subset=["r"])
    r["decile"] = r.groupby("fold")["dev"].transform(
        lambda s: pd.qcut(s.abs().rank(method="first"), 10, labels=False))
    tab = r.groupby("decile").agg(mean_r=("r", "mean"), n=("r", "size"),
                                  abs_dev=("dev", lambda s: s.abs().mean()))
    return tab


def main() -> int:
    res = pd.read_parquet(OUT / "oos_preds_v1.parquet")
    for name in ("B futures+geo [champion]", "D fut+geo+mbp [candidate]"):
        sub = res[res["ablation"] == name]
        tab = info_table(sub)
        top = tab.iloc[-2:]
        print(f"\n== {name} — |p_dir − geometry prior| deciles ==")
        print(tab.round(4).to_string())
        print(f"top-2 deciles pooled: meanR {float((top['mean_r'] * top['n']).sum() / top['n'].sum()):+.4f} "
              f"(n={int(top['n'].sum())})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
