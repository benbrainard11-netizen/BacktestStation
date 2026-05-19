"""CLI to validate a dataset snapshot.

Wraps `app.research.validation.runner.run_snapshot_validation`. Reads
the snapshot's partitions from the DB, runs gates against each, writes
a partition_validation_reports row + per-partition findings.

Usage:
    backend/.venv/Scripts/python.exe backend/scripts/data/validate_snapshot.py \
        <snapshot_id> [--strict] [--quick] [--schemas ohlcv-1m,tbbo] [--json]

The 247-built `bs data validate` CLI wraps this once Q3 lands.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]  # repo root
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import (  # noqa: E402
    create_all,
    make_engine,
    make_session_factory,
)
from app.db.models import (  # noqa: E402
    DatasetSnapshot,
    PartitionValidationReport,
)
from app.research.validation.runner import (  # noqa: E402
    RunnerConfig,
    run_snapshot_validation,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot_id", help="dataset_snapshots.snapshot_id (sha256-prefixed)")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Promote warn-severity gates to fail.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip slow gates (heavy JSON parses).",
    )
    parser.add_argument(
        "--schemas",
        default=None,
        help="Comma-separated schemas to validate. Default: all gates run.",
    )
    parser.add_argument(
        "--db-path",
        default=str(ROOT / "data" / "meta.sqlite"),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit summary JSON (single line) suitable for downstream tools.",
    )
    parser.add_argument(
        "--generator-version",
        default="v1",
        help="Stamp written into partition_validation_reports.generator_version.",
    )
    args = parser.parse_args()

    engine = make_engine(f"sqlite:///{args.db_path}")
    create_all(engine)  # idempotent; ensures tables exist
    sf = make_session_factory(engine)

    skip_gate_names: frozenset[str] = frozenset()
    if args.schemas:
        # When --schemas filter is given, we can't drop them by gate-name alone;
        # easiest approach: short-circuit in the runner by checking ctx.schema.
        # Implemented in the runner via PartitionContext routing already, but
        # we don't have a clean "skip schemas" knob yet. Filter happens at the
        # gate-registry lookup, so if a partition's schema is in the requested
        # set its gates run; otherwise no gates fire. The runner reads the
        # registry, so for now we just print which schemas the user asked for
        # and let all gates run.
        requested = {s.strip() for s in args.schemas.split(",")}
        print(f"# --schemas filter requested: {sorted(requested)} "
              f"(note: currently runs all schemas; per-schema filter is a TODO)",
              file=sys.stderr)

    with sf() as db:
        snapshot = db.query(DatasetSnapshot).filter_by(
            snapshot_id=args.snapshot_id
        ).first()
        if snapshot is None:
            print(f"ERROR: snapshot {args.snapshot_id!r} not found", file=sys.stderr)
            return 1

        cfg = RunnerConfig(
            strict=args.strict,
            generator_version=args.generator_version,
            skip_gate_names=skip_gate_names,
            quick=args.quick,
        )
        print(f"Validating snapshot: {args.snapshot_id}", file=sys.stderr)
        print(f"  name: {snapshot.name}", file=sys.stderr)
        print(f"  partitions: {snapshot.partition_count}", file=sys.stderr)
        print(f"  strict: {cfg.strict}, quick: {cfg.quick}", file=sys.stderr)

        report_id = run_snapshot_validation(
            snapshot_id=args.snapshot_id,
            db=db,
            config=cfg,
            progress=not args.json,
        )
        db.commit()

        report = db.get(PartitionValidationReport, report_id)
        summary = json.loads(report.summary_json) if report.summary_json else {}

    if args.json:
        out = {
            "report_id": report.id,
            "snapshot_id": args.snapshot_id,
            "total_partitions": report.total_partitions,
            "partitions_pass": report.partitions_pass,
            "partitions_warn": report.partitions_warn,
            "partitions_fail": report.partitions_fail,
            "generator_version": report.generator_version,
            "summary": summary,
        }
        print(json.dumps(out, indent=2, default=str))
    else:
        print()
        print(f"=== Report id={report.id} ===")
        print(f"Total partitions: {report.total_partitions}")
        print(f"  pass: {report.partitions_pass}")
        print(f"  warn: {report.partitions_warn}")
        print(f"  fail: {report.partitions_fail}")
        if summary.get("top_failing_gates"):
            print("Top failing gates:")
            for entry in summary["top_failing_gates"]:
                print(f"  {entry['gate']}: {entry['n_partitions']} partitions")
        print(f"Elapsed: {summary.get('elapsed_seconds')}s")

    # Exit code: 0 if all-pass, 1 if any fails (suitable for CI)
    return 0 if report.partitions_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
