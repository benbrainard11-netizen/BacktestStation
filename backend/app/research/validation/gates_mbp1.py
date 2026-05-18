"""Gates for `mbp-1` partitions.

Per `docs/VALIDATION_DESIGN.md`, 15 gates = all 12 TBBO gates +
3 MBP-1-specific:
- depth_zero (fail) — MBP-1 always reports level 0
- flags_in_range (warn) — uint8-compatible
- instrument_id_consistent (warn) — one instrument_id per partition;
  may legitimately flip on roll days

Column schema (`MBP1_SCHEMA`): same as TBBO plus `ts_in_delta`,
`depth`, `flags`, `bid_ct`, `ask_ct`.

Reuses the TBBO gate functions verbatim — same checks, different
schema registration.
"""

from __future__ import annotations

import pandas as pd

from app.research.validation import gates_tbbo
from app.research.validation.schema_gates import (
    Gate,
    GateResult,
    PartitionContext,
    failing,
    passing,
    register_gate,
)


SCHEMA = "mbp-1"

REQUIRED_COLS = gates_tbbo.REQUIRED_COLS


def _empty_pass(name: str) -> GateResult:
    return passing(name, details={"reason": "empty_partition"})


def _missing_col_fail(name: str, col: str) -> GateResult:
    return failing(
        name,
        count=0,
        message=f"required column {col!r} missing from partition",
        details={"missing_column": col},
    )


# ---------- mbp-1-specific gates ----------


def gate_depth_zero(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    """MBP-1 always reports top-of-book (depth == 0). Anything else
    indicates an MBP-N file mislabeled as MBP-1, or an upstream bug.
    """
    name = "depth_zero"
    if df.empty:
        return _empty_pass(name)
    if "depth" not in df.columns:
        return _missing_col_fail(name, "depth")
    depth = pd.to_numeric(df["depth"], errors="coerce")
    bad = depth.notna() & (depth != 0)
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        message=f"{count} rows have depth != 0",
        details={
            "sample_depths": depth[bad].head(10).astype(int).tolist(),
            "sample_row_indexes": df.index[bad].tolist()[:10],
        },
    )


def gate_flags_in_range(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    """flags column should fit in uint8 (0..255)."""
    name = "flags_in_range"
    if df.empty:
        return _empty_pass(name)
    if "flags" not in df.columns:
        return passing(name, details={"reason": "no_flags_column"})
    flags = pd.to_numeric(df["flags"], errors="coerce")
    bad = flags.notna() & ((flags < 0) | (flags > 255))
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        severity="warn",
        message=f"{count} rows have flags outside uint8 range",
        details={
            "sample_flags": flags[bad].head(10).astype(int).tolist(),
        },
    )


def gate_instrument_id_consistent(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    """A single (symbol, date) partition should have one instrument_id.

    Warns instead of failing because continuous-contract roll days
    legitimately span two instrument_ids when the rollover crosses
    midnight UTC. The runner can promote this to fail in --strict mode.
    """
    name = "instrument_id_consistent"
    if df.empty:
        return _empty_pass(name)
    if "instrument_id" not in df.columns:
        return passing(name, details={"reason": "no_instrument_id_column"})
    ids = df["instrument_id"].dropna().unique().tolist()
    if len(ids) <= 1:
        return passing(name, details={"instrument_id_count": len(ids)})
    return failing(
        name,
        count=len(ids),
        severity="warn",
        message=(
            f"{len(ids)} distinct instrument_ids in partition "
            f"(possible roll day)"
        ),
        details={"instrument_ids": [int(x) for x in ids[:10]]},
    )


# ---------- registration ----------
#
# Re-register all 12 TBBO gates under the mbp-1 schema name. The
# functions are pure; only the schema registry binding changes.
_TBBO_GATE_NAMES_TO_FNS = {
    "bid_le_ask": gates_tbbo.gate_bid_le_ask,
    "price_positive": gates_tbbo.gate_price_positive,
    "size_non_negative": gates_tbbo.gate_size_non_negative,
    "bid_sz_non_negative": gates_tbbo.gate_bid_sz_non_negative,
    "ask_sz_non_negative": gates_tbbo.gate_ask_sz_non_negative,
    "valid_action": gates_tbbo.gate_valid_action,
    "valid_side": gates_tbbo.gate_valid_side,
    "sequence_monotonic": gates_tbbo.gate_sequence_monotonic,
    "timestamp_monotonic_or_equal": gates_tbbo.gate_timestamp_monotonic_or_equal,
    "required_columns_not_null": gates_tbbo.gate_required_columns_not_null,
    "partition_symbol_matches_rows": gates_tbbo.gate_partition_symbol_matches_rows,
    "partition_date_matches_rows": gates_tbbo.gate_partition_date_matches_rows,
}

_DEFAULT_SEVERITY_FROM_TBBO = {
    "sequence_monotonic": "warn",
    "timestamp_monotonic_or_equal": "warn",
}


_GATES: list[Gate] = []

for _name, _fn in _TBBO_GATE_NAMES_TO_FNS.items():
    _GATES.append(
        Gate(
            name=_name,
            description=f"(see gates_tbbo.{_name}) — applied to mbp-1",
            schema=SCHEMA,
            fn=_fn,
            default_severity_on_hit=_DEFAULT_SEVERITY_FROM_TBBO.get(_name, "fail"),
        )
    )

_GATES.extend(
    [
        Gate(
            name="depth_zero",
            description="MBP-1 partitions report only top-of-book (depth==0)",
            schema=SCHEMA,
            fn=gate_depth_zero,
        ),
        Gate(
            name="flags_in_range",
            description="flags column fits in uint8 (0..255)",
            schema=SCHEMA,
            fn=gate_flags_in_range,
            default_severity_on_hit="warn",
        ),
        Gate(
            name="instrument_id_consistent",
            description=(
                "one instrument_id per (symbol, date); warn on multi-id "
                "(roll-day artifact)"
            ),
            schema=SCHEMA,
            fn=gate_instrument_id_consistent,
            default_severity_on_hit="warn",
        ),
    ]
)


for _gate in _GATES:
    register_gate(_gate)
