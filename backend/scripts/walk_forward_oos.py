"""Walk-forward OOS test on the strongest 3e cell.

Frozen rule (chosen from full 11-year in-sample analysis 2026-05-09):

    Anchor:    low-side previous_day_smt
    Filter:    active_at_close=1
    PSP:       1h_psp aligned (bullish), within 24h, knowable_ts ≤ period_close
    FVG:       4h_fvg aligned (bullish), within 24h, knowable_ts ≤ period_close,
               same primary symbol as SMT

In-sample (full 11 yrs) headline:
    active+has_psp+has_fvg = 111 events, 89.2% N+1, 93.7% N+1-or-N+2
    baseline (resolved+no_psp+no_fvg) = 148 events, 24.3% / 43.2%

This script splits the data chronologically and computes the 8-cell
crosstab (active × has_psp × has_fvg) on each half. If the rule is
real, the train and test halves should show similar pattern. If it
was in-sample overfit, the test half will collapse.

Default cutoff: 2023-01-01. Multiple cutoffs test sensitivity.

Zero look-ahead: same as composite_analysis.py — knowable_ts caps at
period_close, no event firing during N+1 is counted.
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

UTC = timezone.utc
DB_PATH = Path(r"C:\Users\benbr\BacktestStation\data\meta.sqlite")
DOC_PATH = Path(r"C:\Users\benbr\BacktestStation\docs\WALK_FORWARD_OOS.md")

SMT_LAG_MIN: dict[str, int] = {"weekly_smt": 4 * 60, "previous_day_smt": 60}
PSP_LAG_MIN: dict[str, int] = {"1h_psp": 60, "4h_psp": 240, "daily_psp": 24 * 60}
FVG_LAG_MIN: dict[str, int] = {"1h_fvg": 60, "4h_fvg": 240, "daily_fvg": 24 * 60}
OB_LAG_MIN: dict[str, int] = {
    "swept_pdl_1h": 60, "swept_pdl_4h": 240,
    "swept_pdh_1h": 60, "swept_pdh_4h": 240,
    "swept_pwl_4h": 240, "swept_pwl_daily": 24 * 60,
    "swept_pwh_4h": 240, "swept_pwh_daily": 24 * 60,
}

DEFAULT_CUTOFFS = ["2022-01-01", "2023-01-01", "2024-01-01"]


def build_rule(
    smt_type: str, smt_side: str,
    psp_type: str | None, psp_window_h: int,
    fvg_type: str | None, fvg_window_h: int,
    ob_mode: str | None,
) -> dict[str, Any]:
    target_side = "bullish" if smt_side == "low" else "bearish"
    return {
        "smt_type": smt_type,
        "smt_side": smt_side,
        "psp_type": psp_type,
        "psp_target_side": target_side,
        "psp_window_h": psp_window_h,
        "fvg_type": fvg_type,
        "fvg_target_side": target_side,
        "fvg_window_h": fvg_window_h,
        "ob_mode": ob_mode,
        "ob_target_side": target_side,
    }


# ---------- loaders ----------


def load_smt(con: sqlite3.Connection) -> pd.DataFrame:
    sql = """
        SELECT id AS smt_id, event_type, side, primary_symbol,
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
    df["smt_lag_min"] = df["event_type"].map(SMT_LAG_MIN).astype("Int64")
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


def load_ob(con: sqlite3.Connection) -> pd.DataFrame:
    sql = """
        SELECT bar_end_utc AS ob_bar_end, event_type AS ob_mode, side AS ob_side,
               primary_symbol AS ob_primary
        FROM research_events
        WHERE feature_name='order_block'
    """
    df = pd.read_sql_query(sql, con)
    df["ob_bar_end"] = pd.to_datetime(df["ob_bar_end"], utc=True)
    df["ob_lag_min"] = df["ob_mode"].map(OB_LAG_MIN).astype("Int64")
    df["ob_knowable_ts"] = df["ob_bar_end"] + pd.to_timedelta(
        df["ob_lag_min"], unit="m",
    )
    return df.sort_values("ob_knowable_ts").reset_index(drop=True)


# ---------- core: apply the frozen rule to an SMT slice ----------


def _has_aligned_event(
    smt_knowable_ns: np.ndarray,
    smt_period_close_ns: np.ndarray,
    event_knowable_sorted_ns: np.ndarray,
    window_h: int,
) -> np.ndarray:
    if len(event_knowable_sorted_ns) == 0:
        return np.zeros(len(smt_knowable_ns), dtype=bool)
    window_ns = int(window_h) * 3600 * 10**9
    upper_ns = np.minimum(smt_knowable_ns + window_ns, smt_period_close_ns)
    left = np.searchsorted(event_knowable_sorted_ns, smt_knowable_ns, side="right")
    right = np.searchsorted(event_knowable_sorted_ns, upper_ns, side="right")
    return right > left


def apply_rule_crosstab(
    smt: pd.DataFrame,
    psp: pd.DataFrame,
    fvg: pd.DataFrame,
    ob: pd.DataFrame | None,
    rule: dict[str, Any],
) -> list[dict[str, Any]]:
    """Apply the rule and return crosstab rows.

    Dimensions included automatically: active_at_close. PSP/FVG/OB are
    each included if their rule entry is non-None.
    """
    if smt.empty:
        return []
    smt_knowable_ns = smt["smt_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
    period_close_ns = smt["period_close_ts"].to_numpy("datetime64[ns]").astype("int64")
    smt_primary = smt["primary_symbol"].to_numpy()

    flags: dict[str, np.ndarray] = {}

    if rule.get("psp_type"):
        psp_ts = (
            psp[(psp["psp_type"] == rule["psp_type"])
                & (psp["psp_side"] == rule["psp_target_side"])]
            ["psp_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
        )
        flags["psp"] = _has_aligned_event(
            smt_knowable_ns, period_close_ns, psp_ts, rule["psp_window_h"],
        )

    if rule.get("fvg_type"):
        has_fvg = np.zeros(len(smt), dtype=bool)
        for primary in pd.unique(smt_primary):
            primary_mask = smt_primary == primary
            idx = np.where(primary_mask)[0]
            fvg_ts = (
                fvg[(fvg["fvg_type"] == rule["fvg_type"])
                    & (fvg["fvg_side"] == rule["fvg_target_side"])
                    & (fvg["fvg_primary"] == primary)]
                ["fvg_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
            )
            has_fvg[idx] = _has_aligned_event(
                smt_knowable_ns[idx], period_close_ns[idx], fvg_ts,
                rule["fvg_window_h"],
            )
        flags["fvg"] = has_fvg

    if rule.get("ob_mode") and ob is not None:
        has_ob = np.zeros(len(smt), dtype=bool)
        for primary in pd.unique(smt_primary):
            primary_mask = smt_primary == primary
            idx = np.where(primary_mask)[0]
            ob_ts = (
                ob[(ob["ob_mode"] == rule["ob_mode"])
                   & (ob["ob_side"] == rule["ob_target_side"])
                   & (ob["ob_primary"] == primary)]
                ["ob_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
            )
            # OB doesn't have an explicit window — capped at period_close.
            # We use a huge window so only the period_close cap matters.
            has_ob[idx] = _has_aligned_event(
                smt_knowable_ns[idx], period_close_ns[idx], ob_ts, 24 * 30,
            )
        flags["ob"] = has_ob

    # Build cells: cartesian product of {active=1,0} × each present flag.
    smt_w = smt.assign(**flags)
    rows: list[dict[str, Any]] = []
    flag_names = list(flags.keys())  # order: psp, fvg, ob
    flag_values = [(True, False) for _ in flag_names]
    from itertools import product
    for active_label, active_value in (("active", 1), ("resolved", 0)):
        for combo in product(*flag_values):
            mask = (smt_w["active_at_close"] == active_value)
            cell_label: dict[str, str] = {"active": active_label}
            for fn, fv in zip(flag_names, combo):
                mask = mask & (smt_w[fn] == fv)
                cell_label[fn] = f"has_{fn}" if fv else f"no_{fn}"
            sel = smt_w[mask]
            n = len(sel)
            row = {**cell_label, "n": int(n)}
            if n > 0:
                conf_n1 = sel["conf_n1"].fillna(0).astype(int).sum()
                conf_n1_or_n2 = (
                    ((sel["conf_n1"].fillna(0).astype(int) == 1)
                     | (sel["conf_n2"].fillna(0).astype(int) == 1)).sum()
                )
                row["pct_n1"] = round(100.0 * conf_n1 / n, 1)
                row["pct_n1_or_n2"] = round(100.0 * conf_n1_or_n2 / n, 1)
            else:
                row["pct_n1"] = None
                row["pct_n1_or_n2"] = None
            rows.append(row)
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
    parser.add_argument("--smt-type", default="previous_day_smt")
    parser.add_argument("--smt-side", default="low", choices=["low", "high"])
    parser.add_argument(
        "--psp-type", default="1h_psp",
        help="PSP timeframe to filter on, or 'none' to skip the PSP dimension.",
    )
    parser.add_argument("--psp-window-h", type=int, default=24)
    parser.add_argument(
        "--fvg-type", default="4h_fvg",
        help="FVG timeframe, or 'none'.",
    )
    parser.add_argument("--fvg-window-h", type=int, default=24)
    parser.add_argument(
        "--ob-mode", default="none",
        help="OB mode (e.g. swept_pdh_4h), or 'none'.",
    )
    parser.add_argument(
        "--cutoffs", type=str, nargs="+", default=DEFAULT_CUTOFFS,
        help="Chronological train/test split dates (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--target-cell", default=None,
        help="Cell name to highlight in the train/test side-by-side, "
             "as comma-separated flags (e.g. 'active,has_psp,has_fvg,has_ob'). "
             "Default: all flags = has_*.",
    )
    args = parser.parse_args()

    rule = build_rule(
        smt_type=args.smt_type, smt_side=args.smt_side,
        psp_type=None if args.psp_type == "none" else args.psp_type,
        psp_window_h=args.psp_window_h,
        fvg_type=None if args.fvg_type == "none" else args.fvg_type,
        fvg_window_h=args.fvg_window_h,
        ob_mode=None if args.ob_mode == "none" else args.ob_mode,
    )

    con = sqlite3.connect(args.db)
    print(">>> loading events...")
    smt = load_smt(con)
    psp = load_psp(con)
    fvg = load_fvg(con)
    ob = load_ob(con) if rule.get("ob_mode") else None
    smt_anchor = smt[
        (smt["event_type"] == rule["smt_type"]) & (smt["side"] == rule["smt_side"])
    ]
    print(
        f"    SMT total: {len(smt):,}, anchor "
        f"({rule['smt_type']}/{rule['smt_side']}): {len(smt_anchor):,}"
    )

    sections: list[tuple[str, str]] = []

    print("\n>>> FULL SAMPLE (in-sample reference)")
    full = apply_rule_crosstab(smt_anchor, psp, fvg, ob, rule)
    print_crosstab(full, label="FULL SAMPLE")
    sections.append((
        "## Full sample (in-sample reference)",
        f"{len(smt_anchor):,} {rule['smt_type']}/{rule['smt_side']} events.\n\n"
        + crosstab_md(full)
    ))

    target_flags = (
        args.target_cell.split(",") if args.target_cell
        else None  # auto: all has_*
    )

    for cutoff_str in args.cutoffs:
        cutoff_dt = datetime.fromisoformat(cutoff_str).replace(tzinfo=UTC)
        train = smt_anchor[smt_anchor["smt_bar_end"] < cutoff_dt]
        test = smt_anchor[smt_anchor["smt_bar_end"] >= cutoff_dt]
        print(f"\n>>> CUTOFF {cutoff_str}: train n={len(train)}, test n={len(test)}")

        train_rows = apply_rule_crosstab(train, psp, fvg, ob, rule)
        test_rows = apply_rule_crosstab(test, psp, fvg, ob, rule)
        print_crosstab(train_rows, label=f"TRAIN < {cutoff_str}")
        print_crosstab(test_rows, label=f"TEST >= {cutoff_str}")

        diff_section = (
            f"### Cutoff: {cutoff_str}\n\n"
            f"Train n={len(train)} | Test n={len(test)}.\n\n"
            f"**Train (`smt_bar_end < {cutoff_str}`)**\n\n"
            f"{crosstab_md(train_rows)}\n\n"
            f"**Test (`smt_bar_end >= {cutoff_str}`)**\n\n"
            f"{crosstab_md(test_rows)}\n\n"
            f"**Target cell vs baseline**\n\n"
            + side_by_side_target_cell(train_rows, test_rows, target_flags)
        )
        sections.append((f"## Walk-forward split: {cutoff_str}", diff_section))

    args.doc.parent.mkdir(parents=True, exist_ok=True)
    with open(args.doc, "w", encoding="utf-8") as f:
        f.write("# Walk-forward OOS\n\n")
        f.write(
            f"_Generated by `scripts/walk_forward_oos.py` "
            f"on {datetime.now(UTC).isoformat()}._\n\n"
        )
        rule_lines = [
            f"- Anchor: `{rule['smt_type']}` / side=`{rule['smt_side']}` × `active_at_close`",
        ]
        if rule.get("psp_type"):
            rule_lines.append(
                f"- PSP: `{rule['psp_type']}` ({rule['psp_target_side']}) within "
                f"{rule['psp_window_h']}h, knowable_ts ≤ period_close"
            )
        if rule.get("fvg_type"):
            rule_lines.append(
                f"- FVG: `{rule['fvg_type']}` ({rule['fvg_target_side']}) within "
                f"{rule['fvg_window_h']}h, same primary, knowable_ts ≤ period_close"
            )
        if rule.get("ob_mode"):
            rule_lines.append(
                f"- OB: `{rule['ob_mode']}` ({rule['ob_target_side']}), "
                f"same primary, knowable_ts ≤ period_close"
            )
        f.write("**Rule**:\n" + "\n".join(rule_lines) + "\n\n")
        f.write(
            "If real signal, train and test halves should show similar rates. "
            "If in-sample overfit, the test half will collapse.\n"
        )
        for heading, body in sections:
            f.write(f"\n---\n\n{heading}\n\n{body}\n")
    print(f"\nwrote {args.doc}")
    con.close()
    return 0


def _flag_columns(rows: list[dict[str, Any]]) -> list[str]:
    """Discover which flag columns exist in this set of rows
    (active is always present; psp/fvg/ob present iff in the rule)."""
    if not rows:
        return ["active"]
    cols = ["active"]
    for k in ("psp", "fvg", "ob"):
        if k in rows[0]:
            cols.append(k)
    return cols


def print_crosstab(rows: list[dict[str, Any]], *, label: str) -> None:
    print(f"\n=== {label} ===")
    if not rows:
        print("  (empty)")
        return
    cols = _flag_columns(rows)
    header = "  " + "  ".join(f"{c:10s}" for c in cols) + f"  {'n':>5s}  {'pct_n1':>9s}  {'pct_n1or2':>10s}"
    print(header)
    for r in rows:
        n1 = f"{r['pct_n1']}%" if r["pct_n1"] is not None else "—"
        n12 = f"{r['pct_n1_or_n2']}%" if r["pct_n1_or_n2"] is not None else "—"
        print("  " + "  ".join(f"{r[c]:10s}" for c in cols)
              + f"  {r['n']:>5d}  {n1:>9s}  {n12:>10s}")


def crosstab_md(rows: list[dict[str, Any]]) -> str:
    cols = _flag_columns(rows)
    md_rows = []
    for r in rows:
        n1 = f"{r['pct_n1']}%" if r["pct_n1"] is not None else "—"
        n12 = f"{r['pct_n1_or_n2']}%" if r["pct_n1_or_n2"] is not None else "—"
        md_rows.append([r[c] for c in cols] + [str(r["n"]), n1, n12])
    return _md_table(cols + ["n", "pct_n1", "pct_n1_or_n2"], md_rows)


def side_by_side_target_cell(
    train: list[dict[str, Any]], test: list[dict[str, Any]],
    target_flags: list[str] | None = None,
) -> str:
    """Show target vs baseline cell on train vs test. Target flags
    default to 'active' + all has_* dims; baseline = 'resolved' + all no_*."""
    if not train:
        return "_(no rows)_"
    cols = _flag_columns(train)
    if target_flags is None:
        target_flags = ["active"] + [f"has_{c}" for c in cols if c != "active"]
    baseline_flags = ["resolved"] + [f"no_{c}" for c in cols if c != "active"]

    def find(rows, flags):
        for r in rows:
            if all(r[col] == flag for col, flag in zip(cols, flags)):
                return r
        return None

    target_t = find(train, target_flags)
    target_e = find(test, target_flags)
    baseline_t = find(train, baseline_flags)
    baseline_e = find(test, baseline_flags)

    headers = ["cell", "train n", "train pct_n1", "train pct_n1_or_n2",
               "test n", "test pct_n1", "test pct_n1_or_n2"]
    rows = []
    for label, t, e in (
        ("+".join(target_flags) + " (target)", target_t, target_e),
        ("+".join(baseline_flags) + " (baseline)", baseline_t, baseline_e),
    ):
        rows.append([
            label,
            _fmt(t["n"]) if t else "—",
            _fmt(f"{t['pct_n1']}%") if t and t["pct_n1"] is not None else "—",
            _fmt(f"{t['pct_n1_or_n2']}%") if t and t["pct_n1_or_n2"] is not None else "—",
            _fmt(e["n"]) if e else "—",
            _fmt(f"{e['pct_n1']}%") if e and e["pct_n1"] is not None else "—",
            _fmt(f"{e['pct_n1_or_n2']}%") if e and e["pct_n1_or_n2"] is not None else "—",
        ])
    return _md_table(headers, rows)


if __name__ == "__main__":
    raise SystemExit(main())
