"""SMT × PSP × FVG composite analysis — ZERO LOOK-AHEAD.

Every analysis here enforces a hard rule:

    Aligned-event evidence must be CONFIRMED before period N closes.

That means: for each event we compute `knowable_ts = bar_end_utc +
bucket_minutes` (when the event's bar actually closed). For "is X
aligned to this SMT", we require:

    smt_knowable_ts < event.knowable_ts ≤ MIN(smt_knowable_ts + window,
                                              period_N_close)

Anything firing during N+1 is leakage and is excluded by construction.

Sections:

  3a. Do lookforward PSPs MARK the period's actual extreme?
      (Time-gap version, v2.) Restricted to PSPs CONFIRMED in
      (SMT_knowable_ts, period_close].

  3b. Does an aligned PSP confirmed before N closes lift N+1?
      Sweep (SMT side × PSP timeframe × lookforward window). Window
      is capped at period_close.

  3c. Stacked: low-side + active_at_close + best PSP filter from 3b.

  3d. Same as 3b but for confirming FVGs (per-symbol).

  3e. Triple stack: SMT × aligned-PSP × confirming-FVG, all with
      knowable_ts capped at period_close.

Output: prints tables AND writes docs/COMPOSITE_FINDINGS.md.

Read-only on data/meta.sqlite.

Implementation: load events once into pandas, do per-bucket logic
with numpy searchsorted on `knowable_ts`. The previous SQL EXISTS /
JSON_EXTRACT approach hung on the 73K-event table.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

UTC = timezone.utc

DB_PATH = Path(r"C:\Users\benbr\BacktestStation\data\meta.sqlite")
DOC_PATH = Path(r"C:\Users\benbr\BacktestStation\docs\COMPOSITE_FINDINGS.md")

LOOKFORWARD_WINDOWS_HOURS = [1, 4, 12, 24, 48]
PSP_EVENT_TYPES = ["1h_psp", "4h_psp", "daily_psp"]
FVG_EVENT_TYPES = ["1h_fvg", "4h_fvg", "daily_fvg"]
SMT_EVENT_TYPES = ["previous_day_smt", "weekly_smt"]
EXTREME_TOLERANCE_PTS = 1.0  # within 1 pt = "marked" (v1, retained for ad-hoc use)
MARKS_V2_GAP_WINDOWS_MIN = [60, 240, 720, 1440]  # 1h, 4h, 12h, 24h

# Confirmation lag for each event type — minutes from bar_end_utc
# (bucket START) to bar close. Applied as `knowable_ts = bar_end +
# lag` so we never use evidence before its bar closed.
SMT_LAG_MIN: dict[str, int] = {"weekly_smt": 4 * 60, "previous_day_smt": 60}
PSP_LAG_MIN: dict[str, int] = {"1h_psp": 60, "4h_psp": 240, "daily_psp": 24 * 60}
FVG_LAG_MIN: dict[str, int] = {"1h_fvg": 60, "4h_fvg": 240, "daily_fvg": 24 * 60}


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


# ---------- shared loaders (run once) ----------


def load_smt_events(con: sqlite3.Connection) -> pd.DataFrame:
    """One row per SMT event with the outcome fields needed downstream.
    Restricted to events whose outcomes have been computed.

    Adds `smt_knowable_ts = smt_bar_end + lag(event_type)`. Honest
    rule: don't treat the SMT as "available" before its tracking
    bar closes.
    """
    sql = """
        SELECT id AS smt_id, event_type, side, primary_symbol,
               bar_end_utc AS smt_bar_end,
               json_extract(outcomes, '$.next_period.thesis_confirmed_strict') AS conf_n1,
               json_extract(outcomes, '$.n_plus_2.thesis_confirmed_strict') AS conf_n2,
               json_extract(outcomes, '$.period_close.smt_active_for_side_at_close') AS active_at_close,
               json_extract(outcomes, '$.period_close.ts_utc') AS period_close_ts,
               CASE WHEN side='high'
                    THEN json_extract(outcomes, '$.period_close.primary_period_high_ts')
                    ELSE json_extract(outcomes, '$.period_close.primary_period_low_ts')
               END AS extreme_ts,
               json_extract(outcomes, '$.outcome_version') AS outcome_version
        FROM research_events
        WHERE feature_name='smt_htf_reference_divergence'
          AND outcomes IS NOT NULL
    """
    df = pd.read_sql_query(sql, con)
    df["smt_bar_end"] = pd.to_datetime(df["smt_bar_end"], utc=True)
    df["period_close_ts"] = pd.to_datetime(df["period_close_ts"], utc=True)
    df["extreme_ts"] = pd.to_datetime(df["extreme_ts"], utc=True, errors="coerce")
    df["smt_lag_min"] = df["event_type"].map(SMT_LAG_MIN).astype("Int64")
    df["smt_knowable_ts"] = df["smt_bar_end"] + pd.to_timedelta(
        df["smt_lag_min"], unit="m",
    )
    return df


def load_psp_events(con: sqlite3.Connection) -> pd.DataFrame:
    """PSP events with `psp_knowable_ts = bar_end + lag(event_type)`."""
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


def load_fvg_events(con: sqlite3.Connection) -> pd.DataFrame:
    """FVG events with `fvg_knowable_ts = bar_end + lag(event_type)`.
    side is 'bullish' | 'bearish'. primary_symbol is the symbol the
    FVG formed on (FVG is single-symbol, unlike SMT/PSP).
    """
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


# ---------- 3a-v2 (time-based) ----------


def analyze_marks_extreme_v2_time(
    smt: pd.DataFrame, psp: pd.DataFrame,
) -> list[dict[str, Any]]:
    """For each SMT (v2 outcomes), find the minimum time-gap between
    any PSP fired in (SMT_break_ts, period_close] and the SMT primary
    symbol's actual extreme bar timestamp.
    """
    smt = smt[smt["outcome_version"] == "v2"].copy()
    psp_ns = psp["psp_bar_end"].to_numpy("datetime64[ns]").astype("int64")

    smt_bar_end_ns = smt["smt_bar_end"].to_numpy("datetime64[ns]").astype("int64")
    period_close_ns = smt["period_close_ts"].to_numpy("datetime64[ns]").astype("int64")
    extreme_ns = smt["extreme_ts"].to_numpy("datetime64[ns]").astype("int64")
    nat_sentinel = np.iinfo("int64").min  # datetime64[ns] NaT after int64 cast

    min_gap_min = np.full(len(smt), np.nan)
    for i in range(len(smt)):
        if extreme_ns[i] == nat_sentinel:
            continue
        left = np.searchsorted(psp_ns, smt_bar_end_ns[i], side="right")
        right = np.searchsorted(psp_ns, period_close_ns[i], side="right")
        if right <= left:
            continue
        gaps_ns = np.abs(psp_ns[left:right] - extreme_ns[i])
        min_gap_min[i] = float(gaps_ns.min()) / 1e9 / 60.0
    smt = smt.assign(min_gap_min=min_gap_min)

    out: list[dict[str, Any]] = []
    for smt_type in SMT_EVENT_TYPES:
        for smt_side in ("high", "low"):
            sub = smt[(smt["event_type"] == smt_type) & (smt["side"] == smt_side)]
            for window in MARKS_V2_GAP_WINDOWS_MIN:
                marked_mask = sub["min_gap_min"].notna() & (
                    sub["min_gap_min"] <= window
                )
                marked = sub[marked_mask]
                unmarked = sub[~marked_mask]
                cm = marked[marked["conf_n1"].notna()]
                cu = unmarked[unmarked["conf_n1"].notna()]
                rate_marked = (
                    cm["conf_n1"].sum() / len(cm) * 100.0 if len(cm) else None
                )
                rate_unmarked = (
                    cu["conf_n1"].sum() / len(cu) * 100.0 if len(cu) else None
                )
                out.append({
                    "smt_type": smt_type,
                    "smt_side": smt_side,
                    "gap_window_min": window,
                    "n_total": int(len(sub)),
                    "n_marked": int(len(marked)),
                    "pct_marked": (
                        round(100.0 * len(marked) / len(sub), 1) if len(sub) else None
                    ),
                    "n_conf_marked": int(len(cm)),
                    "rate_marked": (
                        round(rate_marked, 1) if rate_marked is not None else None
                    ),
                    "n_conf_unmarked": int(len(cu)),
                    "rate_unmarked": (
                        round(rate_unmarked, 1) if rate_unmarked is not None else None
                    ),
                    "lift_pts": (
                        round(rate_marked - rate_unmarked, 1)
                        if rate_marked is not None and rate_unmarked is not None
                        else None
                    ),
                })
    return out


# ---------- 3b. Lookforward window confirmation lift (vectorized) ----------


def _has_aligned_event(
    smt_knowable_ns: np.ndarray,
    smt_period_close_ns: np.ndarray,
    event_knowable_sorted_ns: np.ndarray,
    window_h: int,
) -> np.ndarray:
    """For each SMT, return True if at least one aligned event was
    knowable in (smt_knowable_ts, MIN(smt_knowable_ts + window,
    period_close)]. Vectorized over all SMTs at once.

    Zero look-ahead: we never count an event that hadn't confirmed
    by N's close. Capping at period_close means any window that
    would extend into N+1 is truncated.
    """
    if len(event_knowable_sorted_ns) == 0:
        return np.zeros(len(smt_knowable_ns), dtype=bool)
    window_ns = int(window_h) * 3600 * 10**9
    upper_ns = np.minimum(smt_knowable_ns + window_ns, smt_period_close_ns)
    left = np.searchsorted(event_knowable_sorted_ns, smt_knowable_ns, side="right")
    right = np.searchsorted(event_knowable_sorted_ns, upper_ns, side="right")
    return right > left


def analyze_lookforward_lift(
    smt: pd.DataFrame, psp: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Sweep (smt_type, smt_side, psp_type, window_hours) — for each
    bucket compare confirmation rate with vs without an aligned PSP.

    Zero look-ahead: PSP knowable_ts must be in (smt_knowable_ts,
    MIN(smt_knowable_ts + window, period_close)]. Windows that would
    extend into N+1 are truncated at period_close.
    """
    results: list[dict[str, Any]] = []

    psp_index: dict[tuple[str, str], np.ndarray] = {}
    for psp_type in PSP_EVENT_TYPES:
        for psp_side in ("bullish", "bearish"):
            sub = psp[
                (psp["psp_type"] == psp_type) & (psp["psp_side"] == psp_side)
            ]
            psp_index[(psp_type, psp_side)] = (
                sub["psp_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
            )

    for smt_type in SMT_EVENT_TYPES:
        for smt_side in ("high", "low"):
            target_psp_side = "bearish" if smt_side == "high" else "bullish"
            smt_sub = smt[
                (smt["event_type"] == smt_type) & (smt["side"] == smt_side)
            ]
            if smt_sub.empty:
                continue
            smt_knowable_ns = (
                smt_sub["smt_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
            )
            period_close_ns = (
                smt_sub["period_close_ts"].to_numpy("datetime64[ns]").astype("int64")
            )
            conf_series = pd.to_numeric(smt_sub["conf_n1"], errors="coerce")
            conf_valid = conf_series.notna().to_numpy()
            conf_vals = conf_series.fillna(0).to_numpy(dtype=float)
            for psp_type in PSP_EVENT_TYPES:
                psp_ts = psp_index[(psp_type, target_psp_side)]
                for window_h in LOOKFORWARD_WINDOWS_HOURS:
                    has_psp = _has_aligned_event(
                        smt_knowable_ns, period_close_ns, psp_ts, window_h,
                    )

                    has_mask = has_psp & conf_valid
                    no_mask = (~has_psp) & conf_valid
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
                        "smt_type": smt_type,
                        "smt_side": smt_side,
                        "psp_type": psp_type,
                        "window_h": window_h,
                        "n_with_psp": n_with,
                        "rate_with": (
                            round(rate_with, 1) if rate_with is not None else None
                        ),
                        "n_without_psp": n_without,
                        "rate_without": (
                            round(rate_without, 1) if rate_without is not None else None
                        ),
                        "lift_pts": lift,
                    })

    return results


# ---------- 3c. Stacked filter ----------


def analyze_stacked_best(
    smt: pd.DataFrame,
    psp: pd.DataFrame,
    *,
    psp_type: str,
    window_h: int,
) -> list[dict[str, Any]]:
    """For low-side previous_day_smt + active-at-close + thesis-aligned
    PSP within the supplied window, compare to baseline. Zero look-ahead:
    PSP knowable_ts capped at period_close."""
    smt_sub = smt[
        (smt["event_type"] == "previous_day_smt") & (smt["side"] == "low")
    ].copy()
    if smt_sub.empty:
        return []
    psp_sub = psp[
        (psp["psp_type"] == psp_type) & (psp["psp_side"] == "bullish")
    ]
    psp_ts = psp_sub["psp_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
    smt_knowable_ns = smt_sub["smt_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
    period_close_ns = smt_sub["period_close_ts"].to_numpy("datetime64[ns]").astype("int64")
    smt_sub = smt_sub.assign(
        has_aligned_psp=_has_aligned_event(
            smt_knowable_ns, period_close_ns, psp_ts, window_h,
        )
    )

    rows: list[dict[str, Any]] = []
    for active_label, active_value in (("active", 1), ("resolved", 0)):
        for psp_label, psp_value in (("has_psp", True), ("no_psp", False)):
            sel = smt_sub[
                (smt_sub["active_at_close"] == active_value)
                & (smt_sub["has_aligned_psp"] == psp_value)
            ]
            n = len(sel)
            if n == 0:
                continue
            n1 = sel["conf_n1"].fillna(0).astype(int).sum()
            n1_or_n2 = (
                ((sel["conf_n1"].fillna(0).astype(int) == 1)
                 | (sel["conf_n2"].fillna(0).astype(int) == 1)).sum()
            )
            rows.append({
                "active_label": active_label,
                "psp_label": psp_label,
                "n": int(n),
                "pct_n1": round(100.0 * n1 / n, 1),
                "pct_n1_or_n2": round(100.0 * n1_or_n2 / n, 1),
            })
    return rows


# ---------- 3d. FVG lookforward confirmation lift ----------


def analyze_fvg_lookforward_lift(
    smt: pd.DataFrame, fvg: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Same shape as analyze_lookforward_lift but for FVGs.

    Confirming-FVG side mapping: high-side SMT thesis is DOWN → bearish
    FVG; low-side SMT thesis is UP → bullish FVG.

    FVG is per-symbol — consider it aligned only when its primary symbol
    matches the SMT's primary.

    Zero look-ahead: FVG knowable_ts (= c3 close = bar_end + bucket
    minutes) must be in (smt_knowable_ts, MIN(smt_knowable_ts +
    window, period_close)]. This kills the "daily FVG within 24h"
    leakage where c3 hadn't closed yet.
    """
    results: list[dict[str, Any]] = []

    # Per (fvg_type, fvg_side, fvg_primary) sorted knowable-ts arrays
    fvg_index: dict[tuple[str, str, str], np.ndarray] = {}
    primaries = fvg["fvg_primary"].dropna().unique().tolist()
    for fvg_type in FVG_EVENT_TYPES:
        for fvg_side in ("bullish", "bearish"):
            for primary in primaries:
                sub = fvg[
                    (fvg["fvg_type"] == fvg_type)
                    & (fvg["fvg_side"] == fvg_side)
                    & (fvg["fvg_primary"] == primary)
                ]
                fvg_index[(fvg_type, fvg_side, primary)] = (
                    sub["fvg_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
                )

    for smt_type in SMT_EVENT_TYPES:
        for smt_side in ("high", "low"):
            target_fvg_side = "bearish" if smt_side == "high" else "bullish"
            smt_sub = smt[
                (smt["event_type"] == smt_type) & (smt["side"] == smt_side)
            ]
            if smt_sub.empty:
                continue
            smt_knowable_ns = (
                smt_sub["smt_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
            )
            period_close_ns = (
                smt_sub["period_close_ts"].to_numpy("datetime64[ns]").astype("int64")
            )
            smt_primary = smt_sub["primary_symbol"].to_numpy()
            conf_series = pd.to_numeric(smt_sub["conf_n1"], errors="coerce")
            conf_valid = conf_series.notna().to_numpy()
            conf_vals = conf_series.fillna(0).to_numpy(dtype=float)
            for fvg_type in FVG_EVENT_TYPES:
                for window_h in LOOKFORWARD_WINDOWS_HOURS:
                    has_fvg = np.zeros(len(smt_sub), dtype=bool)
                    for primary in primaries:
                        primary_mask = smt_primary == primary
                        if not primary_mask.any():
                            continue
                        idx = np.where(primary_mask)[0]
                        fvg_ts = fvg_index.get(
                            (fvg_type, target_fvg_side, primary), np.array([], dtype="int64"),
                        )
                        has_fvg[idx] = _has_aligned_event(
                            smt_knowable_ns[idx], period_close_ns[idx], fvg_ts, window_h,
                        )

                    has_mask = has_fvg & conf_valid
                    no_mask = (~has_fvg) & conf_valid
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
                        "smt_type": smt_type,
                        "smt_side": smt_side,
                        "fvg_type": fvg_type,
                        "window_h": window_h,
                        "n_with_fvg": n_with,
                        "rate_with": (
                            round(rate_with, 1) if rate_with is not None else None
                        ),
                        "n_without_fvg": n_without,
                        "rate_without": (
                            round(rate_without, 1) if rate_without is not None else None
                        ),
                        "lift_pts": lift,
                    })

    return results


# ---------- 3e. Triple stack: SMT × aligned-PSP × confirming-FVG ----------


def analyze_triple_stack(
    smt: pd.DataFrame,
    psp: pd.DataFrame,
    fvg: pd.DataFrame,
    *,
    smt_type: str,
    smt_side: str,
    psp_type: str,
    psp_window_h: int,
    fvg_type: str,
    fvg_window_h: int,
) -> list[dict[str, Any]]:
    """8-cell crosstab over (active_at_close, has_psp, has_fvg).

    Selects SMTs of the requested (smt_type, smt_side). For each, flags
    has_aligned_psp (thesis-aligned, within psp_window_h) and
    has_aligned_fvg (FVG on the same primary symbol, thesis-aligned,
    within fvg_window_h). Reports n + pct_n1 + pct_n1_or_n2 per cell.
    """
    smt_sub = smt[
        (smt["event_type"] == smt_type) & (smt["side"] == smt_side)
    ].copy()
    if smt_sub.empty:
        return []

    target_psp_side = "bearish" if smt_side == "high" else "bullish"
    target_fvg_side = "bearish" if smt_side == "high" else "bullish"

    smt_knowable_ns = smt_sub["smt_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
    period_close_ns = smt_sub["period_close_ts"].to_numpy("datetime64[ns]").astype("int64")

    # has_aligned_psp (cross-symbol — PSP is by side only)
    psp_ts = (
        psp[(psp["psp_type"] == psp_type) & (psp["psp_side"] == target_psp_side)]
        ["psp_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
    )
    has_psp = _has_aligned_event(
        smt_knowable_ns, period_close_ns, psp_ts, psp_window_h,
    )

    # has_aligned_fvg (per-primary)
    smt_primary = smt_sub["primary_symbol"].to_numpy()
    has_fvg = np.zeros(len(smt_sub), dtype=bool)
    for primary in pd.unique(smt_primary):
        primary_mask = smt_primary == primary
        if not primary_mask.any():
            continue
        idx = np.where(primary_mask)[0]
        fvg_ts = (
            fvg[
                (fvg["fvg_type"] == fvg_type)
                & (fvg["fvg_side"] == target_fvg_side)
                & (fvg["fvg_primary"] == primary)
            ]["fvg_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
        )
        has_fvg[idx] = _has_aligned_event(
            smt_knowable_ns[idx], period_close_ns[idx], fvg_ts, fvg_window_h,
        )

    smt_sub = smt_sub.assign(has_psp=has_psp, has_fvg=has_fvg)

    rows: list[dict[str, Any]] = []
    for active_label, active_value in (("active", 1), ("resolved", 0)):
        for psp_label, psp_value in (("has_psp", True), ("no_psp", False)):
            for fvg_label, fvg_value in (("has_fvg", True), ("no_fvg", False)):
                sel = smt_sub[
                    (smt_sub["active_at_close"] == active_value)
                    & (smt_sub["has_psp"] == psp_value)
                    & (smt_sub["has_fvg"] == fvg_value)
                ]
                n = len(sel)
                if n == 0:
                    rows.append({
                        "active_label": active_label,
                        "psp_label": psp_label,
                        "fvg_label": fvg_label,
                        "n": 0,
                        "pct_n1": None,
                        "pct_n1_or_n2": None,
                    })
                    continue
                n1 = sel["conf_n1"].fillna(0).astype(int).sum()
                n1_or_n2 = (
                    ((sel["conf_n1"].fillna(0).astype(int) == 1)
                     | (sel["conf_n2"].fillna(0).astype(int) == 1)).sum()
                )
                rows.append({
                    "active_label": active_label,
                    "psp_label": psp_label,
                    "fvg_label": fvg_label,
                    "n": int(n),
                    "pct_n1": round(100.0 * n1 / n, 1),
                    "pct_n1_or_n2": round(100.0 * n1_or_n2 / n, 1),
                })
    return rows


# ---------- main ----------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--doc", type=Path, default=DOC_PATH)
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    sections: list[tuple[str, str]] = []  # (heading, body_md)

    print(">>> loading SMT + PSP + FVG events into pandas...")
    smt = load_smt_events(con)
    psp = load_psp_events(con)
    fvg = load_fvg_events(con)
    print(
        f"    loaded {len(smt):,} SMT events, {len(psp):,} PSP events, "
        f"{len(fvg):,} FVG events"
    )

    # ---- 3a-v2 (time-based) ----
    print("\n>>> 3a-v2 — PSP time-gap to actual extreme bar")
    a2t = analyze_marks_extreme_v2_time(smt, psp)
    headers_3a2t = [
        "smt_type", "side", "gap_le_min", "n_total", "n_marked", "% marked",
        "rate_n1 marked", "rate_n1 unmarked", "lift",
    ]
    rows_3a2t: list[list[str]] = []
    for r in a2t:
        rows_3a2t.append([
            r["smt_type"], r["smt_side"], str(r["gap_window_min"]),
            str(r["n_total"]), str(r["n_marked"]),
            f"{r['pct_marked']}%" if r['pct_marked'] is not None else "—",
            (
                f"{r['rate_marked']}% (n={r['n_conf_marked']})"
                if r['rate_marked'] is not None else "—"
            ),
            (
                f"{r['rate_unmarked']}% (n={r['n_conf_unmarked']})"
                if r['rate_unmarked'] is not None else "—"
            ),
            f"{r['lift_pts']:+}" if r['lift_pts'] is not None else "—",
        ])
    _print_table(
        "PSP time-gap to extreme bar — by SMT type x side x window",
        headers_3a2t, rows_3a2t,
    )
    sections.append((
        "## 3a-v2 — PSP time-gap to actual extreme bar (looser, time-based)",
        (
            "v1 was binary on price (within 1pt) and got 0% across the "
            "board. v2 uses TIME proximity: requires SMT outcomes v2 (which "
            "stores `primary_period_high_ts` / `primary_period_low_ts`). "
            "For each SMT, find the minimum time-gap between any in-period "
            "PSP and the actual extreme bar timestamp.\n\n"
            + _md_table(headers_3a2t, rows_3a2t)
        ),
    ))

    # ---- 3b ----
    print("\n>>> 3b — Lookforward window aligned-PSP confirmation lift")
    b_rows = analyze_lookforward_lift(smt, psp)
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
            "**Zero look-ahead.** PSP `knowable_ts = bar_end + "
            "bucket_minutes`. Window upper bound is "
            "MIN(smt_knowable_ts + window, period_close); a PSP "
            "firing during N+1 is NOT counted.\n\n"
            "_Top 30 buckets by absolute lift:_\n\n"
            + _md_table(headers_3b, rows_3b_print)
        ),
    ))

    # ---- 3c ----
    print("\n>>> 3c — Stacked: low-side + active-at-close + best PSP filter")
    # Pick the best (psp_type, window) for low-side previous_day_smt by
    # lift, with n_with_psp >= 100 to avoid tiny-cell flukes (e.g. a
    # daily_psp/1h cell with n=6 has no statistical relevance).
    best = max(
        (r for r in b_rows
         if r["smt_type"] == "previous_day_smt" and r["smt_side"] == "low"
         and r["lift_pts"] is not None and r["n_with_psp"] >= 100),
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
            smt, psp, psp_type=best["psp_type"], window_h=best["window_h"],
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

    # ---- 3d. FVG lookforward confirmation lift ----
    print("\n>>> 3d — FVG lookforward confirming-FVG lift")
    d_rows = analyze_fvg_lookforward_lift(smt, fvg)
    d_rows.sort(key=lambda r: abs(r["lift_pts"] or 0), reverse=True)
    headers_3d = [
        "smt_type", "side", "fvg_type", "win_h",
        "n+rate (with fvg)", "n+rate (no fvg)", "lift_pts",
    ]
    rows_3d_print: list[list[str]] = []
    for r in d_rows[:30]:
        rows_3d_print.append([
            r["smt_type"], r["smt_side"], r["fvg_type"], str(r["window_h"]),
            (
                f"{r['n_with_fvg']}/{r['rate_with']}%"
                if r['rate_with'] is not None else f"{r['n_with_fvg']}/—"
            ),
            (
                f"{r['n_without_fvg']}/{r['rate_without']}%"
                if r['rate_without'] is not None else f"{r['n_without_fvg']}/—"
            ),
            f"{r['lift_pts']:+}" if r["lift_pts"] is not None else "—",
        ])
    _print_table(
        "FVG lookforward x FVG timeframe (top 30 by |lift|)",
        headers_3d, rows_3d_print,
    )
    sections.append((
        "## 3d — Confirming-FVG lookforward lift",
        (
            "Same shape as 3b but with FVGs instead of PSPs. Confirming "
            "side: high-side SMT thesis is DOWN → bearish FVG; low-side "
            "SMT thesis is UP → bullish FVG. FVG must be on the SAME "
            "primary symbol as the SMT (FVGs are single-symbol).\n\n"
            "**Zero look-ahead.** Each FVG's `knowable_ts = bar_end + "
            "bucket_minutes` (= c3 close). Aligned-FVG window is capped "
            "at period_close. Daily FVGs whose c3 hasn't closed before "
            "N's close are NOT counted as aligned.\n\n"
            "_Top 30 buckets by absolute lift:_\n\n"
            + _md_table(headers_3d, rows_3d_print)
        ),
    ))

    # ---- 3e. Triple stack: SMT × aligned-PSP × confirming-FVG ----
    print("\n>>> 3e — Triple stack: SMT × aligned-PSP × confirming-FVG")
    # Anchor cell: low-side previous_day_smt (the strongest single bucket
    # we've seen in 3c). Pick best PSP and FVG for that cell from
    # 3b/3d sweeps.
    target_smt_type = "previous_day_smt"
    target_smt_side = "low"
    # Both auto-picks require n_with >= 100 to avoid tiny-cell flukes.
    best_psp = max(
        (r for r in b_rows
         if r["smt_type"] == target_smt_type and r["smt_side"] == target_smt_side
         and r["lift_pts"] is not None and r["n_with_psp"] >= 100),
        key=lambda r: r["lift_pts"], default=None,
    )
    best_fvg = max(
        (r for r in d_rows
         if r["smt_type"] == target_smt_type and r["smt_side"] == target_smt_side
         and r["lift_pts"] is not None and r["n_with_fvg"] >= 100),
        key=lambda r: r["lift_pts"], default=None,
    )
    if best_psp is None or best_fvg is None:
        print("  (insufficient bucket coverage for triple stack)")
        e_md = "_(insufficient bucket coverage for triple stack)_"
    else:
        print(
            f"  anchor: {target_smt_type}/{target_smt_side}; "
            f"psp={best_psp['psp_type']} window={best_psp['window_h']}h "
            f"(lift {best_psp['lift_pts']:+}); "
            f"fvg={best_fvg['fvg_type']} window={best_fvg['window_h']}h "
            f"(lift {best_fvg['lift_pts']:+})"
        )
        e = analyze_triple_stack(
            smt, psp, fvg,
            smt_type=target_smt_type, smt_side=target_smt_side,
            psp_type=best_psp["psp_type"], psp_window_h=best_psp["window_h"],
            fvg_type=best_fvg["fvg_type"], fvg_window_h=best_fvg["window_h"],
        )
        headers_3e = [
            "active", "psp", "fvg", "n", "pct_n1", "pct_n1_or_n2",
        ]
        rows_3e: list[list[str]] = []
        for r in e:
            rows_3e.append([
                r["active_label"], r["psp_label"], r["fvg_label"], str(r["n"]),
                f"{r['pct_n1']}%" if r["pct_n1"] is not None else "—",
                f"{r['pct_n1_or_n2']}%" if r["pct_n1_or_n2"] is not None else "—",
            ])
        _print_table(
            f"Triple stack: {target_smt_type}/{target_smt_side} × active × "
            f"{best_psp['psp_type']}({best_psp['window_h']}h) × "
            f"{best_fvg['fvg_type']}({best_fvg['window_h']}h)",
            headers_3e, rows_3e,
        )
        e_md = (
            f"Anchor: low-side `previous_day_smt`. Best PSP filter from 3b: "
            f"`{best_psp['psp_type']}` × `{best_psp['window_h']}h` (lift "
            f"{best_psp['lift_pts']:+}). Best FVG filter from 3d (n_with≥100): "
            f"`{best_fvg['fvg_type']}` × `{best_fvg['window_h']}h` (lift "
            f"{best_fvg['lift_pts']:+}).\n\n"
            "**Zero look-ahead.** All aligned events must be CONFIRMED "
            "(knowable_ts ≤ period_close) before N+1 begins.\n\n"
            "_Cells: active_at_close × has_aligned_PSP × has_confirming_FVG._\n\n"
            + _md_table(headers_3e, rows_3e)
        )
    sections.append(("## 3e — Triple stack (SMT × PSP × FVG)", e_md))

    # ---- write doc ----
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    with open(args.doc, "w", encoding="utf-8") as f:
        f.write("# Composite findings: SMT × PSP × FVG (zero look-ahead)\n\n")
        f.write(
            f"_Generated by `scripts/smt_psp_composite_analysis.py` "
            f"on {datetime.now(UTC).isoformat()}._\n\n"
        )
        f.write(
            f"Tests whether PSPs and/or FVGs add information to SMT "
            f"events, run against the full event set "
            f"({len(smt):,} SMT, {len(psp):,} PSP, {len(fvg):,} FVG).\n\n"
        )
        f.write(
            "**Zero look-ahead.** Every aligned-event check uses `knowable_ts "
            "= bar_end_utc + bucket_minutes` and is capped at `period_N_close`. "
            "An event whose bar hadn't closed before N's close is NEVER "
            "counted as aligned. No window can bleed into the N+1 prediction "
            "period.\n\n"
        )
        f.write(
            "**Important**: every finding here is descriptive. None of these "
            "are validated edges. Walk-forward OOS is required before any of "
            "these cells become a strategy. n-counts matter; small subsets "
            "are not signal.\n"
        )
        for heading, body in sections:
            f.write(f"\n---\n\n{heading}\n\n{body}\n")
        f.write("\n")
    print(f"\nwrote {args.doc}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
