"""Build the asset-universe manifest for ML dataset/version control.

This is the identity layer for research data. It records which symbols exist
in the warehouse, which symbols were used by research events, and which symbols
are present in ML feature matrices. The goal is to prevent silent changes to
the asset universe when another machine expands coverage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import pyarrow.parquet as pq
except Exception:  # pragma: no cover - dependency exists in normal ML env
    pq = None

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

UTC = timezone.utc
DB_PATH = ROOT / "data" / "meta.sqlite"
CATALOG_JSON = ROOT / "data" / "ml" / "catalog" / "ml_dataset_catalog.json"
DEFAULT_JSON = ROOT / "data" / "ml" / "catalog" / "asset_universe_manifest.json"
DEFAULT_DOC = ROOT / "docs" / "ASSET_UNIVERSE_MANIFEST.md"

SYMBOL_SPECS: dict[str, dict[str, Any]] = {
    "ES": {
        "name": "E-mini S&P 500",
        "asset_class": "futures",
        "exchange": "CME Globex",
        "dataset_code": "GLBX.MDP3",
        "tick_size": 0.25,
        "tick_value_usd": 12.50,
        "point_value_usd": 50.0,
        "session_calendar": "CME equity index futures / Globex",
        "display_timezone": "America/New_York",
    },
    "NQ": {
        "name": "E-mini Nasdaq-100",
        "asset_class": "futures",
        "exchange": "CME Globex",
        "dataset_code": "GLBX.MDP3",
        "tick_size": 0.25,
        "tick_value_usd": 5.00,
        "point_value_usd": 20.0,
        "session_calendar": "CME equity index futures / Globex",
        "display_timezone": "America/New_York",
    },
    "YM": {
        "name": "E-mini Dow",
        "asset_class": "futures",
        "exchange": "CBOT Globex",
        "dataset_code": "GLBX.MDP3",
        "tick_size": 1.0,
        "tick_value_usd": 5.00,
        "point_value_usd": 5.0,
        "session_calendar": "CME equity index futures / Globex",
        "display_timezone": "America/New_York",
    },
    "RTY": {
        "name": "E-mini Russell 2000",
        "asset_class": "futures",
        "exchange": "CME Globex",
        "dataset_code": "GLBX.MDP3",
        "tick_size": 0.10,
        "tick_value_usd": 5.00,
        "point_value_usd": 50.0,
        "session_calendar": "CME equity index futures / Globex",
        "display_timezone": "America/New_York",
    },
}


@dataclass(frozen=True, slots=True)
class PartitionRollup:
    schema: str
    symbol: str
    partition_count: int
    file_count: int
    total_bytes: int
    row_count: int | None
    earliest_date: str | None
    latest_date: str | None
    missing_calendar_days_ex_saturday: int | None
    missing_calendar_days_sample: list[str]
    path_prefix: str


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _run_git(args: list[str]) -> str | None:
    try:
        out = subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    return out.strip()


def _git_meta() -> dict[str, Any]:
    status = _run_git(["status", "--short"])
    return {
        "branch": _run_git(["branch", "--show-current"]),
        "commit": _run_git(["rev-parse", "HEAD"]),
        "dirty": bool(status),
    }


def _symbol_root(symbol: str) -> str:
    if symbol.endswith(".c.0"):
        return symbol.split(".", 1)[0]
    m = re.match(r"^([A-Z]+)[FGHJKMNQUVXZ]\d$", symbol)
    if m:
        return m.group(1)
    return re.sub(r"[^A-Z].*$", "", symbol) or symbol


def _symbol_kind(symbol: str) -> str:
    if symbol.endswith(".c.0"):
        return "continuous_front_month"
    if re.match(r"^[A-Z]+[FGHJKMNQUVXZ]\d$", symbol):
        return "specific_contract"
    return "unknown"


def _symbol_meta(symbol: str) -> dict[str, Any]:
    root = _symbol_root(symbol)
    spec = dict(SYMBOL_SPECS.get(root, {}))
    spec.update(
        {
            "symbol": symbol,
            "root_symbol": root,
            "symbol_kind": _symbol_kind(symbol),
        }
    )
    if not SYMBOL_SPECS.get(root):
        spec.setdefault("asset_class", "unknown")
        spec.setdefault("session_calendar", "unknown")
        spec.setdefault("display_timezone", "unknown")
    return spec


def _safe_date_from_partition(name: str) -> date | None:
    value = name.split("=", 1)[-1]
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parquet_rows(path: Path) -> int | None:
    if pq is None:
        return None
    try:
        return int(pq.ParquetFile(path).metadata.num_rows)
    except Exception:
        return None


def _missing_ex_saturday(dates: set[date]) -> tuple[int | None, list[str]]:
    if not dates:
        return None, []
    start = min(dates)
    end = max(dates)
    missing: list[str] = []
    cur = start
    while cur <= end:
        if cur.weekday() != 5 and cur not in dates:
            missing.append(cur.isoformat())
        cur += timedelta(days=1)
    return len(missing), missing[:25]


def _rollup_partition_dirs(
    *,
    schema: str,
    symbol_dir: Path,
    count_rows: bool,
    row_count_workers: int,
) -> PartitionRollup:
    dates: set[date] = set()
    file_count = 0
    total_bytes = 0
    row_count = 0 if count_rows else None
    parquet_files: list[Path] = []

    for date_dir in sorted(symbol_dir.glob("date=*")):
        if not date_dir.is_dir():
            continue
        date_value = _safe_date_from_partition(date_dir.name)
        if date_value is None:
            continue
        files = [p for p in date_dir.glob("*.parquet") if p.is_file()]
        if not files:
            continue
        dates.add(date_value)
        for path in files:
            file_count += 1
            total_bytes += int(path.stat().st_size)
            if row_count is not None:
                parquet_files.append(path)

    if row_count is not None and parquet_files and pq is not None:
        workers = max(1, row_count_workers)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            row_count = sum(row or 0 for row in executor.map(_parquet_rows, parquet_files))

    missing_count, missing_sample = _missing_ex_saturday(dates)
    return PartitionRollup(
        schema=schema,
        symbol=symbol_dir.name.split("=", 1)[-1],
        partition_count=len(dates),
        file_count=file_count,
        total_bytes=total_bytes,
        row_count=row_count,
        earliest_date=min(dates).isoformat() if dates else None,
        latest_date=max(dates).isoformat() if dates else None,
        missing_calendar_days_ex_saturday=missing_count,
        missing_calendar_days_sample=missing_sample,
        path_prefix=str(symbol_dir),
    )


def _scan_warehouse(
    warehouse_root: Path,
    *,
    count_rows: bool,
    row_count_workers: int,
) -> dict[str, Any]:
    by_symbol_schema: list[dict[str, Any]] = []

    bars_root = warehouse_root / "processed" / "bars"
    if bars_root.exists():
        for tf_dir in sorted(bars_root.glob("timeframe=*")):
            if not tf_dir.is_dir():
                continue
            timeframe = tf_dir.name.split("=", 1)[-1]
            schema = f"ohlcv-{timeframe}"
            for symbol_dir in sorted(tf_dir.glob("symbol=*")):
                if symbol_dir.is_dir():
                    by_symbol_schema.append(
                        asdict(_rollup_partition_dirs(
                            schema=schema,
                            symbol_dir=symbol_dir,
                            count_rows=count_rows,
                            row_count_workers=row_count_workers,
                        ))
                    )

    raw_root = warehouse_root / "raw" / "databento"
    if raw_root.exists():
        for schema_dir in sorted(raw_root.iterdir()):
            if not schema_dir.is_dir():
                continue
            for symbol_dir in sorted(schema_dir.glob("symbol=*")):
                if symbol_dir.is_dir():
                    by_symbol_schema.append(
                        asdict(_rollup_partition_dirs(
                            schema=schema_dir.name,
                            symbol_dir=symbol_dir,
                            count_rows=count_rows,
                            row_count_workers=row_count_workers,
                        ))
                    )

    legacy_root = warehouse_root / "parquet"
    if legacy_root.exists():
        for symbol_dir in sorted(legacy_root.iterdir()):
            if not symbol_dir.is_dir():
                continue
            for schema_dir in sorted(symbol_dir.iterdir()):
                if not schema_dir.is_dir():
                    continue
                dates: set[date] = set()
                file_count = 0
                total_bytes = 0
                row_count = 0 if count_rows else None
                parquet_files: list[Path] = []
                for path in sorted(schema_dir.glob("*.parquet")):
                    try:
                        dates.add(date.fromisoformat(path.stem))
                    except ValueError:
                        continue
                    file_count += 1
                    total_bytes += int(path.stat().st_size)
                    if row_count is not None:
                        parquet_files.append(path)
                if row_count is not None and parquet_files and pq is not None:
                    workers = max(1, row_count_workers)
                    with ThreadPoolExecutor(max_workers=workers) as executor:
                        row_count = sum(row or 0 for row in executor.map(_parquet_rows, parquet_files))
                missing_count, missing_sample = _missing_ex_saturday(dates)
                by_symbol_schema.append(
                    {
                        "schema": schema_dir.name,
                        "symbol": symbol_dir.name,
                        "partition_count": len(dates),
                        "file_count": file_count,
                        "total_bytes": total_bytes,
                        "row_count": row_count,
                        "earliest_date": min(dates).isoformat() if dates else None,
                        "latest_date": max(dates).isoformat() if dates else None,
                        "missing_calendar_days_ex_saturday": missing_count,
                        "missing_calendar_days_sample": missing_sample,
                        "path_prefix": str(schema_dir),
                    }
                )

    symbols = sorted({row["symbol"] for row in by_symbol_schema})
    schemas = sorted({row["schema"] for row in by_symbol_schema})
    return {
        "warehouse_root": str(warehouse_root),
        "backend": os.environ.get("BS_DATA_BACKEND", "local"),
        "counted_parquet_rows": count_rows and pq is not None,
        "symbol_count": len(symbols),
        "symbols": symbols,
        "schemas": schemas,
        "by_symbol_schema": sorted(
            by_symbol_schema,
            key=lambda r: (r["symbol"], r["schema"], r.get("earliest_date") or ""),
        ),
    }


def _connect_db(path: Path) -> sqlite3.Connection | None:
    if not path.exists():
        return None
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def _rows(cur: sqlite3.Cursor, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]


def _research_summary(db_path: Path) -> dict[str, Any]:
    con = _connect_db(db_path)
    if con is None:
        return {"available": False, "path": str(db_path)}
    cur = con.cursor()
    total = _rows(cur, "SELECT COUNT(*) AS rows FROM research_events")[0]["rows"]
    by_symbol = _rows(
        cur,
        """
        SELECT
          primary_symbol AS symbol,
          COUNT(*) AS rows,
          COUNT(DISTINCT feature_name) AS feature_count,
          COUNT(DISTINCT event_type) AS event_type_count,
          MIN(bar_end_utc) AS min_bar_end_utc,
          MAX(bar_end_utc) AS max_bar_end_utc,
          SUM(CASE WHEN outcomes IS NOT NULL AND outcomes != 'null' THEN 1 ELSE 0 END) AS outcomes_non_null
        FROM research_events
        GROUP BY primary_symbol
        ORDER BY primary_symbol
        """,
    )
    by_feature = _rows(
        cur,
        """
        SELECT
          feature_name,
          COUNT(*) AS rows,
          COUNT(DISTINCT primary_symbol) AS primary_symbols,
          COUNT(DISTINCT event_type) AS event_types,
          MIN(bar_end_utc) AS min_bar_end_utc,
          MAX(bar_end_utc) AS max_bar_end_utc,
          SUM(CASE WHEN outcomes IS NOT NULL AND outcomes != 'null' THEN 1 ELSE 0 END) AS outcomes_non_null
        FROM research_events
        GROUP BY feature_name
        ORDER BY rows DESC, feature_name
        """,
    )
    feature_symbol_counts = _rows(
        cur,
        """
        SELECT feature_name, primary_symbol AS symbol, COUNT(*) AS rows
        FROM research_events
        GROUP BY feature_name, primary_symbol
        ORDER BY feature_name, primary_symbol
        """,
    )
    con.close()
    for row in by_symbol:
        row["outcome_coverage_pct"] = (
            float(row["outcomes_non_null"]) / float(row["rows"]) if row["rows"] else None
        )
    for row in by_feature:
        row["outcome_coverage_pct"] = (
            float(row["outcomes_non_null"]) / float(row["rows"]) if row["rows"] else None
        )
    return {
        "available": True,
        "path": str(db_path),
        "total_events": total,
        "symbols": [row["symbol"] for row in by_symbol],
        "by_symbol": by_symbol,
        "by_feature": by_feature,
        "feature_symbol_counts": feature_symbol_counts,
    }


def _load_ml_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"available": False, "path": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    matrices = []
    ml_symbols: set[str] = set()
    for item in data.get("feature_matrices", []):
        symbols = item.get("primary_symbols") or []
        ml_symbols.update(symbols)
        matrices.append(
            {
                "short_name": item.get("short_name"),
                "feature_name": item.get("feature_name"),
                "rows": item.get("rows"),
                "columns": item.get("columns"),
                "min_bar_end_utc": item.get("min_bar_end_utc"),
                "max_bar_end_utc": item.get("max_bar_end_utc"),
                "primary_symbols": symbols,
                "event_type_count": len(item.get("event_types") or []),
            }
        )
    return {
        "available": True,
        "path": str(path),
        "generated_utc": data.get("generated_utc"),
        "total_events": (data.get("database") or {}).get("total_events"),
        "feature_matrix_count": len(data.get("feature_matrices") or []),
        "anchor_artifact_count": len(data.get("anchor_artifacts") or []),
        "symbols": sorted(ml_symbols),
        "feature_matrices": matrices,
    }


def _active_universe(
    *,
    warehouse: dict[str, Any],
    research: dict[str, Any],
    catalog: dict[str, Any],
) -> dict[str, Any]:
    research_symbols = set(research.get("symbols") or [])
    ml_symbols = set(catalog.get("symbols") or [])
    active = sorted(research_symbols | ml_symbols)
    warehouse_symbols = set(warehouse.get("symbols") or [])
    data_only = sorted(warehouse_symbols - set(active))
    active_without_bars = sorted(set(active) - warehouse_symbols)

    active_bar_rows = [
        row
        for row in warehouse.get("by_symbol_schema", [])
        if row.get("symbol") in active and row.get("schema") == "ohlcv-1m"
    ]
    earliest = min((row.get("earliest_date") for row in active_bar_rows if row.get("earliest_date")), default=None)
    latest = max((row.get("latest_date") for row in active_bar_rows if row.get("latest_date")), default=None)

    return {
        "symbols": active,
        "symbol_count": len(active),
        "research_symbols": sorted(research_symbols),
        "ml_symbols": sorted(ml_symbols),
        "warehouse_symbols": sorted(warehouse_symbols),
        "data_only_symbols": data_only,
        "active_symbols_without_warehouse_bars": active_without_bars,
        "active_ohlcv_1m_earliest_date": earliest,
        "active_ohlcv_1m_latest_date": latest,
    }


def _fingerprint(payload: dict[str, Any]) -> str:
    material = {
        "universe_id": payload["universe_id"],
        "active_universe": payload["active_universe"],
        "research_total_events": payload["research_events"].get("total_events"),
        "research_by_symbol": payload["research_events"].get("by_symbol"),
        "feature_matrices": payload["ml_catalog"].get("feature_matrices"),
        "warehouse_active_rows": [
            row
            for row in payload["warehouse"].get("by_symbol_schema", [])
            if row.get("symbol") in payload["active_universe"]["symbols"]
        ],
    }
    blob = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _warnings(
    active: dict[str, Any],
    warehouse: dict[str, Any],
    research: dict[str, Any],
    *,
    db_path: Path,
) -> list[str]:
    out: list[str] = []
    if active["data_only_symbols"]:
        out.append(
            "Warehouse contains symbols not present in current research/ML universe: "
            + ", ".join(active["data_only_symbols"])
        )
    if active["active_symbols_without_warehouse_bars"]:
        out.append(
            "Active research/ML symbols missing warehouse bars: "
            + ", ".join(active["active_symbols_without_warehouse_bars"])
        )
    datasets_count = 0
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM datasets")
        datasets_count = int(cur.fetchone()[0])
        con.close()
    except Exception:
        datasets_count = 0
    if datasets_count == 0 and warehouse.get("symbol_count"):
        out.append("DB datasets registry is empty; manifest used direct warehouse path scan.")
    if not research.get("available"):
        out.append("Research event database was not available.")
    return out


def _fmt_int(value: Any) -> str:
    if value is None:
        return "-"
    return f"{int(value):,}"


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "-"
    return f"{100.0 * float(value):.1f}%"


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


def _write_doc(path: Path, manifest: dict[str, Any]) -> None:
    active = manifest["active_universe"]
    research = manifest["research_events"]
    catalog = manifest["ml_catalog"]
    warehouse_rows = [
        row
        for row in manifest["warehouse"]["by_symbol_schema"]
        if row["schema"] == "ohlcv-1m"
    ]
    symbol_rows = []
    symbol_meta = manifest["symbol_metadata"]
    for symbol in active["symbols"]:
        meta = symbol_meta.get(symbol, {})
        bar = next((row for row in warehouse_rows if row["symbol"] == symbol), {})
        research_row = next((row for row in research.get("by_symbol", []) if row["symbol"] == symbol), {})
        symbol_rows.append(
            [
                f"`{symbol}`",
                meta.get("name", "-"),
                meta.get("symbol_kind", "-"),
                bar.get("earliest_date", "-"),
                bar.get("latest_date", "-"),
                _fmt_int(bar.get("partition_count")),
                _fmt_int(bar.get("row_count")),
                _fmt_int(research_row.get("rows")),
            ]
        )

    data_only_rows = []
    for symbol in active["data_only_symbols"]:
        meta = symbol_meta.get(symbol, {})
        bars = next((row for row in warehouse_rows if row["symbol"] == symbol), {})
        data_only_rows.append(
            [
                f"`{symbol}`",
                meta.get("symbol_kind", "-"),
                bars.get("earliest_date", "-"),
                bars.get("latest_date", "-"),
                _fmt_int(bars.get("partition_count")),
                _fmt_int(bars.get("row_count")),
            ]
        )

    feature_rows = [
        [
            f"`{row['feature_name']}`",
            _fmt_int(row["rows"]),
            row["primary_symbols"],
            row["event_types"],
            row["min_bar_end_utc"],
            row["max_bar_end_utc"],
            _fmt_pct(row["outcome_coverage_pct"]),
        ]
        for row in research.get("by_feature", [])
    ]

    matrix_rows = [
        [
            f"`{row['short_name']}`",
            f"`{row['feature_name']}`",
            _fmt_int(row["rows"]),
            _fmt_int(row["columns"]),
            ", ".join(f"`{s}`" for s in row["primary_symbols"]),
        ]
        for row in catalog.get("feature_matrices", [])
    ]

    warnings = manifest.get("warnings") or []
    warning_lines = ["- " + item for item in warnings] if warnings else ["- None"]
    lines = [
        "# Asset Universe Manifest",
        "",
        f"_Generated `{manifest['generated_utc']}`._",
        "",
        "This pins the data identity behind the current ML/research build.",
        "",
        "## Identity",
        "",
        _md_table(
            ["Field", "Value"],
            [
                ["Universe id", f"`{manifest['universe_id']}`"],
                ["Dataset fingerprint", f"`{manifest['dataset_fingerprint']}`"],
                ["Git commit", f"`{manifest['git']['commit']}`"],
                ["Git dirty when generated", f"`{manifest['git']['dirty']}`"],
                ["Warehouse root", f"`{manifest['warehouse']['warehouse_root']}`"],
                ["Active symbols", ", ".join(f"`{s}`" for s in active["symbols"])],
                ["Research events", _fmt_int(research.get("total_events"))],
                ["Feature matrices", _fmt_int(catalog.get("feature_matrix_count"))],
                ["Anchor/model artifacts", _fmt_int(catalog.get("anchor_artifact_count"))],
                ["Active 1m bar coverage", f"{active.get('active_ohlcv_1m_earliest_date')} -> {active.get('active_ohlcv_1m_latest_date')}"],
            ],
        ),
        "",
        "## Active Research Universe",
        "",
        _md_table(
            [
                "Symbol",
                "Name",
                "Kind",
                "Bars start",
                "Bars end",
                "1m partitions",
                "1m rows",
                "Research events",
            ],
            symbol_rows,
        ),
        "",
        "## Warehouse-Only Symbols",
        "",
        "These exist on disk but are not yet part of the current research/ML matrices.",
        "",
        _md_table(
            ["Symbol", "Kind", "Bars start", "Bars end", "1m partitions", "1m rows"],
            data_only_rows,
        )
        if data_only_rows
        else "None.",
        "",
        "## Research Events By Feature",
        "",
        _md_table(
            [
                "Feature",
                "Rows",
                "Symbols",
                "Event types",
                "First event",
                "Last event",
                "Outcome coverage",
            ],
            feature_rows,
        ),
        "",
        "## Feature Matrices",
        "",
        _md_table(["Short", "Feature", "Rows", "Columns", "Symbols"], matrix_rows),
        "",
        "## Warnings",
        "",
        "\n".join(warning_lines),
        "",
        "## Rule",
        "",
        "If another machine adds assets, regenerate this manifest before comparing model results.",
        "Different active symbols or date coverage means a different dataset, even if the code is identical.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    warehouse_root = args.warehouse_root
    count_rows = not args.skip_parquet_row_counts
    warehouse = _scan_warehouse(
        warehouse_root,
        count_rows=count_rows,
        row_count_workers=args.row_count_workers,
    )
    research = _research_summary(args.database)
    catalog = _load_ml_catalog(args.ml_catalog)
    active = _active_universe(warehouse=warehouse, research=research, catalog=catalog)
    symbols_all = sorted(set(warehouse["symbols"]) | set(active["symbols"]))

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "universe_id": args.universe_id,
        "generated_utc": _now_iso(),
        "builder": "backend/scripts/ml/build_asset_universe_manifest.py",
        "git": _git_meta(),
        "paths": {
            "repo_root": str(ROOT),
            "database": str(args.database),
            "ml_catalog": str(args.ml_catalog),
        },
        "symbol_metadata": {symbol: _symbol_meta(symbol) for symbol in symbols_all},
        "active_universe": active,
        "warehouse": warehouse,
        "research_events": research,
        "ml_catalog": catalog,
    }
    manifest["warnings"] = _warnings(active, warehouse, research, db_path=args.database)
    manifest["dataset_fingerprint"] = _fingerprint(manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-id", default="futures_core_v1")
    parser.add_argument("--warehouse-root", type=Path, default=Path(os.environ.get("BS_DATA_ROOT", "C:/data")))
    parser.add_argument("--database", type=Path, default=DB_PATH)
    parser.add_argument("--ml-catalog", type=Path, default=CATALOG_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument(
        "--skip-parquet-row-counts",
        action="store_true",
        help="Only count partitions/files/bytes; faster for huge warehouses.",
    )
    parser.add_argument(
        "--row-count-workers",
        type=int,
        default=16,
        help="Worker threads for parquet metadata row counts.",
    )
    args = parser.parse_args()

    manifest = build_manifest(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    _write_doc(args.doc, manifest)
    print(f"wrote {args.output_json}")
    print(f"wrote {args.doc}")
    print(
        "active_symbols="
        + ",".join(manifest["active_universe"]["symbols"])
        + f" fingerprint={manifest['dataset_fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
