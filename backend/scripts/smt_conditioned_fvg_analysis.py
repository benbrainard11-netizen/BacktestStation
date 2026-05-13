"""SMT-conditioned FVG analysis — zero look-ahead.

Tests Ben's idea: FVGs that form WHILE an SMT thesis is alive may be
qualitatively different from random FVGs. "Thesis is alive" means the
period N hasn't closed yet (we use period_close as the active-window
end per Ben's choice 2026-05-09).

For each (SMT timeframe × SMT side × FVG timeframe) combination:

  1. Filter SMTs to (smt_type, smt_side) with computed outcomes.
  2. For each SMT, find aligned FVGs satisfying:
       - fvg_primary == smt_primary           (FVG on same instrument)
       - fvg_side aligned to SMT thesis       (low-side SMT → bullish FVG;
                                               high-side SMT → bearish FVG)
       - fvg_knowable_ts ∈ (smt_knowable_ts, period_N_close]
                                              (zero look-ahead — FVG must
                                               be CONFIRMED before period
                                               N ends, not during N+1)
  3. Compute aggregates over those SMT-conditioned FVG outcomes.
  4. Compare to general-population baseline (all FVGs of same
     (fvg_type, fvg_side, primary_symbol)).

Metrics per bucket:
  - n_smt_conditioned, n_general
  - tap_rate, close_inside_rate, close_through_rate
  - tap_bar_classification distribution
  - mean post-tap MFE (3 / 10 / 50 candles)
  - mean deepest_wick_frac, deepest_close_frac
  - quartile-hit distribution

Output: docs/SMT_FVG_FINDINGS.md.

Read-only on data/meta.sqlite. Requires fvg_reactions outcome_version=v2.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

UTC = timezone.utc

DB_PATH = Path(r"C:\Users\benbr\BacktestStation\data\meta.sqlite")
DOC_PATH = Path(r"C:\Users\benbr\BacktestStation\docs\SMT_FVG_FINDINGS.md")

PSP_LAG_MIN: dict[str, int] = {"1h_psp": 60, "4h_psp": 240, "daily_psp": 24 * 60}
FVG_LAG_MIN: dict[str, int] = {"1h_fvg": 60, "4h_fvg": 240, "daily_fvg": 24 * 60}
SMT_LAG_MIN: dict[str, int] = {"weekly_smt": 4 * 60, "previous_day_smt": 60}

SMT_TYPES = ["previous_day_smt", "weekly_smt"]
SMT_SIDES = ["high", "low"]
FVG_TYPES = ["1h_fvg", "4h_fvg", "daily_fvg"]


# ---------- loaders ----------


def load_smt(con: sqlite3.Connection) -> pd.DataFrame:
    sql = """
        SELECT id AS smt_id, event_type AS smt_type, side AS smt_side,
               primary_symbol AS smt_primary,
               bar_end_utc AS smt_bar_end,
               json_extract(outcomes, '$.period_close.ts_utc') AS period_close_ts,
               json_extract(outcomes, '$.next_period.thesis_confirmed_strict') AS conf_n1,
               json_extract(outcomes, '$.n_plus_2.thesis_confirmed_strict') AS conf_n2,
               json_extract(outcomes, '$.period_close.smt_active_for_side_at_close') AS active_at_close
        FROM research_events
        WHERE feature_name='smt_htf_reference_divergence'
          AND outcomes IS NOT NULL
    """
    df = pd.read_sql_query(sql, con)
    df["smt_bar_end"] = pd.to_datetime(df["smt_bar_end"], utc=True)
    df["period_close_ts"] = pd.to_datetime(df["period_close_ts"], utc=True)
    df["smt_lag_min"] = df["smt_type"].map(SMT_LAG_MIN).astype("Int64")
    df["smt_knowable_ts"] = df["smt_bar_end"] + pd.to_timedelta(
        df["smt_lag_min"], unit="m",
    )
    return df


def load_fvg_with_outcomes(con: sqlite3.Connection) -> pd.DataFrame:
    """Load FVGs joined with their v2 outcomes."""
    sql = """
        SELECT id AS fvg_id, event_type AS fvg_type, side AS fvg_side,
               primary_symbol AS fvg_primary,
               bar_end_utc AS fvg_bar_end,
               outcomes
        FROM research_events
        WHERE feature_name='fvg_formation'
    """
    df = pd.read_sql_query(sql, con)
    df["fvg_bar_end"] = pd.to_datetime(df["fvg_bar_end"], utc=True)
    df["fvg_lag_min"] = df["fvg_type"].map(FVG_LAG_MIN).astype("Int64")
    df["fvg_knowable_ts"] = df["fvg_bar_end"] + pd.to_timedelta(
        df["fvg_lag_min"], unit="m",
    )

    # Parse the outcomes JSON column. Vectorized json_extract for the
    # most-used fields would be faster than json.loads per row, but
    # 54K rows * single load is acceptable.
    def parse(o: str | None) -> dict[str, Any] | None:
        return json.loads(o) if o else None

    df["outcomes_parsed"] = df["outcomes"].map(parse)

    def safe_get(d: dict | None, *path: str) -> Any:
        cur: Any = d
        for k in path:
            if cur is None:
                return None
            cur = cur.get(k) if isinstance(cur, dict) else None
        return cur

    df["o_outcome_version"] = df["outcomes_parsed"].map(
        lambda o: safe_get(o, "outcome_version"),
    )
    df["o_tapped"] = df["outcomes_parsed"].map(
        lambda o: safe_get(o, "mitigation", "tapped"),
    )
    df["o_closed_inside"] = df["outcomes_parsed"].map(
        lambda o: safe_get(o, "mitigation", "closed_inside"),
    )
    df["o_closed_through"] = df["outcomes_parsed"].map(
        lambda o: safe_get(o, "mitigation", "closed_through"),
    )
    df["o_tap_class"] = df["outcomes_parsed"].map(
        lambda o: safe_get(o, "mitigation", "tap_bar_classification"),
    )
    df["o_bars_to_tap"] = df["outcomes_parsed"].map(
        lambda o: safe_get(o, "mitigation", "bars_to_tap"),
    )
    df["o_deepest_wick_frac"] = df["outcomes_parsed"].map(
        lambda o: safe_get(o, "mitigation", "deepest_wick_frac"),
    )
    df["o_deepest_close_frac"] = df["outcomes_parsed"].map(
        lambda o: safe_get(o, "mitigation", "deepest_close_frac"),
    )
    df["o_post_tap_3_mfe"] = df["outcomes_parsed"].map(
        lambda o: safe_get(o, "post_tap_reaction", "forward_3_after_tap", "mfe_pts_in_thesis"),
    )
    df["o_post_tap_10_mfe"] = df["outcomes_parsed"].map(
        lambda o: safe_get(o, "post_tap_reaction", "forward_10_after_tap", "mfe_pts_in_thesis"),
    )
    df["o_post_tap_50_mfe"] = df["outcomes_parsed"].map(
        lambda o: safe_get(o, "post_tap_reaction", "forward_50_after_tap", "mfe_pts_in_thesis"),
    )
    df["o_post_tap_3_mae"] = df["outcomes_parsed"].map(
        lambda o: safe_get(o, "post_tap_reaction", "forward_3_after_tap", "mae_pts_against_thesis"),
    )

    df = df.drop(columns=["outcomes", "outcomes_parsed"])
    return df.sort_values("fvg_knowable_ts").reset_index(drop=True)


# ---------- analysis ----------


def smt_conditioned_fvg_ids(
    smt: pd.DataFrame,
    fvg: pd.DataFrame,
    *,
    smt_type: str,
    smt_side: str,
    fvg_type: str,
) -> tuple[np.ndarray, dict[str, int]]:
    """For the given (smt_type, smt_side, fvg_type) bucket, return:
      - fvg_id array of all FVGs that fired in the active window of
        any SMT
      - count of n_smt_with_at_least_one_aligned_fvg

    Active window: (smt_knowable_ts, period_close]. Per-primary alignment.
    """
    target_fvg_side = "bearish" if smt_side == "high" else "bullish"
    smt_sub = smt[
        (smt["smt_type"] == smt_type) & (smt["smt_side"] == smt_side)
    ]
    if smt_sub.empty:
        return np.array([], dtype=int), {"n_smt": 0, "n_smt_with_fvg": 0}

    fvg_sub = fvg[
        (fvg["fvg_type"] == fvg_type) & (fvg["fvg_side"] == target_fvg_side)
    ]
    if fvg_sub.empty:
        return np.array([], dtype=int), {"n_smt": int(len(smt_sub)), "n_smt_with_fvg": 0}

    # Per-primary searchsorted over fvg_knowable_ts.
    smt_with_fvg = 0
    matched_fvg_ids: set[int] = set()

    for primary in smt_sub["smt_primary"].unique():
        smt_prim = smt_sub[smt_sub["smt_primary"] == primary]
        fvg_prim = fvg_sub[fvg_sub["fvg_primary"] == primary].sort_values(
            "fvg_knowable_ts"
        )
        if fvg_prim.empty:
            continue

        smt_knowable_ns = (
            smt_prim["smt_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
        )
        period_close_ns = (
            smt_prim["period_close_ts"].to_numpy("datetime64[ns]").astype("int64")
        )
        fvg_knowable_ns = (
            fvg_prim["fvg_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
        )
        fvg_ids = fvg_prim["fvg_id"].to_numpy()

        for i in range(len(smt_prim)):
            left = np.searchsorted(fvg_knowable_ns, smt_knowable_ns[i], side="right")
            right = np.searchsorted(fvg_knowable_ns, period_close_ns[i], side="right")
            if right > left:
                smt_with_fvg += 1
                matched_fvg_ids.update(fvg_ids[left:right].tolist())

    return np.array(sorted(matched_fvg_ids), dtype=int), {
        "n_smt": int(len(smt_sub)),
        "n_smt_with_fvg": int(smt_with_fvg),
    }


def metrics_for_subset(
    fvg_subset: pd.DataFrame, *, label: str,
) -> dict[str, Any]:
    """Aggregate metrics for an FVG subset."""
    n = int(len(fvg_subset))
    if n == 0:
        return {"label": label, "n": 0}

    tap_rate = float(
        fvg_subset["o_tapped"].fillna(False).astype(bool).mean()
    ) * 100.0
    close_in_rate = float(
        fvg_subset["o_closed_inside"].fillna(False).astype(bool).mean()
    ) * 100.0
    close_thru_rate = float(
        fvg_subset["o_closed_through"].fillna(False).astype(bool).mean()
    ) * 100.0

    tap_class = fvg_subset["o_tap_class"].dropna()
    n_tapped = int(len(tap_class))
    counts = Counter(tap_class.tolist())
    pct_wick_reject = (
        100.0 * counts.get("wick_reject", 0) / n_tapped if n_tapped else None
    )
    pct_close_inside = (
        100.0 * counts.get("close_inside", 0) / n_tapped if n_tapped else None
    )
    pct_close_through = (
        100.0 * counts.get("close_through", 0) / n_tapped if n_tapped else None
    )

    # Among tapped FVGs, mean post-tap MFE
    tapped_only = fvg_subset[fvg_subset["o_tapped"] == True]  # noqa: E712
    mfe_3 = (
        float(tapped_only["o_post_tap_3_mfe"].dropna().mean())
        if not tapped_only["o_post_tap_3_mfe"].dropna().empty else None
    )
    mfe_10 = (
        float(tapped_only["o_post_tap_10_mfe"].dropna().mean())
        if not tapped_only["o_post_tap_10_mfe"].dropna().empty else None
    )
    mfe_50 = (
        float(tapped_only["o_post_tap_50_mfe"].dropna().mean())
        if not tapped_only["o_post_tap_50_mfe"].dropna().empty else None
    )
    mae_3 = (
        float(tapped_only["o_post_tap_3_mae"].dropna().mean())
        if not tapped_only["o_post_tap_3_mae"].dropna().empty else None
    )
    median_bars_to_tap = (
        float(tapped_only["o_bars_to_tap"].dropna().median())
        if not tapped_only["o_bars_to_tap"].dropna().empty else None
    )

    return {
        "label": label,
        "n": n,
        "tap_rate_pct": round(tap_rate, 1),
        "close_inside_rate_pct": round(close_in_rate, 1),
        "close_through_rate_pct": round(close_thru_rate, 1),
        "n_tapped": n_tapped,
        "pct_wick_reject_of_tapped": (
            round(pct_wick_reject, 1) if pct_wick_reject is not None else None
        ),
        "pct_close_inside_of_tapped": (
            round(pct_close_inside, 1) if pct_close_inside is not None else None
        ),
        "pct_close_through_of_tapped": (
            round(pct_close_through, 1) if pct_close_through is not None else None
        ),
        "median_bars_to_tap": (
            round(median_bars_to_tap, 1) if median_bars_to_tap is not None else None
        ),
        "mean_post_tap_3_mfe": round(mfe_3, 2) if mfe_3 is not None else None,
        "mean_post_tap_10_mfe": round(mfe_10, 2) if mfe_10 is not None else None,
        "mean_post_tap_50_mfe": round(mfe_50, 2) if mfe_50 is not None else None,
        "mean_post_tap_3_mae": round(mae_3, 2) if mae_3 is not None else None,
    }


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_(no rows)_"
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def _fmt(x: Any) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:g}"
    return str(x)


# ---------- main ----------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--doc", type=Path, default=DOC_PATH)
    parser.add_argument(
        "--require-v2",
        action="store_true",
        default=True,
        help="Skip FVGs without outcome_version=v2 (default true)",
    )
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    print(">>> loading SMT + FVG events into pandas...")
    smt = load_smt(con)
    fvg = load_fvg_with_outcomes(con)
    print(f"    {len(smt):,} SMT events, {len(fvg):,} FVG events")

    if args.require_v2:
        n_before = len(fvg)
        fvg = fvg[fvg["o_outcome_version"] == "v2"].reset_index(drop=True)
        print(f"    filtered to v2 outcomes: {len(fvg):,} / {n_before:,}")
    if fvg.empty:
        print("    no v2 FVG outcomes available — run "
              "`compute_research_outcomes --computer fvg_reactions_v1` first")
        return 1

    sections: list[tuple[str, str]] = []

    for smt_type in SMT_TYPES:
        for smt_side in SMT_SIDES:
            target_fvg_side = "bearish" if smt_side == "high" else "bullish"
            for fvg_type in FVG_TYPES:
                bucket_label = f"{smt_type} / side={smt_side} × {fvg_type} ({target_fvg_side})"
                print(f"\n>>> {bucket_label}")
                cond_ids, summary = smt_conditioned_fvg_ids(
                    smt, fvg,
                    smt_type=smt_type, smt_side=smt_side, fvg_type=fvg_type,
                )
                if summary["n_smt"] == 0:
                    continue
                cond_set = set(int(i) for i in cond_ids)
                # SMT-conditioned subset: FVGs whose id is in cond_set
                cond_subset = fvg[fvg["fvg_id"].isin(cond_set)]
                # General population: same (fvg_type, fvg_side, primary)
                # restricted by SMT primaries we actually saw — keeps
                # comparison apples-to-apples.
                smt_primaries = smt[
                    (smt["smt_type"] == smt_type) & (smt["smt_side"] == smt_side)
                ]["smt_primary"].unique().tolist()
                gen_subset = fvg[
                    (fvg["fvg_type"] == fvg_type)
                    & (fvg["fvg_side"] == target_fvg_side)
                    & (fvg["fvg_primary"].isin(smt_primaries))
                ]

                cond_metrics = metrics_for_subset(cond_subset, label="smt_conditioned")
                gen_metrics = metrics_for_subset(gen_subset, label="general_pop")

                print(f"  SMTs: {summary['n_smt']}, with-aligned-FVG: "
                      f"{summary['n_smt_with_fvg']}")
                print(f"  cond n_fvg: {cond_metrics['n']}, gen n_fvg: {gen_metrics['n']}")

                rows = []
                for key in [
                    "n", "tap_rate_pct", "close_inside_rate_pct",
                    "close_through_rate_pct",
                    "n_tapped", "pct_wick_reject_of_tapped",
                    "pct_close_inside_of_tapped", "pct_close_through_of_tapped",
                    "median_bars_to_tap",
                    "mean_post_tap_3_mfe", "mean_post_tap_10_mfe",
                    "mean_post_tap_50_mfe", "mean_post_tap_3_mae",
                ]:
                    rows.append([
                        key,
                        _fmt(cond_metrics.get(key)),
                        _fmt(gen_metrics.get(key)),
                    ])
                table_md = _md_table(
                    ["metric", "smt_conditioned", "general_pop"], rows,
                )
                section_body = (
                    f"SMTs in bucket: **{summary['n_smt']}** "
                    f"(of which **{summary['n_smt_with_fvg']}** had ≥1 aligned FVG "
                    f"in active window).\n\n"
                    f"{table_md}\n"
                )
                sections.append((
                    f"### {bucket_label}",
                    section_body,
                ))

    # Write the doc.
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    with open(args.doc, "w", encoding="utf-8") as f:
        f.write("# SMT-conditioned FVG findings\n\n")
        f.write(
            f"_Generated by `scripts/smt_conditioned_fvg_analysis.py` "
            f"on {datetime.now(UTC).isoformat()}._\n\n"
        )
        f.write(
            "Compares FVG behavior in the **SMT-thesis-active window** "
            "vs the general FVG population.\n\n"
            "**Active window definition.** For each SMT, the active window "
            "is `(smt_knowable_ts, period_N_close]`. Aligned FVG = same "
            "primary symbol, thesis-aligned side, knowable_ts inside the "
            "window. **Zero look-ahead** — FVGs whose c3 hadn't closed "
            "before period N's end are NOT counted.\n\n"
            "**Comparison baseline.** General population = all FVGs of the "
            "same `(fvg_type, fvg_side, primary_symbol)` across the full "
            "history (includes both SMT-overlapping and non-SMT FVGs). "
            "This is a coarse baseline; a tighter comparison would be "
            "FVGs explicitly NOT in any SMT active window. This is "
            "queued for v2 if the coarse comparison shows signal.\n\n"
            "**Metrics**:\n"
            "- `tap_rate_pct` — % of FVGs whose wick entered the gap\n"
            "- `close_inside_rate_pct` / `close_through_rate_pct` — close-based outcomes\n"
            "- `pct_*_of_tapped` — among tapped, how the tap bar resolved\n"
            "- `median_bars_to_tap` — typical lag from FVG formation to first tap\n"
            "- `mean_post_tap_N_mfe` — average MFE in thesis direction "
            "measured FROM the tap bar's close, over N forward candles\n\n"
            "**Caveat.** Descriptive only. Walk-forward OOS required before "
            "any of these become a strategy.\n"
        )
        for heading, body in sections:
            f.write(f"\n---\n\n{heading}\n\n{body}\n")

    print(f"\nwrote {args.doc}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
