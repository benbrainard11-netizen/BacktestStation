"""Build a consolidated index of snapshot leaderboard and walk-forward results."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
CATALOG_DIR = ROOT / "data" / "ml" / "catalog"
DEFAULT_CSV = CATALOG_DIR / "model_result_index.csv"
DEFAULT_PARQUET = CATALOG_DIR / "model_result_index.parquet"
DEFAULT_JSON = CATALOG_DIR / "model_result_index.json"
DEFAULT_DOC = ROOT / "docs" / "ML_MODEL_RESULT_INDEX.md"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _artifact_type(stem: str) -> str:
    if "walk_forward" in stem and "summary" in stem:
        return "walk_forward_summary"
    if "walk_forward" in stem and "folds" in stem:
        return "walk_forward_folds"
    if "leaderboard" in stem:
        return "leaderboard"
    return "other"


def _infer_concept_flavor(stem: str) -> tuple[str, str]:
    flavor = "base"
    concept = stem
    if "_snapshot_leaderboard" in stem:
        concept, rest = stem.split("_snapshot_leaderboard", 1)
        flavor = rest.strip("_") or "base"
    elif "_model_leaderboard" in stem:
        concept, rest = stem.split("_model_leaderboard", 1)
        flavor = rest.strip("_") or "base"
    elif "_snapshot_walk_forward_" in stem:
        concept, rest = stem.split("_snapshot_walk_forward_", 1)
        if rest.startswith("summary_"):
            flavor = rest.removeprefix("summary_") or "base"
        elif rest.startswith("folds_"):
            flavor = rest.removeprefix("folds_") or "base"
        else:
            flavor = rest
    elif "_walk_forward_" in stem:
        concept, rest = stem.split("_walk_forward_", 1)
        rest = rest.replace("_summary", "").replace("_folds", "")
        if rest.startswith("summary_"):
            rest = rest.removeprefix("summary_")
        if rest.startswith("folds_"):
            rest = rest.removeprefix("folds_")
        flavor = rest or "base"
    return concept, flavor


def _read_result_file(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    stem = path.stem
    artifact = _artifact_type(stem)
    concept, flavor = _infer_concept_flavor(stem)
    stat = path.stat()
    df = df.copy()
    df.insert(0, "result_file", str(path))
    df.insert(1, "result_name", stem)
    df.insert(2, "artifact_type", artifact)
    df.insert(3, "concept", concept)
    df.insert(4, "flavor", flavor)
    df.insert(5, "file_bytes", int(stat.st_size))
    df.insert(6, "file_modified_utc", datetime.fromtimestamp(stat.st_mtime, UTC).isoformat())
    return df


def _normalize_rows(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    raw = pd.concat(frames, ignore_index=True, sort=False)
    keep_first = [
        "result_file", "result_name", "artifact_type", "concept", "flavor",
        "snapshot", "side", "label", "status", "reason",
        "n_total", "n_train", "n_val", "n_test",
        "test_rate", "test_auc", "val_auc",
        "folds_attempted", "folds_ok", "folds_skipped", "test_rows_total",
        "mean_test_auc", "median_test_auc", "min_test_auc", "std_test_auc",
        "mean_top_bucket_rate", "min_top_bucket_rate", "mean_top_bucket_lift",
        "top_bucket_rate", "top_bucket_lift_vs_base",
        "usable_feature_columns", "encoded_feature_columns",
        "dropped_feature_columns", "categorical_source_columns", "top_features",
        "file_bytes", "file_modified_utc",
    ]
    for col in keep_first:
        if col not in raw.columns:
            raw[col] = pd.NA
    other_cols = [c for c in raw.columns if c not in keep_first]
    return raw[keep_first + sorted(other_cols)]


def _collect() -> pd.DataFrame:
    paths: list[Path] = []
    paths.extend(ANCHORS_DIR.glob("*leaderboard*.parquet"))
    paths.extend(ANCHORS_DIR.glob("*walk_forward*summary*.parquet"))
    frames = [_read_result_file(path) for path in sorted(set(paths))]
    return _normalize_rows(frames)


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def _fmt_float(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.3f}"


def _fmt_int(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{int(value):,}"


def _write_doc(path: Path, index: pd.DataFrame, generated_utc: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    leader = index[index["artifact_type"].eq("leaderboard")].copy()
    wf = index[index["artifact_type"].eq("walk_forward_summary")].copy()

    leader_ok = leader[leader["status"].fillna("ok").eq("ok")].copy()
    leader_ok["test_auc_num"] = pd.to_numeric(leader_ok["test_auc"], errors="coerce")
    leader_ok = leader_ok.sort_values("test_auc_num", ascending=False).head(25)
    leader_rows = [
        [
            f"`{r.concept}`", f"`{r.flavor}`", f"`{r.snapshot}`", f"`{r.side}`",
            f"`{r.label}`", _fmt_int(r.n_test), _fmt_float(r.test_rate),
            _fmt_float(r.test_auc), _fmt_float(r.top_bucket_rate),
        ]
        for r in leader_ok.itertuples(index=False)
    ]

    wf_ok = wf.copy()
    wf_ok["mean_test_auc_num"] = pd.to_numeric(wf_ok["mean_test_auc"], errors="coerce")
    wf_ok = wf_ok.sort_values("mean_test_auc_num", ascending=False).head(25)
    wf_rows = [
        [
            f"`{r.concept}`", f"`{r.flavor}`", f"`{r.snapshot}`", f"`{r.side}`",
            f"`{r.label}`", _fmt_int(r.folds_ok), _fmt_int(r.test_rows_total),
            _fmt_float(r.mean_test_auc), _fmt_float(r.min_test_auc),
            _fmt_float(r.mean_top_bucket_rate),
        ]
        for r in wf_ok.itertuples(index=False)
    ]

    coverage = (
        index.groupby(["concept", "flavor", "artifact_type"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["concept", "flavor", "artifact_type"])
    )
    coverage_rows = [
        [f"`{r.concept}`", f"`{r.flavor}`", f"`{r.artifact_type}`", _fmt_int(r.rows)]
        for r in coverage.itertuples(index=False)
    ]

    text = [
        "# ML Model Result Index",
        "",
        f"_Generated `{generated_utc}`._",
        "",
        "This file consolidates all saved leaderboard and walk-forward result parquet files.",
        "",
        "## Outputs",
        "",
        f"- CSV: `{DEFAULT_CSV}`",
        f"- Parquet: `{DEFAULT_PARQUET}`",
        f"- JSON summary: `{DEFAULT_JSON}`",
        "",
        "## Coverage",
        "",
        _md_table(["Concept", "Flavor", "Result type", "Rows"], coverage_rows),
        "",
        "## Highest Static Test AUC Rows",
        "",
        _md_table(
            ["Concept", "Flavor", "Snapshot", "Side", "Label", "Test rows", "Base rate", "AUC", "Top bucket"],
            leader_rows,
        ),
        "",
        "## Highest Walk-Forward Mean AUC Rows",
        "",
        _md_table(
            ["Concept", "Flavor", "Snapshot", "Side", "Label", "Folds ok", "Rows", "Mean AUC", "Min AUC", "Top bucket"],
            wf_rows,
        ),
        "",
        "## Reading The Results",
        "",
        "- Static leaderboard rows are useful for fast comparison, but they are easier to overfit.",
        "- Walk-forward rows matter more because each fold tests on later years.",
        "- Very high AUC on labels with very high base rate can still be less useful than a lower-AUC hard label.",
        "- `top_features` is a model diagnostic, not proof of causality.",
    ]
    path.write_text("\n".join(text) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> pd.DataFrame:
    index = _collect()
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    index.to_csv(args.csv, index=False)
    index.to_parquet(args.parquet, index=False)
    generated_utc = _now()
    summary = {
        "generated_utc": generated_utc,
        "rows": int(len(index)),
        "result_files": int(index["result_file"].nunique()) if len(index) else 0,
        "artifact_types": index["artifact_type"].value_counts(dropna=False).to_dict() if len(index) else {},
        "concepts": sorted(index["concept"].dropna().unique().tolist()) if len(index) else [],
        "csv": str(args.csv),
        "parquet": str(args.parquet),
    }
    args.json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_doc(args.doc, index, generated_utc)
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    args = parser.parse_args()
    index = build(args)
    print(f"wrote {args.csv}: {len(index):,} rows")
    print(f"wrote {args.parquet}")
    print(f"wrote {args.json}")
    print(f"wrote {args.doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
