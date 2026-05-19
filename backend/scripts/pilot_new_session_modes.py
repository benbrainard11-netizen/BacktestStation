"""Pilot run: 24 new session × {15m, 30m} mode variants on NQ.c.0 (2024-2026).

Validates the new modes added in commit 15e6d9d produce sensible event
counts before committing to a full universe historical run. Pilot scope:

  - Symbols: NQ.c.0 only (single liquid major)
  - Date range: 2024-01-01 → 2026-05-15
  - Detectors: order_block + liquidity_sweep
  - Modes: only the 24 new 15m + 30m session variants

Per-mode log goes to scripts/logs/pilot_new_session_modes_<runid>.jsonl.

Run:
    cd backend
    python scripts/pilot_new_session_modes.py
"""

from __future__ import annotations

import json
import logging
import sys
import time as time_mod
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.reader import read_bars  # noqa: E402
from app.db.session import create_all, make_engine, make_session_factory  # noqa: E402
from app.research import detectors as detector_registry  # noqa: E402
from app.research.scan import run_scan  # noqa: E402


SYMBOLS = ["NQ.c.0"]
START = date(2024, 1, 1)
END = date(2026, 5, 16)  # exclusive — covers through 2026-05-15

DETECTORS = {
    "order_block": (
        "swept_asia_low_15m",
        "swept_asia_high_15m",
        "swept_asia_low_30m",
        "swept_asia_high_30m",
        "swept_london_low_15m",
        "swept_london_high_15m",
        "swept_london_low_30m",
        "swept_london_high_30m",
        "swept_ny_low_15m",
        "swept_ny_high_15m",
        "swept_ny_low_30m",
        "swept_ny_high_30m",
    ),
    "liquidity_sweep": (
        "asia_low_15m",
        "asia_high_15m",
        "asia_low_30m",
        "asia_high_30m",
        "london_low_15m",
        "london_high_15m",
        "london_low_30m",
        "london_high_30m",
        "ny_low_15m",
        "ny_high_15m",
        "ny_low_30m",
        "ny_high_30m",
    ),
}


def _adapter():
    def f(*a, **kw):
        return read_bars(*a, **kw)
    return f


def main() -> int:
    logging.basicConfig(level=logging.WARNING,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                        stream=sys.stderr)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"pilot_new_session_modes_{run_id}.jsonl"

    print(f"=== Pilot: 24 new session × {{15m, 30m}} modes ===")
    print(f"Run ID: {run_id}")
    print(f"Log:    {log_path}")
    print(f"Symbols: {SYMBOLS}")
    print(f"Date range: {START} -> {END} (exclusive, ~2.4 years)")
    total = sum(len(m) for m in DETECTORS.values())
    print(f"Total scans queued: {total}")
    print()

    for det in DETECTORS:
        detector_registry.get(det)
    print("All detectors registered. Starting scans...\n")

    engine = make_engine()
    create_all(engine)
    factory = make_session_factory(engine)
    bar_reader = _adapter()

    t0 = time_mod.time()
    completed = 0
    with log_path.open("w", encoding="utf-8") as logf:
        with factory() as db:
            for det_name, modes in DETECTORS.items():
                for mode in modes:
                    completed += 1
                    label = f"[{completed:>2}/{total}] {det_name}/{mode}"
                    t_start = time_mod.time()
                    print(f"{label} starting...", flush=True)
                    try:
                        result = run_scan(
                            detector_name=det_name,
                            symbols=SYMBOLS,
                            start=START,
                            end=END,
                            bar_reader=bar_reader,
                            db=db,
                            mode=mode,
                        )
                        db.commit()
                        elapsed = time_mod.time() - t_start
                        summary = result.as_dict()
                        summary["elapsed_seconds"] = round(elapsed, 1)
                        logf.write(json.dumps(summary, default=str) + "\n")
                        logf.flush()
                        print(
                            f"{label} done in {elapsed:.1f}s  "
                            f"events_returned={result.n_events_returned:,}  "
                            f"inserted={result.n_inserted:,}  "
                            f"skipped_dup={result.n_skipped_duplicate:,}  "
                            f"errors={result.n_errors}",
                            flush=True,
                        )
                    except Exception as exc:
                        db.rollback()
                        elapsed = time_mod.time() - t_start
                        err = f"{type(exc).__name__}: {exc}"
                        logf.write(json.dumps({
                            "detector": det_name, "mode": mode,
                            "fatal_error": err,
                            "elapsed_seconds": round(elapsed, 1),
                        }) + "\n")
                        logf.flush()
                        print(f"{label} FATAL after {elapsed:.1f}s: {err}", flush=True)

    total_elapsed = time_mod.time() - t0
    print()
    print(f"=== Done in {total_elapsed/60:.1f} min ({total_elapsed:.0f}s) ===")
    print(f"Per-mode log: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
