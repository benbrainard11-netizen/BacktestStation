"""Multi-year walk-forward across the 10 new strict sweep labels.

247 just shipped strategy-lab-core-2026-05-15-strict-sweep with 10
strict sweep labels and a 52k-row matrix. Their CPU walk-forward only
covered 4 configs; this script does the full 12-config sweep on GPU.

Each label gets:
  - side=all (the headline test)
  - side=high and side=low for the strongest label only (sanity-check
    directional consistency)

All 6 test years (2020-2025). Same v2 framework: top-10% precision per
year, edge over base rate, verdict per label.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.gpu_train_pipeline import filter_matrix, run_fold
from scripts.ml.gpu_train_schema_safe import (
    assert_no_label_leak,
    coerce_binary_label,
    load_schema,
    schema_safe_feature_columns,
)
from scripts.ml.gpu_train_walk_forward import extract_years
from scripts.ml.gpu_train_xgb import resolve_device

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
EXPORT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_sweep")
ANCHORS = EXPORT / "data" / "ml" / "anchors"
MATRIX = ANCHORS / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.parquet"
SCHEMA = ANCHORS / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.schema.json"

TEST_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
TOP_DECILE = 0.10

OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_strict_sweep_walkforward"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# 10 strict sweep labels × 1 side ("all") for the broad scan, plus
# high/low for the headline label to check directional consistency.
LABEL_BASES = [
    "sweep_failed_recovered",
    "sweep_succeeded_held_rejection",
    "sweep_partial_retest_rejected",
    "sweep_failed_immediately",
    "sweep_extended_continuation",
]
HORIZONS = ["next_60m", "next_240m"]


@dataclass(frozen=True)
class Cfg:
    label: str
    side: str


def _build_configs() -> list[Cfg]:
    configs: list[Cfg] = []
    # All 10 (label × horizon) at side=all.
    for h in HORIZONS:
        for base in LABEL_BASES:
            configs.append(Cfg(label=f"label.strict.{h}.{base}", side="all"))
    # Add high/low for the proven 60m winner.
    for side in ("high", "low"):
        configs.append(Cfg(label="label.strict.next_60m.sweep_failed_recovered", side=side))
    return configs


def _evaluate(df: pd.DataFrame, schema, cfg: Cfg, device: str) -> list[dict]:
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    work = filter_matrix(df, snapshot="at_fire", side=cfg.side, event_type="all")
    if cfg.label not in work.columns:
        return [{"test_year": y, "status": "label_missing"} for y in TEST_YEARS]
    y_series = coerce_binary_label(work[cfg.label])
    work = work.loc[y_series.notna()].copy()
    if len(work) < 200:
        return [{"test_year": y, "status": "too_few_rows", "n_total": len(work)} for y in TEST_YEARS]
    y = y_series.loc[work.index].astype(int).to_numpy()
    years = extract_years(work)
    rows = []
    for ty in TEST_YEARS:
        result = run_fold(df=work, years=years, y=y, label=cfg.label,
                          feature_pool=feature_pool, test_year=ty, device=device)
        if result["status"] != "ok":
            rows.append({"test_year": ty, "status": result["status"]})
            continue
        preds = result["predictions"]
        rec = result["record"]
        y_true = preds["y_true"].to_numpy()
        p_test = preds["p_test"].to_numpy()
        ranked = np.argsort(-p_test)
        k = max(1, int(round(len(ranked) * TOP_DECILE)))
        idx = ranked[:k]
        prec = float(y_true[idx].mean())
        base = float(rec["base_rate_test"])
        rows.append({
            "test_year": ty, "status": "ok",
            "n_test": int(rec["n_test"]),
            "test_auc": float(rec["auc_test"]),
            "base_rate": base,
            "top10_n": k,
            "top10_precision": prec,
            "top10_edge": prec - base,
        })
    return rows


def main() -> int:
    print(f"loading {MATRIX.name}")
    schema = load_schema(SCHEMA)
    df = pd.read_parquet(MATRIX)
    print(f"  rows={len(df):,}  cols={len(df.columns):,}")

    device_info = resolve_device("auto")
    print(f"  device={device_info.resolved}")

    configs = _build_configs()
    print(f"  configs to run: {len(configs)}")

    overall_t0 = time.time()
    records = []
    for i, cfg in enumerate(configs, 1):
        print(f"\n[{i}/{len(configs)}] {cfg.side:>5} | {cfg.label}")
        t0 = time.time()
        rows = _evaluate(df, schema, cfg, device_info.resolved)
        for row in rows:
            row["label"] = cfg.label
            row["side"] = cfg.side
            records.append(row)
        ok = [r for r in rows if r.get("status") == "ok"]
        if ok:
            precs = [r["top10_precision"] for r in ok]
            edges = [r["top10_edge"] for r in ok]
            n_pass = sum(1 for p in precs if p >= 0.85)
            print(f"  done in {time.time()-t0:.0f}s | top-10 prec: mean={np.mean(precs):.3f} min={min(precs):.3f} | "
                  f"edge: mean={np.mean(edges):+.3f} min={min(edges):+.3f} | {n_pass}/6 years >= 0.85")

    df_all = pd.DataFrame(records)
    df_all.to_csv(OUT_DIR / "per_label_per_year.csv", index=False, float_format="%.4f")

    # Aggregate per label.
    ok_df = df_all[df_all["status"] == "ok"].copy()
    agg = ok_df.groupby(["label", "side"]).agg(
        years_ok=("test_year", "count"),
        mean_auc=("test_auc", "mean"),
        mean_base=("base_rate", "mean"),
        mean_top10_prec=("top10_precision", "mean"),
        min_top10_prec=("top10_precision", "min"),
        mean_top10_edge=("top10_edge", "mean"),
        min_top10_edge=("top10_edge", "min"),
        total_top10_signals=("top10_n", "sum"),
    ).reset_index()

    def _verdict(row) -> str:
        if row["years_ok"] < len(TEST_YEARS):
            return f"INCOMPLETE ({int(row['years_ok'])}/{len(TEST_YEARS)})"
        sub = ok_df[(ok_df["label"] == row["label"]) & (ok_df["side"] == row["side"])]
        n_pass = int((sub["top10_precision"] >= 0.85).sum())
        if n_pass >= 5:
            return f"ROBUST ({n_pass}/6 >= 0.85)"
        if n_pass >= 3:
            return f"MIXED ({n_pass}/6 >= 0.85)"
        return f"FLUKE ({n_pass}/6 >= 0.85)"

    agg["verdict"] = agg.apply(_verdict, axis=1)
    agg = agg.sort_values("mean_top10_prec", ascending=False).reset_index(drop=True)
    agg.to_csv(OUT_DIR / "label_ranking.csv", index=False, float_format="%.4f")
    print("\n=== STRICT SWEEP LABEL RANKING ===")
    print(agg.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Plot mean top-10 precision per (label, side).
    fig, ax = plt.subplots(figsize=(13, 8))
    agg["display"] = agg["label"].str.replace("label.strict.", "") + "  [" + agg["side"] + "]"
    y_pos = np.arange(len(agg))
    colors = ["green" if v.startswith("ROBUST") else "gold" if v.startswith("MIXED") else "lightgray" for v in agg["verdict"]]
    ax.barh(y_pos, agg["mean_top10_prec"], color=colors, edgecolor="black")
    for yi, base in enumerate(agg["mean_base"]):
        ax.plot([base], [yi], "rD", markersize=6)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(agg["display"], fontsize=8)
    ax.set_xlabel("Mean top-10% precision (across 6 test years)")
    ax.set_title("Strict sweep label tournament — multi-year robustness\nGreen=ROBUST, gold=MIXED, gray=FLUKE/INCOMPLETE; red diamonds = base rate")
    ax.set_xlim(0, 1.05)
    ax.grid(True, alpha=0.3, axis="x")
    ax.invert_yaxis()
    plt.tight_layout()
    fig.savefig(OUT_DIR / "label_ranking.png", dpi=120)
    plt.close(fig)

    elapsed = time.time() - overall_t0
    verdict_counts = agg["verdict"].apply(lambda v: v.split()[0]).value_counts().to_dict()
    summary = {
        "configs_total": len(configs),
        "verdict_counts": verdict_counts,
        "elapsed_min": round(elapsed / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {elapsed/60:.1f} min ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
