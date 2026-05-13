"""Run time_profile scans + outcomes for all 4 modes."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
LOG_DIR = Path(r"C:\Users\benbr\BacktestStation\logs\overnight")
LOG_DIR.mkdir(parents=True, exist_ok=True)

SCAN_TASKS = [
    ("tp daily_3session", "time_profile", "daily_3session"),
    ("tp daily_4session", "time_profile", "daily_4session"),
    ("tp weekly",         "time_profile", "weekly"),
    ("tp monthly",        "time_profile", "monthly"),
]
SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0"]
START_DATE = "2015-01-01"
END_DATE = "2026-05-08"


def setup_logging() -> Path:
    ts = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")
    log_path = LOG_DIR / f"time_profile_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)],
    )
    return log_path


def run_scan(label, detector, mode):
    cmd = [
        sys.executable, "-m", "app.cli.scan_research_events",
        "--detector", detector, "--mode", mode,
        "--symbols", *SYMBOLS, "--start", START_DATE, "--end", END_DATE,
    ]
    logging.info(f"START scan: {label}")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=14400)
    elapsed = time.time() - t0
    if proc.returncode != 0:
        logging.error(f"FAIL {label} (exit {proc.returncode})")
        logging.error(proc.stderr[-500:])
        return False
    out = proc.stdout
    try:
        summary = json.loads(out[out.rfind("{"):out.rfind("}") + 1])
        logging.info(
            f"OK {label}: n_inserted={summary.get('n_inserted')} "
            f"n_errors={summary.get('n_errors')} ({elapsed:.0f}s)"
        )
    except Exception:
        logging.info(f"OK {label} ({elapsed:.0f}s)")
    return True


def run_outcomes():
    cmd = [
        sys.executable, "-m", "app.cli.compute_research_outcomes",
        "--computer", "time_profile_reactions_v1",
    ]
    logging.info("START outcomes: time_profile_reactions")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=14400)
    elapsed = time.time() - t0
    if proc.returncode != 0:
        logging.error(f"FAIL outcomes (exit {proc.returncode})")
        logging.error(proc.stderr[-500:])
        return False
    out = proc.stdout
    try:
        summary = json.loads(out[out.rfind("{"):out.rfind("}") + 1])
        logging.info(
            f"OK outcomes: n_candidates={summary.get('n_candidates')} "
            f"n_updated={summary.get('n_updated')} "
            f"n_errors={summary.get('n_errors')} ({elapsed:.0f}s)"
        )
    except Exception:
        logging.info(f"OK outcomes ({elapsed:.0f}s)")
    return True


def main():
    log_path = setup_logging()
    logging.info(f"time_profile build started. Log: {log_path}")
    for label, det, mode in SCAN_TASKS:
        try:
            run_scan(label, det, mode)
        except Exception as exc:
            logging.exception(f"FATAL {label}: {exc}")
    try:
        run_outcomes()
    except Exception as exc:
        logging.exception(f"FATAL outcomes: {exc}")
    logging.info("time_profile build done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
