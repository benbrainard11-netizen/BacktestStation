"""Read-only freshness audit for local warehouse partitions vs R2.

The audit does not call Databento and does not upload anything. It compares:

1. Local partitions under BS_DATA_ROOT.
2. R2 `_inventory.json`.
3. Actual objects listed from the configured R2 bucket.

Default scope is schema=mbo because that is the daily local-to-R2 mirror path.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.core.paths import warehouse_root
from app.ingest.r2_client import INVENTORY_KEY, make_s3_client, read_inventory
from app.ingest.r2_partitions import Partition, enumerate_partitions

CORE_MBO_SYMBOLS = ("ES.c.0", "NQ.c.0", "RTY.c.0", "YM.c.0")
EXPECTED_MARKET_SCHEMAS = ("tbbo", "mbp-1", "mbo", "ohlcv-1m")
REPORT_NAME = "r2_freshness_latest.json"

_RAW_KEY_RE = re.compile(
    r"^raw/databento/(?P<schema>[a-z0-9-]+)/"
    r"symbol=(?P<symbol>[^/]+)/date=(?P<date>\d{4}-\d{2}-\d{2})/"
    r"part-\d+\.parquet$"
)
_BARS_KEY_RE = re.compile(
    r"^processed/bars/timeframe=(?P<timeframe>[^/]+)/"
    r"symbol=(?P<symbol>[^/]+)/date=(?P<date>\d{4}-\d{2}-\d{2})/"
    r"part-\d+\.parquet$"
)


@dataclass(frozen=True)
class PartitionRef:
    r2_key: str
    schema: str
    symbol: str
    date: dt.date
    size: int


@dataclass
class SymbolSummary:
    count: int = 0
    total_bytes: int = 0
    earliest_date: str | None = None
    latest_date: str | None = None


@dataclass
class SourceSummary:
    partition_count: int = 0
    total_bytes: int = 0
    earliest_date: str | None = None
    latest_date: str | None = None
    schemas: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    by_symbol: dict[str, SymbolSummary] = field(default_factory=dict)


@dataclass
class DriftSummary:
    count: int
    sample: list[str]


@dataclass
class R2FreshnessAudit:
    ok: bool
    fetched_at: str
    bucket: str | None
    data_root: str
    schemas: list[str]
    expected_symbols: list[str]
    expected_schemas: list[str]
    local: SourceSummary
    inventory: SourceSummary
    bucket_objects: SourceSummary
    inventory_all_schemas: list[str]
    missing_expected_schemas_in_inventory: list[str]
    missing_expected_symbols: dict[str, list[str]]
    symbols_behind_latest: dict[str, dict[str, str | None]]
    local_missing_in_inventory: DriftSummary
    inventory_missing_local: DriftSummary
    inventory_missing_in_bucket: DriftSummary
    bucket_missing_in_inventory: DriftSummary
    inventory_matches_bucket: bool
    local_is_fully_indexed: bool
    local_matches_inventory: bool
    report_path: str | None = None
    errors: list[str] = field(default_factory=list)


def run(
    *,
    data_root: Path | None = None,
    schemas: set[str] | None = None,
    expected_symbols: list[str] | None = None,
    expected_schemas: list[str] | None = None,
    write_report: bool = True,
    sample_limit: int = 20,
) -> R2FreshnessAudit:
    """Build a freshness report without mutating local disk or R2."""
    root = data_root or warehouse_root()
    schema_filter = schemas or {"mbo"}
    expected_symbol_list = expected_symbols or list(CORE_MBO_SYMBOLS)
    expected_schema_list = expected_schemas or list(EXPECTED_MARKET_SCHEMAS)
    fetched_at = dt.datetime.now(dt.timezone.utc).isoformat()
    errors: list[str] = []

    local_parts = [
        _from_local_partition(p)
        for p in enumerate_partitions(root)
        if p.schema_name in schema_filter
    ]

    bucket: str | None = None
    inventory_parts_all: list[PartitionRef] = []
    bucket_parts: list[PartitionRef] = []
    try:
        client, bucket = make_s3_client()
        inventory = read_inventory(client, bucket)
        if not isinstance(inventory, dict):
            errors.append(f"{INVENTORY_KEY} is missing or is not a JSON object")
        else:
            inventory_parts_all = _parse_inventory_parts(inventory)
        bucket_parts = _list_bucket_partitions(client, bucket, schema_filter)
    except Exception as exc:  # noqa: BLE001 - audit should return a report
        errors.append(f"R2 unavailable: {type(exc).__name__}: {exc}")

    inventory_parts = [p for p in inventory_parts_all if p.schema in schema_filter]

    local_keys = {p.r2_key for p in local_parts}
    inventory_keys = {p.r2_key for p in inventory_parts}
    bucket_keys = {p.r2_key for p in bucket_parts}
    inventory_all_schemas = sorted({p.schema for p in inventory_parts_all})

    local_missing_in_inventory = sorted(local_keys - inventory_keys)
    inventory_missing_local = sorted(inventory_keys - local_keys)
    inventory_missing_in_bucket = sorted(inventory_keys - bucket_keys)
    bucket_missing_in_inventory = sorted(bucket_keys - inventory_keys)

    local_summary = _summarize(local_parts)
    inventory_summary = _summarize(inventory_parts)
    bucket_summary = _summarize(bucket_parts)
    missing_expected_symbols = {
        "local": _missing_symbols(local_summary, expected_symbol_list),
        "inventory": _missing_symbols(inventory_summary, expected_symbol_list),
        "bucket": _missing_symbols(bucket_summary, expected_symbol_list),
    }
    symbols_behind_latest = {
        "local": _symbols_behind_latest(local_summary, expected_symbol_list),
        "inventory": _symbols_behind_latest(inventory_summary, expected_symbol_list),
        "bucket": _symbols_behind_latest(bucket_summary, expected_symbol_list),
    }
    missing_expected_schemas = sorted(set(expected_schema_list) - set(inventory_all_schemas))

    inventory_matches_bucket = not inventory_missing_in_bucket and not bucket_missing_in_inventory
    local_is_fully_indexed = not local_missing_in_inventory
    local_matches_inventory = not local_missing_in_inventory and not inventory_missing_local
    ok = (
        not errors
        and inventory_matches_bucket
        and local_is_fully_indexed
        and not missing_expected_schemas
        and not any(missing_expected_symbols.values())
        and not any(symbols_behind_latest.values())
    )

    audit = R2FreshnessAudit(
        ok=ok,
        fetched_at=fetched_at,
        bucket=bucket,
        data_root=str(root),
        schemas=sorted(schema_filter),
        expected_symbols=list(expected_symbol_list),
        expected_schemas=list(expected_schema_list),
        local=local_summary,
        inventory=inventory_summary,
        bucket_objects=bucket_summary,
        inventory_all_schemas=inventory_all_schemas,
        missing_expected_schemas_in_inventory=missing_expected_schemas,
        missing_expected_symbols=missing_expected_symbols,
        symbols_behind_latest=symbols_behind_latest,
        local_missing_in_inventory=_drift(local_missing_in_inventory, sample_limit),
        inventory_missing_local=_drift(inventory_missing_local, sample_limit),
        inventory_missing_in_bucket=_drift(inventory_missing_in_bucket, sample_limit),
        bucket_missing_in_inventory=_drift(bucket_missing_in_inventory, sample_limit),
        inventory_matches_bucket=inventory_matches_bucket,
        local_is_fully_indexed=local_is_fully_indexed,
        local_matches_inventory=local_matches_inventory,
        errors=errors,
    )

    if write_report:
        report_path = root / "logs" / REPORT_NAME
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(to_dict(audit), indent=2), encoding="utf-8")
        audit.report_path = str(report_path)
    return audit


def to_dict(audit: R2FreshnessAudit) -> dict[str, Any]:
    return asdict(audit)


def format_text(audit: R2FreshnessAudit) -> str:
    status = "OK" if audit.ok else "FAIL"
    lines = [
        f"R2 freshness audit | status={status} | bucket={audit.bucket or 'unknown'} "
        f"| schemas={','.join(audit.schemas)}",
        f"data_root={audit.data_root}",
        "",
        _summary_line("local", audit.local),
        _summary_line("inventory", audit.inventory),
        _summary_line("bucket", audit.bucket_objects),
        "",
        f"inventory_matches_bucket={audit.inventory_matches_bucket}",
        f"local_is_fully_indexed={audit.local_is_fully_indexed}",
        f"local_matches_inventory={audit.local_matches_inventory}",
        f"missing_expected_schemas_in_inventory={audit.missing_expected_schemas_in_inventory}",
        f"missing_expected_symbols={audit.missing_expected_symbols}",
        f"symbols_behind_latest={audit.symbols_behind_latest}",
        "",
        _drift_line("local_missing_in_inventory", audit.local_missing_in_inventory),
        _drift_line("inventory_missing_local", audit.inventory_missing_local),
        _drift_line("inventory_missing_in_bucket", audit.inventory_missing_in_bucket),
        _drift_line("bucket_missing_in_inventory", audit.bucket_missing_in_inventory),
    ]
    if audit.errors:
        lines.extend(["", "errors:"])
        lines.extend(f"- {err}" for err in audit.errors)
    if audit.report_path:
        lines.extend(["", f"report={audit.report_path}"])
    return "\n".join(lines)


def _from_local_partition(part: Partition) -> PartitionRef:
    return PartitionRef(
        r2_key=part.r2_key,
        schema=part.schema_name,
        symbol=part.symbol,
        date=part.date,
        size=part.size,
    )


def _parse_inventory_parts(inventory: dict[str, Any]) -> list[PartitionRef]:
    raw_parts = inventory.get("partitions")
    if not isinstance(raw_parts, list):
        return []
    out: list[PartitionRef] = []
    for raw in raw_parts:
        if not isinstance(raw, dict):
            continue
        key = _str_field(raw, "r2_key") or _str_field(raw, "key")
        parsed = _parse_key(key, _int_field(raw, "size", "size_bytes", "bytes"))
        if parsed is None:
            continue
        schema = _str_field(raw, "schema") or parsed.schema
        symbol = _str_field(raw, "symbol") or parsed.symbol
        date_value = _parse_date(_str_field(raw, "date")) or parsed.date
        size = _int_field(raw, "size", "size_bytes", "bytes") or parsed.size
        out.append(
            PartitionRef(
                r2_key=parsed.r2_key,
                schema=schema,
                symbol=symbol,
                date=date_value,
                size=size,
            )
        )
    return out


def _list_bucket_partitions(
    client: Any,
    bucket: str,
    schemas: set[str],
) -> list[PartitionRef]:
    out: list[PartitionRef] = []
    for schema in sorted(schemas):
        for prefix in _prefixes_for_schema(schema):
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for item in page.get("Contents", []):
                    key = item.get("Key")
                    if not isinstance(key, str):
                        continue
                    parsed = _parse_key(key, int(item.get("Size") or 0))
                    if parsed is not None and parsed.schema == schema:
                        out.append(parsed)
    return out


def _parse_key(key: str | None, size: int) -> PartitionRef | None:
    if not key:
        return None
    raw_match = _RAW_KEY_RE.match(key)
    if raw_match:
        return PartitionRef(
            r2_key=key,
            schema=raw_match.group("schema"),
            symbol=raw_match.group("symbol"),
            date=dt.date.fromisoformat(raw_match.group("date")),
            size=size,
        )
    bars_match = _BARS_KEY_RE.match(key)
    if bars_match:
        return PartitionRef(
            r2_key=key,
            schema=f"ohlcv-{bars_match.group('timeframe')}",
            symbol=bars_match.group("symbol"),
            date=dt.date.fromisoformat(bars_match.group("date")),
            size=size,
        )
    return None


def _prefixes_for_schema(schema: str) -> list[str]:
    if schema.startswith("ohlcv-"):
        timeframe = schema.removeprefix("ohlcv-")
        return [f"processed/bars/timeframe={timeframe}/"]
    return [f"raw/databento/{schema}/"]


def _summarize(parts: list[PartitionRef]) -> SourceSummary:
    if not parts:
        return SourceSummary()
    dates = sorted(p.date for p in parts)
    symbols = sorted({p.symbol for p in parts})
    by_symbol: dict[str, SymbolSummary] = {}
    for symbol in symbols:
        symbol_parts = [p for p in parts if p.symbol == symbol]
        symbol_dates = sorted(p.date for p in symbol_parts)
        by_symbol[symbol] = SymbolSummary(
            count=len(symbol_parts),
            total_bytes=sum(p.size for p in symbol_parts),
            earliest_date=symbol_dates[0].isoformat() if symbol_dates else None,
            latest_date=symbol_dates[-1].isoformat() if symbol_dates else None,
        )
    return SourceSummary(
        partition_count=len(parts),
        total_bytes=sum(p.size for p in parts),
        earliest_date=dates[0].isoformat(),
        latest_date=dates[-1].isoformat(),
        schemas=sorted({p.schema for p in parts}),
        symbols=symbols,
        by_symbol=by_symbol,
    )


def _missing_symbols(summary: SourceSummary, expected_symbols: list[str]) -> list[str]:
    present = set(summary.symbols)
    return sorted(symbol for symbol in expected_symbols if symbol not in present)


def _symbols_behind_latest(
    summary: SourceSummary,
    expected_symbols: list[str],
) -> dict[str, str | None]:
    if summary.latest_date is None:
        return {}
    behind: dict[str, str | None] = {}
    for symbol in expected_symbols:
        symbol_summary = summary.by_symbol.get(symbol)
        if symbol_summary is None:
            continue
        if symbol_summary.latest_date != summary.latest_date:
            behind[symbol] = symbol_summary.latest_date
    return behind


def _drift(keys: list[str], sample_limit: int) -> DriftSummary:
    return DriftSummary(count=len(keys), sample=keys[:sample_limit])


def _summary_line(name: str, summary: SourceSummary) -> str:
    gb = summary.total_bytes / 1_000_000_000
    return (
        f"{name}: partitions={summary.partition_count} bytes={summary.total_bytes} "
        f"gb={gb:.3f} latest={summary.latest_date} symbols={','.join(summary.symbols)}"
    )


def _drift_line(name: str, drift: DriftSummary) -> str:
    suffix = f" sample={drift.sample}" if drift.sample else ""
    return f"{name}: count={drift.count}{suffix}"


def _str_field(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) and value else None


def _int_field(raw: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value)
    return 0


def _parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def _parse_csv_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit local/R2 data freshness.")
    parser.add_argument(
        "--schemas",
        default="mbo",
        help="Comma-separated schema filter. Default: mbo.",
    )
    parser.add_argument(
        "--expected-symbols",
        default=",".join(CORE_MBO_SYMBOLS),
        help="Comma-separated symbols expected in the selected schema.",
    )
    parser.add_argument(
        "--expected-schemas",
        default=",".join(EXPECTED_MARKET_SCHEMAS),
        help="Comma-separated schemas expected somewhere in R2 _inventory.json.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument(
        "--no-write",
        action="store_true",
        help=f"Do not write logs/{REPORT_NAME}.",
    )
    args = parser.parse_args(argv)

    audit = run(
        schemas=_parse_csv_set(args.schemas),
        expected_symbols=_parse_csv_list(args.expected_symbols),
        expected_schemas=_parse_csv_list(args.expected_schemas),
        write_report=not args.no_write,
    )
    if args.json:
        print(json.dumps(to_dict(audit), indent=2))
    else:
        print(format_text(audit))
    return 0 if audit.ok else 1


if __name__ == "__main__":
    sys.exit(main())
