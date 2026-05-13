"""Re-run outcome computers for detectors that have JSON-null outcomes
after the intraday bar-load bug fix (2026-05-10).

Runs sequentially to avoid SQLite write-lock conflicts.
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

# All outcome computers affected by the intraday load bug.
# Listed in approximate order of n_nulls.
OUTCOME_TASKS = [
    ("fvg_reactions",            "fvg_reactions_v1"),         # 28,674 nulls
    ("psp_reactions",            "psp_reactions_v1"),         # 7,016 nulls
    ("volume_profile_reactions", "volume_profile_reactions_v2"),  # 1,739
    ("first_third_reactions",    "first_third_reactions_v1"), # 9
    ("orb_reactions",            "orb_reactions_v1"),         # 19
    ("time_profile_reactions",   "time_profile_reactions_v1"),# 24
    ("swing_pivot_reactions",    "swing_pivot_reactions_v1"), # 8
    ("equal_levels_reactions",   "equal_levels_reactions_v1"),# small
    ("displacement_reactions",   "displacement_reactions_v1"),# small
    ("order_block_reactions",    "order_block_reactions_v1"), # tiny
    ("liquidity_sweep_reactions", "liquidity_sweep_reactions_v1"),  # tiny
]


def setup_logging() -> Path:
    ts = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")
    log_path = LOG_DIR / f"rerun_nulls_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)],
    )
    return log_path


def run_outcomes(label, computer):
    cmd = [
        sys.executable, "-m", "app.cli.compute_research_outcomes",
        "--computer", computer,
    ]
    logging.info(f"START: {label}")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=43200)
    elapsed = time.time() - t0
    if proc.returncode != 0:
        logging.error(f"FAIL {label} (exit {proc.returncode}, {elapsed:.0f}s)")
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
    logging.info(f"rerun_null_outcomes started. Log: {log_path}")
    for label, comp in OUTCOME_TASKS:
        try:
            run_outcomes(label, comp)
        except Exception as exc:
            logging.exception(f"FATAL {label}: {exc}")
    logging.info("rerun_null_outcomes done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
