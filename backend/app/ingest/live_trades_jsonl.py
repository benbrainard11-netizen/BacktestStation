"""One-shot importer for the live bot's trades.jsonl.

The Fractal AMD live bot (FractalAMD-/production/live_bot.py on
ben-247) appends one JSON record per closed trade to
`production/trades.jsonl`. This module reads that file and lands the
trades in BacktestStation's metadata DB as a single
BacktestRun(source="live") so they show up in /backtests alongside
engine and imported runs.

Idempotency is via run replacement: each invocation looks for a
prior live run for the same JSONL path and deletes it (cascade clears
children) before creating a fresh one with all current trades. So you
can re-run the importer N times as the bot accumulates trades without
duplicating anything.

CLI:
    python -m app.ingest.live_trades_jsonl \
        --jsonl C:/Users/benbr/FractalAMD-/production/trades.jsonl \
        --strategy-version-id 1 \
        --symbol NQ.c.0

Live JSONL record schema (per live_bot.py:1072-1090 as of 2026-04-12):
    date, entry_time (HH:MM:SS), direction (BULLISH/BEARISH), symbol
    (NQM6/MNQM6), contracts, entry_price, exit_price, stop, target,
    risk (points), risk_dollars, rof_score, exit_reason, pnl_r,
    pnl_dollars, order_id, basket_id

Schema gap: NO exit_time. The bot only records entry_time. We leave
exit_ts as None on the imported Trade rows; the dossier UI handles
this gracefully.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db.models import (
    BacktestRun,
    ConfigSnapshot,
    Trade,
)
from app.db.session import (
    create_all,
    make_engine,
    make_session_factory,
)


ET = ZoneInfo("America/New_York")
RUN_NAME_PREFIX = "live (jsonl):"


@dataclass(frozen=True)
class ParsedTrade:
    """Validated trade record after parsing one JSONL line.

    Many fields are optional to support multiple live-bot schema
    versions. The bot's schema is additive (v1 omits exit_time / FVG
    context; v2 adds them) -- the importer fills nulls when fields
    are absent.
    """

    entry_ts: dt.datetime  # tz-naive UTC
    side: str  # "long" | "short"
    symbol: str
    contracts: int
    entry_price: float
    exit_price: float
    stop_price: float
    target_price: float
    pnl_dollars: float | None
    pnl_r: float
    exit_reason: str
    order_id: str
    basket_id: str
    exit_ts: dt.datetime | None = None  # v2+: parsed from exit_time
    session_label: str | None = None  # v2+: Globex session bucket


def parse_record(record: dict, tz: ZoneInfo = ET) -> ParsedTrade | None:
    """Convert one raw JSONL dict to a ParsedTrade. Returns None if invalid.

    Required fields: date, entry_time, direction, entry_price,
    exit_price, stop, target, pnl_r. Older live-bot builds don't emit
    symbol / contracts / pnl_dollars / risk_dollars -- those are
    treated as optional with sensible defaults.

    `tz` is the wall-clock timezone the live bot writes its
    entry_time / exit_time fields in. Default is ET — verified by
    aligning live entry prices against historical 1m bars (a 09:31
    record for 2026-04-22 with entry_price=26868.75 matches the
    13:31 UTC bar's open exactly, i.e. 09:31 EDT). Pass UTC if the
    bot ever switches to writing tz-explicit ISO 8601.
    """
    required = (
        "date",
        "entry_time",
        "direction",
        "entry_price",
        "exit_price",
        "stop",
        "target",
        "pnl_r",
    )
    if any(k not in record for k in required):
        return None

    direction = str(record["direction"]).upper()
    if direction == "BULLISH":
        side = "long"
    elif direction == "BEARISH":
        side = "short"
    else:
        return None

    # date is YYYY-MM-DD, entry_time is HH:MM:SS — both written by
    # the live bot's `trade.entry_time.strftime("%H:%M:%S")` without
    # explicit tz tagging. The literal value is wall-clock in `tz`
    # (default ET). Re-verified 2026-04-26: a 2026-04-22 09:31:00 /
    # 26868.75 BEARISH live trade matches the 13:31 UTC bar's open
    # exactly, i.e. 09:31 EDT. Localize then convert to UTC, store
    # tz-naive UTC for the SQLAlchemy DateTime column.
    entry_local = dt.datetime.fromisoformat(
        f"{record['date']}T{record['entry_time']}"
    ).replace(tzinfo=tz)
    entry_ts = entry_local.astimezone(dt.timezone.utc).replace(tzinfo=None)

    pnl_dollars: float | None = None
    if "pnl_dollars" in record and record["pnl_dollars"] is not None:
        pnl_dollars = float(record["pnl_dollars"])

    # v2+ fields (live_bot schema_version "live_bot_v2"). Parser is
    # forgiving: malformed exit_time -> None rather than skipping the
    # whole record.
    exit_ts: dt.datetime | None = None
    raw_exit = record.get("exit_time")
    if raw_exit:
        try:
            exit_dt = dt.datetime.fromisoformat(str(raw_exit))
            # Same convention as entry_time: bot writes wall-clock in
            # `tz` (default ET), no explicit tz on the string. If the
            # string IS tz-aware (forward-compatible with future bot
            # builds), trust the tag.
            if exit_dt.tzinfo is None:
                exit_dt = exit_dt.replace(tzinfo=tz)
            exit_ts = exit_dt.astimezone(dt.timezone.utc).replace(tzinfo=None)
        except (ValueError, TypeError):
            exit_ts = None

    session_label: str | None = None
    if "session_label" in record and record["session_label"] is not None:
        session_label = str(record["session_label"])

    return ParsedTrade(
        entry_ts=entry_ts,
        side=side,
        symbol=str(record.get("symbol", "")),
        contracts=int(record.get("contracts", 1)),
        entry_price=float(record["entry_price"]),
        exit_price=float(record["exit_price"]),
        stop_price=float(record["stop"]),
        target_price=float(record["target"]),
        pnl_dollars=pnl_dollars,
        pnl_r=float(record["pnl_r"]),
        exit_reason=str(record.get("exit_reason", "")),
        order_id=str(record.get("order_id", "")),
        basket_id=str(record.get("basket_id", "")),
        exit_ts=exit_ts,
        session_label=session_label,
    )


def read_jsonl(
    path: Path, logger: logging.Logger, tz: ZoneInfo = ET
) -> list[ParsedTrade]:
    """Read trades.jsonl. Skips malformed lines (logged); returns parsed trades."""
    trades: list[ParsedTrade] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(f"line {line_no}: not valid JSON ({e})")
                continue
            parsed = parse_record(record, tz=tz)
            if parsed is None:
                logger.warning(
                    f"line {line_no}: missing required field or unknown direction"
                )
                continue
            trades.append(parsed)
    return trades


def import_jsonl(
    jsonl_path: Path,
    *,
    strategy_version_id: int,
    symbol: str,
    db_url: str | None = None,
    logger: logging.Logger | None = None,
    tz: ZoneInfo = ET,
) -> tuple[int, int]:
    """Read jsonl_path and replace any prior live run for it. Returns
    (run_id, trade_count).

    `tz` is the wall-clock timezone the live bot's JSONL records use
    (default ET). See `parse_record` for the rationale.
    """
    log = logger or logging.getLogger("live_trades_jsonl")

    trades = read_jsonl(jsonl_path, log, tz=tz)
    log.info(f"parsed {len(trades)} trades from {jsonl_path}")

    engine = make_engine(db_url) if db_url else make_engine()
    create_all(engine)
    factory = make_session_factory(engine)

    run_name = f"{RUN_NAME_PREFIX} {jsonl_path.name}"

    with factory() as session:
        # Idempotency: nuke any prior import for this jsonl. Use the
        # shared run-deletion helper so we honor FK enforcement (notes,
        # baselines, prop-firm sims pointing at the prior run all get
        # cleaned up the same way the API DELETE endpoint does).
        from app.services.run_deletion import delete_run as _delete_run_with_cleanup

        prior = session.scalars(
            select(BacktestRun).where(
                BacktestRun.name == run_name,
                BacktestRun.source == "live",
            )
        ).all()
        for run in prior:
            _delete_run_with_cleanup(session, run)
        if prior:
            log.info(f"replaced {len(prior)} prior live run(s) for this jsonl")
            session.flush()

        if not trades:
            session.commit()
            return 0, 0

        first = min(t.entry_ts for t in trades)
        last = max(t.entry_ts for t in trades)

        run = BacktestRun(
            strategy_version_id=strategy_version_id,
            name=run_name,
            symbol=symbol,
            timeframe="1m",
            start_ts=first,
            end_ts=last,
            import_source=str(jsonl_path),
            source="live",
            status="complete",
        )
        session.add(run)
        session.flush()

        for t in trades:
            session.add(
                Trade(
                    backtest_run_id=run.id,
                    entry_ts=t.entry_ts,
                    exit_ts=t.exit_ts,  # v2+ live-bot schema; None for v1 records
                    symbol=symbol,
                    side=t.side,
                    entry_price=t.entry_price,
                    exit_price=t.exit_price,
                    stop_price=t.stop_price,
                    target_price=t.target_price,
                    size=float(t.contracts),
                    pnl=t.pnl_dollars,  # may be None for older live-bot builds
                    r_multiple=t.pnl_r,
                    exit_reason=t.exit_reason or None,
                )
            )

        session.add(
            ConfigSnapshot(
                backtest_run_id=run.id,
                payload={
                    "import_kind": "live_trades_jsonl",
                    "jsonl_path": str(jsonl_path),
                    "trade_count": len(trades),
                    "first_trade_ts": first.isoformat(),
                    "last_trade_ts": last.isoformat(),
                    "schema_version": "live_bot_v1",
                },
            )
        )

        session.commit()
        log.info(
            f"imported run id={run.id} trades={len(trades)} "
            f"({first.isoformat()} .. {last.isoformat()})"
        )
        return run.id, len(trades)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="One-shot import of the live bot's trades.jsonl into BacktestStation."
    )
    p.add_argument(
        "--jsonl",
        required=True,
        type=Path,
        help="Path to trades.jsonl (e.g. C:/Users/benbr/FractalAMD-/production/trades.jsonl)",
    )
    p.add_argument(
        "--strategy-version-id",
        required=True,
        type=int,
        help="StrategyVersion FK -- the run will be associated with this version.",
    )
    p.add_argument(
        "--symbol",
        default="NQ.c.0",
        help="Symbol to record on the BacktestRun + each Trade row (default: NQ.c.0).",
    )
    p.add_argument(
        "--time-zone",
        default="America/New_York",
        help=(
            "IANA tz name the live bot writes wall-clock entry_time / "
            "exit_time in. Default America/New_York (ET). The importer "
            "localizes-then-converts to UTC for storage. Override with "
            "UTC if a future bot build emits explicit-UTC strings."
        ),
    )
    args = p.parse_args(argv)
    try:
        bot_tz = ZoneInfo(args.time_zone)
    except Exception as exc:
        sys.stderr.write(f"invalid --time-zone {args.time_zone!r}: {exc}\n")
        return 1

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    log = logging.getLogger("live_trades_jsonl")

    if not args.jsonl.exists():
        log.error(f"jsonl not found: {args.jsonl}")
        return 1

    run_id, count = import_jsonl(
        args.jsonl,
        strategy_version_id=args.strategy_version_id,
        symbol=args.symbol,
        logger=log,
        tz=bot_tz,
    )
    print(f"run_id={run_id} trades={count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
