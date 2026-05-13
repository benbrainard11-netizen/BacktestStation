"""Build a catalog/manifest for ML research datasets and concept coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(r"C:\Users\benbr\BacktestStation")
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

UTC = timezone.utc
DB_PATH = ROOT / "data" / "meta.sqlite"
FEATURES_DIR = ROOT / "data" / "ml" / "features"
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
CATALOG_DIR = ROOT / "data" / "ml" / "catalog"
DEFAULT_JSON = CATALOG_DIR / "ml_dataset_catalog.json"
DEFAULT_DOC = ROOT / "docs" / "ML_DATASET_CATALOG.md"

DETECTOR_TO_SHORT = {
    "smt_htf_reference_divergence": "smt",
    "psp_candle_divergence": "psp",
    "fvg_formation": "fvg",
    "order_block": "ob",
    "liquidity_sweep": "sweep",
    "displacement_candle": "disp",
    "swing_pivot": "swing",
    "first_third_range": "ft",
    "opening_range_breakout": "orb",
    "equal_levels": "eql",
    "time_profile": "tp",
    "volume_profile": "vp",
    "forming_volume_profile": "fvp",
    "opening_gap_levels": "ogap",
    "interval_true_range": "itr",
}
SHORT_TO_DETECTOR = {v: k for k, v in DETECTOR_TO_SHORT.items()}


def _sha256(path: Path, *, max_bytes: int | None = None) -> str:
    h = hashlib.sha256()
    remaining = max_bytes
    with open(path, "rb") as f:
        while True:
            read_size = 1024 * 1024
            if remaining is not None:
                if remaining <= 0:
                    break
                read_size = min(read_size, remaining)
            chunk = f.read(read_size)
            if not chunk:
                break
            h.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    digest = h.hexdigest()
    return digest if max_bytes is None else f"partial:{max_bytes}:{digest}"


def _file_meta(path: Path, *, hash_files: bool) -> dict[str, Any]:
    stat = path.stat()
    meta = {
        "path": str(path),
        "bytes": int(stat.st_size),
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }
    if hash_files:
        meta["sha256"] = _sha256(path)
    return meta


def _fmt_int(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{int(value):,}"


def _fmt_pct(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{100.0 * float(value):.1f}%"


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


def _is_binary_like(s: pd.Series) -> bool:
    sample = s.dropna()
    if sample.empty:
        return False
    if sample.dtype == bool:
        return True
    if pd.api.types.is_numeric_dtype(sample):
        return set(sample.unique()).issubset({0, 1, 0.0, 1.0, True, False})
    return False


def _load_registries() -> dict[str, Any]:
    registry: dict[str, Any] = {
        "detectors": {},
        "outcomes": {},
        "errors": [],
    }
    try:
        from app.research.detectors import DETECTORS

        for name, detector in sorted(DETECTORS.items()):
            registry["detectors"][name] = {
                "feature_name": getattr(detector, "feature_name", name),
                "detector_version": getattr(detector, "detector_version", None),
                "supported_modes": list(getattr(detector, "supported_modes", ())),
            }
    except Exception as exc:  # pragma: no cover - catalog should degrade gracefully.
        registry["errors"].append(f"detector registry import failed: {exc}")

    try:
        from app.research.outcomes import OUTCOMES

        for name, computer in sorted(OUTCOMES.items()):
            registry["outcomes"][name] = {
                "feature_name": getattr(computer, "feature_name", name),
                "outcome_version": getattr(computer, "outcome_version", None),
            }
    except Exception as exc:  # pragma: no cover - catalog should degrade gracefully.
        registry["errors"].append(f"outcome registry import failed: {exc}")

    return registry


def _db_stats(con: sqlite3.Connection) -> dict[str, Any]:
    total = pd.read_sql_query("SELECT COUNT(*) AS n FROM research_events", con)["n"].iloc[0]
    by_feature = pd.read_sql_query(
        """
        SELECT
            feature_name,
            COUNT(*) AS rows,
            COUNT(outcomes) AS outcomes_non_null,
            MIN(bar_end_utc) AS min_bar_end_utc,
            MAX(bar_end_utc) AS max_bar_end_utc,
            COUNT(DISTINCT event_type) AS event_types,
            COUNT(DISTINCT primary_symbol) AS primary_symbols
        FROM research_events
        GROUP BY feature_name
        ORDER BY rows DESC
        """,
        con,
    )
    by_event_type = pd.read_sql_query(
        """
        SELECT
            feature_name,
            event_type,
            COUNT(*) AS rows,
            COUNT(outcomes) AS outcomes_non_null,
            MIN(bar_end_utc) AS min_bar_end_utc,
            MAX(bar_end_utc) AS max_bar_end_utc
        FROM research_events
        GROUP BY feature_name, event_type
        ORDER BY feature_name, event_type
        """,
        con,
    )
    by_feature["outcomes_non_null_pct"] = by_feature["outcomes_non_null"] / by_feature["rows"]
    by_event_type["outcomes_non_null_pct"] = (
        by_event_type["outcomes_non_null"] / by_event_type["rows"]
    )
    return {
        "total_events": int(total),
        "by_feature": by_feature.to_dict(orient="records"),
        "by_event_type": by_event_type.to_dict(orient="records"),
    }


def _feature_matrix_stats(path: Path, *, hash_files: bool) -> dict[str, Any]:
    df = pd.read_parquet(path)
    label_cols = [c for c in df.columns if c.startswith("oc.")]
    ed_cols = [c for c in df.columns if c.startswith("ed.")]
    ctx_cols = [c for c in df.columns if c.startswith("ctx.")]
    xd_cols = [c for c in df.columns if c.startswith("xd.")]
    binary_labels = [c for c in label_cols if _is_binary_like(df[c])]
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    object_cols = [c for c in df.columns if pd.api.types.is_object_dtype(df[c])]
    short_name = path.stem
    feature_name = SHORT_TO_DETECTOR.get(short_name, short_name)
    out = {
        "short_name": short_name,
        "feature_name": feature_name,
        "file": _file_meta(path, hash_files=hash_files),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "min_bar_end_utc": (
            pd.to_datetime(df["bar_end_utc"], utc=True).min().isoformat()
            if "bar_end_utc" in df.columns and len(df) else None
        ),
        "max_bar_end_utc": (
            pd.to_datetime(df["bar_end_utc"], utc=True).max().isoformat()
            if "bar_end_utc" in df.columns and len(df) else None
        ),
        "event_types": sorted(str(x) for x in df.get("event_type", pd.Series(dtype=object)).dropna().unique()),
        "sides": sorted(str(x) for x in df.get("side", pd.Series(dtype=object)).dropna().unique()),
        "primary_symbols": sorted(str(x) for x in df.get("primary_symbol", pd.Series(dtype=object)).dropna().unique()),
        "column_counts": {
            "event_data": len(ed_cols),
            "outcome_labels": len(label_cols),
            "binary_outcome_labels": len(binary_labels),
            "context": len(ctx_cols),
            "cross_detector": len(xd_cols),
            "numeric": len(numeric_cols),
            "object": len(object_cols),
        },
        "binary_labels": binary_labels,
        "label_columns": label_cols,
    }
    return out


def _schema_stats(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "file": _file_meta(path, hash_files=False),
        "rows": data.get("rows"),
        "anchor": data.get("anchor"),
        "snapshots": data.get("snapshot_names", []),
        "feature_columns": len(data.get("feature_columns", [])),
        "label_columns": len(data.get("label_columns", [])),
        "generated_utc": data.get("generated_utc"),
    }


def _artifact_stats(path: Path, *, hash_files: bool) -> dict[str, Any]:
    out = {"file": _file_meta(path, hash_files=hash_files), "kind": path.suffix.lstrip(".")}
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
        out["rows"] = int(len(df))
        out["columns"] = int(len(df.columns))
        if "asof.snapshot" in df.columns:
            out["snapshots"] = sorted(str(x) for x in df["asof.snapshot"].dropna().unique())
        if "status" in df.columns:
            out["status_counts"] = {
                str(k): int(v) for k, v in df["status"].value_counts(dropna=False).items()
            }
    elif path.suffix == ".csv":
        df = pd.read_csv(path)
        out["rows"] = int(len(df))
        out["columns"] = int(len(df.columns))
        if "status" in df.columns:
            out["status_counts"] = {
                str(k): int(v) for k, v in df["status"].value_counts(dropna=False).items()
            }
    elif path.suffix == ".json":
        out.update(_schema_stats(path))
    return out


def _build_gap_analysis(
    registry: dict[str, Any],
    features: list[dict[str, Any]],
    anchor_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    feature_names = {f["feature_name"] for f in features}
    detectors = {
        data["feature_name"]: data
        for data in registry.get("detectors", {}).values()
    }
    outcomes = {
        data["feature_name"]: data
        for data in registry.get("outcomes", {}).values()
    }
    snapshot_schemas = [
        {
            "path": a["file"]["path"],
            "feature_name": (a.get("anchor") or {}).get("feature_name"),
            "event_type": (a.get("anchor") or {}).get("event_type"),
            "side": (a.get("anchor") or {}).get("side"),
        }
        for a in anchor_artifacts
        if a["file"]["path"].endswith(".schema.json")
    ]
    known_snapshot_anchors = {
        item["feature_name"] for item in snapshot_schemas if item.get("feature_name")
    }
    smt_expected = {"previous_day_smt", "weekly_smt"}
    smt_present = {
        item["event_type"]
        for item in snapshot_schemas
        if item.get("feature_name") == "smt_htf_reference_divergence"
    }
    missing_feature_matrix = sorted(set(detectors) - feature_names)
    missing_outcome_computer = sorted(set(detectors) - set(outcomes))
    missing_snapshot_builder = sorted(feature_names - known_snapshot_anchors)
    return {
        "detectors_registered": len(detectors),
        "outcomes_registered": len(outcomes),
        "feature_matrices_present": len(feature_names),
        "snapshot_schemas": snapshot_schemas,
        "snapshot_builders_present_for": sorted(known_snapshot_anchors),
        "smt_snapshot_event_types_present": sorted(smt_present),
        "smt_snapshot_event_types_missing": sorted(smt_expected - smt_present),
        "missing_feature_matrix": missing_feature_matrix,
        "missing_outcome_computer": missing_outcome_computer,
        "missing_snapshot_builder": missing_snapshot_builder,
    }


def _write_doc(path: Path, catalog: dict[str, Any]) -> None:
    feature_rows = []
    db_by_feature = {
        row["feature_name"]: row for row in catalog["database"]["by_feature"]
    }
    for item in sorted(catalog["feature_matrices"], key=lambda x: x["rows"], reverse=True):
        db_row = db_by_feature.get(item["feature_name"], {})
        feature_rows.append([
            item["short_name"],
            item["feature_name"],
            _fmt_int(item["rows"]),
            _fmt_int(item["columns"]),
            _fmt_int(item["column_counts"]["event_data"]),
            _fmt_int(item["column_counts"]["outcome_labels"]),
            _fmt_int(item["column_counts"]["binary_outcome_labels"]),
            _fmt_int(item["column_counts"]["cross_detector"]),
            _fmt_pct(db_row.get("outcomes_non_null_pct")),
            item["min_bar_end_utc"][:10] if item["min_bar_end_utc"] else "-",
            item["max_bar_end_utc"][:10] if item["max_bar_end_utc"] else "-",
        ])

    snapshot_rows = []
    for item in catalog["anchor_artifacts"]:
        name = Path(item["file"]["path"]).name
        snapshot_rows.append([
            name,
            item.get("kind", "-"),
            _fmt_int(item.get("rows")),
            _fmt_int(item.get("columns")),
            ", ".join(item.get("snapshots", [])) or "-",
            json.dumps(item.get("status_counts", {})) if item.get("status_counts") else "-",
        ])

    gap = catalog["gap_analysis"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# ML dataset catalog\n\n")
        f.write(f"_Generated `{catalog['generated_utc']}`._\n\n")
        f.write("## Summary\n\n")
        f.write(_md_table(
            ["item", "value"],
            [
                ["research_events rows", _fmt_int(catalog["database"]["total_events"])],
                ["registered detectors", gap["detectors_registered"]],
                ["registered outcome computers", gap["outcomes_registered"]],
                ["feature matrices", gap["feature_matrices_present"]],
                ["snapshot-builder anchor coverage", ", ".join(gap["snapshot_builders_present_for"]) or "-"],
                ["catalog json", catalog["catalog_json_path"]],
            ],
        ))
        f.write("\n\n")

        f.write("## What Already Exists\n\n")
        f.write(
            "- The repo already has registered concept detectors and matching outcome modules.\n"
            "- `data/ml/features` contains per-detector feature matrices for the registered concepts.\n"
            f"- Snapshot/as-of coverage currently exists for "
            f"{', '.join(gap['snapshot_builders_present_for']) or 'none'}.\n"
            "- SMT has richer `at_fire` plus `at_period_close` matrices; generic non-SMT "
            "coverage currently starts with conservative `at_fire` snapshots.\n"
            "- The model leaderboard and walk-forward reports now cover multiple anchor concepts, "
            "including opening gaps and live-style forming volume profile.\n\n"
        )

        f.write("## Feature Matrices\n\n")
        f.write(_md_table(
            [
                "short", "feature_name", "rows", "cols", "ed", "oc",
                "binary_oc", "xd", "db_outcomes", "min", "max",
            ],
            feature_rows,
        ))
        f.write("\n\n")

        f.write("## Anchor / Model Artifacts\n\n")
        f.write(_md_table(
            ["artifact", "kind", "rows", "cols", "snapshots", "status_counts"],
            snapshot_rows,
        ))
        f.write("\n\n")

        f.write("## Gaps To Fill\n\n")
        f.write(_md_table(
            ["gap", "items"],
            [
                ["missing feature matrix", ", ".join(gap["missing_feature_matrix"]) or "none"],
                ["missing outcome computer", ", ".join(gap["missing_outcome_computer"]) or "none"],
                ["missing SMT snapshot event type", ", ".join(gap["smt_snapshot_event_types_missing"]) or "none"],
                ["missing snapshot builder", ", ".join(gap["missing_snapshot_builder"]) or "none"],
            ],
        ))
        f.write("\n\n")

        f.write("## Recommended Next Build\n\n")
        f.write(
            "The highest-leverage missing piece is **generic snapshot-builder coverage** "
            "for the remaining non-SMT concepts. The raw feature matrices exist, but they are "
            "event-time rows. The RTX-ready training database should be built from "
            "audited as-of snapshots so models can safely combine concepts without "
            "look-ahead leakage.\n\n"
        )
        f.write("Suggested order:\n\n")
        f.write(
            "1. Add period-close snapshot builders for `liquidity_sweep`, `fvg_formation`, "
            "`displacement_candle`, and `order_block`.\n"
            "2. Add neutral future-response labels shared across anchors: forward return, "
            "MFE, MAE, took prior high/low, volatility expansion, and time-to-touch.\n"
            "3. Partition snapshot outputs by `anchor=<concept>/event_type=<type>/year=<year>` "
            "once the per-concept schemas stabilize.\n"
            "4. Re-run this catalog after every matrix generation so the RTX training "
            "box can discover datasets from one manifest instead of hard-coded paths.\n"
        )


def build_catalog(args: argparse.Namespace) -> dict[str, Any]:
    registry = _load_registries()
    con = sqlite3.connect(args.db)
    database = _db_stats(con)
    con.close()

    feature_matrices = [
        _feature_matrix_stats(path, hash_files=args.hash_files)
        for path in sorted(args.features_dir.glob("*.parquet"))
    ]
    anchor_artifacts = [
        _artifact_stats(path, hash_files=args.hash_files)
        for path in sorted(args.anchors_dir.glob("*"))
        if path.is_file() and path.suffix in {".parquet", ".csv", ".json"}
    ]
    catalog = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "builder": "backend/scripts/ml/build_ml_dataset_catalog.py",
        "root": str(ROOT),
        "catalog_json_path": str(args.output_json),
        "registry": registry,
        "database": database,
        "feature_matrices": feature_matrices,
        "anchor_artifacts": anchor_artifacts,
    }
    catalog["gap_analysis"] = _build_gap_analysis(
        registry, feature_matrices, anchor_artifacts,
    )
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--features-dir", type=Path, default=FEATURES_DIR)
    parser.add_argument("--anchors-dir", type=Path, default=ANCHORS_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--hash-files", action="store_true")
    args = parser.parse_args()

    catalog = build_catalog(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    _write_doc(args.doc, catalog)

    print(
        "cataloged "
        f"{len(catalog['feature_matrices'])} feature matrices, "
        f"{len(catalog['anchor_artifacts'])} anchor/model artifacts, "
        f"{catalog['database']['total_events']:,} research events"
    )
    print(f"wrote {args.output_json}")
    print(f"wrote {args.doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
