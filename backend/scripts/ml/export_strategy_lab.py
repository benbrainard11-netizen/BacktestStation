"""Build a clean strategy-lab data package from audited ML artifacts.

The repo intentionally ignores /data because the parquet files are large.
This exporter creates a separate shareable folder under /exports with:

  - selected audited anchor matrices and matching schemas
  - leaderboard and walk-forward result files
  - human-readable docs
  - MANIFEST.json with sizes and sha256 checksums
  - DATA_DICTIONARY.md and a small loading example
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
DEFAULT_EXPORTS_DIR = ROOT / "exports"


@dataclass(frozen=True, slots=True)
class ExportDataset:
    name: str
    description: str
    matrix: str
    schema: str
    audit_doc: str
    leaderboard_doc: str
    walk_forward_doc: str
    result_files: tuple[str, ...]


CORE_DATASETS: tuple[ExportDataset, ...] = (
    ExportDataset(
        name="fvg_xctx_fvggeom",
        description="FVG anchor rows with cross-concept context and state-aware nearby FVG geometry.",
        matrix="data/ml/anchors/fvg_snapshots_xctx_fvggeom.parquet",
        schema="data/ml/anchors/fvg_snapshots_xctx_fvggeom.schema.json",
        audit_doc="docs/ML_SNAPSHOT_AUDIT_FVG_FVGGEOM.md",
        leaderboard_doc="docs/ML_SNAPSHOT_LEADERBOARD_FVG_FVGGEOM.md",
        walk_forward_doc="docs/ML_SNAPSHOT_WALK_FORWARD_FVG_FVGGEOM.md",
        result_files=(
            "data/ml/anchors/fvg_snapshot_leaderboard_xctx_fvggeom.csv",
            "data/ml/anchors/fvg_snapshot_leaderboard_xctx_fvggeom.parquet",
            "data/ml/anchors/fvg_walk_forward_fvggeom_summary.csv",
            "data/ml/anchors/fvg_walk_forward_fvggeom_summary.parquet",
            "data/ml/anchors/fvg_walk_forward_fvggeom_folds.csv",
            "data/ml/anchors/fvg_walk_forward_fvggeom_folds.parquet",
        ),
    ),
    ExportDataset(
        name="sweep_xctx_fvggeom",
        description="Liquidity sweep anchor rows with cross-concept context and state-aware nearby FVG geometry.",
        matrix="data/ml/anchors/sweep_snapshots_xctx_fvggeom.parquet",
        schema="data/ml/anchors/sweep_snapshots_xctx_fvggeom.schema.json",
        audit_doc="docs/ML_SNAPSHOT_AUDIT_SWEEP_FVGGEOM.md",
        leaderboard_doc="docs/ML_SNAPSHOT_LEADERBOARD_SWEEP_FVGGEOM.md",
        walk_forward_doc="docs/ML_SNAPSHOT_WALK_FORWARD_SWEEP_FVGGEOM.md",
        result_files=(
            "data/ml/anchors/sweep_snapshot_leaderboard_xctx_fvggeom.csv",
            "data/ml/anchors/sweep_snapshot_leaderboard_xctx_fvggeom.parquet",
            "data/ml/anchors/sweep_walk_forward_fvggeom_summary.csv",
            "data/ml/anchors/sweep_walk_forward_fvggeom_summary.parquet",
            "data/ml/anchors/sweep_walk_forward_fvggeom_folds.csv",
            "data/ml/anchors/sweep_walk_forward_fvggeom_folds.parquet",
        ),
    ),
    ExportDataset(
        name="tp_xctx_fvggeom",
        description="Time-profile anchor rows with cross-concept context and state-aware nearby FVG geometry.",
        matrix="data/ml/anchors/tp_snapshots_xctx_fvggeom.parquet",
        schema="data/ml/anchors/tp_snapshots_xctx_fvggeom.schema.json",
        audit_doc="docs/ML_SNAPSHOT_AUDIT_TP_FVGGEOM.md",
        leaderboard_doc="docs/ML_SNAPSHOT_LEADERBOARD_TP_FVGGEOM.md",
        walk_forward_doc="docs/ML_SNAPSHOT_WALK_FORWARD_TP_FVGGEOM.md",
        result_files=(
            "data/ml/anchors/tp_snapshot_leaderboard_xctx_fvggeom.csv",
            "data/ml/anchors/tp_snapshot_leaderboard_xctx_fvggeom.parquet",
            "data/ml/anchors/tp_walk_forward_fvggeom_summary.csv",
            "data/ml/anchors/tp_walk_forward_fvggeom_summary.parquet",
            "data/ml/anchors/tp_walk_forward_fvggeom_folds.csv",
            "data/ml/anchors/tp_walk_forward_fvggeom_folds.parquet",
        ),
    ),
    ExportDataset(
        name="smt_previous_day_xctx_fvggeom",
        description="Previous-day SMT anchor rows with cross-concept context and state-aware nearby FVG geometry.",
        matrix="data/ml/anchors/smt_previous_day_snapshots_xctx_fvggeom.parquet",
        schema="data/ml/anchors/smt_previous_day_snapshots_xctx_fvggeom.schema.json",
        audit_doc="docs/ML_SNAPSHOT_AUDIT_SMT_FVGGEOM.md",
        leaderboard_doc="docs/ML_SNAPSHOT_LEADERBOARD_SMT_FVGGEOM.md",
        walk_forward_doc="docs/ML_SNAPSHOT_WALK_FORWARD_SMT_FVGGEOM.md",
        result_files=(
            "data/ml/anchors/smt_previous_day_snapshot_leaderboard_xctx_fvggeom.csv",
            "data/ml/anchors/smt_previous_day_snapshot_leaderboard_xctx_fvggeom.parquet",
            "data/ml/anchors/smt_previous_day_walk_forward_fvggeom_summary.csv",
            "data/ml/anchors/smt_previous_day_walk_forward_fvggeom_summary.parquet",
            "data/ml/anchors/smt_previous_day_walk_forward_fvggeom_folds.csv",
            "data/ml/anchors/smt_previous_day_walk_forward_fvggeom_folds.parquet",
        ),
    ),
    ExportDataset(
        name="vp_v2_xctx",
        description="Volume-profile anchor rows with v2 post-touch reaction labels and cross-concept context.",
        matrix="data/ml/anchors/vp_snapshots_xctx.parquet",
        schema="data/ml/anchors/vp_snapshots_xctx.schema.json",
        audit_doc="docs/ML_SNAPSHOT_AUDIT_VP_V2_XCTX.md",
        leaderboard_doc="docs/ML_SNAPSHOT_LEADERBOARD_VP_V2_XCTX.md",
        walk_forward_doc="docs/ML_SNAPSHOT_WALK_FORWARD_VP_V2_XCTX.md",
        result_files=(
            "data/ml/anchors/vp_snapshot_leaderboard_v2_xctx.csv",
            "data/ml/anchors/vp_snapshot_leaderboard_v2_xctx.parquet",
            "data/ml/anchors/vp_walk_forward_v2_xctx_summary.csv",
            "data/ml/anchors/vp_walk_forward_v2_xctx_summary.parquet",
            "data/ml/anchors/vp_walk_forward_v2_xctx_folds.csv",
            "data/ml/anchors/vp_walk_forward_v2_xctx_folds.parquet",
        ),
    ),
    ExportDataset(
        name="forming_vp_xctx",
        description="Live-style daily forming volume-profile as-of rows with forward reaction labels and cross-concept context.",
        matrix="data/ml/anchors/forming_vp_snapshots_xctx.parquet",
        schema="data/ml/anchors/forming_vp_snapshots_xctx.schema.json",
        audit_doc="docs/ML_SNAPSHOT_AUDIT_FORMING_VP_XCTX.md",
        leaderboard_doc="docs/ML_SNAPSHOT_LEADERBOARD_FORMING_VP_XCTX.md",
        walk_forward_doc="docs/ML_SNAPSHOT_WALK_FORWARD_FORMING_VP_XCTX.md",
        result_files=(
            "data/ml/anchors/forming_vp_snapshot_leaderboard_xctx.csv",
            "data/ml/anchors/forming_vp_snapshot_leaderboard_xctx.parquet",
            "data/ml/anchors/forming_vp_walk_forward_xctx_summary.csv",
            "data/ml/anchors/forming_vp_walk_forward_xctx_summary.parquet",
            "data/ml/anchors/forming_vp_walk_forward_xctx_folds.csv",
            "data/ml/anchors/forming_vp_walk_forward_xctx_folds.parquet",
        ),
    ),
    ExportDataset(
        name="opening_gap_xctx_gapctx",
        description="NDOG/NWOG anchor rows with cross-concept context plus state-aware prior opening-gap memory.",
        matrix="data/ml/anchors/opening_gap_snapshots_xctx_gapctx.parquet",
        schema="data/ml/anchors/opening_gap_snapshots_xctx_gapctx.schema.json",
        audit_doc="docs/ML_SNAPSHOT_AUDIT_OPENING_GAP_XCTX_GAPCTX.md",
        leaderboard_doc="docs/ML_SNAPSHOT_LEADERBOARD_OPENING_GAP_XCTX_GAPCTX.md",
        walk_forward_doc="docs/ML_SNAPSHOT_WALK_FORWARD_OPENING_GAP_XCTX_GAPCTX.md",
        result_files=(
            "data/ml/anchors/opening_gap_snapshot_leaderboard_xctx_gapctx.csv",
            "data/ml/anchors/opening_gap_snapshot_leaderboard_xctx_gapctx.parquet",
            "data/ml/anchors/opening_gap_walk_forward_xctx_gapctx_summary.csv",
            "data/ml/anchors/opening_gap_walk_forward_xctx_gapctx_summary.parquet",
            "data/ml/anchors/opening_gap_walk_forward_xctx_gapctx_folds.csv",
            "data/ml/anchors/opening_gap_walk_forward_xctx_gapctx_folds.parquet",
            "data/ml/anchors/opening_gap_age_decay.csv",
        ),
    ),
    ExportDataset(
        name="itr_xctx",
        description="Interval true range anchor rows for daily, weekly, and session ranges with cross-concept context.",
        matrix="data/ml/anchors/itr_snapshots_xctx.parquet",
        schema="data/ml/anchors/itr_snapshots_xctx.schema.json",
        audit_doc="docs/ML_SNAPSHOT_AUDIT_ITR_XCTX.md",
        leaderboard_doc="docs/ML_SNAPSHOT_LEADERBOARD_ITR_XCTX.md",
        walk_forward_doc="docs/ML_SNAPSHOT_WALK_FORWARD_ITR_XCTX.md",
        result_files=(
            "backend/app/research/features/itr/README.md",
            "backend/app/research/features/itr/stats.md",
            "data/ml/features/itr.parquet",
            "data/ml/context/itr_cross_concept_context.parquet",
            "data/ml/anchors/itr_snapshot_leaderboard_xctx.csv",
            "data/ml/anchors/itr_snapshot_leaderboard_xctx.parquet",
            "data/ml/anchors/itr_mode_leaderboard_summary.csv",
            "data/ml/anchors/itr_mode_label_leaderboard.csv",
            "data/ml/anchors/itr_snapshot_walk_forward_summary_xctx.csv",
            "data/ml/anchors/itr_snapshot_walk_forward_summary_xctx.parquet",
            "data/ml/anchors/itr_snapshot_walk_forward_folds_xctx.csv",
            "data/ml/anchors/itr_snapshot_walk_forward_folds_xctx.parquet",
        ),
    ),
    ExportDataset(
        name="forming_vp_xctx_gapctx",
        description="Live-style daily forming volume-profile rows with cross-concept context plus NDOG/NWOG memory features.",
        matrix="data/ml/anchors/forming_vp_snapshots_xctx_gapctx.parquet",
        schema="data/ml/anchors/forming_vp_snapshots_xctx_gapctx.schema.json",
        audit_doc="docs/ML_SNAPSHOT_AUDIT_FORMING_VP_GAPCTX.md",
        leaderboard_doc="docs/ML_SNAPSHOT_LEADERBOARD_FORMING_VP_GAPCTX.md",
        walk_forward_doc="docs/ML_SNAPSHOT_WALK_FORWARD_FORMING_VP_GAPCTX.md",
        result_files=(
            "data/ml/anchors/forming_vp_snapshot_leaderboard_gapctx.csv",
            "data/ml/anchors/forming_vp_snapshot_leaderboard_gapctx.parquet",
            "data/ml/anchors/forming_vp_walk_forward_gapctx_summary.csv",
            "data/ml/anchors/forming_vp_walk_forward_gapctx_summary.parquet",
            "data/ml/anchors/forming_vp_walk_forward_gapctx_folds.csv",
            "data/ml/anchors/forming_vp_walk_forward_gapctx_folds.parquet",
        ),
    ),
)

CORE_DOCS: tuple[str, ...] = (
    "docs/ML_DATA_LOCATION_GUIDE.md",
    "docs/ML_DATASET_CATALOG.md",
    "docs/ML_FVG_GEOMETRY_CONTEXT.md",
    "docs/ML_VP_V2_LABELS.md",
    "docs/ML_FORMING_VP_ASOF.md",
    "docs/ML_OPENING_GAP_LEVELS.md",
    "docs/ML_OPENING_GAP_AGE_DECAY.md",
    "docs/ML_CROSS_CONCEPT_CONTEXT_OVERNIGHT.md",
    "docs/ML_CROSS_CONCEPT_CONTEXT_SMT.md",
    "docs/ML_BASELINE_LEAKAGE_AUDIT.md",
)

CATALOG_FILES: tuple[str, ...] = (
    "data/ml/catalog/ml_dataset_catalog.json",
)


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_git(args: list[str]) -> str | None:
    try:
        out = subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    return out.strip()


def _copy_file(src_rel: str, export_root: Path, manifest_files: list[dict[str, Any]]) -> None:
    src = ROOT / src_rel
    if not src.exists():
        raise FileNotFoundError(src)
    dst = export_root / src_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    manifest_files.append(
        {
            "path": src_rel.replace("\\", "/"),
            "size_bytes": int(dst.stat().st_size),
            "sha256": _sha256(dst),
        }
    )


def _load_schema(schema_rel: str) -> dict[str, Any]:
    with (ROOT / schema_rel).open("r", encoding="utf-8") as f:
        return json.load(f)


def _dataset_manifest_entry(dataset: ExportDataset) -> dict[str, Any]:
    schema = _load_schema(dataset.schema)
    return {
        "name": dataset.name,
        "description": dataset.description,
        "matrix": dataset.matrix,
        "schema": dataset.schema,
        "rows": schema.get("rows"),
        "snapshot_names": schema.get("snapshot_names"),
        "feature_column_count": len(schema.get("feature_columns", [])),
        "label_column_count": len(schema.get("label_columns", [])),
        "anchor": schema.get("anchor"),
        "top_feature_prefixes": _top_prefixes(schema.get("feature_columns", [])),
        "sample_labels": schema.get("label_columns", [])[:12],
    }


def _top_prefixes(columns: list[str], limit: int = 12) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for col in columns:
        prefix = col.split(".", 1)[0] if "." in col else col
        counts[prefix] = counts.get(prefix, 0) + 1
    return [
        {"prefix": prefix, "columns": count}
        for prefix, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _write_readme(export_root: Path, datasets: tuple[ExportDataset, ...]) -> None:
    lines = [
        "# Strategy Lab Export",
        "",
        "This package is a clean snapshot of audited ML research datasets.",
        "",
        "## Start Here",
        "",
        "1. Open `DATA_DICTIONARY.md` to see what datasets are included.",
        "2. Open `docs/ML_DATA_LOCATION_GUIDE.md` for the folder map.",
        "3. Use `examples/load_anchor_matrix.py` to load a matrix safely.",
        "4. Treat `label.*` columns as future answers, never as model inputs.",
        "",
        "## Included Core Datasets",
        "",
    ]
    for dataset in datasets:
        lines.extend(
            [
                f"### {dataset.name}",
                "",
                dataset.description,
                "",
                f"- Matrix: `{dataset.matrix}`",
                f"- Schema: `{dataset.schema}`",
                f"- Audit: `{dataset.audit_doc}`",
                f"- Walk-forward: `{dataset.walk_forward_doc}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Safe Loading Rule",
            "",
            "Load the schema JSON and use `feature_columns` for inputs and `label_columns` for future outcomes.",
            "",
            "Do not infer features by selecting every numeric column. Metadata and labels are mixed into the same parquet.",
            "",
            "## Files",
            "",
            "- `MANIFEST.json`: file checksums, sizes, row counts, and git metadata.",
            "- `DATA_DICTIONARY.md`: readable dataset summary.",
            "- `requirements.txt`: minimal Python packages for reading parquet and training small models.",
        ]
    )
    (export_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_requirements(export_root: Path) -> None:
    (export_root / "requirements.txt").write_text(
        "\n".join([
            "pandas",
            "pyarrow",
            "numpy",
            "scikit-learn",
            "lightgbm",
        ]) + "\n",
        encoding="utf-8",
    )


def _write_loader_example(export_root: Path) -> None:
    path = export_root / "examples" / "load_anchor_matrix.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '''"""Minimal safe loader for an exported anchor matrix."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "data/ml/anchors/fvg_snapshots_xctx_fvggeom.parquet"
SCHEMA = ROOT / "data/ml/anchors/fvg_snapshots_xctx_fvggeom.schema.json"


def main() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    feature_cols = schema["feature_columns"]
    label_cols = schema["label_columns"]
    meta_cols = [
        "anchor.event_id",
        "anchor.primary_symbol",
        "anchor.event_type",
        "anchor.side",
        "asof.snapshot_ts",
        "asof.feature_cutoff_ts",
    ]

    # Read only a small subset first. Full matrix can be large.
    df = pd.read_parquet(MATRIX, columns=meta_cols + feature_cols[:25] + label_cols[:5])
    print(df.head())
    print(f"rows={len(df):,} features={len(feature_cols):,} labels={len(label_cols):,}")


if __name__ == "__main__":
    main()
''',
        encoding="utf-8",
    )


def _write_data_dictionary(
    export_root: Path,
    dataset_entries: list[dict[str, Any]],
) -> None:
    lines = [
        "# Data Dictionary",
        "",
        "This file summarizes the exported anchor matrices.",
        "",
        "## Global Rules",
        "",
        "- `feature_columns` in each schema are safe model inputs for that snapshot.",
        "- `label_columns` are future outcomes. Do not use them as inputs.",
        "- `asof.feature_cutoff_ts` is the timestamp the row is allowed to know through.",
        "- Prefer walk-forward result files when judging model usefulness.",
        "",
    ]
    for entry in dataset_entries:
        lines.extend(
            [
                f"## {entry['name']}",
                "",
                entry["description"],
                "",
                f"- Matrix: `{entry['matrix']}`",
                f"- Schema: `{entry['schema']}`",
                f"- Rows: `{entry['rows']}`",
                f"- Snapshots: `{', '.join(entry.get('snapshot_names') or [])}`",
                f"- Feature columns: `{entry['feature_column_count']}`",
                f"- Label columns: `{entry['label_column_count']}`",
                "",
                "Top feature prefixes:",
                "",
            ]
        )
        for item in entry["top_feature_prefixes"]:
            lines.append(f"- `{item['prefix']}`: {item['columns']} columns")
        lines.extend(["", "Sample labels:", ""])
        for label in entry["sample_labels"]:
            lines.append(f"- `{label}`")
        lines.append("")
    (export_root / "DATA_DICTIONARY.md").write_text("\n".join(lines), encoding="utf-8")


def _write_manifest(
    export_root: Path,
    files: list[dict[str, Any]],
    dataset_entries: list[dict[str, Any]],
) -> None:
    status = _run_git(["status", "--short"])
    manifest = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "package": export_root.name,
        "repo_root": str(ROOT),
        "git_branch": _run_git(["branch", "--show-current"]),
        "git_commit": _run_git(["rev-parse", "HEAD"]),
        "git_dirty": bool(status),
        "datasets": dataset_entries,
        "files": sorted(files, key=lambda item: item["path"]),
        "safety_rules": [
            "Use schema feature_columns as model inputs.",
            "Never use label.* columns as model inputs.",
            "Prefer walk-forward results over one-split leaderboards.",
            "Completed VP artifacts are completed-period profiles, not live forming VP.",
        ],
    }
    (export_root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _zip_export(export_root: Path) -> Path:
    zip_path = export_root.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(export_root.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(export_root.parent))
    return zip_path


def build_export(args: argparse.Namespace) -> Path:
    stamp = args.name or f"strategy_lab_{datetime.now(UTC).strftime('%Y%m%d_%H%M%SZ')}"
    export_root = args.output_dir / stamp
    if export_root.exists():
        if not args.force:
            raise FileExistsError(f"{export_root} already exists; use --force or --name a new package")
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True)

    files: list[dict[str, Any]] = []
    dataset_entries = [_dataset_manifest_entry(dataset) for dataset in CORE_DATASETS]

    for dataset in CORE_DATASETS:
        for rel in (
            dataset.matrix,
            dataset.schema,
            dataset.audit_doc,
            dataset.leaderboard_doc,
            dataset.walk_forward_doc,
            *dataset.result_files,
        ):
            _copy_file(rel, export_root, files)

    for rel in (*CORE_DOCS, *CATALOG_FILES):
        _copy_file(rel, export_root, files)

    _write_readme(export_root, CORE_DATASETS)
    _write_requirements(export_root)
    _write_loader_example(export_root)
    _write_data_dictionary(export_root, dataset_entries)

    for rel in ("README.md", "requirements.txt", "examples/load_anchor_matrix.py", "DATA_DICTIONARY.md"):
        path = export_root / rel
        files.append({"path": rel, "size_bytes": int(path.stat().st_size), "sha256": _sha256(path)})

    _write_manifest(export_root, files, dataset_entries)

    if args.zip:
        zip_path = _zip_export(export_root)
        print(f"wrote zip {zip_path}")

    return export_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_EXPORTS_DIR)
    parser.add_argument("--name", help="Export folder name. Defaults to UTC timestamp.")
    parser.add_argument("--force", action="store_true", help="Replace existing export folder.")
    parser.add_argument("--zip", action="store_true", help="Also create a .zip next to the export folder.")
    args = parser.parse_args()

    export_root = build_export(args)
    print(f"wrote export {export_root}")
    print(f"open {export_root / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
