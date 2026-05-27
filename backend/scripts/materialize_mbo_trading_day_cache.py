"""Materialize clean MBO files by futures trading day.

Raw Databento files are UTC-calendar request partitions. They can contain
MBO snapshot carry-in rows whose ``ts_event`` predates the request window.
That is valid source data, but it is hostile to research scripts.

This script writes a clean, simple layer:

    clean/databento/mbo_trading_day/
      symbol=ES.c.0/trading_day=2026-04-22/part-000.parquet

Each output file contains only live MBO events whose ``ts_event`` is inside:

    trading_day 18:00 ET previous day -> 17:00 ET trading_day

and whose ``ts_event`` also belongs to the UTC-calendar raw partition it came
from. That second filter drops snapshot carry-in rows from the next raw file.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

import duckdb

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.paths import warehouse_root  # noqa: E402
from app.data.schema import GENERATOR_VERSION, SCHEMA_VERSION  # noqa: E402
from app.research.sessions import globex_day_for_trading_date  # noqa: E402

SYMBOLS = ("ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0")
GENERATOR_NAME = "materialize_mbo_trading_day_cache"


def date_range(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)


def calendar_dates_for_window(start: dt.datetime, end: dt.datetime) -> list[dt.date]:
    last = end - dt.timedelta(microseconds=1)
    return [d for d in date_range(start.date(), last.date())]


def raw_path(data_root: Path, symbol: str, day: dt.date) -> Path:
    return (
        data_root
        / "raw"
        / "databento"
        / "mbo"
        / f"symbol={symbol}"
        / f"date={day.isoformat()}"
        / "part-000.parquet"
    )


def out_path(data_root: Path, symbol: str, trading_day: dt.date) -> Path:
    return (
        data_root
        / "clean"
        / "databento"
        / "mbo_trading_day"
        / f"symbol={symbol}"
        / f"trading_day={trading_day.isoformat()}"
        / "part-000.parquet"
    )


def _sql_list(paths: list[Path]) -> str:
    items = []
    for path in paths:
        safe = path.as_posix().replace("'", "''")
        items.append(f"'{safe}'")
    return "[" + ", ".join(items) + "]"


def _sql_string(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _sql_kv_metadata(values: dict[str, object | None]) -> str:
    items = []
    for key, value in values.items():
        if value is None:
            continue
        items.append(f"{_sql_string(key)}: {_sql_string(value)}")
    return "{" + ", ".join(items) + "}"


def materialize_one(
    con: duckdb.DuckDBPyConnection,
    *,
    data_root: Path,
    symbol: str,
    trading_day: dt.date,
    overwrite: bool,
    allow_missing_sources: bool,
) -> dict[str, object]:
    period = globex_day_for_trading_date(trading_day)
    dates = calendar_dates_for_window(period.start_utc, period.end_utc)
    sources = [raw_path(data_root, symbol, day) for day in dates]
    missing = [p for p in sources if not p.exists()]
    destination = out_path(data_root, symbol, trading_day)

    row: dict[str, object] = {
        "symbol": symbol,
        "trading_day": trading_day.isoformat(),
        "start_utc": period.start_utc.isoformat(),
        "end_utc": period.end_utc.isoformat(),
        "source_partitions": ";".join(p.as_posix() for p in sources),
        "missing_partitions": ";".join(p.as_posix() for p in missing),
        "output": destination.as_posix(),
        "status": "pending",
        "rows": 0,
        "dropped_snapshot_rows": 0,
        "size_bytes": 0,
    }
    if missing and not allow_missing_sources:
        row["status"] = "missing_source"
        return row
    sources = [p for p in sources if p.exists()]
    if not sources:
        row["status"] = "missing_source"
        return row
    if destination.exists() and destination.stat().st_size > 0 and not overwrite:
        row["status"] = "exists"
        row["size_bytes"] = destination.stat().st_size
        row["rows"] = con.execute(
            "select count(*) from read_parquet(?)", [destination.as_posix()]
        ).fetchone()[0]
        return row

    destination.parent.mkdir(parents=True, exist_ok=True)
    source_list = _sql_list(sources)
    start_iso = period.start_utc.isoformat()
    end_iso = period.end_utc.isoformat()
    dest_sql = destination.as_posix().replace("'", "''")

    base_sql = f"""
        from read_parquet({source_list}, filename=true, union_by_name=true)
        where
            ts_event >= timestamp '{start_iso}'
            and ts_event < timestamp '{end_iso}'
            and ts_event >= cast(
                regexp_extract(filename, 'date=(\\d{{4}}-\\d{{2}}-\\d{{2}})', 1)
                || ' 00:00:00+00' as timestamptz
            )
            and ts_event < cast(
                regexp_extract(filename, 'date=(\\d{{4}}-\\d{{2}}-\\d{{2}})', 1)
                || ' 00:00:00+00' as timestamptz
            ) + interval 1 day
    """
    snapshot_sql = f"""
        select count(*)
        from read_parquet({source_list}, filename=true, union_by_name=true)
        where
            ts_event >= timestamp '{start_iso}'
            and ts_event < timestamp '{end_iso}'
            and (
                ts_event < cast(
                    regexp_extract(filename, 'date=(\\d{{4}}-\\d{{2}}-\\d{{2}})', 1)
                    || ' 00:00:00+00' as timestamptz
                )
                or ts_event >= cast(
                    regexp_extract(filename, 'date=(\\d{{4}}-\\d{{2}}-\\d{{2}})', 1)
                    || ' 00:00:00+00' as timestamptz
                ) + interval 1 day
            )
    """
    row["dropped_snapshot_rows"] = con.execute(snapshot_sql).fetchone()[0]
    row_count, ts_min, ts_max = con.execute(
        f"select count(*), min(ts_event), max(ts_event) {base_sql}"
    ).fetchone()
    row["rows"] = row_count
    metadata = _sql_kv_metadata(
        {
            "bs.source.kind": "clean-parquet",
            "bs.source.path": row["source_partitions"],
            "bs.generator.name": GENERATOR_NAME,
            "bs.generator.version": GENERATOR_VERSION,
            "bs.generator.timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "bs.row_count": row_count,
            "bs.schema.name": "mbo",
            "bs.schema.version": SCHEMA_VERSION,
            "bs.trading_day": trading_day.isoformat(),
            "bs.session.kind": "globex_trading_day",
            "bs.session.start_utc": period.start_utc.isoformat(),
            "bs.session.end_utc": period.end_utc.isoformat(),
            "bs.ts_event.min": ts_min.isoformat() if ts_min is not None else None,
            "bs.ts_event.max": ts_max.isoformat() if ts_max is not None else None,
            "bs.dropped_snapshot_rows": row["dropped_snapshot_rows"],
        }
    )
    con.execute(
        f"""
        copy (
            select * exclude(filename)
            {base_sql}
            order by ts_event, sequence
        )
        to '{dest_sql}'
        (format parquet, compression snappy, KV_METADATA {metadata})
        """
    )
    row["status"] = "written_missing_source" if missing else "written"
    row["size_bytes"] = destination.stat().st_size
    return row


def write_manifest(manifest: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    manifest.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with manifest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="first trading day, inclusive")
    parser.add_argument("--end", required=True, help="last trading day, inclusive")
    parser.add_argument("--symbols", nargs="+", default=list(SYMBOLS))
    parser.add_argument("--data-root", type=Path, default=warehouse_root())
    parser.add_argument("--manifest", type=Path)
    parser.add_argument(
        "--allow-missing-sources",
        action="store_true",
        help="Write from available source partitions and record missing ones in the manifest.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args(argv)

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    manifest = args.manifest or (
        args.data_root
        / "clean"
        / "databento"
        / "mbo_trading_day"
        / f"manifest_{start.isoformat()}_{end.isoformat()}.csv"
    )

    con = duckdb.connect()
    con.execute("set TimeZone='UTC'")
    con.execute(f"set threads={int(args.threads)}")

    rows: list[dict[str, object]] = []
    total = 0
    for trading_day in date_range(start, end):
        if trading_day.weekday() >= 5:
            continue
        for symbol in args.symbols:
            total += 1
            result = materialize_one(
                con,
                data_root=args.data_root,
                symbol=symbol,
                trading_day=trading_day,
                overwrite=args.overwrite,
                allow_missing_sources=args.allow_missing_sources,
            )
            rows.append(result)
            print(
                f"{result['status']:>14} {symbol:7s} {trading_day} "
                f"rows={result['rows']:,} "
                f"dropped_snapshot={result['dropped_snapshot_rows']:,}"
            )
            if total % 20 == 0:
                write_manifest(manifest, rows)

    write_manifest(manifest, rows)
    return 0 if all(r["status"] != "missing_source" for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
