"""Is the ES model's 2025-26 era lift REGIME-CONDITIONAL SKILL or one lucky year?

Test: per-fold OOS IC across all ~30 folds (2016->2026) vs each fold's vol regime.
If IC rises with vol consistently across the DECADE (incl. 2018 Volmageddon/Q4,
2020 COVID, 2022 bear), the model has a conditional edge: deployable as
"trade only in regime". If 2025-26 stands alone, it's luck and dies here.

No-GX feature set (the ablation winner). Also: which block carries the era —
drop-one-block ablations evaluated on high-vol folds.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/diagnose_era.py
Artifact: report/era_diagnosis.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from model_wf import run_wf  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

BLOCKS = {
    "trend": lambda c: c.startswith(("ret_", "ma_", "dist_")),
    "vol": lambda c: c.startswith(("rv_", "park_", "rng_", "vol_z", "gap", "clv")),
    "cross": lambda c: c.startswith("x_"),
    "calendar": lambda c: c.startswith("dow_"),
}


def fold_table(
    pr: pd.Series, fr_: pd.Series, y: pd.Series, f: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    for fid in sorted(fr_[fr_ >= 0].unique()):
        m = (fr_ == fid) & pr.notna() & y.notna()
        if m.sum() < 30:
            continue
        rows.append(
            {
                "fold": int(fid),
                "start": pd.DatetimeIndex(f.index[m]).min().date(),
                "n": int(m.sum()),
                "ic": round(float(spearmanr(pr[m], y[m]).statistic), 3),
                "med_rv20_bps": round(float(f.loc[m, "rv20_bps"].median()), 0),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    f = pd.read_parquet(MODULE / "data" / "features_es.parquet")
    feats = [
        c
        for c in f.columns
        if not c.startswith(("y_", "gx_")) and c not in ("rv20_bps", "c_px")
    ]
    y = f["y_tbR"]

    pr, fr_ = run_wf(f[feats], y, shuffle_target=False)
    tab = fold_table(pr, fr_, y, f)
    rho = spearmanr(tab["ic"], tab["med_rv20_bps"])
    hi_vol = tab[tab["med_rv20_bps"] >= tab["med_rv20_bps"].quantile(0.7)]
    lo_vol = tab[tab["med_rv20_bps"] <= tab["med_rv20_bps"].quantile(0.3)]

    lines = [
        "# Era diagnosis — is the ES model's edge regime-conditional?",
        "",
        tab.to_string(index=False),
        "",
        f"spearman(fold IC, fold vol) = {rho.statistic:+.3f} (p={rho.pvalue:.3f}, n={len(tab)})",
        f"high-vol folds (top 30%): mean IC {hi_vol['ic'].mean():+.3f} (n={len(hi_vol)})",
        f"low-vol folds (bottom 30%): mean IC {lo_vol['ic'].mean():+.3f} (n={len(lo_vol)})",
        "",
    ]

    # which block carries the recent era: drop-one on the last 5 folds
    last_folds = sorted(tab["fold"])[-5:]
    m_era = fr_.isin(last_folds) & pr.notna() & y.notna()
    base_ic = float(spearmanr(pr[m_era], y[m_era]).statistic)
    lines += [
        f"recent-era (last 5 folds) pooled IC, full no-gx set: {base_ic:+.3f}",
        "drop-one-block on recent era:",
    ]
    for name, sel in BLOCKS.items():
        sub = [c for c in feats if not sel(c)]
        p2, f2 = run_wf(f[sub], y, shuffle_target=False)
        m2 = f2.isin(last_folds) & p2.notna() & y.notna()
        ic2 = float(spearmanr(p2[m2], y[m2]).statistic)
        lines.append(f"  -{name:9s}: {ic2:+.3f} (delta {ic2 - base_ic:+.3f})")

    report = "\n".join(lines)
    (MODULE / "report" / "era_diagnosis.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
