"""SMT × PSP composite analysis.

Tests three concrete questions about whether PSPs add information to
SMT events:

  3a. Do lookforward PSPs MARK the period's actual high/low?
      For each SMT, search PSPs in (SMT_break_ts, period_close]. For
      each PSP, compare its candle high (high-side SMT) or low
      (low-side SMT) on the SMT primary symbol to the period's
      actual extreme (from SMT outcomes).

  3b. Does presence of an aligned PSP after the SMT lift the N+1
      confirmation rate?
      For each (SMT side, PSP timeframe, lookforward window in
      {1h, 4h, 12h, 24h, 48h}) bucket, compare confirmation rate
      with vs without an aligned PSP.

  3c. Stacked filter: low-side + active-at-close + best lookforward
      PSP filter from 3b. Compare to the SMT-alone baseline.

Output: prints tables to stdout AND writes a markdown summary to
docs/COMPOSITE_FINDINGS.md.

Read-only on data/meta.sqlite.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

UTC = timezone.utc

DB_PATH = Path(r"C:\Users\benbr\BacktestStation\data\meta.sqlite")
DOC_PATH = Path(r"C:\Users\benbr\BacktestStation\docs\COMPOSITE_FINDINGS.md")

LOOKFORWARD_WINDOWS_HOURS = [1, 4, 12, 24, 48]
PSP_EVENT_TYPES = ["1h_psp", "4h_psp", "daily_psp"]
SMT_EVENT_TYPES = ["previous_day_smt", "weekly_smt"]
EXTREME_TOLERANCE_PTS = 1.0  # within 1 pt = "marked"


def _row(cur, *args) -> list[dict]:
    cur.execute(*args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def _print_table(title: str, headers: list[str], rows: list[list[str]]) -> None:
    print(f"\n=== {title} ===")
    if not rows:
        print("  (no rows)")
        return
    widths = [
        max(len(h), max(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)
    ]
    print("  " + "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    print("  " + "  ".join("-" * w for w in widths))
    for r in rows:
        print("  " + "  ".join(str(r[i]).ljust(widths[i]) for i in range(len(headers))))


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_(no rows)_"
    out: list[str] = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


# ---------- 3a. PSPs that mark the period extreme ----------


def analyze_marks_extreme(con: sqlite3.Connection) -> dict[str, Any]:
    """For each SMT event with computed outcomes, look at lookforward
    PSPs (any timeframe) and ask: does the PSP candle's high (or low,
    by side) on the SMT primary symbol approximate the period's
    actual extreme high (or low)?

    Returns a dict:
      summary_per_smt_type: per (smt_event_type, smt_side):
        n_smt_with_outcomes,
        n_marked_by_any_lookforward_psp,
        n_marked_breakdown_by_psp_type,
        confirm_rate_when_marked,
        confirm_rate_when_unmarked
    """
    cur = con.cursor()
    out: dict[str, Any] = {"by_type_side": []}

    for smt_type in SMT_EVENT_TYPES:
        for smt_side in ("high", "low"):
            extreme_field = (
                "primary_period_high" if smt_side == "high" else "primary_period_low"
            )
            psp_extreme_path = (
                "$.per_symbol_states.{primary}.high"
                if smt_side == "high"
                else "$.per_symbol_states.{primary}.low"
            )

            sql = f"""
WITH smt AS (
    SELECT id, primary_symbol, bar_end_utc,
           json_extract(outcomes, '$.period_close.{extreme_field}') AS period_extreme,
           json_extract(outcomes, '$.period_close.ts_utc') AS period_close_ts,
           json_extract(outcomes, '$.next_period.thesis_confirmed_strict') AS conf_n1
    FROM research_events
    WHERE feature_name='smt_htf_reference_divergence'
      AND event_type=?
      AND side=?
      AND outcomes IS NOT NULL
),
psps AS (
    SELECT bar_end_utc, primary_symbol, event_type, event_data
    FROM research_events
    WHERE feature_name='psp_candle_divergence'
)
SELECT smt.id AS smt_id,
       smt.conf_n1,
       smt.period_extreme,
       (
         SELECT MAX(
             CASE WHEN ABS(
                 CAST(json_extract(psps.event_data,
                     CASE WHEN ?='high'
                          THEN '$.per_symbol_states.' || smt.primary_symbol || '.high'
                          ELSE '$.per_symbol_states.' || smt.primary_symbol || '.low'
                     END
                 ) AS REAL) - smt.period_extreme
             ) <= ? THEN 1 ELSE 0 END
         )
         FROM psps
         WHERE psps.bar_end_utc > smt.bar_end_utc
           AND psps.bar_end_utc <= smt.period_close_ts
       ) AS marked
FROM smt
"""
            cur.execute(sql, (smt_type, smt_side, smt_side, EXTREME_TOLERANCE_PTS))
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]

            n_total = len(rows)
            n_marked = sum(1 for r in rows if r["marked"])
            conf_marked = [
                r for r in rows if r["marked"] and r["conf_n1"] is not None
            ]
            conf_unmarked = [
                r for r in rows if not r["marked"] and r["conf_n1"] is not None
            ]
            rate_marked = (
                sum(r["conf_n1"] for r in conf_marked) / len(conf_marked) * 100.0
                if conf_marked else None
            )
            rate_unmarked = (
                sum(r["conf_n1"] for r in conf_unmarked) / len(conf_unmarked) * 100.0
                if conf_unmarked else None
            )
            out["by_type_side"].append({
                "smt_type": smt_type,
                "smt_side": smt_side,
                "n_total": n_total,
                "n_marked": n_marked,
                "pct_marked": (
                    round(100.0 * n_marked / n_total, 1) if n_total else None
                ),
                "n_conf_marked": len(conf_marked),
                "rate_n1_when_marked": (
                    round(rate_marked, 1) if rate_marked is not None else None
                ),
                "n_conf_unmarked": len(conf_unmarked),
                "rate_n1_when_unmarked": (
                    round(rate_unmarked, 1) if rate_unmarked is not None else None
                ),
            })

    return out


# ---------- 3b. Lookforward window confirmation lift ----------


def analyze_lookforward_lift(con: sqlite3.Connection) -> list[dict[str, Any]]:
    """Sweep (smt_type, smt_side, psp_type, window_hours) — for each
    bucket, compute confirmation rate with vs without aligned PSP."""
    cur = con.cursor()
    results: list[dict[str, Any]] = []

    for smt_type in SMT_EVENT_TYPES:
        for smt_side in ("high", "low"):
            target_psp_side = "bearish" if smt_side == "high" else "bullish"
            for psp_type in PSP_EVENT_TYPES:
                for window_h in LOOKFORWARD_WINDOWS_HOURS:
                    sql = """
WITH smt AS (
    SELECT id, bar_end_utc,
           json_extract(outcomes, '$.next_period.thesis_confirmed_strict') AS conf_n1
    FROM research_events
    WHERE feature_name='smt_htf_reference_divergence'
      AND event_type=?
      AND side=?
      AND outcomes IS NOT NULL
)
SELECT smt.id, smt.conf_n1,
       EXISTS (
         SELECT 1 FROM research_events psp
         WHERE psp.feature_name='psp_candle_divergence'
           AND psp.event_type=?
           AND psp.side=?
           AND psp.bar_end_utc > smt.bar_end_utc
           AND (julianday(psp.bar_end_utc) - julianday(smt.bar_end_utc)) * 24 <= ?
       ) AS has_aligned_psp
FROM smt
"""
                    cur.execute(
                        sql, (smt_type, smt_side, psp_type, target_psp_side, window_h),
                    )
                    rows = cur.fetchall()
                    has = [r for r in rows if r[2] and r[1] is not None]
                    no = [r for r in rows if not r[2] and r[1] is not None]
                    rate_with = (
                        sum(r[1] for r in has) / len(has) * 100.0 if has else None
                    )
                    rate_without = (
                        sum(r[1] for r in no) / len(no) * 100.0 if no else None
                    )
                    lift = (
                        round(rate_with - rate_without, 1)
                        if rate_with is not None and rate_without is not None
                        else None
                    )
                    results.append({
                        "smt_type": smt_type,
                        "smt_side": smt_side,
                        "psp_type": psp_type,
                        "window_h": window_h,
                        "n_with_psp": len(has),
                        "rate_with": (
                            round(rate_with, 1) if rate_with is not None else None
                        ),
                        "n_without_psp": len(no),
                        "rate_without": (
                            round(rate_without, 1) if rate_without is not None else None
                        ),
                        "lift_pts": lift,
                    })

    return results


# ---------- 3c. Stacked filter: low + active + best lookforward ----------


def analyze_stacked_best(
    con: sqlite3.Connection,
    *,
    psp_type: str,
    window_h: int,
) -> list[dict[str, Any]]:
    """For low-side previous_day_smt + active-at-close + thesis-aligned
    PSP within the supplied window, compare to baseline."""
    cur = con.cursor()
    sql = """
WITH smt AS (
    SELECT id, bar_end_utc,
           json_extract(outcomes, '$.period_close.smt_active_for_side_at_close') AS active_at_close,
           json_extract(outcomes, '$.next_period.thesis_confirmed_strict') AS conf_n1,
           json_extract(outcomes, '$.n_plus_2.thesis_confirmed_strict') AS conf_n2
    FROM research_events
    WHERE feature_name='smt_htf_reference_divergence'
      AND event_type='previous_day_smt'
      AND side='low'
      AND outcomes IS NOT NULL
),
joined AS (
    SELECT smt.id, smt.active_at_close, smt.conf_n1, smt.conf_n2,
           EXISTS (
             SELECT 1 FROM research_events psp
             WHERE psp.feature_name='psp_candle_divergence'
               AND psp.event_type=?
               AND psp.side='bullish'
               AND psp.bar_end_utc > smt.bar_end_utc
               AND (julianday(psp.bar_end_utc) - julianday(smt.bar_end_utc)) * 24 <= ?
           ) AS has_aligned_psp
    FROM smt
)
SELECT
    CASE WHEN active_at_close=1 THEN 'active' ELSE 'resolved' END AS active_label,
    CASE WHEN has_aligned_psp=1 THEN 'has_psp' ELSE 'no_psp' END AS psp_label,
    COUNT(*) AS n,
    ROUND(100.0 * SUM(CASE WHEN conf_n1=1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_n1,
    ROUND(100.0 * SUM(CASE WHEN conf_n1=1 OR conf_n2=1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_n1_or_n2
FROM joined
GROUP BY active_label, psp_label
ORDER BY active_label DESC, psp_label DESC
"""
    cur.execute(sql, (psp_type, window_h))
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


# ---------- main ----------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--doc", type=Path, default=DOC_PATH)
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    sections: list[tuple[str, str]] = []  # (heading, body_md)

    # ---- 3a ----
    print("\n>>> 3a — PSP marks the period extreme")
    a = analyze_marks_extreme(con)
    rows_3a: list[list[str]] = []
    for r in a["by_type_side"]:
        rows_3a.append([
            r["smt_type"], r["smt_side"], str(r["n_total"]), str(r["n_marked"]),
            f"{r['pct_marked']}%" if r['pct_marked'] is not None else "—",
            (
                f"{r['rate_n1_when_marked']}% (n={r['n_conf_marked']})"
                if r['rate_n1_when_marked'] is not None else "—"
            ),
            (
                f"{r['rate_n1_when_unmarked']}% (n={r['n_conf_unmarked']})"
                if r['rate_n1_when_unmarked'] is not None else "—"
            ),
        ])
    headers_3a = ["smt_type", "side", "n_smt", "n_marked", "% marked",
                  "N+1 conf | marked", "N+1 conf | unmarked"]
    _print_table("PSP marks the period extreme — by SMT type x side", headers_3a, rows_3a)
    sections.append((
        "## 3a — PSP marks the period extreme",
        (
            "For each SMT, scan PSPs fired in `(SMT_break_ts, period_close]`. "
            f"A PSP \"marks\" the extreme if its candle high (high-side SMT) or "
            f"low (low-side SMT) on the SMT primary symbol is within {EXTREME_TOLERANCE_PTS}pt "
            "of the period's actual extreme.\n\n"
            + _md_table(headers_3a, rows_3a)
        ),
    ))

    # ---- 3b ----
    print("\n>>> 3b — Lookforward window aligned-PSP confirmation lift")
    b_rows = analyze_lookforward_lift(con)
    # Sort by absolute |lift| descending to surface the biggest gaps first
    b_rows.sort(key=lambda r: abs(r["lift_pts"] or 0), reverse=True)
    headers_3b = [
        "smt_type", "side", "psp_type", "win_h",
        "n+rate (with psp)", "n+rate (no psp)", "lift_pts",
    ]
    rows_3b_print: list[list[str]] = []
    for r in b_rows[:30]:  # top 30
        rows_3b_print.append([
            r["smt_type"], r["smt_side"], r["psp_type"], str(r["window_h"]),
            (
                f"{r['n_with_psp']}/{r['rate_with']}%"
                if r['rate_with'] is not None else f"{r['n_with_psp']}/—"
            ),
            (
                f"{r['n_without_psp']}/{r['rate_without']}%"
                if r['rate_without'] is not None else f"{r['n_without_psp']}/—"
            ),
            f"{r['lift_pts']:+}" if r["lift_pts"] is not None else "—",
        ])
    _print_table(
        "Lookforward window x PSP timeframe (top 30 by |lift|)",
        headers_3b, rows_3b_print,
    )
    sections.append((
        "## 3b — Lookforward window confirmation lift",
        (
            "Sweep (SMT side × PSP timeframe × lookforward window). For each, "
            "compare N+1 thesis-confirmation rate with vs without an aligned PSP "
            "(thesis-aligned: high-side SMT → bearish PSP minority; "
            "low-side SMT → bullish PSP minority).\n\n"
            "_Top 30 buckets by absolute lift:_\n\n"
            + _md_table(headers_3b, rows_3b_print)
        ),
    ))

    # ---- 3c ----
    print("\n>>> 3c — Stacked: low-side + active-at-close + best PSP filter")
    # Pick the best (psp_type, window) for low-side previous_day_smt by lift
    best = max(
        (r for r in b_rows
         if r["smt_type"] == "previous_day_smt" and r["smt_side"] == "low"
         and r["lift_pts"] is not None),
        key=lambda r: r["lift_pts"], default=None,
    )
    if best is None:
        print("  (no usable bucket for low-side previous_day_smt)")
        c_md = "_(no usable bucket; sweep returned no positive lift)_"
    else:
        print(
            f"  best low-side bucket: psp={best['psp_type']} window={best['window_h']}h "
            f"lift={best['lift_pts']:+}pts"
        )
        c = analyze_stacked_best(
            con, psp_type=best["psp_type"], window_h=best["window_h"],
        )
        headers_3c = ["active_at_close", "psp_filter", "n", "pct_n1", "pct_n1_or_n2"]
        rows_3c = [
            [r["active_label"], r["psp_label"], str(r["n"]),
             f"{r['pct_n1']}%", f"{r['pct_n1_or_n2']}%"]
            for r in c
        ]
        _print_table(
            f"Stacked: low-side prev_day_smt × active_at_close × {best['psp_type']} "
            f"({best['window_h']}h)",
            headers_3c, rows_3c,
        )
        c_md = (
            f"Best lookforward bucket from 3b for low-side `previous_day_smt`: "
            f"`{best['psp_type']}` × `{best['window_h']}h` (lift "
            f"{best['lift_pts']:+}pts).\n\n"
            + _md_table(headers_3c, rows_3c)
        )
    sections.append(("## 3c — Stacked filter", c_md))

    # ---- write doc ----
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    with open(args.doc, "w", encoding="utf-8") as f:
        f.write("# Composite findings: SMT × PSP\n\n")
        f.write(
            f"_Generated by `scripts/smt_psp_composite_analysis.py` "
            f"on {datetime.now(UTC).isoformat()}._\n\n"
        )
        f.write(
            "Tests three concrete questions about whether PSPs add information "
            "to SMT events, run against the full 2015–2026 event set "
            "(~2,891 SMT, ~15,827 PSP).\n\n"
        )
        f.write(
            "**Important**: every finding here is descriptive. None of these "
            "are validated edges. n-counts matter; small subsets are not signal.\n"
        )
        for heading, body in sections:
            f.write(f"\n---\n\n{heading}\n\n{body}\n")
        f.write("\n")
    print(f"\nwrote {args.doc}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
