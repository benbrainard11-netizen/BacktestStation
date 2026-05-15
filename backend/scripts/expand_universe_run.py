"""Expand the research universe — run every detector against a symbol list.

This is the universe-expansion analog of `overnight_build.py`. Where that
script hardcoded `SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0"]` and a fixed task
list, this one takes `--symbols` and `--start/--end` from the CLI and walks
the full detector registry returned by `scan_research_events --list`.

Skip-on-error semantics: any failing (detector, mode) logs and we keep going.
A summary JSON is written next to the log file at the end.

Typical use — add RTY to the active universe:

    python -m scripts.expand_universe_run \\
        --symbols RTY.c.0 \\
        --start 2018-05-01 \\
        --end   2026-04-25

After it finishes, regenerate the asset universe manifest:

    python -m scripts.ml.build_asset_universe_manifest

…and RTY will appear in `active_universe.symbols`.

Cross-symbol detectors (`psp_candle_divergence`, `smt_htf_reference_divergence`)
fire on the symbols you pass. To compute SMT/PSP across the full universe,
run this script with the full list, not one-symbol-at-a-time.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
BACKEND_DIR = ROOT / "backend"
LOG_DIR = ROOT / "logs" / "expand_universe"


def setup_logging(slug: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")
    log_path = LOG_DIR / f"expand_universe_{slug}_{ts}.log"
    for handler in list(logging.root.handlers):
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_path), logging.StreamHandler(sys.stdout)],
    )
    return log_path


def discover_modes() -> list[tuple[str, str]]:
    """Run `scan_research_events --list` and parse out (detector, mode) pairs."""
    proc = subprocess.run(
        [sys.executable, "-m", "app.cli.scan_research_events", "--list"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"scan_research_events --list failed: {proc.stderr}")
    pairs: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        match = re.match(r"^([\w_]+)\s+feature=\S+\s+version=\S+\s+modes=(\S+)$", line.strip())
        if not match:
            continue
        detector = match.group(1)
        for mode in match.group(2).split("/"):
            pairs.append((detector, mode))
    return pairs


def run_scan(detector: str, mode: str, symbols: list[str], start: str, end: str) -> dict:
    label = f"{detector}/{mode}"
    cmd = [
        sys.executable, "-m", "app.cli.scan_research_events",
        "--detector", detector, "--mode", mode,
        "--symbols", *symbols,
        "--start", start, "--end", end,
    ]
    logging.info(f"START {label}")
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=BACKEND_DIR, capture_output=True, text=True, timeout=14400)
    elapsed = time.time() - t0
    if proc.returncode != 0:
        logging.error(f"FAIL {label} (exit {proc.returncode}, {elapsed:.0f}s)")
        logging.error(f"  stderr tail: {proc.stderr[-500:]}")
        return {"label": label, "ok": False, "elapsed_s": elapsed,
                "error": proc.stderr[-500:]}
    summary = _parse_json_tail(proc.stdout)
    n_inserted = summary.get("n_inserted", 0)
    n_errors = summary.get("n_errors", 0)
    logging.info(f"OK    {label}: n_inserted={n_inserted} n_errors={n_errors} ({elapsed:.0f}s)")
    return {"label": label, "ok": True, "elapsed_s": elapsed,
            "n_inserted": n_inserted, "n_errors": n_errors}


def _parse_json_tail(stdout: str) -> dict:
    try:
        last_open = stdout.rfind("{")
        last_close = stdout.rfind("}")
        if last_open == -1 or last_close == -1 or last_close <= last_open:
            return {}
        return json.loads(stdout[last_open:last_close + 1])
    except Exception as exc:
        return {"parse_error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="+", required=True,
                        help="Symbol list, e.g. RTY.c.0 CL.c.0")
    parser.add_argument("--start", required=True, help="ISO date, e.g. 2018-05-01")
    parser.add_argument("--end", required=True, help="ISO date, e.g. 2026-04-25")
    parser.add_argument("--include-detectors", nargs="+",
                        help="Restrict to these detector names. Default: all.")
    parser.add_argument("--exclude-detectors", nargs="+",
                        help="Skip these detector names.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned (detector, mode) tasks and exit.")
    args = parser.parse_args()

    slug = "_".join(sym.replace(".c.0", "") for sym in args.symbols)[:60]
    log_path = setup_logging(slug)
    logging.info(f"expand_universe start: symbols={args.symbols} start={args.start} end={args.end}")
    logging.info(f"log: {log_path}")

    pairs = discover_modes()
    if args.include_detectors:
        keep = set(args.include_detectors)
        pairs = [p for p in pairs if p[0] in keep]
    if args.exclude_detectors:
        skip = set(args.exclude_detectors)
        pairs = [p for p in pairs if p[0] not in skip]
    logging.info(f"planned scans: {len(pairs)} (detector,mode) pairs")
    if args.dry_run:
        for detector, mode in pairs:
            print(f"  {detector}/{mode}")
        return 0

    started_at = datetime.now(UTC)
    results: list[dict] = []
    for detector, mode in pairs:
        try:
            r = run_scan(detector, mode, args.symbols, args.start, args.end)
        except Exception as exc:
            logging.exception(f"FATAL exception scanning {detector}/{mode}: {exc}")
            r = {"label": f"{detector}/{mode}", "ok": False, "error": str(exc)}
        results.append(r)

    finished_at = datetime.now(UTC)
    total_seconds = (finished_at - started_at).total_seconds()
    n_ok = sum(1 for r in results if r.get("ok"))
    n_fail = len(results) - n_ok
    total_inserted = sum(r.get("n_inserted", 0) for r in results if r.get("ok"))

    logging.info("=" * 60)
    logging.info(f"EXPAND UNIVERSE COMPLETE — {total_seconds/60:.1f} minutes")
    logging.info(f"  scans: {n_ok} ok / {n_fail} fail")
    logging.info(f"  total events inserted: {total_inserted:,}")
    logging.info("=" * 60)
    if n_fail:
        logging.warning("FAILURES:")
        for r in results:
            if not r.get("ok"):
                logging.warning(f"  {r['label']}: {str(r.get('error', 'unknown'))[:200]}")

    summary_path = log_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps({
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "total_seconds": total_seconds,
        "symbols": args.symbols,
        "start": args.start,
        "end": args.end,
        "results": results,
    }, indent=2, default=str), encoding="utf-8")
    logging.info(f"summary: {summary_path}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
