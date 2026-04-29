"""Runner: the I/O layer around the pure engine.

Responsibilities (kept OUT of `engine.py` per CLAUDE.md §1 — engine
is pure):

  - Load bars via `app.data.read_bars`
  - Convert to Bar dataclasses for the engine
  - Call `engine.run(...)`
  - Serialize the result:
      data/backtests/strategy={name}/run={ts}_{id}/
        config.json
        trades.parquet
        equity.parquet
        events.parquet
        metrics.json
  - Insert a `BacktestRun` row in the SQLite metadata DB so the run
    appears in the Strategy Workstation UI alongside imported runs.

Determinism: the run output sequences are deterministic. The directory
name and the started_at timestamp in config.json are not — but those
don't affect the byte-equality of trades.parquet / equity.parquet /
events.parquet / metrics.json. Tests pin to the byte-equality of the
data files.

CLI:
    python -m app.backtest.runner \\
        --strategy moving_average_crossover \\
        --symbol NQ.c.0 \\
        --start 2026-04-20 --end 2026-04-25 \\
        --strategy-version-id 5
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from app.backtest import ENGINE_VERSION
from app.backtest.engine import BacktestResult, RunConfig, run as engine_run
from app.backtest.orders import Trade
from app.backtest.strategy import Bar, Strategy
from app.data import read_bars
from app.db.models import (
    BacktestRun,
    ConfigSnapshot,
    EquityPoint as EquityPointModel,
    RunMetrics,
    Trade as TradeModel,
)
from app.db.session import (
    create_all,
    get_session,
    make_engine,
    make_session_factory,
)
from sqlalchemy.orm import Session


# --- Strategy resolution ----------------------------------------------


def _resolve_strategy(name: str, params: dict, config: RunConfig) -> Strategy:
    """Map a strategy name to its class + instantiate.

    Kept as a small lookup for v1; will become a registry once there
    are more than a couple of strategies."""
    if name == "moving_average_crossover":
        from app.strategies.examples.moving_average_crossover import (
            MovingAverageCrossover,
        )

        return MovingAverageCrossover.from_config(
            params, tick_size=config.tick_size, qty=config.qty
        )
    if name == "fractal_amd":
        from app.strategies.fractal_amd import FractalAMD

        return FractalAMD.from_config(
            params, tick_size=config.tick_size, qty=config.qty
        )
    if name == "fractal_amd_trusted":
        from app.strategies.fractal_amd_trusted import FractalAMDTrusted

        return FractalAMDTrusted.from_config(
            params, tick_size=config.tick_size, qty=config.qty
        )
    if name == "composable":
        from app.strategies.composable import ComposableStrategy

        strat = ComposableStrategy.from_config(
            params, tick_size=config.tick_size, qty=config.qty
        )
        # Composable needs to know which aux symbols to track. RunConfig
        # carries them; we set them explicitly so the plugin's
        # aux_history mirrors the engine's aux_bars dict.
        strat.aux_symbols = tuple(config.aux_symbols)
        strat.aux_history = {sym: [] for sym in config.aux_symbols}
        return strat
    raise ValueError(
        f"unknown strategy {name!r}; add a branch in runner._resolve_strategy"
    )


# --- Bar loading -------------------------------------------------------


def load_bars(config: RunConfig) -> list[Bar]:
    """Read primary bars from the warehouse and convert to Bar dataclasses."""
    return _read_symbol_bars(
        symbol=config.symbol,
        timeframe=config.timeframe,
        start=config.start,
        end=config.end,
    )


def load_aux_bars(
    config: RunConfig,
) -> dict[str, dict[dt.datetime, Bar]]:
    """Read each aux symbol's bars and index by ts_event.

    Returns `{symbol: {ts_event: Bar}}`. Missing symbols (no data)
    return an empty inner dict, which the engine treats as
    "always None at every minute".
    """
    out: dict[str, dict[dt.datetime, Bar]] = {}
    for sym in config.aux_symbols:
        bars = _read_symbol_bars(
            symbol=sym,
            timeframe=config.timeframe,
            start=config.start,
            end=config.end,
        )
        out[sym] = {b.ts_event: b for b in bars}
    return out


def _read_symbol_bars(
    *, symbol: str, timeframe: str, start: str, end: str
) -> list[Bar]:
    df = read_bars(
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        as_pandas=True,
    )
    if df is None or len(df) == 0:
        return []

    bars: list[Bar] = []
    for row in df.itertuples(index=False):
        ts = row.ts_event
        # Pandas may give Timestamp; Bar wants datetime. tz-aware UTC either way.
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()
        bars.append(
            Bar(
                ts_event=ts,
                symbol=row.symbol,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=int(row.volume),
                trade_count=int(row.trade_count),
                vwap=float(row.vwap),
            )
        )
    return bars


# --- Output paths ------------------------------------------------------


def _data_root() -> Path:
    default = "C:/data" if os.name == "nt" else "./data"
    return Path(os.environ.get("BS_DATA_ROOT", default))


def make_run_dir(
    data_root: Path, strategy_name: str, started_at: dt.datetime
) -> tuple[Path, str]:
    """Build the per-run output directory. Returns (path, run_id)."""
    run_id = uuid.uuid4().hex[:8]
    stamp = started_at.strftime("%Y-%m-%dT%H-%M-%S")
    name = f"{stamp}_{run_id}"
    path = (
        data_root
        / "backtests"
        / f"strategy={strategy_name}"
        / f"run={name}"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path, run_id


# --- Serialization -----------------------------------------------------


def _git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return None


def write_run(
    out_dir: Path,
    result: BacktestResult,
    started_at: dt.datetime,
    completed_at: dt.datetime,
    git_sha: str | None,
) -> None:
    # config.json — full config snapshot + reproducibility metadata.
    config_payload = {
        **asdict(result.config),
        "engine_version": ENGINE_VERSION,
        "git_sha": git_sha,
        "started_at": started_at.isoformat(timespec="seconds"),
        "completed_at": completed_at.isoformat(timespec="seconds"),
    }
    (out_dir / "config.json").write_text(
        json.dumps(config_payload, indent=2, default=str), encoding="utf-8"
    )

    # trades.parquet
    trade_table = _trades_to_table(result.trades)
    pq.write_table(trade_table, out_dir / "trades.parquet", compression="zstd")

    # equity.parquet
    equity_table = _equity_to_table(result.equity_points)
    pq.write_table(
        equity_table, out_dir / "equity.parquet", compression="zstd"
    )

    # events.parquet
    events_table = _events_to_table(result.events)
    pq.write_table(
        events_table, out_dir / "events.parquet", compression="zstd"
    )

    # metrics.json
    (out_dir / "metrics.json").write_text(
        json.dumps(result.metrics, indent=2), encoding="utf-8"
    )


def _trades_to_table(trades: list) -> pa.Table:
    rows = [
        {
            "entry_ts": t.entry_ts,
            "exit_ts": t.exit_ts,
            "side": t.side.value,
            "qty": t.qty,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "stop_price": t.stop_price,
            "target_price": t.target_price,
            "pnl": t.pnl,
            "r_multiple": t.r_multiple,
            "exit_reason": t.exit_reason,
            "fill_confidence": t.fill_confidence,
        }
        for t in trades
    ]
    if not rows:
        # Empty trades is valid; still produce a typed empty table.
        schema = pa.schema(
            [
                ("entry_ts", pa.timestamp("ns", tz="UTC")),
                ("exit_ts", pa.timestamp("ns", tz="UTC")),
                ("side", pa.string()),
                ("qty", pa.int64()),
                ("entry_price", pa.float64()),
                ("exit_price", pa.float64()),
                ("stop_price", pa.float64()),
                ("target_price", pa.float64()),
                ("pnl", pa.float64()),
                ("r_multiple", pa.float64()),
                ("exit_reason", pa.string()),
                ("fill_confidence", pa.string()),
            ]
        )
        return schema.empty_table()
    return pa.Table.from_pylist(rows)


def _equity_to_table(equity_points: list) -> pa.Table:
    rows = [
        {"ts": p.ts, "equity": p.equity, "drawdown": p.drawdown}
        for p in equity_points
    ]
    if not rows:
        return pa.schema(
            [
                ("ts", pa.timestamp("ns", tz="UTC")),
                ("equity", pa.float64()),
                ("drawdown", pa.float64()),
            ]
        ).empty_table()
    return pa.Table.from_pylist(rows)


def _events_to_table(events: list) -> pa.Table:
    rows = [
        {
            "ts": e.ts,
            "type": e.type.value,
            "bar_index": e.bar_index,
            "payload_json": json.dumps(e.payload, default=str),
        }
        for e in events
    ]
    if not rows:
        return pa.schema(
            [
                ("ts", pa.timestamp("ns", tz="UTC")),
                ("type", pa.string()),
                ("bar_index", pa.int64()),
                ("payload_json", pa.string()),
            ]
        ).empty_table()
    return pa.Table.from_pylist(rows)


# --- DB integration ----------------------------------------------------


def persist_run_to_session(
    session: Session,
    config: RunConfig,
    result: BacktestResult,
    out_dir: Path | None,
    strategy_version_id: int,
) -> int:
    """Insert BacktestRun + trades/equity/metrics/config into the given session.

    Caller owns the session lifecycle and the commit. Returns the new run id.
    Used by both `insert_db_row` (CLI / standalone) and the `POST
    /api/backtests/run` endpoint (which passes its own FastAPI session).
    """
    run = BacktestRun(
        strategy_version_id=strategy_version_id,
        name=f"{config.strategy_name} {config.start}..{config.end}",
        symbol=config.symbol,
        timeframe=config.timeframe,
        start_ts=_iso_to_dt(config.start),
        end_ts=_iso_to_dt(config.end),
        import_source=str(out_dir) if out_dir is not None else None,
        source="engine",
        status="complete",
    )
    session.add(run)
    session.flush()  # populate run.id

    for t in result.trades:
        session.add(
            TradeModel(
                backtest_run_id=run.id,
                entry_ts=_strip_tz(t.entry_ts),
                exit_ts=_strip_tz(t.exit_ts),
                symbol=config.symbol,
                side=t.side.value,
                entry_price=t.entry_price,
                exit_price=t.exit_price,
                stop_price=t.stop_price,
                target_price=t.target_price,
                size=float(t.qty),
                pnl=t.pnl,
                r_multiple=t.r_multiple,
                exit_reason=t.exit_reason,
            )
        )
    for p in result.equity_points:
        session.add(
            EquityPointModel(
                backtest_run_id=run.id,
                ts=_strip_tz(p.ts),
                equity=p.equity,
                drawdown=p.drawdown,
            )
        )
    if result.metrics:
        m = result.metrics
        session.add(
            RunMetrics(
                backtest_run_id=run.id,
                net_pnl=m.get("net_pnl"),
                net_r=m.get("net_r"),
                win_rate=m.get("win_rate"),
                profit_factor=m.get("profit_factor"),
                max_drawdown=m.get("max_drawdown"),
                avg_r=m.get("avg_r"),
                avg_win=m.get("avg_win"),
                avg_loss=m.get("avg_loss"),
                trade_count=m.get("trade_count"),
                longest_losing_streak=m.get("longest_losing_streak"),
                best_trade=m.get("best_trade"),
                worst_trade=m.get("worst_trade"),
            )
        )
    session.add(
        ConfigSnapshot(
            backtest_run_id=run.id,
            payload={**asdict(config), "engine_version": ENGINE_VERSION},
        )
    )
    return run.id


def insert_db_row(
    config: RunConfig,
    result: BacktestResult,
    out_dir: Path,
    strategy_version_id: int,
    db_url: str | None = None,
) -> int:
    """Insert a BacktestRun + child rows. Standalone wrapper around
    `persist_run_to_session` that opens its own session against the
    configured DB. Used by the CLI runner."""
    if db_url is None:
        engine = make_engine()
    else:
        engine = make_engine(db_url)
    create_all(engine)
    factory = make_session_factory(engine)
    with factory() as session:
        run_id = persist_run_to_session(
            session, config, result, out_dir, strategy_version_id
        )
        session.commit()
        return run_id


def _iso_to_dt(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value).replace(tzinfo=dt.timezone.utc)


def _strip_tz(value: Any) -> dt.datetime:
    """SQLAlchemy DateTime columns in this repo are tz-naive — strip tz."""
    if isinstance(value, dt.datetime):
        if value.tzinfo is not None:
            return value.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return value
    return value


# --- Entry points ------------------------------------------------------


def run_backtest(
    config: RunConfig,
    *,
    strategy_version_id: int | None = None,
    persist: bool = True,
    db_url: str | None = None,
) -> tuple[BacktestResult, Path | None, int | None]:
    """Run a backtest end-to-end. Returns (result, out_dir, run_id).

    If `persist=False`, no files are written and no DB row inserted —
    used by tests. If `strategy_version_id` is None, no DB row is
    inserted either (file outputs only).
    """
    started_at = dt.datetime.now(dt.timezone.utc)
    bars = load_bars(config)
    aux_bars = load_aux_bars(config)
    strategy = _resolve_strategy(config.strategy_name, config.params, config)
    result = engine_run(strategy, bars, config, aux_bars=aux_bars)
    completed_at = dt.datetime.now(dt.timezone.utc)

    out_dir: Path | None = None
    run_id: int | None = None
    if persist:
        out_dir, _ = make_run_dir(_data_root(), config.strategy_name, started_at)
        write_run(out_dir, result, started_at, completed_at, _git_sha())
        if strategy_version_id is not None:
            run_id = insert_db_row(
                config, result, out_dir, strategy_version_id, db_url=db_url
            )
    return result, out_dir, run_id


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run a backtest engine v1")
    p.add_argument("--strategy", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--timeframe", default="1m")
    p.add_argument("--qty", type=int, default=1)
    p.add_argument("--initial-equity", type=float, default=25_000.0)
    p.add_argument(
        "--strategy-version-id",
        type=int,
        default=None,
        help="If set, inserts a BacktestRun row in the metadata DB.",
    )
    p.add_argument(
        "--params",
        type=str,
        default="{}",
        help="JSON string of strategy-specific params.",
    )
    args = p.parse_args(argv)

    config = RunConfig(
        strategy_name=args.strategy,
        symbol=args.symbol,
        timeframe=args.timeframe,
        start=args.start,
        end=args.end,
        initial_equity=args.initial_equity,
        qty=args.qty,
        params=json.loads(args.params),
    )
    result, out_dir, run_id = run_backtest(
        config, strategy_version_id=args.strategy_version_id
    )

    print(f"trades={len(result.trades)} net_pnl={result.metrics['net_pnl']:.2f}")
    if out_dir:
        print(f"output: {out_dir}")
    if run_id:
        print(f"db_run_id: {run_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
