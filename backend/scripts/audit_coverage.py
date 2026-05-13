"""Coverage audit — database health check.

For every (detector × event_type × symbol × year):
  - event count
  - outcomes-coverage count
  - "real" outcomes count (excludes the JSON-literal "null" bug case)
  - missing %
  - flags suspicious gaps (year-over-year drops, null outcomes, etc.)

Output: prints summary to stdout + writes docs/COVERAGE_AUDIT.md.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc
DB_PATH = Path(r"C:\Users\benbr\BacktestStation\data\meta.sqlite")
DOC_PATH = Path(r"C:\Users\benbr\BacktestStation\docs\COVERAGE_AUDIT.md")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--doc", type=Path, default=DOC_PATH)
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    cur = con.cursor()

    # ---- Overall summary ----
    print("=== overall ===")
    cur.execute("SELECT COUNT(*) FROM research_events")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM research_events WHERE outcomes IS NOT NULL")
    n_not_null = cur.fetchone()[0]
    # "outcomes IS NULL" vs the JSON-literal "null" string bug.
    cur.execute("SELECT COUNT(*) FROM research_events WHERE outcomes = 'null'")
    n_json_null = cur.fetchone()[0]
    n_real = n_not_null - n_json_null
    print(f"  total events: {total:>8,}")
    print(f"  outcomes IS NOT NULL: {n_not_null:>8,} ({100.0*n_not_null/total:.1f}%)")
    print(f"  JSON-null string bug: {n_json_null:>8,} (should be 0)")
    print(f"  real outcomes: {n_real:>8,} ({100.0*n_real/total:.1f}%)")
    print()

    # ---- Per-detector breakdown ----
    print("=== per detector × event_type ===")
    cur.execute("""
        SELECT feature_name, event_type,
               COUNT(*) AS n_total,
               SUM(CASE WHEN outcomes IS NOT NULL THEN 1 ELSE 0 END) AS n_with_outcomes_col,
               SUM(CASE WHEN outcomes = 'null' THEN 1 ELSE 0 END) AS n_json_null,
               SUM(CASE WHEN outcomes IS NOT NULL AND outcomes != 'null' THEN 1 ELSE 0 END) AS n_real
        FROM research_events
        GROUP BY feature_name, event_type
        ORDER BY feature_name, event_type
    """)
    per_mode = cur.fetchall()
    print(f"  {'feature_name':30s} {'event_type':28s} "
          f"{'n_total':>8s} {'n_real':>8s} {'json_null':>9s} {'pct_real':>9s}  {'status':<10s}")
    issues: list[str] = []
    for r in per_mode:
        feature, etype, n_total, _, n_json_null, n_real = r
        pct_real = 100.0 * n_real / n_total if n_total else 0
        if pct_real >= 99.5:
            status = "OK"
        elif n_json_null > 0:
            status = "JSON_NULL"
            issues.append(f"{feature}/{etype}: {n_json_null} JSON-null outcomes")
        elif pct_real < 95:
            status = "PARTIAL"
            issues.append(f"{feature}/{etype}: {pct_real:.1f}% real outcomes")
        else:
            status = "minor"
        print(f"  {feature:30s} {etype:28s} {n_total:>8,d} {n_real:>8,d} "
              f"{n_json_null:>9,d} {pct_real:>8.1f}%  {status:<10s}")

    # ---- Per-symbol coverage ----
    print()
    print("=== per symbol ===")
    cur.execute("""
        SELECT primary_symbol, COUNT(*) AS n_total,
               SUM(CASE WHEN outcomes IS NOT NULL AND outcomes != 'null' THEN 1 ELSE 0 END) AS n_real
        FROM research_events
        GROUP BY primary_symbol ORDER BY primary_symbol
    """)
    for r in cur.fetchall():
        sym, n_total, n_real = r
        pct = 100.0 * n_real / n_total if n_total else 0
        print(f"  {sym:15s} total={n_total:>7,d} real_outcomes={n_real:>7,d} ({pct:.1f}%)")

    # ---- Year-over-year sanity (drops = data holes) ----
    print()
    print("=== year-over-year event counts (detect data holes) ===")
    cur.execute("""
        SELECT feature_name,
               CAST(substr(bar_end_utc, 1, 4) AS INTEGER) AS year,
               COUNT(*) AS n
        FROM research_events
        WHERE bar_end_utc IS NOT NULL
        GROUP BY feature_name, year
        ORDER BY feature_name, year
    """)
    rows = cur.fetchall()
    by_feature: dict[str, list[tuple[int, int]]] = {}
    for r in rows:
        by_feature.setdefault(r[0], []).append((r[1], r[2]))
    # Expected partial years (data boundaries) — suppress these from
    # the issue list. Our warehouse covers 2015-01 → 2026-05 roughly.
    EXPECTED_PARTIAL_YEARS = {2014, 2026}
    for feature, ys in by_feature.items():
        counts_by_year = dict(ys)
        years = sorted(counts_by_year.keys())
        if len(years) < 2:
            continue
        # Exclude expected-partial years from median computation.
        median_pool = [c for y, c in ys if y not in EXPECTED_PARTIAL_YEARS]
        if not median_pool:
            continue
        sorted_counts = sorted(median_pool)
        median = sorted_counts[len(sorted_counts) // 2]
        anomalies = [
            (y, c) for y, c in ys
            if median > 100 and c < 0.5 * median
            and y not in EXPECTED_PARTIAL_YEARS
        ]
        print(f"  {feature}: years {years[0]}-{years[-1]}, median {median:,}/yr "
              f"(excluding {sorted(EXPECTED_PARTIAL_YEARS)})")
        for y, c in anomalies:
            issues.append(
                f"{feature}: year {y} only {c} events ({100*c/median:.0f}% of median)"
            )
            print(f"    !! {y}: {c:,} events ({100*c/median:.0f}% of median)")

    # ---- Outcome version distribution ----
    print()
    print("=== outcome version distribution ===")
    cur.execute("""
        SELECT feature_name,
               json_extract(outcomes, '$.outcome_version') AS v,
               COUNT(*) AS n
        FROM research_events
        WHERE outcomes IS NOT NULL AND outcomes != 'null'
        GROUP BY feature_name, v
        ORDER BY feature_name, v
    """)
    for r in cur.fetchall():
        feature, v, n = r
        print(f"  {feature:30s} version={str(v):8s} n={n:>7,}")

    # ---- Issues summary ----
    print()
    print("=" * 60)
    if not issues:
        print("CLEAN — no coverage issues detected.")
    else:
        print(f"FOUND {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")

    # ---- Write doc ----
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    with open(args.doc, "w", encoding="utf-8") as f:
        f.write("# Database coverage audit\n\n")
        f.write(f"_Generated `{datetime.now(UTC).isoformat()}`._\n\n")
        f.write(f"**Total events:** {total:,}\n\n")
        f.write(f"**With outcomes (any):** {n_not_null:,} "
                f"({100.0 * n_not_null / total:.1f}%)\n\n")
        f.write(f"**JSON-null bug rows:** {n_json_null:,}\n\n")
        f.write(f"**Real outcomes:** {n_real:,} "
                f"({100.0 * n_real / total:.1f}%)\n\n")
        f.write("## Per detector × event_type\n\n")
        f.write("| feature | event_type | n_total | n_real | json_null | pct_real | status |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in per_mode:
            feature, etype, n_total_r, _, n_json_null_r, n_real_r = r
            pct_real = 100.0 * n_real_r / n_total_r if n_total_r else 0
            status = (
                "OK" if pct_real >= 99.5
                else ("JSON_NULL" if n_json_null_r > 0
                else ("PARTIAL" if pct_real < 95 else "minor"))
            )
            f.write(
                f"| {feature} | {etype} | {n_total_r:,} | {n_real_r:,} | "
                f"{n_json_null_r:,} | {pct_real:.1f}% | {status} |\n"
            )
        if issues:
            f.write("\n## Issues\n\n")
            for issue in issues:
                f.write(f"- {issue}\n")
        else:
            f.write("\n## Status\n\nCLEAN — no coverage issues detected.\n")
    print(f"\nwrote {args.doc}")
    con.close()
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
