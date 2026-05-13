"""Sweep failure-mode deep dive.

For each sweep mode, compare the FAILED sweeps (no OB confirmation
within forward horizon) to the CONFIRMED sweeps. Look for systematic
differences in:

  - forward MFE/MAE in thesis direction
  - level-recovery rate (did price close back past the swept ref?)
  - continuation depth (how much further did price go past manip
    extreme — these might be true regime-shift breakouts)
  - context: time of day, day of week
  - sweep_depth_pts: was the sweep shallow vs deep?

Question: are sweep failures a signal of REGIME CONTINUATION (price
keeps going past the swept ref, no reversal) — useful as a negative
training label?

Output: docs/SWEEP_FAILURE_FINDINGS.md.
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
DOC_PATH = Path(r"C:\Users\benbr\BacktestStation\docs\SWEEP_FAILURE_FINDINGS.md")

SWEEP_MODES = [
    "pdl_1h", "pdl_4h", "pdh_1h", "pdh_4h",
    "pwl_4h", "pwl_daily", "pwh_4h", "pwh_daily",
]


def load_sweeps(con: sqlite3.Connection) -> pd.DataFrame:
    sql = """
        SELECT id, event_type AS mode, side, primary_symbol,
               event_data, outcomes, context
        FROM research_events
        WHERE feature_name='liquidity_sweep'
          AND outcomes IS NOT NULL
    """
    df = pd.read_sql_query(sql, con)

    def parse(x):
        return json.loads(x) if x else None

    df["ed"] = df["event_data"].map(parse)
    df["o"] = df["outcomes"].map(parse)
    df["ctx"] = df["context"].map(parse)

    def get(d, *path):
        cur = d
        for k in path:
            if cur is None:
                return None
            cur = cur.get(k) if isinstance(cur, dict) else None
        return cur

    df["did_confirm"]      = df["o"].map(lambda d: get(d, "ob_confirmation", "did_confirm"))
    df["bars_to_first_ob"] = df["o"].map(lambda d: get(d, "ob_confirmation", "bars_to_first_ob"))
    df["fwd_3_mfe"]   = df["o"].map(lambda d: get(d, "forward_3_candles", "mfe_pts_in_thesis"))
    df["fwd_10_mfe"]  = df["o"].map(lambda d: get(d, "forward_10_candles", "mfe_pts_in_thesis"))
    df["fwd_50_mfe"]  = df["o"].map(lambda d: get(d, "forward_50_candles", "mfe_pts_in_thesis"))
    df["fwd_3_mae"]   = df["o"].map(lambda d: get(d, "forward_3_candles", "mae_pts_against_thesis"))
    df["fwd_10_mae"]  = df["o"].map(lambda d: get(d, "forward_10_candles", "mae_pts_against_thesis"))
    df["fwd_50_mae"]  = df["o"].map(lambda d: get(d, "forward_50_candles", "mae_pts_against_thesis"))
    df["recovered"]   = df["o"].map(lambda d: get(d, "swept_level_recovery", "level_recovered"))
    df["bars_to_recovery"] = df["o"].map(lambda d: get(d, "swept_level_recovery", "bars_to_recovery"))
    df["continued"]   = df["o"].map(lambda d: get(d, "forward_continuation", "continued"))
    df["deepest_extension"] = df["o"].map(lambda d: get(d, "forward_continuation", "deepest_extension_pts"))
    df["sweep_depth"] = df["ed"].map(lambda d: get(d, "sweep_depth_pts"))
    df["hour_of_day_et"] = df["ctx"].map(lambda d: get(d, "hour_of_day_et"))
    df["day_of_week_et"] = df["ctx"].map(lambda d: get(d, "day_of_week_et"))

    return df.drop(columns=["event_data", "outcomes", "context", "ed", "o", "ctx"])


def aggregate(sub: pd.DataFrame) -> dict[str, Any]:
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
        "mean_fwd_3_mfe":   mean("fwd_3_mfe"),
        "mean_fwd_10_mfe":  mean("fwd_10_mfe"),
        "mean_fwd_50_mfe":  mean("fwd_50_mfe"),
        "mean_fwd_3_mae":   mean("fwd_3_mae"),
        "mean_fwd_10_mae":  mean("fwd_10_mae"),
        "mean_fwd_50_mae":  mean("fwd_50_mae"),
        "recovery_rate_pct":     pct_true("recovered"),
        "median_bars_to_recovery": median("bars_to_recovery"),
        "continuation_rate_pct": pct_true("continued"),
        "mean_deepest_extension": mean("deepest_extension"),
        "mean_sweep_depth":      mean("sweep_depth"),
        "median_sweep_depth":    median("sweep_depth"),
        "median_bars_to_first_ob": median("bars_to_first_ob"),
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
    print(">>> loading sweep events with outcomes...")
    sw = load_sweeps(con)
    print(f"    {len(sw):,} sweep events loaded")

    sections: list[tuple[str, str]] = []

    for mode in SWEEP_MODES:
        sub = sw[sw["mode"] == mode]
        if sub.empty:
            continue
        confirmed = sub[sub["did_confirm"] == True]  # noqa: E712
        failed = sub[sub["did_confirm"] != True]
        n_total = len(sub)
        n_failed = len(failed)
        if n_failed == 0:
            continue

        print(f"\n=== {mode} (n={n_total:,}, failures={n_failed:,} = {100.0*n_failed/n_total:.1f}%) ===")
        confirmed_agg = aggregate(confirmed)
        failed_agg = aggregate(failed)

        keys = [
            "n",
            "mean_fwd_3_mfe", "mean_fwd_10_mfe", "mean_fwd_50_mfe",
            "mean_fwd_3_mae", "mean_fwd_10_mae", "mean_fwd_50_mae",
            "recovery_rate_pct", "median_bars_to_recovery",
            "continuation_rate_pct", "mean_deepest_extension",
            "mean_sweep_depth", "median_sweep_depth",
        ]
        print(f"  {'metric':30s} {'confirmed':>12s} {'failed':>12s}")
        rows_md = []
        for k in keys:
            cv = confirmed_agg.get(k)
            fv = failed_agg.get(k)
            print(f"  {k:30s} {_fmt(cv):>12s} {_fmt(fv):>12s}")
            rows_md.append([k, _fmt(cv), _fmt(fv)])
        sections.append((
            f"### {mode}",
            f"**n_total = {n_total:,}, failures = {n_failed:,} "
            f"({100.0 * n_failed / n_total:.1f}%)**\n\n"
            + _md_table(["metric", "confirmed", "failed"], rows_md),
        ))

    args.doc.parent.mkdir(parents=True, exist_ok=True)
    with open(args.doc, "w", encoding="utf-8") as f:
        f.write("# Sweep failure-mode findings\n\n")
        f.write(
            f"_Generated by `scripts/sweep_failure_analysis.py` "
            f"on {datetime.now(UTC).isoformat()}._\n\n"
        )
        f.write(
            "Compares CONFIRMED sweeps (an aligned OB confirmed within "
            "the forward horizon) vs FAILED sweeps (no OB confirmation), "
            "by mode. Tests whether failures are systematically different "
            "from confirmations — a feature-engineering question for the "
            "AI training pipeline.\n\n"
            "**Definitions:**\n"
            "- `recovery_rate_pct`: % of sweeps where a forward bar's CLOSE "
            "passed back past the swept ref level in thesis direction\n"
            "- `continuation_rate_pct`: % where a forward bar's WICK went "
            "deeper than the manipulation candle's extreme\n"
            "- `mean_deepest_extension`: deepest wick-extension past the "
            "manipulation extreme, in points\n"
            "- `sweep_depth_pts`: how far past the ref level the manipulation "
            "candle's wick went\n\n"
        )
        for heading, body in sections:
            f.write(f"\n{heading}\n\n{body}\n\n")
    print(f"\nwrote {args.doc}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
