"""Quick analysis of SMT research events + outcomes.

Read-only SQL over `data/meta.sqlite`. Surfaces the subsets that
look most informative, organized to answer the kinds of questions
that come up after the first scan: "what conditions make the N+1
confirmation rate jump?"

Run:
    python -m scripts.smt_subset_analysis

Optional: --feature-name to filter (default
smt_htf_reference_divergence).

This is a research tool, not a production dashboard — it prints
tables to stdout so you can read them, not generate plots or
serialize for ML training.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\benbr\BacktestStation\data\meta.sqlite")


def _row(cur, *args) -> list[dict]:
    cur.execute(*args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def _print_table(title: str, rows: list[dict]) -> None:
    print(f"\n=== {title} ===")
    if not rows:
        print("  (no rows)")
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(c), max(len(str(r[c])) for r in rows)) for c in cols}
    header = "  " + "  ".join(c.ljust(widths[c]) for c in cols)
    print(header)
    print("  " + "  ".join("-" * widths[c] for c in cols))
    for r in rows:
        print("  " + "  ".join(str(r[c]).ljust(widths[c]) for c in cols))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--feature-name", default="smt_htf_reference_divergence")
    p.add_argument("--db", type=Path, default=DB_PATH)
    args = p.parse_args()

    if not args.db.exists():
        print(f"db not found: {args.db}")
        return 1

    con = sqlite3.connect(args.db)
    cur = con.cursor()

    feat = args.feature_name

    # ------- 1. Overall confirmation rates -------
    rows = _row(cur, """
        SELECT event_type, side, COUNT(*) AS n,
               SUM(CASE WHEN json_extract(outcomes, '$.next_period.thesis_confirmed_strict') = 1 THEN 1 ELSE 0 END) AS conf_n1,
               ROUND(100.0 * SUM(CASE WHEN json_extract(outcomes, '$.next_period.thesis_confirmed_strict') = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_n1
        FROM research_events
        WHERE feature_name = ?
        GROUP BY event_type, side ORDER BY event_type, side
    """, (feat,))
    _print_table("Confirmation rate at N+1 by event_type x side", rows)

    # ------- 2. The headline filter: smt_active_for_side_at_close -------
    rows = _row(cur, """
        SELECT event_type,
               CASE json_extract(outcomes, '$.period_close.smt_active_for_side_at_close')
                    WHEN 1 THEN 'active' ELSE 'resolved' END AS active_at_close,
               COUNT(*) AS n,
               SUM(CASE WHEN json_extract(outcomes, '$.next_period.thesis_confirmed_strict') = 1 THEN 1 ELSE 0 END) AS conf_n1,
               ROUND(100.0 * SUM(CASE WHEN json_extract(outcomes, '$.next_period.thesis_confirmed_strict') = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct
        FROM research_events
        WHERE feature_name = ?
        GROUP BY event_type, active_at_close ORDER BY event_type, active_at_close
    """, (feat,))
    _print_table(
        "smt_active_at_close x N+1 confirmation (the headline filter)", rows,
    )

    # ------- 3. Active at close, sliced by side -------
    rows = _row(cur, """
        SELECT event_type, side,
               CASE json_extract(outcomes, '$.period_close.smt_active_for_side_at_close')
                    WHEN 1 THEN 'active' ELSE 'resolved' END AS active_at_close,
               COUNT(*) AS n,
               SUM(CASE WHEN json_extract(outcomes, '$.next_period.thesis_confirmed_strict') = 1 THEN 1 ELSE 0 END) AS conf_n1,
               ROUND(100.0 * SUM(CASE WHEN json_extract(outcomes, '$.next_period.thesis_confirmed_strict') = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct
        FROM research_events
        WHERE feature_name = ?
        GROUP BY event_type, side, active_at_close
        ORDER BY event_type, side, active_at_close
    """, (feat,))
    _print_table("Active at close x side x type", rows)

    # ------- 4. By number of unswept laggers -------
    rows = _row(cur, """
        SELECT event_type,
               json_extract(outcomes, '$.period_close.n_lagging_unswept_at_close') AS n_unswept,
               COUNT(*) AS n,
               ROUND(100.0 * SUM(CASE WHEN json_extract(outcomes, '$.next_period.thesis_confirmed_strict') = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_n1
        FROM research_events
        WHERE feature_name = ?
        GROUP BY event_type, n_unswept ORDER BY event_type, n_unswept
    """, (feat,))
    _print_table("Number of laggers still unswept at close", rows)

    # ------- 5. By primary symbol -------
    rows = _row(cur, """
        SELECT event_type, primary_symbol, COUNT(*) AS n,
               ROUND(100.0 * SUM(CASE WHEN json_extract(outcomes, '$.next_period.thesis_confirmed_strict') = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_n1,
               ROUND(AVG(json_extract(outcomes, '$.next_period.primary_return_pct')), 3) AS avg_return_pct
        FROM research_events
        WHERE feature_name = ?
        GROUP BY event_type, primary_symbol ORDER BY event_type, primary_symbol
    """, (feat,))
    _print_table("Primary symbol — confirm rate + avg N+1 return %", rows)

    # ------- 6. By hour of day ET (event time) -------
    rows = _row(cur, """
        SELECT event_type,
               json_extract(context, '$.hour_of_day_et') AS hour_et,
               COUNT(*) AS n,
               ROUND(100.0 * SUM(CASE WHEN json_extract(outcomes, '$.next_period.thesis_confirmed_strict') = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_n1
        FROM research_events
        WHERE feature_name = ?
        GROUP BY event_type, hour_et
        HAVING n >= 30
        ORDER BY event_type, hour_et
    """, (feat,))
    _print_table(
        "Hour of day ET (n>=30 only) — does timing matter?", rows,
    )

    # ------- 7. Best subset: weekly + active + low side (preview) -------
    rows = _row(cur, """
        SELECT event_type, side,
               CASE json_extract(outcomes, '$.period_close.smt_active_for_side_at_close')
                    WHEN 1 THEN 'active' ELSE 'resolved' END AS active_at_close,
               COUNT(*) AS n,
               ROUND(100.0 * SUM(CASE WHEN json_extract(outcomes, '$.next_period.thesis_confirmed_strict') = 1
                                       OR json_extract(outcomes, '$.n_plus_2.thesis_confirmed_strict') = 1
                                  THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_n1_or_n2,
               ROUND(AVG(json_extract(outcomes, '$.next_period.mfe_pts_in_thesis')), 1) AS avg_mfe_n1
        FROM research_events
        WHERE feature_name = ?
        GROUP BY event_type, side, active_at_close
        ORDER BY pct_n1_or_n2 DESC
    """, (feat,))
    _print_table(
        "Best subsets (sorted by N+1-or-N+2 confirmation rate)", rows,
    )

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
