"""Relative-structure (xs_) block evaluation — does SMT-as-features beat raw returns?

Three runs on ES (gx/ox excluded — already judged): control, WITHOUT xs (the current
champion set), WITH xs. Value-add reported full-sample and on the post-2024-07 era
(where the cross-asset signal lives). Then the same WITH/WITHOUT on NQ as the
replication check.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/ablate_xs.py
Artifact: report/xs_ablation.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from features_index import build  # noqa: E402
from model_wf import fold_ic, run_wf  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

ERA = pd.Timestamp("2024-07-01")


def eval_sets(sym: str, run_control: bool) -> dict:
    tag = sym.split(".")[0].lower()
    f = pd.read_parquet(MODULE / "data" / f"features_{tag}.parquet")
    y = f["y_tbR"]
    keep = [
        c
        for c in f.columns
        if not c.startswith(("y_", "gx_", "ox_")) and c not in ("rv20_bps", "c_px")
    ]
    with_xs = keep
    without_xs = [c for c in keep if not c.startswith("xs_")]
    out = {"symbol": sym}
    if run_control:
        pc, fc = run_wf(f[with_xs], y, shuffle_target=True)
        out["control"] = round(fold_ic(pc, y, fc, pc.notna() & y.notna()), 3)
        if abs(out["control"]) > 0.05:
            raise RuntimeError(f"CONTROL SCORED {out['control']}")
    era_mask = pd.Series(pd.DatetimeIndex(f.index) >= ERA, index=f.index)
    for nm, feats in [("without", without_xs), ("with", with_xs)]:
        pr, fr_ = run_wf(f[feats], y, shuffle_target=False)
        m = pr.notna() & y.notna()
        me = m & era_mask
        out[f"{nm}_ic"] = round(fold_ic(pr, y, fr_, m), 3)
        out[f"{nm}_era"] = round(float(spearmanr(pr[me], y[me]).statistic), 3)
    out["era_value_add"] = round(out["with_era"] - out["without_era"], 3)
    print(out)
    return out


def main() -> int:
    build("ES.c.0")  # rebuild matrices with the xs_ block
    build("NQ.c.0")
    rows = [
        eval_sets("ES.c.0", run_control=True),
        eval_sets("NQ.c.0", run_control=False),
    ]
    tab = pd.DataFrame(rows)
    (MODULE / "report" / "xs_ablation.md").write_text(
        "# Relative-structure (SMT-as-features) ablation\n\n"
        + tab.to_string(index=False),
        encoding="utf-8",
    )
    print("\n" + tab.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
