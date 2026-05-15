"""Run the futures_expanded_v1 research-event build safely.

This script intentionally does not train strategies or publish releases. It
only scans detector events and computes outcomes for a clearly named expanded
asset universe.

SMT-like cross-market detectors are run only within correlated clusters. Other
detectors are run across the full active symbol list.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "data" / "ml" / "catalog"
REPORT_JSON = REPORT_DIR / "expanded_universe_research_build_report.json"
REPORT_MD = ROOT / "docs" / "EXPANDED_UNIVERSE_BUILD_REPORT.md"
DB_PATH = DATA_DIR / "meta.sqlite"

UNIVERSE_ID = "futures_expanded_v1"
START_DATE = "2018-05-01"
END_DATE = "2026-04-25"

CORRELATED_CLUSTERS: dict[str, list[str]] = {
    "index_triads": ["NQ.c.0", "ES.c.0", "YM.c.0", "RTY.c.0"],
    "fx_europe": ["6E.c.0", "6B.c.0", "6S.c.0"],
    "fx_commodity": ["6A.c.0", "6C.c.0", "6N.c.0"],
    "oil_products": ["CL.c.0", "BZ.c.0", "RB.c.0", "HO.c.0"],
    "rates_curve": ["ZT.c.0", "ZF.c.0", "ZN.c.0", "ZB.c.0"],
    "grains": ["ZC.c.0", "ZS.c.0", "ZW.c.0"],
}

SINGLE_SYMBOL_ACTIVE = ["6J.c.0", "NG.c.0"]

WAREHOUSE_ONLY_SYMBOLS = {
    "GC.c.0": "sparse 1m bars in warehouse inventory",
    "SI.c.0": "sparse 1m bars in warehouse inventory",
    "HG.c.0": "sparse 1m bars in warehouse inventory",
    "PL.c.0": "sparse 1m bars in warehouse inventory",
    "PA.c.0": "sparse 1m bars in warehouse inventory",
}

DETECTOR_MODES: dict[str, list[str]] = {
    "displacement_candle": ["1h_disp", "4h_disp", "daily_disp"],
    "equal_levels": [
        "eq_pivot_5_1h_5pts",
        "eq_pivot_5_1h_15pts",
        "eq_pivot_5_4h_15pts",
        "eq_pivot_5_daily_30pts",
        "eq_pivot_3_1h_5pts",
        "eq_pivot_3_1h_15pts",
        "eq_pivot_3_4h_15pts",
    ],
    "first_third_range": ["first_third_daily", "first_third_weekly"],
    "forming_volume_profile": ["daily_vp_asof_1h", "daily_vp_asof_4h"],
    "fvg_formation": ["daily_fvg", "4h_fvg", "1h_fvg", "15m_fvg"],
    "interval_true_range": ["daily_itr", "weekly_itr", "asia_itr", "london_itr", "ny_itr"],
    "liquidity_sweep": [
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
    ],
    "opening_gap_levels": ["ndog", "nwog"],
    "opening_range_breakout": ["ny_5m", "ny_15m", "ny_30m", "asia_60m"],
    "order_block": [
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
    ],
    "psp_candle_divergence": ["daily_psp", "4h_psp", "1h_psp"],
    "smt_htf_reference_divergence": ["weekly_smt", "previous_day_smt"],
    "swing_pivot": ["pivot_3_1h", "pivot_5_1h", "pivot_3_4h", "pivot_5_4h", "pivot_5_daily"],
    "time_profile": ["daily_3session", "daily_4session", "weekly", "monthly"],
    "volume_profile": [
        "daily_volume_profile",
        "weekly_volume_profile",
        "asia_volume_profile",
        "london_volume_profile",
        "ny_volume_profile",
    ],
}

CORRELATED_ONLY_DETECTORS = {"smt_htf_reference_divergence", "psp_candle_divergence"}

OUTCOME_COMPUTERS = [
    "displacement_reactions_v1",
    "equal_levels_reactions_v1",
    "first_third_reactions_v1",
    "forming_volume_profile_reactions_v1",
    "fvg_reactions_v1",
    "interval_true_range_reactions_v1",
    "liquidity_sweep_reactions_v1",
    "opening_gap_reactions_v1",
    "orb_reactions_v1",
    "order_block_reactions_v1",
    "psp_reactions_v1",
    "smt_htf_reactions_v1",
    "swing_pivot_reactions_v1",
    "time_profile_reactions_v1",
    "volume_profile_reactions_v2",
]

FAST_OUTCOME_SCRIPTS = {
    "forming_volume_profile_reactions_v1": "backfill_forming_volume_profile_outcomes.py",
    "interval_true_range_reactions_v1": "backfill_interval_true_range_outcomes.py",
    "opening_gap_reactions_v1": "backfill_opening_gap_outcomes.py",
}


def active_symbols() -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for symbols in CORRELATED_CLUSTERS.values():
        for symbol in symbols:
            if symbol not in seen:
                seen.add(symbol)
                out.append(symbol)
    for symbol in SINGLE_SYMBOL_ACTIVE:
        if symbol not in seen:
            seen.add(symbol)
            out.append(symbol)
    return out


def sqlite_url(path: Path) -> str:
    return "sqlite:///" + path.resolve().as_posix()


def parse_json_object(stdout: str) -> dict[str, Any] | None:
    start = stdout.rfind("{")
    end = stdout.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(stdout[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def run_command(label: str, cmd: list[str], *, timeout: int) -> dict[str, Any]:
    started = time.time()
    print(f"START {label}", flush=True)
    proc = subprocess.run(
        cmd,
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    elapsed = time.time() - started
    parsed = parse_json_object(proc.stdout)
    status = "ok" if proc.returncode == 0 else "failed"
    print(f"{status.upper()} {label} elapsed={elapsed:.1f}s", flush=True)
    if proc.returncode != 0:
        print(proc.stderr[-1200:], flush=True)
    return {
        "label": label,
        "status": status,
        "returncode": proc.returncode,
        "elapsed_seconds": round(elapsed, 3),
        "command": cmd,
        "summary": parsed,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def scan_tasks(*, dry_run: bool, only_detector: str | None) -> list[tuple[str, list[str], int]]:
    db_url = sqlite_url(DB_PATH)
    tasks: list[tuple[str, list[str], int]] = []
    all_symbols = active_symbols()
    for detector, modes in DETECTOR_MODES.items():
        if only_detector and detector != only_detector:
            continue
        for mode in modes:
            if detector in CORRELATED_ONLY_DETECTORS:
                for cluster, symbols in CORRELATED_CLUSTERS.items():
                    if len(symbols) < 2:
                        continue
                    cmd = [
                        sys.executable,
                        "-m",
                        "app.cli.scan_research_events",
                        "--detector",
                        detector,
                        "--mode",
                        mode,
                        "--symbols",
                        *symbols,
                        "--start",
                        START_DATE,
                        "--end",
                        END_DATE,
                        "--database-url",
                        db_url,
                    ]
                    if dry_run:
                        cmd.append("--dry-run")
                    tasks.append((f"scan {detector}/{mode}/{cluster}", cmd, 14_400))
            else:
                cmd = [
                    sys.executable,
                    "-m",
                    "app.cli.scan_research_events",
                    "--detector",
                    detector,
                    "--mode",
                    mode,
                    "--symbols",
                    *all_symbols,
                    "--start",
                    START_DATE,
                    "--end",
                    END_DATE,
                    "--database-url",
                    db_url,
                ]
                if dry_run:
                    cmd.append("--dry-run")
                tasks.append((f"scan {detector}/{mode}", cmd, 14_400))
    return tasks


def outcome_tasks(*, dry_run: bool, only_computer: str | None) -> list[tuple[str, list[str], int]]:
    db_url = sqlite_url(DB_PATH)
    tasks: list[tuple[str, list[str], int]] = []
    for computer in OUTCOME_COMPUTERS:
        if only_computer and computer != only_computer:
            continue
        fast_script = FAST_OUTCOME_SCRIPTS.get(computer)
        if fast_script:
            cmd = [
                sys.executable,
                str(BACKEND / "scripts" / fast_script),
                "--database-url",
                db_url,
            ]
        else:
            cmd = [
                sys.executable,
                str(BACKEND / "scripts" / "backfill_research_outcomes_cached.py"),
                "--computer",
                computer,
                "--database-url",
                db_url,
            ]
        if dry_run:
            cmd.append("--dry-run")
        tasks.append((f"outcomes {computer}", cmd, 43_200))
    return tasks


def write_report(results: list[dict[str, Any]], *, phase: str, dry_run: bool) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "universe_id": UNIVERSE_ID,
        "generated_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "phase": phase,
        "dry_run": dry_run,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "active_symbols": active_symbols(),
        "correlated_clusters": CORRELATED_CLUSTERS,
        "warehouse_only_symbols": WAREHOUSE_ONLY_SYMBOLS,
        "results": results,
    }
    REPORT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    failures = [row for row in results if row["status"] != "ok"]
    lines = [
        "# Expanded Universe Build Report",
        "",
        f"- Universe id: `{UNIVERSE_ID}`",
        f"- Phase: `{phase}`",
        f"- Dry run: `{dry_run}`",
        f"- Window: `{START_DATE}` to `{END_DATE}`",
        f"- Active symbols: `{', '.join(active_symbols())}`",
        f"- Failed tasks: `{len(failures)}`",
        "",
        "## Correlated Clusters",
        "",
    ]
    for cluster, symbols in CORRELATED_CLUSTERS.items():
        lines.append(f"- `{cluster}`: `{', '.join(symbols)}`")
    lines.extend(["", "## Warehouse-Only Symbols", ""])
    for symbol, reason in WAREHOUSE_ONLY_SYMBOLS.items():
        lines.append(f"- `{symbol}`: {reason}")
    lines.extend(["", "## Task Summary", "", "| status | label | elapsed_s | key counts |", "|---|---|---:|---|"])
    for row in results:
        summary = row.get("summary") or {}
        counts = []
        for key in (
            "n_inserted",
            "n_errors",
            "n_candidates",
            "n_updated",
            "n_skipped_already_current",
            "n_skipped_no_data",
        ):
            if key in summary:
                counts.append(f"{key}={summary[key]}")
        lines.append(
            f"| {row['status']} | `{row['label']}` | {row['elapsed_seconds']:.1f} | {'; '.join(counts)} |"
        )
    if failures:
        lines.extend(["", "## Failures", ""])
        for row in failures:
            lines.extend([
                f"### {row['label']}",
                "",
                "```text",
                row.get("stderr_tail") or row.get("stdout_tail") or "",
                "```",
                "",
            ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def load_existing_results(*, phase: str, dry_run: bool) -> list[dict[str, Any]]:
    if not REPORT_JSON.exists():
        return []
    try:
        payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if payload.get("phase") != phase or bool(payload.get("dry_run")) != dry_run:
        return []
    results = payload.get("results")
    return results if isinstance(results, list) else []


def replace_result(results: list[dict[str, Any]], result: dict[str, Any]) -> None:
    label = result["label"]
    results[:] = [row for row in results if row.get("label") != label]
    results.append(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["scans", "outcomes", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only-detector")
    parser.add_argument("--only-computer")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-tasks", type=int, default=None)
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = load_existing_results(
        phase=args.phase,
        dry_run=args.dry_run,
    ) if args.resume else []
    completed_ok = {row["label"] for row in results if row.get("status") == "ok"}
    task_count = 0
    if args.phase in {"scans", "all"}:
        for label, cmd, timeout in scan_tasks(
            dry_run=args.dry_run,
            only_detector=args.only_detector,
        ):
            if label in completed_ok:
                print(f"SKIP {label} (already ok)")
                continue
            replace_result(results, run_command(label, cmd, timeout=timeout))
            write_report(results, phase=args.phase, dry_run=args.dry_run)
            task_count += 1
            if args.max_tasks is not None and task_count >= args.max_tasks:
                break
    if args.phase in {"outcomes", "all"}:
        if args.max_tasks is None or task_count < args.max_tasks:
            for label, cmd, timeout in outcome_tasks(
                dry_run=args.dry_run,
                only_computer=args.only_computer,
            ):
                if label in completed_ok:
                    print(f"SKIP {label} (already ok)")
                    continue
                replace_result(results, run_command(label, cmd, timeout=timeout))
                write_report(results, phase=args.phase, dry_run=args.dry_run)
                task_count += 1
                if args.max_tasks is not None and task_count >= args.max_tasks:
                    break

    write_report(results, phase=args.phase, dry_run=args.dry_run)
    failed = [row for row in results if row["status"] != "ok"]
    print(f"wrote {REPORT_JSON}")
    print(f"wrote {REPORT_MD}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
