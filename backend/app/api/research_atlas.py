"""Research atlas API.

This endpoint turns the generated ML catalog into a UI-friendly map of the
research database: concepts, event types, matrices, exported datasets, docs,
and current package metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/research/atlas", tags=["research_atlas"])

ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = ROOT / "data" / "ml" / "catalog" / "ml_dataset_catalog.json"
ASSET_MANIFEST_PATH = ROOT / "data" / "ml" / "catalog" / "asset_universe_manifest.json"
EXPORT_INDEX_PATH = ROOT / "strategy_lab" / "EXPORT_INDEX.json"
FEATURE_DOCS_DIR = ROOT / "backend" / "app" / "research" / "features"

FEATURE_TITLES: dict[str, str] = {
    "disp": "Displacement Candle",
    "eql": "Equal Levels",
    "ft": "First Third Range",
    "fvg": "Fair Value Gap",
    "fvp": "Forming Volume Profile",
    "itr": "Interval True Range",
    "macro": "Scheduled Macro Events",
    "ob": "Order Block",
    "ogap": "Opening Gaps",
    "orb": "Opening Range",
    "psp": "PSP Candle Divergence",
    "smt": "SMT Divergence",
    "sweep": "Liquidity Sweep",
    "swing": "Swing Pivot",
    "tp": "Time Profile",
    "vp": "Volume Profile",
}

FEATURE_DESCRIPTIONS: dict[str, str] = {
    "disp": "Large directional candles and later retracement or invalidation behavior.",
    "eql": "Equal-high and equal-low liquidity pools built from confirmed pivots.",
    "ft": "First-third session or week ranges and later range reactions.",
    "fvg": "Fair-value-gap zones, mitigation, and universal reaction labels.",
    "fvp": "Live-style as-of volume profile snapshots during the forming session.",
    "itr": "Completed daily, weekly, and session true-range intervals.",
    "macro": "Scheduled economic-calendar anchors with pre-release context and post-release reactions.",
    "ob": "Order-block zones formed after swept references, including retests and invalidations.",
    "ogap": "New day and new week opening gaps used as memory levels.",
    "orb": "Opening range breakout observations across Asia and NY windows.",
    "psp": "Paired-symbol candle divergence between index futures.",
    "smt": "One index takes a higher-timeframe reference while peers do not.",
    "sweep": "Reference high/low sweeps and later recovery, continuation, or OB confirmation.",
    "swing": "Confirmed pivot highs and lows across multiple timeframes.",
    "tp": "Time-profile period levels and later reactions.",
    "vp": "Completed-period volume-profile levels and later reactions.",
}

EXPORT_PREFIX_BY_SHORT: dict[str, tuple[str, ...]] = {
    "fvp": ("forming_vp",),
    "ogap": ("opening_gap",),
    "smt": ("smt",),
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _rel_path(path: str | Path | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def _file_name(item: dict[str, Any]) -> str:
    file_info = item.get("file") or {}
    return Path(str(file_info.get("path") or "")).name


def _artifact_group(name: str) -> str:
    lower = name.lower()
    if "walk_forward" in lower:
        return "walk_forward"
    if "leaderboard" in lower:
        return "leaderboard"
    if "snapshot" in lower or "snapshots" in lower:
        return "snapshot_matrix"
    if "context" in lower:
        return "context"
    return "artifact"


def _matches_short(name: str, short: str) -> bool:
    lower = name.lower()
    prefixes = EXPORT_PREFIX_BY_SHORT.get(short, (short,))
    return any(lower.startswith(prefix.lower()) for prefix in prefixes)


def _concept_docs(short: str) -> dict[str, str | None]:
    folder = FEATURE_DOCS_DIR / short
    readme = folder / "README.md"
    stats = folder / "stats.md"
    return {
        "readme": _rel_path(readme) if readme.exists() else None,
        "stats": _rel_path(stats) if stats.exists() else None,
    }


def _export_datasets_for(short: str, export_index: dict[str, Any]) -> list[dict[str, Any]]:
    datasets = export_index.get("datasets") or []
    out = []
    for dataset in datasets:
        name = str(dataset.get("name") or "")
        matrix = str(dataset.get("matrix") or "")
        if _matches_short(name, short) or f"/{short}_" in matrix or f"\\{short}_" in matrix:
            out.append(dataset)
    return out


def _artifacts_for(short: str, artifacts: list[dict[str, Any]], limit: int = 18) -> list[dict[str, Any]]:
    matches = []
    for artifact in artifacts:
        name = _file_name(artifact)
        if not _matches_short(name, short):
            continue
        file_info = artifact.get("file") or {}
        matches.append(
            {
                "name": name,
                "group": _artifact_group(name),
                "kind": artifact.get("kind"),
                "rows": artifact.get("rows"),
                "columns": artifact.get("columns"),
                "status_counts": artifact.get("status_counts") or {},
                "path": _rel_path(file_info.get("path")),
                "bytes": file_info.get("bytes"),
                "modified_utc": file_info.get("modified_utc"),
            }
        )
    return sorted(matches, key=lambda x: (str(x["group"]), str(x["name"])))[:limit]


def _event_breakdown_for(feature_name: str, catalog: dict[str, Any]) -> list[dict[str, Any]]:
    by_event_type = (catalog.get("database") or {}).get("by_event_type") or []
    rows = [r for r in by_event_type if r.get("feature_name") == feature_name]
    return sorted(rows, key=lambda r: int(r.get("rows") or 0), reverse=True)


def _best_artifact_counts(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"snapshot_matrices": 0, "leaderboards": 0, "walk_forward": 0, "context": 0}
    for artifact in artifacts:
        group = artifact.get("group")
        if group == "snapshot_matrix":
            counts["snapshot_matrices"] += 1
        elif group == "leaderboard":
            counts["leaderboards"] += 1
        elif group == "walk_forward":
            counts["walk_forward"] += 1
        elif group == "context":
            counts["context"] += 1
    return counts


@router.get("")
def read_research_atlas() -> dict[str, Any]:
    catalog = _load_json(CATALOG_PATH)
    asset_manifest = _load_json(ASSET_MANIFEST_PATH)
    export_index = _load_json(EXPORT_INDEX_PATH)

    feature_matrices = catalog.get("feature_matrices") or []
    anchor_artifacts = catalog.get("anchor_artifacts") or []
    active = asset_manifest.get("active_universe") or {}
    database = catalog.get("database") or {}

    concepts: list[dict[str, Any]] = []
    for matrix in sorted(feature_matrices, key=lambda item: int(item.get("rows") or 0), reverse=True):
        short = str(matrix.get("short_name") or "")
        feature_name = str(matrix.get("feature_name") or "")
        artifacts = _artifacts_for(short, anchor_artifacts)
        label_columns = matrix.get("label_columns") or []
        binary_labels = matrix.get("binary_labels") or []
        file_info = matrix.get("file") or {}
        concepts.append(
            {
                "short_name": short,
                "title": FEATURE_TITLES.get(short, short.upper()),
                "description": FEATURE_DESCRIPTIONS.get(short, feature_name),
                "feature_name": feature_name,
                "rows": matrix.get("rows") or 0,
                "columns": matrix.get("columns") or 0,
                "matrix_path": _rel_path(file_info.get("path")),
                "matrix_bytes": file_info.get("bytes"),
                "modified_utc": file_info.get("modified_utc"),
                "min_bar_end_utc": matrix.get("min_bar_end_utc"),
                "max_bar_end_utc": matrix.get("max_bar_end_utc"),
                "event_types": matrix.get("event_types") or [],
                "event_type_count": len(matrix.get("event_types") or []),
                "event_type_breakdown": _event_breakdown_for(feature_name, catalog),
                "sides": matrix.get("sides") or [],
                "primary_symbols": matrix.get("primary_symbols") or [],
                "column_counts": matrix.get("column_counts") or {},
                "label_count": len(label_columns),
                "binary_label_count": len(binary_labels),
                "sample_labels": label_columns[:12],
                "sample_binary_labels": binary_labels[:10],
                "docs": _concept_docs(short),
                "artifacts": artifacts,
                "artifact_counts": _best_artifact_counts(artifacts),
                "export_datasets": _export_datasets_for(short, export_index),
            }
        )

    totals = {
        "research_events": database.get("total_events") or asset_manifest.get("research_events", {}).get("total_events") or 0,
        "feature_matrices": len(feature_matrices),
        "anchor_artifacts": len(anchor_artifacts),
        "export_datasets": len(export_index.get("datasets") or []),
        "active_symbol_count": active.get("symbol_count") or len(active.get("symbols") or []),
        "active_symbols": active.get("symbols") or [],
        "one_minute_earliest_date": active.get("active_ohlcv_1m_earliest_date"),
        "one_minute_latest_date": active.get("active_ohlcv_1m_latest_date"),
        "latest_export": export_index.get("current_package"),
        "latest_export_size_bytes": export_index.get("size_bytes"),
    }

    return {
        "generated_utc": catalog.get("generated_utc"),
        "catalog_path": _rel_path(CATALOG_PATH),
        "asset_manifest_path": _rel_path(ASSET_MANIFEST_PATH),
        "export_index_path": _rel_path(EXPORT_INDEX_PATH),
        "totals": totals,
        "active_universe": active,
        "warehouse": asset_manifest.get("warehouse") or {},
        "export": {
            "current_package": export_index.get("current_package"),
            "release_tag": export_index.get("release_tag"),
            "zip_name": export_index.get("zip_name"),
            "size_bytes": export_index.get("size_bytes"),
            "sha256": export_index.get("sha256"),
            "generated_utc": export_index.get("generated_utc"),
            "datasets": export_index.get("datasets") or [],
        },
        "concepts": concepts,
        "gap_analysis": catalog.get("gap_analysis") or {},
        "warnings": asset_manifest.get("warnings") or [],
    }
