"""Overnight build 2026-05-10 — three new detectors + bug-fix re-runs.

What's running:
  Phase 1 SCANS (new detectors over full 11 yrs × 3 symbols):
    - first_third_range × 2 modes (daily, weekly)
    - opening_range_breakout × 4 modes (ny_5m, ny_15m, ny_30m, asia_60m)
    - equal_levels × 7 modes (eq_pivot_*)
  Phase 2 OUTCOMES (compute outcomes for new events + fix yesterday's bug):
    - first_third_reactions       (new)
    - orb_reactions               (new)
    - equal_levels_reactions      (new)
    - liquidity_sweep_reactions   (re-run: fix session-mode null outcomes)
    - order_block_reactions       (re-run: fix session-mode null outcomes)

Skip-on-error semantics. Final summary written to logs/overnight/.
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

SCAN_TASKS: list[tuple[str, str, str]] = [
    # ---- first_third_range ----
    ("ft daily",   "first_third_range",     "first_third_daily"),
    ("ft weekly",  "first_third_range",     "first_third_weekly"),
    # ---- opening_range_breakout ----
    ("orb ny_5m",  "opening_range_breakout", "ny_5m"),
    ("orb ny_15m", "opening_range_breakout", "ny_15m"),
    ("orb ny_30m", "opening_range_breakout", "ny_30m"),
    ("orb asia_60m", "opening_range_breakout", "asia_60m"),
    # ---- equal_levels ----
    ("eq pivot_5_1h_5pts",     "equal_levels", "eq_pivot_5_1h_5pts"),
    ("eq pivot_5_1h_15pts",    "equal_levels", "eq_pivot_5_1h_15pts"),
    ("eq pivot_5_4h_15pts",    "equal_levels", "eq_pivot_5_4h_15pts"),
    ("eq pivot_5_daily_30pts", "equal_levels", "eq_pivot_5_daily_30pts"),
    ("eq pivot_3_1h_5pts",     "equal_levels", "eq_pivot_3_1h_5pts"),
    ("eq pivot_3_1h_15pts",    "equal_levels", "eq_pivot_3_1h_15pts"),
    ("eq pivot_3_4h_15pts",    "equal_levels", "eq_pivot_3_4h_15pts"),
]

OUTCOME_TASKS: list[tuple[str, str]] = [
    # New detector outcomes — fast, no big joins.
    ("first_third_reactions",      "first_third_reactions_v1"),
    ("orb_reactions",              "orb_reactions_v1"),
    ("equal_levels_reactions",     "equal_levels_reactions_v1"),
    # Re-runs to fix yesterday's null-outcome bug on session events.
    # liquidity_sweep_reactions has OB join -> slow; do it last.
    ("order_block_reactions",      "order_block_reactions_v1"),
    ("liquidity_sweep_reactions",  "liquidity_sweep_reactions_v1"),
]

SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0"]
START_DATE = "2015-01-01"
END_DATE = "2026-05-08"


def setup_logging() -> Path:
    ts = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")
    log_path = LOG_DIR / f"overnight_2_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)],
    )
    return log_path


def run_scan(label: str, detector: str, mode: str) -> dict:
    cmd = [
        sys.executable, "-m", "app.cli.scan_research_events",
        "--detector", detector, "--mode", mode,
        "--symbols", *SYMBOLS,
        "--start", START_DATE, "--end", END_DATE,
    ]
    logging.info(f"START scan: {label}")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=14400)
    elapsed = time.time() - t0
    if proc.returncode != 0:
        logging.error(f"FAIL scan {label} (exit {proc.returncode}, {elapsed:.0f}s)")
        logging.error(f"  stderr tail: {proc.stderr[-500:]}")
        return {"label": label, "ok": False, "elapsed_s": elapsed,
                "error": proc.stderr[-500:]}
    out = proc.stdout
    try:
        last_open = out.rfind("{")
        last_close = out.rfind("}")
        summary = json.loads(out[last_open:last_close + 1])
    except Exception as exc:
        summary = {"parse_error": str(exc)}
    logging.info(
        f"OK scan {label}: n_inserted={summary.get('n_inserted')} "
        f"n_errors={summary.get('n_errors')} ({elapsed:.0f}s)"
    )
    return {"label": label, "ok": True, "elapsed_s": elapsed,
            "n_inserted": summary.get("n_inserted"),
            "n_errors": summary.get("n_errors")}


def run_outcomes(label: str, computer: str) -> dict:
    cmd = [
        sys.executable, "-m", "app.cli.compute_research_outcomes",
        "--computer", computer,
    ]
    logging.info(f"START outcomes: {label}")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=43200)
    elapsed = time.time() - t0
    if proc.returncode != 0:
        logging.error(f"FAIL outcomes {label} (exit {proc.returncode}, {elapsed:.0f}s)")
        logging.error(f"  stderr tail: {proc.stderr[-500:]}")
        return {"label": label, "ok": False, "elapsed_s": elapsed,
                "error": proc.stderr[-500:]}
    out = proc.stdout
    try:
        last_open = out.rfind("{")
        last_close = out.rfind("}")
        summary = json.loads(out[last_open:last_close + 1])
    except Exception as exc:
        summary = {"parse_error": str(exc)}
    logging.info(
        f"OK outcomes {label}: n_candidates={summary.get('n_candidates')} "
        f"n_updated={summary.get('n_updated')} "
        f"n_skipped_already_current={summary.get('n_skipped_already_current')} "
        f"n_skipped_no_data={summary.get('n_skipped_no_data')} "
        f"n_errors={summary.get('n_errors')} ({elapsed:.0f}s)"
    )
    return {"label": label, "ok": True, "elapsed_s": elapsed,
            "n_candidates": summary.get("n_candidates"),
            "n_updated": summary.get("n_updated"),
            "n_skipped_no_data": summary.get("n_skipped_no_data"),
            "n_errors": summary.get("n_errors")}


def main() -> int:
    log_path = setup_logging()
    logging.info(f"Overnight build 2026-05-10 started. Log: {log_path}")
    started_at = datetime.now(UTC)

    scan_results: list[dict] = []
    for label, det, mode in SCAN_TASKS:
        try:
            r = run_scan(label, det, mode)
        except Exception as exc:
            logging.exception(f"FATAL scan {label}: {exc}")
            r = {"label": label, "ok": False, "error": str(exc)}
        scan_results.append(r)

    outcome_results: list[dict] = []
    for label, comp in OUTCOME_TASKS:
        try:
            r = run_outcomes(label, comp)
        except Exception as exc:
            logging.exception(f"FATAL outcomes {label}: {exc}")
            r = {"label": label, "ok": False, "error": str(exc)}
        outcome_results.append(r)

    finished_at = datetime.now(UTC)
    total_seconds = (finished_at - started_at).total_seconds()
    n_scan_ok = sum(1 for r in scan_results if r.get("ok"))
    n_scan_fail = len(scan_results) - n_scan_ok
    n_outcome_ok = sum(1 for r in outcome_results if r.get("ok"))
    n_outcome_fail = len(outcome_results) - n_outcome_ok
    total_inserted = sum(
        r.get("n_inserted", 0) or 0 for r in scan_results if r.get("ok")
    )

    logging.info("=" * 60)
    logging.info(f"BUILD COMPLETE — {total_seconds/60:.1f} minutes")
    logging.info(f"  scans:    {n_scan_ok} ok / {n_scan_fail} fail")
    logging.info(f"  outcomes: {n_outcome_ok} ok / {n_outcome_fail} fail")
    logging.info(f"  total events inserted: {total_inserted:,}")
    logging.info("=" * 60)
    if n_scan_fail or n_outcome_fail:
        logging.warning("FAILURES:")
        for r in scan_results + outcome_results:
            if not r.get("ok"):
                logging.warning(f"  {r['label']}: {r.get('error', 'unknown')[:200]}")

    summary_path = log_path.with_suffix(".summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "total_seconds": total_seconds,
            "scan_results": scan_results,
            "outcome_results": outcome_results,
        }, f, indent=2, default=str)
    logging.info(f"summary: {summary_path}")
    return 0 if (n_scan_fail == 0 and n_outcome_fail == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
