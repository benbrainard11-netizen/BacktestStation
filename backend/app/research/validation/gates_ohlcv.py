"""Gates for `ohlcv-1m` partitions.

Per `docs/VALIDATION_DESIGN.md`, 14 gates checking:
- OHLC invariants (5 gates): high>=open, high>=close, high>=low,
  low<=open, low<=close
- Non-negativity (2): volume, trade_count
- VWAP in range (1): low <= vwap <= high when volume > 0 (warn)
- Timestamps (2): unique per (symbol, date), 1m-aligned
- Missing minutes (1): gaps in RTH/24h, warn @ >50/day, fail @ >200/day
- Required columns not null (1)
- Partition key agreement (2): symbol, date

Each gate is a pure function `(df, ctx) -> GateResult`. The runner
calls them; they don't read the disk, don't touch the DB.

Column schema (per `backend/app/data/schema.py:BARS_1M_SCHEMA`):
    ts_event (UTC ts), symbol, open, high, low, close, volume,
    trade_count, vwap
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


SCHEMA = "ohlcv-1m"

# --- threshold defaults (overridable via runner config, not here) ---
MISSING_MINUTES_WARN_THRESHOLD = 50
MISSING_MINUTES_FAIL_THRESHOLD = 200

REQUIRED_COLS = (
    "ts_event",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


# ---------- helpers ----------


def _empty_pass(name: str) -> GateResult:
    return passing(name, details={"reason": "empty_partition"})


def _missing_col_fail(name: str, col: str) -> GateResult:
    return failing(
        name,
        count=0,
        message=f"required column {col!r} missing from partition",
        severity="fail",
        details={"missing_column": col},
    )


# ---------- OHLC invariant gates ----------


def _check_pair(
    df: pd.DataFrame,
    name: str,
    col_a: str,
    col_b: str,
    *,
    op: str,  # "ge" or "le"
) -> GateResult:
    """Generic two-column comparison gate.

    `op="ge"` checks col_a >= col_b. `op="le"` checks col_a <= col_b.
    Returns a fail GateResult with the offending row count + a small
    sample of indexes when violations exist.
    """
    if df.empty:
        return _empty_pass(name)
    for col in (col_a, col_b):
        if col not in df.columns:
            return _missing_col_fail(name, col)

    a = pd.to_numeric(df[col_a], errors="coerce")
    b = pd.to_numeric(df[col_b], errors="coerce")
    # NaN comparisons are False; only flag rows where both sides are
    # finite. NaN handling is the required_columns_not_null gate's job.
    both_present = a.notna() & b.notna()
    if op == "ge":
        bad = both_present & (a < b)
    elif op == "le":
        bad = both_present & (a > b)
    else:  # pragma: no cover — guarded by callers
        raise ValueError(f"unknown op {op!r}")

    count = int(bad.sum())
    if count == 0:
        return passing(name)

    sample = df.index[bad].tolist()[:10]
    return failing(
        name,
        count=count,
        message=(
            f"{count} rows violate {col_a} {'>=' if op == 'ge' else '<='} "
            f"{col_b}"
        ),
        details={"sample_row_indexes": sample, "op": op},
    )


def gate_ohlc_high_ge_open(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    return _check_pair(df, "ohlc_high_ge_open", "high", "open", op="ge")


def gate_ohlc_high_ge_close(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    return _check_pair(df, "ohlc_high_ge_close", "high", "close", op="ge")


def gate_ohlc_high_ge_low(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    return _check_pair(df, "ohlc_high_ge_low", "high", "low", op="ge")


def gate_ohlc_low_le_open(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    return _check_pair(df, "ohlc_low_le_open", "low", "open", op="le")


def gate_ohlc_low_le_close(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    return _check_pair(df, "ohlc_low_le_close", "low", "close", op="le")


# ---------- non-negativity gates ----------


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


def gate_volume_non_negative(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    return _check_non_negative(df, "volume_non_negative", "volume")


def gate_trade_count_non_negative(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    return _check_non_negative(df, "trade_count_non_negative", "trade_count")


# ---------- vwap in range ----------


def gate_vwap_in_range(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    """VWAP should land between low and high on bars with volume.

    Warn (not fail) — VWAP may legitimately differ from low/high range
    when there's tiny volume + price drift across rebases, or when
    upstream computes VWAP across the whole minute including the next
    bar's first trade. We flag, we don't reject.
    """
    name = "vwap_in_range"
    if df.empty:
        return _empty_pass(name)
    for col in ("low", "high", "vwap", "volume"):
        if col not in df.columns:
            return _missing_col_fail(name, col)

    vwap = pd.to_numeric(df["vwap"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")
    high = pd.to_numeric(df["high"], errors="coerce")
    volume = pd.to_numeric(df["volume"], errors="coerce")

    eligible = vwap.notna() & low.notna() & high.notna() & (volume > 0)
    bad = eligible & ((vwap < low) | (vwap > high))
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        severity="warn",
        message=f"{count} bars have vwap outside [low, high]",
        details={"sample_row_indexes": df.index[bad].tolist()[:10]},
    )


# ---------- timestamp gates ----------


def gate_timestamp_unique(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    """No duplicate (symbol, ts_event) rows.

    A partition is a single (symbol, date) so duplicates always indicate
    a merge/ingest bug.
    """
    name = "timestamp_unique"
    if df.empty:
        return _empty_pass(name)
    for col in ("ts_event", "symbol"):
        if col not in df.columns:
            return _missing_col_fail(name, col)

    dup_mask = df.duplicated(subset=["symbol", "ts_event"], keep=False)
    count = int(dup_mask.sum())
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        message=f"{count} duplicate (symbol, ts_event) rows",
        details={"sample_row_indexes": df.index[dup_mask].tolist()[:10]},
    )


def gate_timestamp_aligned_1m(
    df: pd.DataFrame, ctx: PartitionContext
) -> GateResult:
    """All ts_event values are exact-minute boundaries (no seconds, no
    sub-second drift)."""
    name = "timestamp_aligned_1m"
    if df.empty:
        return _empty_pass(name)
    if "ts_event" not in df.columns:
        return _missing_col_fail(name, "ts_event")

    ts = pd.to_datetime(df["ts_event"], errors="coerce", utc=True)
    # Floor-then-compare avoids pandas dtype precision pitfalls (some
    # builds store as datetime64[us, UTC] not datetime64[ns, UTC], so
    # int64 cast yields microseconds-since-epoch and a fixed-nanos modulo
    # produces wrong results).
    floored = ts.dt.floor("1min")
    bad = ts.notna() & (ts != floored)
    count = int(bad.sum())
    if count == 0:
        return passing(name)
    return failing(
        name,
        count=count,
        message=f"{count} ts_event values are not 1m-aligned",
        details={"sample_row_indexes": df.index[bad].tolist()[:10]},
    )


# ---------- missing minutes ----------


def gate_missing_minutes(df: pd.DataFrame, ctx: PartitionContext) -> GateResult:
    """Count minute-gaps within the partition.

    Heuristic: count missing minutes between the first and last bar in
    the partition. Doesn't try to match a specific session calendar —
    that would require contract-by-contract session tables. The threshold
    is generous (>50 to warn, >200 to fail) because non-RTH partitions
    legitimately have lots of low-activity minutes that may not have
    trades.

    Note: an "empty" bar from upstream isn't counted as missing here —
    we only check the (first, last) range. To detect "the partition is
    missing the entire afternoon" you need the lineage tool (out of
    scope for v1).
    """
    name = "missing_minutes"
    if df.empty:
        return _empty_pass(name)
    if "ts_event" not in df.columns:
        return _missing_col_fail(name, "ts_event")

    ts = pd.to_datetime(df["ts_event"], errors="coerce", utc=True).dropna()
    if len(ts) < 2:
        return passing(name, details={"reason": "fewer_than_2_bars"})

    ts = ts.sort_values().drop_duplicates()
    first = ts.iloc[0]
    last = ts.iloc[-1]
    expected = int((last - first).total_seconds() // 60) + 1
    actual = len(ts)
    missing = max(0, expected - actual)

    if missing == 0:
        return passing(name)

    if missing > MISSING_MINUTES_FAIL_THRESHOLD:
        severity = "fail"
    elif missing > MISSING_MINUTES_WARN_THRESHOLD:
        severity = "warn"
    else:
        # Below warn threshold: small gaps are tolerable, log as pass
        # with detail so it surfaces only in --strict mode.
        return passing(
            name,
            details={
                "missing_minutes": missing,
                "first": str(first),
                "last": str(last),
                "below_warn_threshold": True,
            },
        )

    return failing(
        name,
        count=missing,
        severity=severity,
        message=(
            f"{missing} missing minutes between {first} and {last} "
            f"(threshold warn>{MISSING_MINUTES_WARN_THRESHOLD}, "
            f"fail>{MISSING_MINUTES_FAIL_THRESHOLD})"
        ),
        details={
            "missing_minutes": missing,
            "first": str(first),
            "last": str(last),
            "expected_bars": expected,
            "actual_bars": actual,
        },
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


# ---------- partition-key vs row agreement ----------


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
    bad_mask = df["symbol"].astype(str) != str(ctx.symbol)
    count = int(bad_mask.sum())
    if count == 0:
        return passing(name)
    sample_vals = df.loc[bad_mask, "symbol"].astype(str).head(5).tolist()
    return failing(
        name,
        count=count,
        message=(
            f"{count} rows have symbol != partition key {ctx.symbol!r} "
            f"(samples: {sample_vals})"
        ),
        details={
            "partition_symbol": ctx.symbol,
            "sample_row_symbols": sample_vals,
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
    bad_mask = ts.notna() & (row_dates != ctx.date)
    count = int(bad_mask.sum())
    if count == 0:
        return passing(name)
    sample_vals = row_dates[bad_mask].head(5).tolist()
    return failing(
        name,
        count=count,
        message=(
            f"{count} rows have ts_event.date != partition key "
            f"{ctx.date!r} (samples: {sample_vals})"
        ),
        details={"partition_date": ctx.date, "sample_row_dates": sample_vals},
    )


# ---------- registration ----------

_GATES: tuple[Gate, ...] = (
    Gate(
        name="ohlc_high_ge_open",
        description="high >= open on every bar",
        schema=SCHEMA,
        fn=gate_ohlc_high_ge_open,
    ),
    Gate(
        name="ohlc_high_ge_close",
        description="high >= close on every bar",
        schema=SCHEMA,
        fn=gate_ohlc_high_ge_close,
    ),
    Gate(
        name="ohlc_high_ge_low",
        description="high >= low on every bar",
        schema=SCHEMA,
        fn=gate_ohlc_high_ge_low,
    ),
    Gate(
        name="ohlc_low_le_open",
        description="low <= open on every bar",
        schema=SCHEMA,
        fn=gate_ohlc_low_le_open,
    ),
    Gate(
        name="ohlc_low_le_close",
        description="low <= close on every bar",
        schema=SCHEMA,
        fn=gate_ohlc_low_le_close,
    ),
    Gate(
        name="volume_non_negative",
        description="volume >= 0 on every bar",
        schema=SCHEMA,
        fn=gate_volume_non_negative,
    ),
    Gate(
        name="trade_count_non_negative",
        description="trade_count >= 0 on every bar",
        schema=SCHEMA,
        fn=gate_trade_count_non_negative,
    ),
    Gate(
        name="vwap_in_range",
        description="low <= vwap <= high on bars with volume > 0",
        schema=SCHEMA,
        fn=gate_vwap_in_range,
        default_severity_on_hit="warn",
    ),
    Gate(
        name="timestamp_unique",
        description="no duplicate (symbol, ts_event) rows",
        schema=SCHEMA,
        fn=gate_timestamp_unique,
    ),
    Gate(
        name="timestamp_aligned_1m",
        description="ts_event values are exact 1m boundaries",
        schema=SCHEMA,
        fn=gate_timestamp_aligned_1m,
    ),
    Gate(
        name="missing_minutes",
        description=(
            f"count gaps in 1m sequence (warn>{MISSING_MINUTES_WARN_THRESHOLD}, "
            f"fail>{MISSING_MINUTES_FAIL_THRESHOLD})"
        ),
        schema=SCHEMA,
        fn=gate_missing_minutes,
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
