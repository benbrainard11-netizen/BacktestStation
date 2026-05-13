"""Sequential retry: vp scans that failed + all outcomes that failed +
sweep_reactions re-run (the slow one with OB join).

No concurrency this time — fully serialized to avoid SQLite locks.
"""

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

# 1. Scans that failed in vp_build (vp weekly, asia, ny).
SCAN_TASKS = [
    ("vp weekly",  "volume_profile", "weekly_volume_profile"),
    ("vp asia",    "volume_profile", "asia_volume_profile"),
    ("vp ny",      "volume_profile", "ny_volume_profile"),
]

# 2. Outcomes that failed (time_profile + volume_profile) + sweep reactions
# fix from yesterday.
OUTCOME_TASKS = [
    ("time_profile_reactions",    "time_profile_reactions_v1"),
    ("volume_profile_reactions",  "volume_profile_reactions_v2"),
    ("liquidity_sweep_reactions", "liquidity_sweep_reactions_v1"),  # slow, last
]

SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0"]
START_DATE = "2015-01-01"
END_DATE = "2026-05-08"


def setup_logging() -> Path:
    ts = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")
    log_path = LOG_DIR / f"retry_all_{ts}.log"
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
        return
    out = proc.stdout
    try:
        summary = json.loads(out[out.rfind("{"):out.rfind("}") + 1])
        logging.info(
            f"OK {label}: n_inserted={summary.get('n_inserted')} "
            f"n_errors={summary.get('n_errors')} ({elapsed:.0f}s)"
        )
    except Exception:
        logging.info(f"OK {label} ({elapsed:.0f}s)")


def run_outcomes(label, computer):
    cmd = [
        sys.executable, "-m", "app.cli.compute_research_outcomes",
        "--computer", computer,
    ]
    logging.info(f"START outcomes: {label}")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=43200)
    elapsed = time.time() - t0
    if proc.returncode != 0:
        logging.error(f"FAIL {label} (exit {proc.returncode})")
        logging.error(proc.stderr[-500:])
        return
    out = proc.stdout
    try:
        summary = json.loads(out[out.rfind("{"):out.rfind("}") + 1])
        logging.info(
            f"OK {label}: n_candidates={summary.get('n_candidates')} "
            f"n_updated={summary.get('n_updated')} "
            f"n_skipped_already_current={summary.get('n_skipped_already_current')} "
            f"n_skipped_no_data={summary.get('n_skipped_no_data')} "
            f"n_errors={summary.get('n_errors')} ({elapsed:.0f}s)"
        )
    except Exception:
        logging.info(f"OK {label} ({elapsed:.0f}s)")


def main():
    log_path = setup_logging()
    logging.info(f"retry_all started. Log: {log_path}")
    for label, det, mode in SCAN_TASKS:
        run_scan(label, det, mode)
    for label, comp in OUTCOME_TASKS:
        run_outcomes(label, comp)
    logging.info("retry_all done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
