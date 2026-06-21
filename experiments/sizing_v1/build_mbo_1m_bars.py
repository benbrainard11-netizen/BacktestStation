"""Build BacktestStation 1m bars from raw Databento MBO trade prints.

The standard parquet mirror emits 1m bars from TBBO/MBP-1/OHLCV, but not
from MBO. For Mira recent-window replay we need bars covering the same
recent dates as the MBO pull, so this derives OHLCV directly from
action == 'T' MBO records and writes:

    processed/bars/timeframe=1m/symbol=<SYM>/date=<YYYY-MM-DD>/part-000.parquet

Example:
    backend/.venv/Scripts/python.exe experiments/sizing_v1/build_mbo_1m_bars.py \
        --start 2026-05-23 --end 2026-06-05 --overwrite
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.paths import warehouse_root  # noqa: E402

DEFAULT_SYMBOLS = ("ES.c.0", "NQ.c.0", "RTY.c.0", "YM.c.0")


def date_range(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)


def split_symbols(value: str) -> list[str]:
    return [part.strip() for part in value.replace(" ", ",").split(",") if part.strip()]


def raw_mbo_path(data_root: Path, symbol: str, day: dt.date) -> Path:
    return data_root / "raw" / "databento" / "mbo" / f"symbol={symbol}" / f"date={day.isoformat()}" / "part-000.parquet"


def bars_path(data_root: Path, symbol: str, day: dt.date) -> Path:
    return data_root / "processed" / "bars" / "timeframe=1m" / f"symbol={symbol}" / f"date={day.isoformat()}" / "part-000.parquet"


def sql_string(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def build_one(con: duckdb.DuckDBPyConnection, *, data_root: Path, symbol: str, day: dt.date, overwrite: bool) -> dict[str, object]:
    source = raw_mbo_path(data_root, symbol, day)
    dest = bars_path(data_root, symbol, day)
    row: dict[str, object] = {
        "symbol": symbol,
        "date": day.isoformat(),
        "source": source.as_posix(),
        "output": dest.as_posix(),
        "status": "pending",
        "rows": 0,
        "source_bytes": source.stat().st_size if source.exists() else 0,
        "output_bytes": 0,
    }
    if not source.exists() or source.stat().st_size == 0:
        row["status"] = "missing_source"
        return row
    if dest.exists() and dest.stat().st_size > 0 and not overwrite:
        row["status"] = "exists"
        row["rows"] = con.execute("select count(*) from read_parquet(?)", [dest.as_posix()]).fetchone()[0]
        row["output_bytes"] = dest.stat().st_size
        return row

    dest.parent.mkdir(parents=True, exist_ok=True)
    source_sql = sql_string(source.as_posix())
    dest_sql = dest.as_posix().replace("'", "''")
    symbol_sql = sql_string(symbol)
    query = f"""
        with trades as (
            select
                ts_event,
                cast(price as double) as price,
                cast(size as ubigint) as size,
                cast(coalesce(sequence, 0) as ubigint) as sequence
            from read_parquet({source_sql})
            where action = 'T'
              and price is not null
              and isfinite(cast(price as double))
              and cast(price as double) > 0
        ),
        bars as (
            select
                date_trunc('minute', ts_event) as ts_event,
                {symbol_sql}::varchar as symbol,
                first(price order by ts_event, sequence) as open,
                max(price) as high,
                min(price) as low,
                last(price order by ts_event, sequence) as close,
                cast(sum(size) as ubigint) as volume,
                cast(count(*) as uinteger) as trade_count,
                sum(price * size) / nullif(sum(size), 0) as vwap
            from trades
            group by 1, 2
        )
        select *
        from bars
        order by ts_event
    """
    count = con.execute(f"select count(*) from ({query})").fetchone()[0]
    if count == 0:
        row["status"] = "empty_trades"
        return row
    con.execute(
        f"""
        copy ({query})
        to '{dest_sql}'
        (format parquet, compression zstd)
        """
    )
    row["status"] = "written"
    row["rows"] = count
    row["output_bytes"] = dest.stat().st_size
    return row


def write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=dt.date.fromisoformat)
    parser.add_argument("--end", required=True, type=dt.date.fromisoformat)
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--data-root", type=Path, default=warehouse_root())
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    if args.end < args.start:
        parser.error("--end must be on or after --start")
    symbols = split_symbols(args.symbols)
    manifest = args.manifest or (
        args.data_root
        / "processed"
        / "bars"
        / "timeframe=1m"
        / f"mbo_bars_manifest_{args.start.isoformat()}_{args.end.isoformat()}.csv"
    )

    con = duckdb.connect()
    con.execute("set TimeZone='UTC'")
    con.execute(f"set threads={int(args.threads)}")

    rows: list[dict[str, object]] = []
    for day in date_range(args.start, args.end):
        for symbol in symbols:
            result = build_one(con, data_root=args.data_root, symbol=symbol, day=day, overwrite=args.overwrite)
            rows.append(result)
            print(f"{result['status']:>14} {symbol:7s} {day} rows={int(result['rows']):,}")
            if len(rows) % 20 == 0:
                write_manifest(manifest, rows)
    write_manifest(manifest, rows)

    bad = [row for row in rows if row["status"] not in {"written", "exists", "missing_source", "empty_trades"}]
    print(f"manifest -> {manifest}")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
