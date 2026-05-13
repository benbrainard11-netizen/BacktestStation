"""Overnight database build — runs every new scan + outcomes pass
sequentially. Skip-on-error semantics: any failing mode logs the error
and continues with the next.

Built 2026-05-10 to populate:
  - swing_pivot detector: 5 modes × 3 symbols × 11 yrs
  - liquidity_sweep session refs: 6 new modes (asia_*, london_*, ny_*)
  - order_block session refs: 6 new modes
  - fvg_formation 15m: 1 new mode
  - swing_pivot outcomes
  - re-run all outcomes for any new events

Each step is wrapped in try/except. Final summary printed at end.
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

# (label, args) — args passed to scan_research_events or compute_research_outcomes.
SCAN_TASKS: list[tuple[str, list[str]]] = [
    # ---- swing_pivot, all modes ----
    ("swing pivot_3_1h",   ["scan", "swing_pivot", "pivot_3_1h"]),
    ("swing pivot_5_1h",   ["scan", "swing_pivot", "pivot_5_1h"]),
    ("swing pivot_3_4h",   ["scan", "swing_pivot", "pivot_3_4h"]),
    ("swing pivot_5_4h",   ["scan", "swing_pivot", "pivot_5_4h"]),
    ("swing pivot_5_daily", ["scan", "swing_pivot", "pivot_5_daily"]),

    # ---- liquidity_sweep session modes ----
    ("sweep asia_low_1h",   ["scan", "liquidity_sweep", "asia_low_1h"]),
    ("sweep asia_high_1h",  ["scan", "liquidity_sweep", "asia_high_1h"]),
    ("sweep london_low_1h",  ["scan", "liquidity_sweep", "london_low_1h"]),
    ("sweep london_high_1h", ["scan", "liquidity_sweep", "london_high_1h"]),
    ("sweep ny_low_1h",     ["scan", "liquidity_sweep", "ny_low_1h"]),
    ("sweep ny_high_1h",    ["scan", "liquidity_sweep", "ny_high_1h"]),

    # ---- order_block session modes ----
    ("ob swept_asia_low_1h",    ["scan", "order_block", "swept_asia_low_1h"]),
    ("ob swept_asia_high_1h",   ["scan", "order_block", "swept_asia_high_1h"]),
    ("ob swept_london_low_1h",  ["scan", "order_block", "swept_london_low_1h"]),
    ("ob swept_london_high_1h", ["scan", "order_block", "swept_london_high_1h"]),
    ("ob swept_ny_low_1h",      ["scan", "order_block", "swept_ny_low_1h"]),
    ("ob swept_ny_high_1h",     ["scan", "order_block", "swept_ny_high_1h"]),

    # ---- fvg 15m ----
    ("fvg 15m_fvg", ["scan", "fvg_formation", "15m_fvg"]),
]

OUTCOME_TASKS: list[tuple[str, list[str]]] = [
    # Run outcomes for newly-scanned event classes. Existing rows with
    # already-current outcomes are skipped automatically.
    ("swing_pivot_reactions",      ["outcomes", "swing_pivot_reactions_v1"]),
    ("liquidity_sweep_reactions",  ["outcomes", "liquidity_sweep_reactions_v1"]),
    ("order_block_reactions",      ["outcomes", "order_block_reactions_v1"]),
    ("fvg_reactions",              ["outcomes", "fvg_reactions_v1"]),
]

SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0"]
START_DATE = "2015-01-01"
END_DATE = "2026-05-08"


def setup_logging() -> Path:
    ts = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")
    log_path = LOG_DIR / f"overnight_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)],
    )
    return log_path


def run_scan(label: str, detector: str, mode: str) -> dict:
    """Run one scan and parse the JSON summary from its stdout."""
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
    # Parse JSON from end of stdout.
    out = proc.stdout
    try:
        # Find the last { ... } block.
        last_open = out.rfind("{")
        last_close = out.rfind("}")
        summary = json.loads(out[last_open:last_close + 1])
    except Exception as exc:
        summary = {"parse_error": str(exc)}
    n_inserted = summary.get("n_inserted", 0)
    n_errors = summary.get("n_errors", 0)
    logging.info(
        f"OK scan {label}: n_inserted={n_inserted} n_errors={n_errors} "
        f"({elapsed:.0f}s)"
    )
    return {"label": label, "ok": True, "elapsed_s": elapsed,
            "n_inserted": n_inserted, "n_errors": n_errors}


def run_outcomes(label: str, computer: str) -> dict:
    cmd = [
        sys.executable, "-m", "app.cli.compute_research_outcomes",
        "--computer", computer,
    ]
    logging.info(f"START outcomes: {label}")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=14400)
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
        f"OK outcomes {label}: n_updated={summary.get('n_updated')} "
        f"n_skipped={summary.get('n_skipped_already_current')} "
        f"n_errors={summary.get('n_errors')} ({elapsed:.0f}s)"
    )
    return {"label": label, "ok": True, "elapsed_s": elapsed,
            "n_updated": summary.get("n_updated"),
            "n_errors": summary.get("n_errors")}


def main() -> int:
    log_path = setup_logging()
    logging.info(f"Overnight build started. Log: {log_path}")
    started_at = datetime.now(UTC)

    scan_results: list[dict] = []
    for label, args in SCAN_TASKS:
        kind, detector, mode = args
        if kind != "scan":
            continue
        try:
            r = run_scan(label, detector, mode)
        except Exception as exc:
            logging.exception(f"FATAL exception during scan {label}: {exc}")
            r = {"label": label, "ok": False, "error": str(exc)}
        scan_results.append(r)

    outcome_results: list[dict] = []
    for label, args in OUTCOME_TASKS:
        kind, computer = args
        if kind != "outcomes":
            continue
        try:
            r = run_outcomes(label, computer)
        except Exception as exc:
            logging.exception(f"FATAL exception during outcomes {label}: {exc}")
            r = {"label": label, "ok": False, "error": str(exc)}
        outcome_results.append(r)

    finished_at = datetime.now(UTC)
    total_seconds = (finished_at - started_at).total_seconds()
    n_scan_ok = sum(1 for r in scan_results if r.get("ok"))
    n_scan_fail = len(scan_results) - n_scan_ok
    n_outcome_ok = sum(1 for r in outcome_results if r.get("ok"))
    n_outcome_fail = len(outcome_results) - n_outcome_ok
    total_inserted = sum(
        r.get("n_inserted", 0) for r in scan_results if r.get("ok")
    )

    logging.info("=" * 60)
    logging.info(f"OVERNIGHT BUILD COMPLETE — {total_seconds/60:.1f} minutes")
    logging.info(f"  scans:    {n_scan_ok} ok / {n_scan_fail} fail")
    logging.info(f"  outcomes: {n_outcome_ok} ok / {n_outcome_fail} fail")
    logging.info(f"  total events inserted: {total_inserted:,}")
    logging.info("=" * 60)
    if n_scan_fail or n_outcome_fail:
        logging.warning("FAILURES:")
        for r in scan_results + outcome_results:
            if not r.get("ok"):
                logging.warning(
                    f"  {r['label']}: {r.get('error', 'unknown')[:200]}"
                )

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
