"""SMT-conditioned OB analysis — zero look-ahead.

For each (SMT type × SMT side × OB mode) combination: find OBs whose
`knowable_ts` falls in the SMT active window `(smt_knowable_ts,
period_N_close]`, then compare OB outcome metrics to the general
population of OBs of the same (ob_mode, side, primary_symbol).

Also includes the 4-way crosstab `active × has_psp × has_fvg × has_ob`
applied to the OOS-validated anchor (low-side previous_day_smt) — does
adding has_ob sharpen the validated cell?

Zero look-ahead throughout: aligned-event check requires
`event.knowable_ts ≤ period_N_close`.

Output: docs/SMT_OB_FINDINGS.md.
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
DOC_PATH = Path(r"C:\Users\benbr\BacktestStation\docs\SMT_OB_FINDINGS.md")

SMT_LAG_MIN: dict[str, int] = {"weekly_smt": 4 * 60, "previous_day_smt": 60}
PSP_LAG_MIN: dict[str, int] = {"1h_psp": 60, "4h_psp": 240, "daily_psp": 24 * 60}
FVG_LAG_MIN: dict[str, int] = {"1h_fvg": 60, "4h_fvg": 240, "daily_fvg": 24 * 60}
OB_LAG_MIN: dict[str, int] = {
    "swept_pdl_1h": 60, "swept_pdl_4h": 240,
    "swept_pdh_1h": 60, "swept_pdh_4h": 240,
    "swept_pwl_4h": 240, "swept_pwl_daily": 24 * 60,
    "swept_pwh_4h": 240, "swept_pwh_daily": 24 * 60,
}

OB_MODES = list(OB_LAG_MIN.keys())
SMT_TYPES = ["previous_day_smt", "weekly_smt"]
SMT_SIDES = ["high", "low"]

# OB mode → which SMT side it aligns with (bullish OB ↔ low-side SMT).
OB_TO_SIDE = {
    "swept_pdl_1h": "bullish", "swept_pdl_4h": "bullish",
    "swept_pwl_4h": "bullish", "swept_pwl_daily": "bullish",
    "swept_pdh_1h": "bearish", "swept_pdh_4h": "bearish",
    "swept_pwh_4h": "bearish", "swept_pwh_daily": "bearish",
}


# ---------- loaders ----------


def load_smt(con: sqlite3.Connection) -> pd.DataFrame:
    sql = """
        SELECT id AS smt_id, event_type AS smt_type, side AS smt_side,
               primary_symbol AS smt_primary,
               bar_end_utc AS smt_bar_end,
               json_extract(outcomes, '$.next_period.thesis_confirmed_strict') AS conf_n1,
               json_extract(outcomes, '$.n_plus_2.thesis_confirmed_strict') AS conf_n2,
               json_extract(outcomes, '$.period_close.smt_active_for_side_at_close') AS active_at_close,
               json_extract(outcomes, '$.period_close.ts_utc') AS period_close_ts
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


def load_psp(con: sqlite3.Connection) -> pd.DataFrame:
    sql = """
        SELECT bar_end_utc AS psp_bar_end, event_type AS psp_type, side AS psp_side
        FROM research_events
        WHERE feature_name='psp_candle_divergence'
    """
    df = pd.read_sql_query(sql, con)
    df["psp_bar_end"] = pd.to_datetime(df["psp_bar_end"], utc=True)
    df["psp_lag_min"] = df["psp_type"].map(PSP_LAG_MIN).astype("Int64")
    df["psp_knowable_ts"] = df["psp_bar_end"] + pd.to_timedelta(
        df["psp_lag_min"], unit="m",
    )
    return df.sort_values("psp_knowable_ts").reset_index(drop=True)


def load_fvg(con: sqlite3.Connection) -> pd.DataFrame:
    sql = """
        SELECT bar_end_utc AS fvg_bar_end, event_type AS fvg_type, side AS fvg_side,
               primary_symbol AS fvg_primary
        FROM research_events
        WHERE feature_name='fvg_formation'
    """
    df = pd.read_sql_query(sql, con)
    df["fvg_bar_end"] = pd.to_datetime(df["fvg_bar_end"], utc=True)
    df["fvg_lag_min"] = df["fvg_type"].map(FVG_LAG_MIN).astype("Int64")
    df["fvg_knowable_ts"] = df["fvg_bar_end"] + pd.to_timedelta(
        df["fvg_lag_min"], unit="m",
    )
    return df.sort_values("fvg_knowable_ts").reset_index(drop=True)


def load_ob_with_outcomes(con: sqlite3.Connection) -> pd.DataFrame:
    """OB events with v1 outcomes parsed."""
    sql = """
        SELECT id AS ob_id, event_type AS ob_mode, side AS ob_side,
               primary_symbol AS ob_primary,
               bar_end_utc AS ob_bar_end,
               outcomes
        FROM research_events
        WHERE feature_name='order_block'
    """
    df = pd.read_sql_query(sql, con)
    df["ob_bar_end"] = pd.to_datetime(df["ob_bar_end"], utc=True)
    df["ob_lag_min"] = df["ob_mode"].map(OB_LAG_MIN).astype("Int64")
    df["ob_knowable_ts"] = df["ob_bar_end"] + pd.to_timedelta(
        df["ob_lag_min"], unit="m",
    )

    def parse(o: str | None) -> dict | None:
        return json.loads(o) if o else None

    df["o"] = df["outcomes"].map(parse)

    def get(d, *path):
        cur = d
        for k in path:
            if cur is None:
                return None
            cur = cur.get(k) if isinstance(cur, dict) else None
        return cur

    df["o_invalidated"] = df["o"].map(lambda o: get(o, "invalidation", "invalidated"))
    df["o_bars_to_invalid"] = df["o"].map(
        lambda o: get(o, "invalidation", "bars_to_invalidation"),
    )
    df["o_open_tapped"] = df["o"].map(
        lambda o: get(o, "level_tags", "open", "wick_tapped"),
    )
    df["o_full_tapped"] = df["o"].map(
        lambda o: get(o, "level_tags", "close", "wick_tapped"),
    )
    df["o_deepest_wick_frac"] = df["o"].map(
        lambda o: get(o, "deepest_wick_frac"),
    )
    df["o_fwd_3_mfe"] = df["o"].map(
        lambda o: get(o, "forward_3_candles", "mfe_pts_in_thesis"),
    )
    df["o_fwd_10_mfe"] = df["o"].map(
        lambda o: get(o, "forward_10_candles", "mfe_pts_in_thesis"),
    )
    df["o_fwd_50_mfe"] = df["o"].map(
        lambda o: get(o, "forward_50_candles", "mfe_pts_in_thesis"),
    )
    df["o_fwd_3_mae"] = df["o"].map(
        lambda o: get(o, "forward_3_candles", "mae_pts_against_thesis"),
    )
    df["o_post_open_3_mfe"] = df["o"].map(
        lambda o: get(o, "post_tap_reactions", "open_tap", "forward_3_after_tap", "mfe_pts_in_thesis"),
    )
    df["o_post_open_10_mfe"] = df["o"].map(
        lambda o: get(o, "post_tap_reactions", "open_tap", "forward_10_after_tap", "mfe_pts_in_thesis"),
    )
    df = df.drop(columns=["outcomes", "o"])
    return df.sort_values("ob_knowable_ts").reset_index(drop=True)


# ---------- vectorized aligned-event checks ----------


def _has_aligned(
    smt_knowable_ns: np.ndarray,
    smt_period_close_ns: np.ndarray,
    event_knowable_sorted_ns: np.ndarray,
) -> np.ndarray:
    """Aligned = event.knowable_ts ∈ (smt.knowable, smt.period_close]."""
    if len(event_knowable_sorted_ns) == 0:
        return np.zeros(len(smt_knowable_ns), dtype=bool)
    left = np.searchsorted(event_knowable_sorted_ns, smt_knowable_ns, side="right")
    right = np.searchsorted(event_knowable_sorted_ns, smt_period_close_ns, side="right")
    return right > left


def _has_aligned_within_window(
    smt_knowable_ns: np.ndarray,
    smt_period_close_ns: np.ndarray,
    event_knowable_sorted_ns: np.ndarray,
    window_h: int,
) -> np.ndarray:
    """Aligned within window AND ≤ period_close."""
    if len(event_knowable_sorted_ns) == 0:
        return np.zeros(len(smt_knowable_ns), dtype=bool)
    window_ns = int(window_h) * 3600 * 10**9
    upper_ns = np.minimum(smt_knowable_ns + window_ns, smt_period_close_ns)
    left = np.searchsorted(event_knowable_sorted_ns, smt_knowable_ns, side="right")
    right = np.searchsorted(event_knowable_sorted_ns, upper_ns, side="right")
    return right > left


# ---------- OB lift sweep ----------


def ob_lookforward_lift(
    smt: pd.DataFrame, ob: pd.DataFrame,
) -> list[dict[str, Any]]:
    """For each (smt_type, smt_side, ob_mode), compute N+1 confirmation
    rate with vs without an aligned OB on the same primary."""
    results: list[dict[str, Any]] = []

    primaries = ob["ob_primary"].dropna().unique().tolist()
    ob_index: dict[tuple[str, str, str], np.ndarray] = {}
    for ob_mode in OB_MODES:
        ob_side = OB_TO_SIDE[ob_mode]
        for primary in primaries:
            sub = ob[
                (ob["ob_mode"] == ob_mode)
                & (ob["ob_side"] == ob_side)
                & (ob["ob_primary"] == primary)
            ]
            ob_index[(ob_mode, ob_side, primary)] = (
                sub["ob_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
            )

    for smt_type in SMT_TYPES:
        for smt_side in SMT_SIDES:
            target_ob_side = "bullish" if smt_side == "low" else "bearish"
            smt_sub = smt[
                (smt["smt_type"] == smt_type) & (smt["smt_side"] == smt_side)
            ]
            if smt_sub.empty:
                continue
            smt_knowable_ns = (
                smt_sub["smt_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
            )
            period_close_ns = (
                smt_sub["period_close_ts"].to_numpy("datetime64[ns]").astype("int64")
            )
            smt_primary = smt_sub["smt_primary"].to_numpy()
            conf = pd.to_numeric(smt_sub["conf_n1"], errors="coerce")
            conf_valid = conf.notna().to_numpy()
            conf_vals = conf.fillna(0).to_numpy(dtype=float)
            for ob_mode in OB_MODES:
                if OB_TO_SIDE[ob_mode] != target_ob_side:
                    continue
                has_ob = np.zeros(len(smt_sub), dtype=bool)
                for primary in primaries:
                    primary_mask = smt_primary == primary
                    if not primary_mask.any():
                        continue
                    idx = np.where(primary_mask)[0]
                    ob_ts = ob_index.get(
                        (ob_mode, target_ob_side, primary),
                        np.array([], dtype="int64"),
                    )
                    has_ob[idx] = _has_aligned(
                        smt_knowable_ns[idx], period_close_ns[idx], ob_ts,
                    )

                has_mask = has_ob & conf_valid
                no_mask = (~has_ob) & conf_valid
                n_with = int(has_mask.sum())
                n_without = int(no_mask.sum())
                rate_with = (
                    float(conf_vals[has_mask].mean()) * 100.0
                    if n_with else None
                )
                rate_without = (
                    float(conf_vals[no_mask].mean()) * 100.0
                    if n_without else None
                )
                lift = (
                    round(rate_with - rate_without, 1)
                    if rate_with is not None and rate_without is not None
                    else None
                )
                results.append({
                    "smt_type": smt_type, "smt_side": smt_side,
                    "ob_mode": ob_mode,
                    "n_with_ob": n_with, "n_without_ob": n_without,
                    "rate_with": (
                        round(rate_with, 1) if rate_with is not None else None
                    ),
                    "rate_without": (
                        round(rate_without, 1) if rate_without is not None else None
                    ),
                    "lift_pts": lift,
                })

    return results


# ---------- 4-way crosstab on validated anchor ----------


def four_way_crosstab(
    smt: pd.DataFrame,
    psp: pd.DataFrame,
    fvg: pd.DataFrame,
    ob: pd.DataFrame,
    *,
    smt_type: str,
    smt_side: str,
    psp_type: str, psp_window_h: int,
    fvg_type: str, fvg_window_h: int,
    ob_mode: str,
) -> list[dict[str, Any]]:
    """Apply the OOS-validated PSP+FVG filter, plus an OB filter, on
    the anchor (smt_type, smt_side). 16-cell crosstab."""
    smt_sub = smt[
        (smt["smt_type"] == smt_type) & (smt["smt_side"] == smt_side)
    ].copy()
    if smt_sub.empty:
        return []

    target_psp_side = "bullish" if smt_side == "low" else "bearish"
    target_fvg_side = "bullish" if smt_side == "low" else "bearish"
    target_ob_side = OB_TO_SIDE[ob_mode]

    smt_knowable_ns = smt_sub["smt_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
    period_close_ns = smt_sub["period_close_ts"].to_numpy("datetime64[ns]").astype("int64")

    psp_ts = (
        psp[(psp["psp_type"] == psp_type) & (psp["psp_side"] == target_psp_side)]
        ["psp_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
    )
    has_psp = _has_aligned_within_window(
        smt_knowable_ns, period_close_ns, psp_ts, psp_window_h,
    )

    smt_primary = smt_sub["smt_primary"].to_numpy()
    has_fvg = np.zeros(len(smt_sub), dtype=bool)
    has_ob = np.zeros(len(smt_sub), dtype=bool)
    for primary in pd.unique(smt_primary):
        primary_mask = smt_primary == primary
        idx = np.where(primary_mask)[0]
        fvg_ts = (
            fvg[(fvg["fvg_type"] == fvg_type)
                & (fvg["fvg_side"] == target_fvg_side)
                & (fvg["fvg_primary"] == primary)]
            ["fvg_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
        )
        has_fvg[idx] = _has_aligned_within_window(
            smt_knowable_ns[idx], period_close_ns[idx], fvg_ts, fvg_window_h,
        )
        ob_ts = (
            ob[(ob["ob_mode"] == ob_mode)
               & (ob["ob_side"] == target_ob_side)
               & (ob["ob_primary"] == primary)]
            ["ob_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
        )
        has_ob[idx] = _has_aligned(
            smt_knowable_ns[idx], period_close_ns[idx], ob_ts,
        )

    smt_w = smt_sub.assign(has_psp=has_psp, has_fvg=has_fvg, has_ob=has_ob)
    rows: list[dict[str, Any]] = []
    for active_label, active_value in (("active", 1), ("resolved", 0)):
        for psp_label, psp_value in (("has_psp", True), ("no_psp", False)):
            for fvg_label, fvg_value in (("has_fvg", True), ("no_fvg", False)):
                for ob_label, ob_value in (("has_ob", True), ("no_ob", False)):
                    sel = smt_w[
                        (smt_w["active_at_close"] == active_value)
                        & (smt_w["has_psp"] == psp_value)
                        & (smt_w["has_fvg"] == fvg_value)
                        & (smt_w["has_ob"] == ob_value)
                    ]
                    n = len(sel)
                    if n == 0:
                        rows.append({
                            "active": active_label, "psp": psp_label,
                            "fvg": fvg_label, "ob": ob_label,
                            "n": 0, "pct_n1": None, "pct_n1_or_n2": None,
                        })
                        continue
                    n1 = sel["conf_n1"].fillna(0).astype(int).sum()
                    n12 = (
                        ((sel["conf_n1"].fillna(0).astype(int) == 1)
                         | (sel["conf_n2"].fillna(0).astype(int) == 1)).sum()
                    )
                    rows.append({
                        "active": active_label, "psp": psp_label,
                        "fvg": fvg_label, "ob": ob_label,
                        "n": int(n),
                        "pct_n1": round(100.0 * n1 / n, 1),
                        "pct_n1_or_n2": round(100.0 * n12 / n, 1),
                    })
    return rows


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def _fmt(x: Any) -> str:
    if x is None:
        return "—"
    return str(x)


# ---------- main ----------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--doc", type=Path, default=DOC_PATH)
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    print(">>> loading events...")
    smt = load_smt(con)
    psp = load_psp(con)
    fvg = load_fvg(con)
    ob = load_ob_with_outcomes(con)
    print(
        f"    SMT: {len(smt):,}, PSP: {len(psp):,}, "
        f"FVG: {len(fvg):,}, OB: {len(ob):,}"
    )

    sections: list[tuple[str, str]] = []

    # ---- (A) OB lookforward lift sweep ----
    print("\n>>> SMT × OB lift sweep")
    a_rows = ob_lookforward_lift(smt, ob)
    a_rows.sort(key=lambda r: abs(r["lift_pts"] or 0), reverse=True)
    headers_a = [
        "smt_type", "smt_side", "ob_mode",
        "n+rate (with ob)", "n+rate (no ob)", "lift_pts",
    ]
    rows_a: list[list[str]] = []
    for r in a_rows:
        rows_a.append([
            r["smt_type"], r["smt_side"], r["ob_mode"],
            f"{r['n_with_ob']}/{r['rate_with']}%" if r['rate_with'] is not None else f"{r['n_with_ob']}/—",
            f"{r['n_without_ob']}/{r['rate_without']}%" if r['rate_without'] is not None else f"{r['n_without_ob']}/—",
            f"{r['lift_pts']:+}" if r["lift_pts"] is not None else "—",
        ])
    print_lookforward(a_rows[:20])
    sections.append((
        "## A — SMT × aligned-OB N+1 confirmation lift",
        (
            "Same shape as the PSP/FVG sweeps. Aligned OB = same primary "
            "symbol, OB side aligns with SMT thesis (low-side SMT → "
            "bullish OB), `ob_knowable_ts ∈ (smt_knowable_ts, period_close]`.\n\n"
            "_All buckets, sorted by absolute lift:_\n\n"
            + _md_table(headers_a, rows_a)
        ),
    ))

    # ---- (B) 4-way crosstab on validated anchor, sweep all OB modes ----
    print("\n>>> 4-way crosstab on validated anchor, sweeping OB modes")
    bullish_ob_modes = [m for m, s in OB_TO_SIDE.items() if s == "bullish"]
    cell_winners: list[tuple[str, dict[str, Any]]] = []
    for ob_mode in bullish_ob_modes:
        rows = four_way_crosstab(
            smt, psp, fvg, ob,
            smt_type="previous_day_smt", smt_side="low",
            psp_type="1h_psp", psp_window_h=24,
            fvg_type="4h_fvg", fvg_window_h=24,
            ob_mode=ob_mode,
        )
        target = next(
            (r for r in rows
             if r["active"] == "active" and r["psp"] == "has_psp"
             and r["fvg"] == "has_fvg" and r["ob"] == "has_ob"),
            None,
        )
        target_no_ob = next(
            (r for r in rows
             if r["active"] == "active" and r["psp"] == "has_psp"
             and r["fvg"] == "has_fvg" and r["ob"] == "no_ob"),
            None,
        )
        cell_winners.append((ob_mode, {
            "rows": rows, "target": target, "target_no_ob": target_no_ob,
        }))

    summary_rows = []
    for ob_mode, info in cell_winners:
        t = info["target"]
        no = info["target_no_ob"]
        summary_rows.append([
            ob_mode,
            f"{t['n']}" if t else "0",
            f"{t['pct_n1']}%" if t and t["pct_n1"] is not None else "—",
            f"{t['pct_n1_or_n2']}%" if t and t["pct_n1_or_n2"] is not None else "—",
            f"{no['n']}" if no else "0",
            f"{no['pct_n1']}%" if no and no["pct_n1"] is not None else "—",
            f"{no['pct_n1_or_n2']}%" if no and no["pct_n1_or_n2"] is not None else "—",
        ])
    summary_md = _md_table(
        ["ob_mode", "n (with ob)", "pct_n1 (with ob)", "pct_n1_or_n2 (with ob)",
         "n (no ob)", "pct_n1 (no ob)", "pct_n1_or_n2 (no ob)"],
        summary_rows,
    )

    print("\nValidated anchor (low-side previous_day_smt × active+has_psp+has_fvg) "
          "× has_ob — sweeping OB modes:")
    print(f"  baseline (without OB filter): n=111, 89.2% N+1, 93.7% N+1_or_N+2")
    for ob_mode, info in cell_winners:
        t = info["target"]
        no = info["target_no_ob"]
        if t and no:
            print(f"  {ob_mode:20s}  has_ob: n={t['n']:>4d} {t['pct_n1']:>5}% / "
                  f"{t['pct_n1_or_n2']:>5}%   |   no_ob: n={no['n']:>4d} "
                  f"{no['pct_n1']:>5}% / {no['pct_n1_or_n2']:>5}%")

    sections.append((
        "## B — 4-way crosstab on validated anchor (sweeping OB modes)",
        (
            "Anchor: low-side `previous_day_smt`. Existing OOS-validated "
            "filter: `active_at_close=1` × `1h_psp/24h` × `4h_fvg/24h`.\n\n"
            "Question: does adding `has_ob` further sharpen the "
            "**target cell** (active+has_psp+has_fvg) or fragment it into "
            "useless slivers? Sweep all 4 bullish OB modes (low-side SMT → "
            "bullish OB).\n\n"
            "_Baseline (full target cell, no OB filter): n=111, 89.2% / 93.7%._\n\n"
            + summary_md
        ),
    ))

    # Write doc.
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    with open(args.doc, "w", encoding="utf-8") as f:
        f.write("# SMT × OB findings (zero look-ahead)\n\n")
        f.write(
            f"_Generated by `scripts/smt_conditioned_ob_analysis.py` "
            f"on {datetime.now(UTC).isoformat()}._\n\n"
        )
        f.write(
            "Tests whether OB events add information to SMT events, "
            "with strict zero-look-ahead (aligned events must be "
            "CONFIRMED before period N's close).\n\n"
            "**Caveat.** Descriptive only. The 4-way crosstab applies the "
            "OOS-validated PSP+FVG filter — adding OB further is a layered "
            "test of whether we earn additional sharpening for free.\n"
        )
        for heading, body in sections:
            f.write(f"\n---\n\n{heading}\n\n{body}\n")
    print(f"\nwrote {args.doc}")
    con.close()
    return 0


def print_lookforward(rows: list[dict[str, Any]]) -> None:
    print(f"\n  {'smt':25s} {'side':6s} {'ob_mode':18s} "
          f"{'with':>14s} {'without':>14s} {'lift':>7s}")
    for r in rows:
        with_str = (
            f"{r['n_with_ob']}/{r['rate_with']}%"
            if r['rate_with'] is not None else f"{r['n_with_ob']}/—"
        )
        wo_str = (
            f"{r['n_without_ob']}/{r['rate_without']}%"
            if r['rate_without'] is not None else f"{r['n_without_ob']}/—"
        )
        lift_str = f"{r['lift_pts']:+}" if r["lift_pts"] is not None else "—"
        print(f"  {r['smt_type']:25s} {r['smt_side']:6s} {r['ob_mode']:18s} "
              f"{with_str:>14s} {wo_str:>14s} {lift_str:>7s}")


if __name__ == "__main__":
    raise SystemExit(main())
