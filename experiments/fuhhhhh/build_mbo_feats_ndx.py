"""Build causal MBO order-flow features for dataset_ndx rows on MBO-covered dev days.

Uses the mbo_features_ndx engine (leak-free: all windows [t-W, t)). Only computes for
dates where an NQ clean-MBO partition exists (2026-01..2026-03 within the dev window).

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\build_mbo_feats_ndx.py
Output: out/mbo_feats_ndx.parquet
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
import mbo_features_ndx as MBO

OUT = Path(__file__).resolve().parent / "out"


def main() -> int:
    df = pd.read_parquet(OUT / "dataset_ndx.parquet", columns=["date", "ms"])
    days = [d for d in sorted(df["date"].unique())
            if (C.MBO_CLEAN_NQ / f"trading_day={d}" / "part-000.parquet").exists()]
    print(f"{len(days)} MBO-covered dev days ({days[0]}..{days[-1]})", flush=True)
    all_rows, t0 = [], time.time()
    for k, dstr in enumerate(days):
        day = Date.fromisoformat(dstr)
        a = MBO.load_day(day)
        sub = df[df["date"] == dstr].sort_values("ms")
        if a is None:
            continue
        rows = []
        for ms in sub["ms"]:
            f = MBO.features_at(a, D.et_ts(day, int(ms)).value)
            rows.append({"date": dstr, "ms": int(ms), **(f or {})})
        MBO.add_day_zscores(rows)
        all_rows.extend(rows)
        if k and k % 10 == 0:
            r = (time.time() - t0) / k
            print(f"  {k}/{len(days)} ({r:.1f}s/day, ~{r*(len(days)-k)/60:.0f} min left)", flush=True)

    out = pd.DataFrame(all_rows)
    cols = [c for c in out.columns if c.startswith("mbo_")]
    p = OUT / "mbo_feats_ndx.parquet"
    out.to_parquet(p)
    print(f"\n{len(out)} rows x {len(cols)} MBO feats / {out['date'].nunique()} days -> {p}")
    print("NaN share (top 5):")
    print(out[cols].isna().mean().sort_values(ascending=False).head(5).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
