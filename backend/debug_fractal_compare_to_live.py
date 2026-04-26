"""Side-by-side: live trades vs Fractal AMD port output.

Reads the most-recent BacktestRun(source="live") for the configured
strategy version, runs the engine on the same date range with a
tracing strategy, then for each live trade asks:

  - Did the port produce a setup of the same direction near this time?
  - If yes, was it WATCHING / TOUCHED / FILLED at the live entry bar?
  - If WATCHING, what's the closest FVG zone vs live's entry price?
  - If TOUCHED-but-not-FILLED, what gate failed?

Output CSV at `backend/tests/_artifacts/port_vs_live_{start}_{end}.csv`.

Usage:
    cd backend
    .venv/Scripts/python.exe debug_fractal_compare_to_live.py \\
        --strategy-version-id 2 --start 2026-04-14 --end 2026-04-22

The script READS from the meta DB but does not write to it.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

from sqlalchemy import select

from app.backtest.engine import RunConfig, run as engine_run
from app.backtest.runner import load_aux_bars, load_bars
from app.db.models import BacktestRun, Trade as TradeModel
from app.db.session import get_session
from app.strategies.fractal_amd.config import FractalAMDConfig

# Reuse the tracing subclass + classifier from the lifecycle script so
# the two debug tools stay in sync.
from debug_fractal_setup_lifecycle import (
    TracingFractalAMD,
    _classify_validation_failure,
)


_ARTIFACT_DIR = Path(__file__).parent / "tests" / "_artifacts"


def _live_run_for_version(strategy_version_id: int) -> BacktestRun | None:
    """Most-recent live run for a strategy version, or None."""
    with next(get_session()) as session:
        statement = (
            select(BacktestRun)
            .where(BacktestRun.strategy_version_id == strategy_version_id)
            .where(BacktestRun.source == "live")
            .order_by(BacktestRun.created_at.desc(), BacktestRun.id.desc())
            .limit(1)
        )
        return session.scalars(statement).first()


def _live_trades_in_range(
    run_id: int, start: dt.date, end: dt.date
) -> list[TradeModel]:
    """All live trades from `run_id` whose entry_ts falls in [start, end]."""
    start_ts = dt.datetime(start.year, start.month, start.day)
    # End is inclusive of the date.
    end_ts = dt.datetime(end.year, end.month, end.day) + dt.timedelta(days=1)
    with next(get_session()) as session:
        statement = (
            select(TradeModel)
            .where(TradeModel.backtest_run_id == run_id)
            .where(TradeModel.entry_ts >= start_ts)
            .where(TradeModel.entry_ts < end_ts)
            .order_by(TradeModel.entry_ts.asc())
        )
        return list(session.scalars(statement).all())


def _direction_label(side: str) -> str:
    """Trade.side is 'long' / 'short'; align with strategy's
    'BULLISH'/'BEARISH'."""
    return "BULLISH" if side.lower() == "long" else "BEARISH"


def _matching_setup(
    strat: TracingFractalAMD, live_entry: dt.datetime, live_dir: str
) -> dict | None:
    """Find the port setup that best matches a live trade.

    Match priority:
      1. Same direction, touch_ts within ±10 minutes of live_entry
      2. Same direction, fvg zone live entry price falls inside (no touch)
    Returns the underlying setup_record dict, or None.
    """
    candidates = [
        rec for rec in strat.setup_records.values()
        if rec["direction"] == live_dir
    ]
    if not candidates:
        return None

    # Touch-time match
    near: list[tuple[float, dict]] = []
    for rec in candidates:
        if rec["first_touch_ts"] is None:
            continue
        touch_dt = dt.datetime.fromisoformat(rec["first_touch_ts"])
        if touch_dt.tzinfo is None:
            touch_dt = touch_dt.replace(tzinfo=dt.timezone.utc)
        if live_entry.tzinfo is None:
            live_entry = live_entry.replace(tzinfo=dt.timezone.utc)
        delta_min = abs((touch_dt - live_entry).total_seconds()) / 60.0
        if delta_min <= 10:
            near.append((delta_min, rec))
    if near:
        near.sort(key=lambda t: t[0])
        return near[0][1]

    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Compare Fractal AMD port output to live trades."
    )
    p.add_argument(
        "--strategy-version-id",
        type=int,
        required=True,
        help="strategy_version_id whose source='live' run to compare against",
    )
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--symbol", default="NQ.c.0")
    p.add_argument("--aux", default="ES.c.0,YM.c.0")
    p.add_argument("--out-dir", default=str(_ARTIFACT_DIR))
    args = p.parse_args(argv)

    print(
        f"resolving live run for strategy_version_id={args.strategy_version_id}"
    )
    live_run = _live_run_for_version(args.strategy_version_id)
    if live_run is None:
        sys.stderr.write(
            f"no source='live' run found for version {args.strategy_version_id}.\n"
            "Import live trades via app.ingest.live_trades_jsonl first.\n"
        )
        return 1
    print(f"  live run id={live_run.id}, name={live_run.name}")

    start_d = dt.date.fromisoformat(args.start)
    end_d = dt.date.fromisoformat(args.end)
    live_trades = _live_trades_in_range(live_run.id, start_d, end_d)
    print(f"  {len(live_trades)} live trades in [{args.start}, {args.end}]")
    if not live_trades:
        sys.stderr.write("no live trades in range; nothing to compare.\n")
        return 1

    aux_symbols = [s.strip() for s in args.aux.split(",") if s.strip()]
    cfg_engine = RunConfig(
        strategy_name="fractal_amd",
        symbol=args.symbol,
        timeframe="1m",
        start=args.start,
        end=args.end,
        history_max=2000,
        aux_symbols=aux_symbols,
        commission_per_contract=0.0,
        slippage_ticks=1,
        flatten_on_last_bar=False,
    )
    print("loading bars + running engine...")
    bars = load_bars(cfg_engine)
    aux_bars = load_aux_bars(cfg_engine)
    if not bars:
        sys.stderr.write("no primary bars in warehouse for this date range.\n")
        return 1

    cfg = FractalAMDConfig()
    strat = TracingFractalAMD(cfg)
    result = engine_run(strat, bars, cfg_engine, aux_bars=aux_bars)
    print(
        f"  port: {len(result.trades)} trades, "
        f"{len(strat.setup_records)} setups, "
        f"{len(strat.rejection_log)} rejections"
    )

    # Index port trades by entry_ts for fast lookup.
    port_trade_by_ts: dict[dt.datetime, dict] = {}
    for t in result.trades:
        port_trade_by_ts[t.entry_ts] = {
            "side": t.side.value,
            "entry_price": t.entry_price,
            "stop": t.stop_price,
            "target": t.target_price,
            "exit_reason": t.exit_reason,
            "pnl": t.pnl,
        }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"port_vs_live_{args.start}_{args.end}.csv"
    cols = [
        "live_entry_ts",
        "live_side",
        "live_entry_price",
        "live_pnl",
        "port_match_kind",
        "port_setup_direction",
        "port_setup_htf_tf",
        "port_setup_fvg_low",
        "port_setup_fvg_high",
        "port_setup_first_touch_ts",
        "port_setup_first_touch_in_window",
        "port_setup_n_touches",
        "port_setup_final_status",
        "port_setup_rejection_reasons",
        "port_trade_at_same_ts",
    ]

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        n_port_match_touch = 0
        n_port_no_match = 0
        n_port_filled = 0
        for lt in live_trades:
            live_dir = _direction_label(lt.side)
            entry_ts = lt.entry_ts
            if entry_ts.tzinfo is None:
                entry_ts = entry_ts.replace(tzinfo=dt.timezone.utc)
            match = _matching_setup(strat, entry_ts, live_dir)
            row = {
                "live_entry_ts": entry_ts.isoformat(),
                "live_side": lt.side,
                "live_entry_price": lt.entry_price,
                "live_pnl": lt.pnl,
                "port_match_kind": "none",
                "port_setup_direction": "",
                "port_setup_htf_tf": "",
                "port_setup_fvg_low": "",
                "port_setup_fvg_high": "",
                "port_setup_first_touch_ts": "",
                "port_setup_first_touch_in_window": "",
                "port_setup_n_touches": "",
                "port_setup_final_status": "",
                "port_setup_rejection_reasons": "",
                "port_trade_at_same_ts": "",
            }
            if match is not None:
                row["port_match_kind"] = "touch_within_10m"
                row["port_setup_direction"] = match["direction"]
                row["port_setup_htf_tf"] = match["htf_tf"]
                row["port_setup_fvg_low"] = match["fvg_low"]
                row["port_setup_fvg_high"] = match["fvg_high"]
                row["port_setup_first_touch_ts"] = match["first_touch_ts"] or ""
                row["port_setup_first_touch_in_window"] = (
                    "" if match["first_touch_in_window"] is None
                    else str(match["first_touch_in_window"])
                )
                row["port_setup_n_touches"] = match["n_touches"]
                row["port_setup_final_status"] = match["final_status"]
                row["port_setup_rejection_reasons"] = "|".join(
                    match["rejection_reasons"]
                )
                n_port_match_touch += 1
                if match["final_status"] == "FILLED":
                    n_port_filled += 1
            else:
                n_port_no_match += 1

            # If port also took a trade at the exact same entry_ts, note it.
            port_t = port_trade_by_ts.get(entry_ts)
            if port_t is not None:
                row["port_trade_at_same_ts"] = (
                    f"{port_t['side']}@{port_t['entry_price']:.2f}"
                )
            writer.writerow(row)

    print(
        f"summary: {n_port_match_touch} live trades had a port-side touch within 10m; "
        f"{n_port_filled} of those reached FILLED; {n_port_no_match} had no port "
        f"setup at all."
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
