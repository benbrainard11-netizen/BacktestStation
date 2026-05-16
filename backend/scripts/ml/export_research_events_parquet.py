"""Export the SQLite `research_events` table to partitioned parquet.

The live research DB is SQLite because detectors append events locally. For a
shared cloud data lake, parquet is the safer interchange format: it is compact,
versionable, and queryable by DuckDB/Polars without copying a live SQLite file.

Default output:
    data/research_events/feature_name=<feature>/event_year=<year>/part-*.parquet
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(r"C:\Users\benbr\BacktestStation")
DEFAULT_DB = ROOT / "data" / "meta.sqlite"
DEFAULT_OUTPUT = ROOT / "data" / "research_events"
DEFAULT_MANIFEST = DEFAULT_OUTPUT / "manifest.json"
UTC = timezone.utc

TARGET_COLUMNS = (
    "id",
    "event_id",
    "knowledge_card_id",
    "feature_name",
    "event_type",
    "side",
    "primary_symbol",
    "symbols",
    "related_symbols",
    "timeframe",
    "bar_start_utc",
    "bar_end_utc",
    "event_data",
    "context",
    "outcomes",
    "replay_pointer",
    "source_dataset",
    "source_run_id",
    "detector_version",
    "created_at",
)


def _safe_part(value: Any) -> str:
    text = str(value or "unknown")
    for ch in '<>:"/\\|?*':
        text = text.replace(ch, "_")
    return text.replace(" ", "_")


def _event_year(series: pd.Series) -> pd.Series:
    ts = pd.to_datetime(series, utc=True, errors="coerce")
    return ts.dt.year.fillna(0).astype("int16")


def _research_event_columns(con: sqlite3.Connection) -> set[str]:
    rows = con.execute("PRAGMA table_info(research_events)").fetchall()
    return {str(row[1]) for row in rows}


def _select_expr(column: str, existing_columns: set[str]) -> str:
    if column in existing_columns:
        return column
    if column == "related_symbols" and "symbols" in existing_columns:
        return "symbols AS related_symbols"
    if column == "symbols" and "related_symbols" in existing_columns:
        return "related_symbols AS symbols"
    return f"NULL AS {column}"


def _export_sql(con: sqlite3.Connection) -> str:
    existing_columns = _research_event_columns(con)
    if not existing_columns:
        raise sqlite3.OperationalError("research_events table does not exist or has no columns")

    selected = ",\n    ".join(_select_expr(column, existing_columns) for column in TARGET_COLUMNS)
    order_columns = [
        column
        for column in ("feature_name", "bar_end_utc", "primary_symbol", "id")
        if column in existing_columns
    ]
    order_clause = f"\nORDER BY {', '.join(order_columns)}" if order_columns else ""
    return f"SELECT\n    {selected}\nFROM research_events{order_clause}"


def _write_partition(df: pd.DataFrame, out_dir: Path, part_idx: int) -> Path:
    feature_name = _safe_part(df["feature_name"].iloc[0])
    event_year = int(df["event_year"].iloc[0])
    path = out_dir / f"feature_name={feature_name}" / f"event_year={event_year}" / f"part-{part_idx:06d}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df.drop(columns=["event_year"]), preserve_index=False)
    pq.write_table(table, path, compression="zstd")
    return path


def _manifest_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def export(args: argparse.Namespace) -> dict[str, Any]:
    if not args.db.exists():
        raise FileNotFoundError(args.db)
    if args.output.exists() and args.force:
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True, exist_ok=True)

    counts: dict[tuple[str, int], int] = defaultdict(int)
    files: list[dict[str, Any]] = []
    part_idx = 0
    total_rows = 0
    with sqlite3.connect(args.db) as con:
        sql = _export_sql(con)
        for chunk in pd.read_sql_query(sql, con, chunksize=args.chunk_size):
            if chunk.empty:
                continue
            chunk["event_year"] = _event_year(chunk["bar_end_utc"])
            for (feature_name, event_year), sub in chunk.groupby(["feature_name", "event_year"], dropna=False):
                sub = sub.reset_index(drop=True)
                path = _write_partition(sub, args.output, part_idx)
                part_idx += 1
                row_count = int(len(sub))
                total_rows += row_count
                counts[(str(feature_name), int(event_year))] += row_count
                files.append(
                    {
                        "path": _manifest_path(path),
                        "feature_name": str(feature_name),
                        "event_year": int(event_year),
                        "rows": row_count,
                        "size_bytes": int(path.stat().st_size),
                    }
                )

    by_feature: dict[str, int] = defaultdict(int)
    by_year: dict[str, int] = defaultdict(int)
    for (feature_name, event_year), rows in counts.items():
        by_feature[feature_name] += rows
        by_year[str(event_year)] += rows

    manifest = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "source_db": str(args.db),
        "output": str(args.output),
        "rows": total_rows,
        "files": len(files),
        "partitioning": ["feature_name", "event_year"],
        "by_feature": dict(sorted(by_feature.items())),
        "by_year": dict(sorted(by_year.items())),
        "parquet_files": files,
        "note": (
            "This is a cloud/shareable snapshot of research_events. "
            "Use this instead of copying a live SQLite DB when possible."
        ),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--chunk-size", type=int, default=100_000)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    manifest = export(args)
    print(
        f"wrote {manifest['rows']:,} research_events rows to "
        f"{manifest['files']:,} parquet files under {args.output}"
    )
    print(f"wrote {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
