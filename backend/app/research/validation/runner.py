"""Snapshot validation runner.

Walks the partitions of a `DatasetSnapshot` row, runs the appropriate
per-schema gates on each one, and writes a `PartitionValidationReport`
row + N `PartitionValidationFinding` rows to the DB.

Per `docs/VALIDATION_DESIGN.md`. The framework + 48 gates live in
`schema_gates.py` and `gates_*.py`. This module just wires them up to
the warehouse + DB.

Usage from Python:

    from app.db.session import make_engine, make_session_factory
    from app.research.validation.runner import run_snapshot_validation

    engine = make_engine()
    sf = make_session_factory(engine)
    with sf() as db:
        report_id = run_snapshot_validation(
            snapshot_id="sha256-abc...",
            db=db,
            strict=False,
        )
    print(f"wrote report {report_id}")

Usage from CLI: `backend/scripts/data/validate_snapshot.py` wraps this.

Bar/event lookup: parquet files are read from local disk. R2 keys are
mapped to local paths via simple prefix substitution:

    processed/bars/...          -> D:/data/processed/bars/...
    data/research_events/...    -> <repo>/data/research_events/...
    raw/...                     -> D:/data/raw/...

A `--local-roots` override is provided for tests or non-standard layouts.
"""

from __future__ import annotations

import json
import logging
import re
import time as time_mod
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    DatasetSnapshot,
    DatasetSnapshotPartition,
    PartitionValidationFinding,
    PartitionValidationReport,
)
from app.research.validation.schema_gates import (
    GATES_BY_SCHEMA,
    GateResult,
    PartitionContext,
    run_gates_on_partition,
)


log = logging.getLogger(__name__)


# Default local-root mapping. Keys are R2 prefix patterns (without bucket).
DEFAULT_LOCAL_ROOTS = {
    # Prefix substitution: r2_key starting with key gets remapped to value + remainder.
    # E.g., "processed/bars/timeframe=1m/.../part-000.parquet"
    #     -> Path("D:/data/processed/bars/") + "timeframe=1m/.../part-000.parquet"
    "processed/bars/": Path(r"D:/data/processed/bars/"),
    "raw/": Path(r"D:/data/raw/"),
    "data/research_events/": None,  # repo-root relative; filled in at runtime
}

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class RunnerConfig:
    """Tweakable knobs for one runner invocation."""

    strict: bool = False
    generator_version: str = "v1"
    skip_gate_names: frozenset[str] = frozenset()
    quick: bool = False  # in --quick mode, skip slow gates (heuristic)
    local_roots: dict[str, Path] | None = None


# ---------- r2_key parsing ----------

# Example keys:
#   processed/bars/timeframe=1m/symbol=NQ.c.0/date=2020-03-12/part-000.parquet
#   processed/bars/timeframe=tbbo/symbol=NQ.c.0/date=2025-08-05/part-000.parquet
#   processed/bars/timeframe=mbp-1/symbol=NQ.c.0/date=2026-03-02/part-000.parquet
#   data/research_events/feature_name=fvg_formation/event_year=2020/part-000040.parquet
#   raw/databento/...  (raw DBN; we don't validate these directly)

_TIMEFRAME_TO_SCHEMA = {
    "1m": "ohlcv-1m",
    "tbbo": "tbbo",
    "mbp-1": "mbp-1",
}

_BARS_RE = re.compile(
    r"processed/bars/timeframe=(?P<tf>[^/]+)/symbol=(?P<symbol>[^/]+)/"
    r"date=(?P<date>\d{4}-\d{2}-\d{2})/"
)
_RESEARCH_EVENTS_RE = re.compile(
    r"data/research_events/feature_name=(?P<feature>[^/]+)/"
    r"event_year=(?P<year>\d{4})/"
)


def parse_r2_key(r2_key: str) -> PartitionContext | None:
    """Parse an R2 key into a PartitionContext.

    Returns None if the key doesn't match a known partition pattern
    (e.g., raw DBN files, which we don't run gates against).
    """
    bars_match = _BARS_RE.search(r2_key)
    if bars_match:
        tf = bars_match.group("tf")
        schema = _TIMEFRAME_TO_SCHEMA.get(tf)
        if schema is None:
            return None
        return PartitionContext(
            schema=schema,
            symbol=bars_match.group("symbol"),
            date=bars_match.group("date"),
            timeframe=tf,
            r2_key=r2_key,
        )

    re_match = _RESEARCH_EVENTS_RE.search(r2_key)
    if re_match:
        return PartitionContext(
            schema="research_events",
            feature_name=re_match.group("feature"),
            event_year=int(re_match.group("year")),
            r2_key=r2_key,
        )

    return None


def _r2_key_to_local_path(
    r2_key: str, local_roots: dict[str, Path]
) -> Path | None:
    """Map an R2 key to a local-disk path using `local_roots`."""
    for prefix, root in local_roots.items():
        if r2_key.startswith(prefix):
            relative = r2_key[len(prefix):]
            return root / relative
    return None


# ---------- per-partition gates ----------


# Gates that load substantial data; --quick mode skips these.
SLOW_GATES = frozenset(
    {
        # research_events JSON-validating gates iterate row-by-row
        "event_data_valid_json",
        "outcomes_valid_json_if_present",
        # missing_minutes does sorted unique on timestamps; fine but worth
        # gating if we add heavier checks later
    }
)


def _resolve_local_roots(
    user_roots: dict[str, Path] | None,
) -> dict[str, Path]:
    """Build the effective local_roots dict."""
    resolved = dict(DEFAULT_LOCAL_ROOTS)
    # Fill in the runtime default for research_events
    if resolved["data/research_events/"] is None:
        resolved["data/research_events/"] = REPO_ROOT / "data" / "research_events"
    if user_roots:
        resolved.update(user_roots)
    return resolved


def _load_partition(local_path: Path) -> pd.DataFrame | None:
    """Read a parquet partition. Returns None if file is missing."""
    if not local_path.exists():
        return None
    try:
        return pd.read_parquet(local_path)
    except Exception as exc:  # noqa: BLE001 — surface as a gate error
        log.warning("failed to read %s: %s", local_path, exc)
        return None


def _aggregate_partition_severity(results: Iterable[GateResult]) -> str:
    """Roll up per-gate severities to a single per-partition status."""
    saw_warn = False
    for r in results:
        if r.severity == "fail":
            return "fail"
        if r.severity == "warn":
            saw_warn = True
    return "warn" if saw_warn else "pass"


# ---------- main runner ----------


def run_snapshot_validation(
    *,
    snapshot_id: str,
    db: Session,
    config: RunnerConfig | None = None,
    progress: bool = True,
) -> int:
    """Run validation gates against every partition in the snapshot.

    Args:
        snapshot_id: the dataset_snapshots.snapshot_id to validate.
        db: open SQLAlchemy session. Caller commits.
        config: RunnerConfig; defaults to strict=False, generator_version="v1".
        progress: print one-line progress markers per N partitions.

    Returns:
        The id of the inserted PartitionValidationReport row.

    Raises:
        ValueError: if the snapshot doesn't exist or has no partitions.
    """
    cfg = config or RunnerConfig()
    local_roots = _resolve_local_roots(cfg.local_roots)

    # Build the effective skip-set (union of user skips + quick-mode slow gates)
    skip = set(cfg.skip_gate_names)
    if cfg.quick:
        skip.update(SLOW_GATES)

    snapshot = db.scalar(
        select(DatasetSnapshot).where(DatasetSnapshot.snapshot_id == snapshot_id)
    )
    if snapshot is None:
        raise ValueError(f"snapshot {snapshot_id!r} not found")
    partitions: list[DatasetSnapshotPartition] = list(snapshot.partitions)
    if not partitions:
        raise ValueError(f"snapshot {snapshot_id!r} has no partitions")

    log.info(
        "validating snapshot %s (%d partitions, strict=%s, quick=%s)",
        snapshot_id, len(partitions), cfg.strict, cfg.quick,
    )

    t0 = time_mod.time()
    pass_count = warn_count = fail_count = 0
    by_schema: dict[str, dict[str, int]] = defaultdict(
        lambda: {"pass": 0, "warn": 0, "fail": 0, "total": 0}
    )
    failing_gate_counter: Counter[str] = Counter()
    findings_buffer: list[dict] = []

    for i, part in enumerate(partitions, start=1):
        ctx = parse_r2_key(part.r2_key)
        if ctx is None:
            # Unknown partition type; record as a skipped finding
            findings_buffer.append({
                "partition_r2_key": part.r2_key,
                "schema": "unknown",
                "symbol": None,
                "date": None,
                "gate_name": "_partition_parser",
                "severity": "warn",
                "message": "r2_key doesn't match any known partition pattern",
                "details_json": None,
            })
            warn_count += 1
            by_schema["unknown"]["warn"] += 1
            by_schema["unknown"]["total"] += 1
            continue

        if ctx.schema not in GATES_BY_SCHEMA:
            findings_buffer.append({
                "partition_r2_key": part.r2_key,
                "schema": ctx.schema,
                "symbol": ctx.symbol,
                "date": ctx.date,
                "gate_name": "_unknown_schema",
                "severity": "fail",
                "message": f"no gates registered for schema {ctx.schema!r}",
                "details_json": None,
            })
            fail_count += 1
            by_schema[ctx.schema]["fail"] += 1
            by_schema[ctx.schema]["total"] += 1
            continue

        local_path = _r2_key_to_local_path(part.r2_key, local_roots)
        if local_path is None:
            findings_buffer.append({
                "partition_r2_key": part.r2_key,
                "schema": ctx.schema,
                "symbol": ctx.symbol,
                "date": ctx.date,
                "gate_name": "_local_path_unmapped",
                "severity": "warn",
                "message": "r2_key doesn't map to any local root",
                "details_json": None,
            })
            warn_count += 1
            by_schema[ctx.schema]["warn"] += 1
            by_schema[ctx.schema]["total"] += 1
            continue

        df = _load_partition(local_path)
        if df is None:
            findings_buffer.append({
                "partition_r2_key": part.r2_key,
                "schema": ctx.schema,
                "symbol": ctx.symbol,
                "date": ctx.date,
                "gate_name": "_partition_load",
                "severity": "fail",
                "message": f"failed to load partition from {local_path}",
                "details_json": json.dumps({"local_path": str(local_path)}),
            })
            fail_count += 1
            by_schema[ctx.schema]["fail"] += 1
            by_schema[ctx.schema]["total"] += 1
            continue

        results = run_gates_on_partition(
            df, ctx, strict=cfg.strict, skip_gate_names=skip
        )
        partition_severity = _aggregate_partition_severity(results)
        if partition_severity == "fail":
            fail_count += 1
        elif partition_severity == "warn":
            warn_count += 1
        else:
            pass_count += 1
        by_schema[ctx.schema][partition_severity] += 1
        by_schema[ctx.schema]["total"] += 1

        for r in results:
            if r.severity == "pass":
                continue
            findings_buffer.append({
                "partition_r2_key": part.r2_key,
                "schema": ctx.schema,
                "symbol": ctx.symbol,
                "date": ctx.date,
                "gate_name": r.gate_name,
                "severity": r.severity,
                "message": r.message,
                "details_json": json.dumps(r.details) if r.details else None,
            })
            if r.severity == "fail":
                failing_gate_counter[r.gate_name] += 1

        if progress and (i % 100 == 0 or i == len(partitions)):
            elapsed = time_mod.time() - t0
            rate = i / elapsed if elapsed > 0 else 0
            print(
                f"  [{i}/{len(partitions)}] "
                f"pass={pass_count} warn={warn_count} fail={fail_count}  "
                f"({rate:.1f} parts/sec)",
                flush=True,
            )

    summary = {
        "by_schema": dict(by_schema),
        "by_severity": {
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
        },
        "top_failing_gates": [
            {"gate": g, "n_partitions": c}
            for g, c in failing_gate_counter.most_common(10)
        ],
        "elapsed_seconds": round(time_mod.time() - t0, 2),
        "strict_mode": cfg.strict,
        "quick_mode": cfg.quick,
    }

    report = PartitionValidationReport(
        snapshot_id=snapshot_id,
        generator_version=cfg.generator_version,
        total_partitions=len(partitions),
        partitions_pass=pass_count,
        partitions_warn=warn_count,
        partitions_fail=fail_count,
        summary_json=json.dumps(summary),
        status="completed",
    )
    db.add(report)
    db.flush()  # populate report.id

    for f in findings_buffer:
        db.add(
            PartitionValidationFinding(
                report_id=report.id,
                partition_r2_key=f["partition_r2_key"],
                schema=f["schema"],
                symbol=f["symbol"],
                date=f["date"],
                gate_name=f["gate_name"],
                severity=f["severity"],
                message=f["message"],
                details_json=f["details_json"],
            )
        )

    # Soft-link the report onto the snapshot. Caller commits the txn.
    snapshot.validation_report_id = report.id

    return int(report.id)
