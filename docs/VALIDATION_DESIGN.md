# Validation Design — semantic gates for warehouse data

_Spec for `backend/app/research/validation/`. Implementation owner: benpc. Spec owner: benpc._

## Goal

Move from "no semantic data validation" to "every snapshot has a partition_validation_report with explicit gate results." Make data integrity a first-class enforceable artifact, not a CLAUDE.md aspiration.

## Architecture

```
backend/app/research/validation/
    __init__.py
    schema_gates.py        # generic gate runner + Gate dataclass
    gates_ohlcv.py         # OHLC 1m bar gates
    gates_tbbo.py          # TBBO trade-print gates
    gates_mbp1.py          # MBP-1 quote/depth gates
    gates_research_events.py  # research event gates
    runner.py              # snapshot-walker; runs all gates, writes report

backend/scripts/data/
    validate_snapshot.py   # CLI-callable; takes snapshot_id, runs runner.py
```

A `Gate` is:

```python
@dataclass
class Gate:
    name: str
    description: str
    severity: Literal["pass", "warn", "fail"]   # default level on hit
    schema: str                                 # which schema this applies to
    
    def evaluate(self, partition_df: pd.DataFrame) -> GateResult:
        ...
```

A `GateResult` is:

```python
@dataclass
class GateResult:
    gate_name: str
    severity: str   # "pass" / "warn" / "fail"
    count: int      # rows that failed the gate
    details: dict   # gate-specific extras
```

Each `evaluate()` returns one `GateResult`. Pass = 0 failures. Warn = > 0 failures but below threshold. Fail = above threshold.

## Gate catalog by schema

### `ohlcv-1m` gates

| Gate name | Check | Severity on hit |
|---|---|---|
| `ohlc_high_ge_open` | `high >= open` | fail |
| `ohlc_high_ge_close` | `high >= close` | fail |
| `ohlc_high_ge_low` | `high >= low` | fail |
| `ohlc_low_le_open` | `low <= open` | fail |
| `ohlc_low_le_close` | `low <= close` | fail |
| `volume_non_negative` | `volume >= 0` | fail |
| `trade_count_non_negative` | `trade_count >= 0` | fail |
| `vwap_in_range` | `low <= vwap <= high` (if volume > 0) | warn |
| `timestamp_unique` | no duplicate `ts_event` per (symbol, date) | fail |
| `timestamp_aligned_1m` | `ts_event` is 1m-aligned (no microsecond drift) | fail |
| `missing_minutes` | count gaps within trading hours | warn (threshold 50/day) |
| `required_columns_not_null` | required cols (`ts_event`, `symbol`, `open`, etc.) have no nulls | fail |
| `partition_symbol_matches_rows` | `symbol` partition key = all row symbols | fail |
| `partition_date_matches_rows` | `date` partition key = all `ts_event.date()` | fail |

### `tbbo` gates

| Gate name | Check | Severity on hit |
|---|---|---|
| `bid_le_ask` | `bid_px <= ask_px` (when both present) | fail |
| `price_positive` | `price > 0` | fail |
| `size_non_negative` | `size >= 0` | fail |
| `bid_sz_non_negative` | `bid_sz >= 0` | fail |
| `ask_sz_non_negative` | `ask_sz >= 0` | fail |
| `valid_action` | action ∈ {'T', 'A', 'B', 'C', 'M', 'R'} | fail |
| `valid_side` | side ∈ {'A', 'B', 'N'} | fail |
| `sequence_monotonic` | sequence numbers monotonic per symbol/day | warn (some publishers reorder) |
| `timestamp_monotonic_or_equal` | ts_event is non-decreasing per symbol | warn |
| `required_columns_not_null` | required cols not null | fail |
| `partition_symbol_matches_rows` | partition key matches data | fail |
| `partition_date_matches_rows` | partition key matches data | fail |

### `mbp-1` gates

Same as TBBO plus:

| Gate name | Check | Severity on hit |
|---|---|---|
| `depth_zero` | `depth == 0` (MBP-1 always level 0) | fail |
| `flags_in_range` | flags is uint8-compatible | warn |
| `instrument_id_consistent` | one `instrument_id` per (symbol, date) | warn (might flag rollover days) |

### `research_events` gates

| Gate name | Check | Severity on hit |
|---|---|---|
| `feature_name_known` | feature ∈ catalog of known detectors | fail |
| `bar_end_utc_not_null` | `anchor.bar_end_utc` not null | fail |
| `primary_symbol_not_null` | `anchor.primary_symbol` not null | fail |
| `event_data_valid_json` | `event_data` parses as JSON if string | fail |
| `outcomes_valid_json_if_present` | same for `outcomes` | warn |
| `partition_feature_matches` | `feature_name=X/` partition matches row feature | fail |
| `partition_year_matches` | `event_year=Y/` partition matches `bar_end_utc.year` | fail |

## Output report shape

Per snapshot, runner writes:

```json
{
  "report_id": 42,
  "snapshot_id": "sha256-abc...",
  "generated_at": "2026-05-17T22:00:00Z",
  "generator_version": "v1",
  "total_partitions": 4218,
  "partitions_pass": 4180,
  "partitions_warn": 35,
  "partitions_fail": 3,
  "summary": {
    "by_schema": {
      "ohlcv-1m": {"total": 3500, "pass": 3475, "warn": 23, "fail": 2},
      "tbbo": {"total": 700, "pass": 691, "warn": 8, "fail": 1},
      ...
    },
    "by_severity": {"pass": 4180, "warn": 35, "fail": 3},
    "top_failing_gates": [
      {"gate": "missing_minutes", "n_partitions": 18},
      {"gate": "sequence_monotonic", "n_partitions": 7}
    ]
  }
}
```

And per finding (one row per partition × gate that's not "pass"):

```
partition_r2_key: "processed/bars/timeframe=1m/symbol=NQ.c.0/date=2020-03-12/part-000.parquet"
schema: "ohlcv-1m"
symbol: "NQ.c.0"
date: "2020-03-12"
gate_name: "missing_minutes"
severity: "warn"
message: "73 missing minutes during US RTH"
details_json: {"missing_count": 73, "trading_hours": "US_RTH", ...}
```

## Threshold philosophy

- **Schema-level invariants → fail.** E.g., `high < low` is broken data; fail hard.
- **Reasonable-anomalies → warn.** E.g., missing minutes (markets close), sequence gaps (publishers reorder).
- **Strict definitions → operator-configurable.** Allow `--strict` flag that promotes warns to fails.

Default thresholds (overridable):

| Gate | Default warn threshold | Default fail threshold |
|---|---|---|
| missing_minutes | > 50/day | > 200/day |
| sequence_monotonic | any inversions | > 100 inversions |
| timestamp_unique | any dups | any dups (this is always fail) |

## CLI integration

```bash
bs data validate <snapshot_id>            # default: all schemas, default thresholds
bs data validate <snapshot_id> --strict   # warns become fails
bs data validate <snapshot_id> --schemas ohlcv-1m,tbbo   # subset
bs data validate <snapshot_id> --quick    # skip expensive gates (full file hash recomputation, etc.)
bs data validate <snapshot_id> --json     # machine output
```

Output:
- Text: summary table + count of failing partitions per gate
- JSON: full report payload
- Always: row inserted into `partition_validation_reports` + N rows in `partition_validation_findings`

## Implementation order

1. **`schema_gates.py`** — Gate + GateResult dataclasses, runner skeleton
2. **`gates_ohlcv.py`** — 14 gates, with unit tests on synthetic dataframes
3. **`runner.py`** — walks a snapshot's ohlcv-1m partitions, runs gates, writes report
4. **`gates_tbbo.py`** — 12 gates
5. **`gates_mbp1.py`** — 15 gates (TBBO + 3)
6. **`gates_research_events.py`** — 7 gates
7. **`scripts/data/validate_snapshot.py`** — CLI-callable; calls runner
8. **CLI wire-up** (Phase 3 — 247 wraps in `bs data validate`)

Total: ~1 day for benpc to write logic + unit tests. 247's parallel schema work (0.5 day) provides the report tables this writes to.

## Tests

Per-gate unit tests on synthetic dataframes. E.g.:

```python
def test_ohlc_high_ge_low_passes():
    df = pd.DataFrame({"open": [100], "high": [105], "low": [95], "close": [102], "volume": [1000]})
    result = gates_ohlcv.OhlcHighGeLowGate().evaluate(df)
    assert result.severity == "pass"

def test_ohlc_high_ge_low_fails():
    df = pd.DataFrame({"open": [100], "high": [90], "low": [95], "close": [92], "volume": [1000]})
    result = gates_ohlcv.OhlcHighGeLowGate().evaluate(df)
    assert result.severity == "fail"
    assert result.count == 1
```

Goal: 95%+ branch coverage on gate code.

## Out of scope

- Cross-partition validation (e.g., "do consecutive days' close-to-open transitions make sense") — separate "lineage" tool
- Statistical anomaly detection (z-score outliers, distribution shifts) — separate "data drift" tool
- Re-running validation continuously / live — pull-based for now
- Auto-fixing data issues — humans decide whether to repull, exclude, or accept

## Risk

Main risk: validation false positives blocking research. Mitigation:
- Severity defaults are conservative (warn on borderline cases, fail only on schema violations)
- `--strict` flag is opt-in
- Validation report is informational; doesn't auto-fail backtests (operator decides)
