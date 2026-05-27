"""Run the NQ Session Sweep Reaction V1 MBP-1 backtest.

Example:

    python -m app.cli.nq_session_sweep_reaction_v1 \\
        --start 2026-04-01 \\
        --end 2026-05-01 \\
        --output-dir ../data/backtests/nq_session_sweep_reaction_v1_apr2026
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from app.data.reader import read_bars, read_mbp1
from app.research.nq_session_sweep_reaction_v1 import (
    SweepReactionConfig,
    run_backtest,
)

logger = logging.getLogger("nq_session_sweep_reaction_v1")

_MBP1_COLUMNS = [
    "ts_event",
    "symbol",
    "action",
    "side",
    "price",
    "size",
    "bid_px",
    "ask_px",
    "bid_sz",
    "ask_sz",
    "sequence",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--start", type=_parse_date, required=True)
    parser.add_argument("--end", type=_parse_date, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--warmup-days", type=int, default=45)
    parser.add_argument(
        "--load-padding-days",
        type=int,
        default=4,
        help="Calendar days after --end to load for next-session labels.",
    )
    parser.add_argument("--slippage-ticks", type=int, default=1)
    parser.add_argument("--commission-per-contract", type=float, default=2.0)
    parser.add_argument("--qty", type=int, default=1)
    parser.add_argument("--initial-equity", type=float, default=25_000.0)
    parser.add_argument(
        "--disable-range-sanity",
        action="store_true",
        help="Debug only: skip the prior-20 range sanity filter.",
    )
    args = parser.parse_args(argv)
    _setup_logging()

    if args.start >= args.end:
        parser.error("--start must be before --end")
    if args.warmup_days < 0:
        parser.error("--warmup-days must be >= 0")
    if args.load_padding_days < 1:
        parser.error("--load-padding-days must be >= 1")

    cfg = SweepReactionConfig(
        symbol=args.symbol,
        qty=args.qty,
        initial_equity=args.initial_equity,
        commission_per_contract=args.commission_per_contract,
        slippage_ticks=args.slippage_ticks,
        prior_range_min_sessions=(0 if args.disable_range_sanity else 10),
    )
    warmup_start = args.start - timedelta(days=args.warmup_days)
    bars_load_start = warmup_start - timedelta(days=3)
    load_end = args.end + timedelta(days=args.load_padding_days)
    mbp_load_start = args.start

    logger.info(
        "loading 1m bars for %s from %s to %s",
        args.symbol,
        bars_load_start,
        load_end,
    )
    bars = read_bars(
        symbol=args.symbol,
        timeframe="1m",
        start=bars_load_start,
        end=load_end,
    )
    logger.info("loaded %d 1m bars", len(bars))

    logger.info(
        "loading MBP-1 for %s from %s to %s",
        args.symbol,
        mbp_load_start,
        load_end,
    )
    mbp1 = read_mbp1(
        symbol=args.symbol,
        start=mbp_load_start,
        end=load_end,
        columns=_MBP1_COLUMNS,
    )
    logger.info("loaded %d MBP-1 rows", len(mbp1))

    result = run_backtest(
        bars=bars,
        mbp1=mbp1,
        start=args.start,
        end=args.end,
        warmup_start=warmup_start,
        config=cfg,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_outputs(result, args.output_dir, cfg)

    payload = {
        "output_dir": str(args.output_dir),
        "summary": result["summary"],
        "trades_preview": _df_preview(result["trades"]),
        "sessions_preview": _df_preview(result["sessions"]),
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(_json_safe(payload), indent=2),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(payload), indent=2))
    return 0


def _write_outputs(
    result: dict[str, pd.DataFrame | dict[str, object]],
    output_dir: Path,
    config: SweepReactionConfig,
) -> None:
    for name in ("trades", "sessions", "replay_events", "equity"):
        value = result[name]
        assert isinstance(value, pd.DataFrame)
        value.to_csv(output_dir / f"{name}.csv", index=False)
    (output_dir / "config.json").write_text(
        json.dumps(_json_safe(asdict(config)), indent=2),
        encoding="utf-8",
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )


def _df_preview(value: Any, *, limit: int = 10) -> list[dict[str, object]]:
    if isinstance(value, pd.DataFrame):
        return value.head(limit).to_dict(orient="records")
    return []


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, (date, pd.Timestamp)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    if pd.isna(value):
        return None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
