"""Generate OB + Sweep events for 2015-2017 — a fresh untouched window.

PURPOSE: produce research events for years that have never been touched
by v8a/v13-v19/v20 research, so we can run a third independent locked
walk-forward on truly out-of-sample data.

SCOPE:
  - Detectors: order_block, liquidity_sweep (the v20 survivors)
  - Modes: all 14 modes for each detector (matches existing 2018+ coverage)
  - Symbols: NQ.c.0, ES.c.0, YM.c.0 (matches v20 + v27 universe)
  - Date range: 2015-01-01 → 2018-01-01

OUTPUT:
  - Events written to meta.sqlite research_events table (idempotent)
  - JSONL log to scripts/logs/events_2015_2017_<run>.jsonl with per-mode summary
  - Stdout: progress lines

NOTE on lockfile reproducibility:
  v20's lockfile pins research_events_manifest_sha256 = "5ad286d2..." which
  is computed from the parquet export of the events. Writing new events
  to the DB DOES NOT change that hash (the parquet manifest is a snapshot).
  Only re-running the parquet export would change it.

  We do NOT re-export the manifest as part of this script. The v20
  lockfile stays reproducible until/unless someone explicitly re-exports.
"""

from __future__ import annotations

import json
import logging
import sys
import time as time_mod
from datetime import date, datetime, timezone
from pathlib import Path

# Make `app.*` importable when running as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.reader import read_bars  # noqa: E402
from app.db.session import create_all, make_engine, make_session_factory  # noqa: E402
from app.research import detectors as detector_registry  # noqa: E402
from app.research.scan import run_scan  # noqa: E402


# --- config ---

SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0"]
START = date(2015, 1, 1)
END = date(2018, 1, 1)  # exclusive

DETECTORS = {
    "order_block": (
        "swept_pdl_1h",
        "swept_pdl_4h",
        "swept_pdh_1h",
        "swept_pdh_4h",
        "swept_pwl_4h",
        "swept_pwl_daily",
        "swept_pwh_4h",
        "swept_pwh_daily",
        "swept_asia_low_1h",
        "swept_asia_high_1h",
        "swept_london_low_1h",
        "swept_london_high_1h",
        "swept_ny_low_1h",
        "swept_ny_high_1h",
    ),
    "liquidity_sweep": (
        "pdl_1h",
        "pdl_4h",
        "pdh_1h",
        "pdh_4h",
        "pwl_4h",
        "pwl_daily",
        "pwh_4h",
        "pwh_daily",
        "asia_low_1h",
        "asia_high_1h",
        "london_low_1h",
        "london_high_1h",
        "ny_low_1h",
        "ny_high_1h",
    ),
}


def _make_bar_reader_signature_adapter():
    """`run_scan` calls `bar_reader(...)` with whatever positional/kw args
    a given detector chooses. Real `read_bars` is keyword-only. Wrap it
    so detectors that pass-by-keyword (the standard) work."""

    def adapter(*args, **kwargs):
        return read_bars(*args, **kwargs)

    return adapter


def main() -> int:
    logging.basicConfig(
        level=logging.WARNING,  # quiet — scan loop prints its own progress
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"events_2015_2017_{run_id}.jsonl"

    print(f"=== Generate 2015-2017 OB + Sweep events ===")
    print(f"Run ID: {run_id}")
    print(f"Log:    {log_path}")
    print(f"Symbols: {SYMBOLS}")
    print(f"Date range: {START} → {END} (exclusive)")
    total_modes = sum(len(modes) for modes in DETECTORS.values())
    print(f"Detectors × modes: {total_modes} total scans queued")
    print()

    # Verify detectors are registered before doing any work
    for det_name in DETECTORS:
        detector_registry.get(det_name)  # raises KeyError if missing
    print(f"All detectors registered. Starting scans…\n")

    engine = make_engine()
    create_all(engine)
    session_factory = make_session_factory(engine)

    bar_reader = _make_bar_reader_signature_adapter()
    t0 = time_mod.time()
    completed = 0

    with log_path.open("w", encoding="utf-8") as logf:
        with session_factory() as db:
            for det_name, modes in DETECTORS.items():
                for mode in modes:
                    completed += 1
                    label = f"[{completed:>2}/{total_modes}] {det_name}/{mode}"
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
                        # commit per-mode so a crash doesn't drop everything
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
                        if result.n_errors:
                            for err in result.error_messages[:3]:
                                print(f"    ! {err}", flush=True)
                    except Exception as exc:  # pragma: no cover — runtime safety
                        db.rollback()
                        elapsed = time_mod.time() - t_start
                        err_msg = f"{type(exc).__name__}: {exc}"
                        logf.write(json.dumps({
                            "detector": det_name,
                            "mode": mode,
                            "fatal_error": err_msg,
                            "elapsed_seconds": round(elapsed, 1),
                        }) + "\n")
                        logf.flush()
                        print(f"{label} FATAL after {elapsed:.1f}s: {err_msg}",
                              flush=True)

    total_elapsed = time_mod.time() - t0
    print()
    print(f"=== Done in {total_elapsed/60:.1f} min ({total_elapsed:.0f}s) ===")
    print(f"Per-mode log: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
