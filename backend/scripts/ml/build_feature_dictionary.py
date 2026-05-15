"""Build a repo-readable dictionary for ML feature families and datasets."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

try:  # pyarrow gives parquet metadata without loading full matrices.
    import pyarrow.parquet as pq
except Exception:  # pragma: no cover - fallback is only for thin envs.
    pq = None

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from snapshot_feature_registry import registry_as_dict  # noqa: E402

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
FEATURES_DIR = ROOT / "data" / "ml" / "features"
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
CATALOG_DIR = ROOT / "data" / "ml" / "catalog"
DEFAULT_JSON = CATALOG_DIR / "feature_dictionary.json"
DEFAULT_DOC = ROOT / "docs" / "ML_FEATURE_DICTIONARY.md"

RAW_PREFIX_DESCRIPTIONS = {
    "(root)": ("raw_metadata", "Top-level event identifiers, timestamp pieces, side, symbol, and event type."),
    "ed.": ("raw_event_data", "Flattened detector payload from the original event. Safe only when the event is already knowable."),
    "oc.": ("raw_outcomes", "Flattened forward outcomes. These are labels or diagnostics, not model features unless explicitly converted."),
    "ctx.": ("raw_context", "Flattened detector context fields captured at event creation."),
    "xd.": ("prior_cross_detector", "Coarse prior-event flags from the older cross-detector enrichment pass."),
    "label.": ("forward_label", "Forward prediction targets. These must never be fed back as model features."),
}

CONCEPTS = {
    "smt": "Smart-money-technique divergence events.",
    "psp": "Power-of-three / PSP candle divergence events.",
    "fvg": "Fair-value-gap formation events.",
    "ob": "Order-block formation and reaction events.",
    "sweep": "Liquidity sweep events against prior/session levels.",
    "disp": "Displacement candle events.",
    "swing": "Confirmed swing pivot highs/lows.",
    "eql": "Equal high/low liquidity clusters.",
    "ft": "First-third range behavior.",
    "orb": "Opening range breakout events.",
    "tp": "Time-profile parent-period structure.",
    "vp": "Completed volume-profile structure.",
    "fvp": "Forming volume profile snapshots known as of the cutoff.",
    "ogap": "New-day/new-week opening gap levels.",
    "itr": "Completed interval true range/session regime events.",
    "macro": "Scheduled macro-event anchors and pre-release context.",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _schema_path_for_parquet(path: Path) -> Path | None:
    candidate = path.with_suffix(".schema.json")
    return candidate if candidate.exists() else None


def _load_json(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _parquet_meta(path: Path) -> tuple[int, list[str]]:
    if pq is not None:
        pf = pq.ParquetFile(path)
        return int(pf.metadata.num_rows), list(pf.schema.names)
    df = pd.read_parquet(path)
    return int(len(df)), list(df.columns)


def _dataset_type(path: Path) -> str:
    if path.parent == FEATURES_DIR:
        return "phase1_feature_matrix"
    stem = path.stem
    if "leaderboard" in stem or "walk_forward" in stem:
        return "model_result"
    return "snapshot_matrix"


def _prefix(col: str) -> str:
    if "." not in col:
        return "(root)"
    return col.split(".", 1)[0] + "."


def _registry_descriptions() -> dict[str, tuple[str, str]]:
    out = dict(RAW_PREFIX_DESCRIPTIONS)
    registry = registry_as_dict()
    for rule in registry.get("feature_rules", []):
        out[rule["prefix"]] = (rule["family"], rule["description"])
    for rule in registry.get("label_rules", []):
        out[rule["prefix"]] = ("forward_label", rule["description"])
    return out


def _concept_for_path(path: Path, schema: dict[str, Any]) -> str | None:
    if path.parent == FEATURES_DIR:
        return path.stem
    anchor = schema.get("anchor") or {}
    short = anchor.get("short_name")
    if short:
        return str(short)
    stem = path.stem
    for concept in sorted(CONCEPTS, key=len, reverse=True):
        if stem.startswith(concept):
            return concept
    return None


def _build_dataset_record(path: Path) -> dict[str, Any]:
    rows, columns = _parquet_meta(path)
    schema_path = _schema_path_for_parquet(path)
    schema = _load_json(schema_path)
    prefix_counts: dict[str, int] = defaultdict(int)
    prefix_examples: dict[str, list[str]] = defaultdict(list)
    for col in columns:
        pref = _prefix(col)
        prefix_counts[pref] += 1
        if len(prefix_examples[pref]) < 8:
            prefix_examples[pref].append(col)

    stat = path.stat()
    return {
        "name": path.stem,
        "path": str(path),
        "dataset_type": _dataset_type(path),
        "concept": _concept_for_path(path, schema),
        "rows": rows,
        "columns": len(columns),
        "bytes": int(stat.st_size),
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
        "schema_path": str(schema_path) if schema_path else None,
        "anchor": schema.get("anchor"),
        "snapshot_names": schema.get("snapshot_names"),
        "feature_column_count": len(schema.get("feature_columns", [])),
        "label_column_count": len(schema.get("label_columns", [])),
        "prefix_counts": dict(sorted(prefix_counts.items())),
        "prefix_examples": dict(sorted(prefix_examples.items())),
    }


def _collect_datasets() -> list[dict[str, Any]]:
    paths = list(FEATURES_DIR.glob("*.parquet"))
    paths += [
        p for p in ANCHORS_DIR.glob("*.parquet")
        if _dataset_type(p) == "snapshot_matrix"
    ]
    return [_build_dataset_record(p) for p in sorted(paths)]


def _family_records(datasets: list[dict[str, Any]]) -> dict[str, Any]:
    descriptions = _registry_descriptions()
    records: dict[str, Any] = {}
    all_examples: dict[str, list[str]] = defaultdict(list)
    all_datasets: dict[str, set[str]] = defaultdict(set)
    total_counts: dict[str, int] = defaultdict(int)

    for ds in datasets:
        for pref, count in ds["prefix_counts"].items():
            all_datasets[pref].add(ds["name"])
            total_counts[pref] += int(count)
            for col in ds["prefix_examples"].get(pref, []):
                if col not in all_examples[pref] and len(all_examples[pref]) < 20:
                    all_examples[pref].append(col)

    for pref in sorted(total_counts):
        family, desc = descriptions.get(
            pref,
            ("unregistered", "No explicit registry description yet; inspect the owning detector/schema."),
        )
        records[pref] = {
            "family": family,
            "description": desc,
            "dataset_count": len(all_datasets[pref]),
            "total_column_references": total_counts[pref],
            "datasets": sorted(all_datasets[pref]),
            "example_columns": all_examples[pref],
        }
    return records


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def _fmt_int(value: Any) -> str:
    return f"{int(value):,}"


def _write_doc(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    datasets = payload["datasets"]
    families = payload["column_families"]
    feature_sets = [d for d in datasets if d["dataset_type"] == "phase1_feature_matrix"]
    snapshots = [d for d in datasets if d["dataset_type"] == "snapshot_matrix"]

    family_rows = []
    for pref, rec in sorted(families.items()):
        family_rows.append([
            f"`{pref}`",
            rec["family"],
            _fmt_int(rec["dataset_count"]),
            _fmt_int(rec["total_column_references"]),
            rec["description"],
        ])

    concept_rows = []
    for ds in sorted(feature_sets, key=lambda d: d["concept"] or d["name"]):
        concept = ds["concept"] or ds["name"]
        concept_rows.append([
            f"`{concept}`",
            _fmt_int(ds["rows"]),
            _fmt_int(ds["columns"]),
            ", ".join(f"`{k}` {v}" for k, v in ds["prefix_counts"].items()),
        ])

    snapshot_rows = []
    for ds in sorted(snapshots, key=lambda d: (d["concept"] or "", d["name"])):
        snapshot_rows.append([
            f"`{ds['name']}`",
            f"`{ds['concept']}`",
            _fmt_int(ds["rows"]),
            _fmt_int(ds["columns"]),
            _fmt_int(ds["feature_column_count"]),
            _fmt_int(ds["label_column_count"]),
        ])

    text = [
        "# ML Feature Dictionary",
        "",
        f"_Generated `{payload['generated_utc']}`._",
        "",
        "This is the database map. It explains column families, which matrices use them, and which parts are features versus labels.",
        "",
        "## Totals",
        "",
        f"- Phase 1 feature matrices: `{len(feature_sets):,}`",
        f"- Snapshot matrices: `{len(snapshots):,}`",
        f"- Column families: `{len(families):,}`",
        "",
        "## Column Families",
        "",
        _md_table(["Prefix", "Family", "Datasets", "Column refs", "Meaning"], family_rows),
        "",
        "## Phase 1 Feature Matrices",
        "",
        _md_table(["Concept", "Rows", "Cols", "Prefix counts"], concept_rows),
        "",
        "## Snapshot Matrices",
        "",
        _md_table(["Matrix", "Concept", "Rows", "Cols", "Feature cols", "Label cols"], snapshot_rows),
        "",
        "## How To Read Columns",
        "",
        "- `anchor.*` and `asof.*` identify the anchor event and the exact cutoff used for features.",
        "- `<concept>.ed.*` means detector event data for the anchor concept, filtered into a snapshot namespace.",
        "- `xctx.*` means prior cross-concept counts/ages known before the cutoff.",
        "- `fvggeom.*`, `obgeom.*`, and `gapctx.*` mean state-aware level geometry built from prior events only.",
        "- `label.*` is a target. It is not a feature.",
        "",
        "## Machine-Readable Copy",
        "",
        f"- JSON: `{payload['output_json']}`",
    ]
    path.write_text("\n".join(text) + "\n", encoding="utf-8")


def build(args: argparse.Namespace) -> dict[str, Any]:
    datasets = _collect_datasets()
    payload = {
        "generated_utc": _now(),
        "root": str(ROOT),
        "output_json": str(args.output),
        "concepts": CONCEPTS,
        "registry": registry_as_dict(),
        "datasets": datasets,
        "column_families": _family_records(datasets),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_doc(args.doc, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    args = parser.parse_args()
    payload = build(args)
    print(
        f"wrote {args.output}: "
        f"{len(payload['datasets']):,} datasets, {len(payload['column_families']):,} families"
    )
    print(f"wrote {args.doc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
