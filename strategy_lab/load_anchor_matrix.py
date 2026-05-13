"""Load an exported anchor matrix using its schema-defined safe columns."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
INDEX_PATH = THIS_DIR / "EXPORT_INDEX.json"


def _load_index() -> dict:
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def _dataset_entry(index: dict, name: str) -> dict:
    for dataset in index["datasets"]:
        if dataset["name"] == name:
            return dataset
    choices = ", ".join(dataset["name"] for dataset in index["datasets"])
    raise KeyError(f"unknown dataset {name!r}; choices: {choices}")


def _default_meta_columns(columns: set[str]) -> list[str]:
    preferred = [
        "anchor.event_id",
        "anchor.feature_name",
        "anchor.short_name",
        "anchor.primary_symbol",
        "anchor.event_type",
        "anchor.side",
        "anchor.bar_end_utc",
        "asof.snapshot",
        "asof.snapshot_ts",
        "asof.feature_cutoff_ts",
        "asof.label_start_ts",
        "asof.label_end_ts",
    ]
    return [col for col in preferred if col in columns]


def load_dataset(
    export_root: Path,
    dataset_name: str,
    *,
    feature_limit: int | None = None,
    label_limit: int | None = None,
) -> tuple[pd.DataFrame, dict]:
    index = _load_index()
    dataset = _dataset_entry(index, dataset_name)
    matrix_path = export_root / dataset["matrix"]
    schema_path = export_root / dataset["schema"]

    if not matrix_path.exists():
        raise FileNotFoundError(f"missing matrix: {matrix_path}")
    if not schema_path.exists():
        raise FileNotFoundError(f"missing schema: {schema_path}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    feature_cols = list(schema["feature_columns"])
    label_cols = list(schema["label_columns"])
    if feature_limit is not None:
        feature_cols = feature_cols[:feature_limit]
    if label_limit is not None:
        label_cols = label_cols[:label_limit]

    all_cols = set(pd.read_parquet(matrix_path, columns=[]).columns)
    meta_cols = _default_meta_columns(all_cols)
    read_cols = meta_cols + feature_cols + label_cols
    df = pd.read_parquet(matrix_path, columns=read_cols)
    return df, schema


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--dataset", default="fvg_xctx_fvggeom")
    parser.add_argument("--feature-limit", type=int, default=25)
    parser.add_argument("--label-limit", type=int, default=5)
    args = parser.parse_args()

    df, schema = load_dataset(
        args.export_root,
        args.dataset,
        feature_limit=args.feature_limit,
        label_limit=args.label_limit,
    )
    print(df.head())
    print(
        f"loaded rows={len(df):,} "
        f"dataset={args.dataset} "
        f"total_features={len(schema['feature_columns']):,} "
        f"total_labels={len(schema['label_columns']):,}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
