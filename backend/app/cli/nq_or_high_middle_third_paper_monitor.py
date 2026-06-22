"""Run the frozen OR-high middle-third shadow paper monitor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.research.nq_opening_range_mbp_execution_stats import json_safe
from app.research.nq_opening_range_mbp_execution_types import ENTRY_STYLES
from app.research.nq_or_high_middle_third_paper import (
    DEFAULT_OUTPUT_DIR,
    PaperMonitorConfig,
    run_paper_monitor_once,
)
from app.research.nq_or_high_middle_third_paper_report import write_daily_report
from app.research.nq_or_high_middle_third_paper_session import (
    run_paper_monitor_cycle,
    run_paper_monitor_session,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--session-date")
    parser.add_argument("--primary-entry-style", choices=ENTRY_STYLES, default="immediate_break")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--status-path", type=Path)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--auto-session", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--auto-mirror", action="store_true")
    parser.add_argument("--no-auto-mirror", action="store_true")
    parser.add_argument("--mirror-interval-seconds", type=int, default=300)
    parser.add_argument("--mirror-timeout-seconds", type=int, default=120)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--stop-after-report", action="store_true")
    args = parser.parse_args(argv)

    cfg = PaperMonitorConfig(
        symbol=args.symbol,
        primary_entry_style=args.primary_entry_style,
        output_dir=args.output_dir,
        live_status_path=args.status_path or PaperMonitorConfig.live_status_path,
    )
    auto_mirror = args.auto_mirror or (args.auto_session and not args.no_auto_mirror)
    if args.auto_session:
        result = run_paper_monitor_session(
            config=cfg,
            session_date=args.session_date,
            poll_seconds=args.poll_seconds,
            backend_dir=Path.cwd(),
            auto_mirror=auto_mirror,
            mirror_interval_seconds=args.mirror_interval_seconds,
            mirror_timeout_seconds=args.mirror_timeout_seconds,
            stop_after_report=args.stop_after_report,
        )
        print(json.dumps(json_safe(summary(dict(result["snapshot"]))), indent=2))
        return 0
    if args.loop:
        result = run_paper_monitor_session(
            config=cfg,
            session_date=args.session_date,
            poll_seconds=args.poll_seconds,
            backend_dir=Path.cwd(),
            auto_mirror=auto_mirror,
            mirror_interval_seconds=args.mirror_interval_seconds,
            mirror_timeout_seconds=args.mirror_timeout_seconds,
            stop_after_report=False,
        )
        print(json.dumps(json_safe(summary(dict(result["snapshot"]))), indent=2))
        return 0

    if auto_mirror:
        result = run_paper_monitor_cycle(
            config=cfg,
            session_date=args.session_date,
            backend_dir=Path.cwd(),
            auto_mirror=True,
            mirror_timeout_seconds=args.mirror_timeout_seconds,
            write_report=args.write_report,
        )
        snapshot = dict(result["snapshot"])
    else:
        snapshot = run_paper_monitor_once(config=cfg, session_date=args.session_date)
        if args.write_report:
            write_daily_report(snapshot, cfg)
    print(json.dumps(json_safe(summary(snapshot)), indent=2))
    return 0


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
        "data_status": result.get("data_status"),
        "last_signal": result.get("last_signal"),
        "last_error": result.get("last_error"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
