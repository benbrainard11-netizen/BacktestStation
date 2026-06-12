"""Attribution control: same ES model WITHOUT the gx_ block — does gex-era IC survive?

If IC(gex era) stays ~+0.13 without the options features, the era (regime) carries it.
If it collapses toward the pre-gex baseline, the GEX block carries it.
Also: gex-era decile trades with/without the block.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/ablate_gex.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from model_wf import fold_ic, run_wf  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def gex_era_stats(pr, fr_, y, f, label):
    mr = pr.notna() & y.notna()
    gex_mask = mr & f["gx_width"].notna()
    ic_gex = fold_ic(pr, y, fr_, gex_mask)
    ic_all = fold_ic(pr, y, fr_, mr)
    # gex-era decile net (gross R, costless — comparison only)
    rows = []
    for fid in sorted(fr_[gex_mask].unique()):
        m = gex_mask & (fr_ == fid)
        if m.sum() < 25:
            continue
        pb = pr[m]
        hi, lo = pb.quantile(0.9), pb.quantile(0.1)
        rows += [y.loc[d] for d, p_ in pb.items() if p_ >= hi]
        rows += [-y.loc[d] for d, p_ in pb.items() if p_ <= lo]
    mean_r = float(pd.Series(rows).mean()) if rows else float("nan")
    print(
        f"{label}: IC_all {ic_all:+.3f} | IC_gex_era {ic_gex:+.3f} | "
        f"gex-era decile gross R {mean_r:+.3f} (n={len(rows)})"
    )
    return ic_gex


def main() -> int:
    f = pd.read_parquet(MODULE / "data" / "features_es.parquet")
    feats_all = [
        c for c in f.columns if not c.startswith("y_") and c not in ("rv20_bps", "c_px")
    ]
    feats_nogx = [c for c in feats_all if not c.startswith("gx_")]
    y = f["y_tbR"]

    pr1, fr1 = run_wf(f[feats_all], y, shuffle_target=False)
    ic_with = gex_era_stats(pr1, fr1, y, f, "WITH gx block   ")
    pr2, fr2 = run_wf(f[feats_nogx], y, shuffle_target=False)
    ic_without = gex_era_stats(pr2, fr2, y, f, "WITHOUT gx block")
    print(
        f"\nattribution delta (with - without) on gex era: {ic_with - ic_without:+.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
