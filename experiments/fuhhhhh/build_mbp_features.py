"""Build the mbp_ feature block for every (date, ms) row of dataset_v0 and cache it.

Heavy (reads ~13M MBP-1 events/day x 219 days); run once, model iterations reuse the
cache. Pass a single ISO date as argv[1] for a smoke test.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\build_mbp_features.py
Output: out/mbp_features_v0.parquet
"""

from __future__ import annotations

import sys
import time
from datetime import date as Date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_io as D
import mbp_features as M

OUT = Path(__file__).resolve().parent / "out"


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="v0", help="dataset tag to key rows from")
    ap.add_argument("--day", default=None, help="single ISO date smoke test")
    args = ap.parse_args()
    df = pd.read_parquet(OUT / f"dataset_{args.dataset}.parquet",
                         columns=["date", "ms", "geo_dist_up", "geo_dist_dn"])
    days = sorted(df["date"].unique())
    if args.day:
        days = [d for d in days if d == args.day]
    all_rows, missing, t0 = [], [], time.time()
    for k, dstr in enumerate(days):
        day = Date.fromisoformat(dstr)
        arrs = M.load_day(day)
        sub = df[df["date"] == dstr]
        assert sub["ms"].is_monotonic_increasing, "grid rows out of order — z-score causality broken"
        if arrs is None:
            missing.append(dstr)
            continue
        rows = []
        for ms, dup, ddn in zip(sub["ms"], sub["geo_dist_up"], sub["geo_dist_dn"]):
            t_ns = D.et_ts(day, int(ms)).value
            f = M.features_at(arrs, t_ns)
            rows.append({"date": dstr, "ms": int(ms), "_dup": dup, "_ddn": ddn, **(f or {})})
        M.add_day_zscores(rows)
        for r in rows:
            M.add_objective_interactions(r, r.pop("_dup"), r.pop("_ddn"))
        all_rows.extend(rows)
        if k and k % 10 == 0:
            rate = (time.time() - t0) / k
            print(f"  {k}/{len(days)} days  ({rate:.1f}s/day, ~{rate * (len(days) - k) / 60:.0f} min left)", flush=True)

    out = pd.DataFrame(all_rows)
    feat_cols = [c for c in out.columns if c.startswith("mbp_")]
    p = OUT / f"mbp_features_{args.dataset}.parquet"
    out.to_parquet(p)
    print(f"\n{len(out)} rows x {len(feat_cols)} mbp features -> {p}")
    print(f"days done={out['date'].nunique()}  MBP partitions missing={len(missing)} {missing[:5]}")
    print("NaN share per feature (top 5):")
    print(out[feat_cols].isna().mean().sort_values(ascending=False).head(5).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
