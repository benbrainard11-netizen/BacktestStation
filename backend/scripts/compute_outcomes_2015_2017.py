"""Compute outcomes for the 2015-2017 OB + Sweep events.

Runs AFTER generate_events_2015_2017.py finishes. Calls the two
outcome computers (idempotent + version-aware):

  - order_block_reactions_v1
  - liquidity_sweep_reactions_v1

Each computer iterates every event of its feature_name and writes
the `outcomes` JSON column. Existing 2018+ events are not affected
(they'll be skipped as already-current via the runner's version check).

NOTE: this runs against the WHOLE events table, not a date filter,
because run_outcomes doesn't take a date filter (and re-touching
already-current rows is a no-op anyway). On a large DB this may take
longer than just the new 2015-2017 events.
"""

from __future__ import annotations

import json
import logging
import sys
import time as time_mod
from datetime import datetime, timezone
from pathlib import Path

# Make `app.*` importable when running as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.reader import read_bars  # noqa: E402
from app.db.session import create_all, make_engine, make_session_factory  # noqa: E402
from app.research import outcomes as outcome_registry  # noqa: E402
from app.research.outcomes.runner import run_outcomes  # noqa: E402


COMPUTERS = (
    "order_block_reactions_v1",
    "liquidity_sweep_reactions_v1",
)


def _make_bar_reader_adapter():
    def adapter(*args, **kwargs):
        return read_bars(*args, **kwargs)

    return adapter


def main() -> int:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"outcomes_2015_2017_{run_id}.jsonl"

    print(f"=== Compute outcomes for OB + Sweep (whole table) ===")
    print(f"Run ID: {run_id}")
    print(f"Log:    {log_path}")
    print(f"Computers: {COMPUTERS}")
    print()

    # Verify computers are registered before doing any work
    for name in COMPUTERS:
        outcome_registry.get(name)  # raises KeyError if missing

    engine = make_engine()
    create_all(engine)
    session_factory = make_session_factory(engine)
    bar_reader = _make_bar_reader_adapter()

    t0 = time_mod.time()
    with log_path.open("w", encoding="utf-8") as logf:
        with session_factory() as db:
            for name in COMPUTERS:
                t_start = time_mod.time()
                print(f"[{name}] starting…", flush=True)
                try:
                    computer = outcome_registry.get(name)
                    result = run_outcomes(
                        computer=computer,
                        bar_reader=bar_reader,
                        db=db,
                        force=False,
                    )
                    db.commit()
                    elapsed = time_mod.time() - t_start
                    summary = result.as_dict()
                    summary["elapsed_seconds"] = round(elapsed, 1)
                    logf.write(json.dumps(summary, default=str) + "\n")
                    logf.flush()
                    print(
                        f"[{name}] done in {elapsed:.1f}s  "
                        f"candidates={result.n_candidates:,}  "
                        f"updated={result.n_updated:,}  "
                        f"skipped_current={result.n_skipped_already_current:,}  "
                        f"skipped_no_data={result.n_skipped_no_data:,}  "
                        f"errors={result.n_errors}",
                        flush=True,
                    )
                    if result.n_errors:
                        for err in result.error_messages[:3]:
                            print(f"    ! {err}", flush=True)
                except Exception as exc:  # pragma: no cover
                    db.rollback()
                    elapsed = time_mod.time() - t_start
                    err_msg = f"{type(exc).__name__}: {exc}"
                    logf.write(json.dumps({
                        "computer": name,
                        "fatal_error": err_msg,
                        "elapsed_seconds": round(elapsed, 1),
                    }) + "\n")
                    logf.flush()
                    print(f"[{name}] FATAL after {elapsed:.1f}s: {err_msg}",
                          flush=True)

    print()
    print(f"=== Done in {(time_mod.time() - t0)/60:.1f} min ===")
    print(f"Per-computer log: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
