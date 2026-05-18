"""Smoke-test the validation gate library against real partitions.

Not a real validator — runner.py + validate_snapshot.py do the real
work once 247's Q2 (partition_validation_reports table) lands. This
script just feeds a handful of real on-disk partitions through
`run_gates_on_partition` and prints what fires, so we can shake out
gate bugs before the runner is wired up.

Usage:
    python -m backend.scripts.data.smoke_validate_partitions
    python -m backend.scripts.data.smoke_validate_partitions --strict

Or invoke the file directly with the venv's python:
    backend/.venv/Scripts/python.exe \
        backend/scripts/data/smoke_validate_partitions.py
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

# Make `backend/` importable when running as a plain script.
_HERE = Path(__file__).resolve()
_BACKEND_ROOT = _HERE.parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.research.validation import (  # noqa: E402
    GATES_BY_SCHEMA,
    PartitionContext,
    run_gates_on_partition,
)


# Curated partition list: a mix of recent + old, 1m bars + research events.
# Update freely — the goal is breadth, not completeness.
SAMPLES = [
    {
        "label": "NQ.c.0 1m bars, recent",
        "path": Path(
            "D:/data/processed/bars/timeframe=1m/symbol=NQ.c.0/"
            "date=2026-05-15/part-000.parquet"
        ),
        "ctx": PartitionContext(
            schema="ohlcv-1m",
            symbol="NQ.c.0",
            date="2026-05-15",
            timeframe="1m",
        ),
    },
    {
        "label": "NQ.c.0 1m bars, 2015 (oldest era)",
        "path": Path(
            "D:/data/processed/bars/timeframe=1m/symbol=NQ.c.0/"
            "date=2015-01-02/part-000.parquet"
        ),
        "ctx": PartitionContext(
            schema="ohlcv-1m",
            symbol="NQ.c.0",
            date="2015-01-02",
            timeframe="1m",
        ),
    },
    {
        "label": "ES.c.0 1m bars, COVID-week (2020-03-12)",
        "path": Path(
            "D:/data/processed/bars/timeframe=1m/symbol=ES.c.0/"
            "date=2020-03-12/part-000.parquet"
        ),
        "ctx": PartitionContext(
            schema="ohlcv-1m",
            symbol="ES.c.0",
            date="2020-03-12",
            timeframe="1m",
        ),
    },
    {
        "label": "research_events: fvg_formation 2018 (first part)",
        "path_glob": (
            "data/research_events/feature_name=fvg_formation/"
            "event_year=2018/part-*.parquet"
        ),
        "ctx": PartitionContext(
            schema="research_events",
            feature_name="fvg_formation",
            event_year=2018,
        ),
    },
    {
        "label": "research_events: liquidity_sweep 2024 (first part)",
        "path_glob": (
            "data/research_events/feature_name=liquidity_sweep/"
            "event_year=2024/part-*.parquet"
        ),
        "ctx": PartitionContext(
            schema="research_events",
            feature_name="liquidity_sweep",
            event_year=2024,
        ),
    },
    {
        "label": "research_events: displacement_candle 2020 (first part)",
        "path_glob": (
            "data/research_events/feature_name=displacement_candle/"
            "event_year=2020/part-*.parquet"
        ),
        "ctx": PartitionContext(
            schema="research_events",
            feature_name="displacement_candle",
            event_year=2020,
        ),
    },
]


_REPO_ROOT = _BACKEND_ROOT.parent


def _resolve(sample: dict) -> Path | None:
    """Resolve a sample's path. Supports two forms:
    - `path`: literal Path (absolute or repo-relative)
    - `path_glob`: repo-relative glob; first match wins
    """
    if "path" in sample:
        path: Path = sample["path"]
        if path.is_absolute() and path.exists():
            return path
        alt = _REPO_ROOT / path
        return alt if alt.exists() else None
    if "path_glob" in sample:
        candidates = sorted((_REPO_ROOT).glob(sample["path_glob"]))
        return candidates[0] if candidates else None
    return None


def _read(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def _summarize(results, *, schema: str) -> dict:
    counter = Counter(r.severity for r in results)
    non_pass = [r for r in results if r.severity != "pass"]
    return {
        "schema": schema,
        "total_gates": len(results),
        "pass": counter.get("pass", 0),
        "warn": counter.get("warn", 0),
        "fail": counter.get("fail", 0),
        "non_pass": non_pass,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Promote warns to fails (mirrors planned `bs data validate --strict`).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Sample only the first N rows per partition (0 = full file).",
    )
    args = parser.parse_args()

    print(f"Validation library smoke — strict={args.strict}, limit={args.limit}")
    print(f"Registry: {sum(len(g) for g in GATES_BY_SCHEMA.values())} gates "
          f"across {len(GATES_BY_SCHEMA)} schemas\n")

    total_pass = 0
    total_warn = 0
    total_fail = 0
    partitions_seen = 0

    for sample in SAMPLES:
        label = sample["label"]
        ctx: PartitionContext = sample["ctx"]
        print(f"--- {label}")
        path = _resolve(sample)
        if path is None:
            print(f"    [skip] no file matched {sample.get('path') or sample.get('path_glob')!r}\n")
            continue
        print(f"    path: {path}")

        df = _read(path)
        partitions_seen += 1

        if args.limit and len(df) > args.limit:
            df = df.head(args.limit)
        print(f"    rows: {len(df)}, schema: {ctx.schema}")

        results = run_gates_on_partition(df, ctx, strict=args.strict)
        summary = _summarize(results, schema=ctx.schema)

        total_pass += summary["pass"]
        total_warn += summary["warn"]
        total_fail += summary["fail"]

        print(
            f"    gates: {summary['total_gates']} total / "
            f"pass={summary['pass']} warn={summary['warn']} "
            f"fail={summary['fail']}"
        )
        for r in summary["non_pass"]:
            print(f"      [{r.severity:>4}] {r.gate_name}: {r.message}")
            for k, v in (r.details or {}).items():
                if k in {"sample_row_indexes", "sample_bad_values"}:
                    continue  # noisy
                print(f"               {k} = {v}")
        print()

    print("=" * 64)
    print(
        f"OVERALL: {partitions_seen} partitions, "
        f"pass={total_pass}, warn={total_warn}, fail={total_fail}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
