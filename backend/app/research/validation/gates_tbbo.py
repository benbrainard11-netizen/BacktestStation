"""Gates for `tbbo` partitions.

Per `docs/VALIDATION_DESIGN.md`, 12 gates:
- Quote sanity: bid<=ask, prices/sizes non-negative (5)
- Vocabulary: valid action, valid side (2)
- Ordering: sequence monotonic, timestamp non-decreasing (2 warn)
- Required columns not null (1)
- Partition key agreement: symbol, date (2)

Column schema (`TBBO_SCHEMA`):
    ts_event, ts_recv, symbol, action, side, price, size,
    bid_px, ask_px, bid_sz, ask_sz, publisher_id, instrument_id,
    sequence
"""

from __future__ import annotations

import pandas as pd

from app.research.validation.schema_gates import (
    Gate,
    GateResult,
    PartitionContext,
    failing,
    passing,
    register_gate,
)


SCHEMA = "tbbo"

REQUIRED_COLS = (
    "ts_event",
    "symbol",
    "price",
    "size",
    "bid_px",
    "ask_px",
)

VALID_ACTIONS = frozenset({"T", "A", "B", "C", "M", "R"})
VALID_SIDES = frozenset({"A", "B", "N"})

SEQUENCE_MONOTONIC_FAIL_THRESHOLD = 100


def _empty_pass(name: str) -> GateResult:
    return passing(name, details={"reason": "empty_partition"})


def _missing_col_fail(name: str, col: str) -> GateResult:
    return failing(
        name,
        count=0,
        message=f"required column {col!r} missing from partition",
        details={"missing_column": col},
    )


# ---------- quote / trade sanity ----------


def gate_bid_le_ask(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    name = "bid_le_ask"
    if df.empty:
        return _empty_pass(name)
    for col in ("bid_px", "ask_px"):
        if col not in df.columns:
            return _missing_col_fail(name, col)
    bid = pd.to_numeric(df["bid_px"], errors="coerce")
    ask = pd.to_numeric(df["ask_px"], errors="coerce")
    both_present = bid.notna() & ask.notna()
    bad = both_present & (bid > ask)
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        message=f"{count} rows have bid_px > ask_px",
        details={"sample_row_indexes": df.index[bad].tolist()[:10]},
    )


def _check_positive(df: pd.DataFrame, name: str, col: str) -> GateResult:
    if df.empty:
        return _empty_pass(name)
    if col not in df.columns:
        return _missing_col_fail(name, col)
    s = pd.to_numeric(df[col], errors="coerce")
    bad = s.notna() & (s <= 0)
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        message=f"{count} rows have non-positive {col}",
        details={"sample_row_indexes": df.index[bad].tolist()[:10]},
    )


def _check_non_negative(df: pd.DataFrame, name: str, col: str) -> GateResult:
    if df.empty:
        return _empty_pass(name)
    if col not in df.columns:
        return _missing_col_fail(name, col)
    s = pd.to_numeric(df[col], errors="coerce")
    bad = s.notna() & (s < 0)
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        message=f"{count} rows have negative {col}",
        details={"sample_row_indexes": df.index[bad].tolist()[:10]},
    )


def gate_price_positive(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    return _check_positive(df, "price_positive", "price")


def gate_size_non_negative(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    return _check_non_negative(df, "size_non_negative", "size")


def gate_bid_sz_non_negative(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    return _check_non_negative(df, "bid_sz_non_negative", "bid_sz")


def gate_ask_sz_non_negative(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    return _check_non_negative(df, "ask_sz_non_negative", "ask_sz")


# ---------- vocabulary ----------


def _check_membership(
    df: pd.DataFrame,
    name: str,
    col: str,
    allowed: frozenset[str],
) -> GateResult:
    if df.empty:
        return _empty_pass(name)
    if col not in df.columns:
        return _missing_col_fail(name, col)
    s = df[col].astype(str)
    bad = ~s.isin(allowed)
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    sample = s[bad].head(5).tolist()
    return failing(
        name,
        count=count,
        message=(
            f"{count} rows have {col} outside allowed set "
            f"{sorted(allowed)}: samples {sample}"
        ),
        details={
            "sample_bad_values": sample,
            "allowed": sorted(allowed),
        },
    )


def gate_valid_action(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    return _check_membership(df, "valid_action", "action", VALID_ACTIONS)


def gate_valid_side(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    return _check_membership(df, "valid_side", "side", VALID_SIDES)


# ---------- ordering ----------


def gate_sequence_monotonic(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    """Sequence numbers monotonic non-decreasing per partition.

    Warn (not fail) — some publishers reorder events across feeds and
    we want to surface but not reject. Promote to fail in --strict mode
    via the runner.
    """
    name = "sequence_monotonic"
    if df.empty:
        return _empty_pass(name)
    if "sequence" not in df.columns:
        return passing(name, details={"reason": "no_sequence_column"})
    seq = pd.to_numeric(df["sequence"], errors="coerce")
    inversions = int((seq.diff() < 0).sum())
    if inversions == 0:
        return passing(name)
    severity = "fail" if inversions > SEQUENCE_MONOTONIC_FAIL_THRESHOLD else "warn"
    return failing(
        name,
        count=inversions,
        severity=severity,
        message=(
            f"{inversions} sequence inversions "
            f"(threshold fail>{SEQUENCE_MONOTONIC_FAIL_THRESHOLD})"
        ),
        details={"inversions": inversions},
    )


def gate_timestamp_monotonic_or_equal(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    """ts_event is non-decreasing within the partition.

    Warn — late-arriving prints + venue reordering are tolerable. The
    backtester resolves trade order via sequence + ts together; this
    gate flags egregious drift, not normal reordering.
    """
    name = "timestamp_monotonic_or_equal"
    if df.empty:
        return _empty_pass(name)
    if "ts_event" not in df.columns:
        return _missing_col_fail(name, "ts_event")
    ts = pd.to_datetime(df["ts_event"], errors="coerce", utc=True)
    deltas = ts.diff()
    bad = deltas.notna() & (deltas < pd.Timedelta(0))
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        severity="warn",
        message=f"{count} ts_event values decrease vs previous row",
        details={"sample_row_indexes": df.index[bad].tolist()[:10]},
    )


# ---------- required columns not null ----------


def gate_required_columns_not_null(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    name = "required_columns_not_null"
    if df.empty:
        return _empty_pass(name)
    null_counts: dict[str, int] = {}
    missing_cols: list[str] = []
    for col in REQUIRED_COLS:
        if col not in df.columns:
            missing_cols.append(col)
            continue
        n = int(df[col].isna().sum())
        if n > 0:
            null_counts[col] = n
    if missing_cols:
        return failing(
            name,
            count=0,
            message=f"required columns missing: {missing_cols}",
            details={"missing_columns": missing_cols},
        )
    if not null_counts:
        return passing(name)
    total = sum(null_counts.values())
    return failing(
        name,
        count=total,
        message=f"{total} null values across required columns: {null_counts}",
        details={"null_counts": null_counts},
    )


# ---------- partition-key agreement ----------


def gate_partition_symbol_matches_rows(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    name = "partition_symbol_matches_rows"
    if df.empty:
        return _empty_pass(name)
    if ctx.symbol is None:
        return passing(name, details={"reason": "no_partition_symbol_in_ctx"})
    if "symbol" not in df.columns:
        return _missing_col_fail(name, "symbol")
    bad = df["symbol"].astype(str) != str(ctx.symbol)
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        message=f"{count} rows have symbol != partition key {ctx.symbol!r}",
        details={
            "partition_symbol": ctx.symbol,
            "sample_row_symbols": df.loc[bad, "symbol"]
            .astype(str)
            .head(5)
            .tolist(),
        },
    )


def gate_partition_date_matches_rows(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    name = "partition_date_matches_rows"
    if df.empty:
        return _empty_pass(name)
    if ctx.date is None:
        return passing(name, details={"reason": "no_partition_date_in_ctx"})
    if "ts_event" not in df.columns:
        return _missing_col_fail(name, "ts_event")
    ts = pd.to_datetime(df["ts_event"], errors="coerce", utc=True)
    row_dates = ts.dt.strftime("%Y-%m-%d")
    bad = ts.notna() & (row_dates != ctx.date)
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        message=(
            f"{count} rows have ts_event.date != partition key {ctx.date!r}"
        ),
        details={
            "partition_date": ctx.date,
            "sample_row_dates": row_dates[bad].head(5).tolist(),
        },
    )


# ---------- registration ----------

_GATES: tuple[Gate, ...] = (
    Gate(
        name="bid_le_ask",
        description="bid_px <= ask_px on every quote",
        schema=SCHEMA,
        fn=gate_bid_le_ask,
    ),
    Gate(
        name="price_positive",
        description="price > 0 on every trade print",
        schema=SCHEMA,
        fn=gate_price_positive,
    ),
    Gate(
        name="size_non_negative",
        description="size >= 0",
        schema=SCHEMA,
        fn=gate_size_non_negative,
    ),
    Gate(
        name="bid_sz_non_negative",
        description="bid_sz >= 0",
        schema=SCHEMA,
        fn=gate_bid_sz_non_negative,
    ),
    Gate(
        name="ask_sz_non_negative",
        description="ask_sz >= 0",
        schema=SCHEMA,
        fn=gate_ask_sz_non_negative,
    ),
    Gate(
        name="valid_action",
        description=f"action in {sorted(VALID_ACTIONS)}",
        schema=SCHEMA,
        fn=gate_valid_action,
    ),
    Gate(
        name="valid_side",
        description=f"side in {sorted(VALID_SIDES)}",
        schema=SCHEMA,
        fn=gate_valid_side,
    ),
    Gate(
        name="sequence_monotonic",
        description=(
            f"sequence numbers non-decreasing "
            f"(warn any, fail>{SEQUENCE_MONOTONIC_FAIL_THRESHOLD})"
        ),
        schema=SCHEMA,
        fn=gate_sequence_monotonic,
        default_severity_on_hit="warn",
    ),
    Gate(
        name="timestamp_monotonic_or_equal",
        description="ts_event non-decreasing within partition",
        schema=SCHEMA,
        fn=gate_timestamp_monotonic_or_equal,
        default_severity_on_hit="warn",
    ),
    Gate(
        name="required_columns_not_null",
        description=f"required columns ({', '.join(REQUIRED_COLS)}) not null",
        schema=SCHEMA,
        fn=gate_required_columns_not_null,
    ),
    Gate(
        name="partition_symbol_matches_rows",
        description="partition symbol key matches every row's symbol",
        schema=SCHEMA,
        fn=gate_partition_symbol_matches_rows,
    ),
    Gate(
        name="partition_date_matches_rows",
        description="partition date key matches every row's ts_event.date",
        schema=SCHEMA,
        fn=gate_partition_date_matches_rows,
    ),
)


for _gate in _GATES:
    register_gate(_gate)
