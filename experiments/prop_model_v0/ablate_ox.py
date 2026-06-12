"""Options-SURFACE block evaluation on ES — same protocol that judged the walls.

Runs the ES model WITH and WITHOUT the ox_ block (gx_ excluded in both — already
judged); reports surface-era subset IC for each plus the attribution delta, and the
control on the WITH set. The surface block earns a place only if the delta is
positive on its own era — the exact bar the GEX walls failed.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/ablate_ox.py
Artifact: report/ox_ablation.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from model_wf import fold_ic, run_wf  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def era_stats(pr, fr_, y, era_mask, label):
    m_all = pr.notna() & y.notna()
    m_era = m_all & era_mask
    ic_all = fold_ic(pr, y, fr_, m_all)
    ic_era = (
        float(spearmanr(pr[m_era], y[m_era]).statistic)
        if m_era.sum() > 50
        else float("nan")
    )
    print(
        f"{label}: IC_all {ic_all:+.3f} | IC_surface_era {ic_era:+.3f} (n={int(m_era.sum())})"
    )
    return ic_era


def main() -> int:
    f = pd.read_parquet(MODULE / "data" / "features_es.parquet")
    if "ox_atm_iv30" not in f.columns:
        raise RuntimeError(
            "surface block missing — run options_surface.py + features_index.py first"
        )
    y = f["y_tbR"]
    era = f["ox_atm_iv30"].notna()
    print(
        f"surface era: {int(era.sum())} days "
        f"({f.index[era].min().date()} -> {f.index[era].max().date()})"
    )
    feats_with = [
        c
        for c in f.columns
        if not c.startswith(("y_", "gx_")) and c not in ("rv20_bps", "c_px")
    ]
    feats_without = [c for c in feats_with if not c.startswith("ox_")]

    pc, fc = run_wf(f[feats_with], y, shuffle_target=True)
    ic_c = fold_ic(pc, y, fc, pc.notna() & y.notna())
    print(f"control (WITH set): {ic_c:+.3f}")
    if abs(ic_c) > 0.05:
        raise RuntimeError(f"CONTROL SCORED ({ic_c:+.3f})")

    pr1, fr1 = run_wf(f[feats_with], y, shuffle_target=False)
    ic_w = era_stats(pr1, fr1, y, era, "WITH ox surface   ")
    pr2, fr2 = run_wf(f[feats_without], y, shuffle_target=False)
    ic_wo = era_stats(pr2, fr2, y, era, "WITHOUT ox surface")
    delta = ic_w - ic_wo
    verdict = (
        "SURFACE ADDS VALUE"
        if delta > 0.02
        else ("NEUTRAL" if delta > -0.02 else "SURFACE HURTS")
    )
    lines = [
        f"# Options-surface ablation (ES) — delta {delta:+.3f} -> {verdict}",
        f"control {ic_c:+.3f} | with {ic_w:+.3f} | without {ic_wo:+.3f} | era n={int(era.sum())}",
    ]
    (MODULE / "report" / "ox_ablation.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print("\n" + "\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
