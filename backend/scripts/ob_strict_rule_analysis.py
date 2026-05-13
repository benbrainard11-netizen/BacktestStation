"""OB strict-rule analysis.

The order_block detector emits on the LAXEST confirmation rule
(close > ob.body_bottom). Stricter rules are stored as flags:

  - confirms_close_gt_ob_close = True  (laxest — always True for emitted events)
  - confirms_close_gt_ob_open  ∈ {True, False}  (medium)
  - confirms_close_gt_ob_high  ∈ {True, False}  (strictest)

This script buckets OB events by which rules fired and compares
outcome metrics across buckets:
  - Continuation: forward_3/10/50_candles MFE/MAE in thesis
  - Mitigation: tap rate at body_open level + post-tap MFE
  - Invalidation: did a forward bar close past the body's far edge

Question: do stricter confirmations produce stronger forward
behavior? (Or alternatively — does the strictness even matter?)

Output: docs/OB_STRICT_RULE_FINDINGS.md.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

UTC = timezone.utc
DB_PATH = Path(r"C:\Users\benbr\BacktestStation\data\meta.sqlite")
DOC_PATH = Path(r"C:\Users\benbr\BacktestStation\docs\OB_STRICT_RULE_FINDINGS.md")

OB_MODES = [
    "swept_pdl_1h", "swept_pdl_4h", "swept_pdh_1h", "swept_pdh_4h",
    "swept_pwl_4h", "swept_pwl_daily", "swept_pwh_4h", "swept_pwh_daily",
]


def load_ob(con: sqlite3.Connection) -> pd.DataFrame:
    sql = """
        SELECT id, event_type AS ob_mode, side AS ob_side,
               primary_symbol,
               event_data, outcomes
        FROM research_events
        WHERE feature_name='order_block'
          AND outcomes IS NOT NULL
    """
    df = pd.read_sql_query(sql, con)

    def parse(x):
        return json.loads(x) if x else None

    df["ed"] = df["event_data"].map(parse)
    df["o"] = df["outcomes"].map(parse)

    def get(d, *path):
        cur = d
        for k in path:
            if cur is None:
                return None
            cur = cur.get(k) if isinstance(cur, dict) else None
        return cur

    df["confirms_lax"]    = df["ed"].map(lambda d: get(d, "confirms_close_gt_ob_close"))
    df["confirms_medium"] = df["ed"].map(lambda d: get(d, "confirms_close_gt_ob_open"))
    df["confirms_strict"] = df["ed"].map(lambda d: get(d, "confirms_close_gt_ob_high"))

    df["fwd_3_mfe"]  = df["o"].map(lambda d: get(d, "forward_3_candles", "mfe_pts_in_thesis"))
    df["fwd_10_mfe"] = df["o"].map(lambda d: get(d, "forward_10_candles", "mfe_pts_in_thesis"))
    df["fwd_50_mfe"] = df["o"].map(lambda d: get(d, "forward_50_candles", "mfe_pts_in_thesis"))
    df["fwd_3_mae"]  = df["o"].map(lambda d: get(d, "forward_3_candles", "mae_pts_against_thesis"))
    df["fwd_10_mae"] = df["o"].map(lambda d: get(d, "forward_10_candles", "mae_pts_against_thesis"))

    df["invalidated"]      = df["o"].map(lambda d: get(d, "invalidation", "invalidated"))
    df["bars_to_invalid"]  = df["o"].map(lambda d: get(d, "invalidation", "bars_to_invalidation"))
    df["open_tapped"]      = df["o"].map(lambda d: get(d, "level_tags", "open", "wick_tapped"))
    df["full_tapped"]      = df["o"].map(lambda d: get(d, "level_tags", "close", "wick_tapped"))
    df["post_open_3_mfe"]  = df["o"].map(
        lambda d: get(d, "post_tap_reactions", "open_tap", "forward_3_after_tap", "mfe_pts_in_thesis"),
    )
    df["post_open_10_mfe"] = df["o"].map(
        lambda d: get(d, "post_tap_reactions", "open_tap", "forward_10_after_tap", "mfe_pts_in_thesis"),
    )

    return df.drop(columns=["event_data", "outcomes", "ed", "o"])


def classify_strictness(row: pd.Series) -> str:
    """Three buckets: lax_only / medium / strict."""
    if row["confirms_strict"]:
        return "strict"
    if row["confirms_medium"]:
        return "medium"
    return "lax_only"


def aggregate_bucket(sub: pd.DataFrame) -> dict[str, Any]:
    n = int(len(sub))
    if n == 0:
        return {"n": 0}

    def mean(col: str) -> float | None:
        v = sub[col].dropna()
        return round(float(v.mean()), 2) if len(v) else None

    def median(col: str) -> float | None:
        v = sub[col].dropna()
        return round(float(v.median()), 2) if len(v) else None

    def pct_true(col: str) -> float | None:
        v = sub[col].dropna()
        return round(100.0 * float(v.astype(bool).sum()) / len(v), 1) if len(v) else None

    return {
        "n": n,
        "mean_fwd_3_mfe":  mean("fwd_3_mfe"),
        "mean_fwd_10_mfe": mean("fwd_10_mfe"),
        "mean_fwd_50_mfe": mean("fwd_50_mfe"),
        "median_fwd_3_mfe":  median("fwd_3_mfe"),
        "median_fwd_10_mfe": median("fwd_10_mfe"),
        "mean_fwd_3_mae":  mean("fwd_3_mae"),
        "mean_fwd_10_mae": mean("fwd_10_mae"),
        "invalidation_rate_pct": pct_true("invalidated"),
        "open_tap_rate_pct":     pct_true("open_tapped"),
        "full_tap_rate_pct":     pct_true("full_tapped"),
        "mean_post_open_3_mfe":  mean("post_open_3_mfe"),
        "mean_post_open_10_mfe": mean("post_open_10_mfe"),
    }


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def _fmt(x):
    return "—" if x is None else str(x)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--doc", type=Path, default=DOC_PATH)
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    print(">>> loading OB events with outcomes...")
    ob = load_ob(con)
    print(f"    {len(ob):,} OB events loaded")

    ob["strictness"] = ob.apply(classify_strictness, axis=1)
    print()
    print("=== overall strictness distribution ===")
    counts = ob["strictness"].value_counts()
    for k, v in counts.items():
        print(f"  {k:12s} {v:>6,}  ({100.0 * v / len(ob):.1f}%)")

    sections: list[tuple[str, str]] = []

    # Per-mode strictness × outcome metrics.
    for mode in OB_MODES:
        sub = ob[ob["ob_mode"] == mode]
        if sub.empty:
            continue
        bucket_aggs = []
        for strict in ["lax_only", "medium", "strict"]:
            ssub = sub[sub["strictness"] == strict]
            agg = aggregate_bucket(ssub)
            agg["strictness"] = strict
            bucket_aggs.append(agg)
        # Print
        print(f"\n=== {mode} (n={len(sub):,}) ===")
        print(f"  {'strict':10s} {'n':>6s} {'fwd3_mfe':>10s} {'fwd10_mfe':>11s} "
              f"{'fwd50_mfe':>11s} {'fwd3_mae':>10s} {'invalid%':>10s} "
              f"{'opentap%':>10s} {'post3_mfe':>11s}")
        for a in bucket_aggs:
            print(f"  {a['strictness']:10s} {a['n']:>6,d} "
                  f"{_fmt(a.get('mean_fwd_3_mfe')):>10s} "
                  f"{_fmt(a.get('mean_fwd_10_mfe')):>11s} "
                  f"{_fmt(a.get('mean_fwd_50_mfe')):>11s} "
                  f"{_fmt(a.get('mean_fwd_3_mae')):>10s} "
                  f"{_fmt(a.get('invalidation_rate_pct')):>10s} "
                  f"{_fmt(a.get('open_tap_rate_pct')):>10s} "
                  f"{_fmt(a.get('mean_post_open_3_mfe')):>11s}")

        headers = [
            "strictness", "n",
            "fwd_3_mfe", "fwd_10_mfe", "fwd_50_mfe",
            "fwd_3_mae", "fwd_10_mae",
            "invalidation_pct", "open_tap_pct", "full_tap_pct",
            "post_open_3_mfe", "post_open_10_mfe",
        ]
        rows_md = []
        for a in bucket_aggs:
            rows_md.append([
                a["strictness"], str(a["n"]),
                _fmt(a.get("mean_fwd_3_mfe")),
                _fmt(a.get("mean_fwd_10_mfe")),
                _fmt(a.get("mean_fwd_50_mfe")),
                _fmt(a.get("mean_fwd_3_mae")),
                _fmt(a.get("mean_fwd_10_mae")),
                _fmt(a.get("invalidation_rate_pct")),
                _fmt(a.get("open_tap_rate_pct")),
                _fmt(a.get("full_tap_rate_pct")),
                _fmt(a.get("mean_post_open_3_mfe")),
                _fmt(a.get("mean_post_open_10_mfe")),
            ])
        sections.append((
            f"### {mode}",
            f"n={len(sub):,} OB events.\n\n"
            + _md_table(headers, rows_md),
        ))

    # Cross-mode summary: just the strictness distribution.
    summary_rows = []
    overall = aggregate_bucket(ob)
    summary_rows.append([
        "ALL", str(len(ob)),
        _fmt(overall.get("mean_fwd_3_mfe")),
        _fmt(overall.get("mean_fwd_10_mfe")),
        _fmt(overall.get("invalidation_rate_pct")),
    ])
    for strict in ["lax_only", "medium", "strict"]:
        ssub = ob[ob["strictness"] == strict]
        agg = aggregate_bucket(ssub)
        summary_rows.append([
            strict, str(agg["n"]),
            _fmt(agg.get("mean_fwd_3_mfe")),
            _fmt(agg.get("mean_fwd_10_mfe")),
            _fmt(agg.get("invalidation_rate_pct")),
        ])

    args.doc.parent.mkdir(parents=True, exist_ok=True)
    with open(args.doc, "w", encoding="utf-8") as f:
        f.write("# OB strictness × outcomes\n\n")
        f.write(
            f"_Generated by `scripts/ob_strict_rule_analysis.py` "
            f"on {datetime.now(UTC).isoformat()}._\n\n"
        )
        f.write(
            "Buckets OB events by which confirmation rule fired:\n"
            "- `lax_only`: only `close > ob.body_bottom` fired (default emission rule)\n"
            "- `medium`: ALSO `close > ob.body_top` (= `close > ob.open` for bullish)\n"
            "- `strict`: ALSO `close > ob.range_top` (= `close > ob.high` for bullish)\n\n"
            "Strictness is a hierarchy: every `medium` event is also `lax_only`-true; "
            "every `strict` event is also `medium`-true. Buckets here are the "
            "MAXIMUM strictness reached.\n\n"
            "**Question:** do stricter confirmations produce stronger forward "
            "behavior? Or is the laxest rule already capturing all the signal?\n\n"
        )
        f.write("## Overall summary\n\n")
        f.write(_md_table(
            ["bucket", "n", "fwd_3_mfe", "fwd_10_mfe", "invalidation_pct"],
            summary_rows,
        ))
        f.write("\n\n## Per-mode breakdowns\n")
        for heading, body in sections:
            f.write(f"\n{heading}\n\n{body}\n\n")
    print(f"\nwrote {args.doc}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
