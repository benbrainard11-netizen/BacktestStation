"""Run the frozen OR-high middle-third shadow paper monitor."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from app.research.nq_opening_range_mbp_execution_stats import json_safe
from app.research.nq_opening_range_mbp_execution_types import ENTRY_STYLES
from app.research.nq_or_high_middle_third_paper import (
    DEFAULT_OUTPUT_DIR,
    PaperMonitorConfig,
    run_paper_monitor_once,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--session-date")
    parser.add_argument("--primary-entry-style", choices=ENTRY_STYLES, default="immediate_break")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--status-path", type=Path)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args(argv)

    cfg = PaperMonitorConfig(
        symbol=args.symbol,
        primary_entry_style=args.primary_entry_style,
        output_dir=args.output_dir,
        live_status_path=args.status_path or PaperMonitorConfig.live_status_path,
    )
    while True:
        result = run_paper_monitor_once(config=cfg, session_date=args.session_date)
        print(json.dumps(json_safe(summary(result)), indent=2))
        if not args.loop:
            return 0
        time.sleep(args.poll_seconds)


def summary(result: dict[str, object]) -> dict[str, object]:
    account = dict(result.get("paper_account", {}))
    return {
        "mode": result.get("mode"),
        "state": result.get("state"),
        "symbol": result.get("symbol"),
        "session_date": result.get("session_date"),
        "primary_entry_style": result.get("primary_entry_style"),
        "today_pnl": account.get("today_pnl"),
        "today_r": account.get("today_r"),
        "trades_today": account.get("trades_today"),
        "last_signal": result.get("last_signal"),
        "last_error": result.get("last_error"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
