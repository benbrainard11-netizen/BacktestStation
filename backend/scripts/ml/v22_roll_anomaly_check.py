"""Paper-trade Gate 1 — roll-anomaly check (OB strict + Sweep reversed).

QUESTION: is the v20 result inflated by spurious moves on continuous-
contract roll days?

CONTEXT: BacktestStation uses continuous-symbol bars (NQ.c.0, ES.c.0)
which are stitched front-month series. When the front month rolls
(quarterly), the price series jumps. Databento back-adjusts prices,
but discontinuities can still create artificial intraday moves around
the roll window.

METHOD:
  - For each quarterly expiry (3rd Friday of Mar/Jun/Sep/Dec), define a
    roll window: [expiry - 5 days, expiry + 1 day]. Databento typically
    rolls the continuous series ~5 days before expiry; the exact day
    varies by liquidity.
  - For each trade in OB strict + Sweep reversed (filtered) across
    both holdouts, mark whether entry or exit falls in any roll window.
  - Compute cum_R on roll-adjacent trades vs non-roll-adjacent trades.
  - Compare share of cum_R from roll-adjacent days vs expected share
    under uniform distribution (roll_days / total_days).

PASS THRESHOLD (pre-registered):
  - roll-adjacent cum_R share <= 2x expected share  (NOT inflated)
  - roll-adjacent avg_R within 50%-200% of non-adjacent avg_R
  - If outside either, FAIL.

LIMITATIONS:
  - We don't have per-contract bars on disk, so we can't compare
    continuous-symbol prints to per-contract prints. This is the
    "limited" check called out in SYSTEM_MAP.md. A full per-contract
    audit would require pulling and storing per-contract NQ + ES.

OUTPUT:
  experiments/paper_trade_gates_2026_05_17/results/v22_roll_anomaly_check.json
  experiments/paper_trade_gates_2026_05_17/results/v22_roll_anomaly_check.md
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]  # backend/scripts/ml/this.py -> repo root
V20_DIR = REPO_ROOT / "experiments" / "locked_walkforward_2026_05_17" / "results"
OUT_DIR = REPO_ROOT / "experiments" / "paper_trade_gates_2026_05_17" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------- roll-window builder ----------


def _third_friday(year: int, month: int) -> date:
    """3rd Friday of (year, month). Equity-index futures expire here."""
    d = date(year, month, 1)
    fridays = [
        d + timedelta(days=i)
        for i in range(31)
        if (d + timedelta(days=i)).month == month
        and (d + timedelta(days=i)).weekday() == 4
    ]
    return fridays[2]


def build_roll_windows(years: list[int]) -> list[tuple[date, date]]:
    """For each quarterly expiry month (Mar/Jun/Sep/Dec), build a window
    [expiry-5 days, expiry+1 day]. Returns sorted list of (start, end)."""
    windows: list[tuple[date, date]] = []
    for year in years:
        for month in (3, 6, 9, 12):
            expiry = _third_friday(year, month)
            windows.append((expiry - timedelta(days=5), expiry + timedelta(days=1)))
    return sorted(windows)


def is_in_any_roll_window(
    d: date, windows: list[tuple[date, date]]
) -> bool:
    for start, end in windows:
        if start <= d <= end:
            return True
        if d < start:
            break  # windows are sorted
    return False


def total_roll_days(
    start: date, end: date, windows: list[tuple[date, date]]
) -> int:
    """Number of days in [start, end] that fall inside any roll window."""
    count = 0
    cur = start
    while cur <= end:
        if is_in_any_roll_window(cur, windows):
            count += 1
        cur += timedelta(days=1)
    return count


# ---------- load + classify ----------


FAMILY_FILES = {
    "OB strict": [
        "trades_locked_holdout_1_OB_strict_primary_2tick.csv",
        "trades_locked_holdout_2_OB_strict_primary_2tick.csv",
    ],
    "Sweep reversed (filtered)": [
        "trades_locked_holdout_1_Sweep_reversed_filtered_primary_2tick.csv",
        "trades_locked_holdout_2_Sweep_reversed_filtered_primary_2tick.csv",
    ],
}


def load_family_trades(filenames: list[str]) -> pd.DataFrame:
    frames = []
    for fn in filenames:
        path = V20_DIR / fn
        df = pd.read_csv(path)
        df["__source"] = fn
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    # Only count entered + exited trades (drop unfilled).
    out = out.dropna(subset=["pnl_r", "entry_ts", "exit_ts"]).copy()
    out["entry_ts"] = pd.to_datetime(out["entry_ts"], utc=True)
    out["exit_ts"] = pd.to_datetime(out["exit_ts"], utc=True)
    return out


def classify_roll(df: pd.DataFrame, windows: list[tuple[date, date]]) -> pd.Series:
    """Trade is 'roll-adjacent' if either entry or exit lands in a roll
    window."""
    entry_dates = df["entry_ts"].dt.date
    exit_dates = df["exit_ts"].dt.date
    in_window = entry_dates.map(
        lambda d: is_in_any_roll_window(d, windows)
    ) | exit_dates.map(lambda d: is_in_any_roll_window(d, windows))
    return in_window


# ---------- analyze ----------


def analyze_family(
    name: str, df: pd.DataFrame, windows: list[tuple[date, date]]
) -> dict:
    in_roll = classify_roll(df, windows)
    roll_df = df[in_roll]
    non_roll_df = df[~in_roll]

    total_cum_r = float(df["pnl_r"].sum())
    roll_cum_r = float(roll_df["pnl_r"].sum())
    non_roll_cum_r = float(non_roll_df["pnl_r"].sum())

    span_start = df["entry_ts"].min().date()
    span_end = df["exit_ts"].max().date()
    span_days = (span_end - span_start).days + 1
    roll_days = total_roll_days(span_start, span_end, windows)
    expected_roll_share = roll_days / span_days

    roll_share = roll_cum_r / total_cum_r if total_cum_r != 0 else 0.0
    inflation_ratio = (
        roll_share / expected_roll_share if expected_roll_share > 0 else 0.0
    )

    roll_avg_r = float(roll_df["pnl_r"].mean()) if len(roll_df) else 0.0
    non_roll_avg_r = (
        float(non_roll_df["pnl_r"].mean()) if len(non_roll_df) else 0.0
    )
    avg_r_ratio = (
        roll_avg_r / non_roll_avg_r if non_roll_avg_r != 0 else float("inf")
    )

    # Pre-registered thresholds
    inflation_ok = inflation_ratio <= 2.0
    avg_r_ok = 0.5 <= avg_r_ratio <= 2.0 if non_roll_avg_r != 0 else True
    passed = bool(inflation_ok and avg_r_ok)

    return {
        "family": name,
        "trade_span_start": str(span_start),
        "trade_span_end": str(span_end),
        "span_days": span_days,
        "roll_days": roll_days,
        "expected_roll_share": round(expected_roll_share, 4),
        "n_trades_total": int(len(df)),
        "n_trades_roll_adjacent": int(len(roll_df)),
        "n_trades_non_adjacent": int(len(non_roll_df)),
        "cum_r_total": round(total_cum_r, 2),
        "cum_r_roll_adjacent": round(roll_cum_r, 2),
        "cum_r_non_adjacent": round(non_roll_cum_r, 2),
        "roll_cum_r_share": round(roll_share, 4),
        "inflation_ratio": round(inflation_ratio, 3),
        "avg_r_roll_adjacent": round(roll_avg_r, 4),
        "avg_r_non_adjacent": round(non_roll_avg_r, 4),
        "avg_r_ratio": round(avg_r_ratio, 3)
        if avg_r_ratio != float("inf")
        else "inf",
        "checks": {
            "inflation_ok_le_2x": bool(inflation_ok),
            "avg_r_ratio_within_0.5_to_2": bool(avg_r_ok),
        },
        "passed": passed,
    }


# ---------- write report ----------


def write_md(results: list[dict], windows: list[tuple[date, date]]) -> str:
    lines: list[str] = []
    lines.append("# v22 — Roll-Anomaly Check (Paper-Trade Gate 1)")
    lines.append("")
    lines.append(f"_Generated {datetime.utcnow().isoformat()}Z_")
    lines.append("")
    lines.append(
        "Tests whether the v20 OB strict + Sweep reversed result is "
        "inflated by continuous-contract roll-window distortions. "
        "Limited check — no per-contract bars on disk."
    )
    lines.append("")
    lines.append("## Roll windows tested")
    lines.append("")
    lines.append(f"{len(windows)} quarterly windows. Each is "
                 f"[expiry - 5 days, expiry + 1 day].")
    lines.append("")
    overall_pass = all(r["passed"] for r in results)
    lines.append(f"## Verdict: {'PASS' if overall_pass else 'FAIL'}")
    lines.append("")
    for r in results:
        lines.append(f"### {r['family']}")
        lines.append("")
        lines.append(f"- Span: {r['trade_span_start']} → {r['trade_span_end']} ({r['span_days']} days)")
        lines.append(f"- Roll days in span: {r['roll_days']} ({r['expected_roll_share']*100:.1f}% of days)")
        lines.append(f"- Total trades: {r['n_trades_total']:,} (roll-adj: {r['n_trades_roll_adjacent']:,}, non-adj: {r['n_trades_non_adjacent']:,})")
        lines.append(f"- Total cum_R: {r['cum_r_total']:.2f}")
        lines.append(f"- Cum_R roll-adjacent: {r['cum_r_roll_adjacent']:.2f} ({r['roll_cum_r_share']*100:.1f}%)")
        lines.append(f"- Cum_R non-adjacent: {r['cum_r_non_adjacent']:.2f}")
        lines.append(f"- Inflation ratio (actual_share / expected_share): {r['inflation_ratio']}")
        lines.append(f"- avg_R roll-adj: {r['avg_r_roll_adjacent']} / non-adj: {r['avg_r_non_adjacent']} (ratio: {r['avg_r_ratio']})")
        lines.append(f"- Checks: inflation ≤ 2x = {r['checks']['inflation_ok_le_2x']}, avg_R ratio in [0.5, 2] = {r['checks']['avg_r_ratio_within_0.5_to_2']}")
        lines.append(f"- **{'PASS' if r['passed'] else 'FAIL'}**")
        lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- `inflation_ratio` > 2 → cum_R disproportionately concentrated on roll days; likely artifact.")
    lines.append("- `avg_R ratio` outside [0.5, 2] → per-trade R behaves very differently in roll windows; suspicious.")
    lines.append("- Both passing → result is not roll-dominated (within the limits of continuous-symbol data).")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- No per-contract bars, so we can't compare continuous-symbol prints to true contract prints.")
    lines.append("- Roll-window definition is heuristic (5 days before, 1 day after the 3rd-Friday expiry).")
    lines.append("- A pass here does NOT prove zero roll distortion — it just rules out gross concentration.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    print("v22 roll-anomaly check — OB strict + Sweep reversed (filtered)")
    years = list(range(2017, 2027))
    windows = build_roll_windows(years)
    print(f"  built {len(windows)} roll windows across {years[0]}-{years[-1]}")

    results: list[dict] = []
    for family, files in FAMILY_FILES.items():
        df = load_family_trades(files)
        print(f"  {family}: {len(df)} trades loaded")
        results.append(analyze_family(family, df, windows))

    out_json = OUT_DIR / "v22_roll_anomaly_check.json"
    out_md = OUT_DIR / "v22_roll_anomaly_check.md"

    payload = {
        "generator": "v22_roll_anomaly_check",
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "thresholds": {
            "inflation_ratio_max": 2.0,
            "avg_r_ratio_min": 0.5,
            "avg_r_ratio_max": 2.0,
        },
        "n_windows": len(windows),
        "windows_sample": [(str(s), str(e)) for s, e in windows[:5]],
        "results": results,
        "overall_pass": all(r["passed"] for r in results),
    }
    out_json.write_text(json.dumps(payload, indent=2))
    out_md.write_text(write_md(results, windows), encoding="utf-8")

    print(f"  wrote: {out_json.relative_to(REPO_ROOT)}")
    print(f"  wrote: {out_md.relative_to(REPO_ROOT)}")
    print()
    for r in results:
        verdict = "PASS" if r["passed"] else "FAIL"
        print(
            f"  {r['family']:<32} {verdict}  "
            f"inflation={r['inflation_ratio']:>5}  "
            f"avg_R ratio={r['avg_r_ratio']}"
        )
    print()
    overall = "PASS" if payload["overall_pass"] else "FAIL"
    print(f"OVERALL: {overall}")
    return 0 if payload["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
