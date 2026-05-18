"""Gate framework: dataclasses + per-schema registry + runner.

Per `docs/VALIDATION_DESIGN.md`:

- A `Gate` is a callable check against a single partition DataFrame.
- A `GateResult` is its outcome: pass / warn / fail + count + details.
- `GATES_BY_SCHEMA` is the registry; each `gates_*.py` module appends.
- `run_gates_on_partition` runs every registered gate for one schema
  and returns the list of results.

Gates are stateless. They take a DataFrame and return a result. They
don't write to disk, don't touch the DB, don't read config files.
That's the runner's job.

Severity philosophy (from the design doc):
- Schema-level invariants (e.g., `high < low`) → fail
- Reasonable-anomaly (e.g., missing minutes during a holiday) → warn
- `--strict` mode promotes warns to fails (runner concern, not gate
  concern)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

import pandas as pd


Severity = Literal["pass", "warn", "fail"]


@dataclass(frozen=True, slots=True)
class GateResult:
    """Outcome of one gate against one partition.

    Attributes:
        gate_name: stable string id (matches `Gate.name`).
        severity: pass / warn / fail.
        count: number of rows that failed the check. 0 on pass.
        message: short human-readable summary.
        details: gate-specific extras (counts, sample row indexes,
            thresholds). Persisted as JSON in the findings table.
    """

    gate_name: str
    severity: Severity
    count: int
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PartitionContext:
    """Optional context handed to gates that need to validate the
    partition-key/data agreement (e.g., partition_symbol_matches_rows).

    Filled in by the runner from the partition's R2 key / parquet
    path. Gates that don't care can ignore it.
    """

    schema: str
    symbol: str | None = None
    date: str | None = None  # ISO yyyy-mm-dd
    timeframe: str | None = None
    feature_name: str | None = None
    event_year: int | None = None
    r2_key: str | None = None


# Function signature for a gate implementation. Returning a GateResult
# with severity="pass" and count=0 is the success path.
GateFn = Callable[[pd.DataFrame, PartitionContext], GateResult]


@dataclass(frozen=True, slots=True)
class Gate:
    """One registered gate.

    Attributes:
        name: stable id, snake_case, unique within a schema. Used as
            the value of `partition_validation_findings.gate_name`.
        description: short human-readable explanation.
        schema: which schema this gate applies to (ohlcv-1m, tbbo,
            mbp-1, research_events).
        fn: the evaluator. Takes (df, ctx) → GateResult.
        default_severity_on_hit: severity the gate emits when it finds
            at least one violation (gates may override per-row).
        applies_when: optional predicate; if returns False the gate is
            skipped. E.g., a gate that only runs on bars partitions can
            check the schema/timeframe here.
    """

    name: str
    description: str
    schema: str
    fn: GateFn
    default_severity_on_hit: Severity = "fail"
    applies_when: Callable[[PartitionContext], bool] | None = None


# ---------- registry ----------

# Per-schema list of gates. Modules append to this at import time. The
# runner walks `GATES_BY_SCHEMA[partition.schema]`.
GATES_BY_SCHEMA: dict[str, list[Gate]] = {
    "ohlcv-1m": [],
    "tbbo": [],
    "mbp-1": [],
    "research_events": [],
}


def register_gate(gate: Gate) -> None:
    """Register a gate against its schema.

    Re-registration under the same (schema, name) raises — duplicates
    are bugs, not features. Same name across different schemas is OK
    (e.g., `required_columns_not_null` shows up for every schema with
    its own column list).
    """
    if gate.schema not in GATES_BY_SCHEMA:
        raise ValueError(
            f"gate {gate.name!r}: unknown schema {gate.schema!r}. "
            f"Known: {sorted(GATES_BY_SCHEMA)}"
        )
    for existing in GATES_BY_SCHEMA[gate.schema]:
        if existing.name == gate.name:
            raise ValueError(
                f"gate {gate.name!r} already registered for schema "
                f"{gate.schema!r}"
            )
    GATES_BY_SCHEMA[gate.schema].append(gate)


def list_gates(schema: str) -> list[Gate]:
    """All gates registered for one schema, in registration order."""
    if schema not in GATES_BY_SCHEMA:
        raise KeyError(
            f"unknown schema {schema!r}. "
            f"Known: {sorted(GATES_BY_SCHEMA)}"
        )
    return list(GATES_BY_SCHEMA[schema])


# ---------- runner ----------


def run_gates_on_partition(
    df: pd.DataFrame,
    ctx: PartitionContext,
    *,
    strict: bool = False,
    skip_gate_names: set[str] | None = None,
) -> list[GateResult]:
    """Run every registered gate for `ctx.schema` against `df`.

    Args:
        df: the partition DataFrame. May be empty.
        ctx: partition context (schema, symbol, date, etc.).
        strict: if True, promote `warn` results to `fail`. Mirrors the
            `--strict` CLI flag.
        skip_gate_names: optional set of gate names to skip (e.g., the
            `--quick` flag would skip slow gates).

    Returns:
        One GateResult per gate, in registration order. Includes pass
        results — callers filter as needed (e.g., the findings table
        only stores non-pass results).
    """
    gates = list_gates(ctx.schema)
    skip = skip_gate_names or set()
    results: list[GateResult] = []

    for gate in gates:
        if gate.name in skip:
            continue
        if gate.applies_when is not None and not gate.applies_when(ctx):
            continue

        try:
            result = gate.fn(df, ctx)
        except Exception as exc:  # noqa: BLE001 — gates must not crash the runner
            result = GateResult(
                gate_name=gate.name,
                severity="fail",
                count=-1,
                message=f"gate raised {type(exc).__name__}: {exc}",
                details={"exception_type": type(exc).__name__},
            )

        if strict and result.severity == "warn":
            result = GateResult(
                gate_name=result.gate_name,
                severity="fail",
                count=result.count,
                message=result.message + " (promoted to fail by --strict)",
                details={**result.details, "promoted_from": "warn"},
            )

        results.append(result)

    return results


# ---------- helpers for gate authors ----------


def passing(gate_name: str, *, details: dict[str, Any] | None = None) -> GateResult:
    """Build a clean pass result. Gate authors call this on the happy
    path to keep call sites short."""
    return GateResult(
        gate_name=gate_name,
        severity="pass",
        count=0,
        message="",
        details=details or {},
    )


def failing(
    gate_name: str,
    *,
    count: int,
    message: str,
    severity: Severity = "fail",
    details: dict[str, Any] | None = None,
) -> GateResult:
    """Build a non-pass result with the given severity."""
    return GateResult(
        gate_name=gate_name,
        severity=severity,
        count=count,
        message=message,
        details=details or {},
    )
