"""Which peer carries the recent-era cross-asset signal? Drop-one-peer on ES era."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from model_wf import run_wf  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
ERA = pd.Timestamp("2024-07-01")


def era_ic(f, feats, y):
    pr, fr_ = run_wf(f[feats], y, shuffle_target=False)
    m = pr.notna() & y.notna() & (pd.DatetimeIndex(f.index) >= ERA)
    return float(spearmanr(pr[m], y[m]).statistic)


def main() -> int:
    f = pd.read_parquet(MODULE / "data" / "features_es.parquet")
    base_feats = [
        c
        for c in f.columns
        if not c.startswith(("y_", "gx_")) and c not in ("rv20_bps", "c_px")
    ]
    y = f["y_tbR"]
    base = era_ic(f, base_feats, y)
    print(f"ES era IC, full no-gx set: {base:+.3f}")
    for peer in ("nq", "gc", "6e", "zn"):
        sub = [c for c in base_feats if not c.startswith(f"x_{peer}_")]
        ic = era_ic(f, sub, y)
        print(f"  -{peer}: {ic:+.3f} (delta {ic - base:+.3f})")
    only_x = [c for c in base_feats if c.startswith("x_")]
    print(f"  cross-block ONLY ({len(only_x)} feats): {era_ic(f, only_x, y):+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
