"""Overnight continuation for the all-asset MBP-1 download.

Waits for `pull_all_mbp1_free.py --mirror` to finish, then runs the
orderflow asset-discovery scan and writes a compact morning summary.
This script never downloads data itself; it only observes the guarded pull.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("D:/data")
LOG_DIR = DATA_ROOT / "logs"
PULL_PROGRESS = LOG_DIR / "mbp1_all_assets_pull_progress.json"
PIPE_PROGRESS = LOG_DIR / "overnight_orderflow_pipeline_progress.json"
PIPE_LOG = LOG_DIR / "overnight_orderflow_pipeline.log"

SCAN_SCRIPT = REPO_ROOT / "experiments" / "orderflow_asset_discovery_v0" / "scan_mbp1_assets.py"
SCOREBOARD = REPO_ROOT / "experiments" / "orderflow_asset_discovery_v0" / "out" / "symbol_scoreboard.csv"
MORNING_SUMMARY = REPO_ROOT / "experiments" / "orderflow_asset_discovery_v0" / "report" / "overnight_summary.md"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{now_iso()} {message}"
    with PIPE_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def write_progress(payload: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"updated_at_utc": now_iso(), **payload}
    PIPE_PROGRESS.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def read_pull_progress() -> dict | None:
    if not PULL_PROGRESS.exists():
        return None
    try:
        return json.loads(PULL_PROGRESS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def wait_for_pull(max_wait_hours: float, poll_seconds: int) -> dict:
    deadline = time.time() + max_wait_hours * 3600.0
    while time.time() < deadline:
        progress = read_pull_progress()
        if progress:
            status = str(progress.get("status") or "")
            write_progress(
                {
                    "status": "waiting_for_pull",
                    "pull_status": status,
                    "pull_processed_missing": progress.get("processed_missing"),
                    "pull_missing_at_start": progress.get("missing_at_start"),
                    "pull_errors": progress.get("errors") or [],
                }
            )
            if status in {"done", "done_with_errors"}:
                return progress
        else:
            write_progress({"status": "waiting_for_pull", "pull_status": "missing_progress"})
        time.sleep(poll_seconds)
    raise TimeoutError(f"pull did not finish within {max_wait_hours}h")


def run_scan(start: str, end: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCAN_SCRIPT),
        "--start",
        start,
        "--end",
        end,
    ]
    log("running asset discovery scan: " + " ".join(cmd))
    write_progress({"status": "running_asset_scan", "command": cmd})
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def write_morning_summary(pull_progress: dict, scan_output: str, scan_returncode: int) -> None:
    lines = [
        "# Overnight Orderflow Summary",
        "",
        f"Generated: {now_iso()}",
        "",
        "## Download",
        "",
        f"- Pull status: `{pull_progress.get('status')}`",
        f"- Cost quote: `${float(pull_progress.get('cost_quote_usd') or 0):.4f}`",
        f"- Missing at start: `{pull_progress.get('missing_at_start')}`",
        f"- Pulled: `{pull_progress.get('pulled')}`",
        f"- Skipped empty: `{pull_progress.get('skipped_empty')}`",
        f"- Bytes written: `{int(pull_progress.get('bytes_written') or 0):,}`",
        f"- Errors: `{len(pull_progress.get('errors') or [])}`",
        "",
        "## Mirror",
        "",
    ]
    mirror = pull_progress.get("mirror")
    if isinstance(mirror, dict):
        lines.extend(
            [
                f"- Converted DBN: `{mirror.get('converted_dbn')}`",
                f"- Converted partitions: `{mirror.get('converted_partitions')}`",
                f"- Mirror errors: `{len(mirror.get('errors') or [])}`",
            ]
        )
    else:
        lines.append("- Mirror summary missing.")

    lines.extend(
        [
            "",
            "## Asset Discovery",
            "",
            f"- Scan return code: `{scan_returncode}`",
            f"- Scoreboard: `{SCOREBOARD}`",
            "",
        ]
    )

    if SCOREBOARD.exists():
        import pandas as pd

        df = pd.read_csv(SCOREBOARD)
        top = df.head(12)
        lines.extend(
            [
                "| rank | symbol | score | days | med spread bps | trades/bucket | signed IC | imb IC | micro IC |",
                "|---|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for i, row in top.iterrows():
            lines.append(
                f"| {i + 1} | {row['symbol']} | {row['discovery_score']:.3f} | "
                f"{int(row['coverage_days'])} | {row['median_spread_bps']:.4f} | "
                f"{row['mean_trades_per_bucket']:.1f} | {row['signed_next_ic']:.4f} | "
                f"{row['imb_next_ic']:.4f} | {row['micro_next_ic']:.4f} |"
            )
    else:
        lines.append("Scoreboard was not produced.")

    lines.extend(["", "## Scan Log Tail", "", "```text", scan_output[-4000:], "```"])
    MORNING_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    MORNING_SUMMARY.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = argv or []
    max_wait_hours = 12.0
    poll_seconds = 60
    start = "2025-05-28"
    end = "2026-05-27"

    log("overnight pipeline starting")
    write_progress({"status": "starting", "start": start, "end": end})

    try:
        pull_progress = wait_for_pull(max_wait_hours=max_wait_hours, poll_seconds=poll_seconds)
    except Exception as exc:
        log(f"FAILED waiting for pull: {type(exc).__name__}: {exc}")
        write_progress({"status": "failed_waiting_for_pull", "error": f"{type(exc).__name__}: {exc}"})
        return 2

    if pull_progress.get("status") == "done_with_errors":
        log("pull finished with errors; continuing to scan available mirrored data")

    scan = run_scan(start, end)
    log(f"asset scan finished rc={scan.returncode}")
    write_morning_summary(pull_progress, scan.stdout, scan.returncode)
    write_progress(
        {
            "status": "done" if scan.returncode == 0 else "done_with_scan_error",
            "scan_returncode": scan.returncode,
            "scoreboard": str(SCOREBOARD),
            "morning_summary": str(MORNING_SUMMARY),
        }
    )
    return 0 if scan.returncode == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
