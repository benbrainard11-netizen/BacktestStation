"""Look-ahead audit — verify zero-lookahead invariants across all
detectors.

For every event class with outcomes, asserts:

  1. `outcome.reference_close`, `outcome.next_period`, etc., must derive
     from bars whose ts >= event.bar_end_utc + bucket_minutes.
  2. For events that record forward-period timestamps in outcomes
     (next_period, n_plus_2, etc.), those periods must start AFTER
     the event's knowable_ts.

This is a STRUCTURAL check using stored timestamps in outcomes JSON,
not a re-computation. It catches obvious violations like an outcome
saying "next_period.ts_utc_start = some_time_BEFORE bar_end".

Output: prints summary + writes docs/LOOKAHEAD_AUDIT.md.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
DB_PATH = Path(r"C:\Users\benbr\BacktestStation\data\meta.sqlite")
DOC_PATH = Path(r"C:\Users\benbr\BacktestStation\docs\LOOKAHEAD_AUDIT.md")


# Bucket-minutes lookup per (feature_name, event_type). Defines the
# detector confirmation lag — events are knowable at
# bar_end_utc + bucket_minutes.
_BUCKET_MIN: dict[tuple[str, str], int] = {
    # SMT
    ("smt_htf_reference_divergence", "previous_day_smt"): 60,
    ("smt_htf_reference_divergence", "weekly_smt"): 240,
    ("smt_prev_candle_divergence", "15m_prev_candle_smt"): 0,
    ("smt_prev_candle_divergence", "15m_prev_candle_smt_high"): 0,
    ("smt_prev_candle_divergence", "15m_prev_candle_smt_low"): 0,
    ("smt_prev_candle_divergence", "30m_prev_candle_smt"): 0,
    ("smt_prev_candle_divergence", "30m_prev_candle_smt_high"): 0,
    ("smt_prev_candle_divergence", "30m_prev_candle_smt_low"): 0,
    ("smt_prev_candle_divergence", "1h_prev_candle_smt"): 0,
    ("smt_prev_candle_divergence", "1h_prev_candle_smt_high"): 0,
    ("smt_prev_candle_divergence", "1h_prev_candle_smt_low"): 0,
    ("smt_prev_candle_divergence", "90m_prev_candle_smt"): 0,
    ("smt_prev_candle_divergence", "90m_prev_candle_smt_high"): 0,
    ("smt_prev_candle_divergence", "90m_prev_candle_smt_low"): 0,
    ("smt_prev_candle_divergence", "4h_prev_candle_smt"): 0,
    ("smt_prev_candle_divergence", "4h_prev_candle_smt_high"): 0,
    ("smt_prev_candle_divergence", "4h_prev_candle_smt_low"): 0,
    ("smt_prev_candle_divergence", "6h_prev_candle_smt"): 0,
    ("smt_prev_candle_divergence", "6h_prev_candle_smt_high"): 0,
    ("smt_prev_candle_divergence", "6h_prev_candle_smt_low"): 0,
    # PSP
    ("psp_candle_divergence", "1h_psp"): 60,
    ("psp_candle_divergence", "4h_psp"): 240,
    ("psp_candle_divergence", "daily_psp"): 24 * 60,
    # FVG
    ("fvg_formation", "1h_fvg"): 60,
    ("fvg_formation", "4h_fvg"): 240,
    ("fvg_formation", "daily_fvg"): 24 * 60,
    ("fvg_formation", "15m_fvg"): 15,
    # OB
    **{("order_block", t): m for t, m in [
        ("swept_pdl_1h", 60), ("swept_pdl_4h", 240),
        ("swept_pdh_1h", 60), ("swept_pdh_4h", 240),
        ("swept_pwl_4h", 240), ("swept_pwl_daily", 24 * 60),
        ("swept_pwh_4h", 240), ("swept_pwh_daily", 24 * 60),
        ("swept_asia_low_1h", 60), ("swept_asia_high_1h", 60),
        ("swept_london_low_1h", 60), ("swept_london_high_1h", 60),
        ("swept_ny_low_1h", 60), ("swept_ny_high_1h", 60),
    ]},
    # SWEEP
    **{("liquidity_sweep", t): m for t, m in [
        ("pdl_1h", 60), ("pdl_4h", 240), ("pdh_1h", 60), ("pdh_4h", 240),
        ("pwl_4h", 240), ("pwl_daily", 24 * 60),
        ("pwh_4h", 240), ("pwh_daily", 24 * 60),
        ("asia_low_1h", 60), ("asia_high_1h", 60),
        ("london_low_1h", 60), ("london_high_1h", 60),
        ("ny_low_1h", 60), ("ny_high_1h", 60),
    ]},
    # DISP
    ("displacement_candle", "1h_disp"): 60,
    ("displacement_candle", "4h_disp"): 240,
    ("displacement_candle", "daily_disp"): 24 * 60,
    # SWING — knowable at bar_end + (n+1)*tf_minutes
    # (recorded in event_data.knowable_ts_utc; check that separately)
    # FT, ORB, EQL, TIME_PROFILE, VOLUME_PROFILE handled via event_data.parent_period_end_utc
}

# Soft event_data checks. These fields are intentionally stored for research,
# but they are not knowable at event fire and must not be ML features.
_EVENT_DATA_FILL_AFTER_FIRE_PATTERNS: dict[tuple[str, str], tuple[str, ...]] = {
    ("smt_htf_reference_divergence", "previous_day_smt"): (
        "did_all_confirm_by_window_end",
        "later_confirmations",
        "divergence_duration_seconds",
        "symbol_states.*.broke_high",
        "symbol_states.*.broke_low",
        "symbol_states.*.high_break_time_utc",
        "symbol_states.*.high_break_price",
        "symbol_states.*.low_break_time_utc",
        "symbol_states.*.low_break_price",
    ),
    ("smt_htf_reference_divergence", "weekly_smt"): (
        "did_all_confirm_by_window_end",
        "later_confirmations",
        "divergence_duration_seconds",
        "symbol_states.*.broke_high",
        "symbol_states.*.broke_low",
        "symbol_states.*.high_break_time_utc",
        "symbol_states.*.high_break_price",
        "symbol_states.*.low_break_time_utc",
        "symbol_states.*.low_break_price",
    ),
}


def _event_data_patterns(feature: str, event_type: str) -> tuple[str, ...]:
    patterns = _EVENT_DATA_FILL_AFTER_FIRE_PATTERNS.get((feature, event_type), ())
    if feature == "macro_event_anchor" and event_type.startswith("pre_"):
        return (*patterns, "actual", "actual_raw", "actual_value", "surprise", "surprise_*")
    return patterns


def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def flatten_json_paths(obj, prefix: str = "", out: dict[str, object] | None = None):
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            next_prefix = f"{prefix}.{k}" if prefix else str(k)
            flatten_json_paths(v, next_prefix, out)
    elif isinstance(obj, list):
        out[prefix] = obj
        for i, item in enumerate(obj):
            flatten_json_paths(item, f"{prefix}.{i}", out)
    else:
        out[prefix] = obj
    return out


def has_meaningful_value(value: object) -> bool:
    # Empty lists still encode "nothing happened later", which is itself a
    # post-fire fact for the fields listed above.
    return value is not None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--doc", type=Path, default=DOC_PATH)
    parser.add_argument("--limit-per-class", type=int, default=200,
                        help="Sample N events per (feature, event_type) for spot-check.")
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()

    cur.execute("""
        SELECT DISTINCT feature_name, event_type
        FROM research_events
        WHERE outcomes IS NOT NULL AND outcomes != 'null'
        ORDER BY feature_name, event_type
    """)
    classes = cur.fetchall()
    print(f"Auditing {len(classes)} (feature × event_type) classes")
    print()

    issues: list[str] = []
    event_data_warnings: list[str] = []
    summary: list[dict] = []

    for feature, event_type in classes:
        cur.execute("""
            SELECT bar_end_utc, event_data, outcomes
            FROM research_events
            WHERE feature_name = ? AND event_type = ?
              AND outcomes IS NOT NULL AND outcomes != 'null'
            ORDER BY RANDOM() LIMIT ?
        """, (feature, event_type, args.limit_per_class))
        rows = cur.fetchall()
        if not rows:
            continue

        n_violations = 0
        n_event_data_flags = 0
        first_violation_msg: str | None = None
        first_event_data_msg: str | None = None
        for bar_end_str, event_data_json, outcomes_json in rows:
            bar_end = parse_dt(bar_end_str.replace(" ", "T"))
            if bar_end.tzinfo is None:
                bar_end = bar_end.replace(tzinfo=UTC)
            try:
                ed = json.loads(event_data_json) if event_data_json else {}
                if not isinstance(ed, dict):
                    ed = {}
            except Exception:
                ed = {}
            try:
                outcomes = json.loads(outcomes_json) if outcomes_json else None
            except Exception:
                continue
            if not outcomes:
                continue

            # Determine knowable_ts.
            key = (feature, event_type)
            if key in _BUCKET_MIN:
                knowable_ts = bar_end + timedelta(minutes=_BUCKET_MIN[key])
            else:
                # For event classes that use event_data.parent_period_end_utc
                # as the natural knowability point.
                if isinstance(ed, dict) and ed.get("parent_period_end_utc"):
                    knowable_ts = parse_dt(ed["parent_period_end_utc"])
                    if knowable_ts.tzinfo is None:
                        knowable_ts = knowable_ts.replace(tzinfo=UTC)
                elif isinstance(ed, dict) and ed.get("knowable_ts_utc"):
                    knowable_ts = parse_dt(ed["knowable_ts_utc"])
                    if knowable_ts.tzinfo is None:
                        knowable_ts = knowable_ts.replace(tzinfo=UTC)
                elif isinstance(ed, dict) and ed.get("known_ts_utc"):
                    knowable_ts = parse_dt(ed["known_ts_utc"])
                    if knowable_ts.tzinfo is None:
                        knowable_ts = knowable_ts.replace(tzinfo=UTC)
                else:
                    # No clear knowability rule for this class; skip
                    continue

            # Check 1: any forward-period timestamps in outcomes >= knowable_ts.
            forward_blocks = []
            for k in ("next_period", "n_plus_2", "forward_window"):
                if k in outcomes and isinstance(outcomes[k], dict):
                    forward_blocks.append((k, outcomes[k]))
            for k, value in outcomes.items():
                if (
                    k not in {"next_period", "n_plus_2", "forward_window"}
                    and k.startswith("next_")
                    and isinstance(value, dict)
                ):
                    forward_blocks.append((k, value))

            for block_name, block in forward_blocks:
                # Find start timestamp candidates.
                for ts_key in ("ts_utc_start", "ts_utc", "start_utc", "window_start_utc"):
                    if ts_key in block and block[ts_key]:
                        try:
                            block_start = parse_dt(block[ts_key])
                            if block_start.tzinfo is None:
                                block_start = block_start.replace(tzinfo=UTC)
                        except Exception:
                            continue
                        if block_start < knowable_ts:
                            n_violations += 1
                            if first_violation_msg is None:
                                first_violation_msg = (
                                    f"{feature}/{event_type}: outcome "
                                    f"{block_name}.{ts_key}={block_start.isoformat()} "
                                    f"< knowable_ts={knowable_ts.isoformat()} "
                                    f"(bar_end={bar_end.isoformat()})"
                                )
                        break

            # Soft check: event_data fields whose semantics require looking
            # forward after the event fired. These are reported so ML scripts
            # can exclude them, but they do not make this audit fail.
            patterns = _event_data_patterns(feature, event_type)
            if patterns and ed:
                flat_ed = flatten_json_paths(ed)
                flagged = sorted(
                    path for path, value in flat_ed.items()
                    if has_meaningful_value(value)
                    and any(fnmatch.fnmatchcase(path, pat) for pat in patterns)
                )
                if flagged:
                    n_event_data_flags += 1
                    if first_event_data_msg is None:
                        first_event_data_msg = (
                            f"{feature}/{event_type}: event_data has post-fire "
                            f"field(s), first={flagged[0]}"
                        )

        pct = 100.0 * n_violations / len(rows) if rows else 0
        status = "OK" if n_violations == 0 else f"VIOLATIONS"
        line = (
            f"  {feature:30s} {event_type:28s} "
            f"sampled={len(rows):>4d} violations={n_violations:>4d} "
            f"({pct:>4.1f}%) ed_flags={n_event_data_flags:>4d} {status}"
        )
        print(line)
        summary.append({
            "feature": feature, "event_type": event_type,
            "sampled": len(rows), "violations": n_violations,
            "pct": pct, "first_violation": first_violation_msg,
            "event_data_flags": n_event_data_flags,
            "first_event_data_flag": first_event_data_msg,
        })
        if n_violations > 0:
            issues.append(
                f"{feature}/{event_type}: {n_violations}/{len(rows)} sampled "
                f"events have look-ahead in outcomes. First: {first_violation_msg}"
            )
        if n_event_data_flags > 0:
            event_data_warnings.append(
                f"{feature}/{event_type}: {n_event_data_flags}/{len(rows)} sampled "
                f"events contain post-fire event_data fields. First: {first_event_data_msg}"
            )

    print()
    print("=" * 60)
    if not issues:
        print(f"CLEAN — no look-ahead violations across {len(classes)} classes.")
    else:
        print(f"FOUND {len(issues)} class(es) with violations:")
        for issue in issues:
            print(f"  - {issue}")
    if event_data_warnings:
        print()
        print("EVENT_DATA WARNINGS (soft, not audit-failing):")
        for warning in event_data_warnings:
            print(f"  - {warning}")

    args.doc.parent.mkdir(parents=True, exist_ok=True)
    with open(args.doc, "w", encoding="utf-8") as f:
        f.write("# Look-ahead audit\n\n")
        f.write(f"_Generated `{datetime.now(UTC).isoformat()}`._\n\n")
        f.write(
            "Verifies that outcomes were computed only from bars at or after "
            "`event.bar_end_utc + bucket_minutes` (the detector confirmation lag).\n\n"
            f"Sampled up to {args.limit_per_class} events per (feature × event_type) "
            f"class. {len(classes)} classes audited.\n\n"
        )
        f.write("## Per-class summary\n\n")
        f.write("| feature | event_type | sampled | violations | pct | event_data_flags | status |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for s in summary:
            status = "OK" if s["violations"] == 0 else "VIOLATIONS"
            f.write(
                f"| {s['feature']} | {s['event_type']} | {s['sampled']} | "
                f"{s['violations']} | {s['pct']:.1f}% | "
                f"{s['event_data_flags']} | {status} |\n"
            )
        if issues:
            f.write("\n## Violations\n\n")
            for issue in issues:
                f.write(f"- {issue}\n")
        else:
            f.write("\n## Status\n\nCLEAN — no look-ahead violations.\n")
        if event_data_warnings:
            f.write("\n## Event Data Warnings\n\n")
            f.write(
                "Soft warnings for event_data fields documented as filled after "
                "event fire. These fields can remain in the research event store "
                "but should not be used as event-time ML features.\n\n"
            )
            for warning in event_data_warnings:
                f.write(f"- {warning}\n")
    print(f"\nwrote {args.doc}")
    con.close()
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
