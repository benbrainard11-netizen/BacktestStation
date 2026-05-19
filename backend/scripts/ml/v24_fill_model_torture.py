"""Paper-trade Gate 3 — fill-model torture (volume gating).

QUESTION: was the bar containing each entry/exit liquid enough to
absorb a 1-contract market order? If a large share of edge comes from
sub-N-contract-per-minute bars, fills are at risk live.

CONTEXT: v18 already did the TBBO honest-fill comparison (89% R
retention against actual trade tape). v18 answered the "did the
target/stop print actually happen?" question. This script tests the
COMPLEMENTARY question: even if it printed, was there enough volume
to fill at our assumed size?

Note on out-of-range (OOR): a previous draft of this gate tested
whether `entry_price`/`exit_price` fell inside the bar's [low, high].
That test is mis-specified for v8a's slippage model: 2-tick adverse
slippage on stops/entries/time-exits intentionally places the recorded
fill price 2 ticks outside the bar's OHLC range (this is the simulator
being pessimistic, not wrong). OOR % is reported for transparency but
does not gate.

METHOD:
  - Load 1m bars for NQ.c.0 + ES.c.0 covering 2018-2019 + 2026 YTD.
  - For each trade in OB strict + Sweep reversed (both holdouts):
      * Locate the bar at entry_ts (floor to minute).
      * Locate the bar at exit_ts (floor to minute).
      * Record entry-bar + exit-bar volume.
  - Drop trades where entry-bar volume < threshold; compute cum_R
    retention.

PASS THRESHOLD (pre-registered):
  - cum_R retention after volume gate 10 contracts/min: >= 90%
  - cum_R retention after volume gate 25 contracts/min: >= 80%
  - OOR % reported as informational only.

OUTPUT:
  experiments/paper_trade_gates_2026_05_17/results/v24_fill_model_torture.json
  experiments/paper_trade_gates_2026_05_17/results/v24_fill_model_torture.md
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
V20_DIR = REPO_ROOT / "experiments" / "locked_walkforward_2026_05_17" / "results"
OUT_DIR = REPO_ROOT / "experiments" / "paper_trade_gates_2026_05_17" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BARS_ROOT = Path("D:/data/processed/bars/timeframe=1m")

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

VOL_THRESHOLDS = (10, 25, 100)


def load_bars_for_dates(symbol: str, dates: set[pd.Timestamp]) -> pd.DataFrame:
    """Load only the 1m bar files we need for the given (symbol, dates).

    `dates` is a set of pd.Timestamp at day precision. Files live at
    `<BARS_ROOT>/symbol=<symbol>/date=YYYY-MM-DD/part-000.parquet`.
    """
    frames = []
    missing: list[str] = []
    for d in sorted(dates):
        if isinstance(d, pd.Timestamp):
            date_str = d.strftime("%Y-%m-%d")
        else:
            date_str = pd.Timestamp(d).strftime("%Y-%m-%d")
        path = BARS_ROOT / f"symbol={symbol}" / f"date={date_str}" / "part-000.parquet"
        if not path.exists():
            missing.append(date_str)
            continue
        bars = pd.read_parquet(path)
        bars["ts_event"] = pd.to_datetime(bars["ts_event"], utc=True)
        frames.append(bars)
    if not frames:
        return pd.DataFrame(), missing
    return pd.concat(frames, ignore_index=True), missing


def load_family_trades(filenames: list[str]) -> pd.DataFrame:
    frames = []
    for fn in filenames:
        df = pd.read_csv(V20_DIR / fn)
        df = df.dropna(subset=["pnl_r", "entry_ts", "exit_ts"]).copy()
        df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True)
        df["exit_ts"] = pd.to_datetime(df["exit_ts"], utc=True)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def attach_bar_state(
    trades: pd.DataFrame, bars: pd.DataFrame, *, ts_col: str, prefix: str
) -> pd.DataFrame:
    """For each trade, find the 1m bar whose ts_event == floor(trades[ts_col]).

    Adds columns: <prefix>_low, <prefix>_high, <prefix>_volume,
                  <prefix>_bar_found
    """
    if bars.empty:
        trades[f"{prefix}_low"] = float("nan")
        trades[f"{prefix}_high"] = float("nan")
        trades[f"{prefix}_volume"] = float("nan")
        trades[f"{prefix}_bar_found"] = False
        return trades

    trades = trades.copy()
    floored = trades[ts_col].dt.floor("1min")
    trades["__lookup_key"] = trades["symbol"] + "|" + floored.astype(str)

    bars = bars.copy()
    bars["__lookup_key"] = bars["symbol"] + "|" + bars["ts_event"].astype(str)
    bars_idx = bars.set_index("__lookup_key")[["low", "high", "volume"]]

    merged = trades["__lookup_key"].map(
        lambda k: bars_idx.loc[k] if k in bars_idx.index else None
    )

    trades[f"{prefix}_low"] = merged.map(lambda r: r["low"] if r is not None else float("nan"))
    trades[f"{prefix}_high"] = merged.map(lambda r: r["high"] if r is not None else float("nan"))
    trades[f"{prefix}_volume"] = merged.map(lambda r: r["volume"] if r is not None else float("nan"))
    trades[f"{prefix}_bar_found"] = trades[f"{prefix}_low"].notna()
    trades.drop(columns=["__lookup_key"], inplace=True)
    return trades


def analyze_family(name: str, trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"family": name, "passed": False, "error": "no trades"}

    n_total = len(trades)
    cum_r_total = float(trades["pnl_r"].sum())

    # Need bars for the union of (symbol, date) across entry+exit
    needed: dict[str, set[pd.Timestamp]] = {}
    for sym in trades["symbol"].unique():
        sub = trades[trades["symbol"] == sym]
        dates = set(sub["entry_ts"].dt.floor("D")) | set(sub["exit_ts"].dt.floor("D"))
        needed[sym] = dates

    bars_by_symbol: dict[str, pd.DataFrame] = {}
    missing_dates: dict[str, list[str]] = {}
    for sym, dates in needed.items():
        bars, missing = load_bars_for_dates(sym, dates)
        bars_by_symbol[sym] = bars
        missing_dates[sym] = missing
        print(f"    [{name} | {sym}] loaded {len(bars):,} bar rows over "
              f"{len(dates)} dates ({len(missing)} missing)")

    all_bars = pd.concat(bars_by_symbol.values(), ignore_index=True)
    trades = attach_bar_state(trades, all_bars, ts_col="entry_ts", prefix="entry_bar")
    trades = attach_bar_state(trades, all_bars, ts_col="exit_ts", prefix="exit_bar")

    # (a) range checks
    entry_out_of_range = (
        trades["entry_bar_bar_found"]
        & (
            (trades["entry_price"] < trades["entry_bar_low"])
            | (trades["entry_price"] > trades["entry_bar_high"])
        )
    )
    exit_out_of_range = (
        trades["exit_bar_bar_found"]
        & (
            (trades["exit_price"] < trades["exit_bar_low"])
            | (trades["exit_price"] > trades["exit_bar_high"])
        )
    )
    any_oor = entry_out_of_range | exit_out_of_range
    pct_oor = float(any_oor.mean()) * 100

    # (b) volume gating: cum_R retention when dropping trades where
    # entry-bar volume < threshold
    by_threshold = {}
    for thr in VOL_THRESHOLDS:
        ok = trades["entry_bar_volume"] >= thr
        kept = trades[ok]
        n_kept = int(len(kept))
        cum_r_kept = float(kept["pnl_r"].sum())
        retention = (cum_r_kept / cum_r_total) if cum_r_total != 0 else 0.0
        by_threshold[f"vol_gate_ge_{thr}"] = {
            "threshold_contracts": thr,
            "n_trades_kept": n_kept,
            "n_trades_dropped": int(n_total - n_kept),
            "cum_r_kept": round(cum_r_kept, 2),
            "cum_r_retention": round(retention, 4),
        }

    # Pass checks (volume retention only; OOR is informational due to
    # 2-tick adverse slippage being intentionally outside the bar range).
    ret_25_ok = by_threshold["vol_gate_ge_25"]["cum_r_retention"] >= 0.80
    ret_10_ok = by_threshold["vol_gate_ge_10"]["cum_r_retention"] >= 0.90
    passed = bool(ret_25_ok and ret_10_ok)

    return {
        "family": name,
        "n_trades": n_total,
        "cum_r_total": round(cum_r_total, 2),
        "n_bars_with_data": int(trades["entry_bar_bar_found"].sum()),
        "pct_out_of_range_INFORMATIONAL": round(pct_oor, 4),
        "missing_bar_dates": {k: v[:10] for k, v in missing_dates.items() if v},
        "by_threshold": by_threshold,
        "checks": {
            "retention_ge_80pct_at_vol25": bool(ret_25_ok),
            "retention_ge_90pct_at_vol10": bool(ret_10_ok),
        },
        "passed": passed,
    }


def write_md(results: list[dict]) -> str:
    lines: list[str] = []
    lines.append("# v24 — Fill-Model Torture (Paper-Trade Gate 3)")
    lines.append("")
    lines.append(f"_Generated {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")}Z_")
    lines.append("")
    lines.append(
        "Tests OHLC-level range consistency + volume credibility of v20 fills "
        "for OB strict + Sweep reversed (filtered). Complements v18's TBBO "
        "honest-fill check."
    )
    lines.append("")
    overall = all(r.get("passed", False) for r in results)
    lines.append(f"## Verdict: {'PASS' if overall else 'FAIL'}")
    lines.append("")
    for r in results:
        lines.append(f"### {r['family']}")
        lines.append("")
        if "error" in r:
            lines.append(f"- ERROR: {r['error']}")
            lines.append("")
            continue
        lines.append(f"- Total trades: {r['n_trades']:,}")
        lines.append(f"- Total cum_R: {r['cum_r_total']}")
        lines.append(f"- Entry-bar matched: {r['n_bars_with_data']:,}")
        lines.append(f"- % trades with entry or exit price OUTSIDE bar [low, high] (INFORMATIONAL — see header note): {r['pct_out_of_range_INFORMATIONAL']}%")
        if r.get("missing_bar_dates"):
            lines.append(f"- Missing bar dates: {r['missing_bar_dates']}")
        lines.append("")
        lines.append("| Volume gate | Trades kept | Trades dropped | cum_R kept | Retention |")
        lines.append("|---|---:|---:|---:|---:|")
        for key, b in r["by_threshold"].items():
            lines.append(
                f"| {b['threshold_contracts']}+ contracts/min | "
                f"{b['n_trades_kept']:,} | {b['n_trades_dropped']:,} | "
                f"{b['cum_r_kept']:.2f} | {b['cum_r_retention']*100:.1f}% |"
            )
        lines.append("")
        c = r["checks"]
        lines.append(f"- ≥ 80% retention at vol-gate 25: **{c['retention_ge_80pct_at_vol25']}**")
        lines.append(f"- ≥ 90% retention at vol-gate 10: **{c['retention_ge_90pct_at_vol10']}**")
        lines.append(f"- **{'PASS' if r['passed'] else 'FAIL'}**")
        lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- Volume-gate retention measures how much edge is preserved if we filter out trades whose entry minute had too little real volume to absorb our order. 1 contract is small, so even thin bars should hold up.")
    lines.append("- Vol-25 retention < 80% means an uncomfortable share of edge comes from sub-25-contract-per-minute bars — possibly Asia session or low-liquidity holiday hours.")
    lines.append("- The OOR % is informational only: 2-tick adverse slippage on stops/entries/time-exits is intentionally OUTSIDE the bar range (the simulator being pessimistic). A high OOR % just means slippage is being applied; it does NOT indicate fill dishonesty.")
    lines.append("- v18 already verified honest-fill against actual trade tape at 89% R retention (TBBO replay). This gate adds the orthogonal volume question.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    print("v24 fill-model torture — OHLC range + volume gating")
    results: list[dict] = []
    for family, files in FAMILY_FILES.items():
        trades = load_family_trades(files)
        print(f"  {family}: {len(trades)} trades")
        results.append(analyze_family(family, trades))

    payload = {
        "generator": "v24_fill_model_torture",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "volume_thresholds": list(VOL_THRESHOLDS),
        "results": results,
        "overall_pass": all(r.get("passed", False) for r in results),
    }
    out_json = OUT_DIR / "v24_fill_model_torture.json"
    out_md = OUT_DIR / "v24_fill_model_torture.md"
    out_json.write_text(json.dumps(payload, indent=2))
    out_md.write_text(write_md(results), encoding="utf-8")

    print()
    for r in results:
        if "error" in r:
            print(f"  {r['family']:<32} ERROR")
            continue
        verdict = "PASS" if r["passed"] else "FAIL"
        ret10 = r["by_threshold"]["vol_gate_ge_10"]["cum_r_retention"] * 100
        ret25 = r["by_threshold"]["vol_gate_ge_25"]["cum_r_retention"] * 100
        ret100 = r["by_threshold"]["vol_gate_ge_100"]["cum_r_retention"] * 100
        oor_info = r["pct_out_of_range_INFORMATIONAL"]
        print(
            f"  {r['family']:<32} {verdict}  ret(10/25/100)={ret10:.1f}/{ret25:.1f}/{ret100:.1f}%  "
            f"oor_info={oor_info}%"
        )
    overall = "PASS" if payload["overall_pass"] else "FAIL"
    print(f"\nOVERALL: {overall}")
    return 0 if payload["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
