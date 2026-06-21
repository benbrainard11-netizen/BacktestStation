"""Full-universe re-detection: 24 new session × {15m, 30m} modes.

Runs the order_block + liquidity_sweep detectors with the new 12+12
session-scope 15m/30m mode variants across the FULL symbol universe
and the full available date range.

Scope:
  - Symbols: 22 (full BacktestStation universe minus a couple)
  - Date range: 2015-01-01 → 2026-05-16
  - Detectors: order_block + liquidity_sweep
  - Modes: only the 24 new 15m + 30m session variants

Per-(detector, symbol, mode) commit so a crash anywhere doesn't lose
prior progress. JSONL log per-scan.

Expected runtime: 6-12 hours on benpc. Run overnight.

NOTE: these modes inherit the state-machine bugs (#14-17) currently
under investigation. Events generated here will need regeneration
after the bugs are fixed -- the detector_version field stays 'v1' so
v2 can supersede them later.

Run:
    cd backend
    python scripts/full_universe_new_modes.py
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


# Full warehouse symbols (from D:/data/processed/bars listing)
SYMBOLS = [
    "NQ.c.0", "ES.c.0", "YM.c.0", "RTY.c.0",        # equity index majors
    "CL.c.0", "BZ.c.0", "NG.c.0", "RB.c.0", "HO.c.0",  # energy
    "GC.c.0", "SI.c.0", "PA.c.0", "PL.c.0", "HG.c.0",  # metals
    "ZN.c.0", "ZB.c.0", "ZF.c.0", "ZT.c.0",         # rates
    "ZC.c.0", "ZS.c.0", "ZW.c.0",                   # grains
    "6A.c.0", "6B.c.0", "6C.c.0", "6E.c.0",
    "6J.c.0", "6N.c.0", "6S.c.0",                   # FX
]

START = date(2015, 1, 1)
END = date(2026, 5, 16)

DETECTORS = {
    "order_block": (
        "swept_asia_low_15m", "swept_asia_high_15m",
        "swept_asia_low_30m", "swept_asia_high_30m",
        "swept_london_low_15m", "swept_london_high_15m",
        "swept_london_low_30m", "swept_london_high_30m",
        "swept_ny_low_15m", "swept_ny_high_15m",
        "swept_ny_low_30m", "swept_ny_high_30m",
    ),
    "liquidity_sweep": (
        "asia_low_15m", "asia_high_15m",
        "asia_low_30m", "asia_high_30m",
        "london_low_15m", "london_high_15m",
        "london_low_30m", "london_high_30m",
        "ny_low_15m", "ny_high_15m",
        "ny_low_30m", "ny_high_30m",
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
    log_path = log_dir / f"full_universe_new_modes_{run_id}.jsonl"

    print(f"=== Full-universe new-mode re-detection ===")
    print(f"Run ID: {run_id}")
    print(f"Log:    {log_path}")
    print(f"Symbols: {len(SYMBOLS)}")
    print(f"Date range: {START} -> {END}")
    total = sum(len(m) for m in DETECTORS.values()) * len(SYMBOLS)
    print(f"Total scans: {total}")
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
        for symbol in SYMBOLS:
            for det_name, modes in DETECTORS.items():
                for mode in modes:
                    completed += 1
                    label = f"[{completed:>4}/{total}] {symbol} {det_name}/{mode}"
                    t_start = time_mod.time()
                    try:
                        # NEW session per scan to keep transactions small
                        with factory() as db:
                            result = run_scan(
                                detector_name=det_name,
                                symbols=[symbol],
                                start=START, end=END,
                                bar_reader=bar_reader,
                                db=db,
                                mode=mode,
                            )
                            db.commit()
                        elapsed = time_mod.time() - t_start
                        summary = result.as_dict()
                        summary["symbol"] = symbol
                        summary["elapsed_seconds"] = round(elapsed, 1)
                        logf.write(json.dumps(summary, default=str) + "\n")
                        logf.flush()
                        if completed % 10 == 0 or elapsed > 60:
                            eta_min = (total - completed) * (time_mod.time() - t0) / max(completed, 1) / 60
                            print(
                                f"{label} done in {elapsed:.1f}s "
                                f"events_returned={result.n_events_returned} "
                                f"inserted={result.n_inserted} "
                                f"eta={eta_min:.0f}min",
                                flush=True,
                            )
                    except Exception as exc:
                        elapsed = time_mod.time() - t_start
                        err = f"{type(exc).__name__}: {exc}"
                        logf.write(json.dumps({
                            "symbol": symbol, "detector": det_name, "mode": mode,
                            "fatal_error": err, "elapsed_seconds": round(elapsed, 1),
                        }) + "\n")
                        logf.flush()
                        print(f"{label} FATAL after {elapsed:.1f}s: {err}", flush=True)

    total_elapsed = time_mod.time() - t0
    print()
    print(f"=== Done in {total_elapsed/60:.1f} min ({total_elapsed/3600:.1f} hr) ===")
    print(f"Per-scan log: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
