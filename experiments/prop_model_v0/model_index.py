"""ES day-flat model — same control-first purged WF protocol (reuses btc harness).

Reports mean per-fold OOS IC overall AND on the gex-era subset (2025-05+, where the
options block has data) — the GEX block's incremental value is the gex-era delta vs
the same model's pre-gex performance, plus its feature importances.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/model_index.py
Artifact: report/model_index_v0.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import lightgbm as lgb
import pandas as pd

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from model_wf import PARAMS, fold_ic, run_wf, week_boot_p  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

COST_PTS_ES = 2.0  # ~8 ticks RT stressed (spread+slip+comm) for a day-horizon taker


def main() -> int:
    f = pd.read_parquet(MODULE / "data" / "features_es.parquet")
    feats = [
        c for c in f.columns if not c.startswith("y_") and c not in ("rv20_bps", "c_px")
    ]
    X, y = f[feats], f["y_tbR"]
    print(f"ES matrix: {len(feats)} features x {len(f)} days")

    print("\n[1/2] NEGATIVE CONTROL...")
    pc, fc = run_wf(X, y, shuffle_target=True)
    mc = pc.notna() & y.notna()
    ic_c = fold_ic(pc, y, fc, mc)
    print(f"control mean-fold IC = {ic_c:+.3f}")
    if abs(ic_c) > 0.05:
        raise RuntimeError(f"CONTROL SCORED ({ic_c:+.3f}) — aborting")

    print("\n[2/2] REAL MODEL...")
    pr, fr_ = run_wf(X, y, shuffle_target=False)
    mr = pr.notna() & y.notna()
    ic = fold_ic(pr, y, fr_, mr)
    gex_mask = mr & f["gx_width"].notna()
    pre_mask = mr & f["gx_width"].isna()
    ic_gex = fold_ic(pr, y, fr_, gex_mask)
    ic_pre = fold_ic(pr, y, fr_, pre_mask)

    # decile trade test in net R (cost converted via 0.75*rv20 stop distance)
    cost_r = (COST_PTS_ES / f["c_px"]) / (0.75 * f["rv20_bps"] / 1e4)
    trades = []
    for fid in sorted(fr_[mr].unique()):
        m = mr & (fr_ == fid)
        if m.sum() < 30:
            continue
        pb = pr[m]
        hi, lo = pb.quantile(0.9), pb.quantile(0.1)
        for dt_, p_ in pb.items():
            if p_ >= hi:
                trades.append(
                    {"date": dt_, "net": y.loc[dt_] - cost_r.loc[dt_], "side": "long"}
                )
            elif p_ <= lo:
                trades.append(
                    {"date": dt_, "net": -y.loc[dt_] - cost_r.loc[dt_], "side": "short"}
                )
    tr = pd.DataFrame(trades)
    tr["week"] = pd.DatetimeIndex(tr["date"]).to_period("W").astype(str)
    tr["gex_era"] = pd.DatetimeIndex(tr["date"]) >= pd.Timestamp("2025-05-01")
    net, w = tr["net"].to_numpy(float), tr["week"].to_numpy()

    model = lgb.LGBMRegressor(**PARAMS)
    ok = y.notna()
    model.fit(X[ok], y[ok])
    imp = pd.Series(model.feature_importances_, index=feats)
    gx_imp = imp[[c for c in feats if c.startswith("gx_")]].sort_values(ascending=False)

    lines = [
        f"# ES day-flat model v0 — {len(feats)} features, {int(mr.sum())} OOS days",
        "",
        f"control IC {ic_c:+.3f} | REAL mean-fold IC {ic:+.3f} | "
        f"pre-gex era {ic_pre:+.3f} | GEX era (2025-05+) {ic_gex:+.3f}",
        "",
        f"decile trades n={len(tr)}: mean net R {net.mean():+.3f}, "
        f"week-block p5 {week_boot_p(net, w, 5):+.3f}",
        "by era:",
        tr.groupby("gex_era")["net"].agg(["count", "mean"]).round(3).to_string(),
        "by side:",
        tr.groupby("side")["net"].agg(["count", "mean"]).round(3).to_string(),
        "",
        "GEX feature importances (full fit, descriptive):",
        gx_imp.to_string(),
        "",
        "GEX block spans 2025-05+ only; its incremental value = gex-era IC/trades",
        "vs pre-gex era on the same model. Multi-year walls rerun when regen lands.",
    ]
    (MODULE / "report" / "model_index_v0.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print("\n" + "\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
