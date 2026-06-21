"""Build NQ orderflow (mbp_) features for the move-model dataset rows (the COMPASS).

Reuses the mbp_features engine (OFI / signed-vol / top-book imbalance / large-trade /
spread-intensity) on NQ MBP-1. One row per (date, ms) of dataset_ndx, raw features +
causal within-day z-scores. Objective-interaction features are SKIPPED (the move target
uses symmetric +-MOVE_ATR barriers, so objective distances are constant -> degenerate).

Heavy (reads the full NQ MBP-1 partition per day). Run once; the model merges the cache.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\build_mbp_features_ndx.py
Output: out/mbp_features_ndx.parquet
"""
from __future__ import annotations

import sys
import time
from datetime import date as Date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D
import mbp_features as M

OUT = Path(__file__).resolve().parent / "out"


def main() -> int:
    df = pd.read_parquet(OUT / "dataset_ndx.parquet", columns=["date", "ms"])
    days = sorted(df["date"].unique())
    all_rows, missing, t0 = [], [], time.time()
    for k, dstr in enumerate(days):
        day = Date.fromisoformat(dstr)
        arrs = M.load_day(day, root=C.MBP1_NQ)
        sub = df[df["date"] == dstr].sort_values("ms")
        assert sub["ms"].is_monotonic_increasing, "grid rows out of order — z causality broken"
        if arrs is None:
            missing.append(dstr)
            continue
        rows = []
        for ms in sub["ms"]:
            t_ns = D.et_ts(day, int(ms)).value
            f = M.features_at(arrs, t_ns)
            rows.append({"date": dstr, "ms": int(ms), **(f or {})})
        M.add_day_zscores(rows)
        all_rows.extend(rows)
        if k and k % 10 == 0:
            rate = (time.time() - t0) / k
            print(f"  {k}/{len(days)} days ({rate:.1f}s/day, ~{rate * (len(days) - k) / 60:.0f} min left)", flush=True)

    out = pd.DataFrame(all_rows)
    feat_cols = [c for c in out.columns if c.startswith("mbp_")]
    p = OUT / "mbp_features_ndx.parquet"
    out.to_parquet(p)
    print(f"\n{len(out)} rows x {len(feat_cols)} mbp features -> {p}")
    print(f"days done={out['date'].nunique()}  NQ MBP partitions missing={len(missing)} {missing[:5]}")
    print("NaN share per feature (top 5):")
    print(out[feat_cols].isna().mean().sort_values(ascending=False).head(5).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
