"""Label registry — unified queryable view across every label we've scored.

Sources scanned on rebuild:
  - GPU XGB scoreboards under experiments/gpu_runs/**/scoreboard.csv
    (today's 112-config full scoreboard + the strict-reactions sweep + ...)
  - GPU XGB per-config artifacts under experiments/gpu_runs/**/metrics_summary.csv
  - CPU LightGBM walk-forward summaries in the latest release ZIP at
    D:\BacktestStationData\strategy_lab_core_*\data\ml\anchors\*_walk_forward*summary.csv

Output:
  - data/ml/catalog/label_registry.parquet   (unified, deduped)
  - data/ml/catalog/label_registry.duckdb    (queryable SQL DB)

Usage:
  python -m scripts.ml.label_registry build
  python -m scripts.ml.label_registry top --by gpu_top_lift --limit 20
  python -m scripts.ml.label_registry query "SELECT * FROM labels WHERE gpu_mean_auc > 0.9 ORDER BY gpu_top_lift DESC LIMIT 10"
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
EXPERIMENTS = ROOT / "experiments" / "gpu_runs"
CATALOG_DIR = ROOT / "data" / "ml" / "catalog"
PARQUET_PATH = CATALOG_DIR / "label_registry.parquet"
DUCKDB_PATH = CATALOG_DIR / "label_registry.duckdb"

# Where the LATEST release ZIP extracted to. Update this path when a new
# release is downloaded.
RELEASE_ANCHORS = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions") / "data" / "ml" / "anchors"

# Common columns of the unified registry.
COLUMNS = [
    "matrix", "snapshot", "side", "label",
    "gpu_mean_auc", "gpu_min_auc", "gpu_top_lift", "gpu_top_rate", "gpu_base_rate",
    "cpu_mean_auc", "cpu_min_auc", "cpu_top_lift", "cpu_top_rate", "cpu_base_rate",
    "delta_mean_auc", "delta_top_lift",
    "n_test", "n_folds_ok",
    "sources",
]


def _norm(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _read_gpu_scoreboard(path: Path) -> list[dict]:
    """Read a scoreboard.csv produced by overnight_sweep / strict_reactions_sweep."""
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("status") and r["status"] != "ok":
                continue
            row = {
                "matrix": r.get("matrix") or "",
                "snapshot": r.get("snapshot") or "",
                "side": r.get("side") or "",
                "label": r.get("label") or "",
                "gpu_mean_auc": _norm(r.get("gpu_mean_auc")),
                "gpu_min_auc": _norm(r.get("gpu_min_auc")),
                "gpu_top_lift": _norm(r.get("gpu_top_lift")),
                "gpu_top_rate": _norm(r.get("gpu_top_rate")),
                "gpu_base_rate": _norm(r.get("gpu_base_rate")),
                "cpu_mean_auc": _norm(r.get("cpu_mean_auc")),
                "cpu_min_auc": _norm(r.get("cpu_min_auc")),
                "cpu_top_lift": _norm(r.get("cpu_top_lift")),
                "cpu_top_rate": _norm(r.get("cpu_top_rate")),
                "cpu_base_rate": _norm(r.get("cpu_base_rate")),
                "delta_mean_auc": _norm(r.get("delta_mean_auc")),
                "delta_top_lift": _norm(r.get("delta_top_lift")),
                "n_test": _norm(r.get("n_filtered")),
                "n_folds_ok": _norm(r.get("n_folds_ok")),
                "sources": path.relative_to(ROOT).as_posix(),
            }
            if row["delta_mean_auc"] is None and row["gpu_mean_auc"] is not None and row["cpu_mean_auc"] is not None:
                row["delta_mean_auc"] = row["gpu_mean_auc"] - row["cpu_mean_auc"]
            if row["delta_top_lift"] is None and row["gpu_top_lift"] is not None and row["cpu_top_lift"] is not None:
                row["delta_top_lift"] = row["gpu_top_lift"] - row["cpu_top_lift"]
            out.append(row)
    return out


def _read_gpu_metrics_summary(path: Path) -> list[dict]:
    """Read a single-run metrics_summary.csv (per-fold rows). Aggregate to 1 row."""
    # Infer matrix from the run dir name (`<side>_<snapshot>_<slug>`); skip if we can't.
    run_dir = path.parent
    parent_name = run_dir.parent.name  # e.g. 2026-05-15_strict_opening_gap
    cfg_name = run_dir.name             # e.g. all_at_fire_partial_touch_rejected
    # Read fold rows.
    folds: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            folds.append(r)
    if not folds:
        return []
    label = folds[0].get("label", "")
    # Average across folds for the metrics that matter.
    aucs = [_norm(r.get("auc_test")) for r in folds if _norm(r.get("auc_test")) is not None]
    if not aucs:
        return []
    top_rates = [_norm(r.get("top_bucket_rate")) for r in folds]
    top_lifts = [_norm(r.get("top_bucket_lift_vs_base")) for r in folds]
    base_rates = [_norm(r.get("base_rate_test")) for r in folds]
    return [{
        "matrix": parent_name,  # rough — caller may rewrite
        "snapshot": "at_fire",
        "side": cfg_name.split("_")[0] if "_" in cfg_name else "all",
        "label": label,
        "gpu_mean_auc": sum(aucs) / len(aucs),
        "gpu_min_auc": min(aucs),
        "gpu_top_lift": sum(x for x in top_lifts if x is not None) / max(1, sum(1 for x in top_lifts if x is not None)),
        "gpu_top_rate": sum(x for x in top_rates if x is not None) / max(1, sum(1 for x in top_rates if x is not None)),
        "gpu_base_rate": sum(x for x in base_rates if x is not None) / max(1, sum(1 for x in base_rates if x is not None)),
        "cpu_mean_auc": None, "cpu_min_auc": None, "cpu_top_lift": None,
        "cpu_top_rate": None, "cpu_base_rate": None,
        "delta_mean_auc": None, "delta_top_lift": None,
        "n_test": None, "n_folds_ok": len(folds),
        "sources": path.relative_to(ROOT).as_posix(),
    }]


def _read_release_summary(path: Path) -> list[dict]:
    """Read a *_walk_forward*summary.csv from the release ZIP. CPU-only baseline."""
    # Infer matrix name from the summary filename.
    stem = path.stem  # e.g. sweep_walk_forward_fvggeom_obgeom_liqgeom_regime_summary
    # Convert "<event>_walk_forward_<layers>_summary" to "<event>_snapshots_xctx_<layers>"
    # Special cases:
    name_map = {
        "forming_vp_walk_forward_xctx_summary": "forming_vp_snapshots_xctx",
        "forming_vp_walk_forward_gapctx_summary": "forming_vp_snapshots_xctx_gapctx",
        "fvg_walk_forward_fvggeom_summary": "fvg_snapshots_xctx_fvggeom_obgeom",
        "fvg_walk_forward_strict_context_summary": "fvg_snapshots_xctx_fvggeom_obgeom_strict",
        "itr_snapshot_walk_forward_summary_xctx": "itr_snapshots_xctx",
        "macro_event_type_walk_forward_summary": "macro_event_type_breakdown",
        "macro_snapshot_walk_forward_summary_xctx": "macro_event_snapshots_xctx",
        "opening_gap_strict_context_walk_forward_summary": "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict",
        "opening_gap_walk_forward_xctx_gapctx_summary": "opening_gap_snapshots_xctx_gapctx",
        "opening_gap_walk_forward_xctx_gapctx_obgeom_liqgeom_regime_summary": "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
        "opening_gap_walk_forward_strict_context_summary": "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict",
        "smt_previous_day_walk_forward_at_fire_thesis_context_layers_summary": "smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime",
        "smt_previous_day_walk_forward_fvggeom_summary": "smt_previous_day_snapshots_xctx_fvggeom",
        "smt_previous_day_walk_forward_fvggeom_obgeom_liqgeom_regime_summary": "smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime",
        "sweep_walk_forward_fvggeom_summary": "sweep_snapshots_xctx_fvggeom",
        "sweep_walk_forward_fvggeom_obgeom_summary": "sweep_snapshots_xctx_fvggeom_obgeom",
        "sweep_walk_forward_fvggeom_obgeom_liqgeom_regime_summary": "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime",
        "tp_walk_forward_fvggeom_summary": "tp_snapshots_xctx_fvggeom_obgeom",
        "vp_walk_forward_v2_xctx_summary": "vp_snapshots_xctx",
    }
    matrix = name_map.get(stem, stem)
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            out.append({
                "matrix": matrix,
                "snapshot": r.get("snapshot") or "",
                "side": r.get("side") or "",
                "label": r.get("label") or "",
                "gpu_mean_auc": None, "gpu_min_auc": None, "gpu_top_lift": None,
                "gpu_top_rate": None, "gpu_base_rate": None,
                "cpu_mean_auc": _norm(r.get("mean_test_auc")),
                "cpu_min_auc": _norm(r.get("min_test_auc")),
                "cpu_top_lift": _norm(r.get("mean_top_bucket_lift")),
                "cpu_top_rate": _norm(r.get("mean_top_bucket_rate")),
                "cpu_base_rate": _norm(r.get("mean_base_rate")),
                "delta_mean_auc": None, "delta_top_lift": None,
                "n_test": _norm(r.get("test_rows_total")),
                "n_folds_ok": _norm(r.get("folds_ok")),
                "sources": path.relative_to(path.parents[5]).as_posix() if path.is_relative_to(path.parents[5]) else path.name,
            })
    return out


def _merge(rows: Iterable[dict]) -> pd.DataFrame:
    """Dedupe on (matrix, snapshot, side, label). When same key has multiple rows,
    pick the one with the most non-null GPU columns (richest)."""
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["_richness"] = df[["gpu_mean_auc", "cpu_mean_auc"]].notna().sum(axis=1)
    df = df.sort_values(["matrix", "snapshot", "side", "label", "_richness"], ascending=[True, True, True, True, False])
    deduped = df.drop_duplicates(subset=["matrix", "snapshot", "side", "label"], keep="first")
    # Recompute deltas where both sides are present.
    deduped = deduped.copy()
    mask = deduped["gpu_mean_auc"].notna() & deduped["cpu_mean_auc"].notna()
    deduped.loc[mask, "delta_mean_auc"] = deduped.loc[mask, "gpu_mean_auc"] - deduped.loc[mask, "cpu_mean_auc"]
    mask2 = deduped["gpu_top_lift"].notna() & deduped["cpu_top_lift"].notna()
    deduped.loc[mask2, "delta_top_lift"] = deduped.loc[mask2, "gpu_top_lift"] - deduped.loc[mask2, "cpu_top_lift"]
    return deduped.drop(columns=["_richness"])[COLUMNS]


def build_registry(verbose: bool = True) -> Path:
    rows: list[dict] = []

    # 1) GPU scoreboards.
    for p in EXPERIMENTS.rglob("scoreboard.csv"):
        n = len(rows)
        rows.extend(_read_gpu_scoreboard(p))
        if verbose:
            print(f"  scoreboard {p.relative_to(ROOT)} -> {len(rows) - n} rows")

    # 2) GPU per-config metrics_summary (single-run dirs).
    for p in EXPERIMENTS.rglob("metrics_summary.csv"):
        n = len(rows)
        rows.extend(_read_gpu_metrics_summary(p))
        if verbose:
            print(f"  metrics_summary {p.relative_to(ROOT)} -> {len(rows) - n} rows")

    # 3) Release walk-forward summaries (CPU baselines).
    if RELEASE_ANCHORS.exists():
        for p in RELEASE_ANCHORS.glob("*_walk_forward*summary.csv"):
            n = len(rows)
            rows.extend(_read_release_summary(p))
            if verbose:
                print(f"  release {p.name} -> {len(rows) - n} rows")

    df = _merge(rows)
    if verbose:
        print(f"merged -> {len(df)} unique (matrix, snapshot, side, label) rows")

    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PARQUET_PATH, index=False)
    con = duckdb.connect(str(DUCKDB_PATH))
    con.execute("DROP TABLE IF EXISTS labels")
    con.execute(f"CREATE TABLE labels AS SELECT * FROM read_parquet('{PARQUET_PATH.as_posix()}')")
    con.execute("CREATE INDEX IF NOT EXISTS idx_matrix ON labels(matrix)")
    con.close()
    if verbose:
        print(f"wrote {PARQUET_PATH}")
        print(f"wrote {DUCKDB_PATH}")
    return PARQUET_PATH


def cmd_top(args: argparse.Namespace) -> int:
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    col = args.by
    where = []
    if args.min_auc is not None:
        where.append(f"COALESCE(gpu_mean_auc, cpu_mean_auc) >= {args.min_auc}")
    if args.min_lift is not None:
        where.append(f"COALESCE(gpu_top_lift, cpu_top_lift) >= {args.min_lift}")
    if args.min_base is not None:
        where.append(f"COALESCE(gpu_base_rate, cpu_base_rate) >= {args.min_base}")
    if args.max_base is not None:
        where.append(f"COALESCE(gpu_base_rate, cpu_base_rate) <= {args.max_base}")
    if args.matrix:
        where.append(f"matrix LIKE '{args.matrix}%'")
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = f"SELECT matrix, snapshot, side, label, COALESCE(gpu_mean_auc, cpu_mean_auc) AS auc, COALESCE(gpu_top_lift, cpu_top_lift) AS lift, COALESCE(gpu_base_rate, cpu_base_rate) AS base_rate FROM labels{where_sql} ORDER BY {col} DESC NULLS LAST LIMIT {args.limit}"
    print(sql)
    print()
    df = con.execute(sql).fetchdf()
    pd.set_option("display.max_rows", args.limit)
    pd.set_option("display.max_colwidth", 80)
    pd.set_option("display.width", 200)
    print(df.to_string(index=False))
    con.close()
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    df = con.execute(args.sql).fetchdf()
    pd.set_option("display.max_rows", 200)
    pd.set_option("display.max_colwidth", 80)
    pd.set_option("display.width", 250)
    print(df.to_string(index=False))
    con.close()
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    build_registry(verbose=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Rebuild the registry from all sources.")
    p_build.set_defaults(func=cmd_build)

    p_top = sub.add_parser("top", help="Show top N labels by a metric.")
    p_top.add_argument("--by", default="gpu_top_lift", help="Sort column.")
    p_top.add_argument("--limit", type=int, default=20)
    p_top.add_argument("--min-auc", type=float)
    p_top.add_argument("--min-lift", type=float)
    p_top.add_argument("--min-base", type=float)
    p_top.add_argument("--max-base", type=float)
    p_top.add_argument("--matrix", help="LIKE filter on matrix prefix")
    p_top.set_defaults(func=cmd_top)

    p_q = sub.add_parser("query", help="Run arbitrary SQL against the labels table.")
    p_q.add_argument("sql")
    p_q.set_defaults(func=cmd_query)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
