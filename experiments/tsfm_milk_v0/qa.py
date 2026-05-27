"""Quality-assurance audit + tests for tsfm_milk_v0.

Modes:
  --audit    Resolve PLAN.md §9 ambiguities (dataset audit).
             Output: report/v0_iter0_dataset_audit.md + out/audit/*.parquet
             Read-only. Runs first.

  --tests    (Not yet implemented) QA tests against built dataset + predictions.

Audit sections (PLAN §9):
  1. Bar coverage gaps — per (symbol, year), days with < 200 RTH bars
  2. Tick size + slippage — (high-low)/tick distribution per symbol
  3. Cross-symbol time alignment — % minutes with all 4 symbols present
  4. Class balance at k=0.5σ — actual up/down/flat fractions per horizon
  5. Vol regime distribution per fold — σ_60 quantile histograms
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]

sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.data.reader import read_bars  # noqa: E402

SYMBOLS = ("ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0")

TICK_SIZES = {
    "ES.c.0": 0.25,
    "NQ.c.0": 0.25,
    "YM.c.0": 1.0,
    "RTY.c.0": 0.10,
}

# RTH window UTC. EDT vs EST shifts by 1 hour but for an audit, approximate is fine.
RTH_START_UTC = dt.time(13, 30)
RTH_END_UTC = dt.time(20, 0)


def _safe_repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


# ---------------------------------------------------------------------------
# Audit 1: Bar coverage gaps per (symbol, year)
# ---------------------------------------------------------------------------


def audit_bar_coverage(start: dt.date, end: dt.date, out_dir: Path) -> dict:
    findings: dict = {
        "section": "1. Bar coverage gaps",
        "per_symbol_year": [],
        "severe_gap_days": [],
        "summary": "",
        "manual_review_required": False,
    }

    rows = []
    severe_gaps = []
    for sym in SYMBOLS:
        # Process by year to bound memory
        for year in range(start.year, end.year + 1):
            ys = dt.date(year, 1, 1)
            ye = dt.date(year, 12, 31)
            ys = max(ys, start)
            ye = min(ye, end)
            if ys > ye:
                continue
            try:
                df = read_bars(symbol=sym, timeframe="1m", start=ys, end=ye + dt.timedelta(days=1))
            except Exception as e:
                rows.append({
                    "symbol": sym,
                    "year": year,
                    "n_days_with_bars": 0,
                    "n_days_lt200_rth_bars": 0,
                    "n_days_lt50_rth_bars": 0,
                    "median_rth_bars_per_day": 0,
                    "status": f"read_error:{type(e).__name__}",
                })
                continue
            if len(df) == 0:
                rows.append({
                    "symbol": sym,
                    "year": year,
                    "n_days_with_bars": 0,
                    "n_days_lt200_rth_bars": 0,
                    "n_days_lt50_rth_bars": 0,
                    "median_rth_bars_per_day": 0,
                    "status": "no_data",
                })
                continue
            df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
            df["date"] = df["ts_event"].dt.date
            in_rth = (df["ts_event"].dt.time >= RTH_START_UTC) & (df["ts_event"].dt.time <= RTH_END_UTC)
            rth = df.loc[in_rth, ["date"]].copy()
            per_day = rth.groupby("date").size()
            n_days = int(per_day.shape[0])
            lt200 = int((per_day < 200).sum())
            lt50 = int((per_day < 50).sum())
            for d, n in per_day[per_day < 50].items():
                severe_gaps.append({"symbol": sym, "date": str(d), "rth_bars": int(n)})
            rows.append({
                "symbol": sym,
                "year": year,
                "n_days_with_bars": n_days,
                "n_days_lt200_rth_bars": lt200,
                "n_days_lt50_rth_bars": lt50,
                "median_rth_bars_per_day": int(per_day.median()) if n_days else 0,
                "status": "ok",
            })
            print(f"  audit_1 {sym} {year}: {n_days} days, {lt200} <200 RTH bars, {lt50} <50", flush=True)

    findings["per_symbol_year"] = rows
    findings["severe_gap_days"] = severe_gaps[:200]  # cap for report
    findings["summary"] = (
        f"Inspected {len(rows)} (symbol, year) cells. "
        f"{sum(r['n_days_lt50_rth_bars'] for r in rows)} severely incomplete days flagged. "
        f"Expected ~390 RTH bars/day (Mon-Fri 13:30-20:00 UTC); anything <200 likely a holiday "
        f"or market disruption."
    )

    # Persist
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out_dir / "audit_bar_coverage.parquet", index=False)
    if severe_gaps:
        pd.DataFrame(severe_gaps).to_parquet(out_dir / "audit_severe_gaps.parquet", index=False)

    return findings


# ---------------------------------------------------------------------------
# Audit 2: Tick size + slippage calibration
# ---------------------------------------------------------------------------


def audit_tick_size(sample_dates: list[dt.date]) -> dict:
    findings: dict = {
        "section": "2. Tick size + slippage calibration",
        "per_symbol": [],
        "summary": "",
        "manual_review_required": False,
    }

    rows = []
    for sym in SYMBOLS:
        tick = TICK_SIZES[sym]
        all_hl = []
        for d in sample_dates:
            try:
                df = read_bars(symbol=sym, timeframe="1m", start=d, end=d + dt.timedelta(days=1))
            except Exception:
                continue
            if len(df) == 0:
                continue
            df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
            in_rth = (df["ts_event"].dt.time >= RTH_START_UTC) & (df["ts_event"].dt.time <= RTH_END_UTC)
            rth = df.loc[in_rth].copy()
            if len(rth) == 0:
                continue
            hl = (rth["high"] - rth["low"]).to_numpy()
            all_hl.append(hl)
        if not all_hl:
            rows.append({"symbol": sym, "status": "no_data", "tick_size": tick})
            continue
        hl = np.concatenate(all_hl)
        hl_ticks = hl / tick

        rows.append({
            "symbol": sym,
            "tick_size": tick,
            "n_bars_sampled": int(len(hl)),
            "hl_min": float(hl.min()),
            "hl_p25": float(np.percentile(hl, 25)),
            "hl_p50": float(np.percentile(hl, 50)),
            "hl_p75": float(np.percentile(hl, 75)),
            "hl_p95": float(np.percentile(hl, 95)),
            "hl_max": float(hl.max()),
            "hl_ticks_p50": float(np.percentile(hl_ticks, 50)),
            "hl_ticks_p95": float(np.percentile(hl_ticks, 95)),
            "status": "ok",
        })
        print(f"  audit_2 {sym}: hl_ticks p50={np.percentile(hl_ticks, 50):.1f}, p95={np.percentile(hl_ticks, 95):.1f}", flush=True)

    findings["per_symbol"] = rows
    findings["summary"] = (
        "Per-symbol (high - low) distribution in price points and ticks. Median tick range "
        "tells you typical 1m bar volatility. p95 tells you tail volatility. "
        "If median is < 2 ticks or > 100 ticks, tick_size config is likely wrong."
    )
    return findings


# ---------------------------------------------------------------------------
# Audit 3: Cross-symbol time alignment
# ---------------------------------------------------------------------------


def audit_cross_symbol_alignment(sample_months: list[tuple[int, int]]) -> dict:
    findings: dict = {
        "section": "3. Cross-symbol time alignment",
        "per_month": [],
        "summary": "",
        "manual_review_required": False,
    }

    rows = []
    for year, month in sample_months:
        start = dt.date(year, month, 1)
        if month == 12:
            end = dt.date(year + 1, 1, 1)
        else:
            end = dt.date(year, month + 1, 1)

        per_sym = {}
        for sym in SYMBOLS:
            try:
                df = read_bars(symbol=sym, timeframe="1m", start=start, end=end)
            except Exception:
                per_sym[sym] = None
                continue
            if len(df) == 0:
                per_sym[sym] = None
                continue
            df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
            in_rth = (df["ts_event"].dt.time >= RTH_START_UTC) & (df["ts_event"].dt.time <= RTH_END_UTC)
            per_sym[sym] = set(df.loc[in_rth, "ts_event"].dt.floor("1min").unique())

        if any(v is None for v in per_sym.values()):
            rows.append({
                "year": year,
                "month": month,
                "n_minutes_total": 0,
                "n_minutes_all_4": 0,
                "alignment_pct": 0.0,
                "status": "missing_symbol",
            })
            continue

        union = set.union(*per_sym.values())
        intersection = set.intersection(*per_sym.values())
        all4_pct = 100.0 * len(intersection) / len(union) if union else 0.0

        rows.append({
            "year": year,
            "month": month,
            "n_minutes_total": len(union),
            "n_minutes_all_4": len(intersection),
            "alignment_pct": round(all4_pct, 2),
            "n_es_only": sum(1 for m in union if m in per_sym["ES.c.0"] and m not in per_sym["NQ.c.0"]),
            "n_nq_only": sum(1 for m in union if m in per_sym["NQ.c.0"] and m not in per_sym["ES.c.0"]),
            "status": "ok",
        })
        print(f"  audit_3 {year}-{month:02d}: {all4_pct:.1f}% all-4 alignment ({len(intersection):,}/{len(union):,})", flush=True)

    findings["per_month"] = rows
    findings["summary"] = (
        "Fraction of RTH minutes where all 4 symbols (ES/NQ/YM/RTY) have a bar. "
        "Should be >99% in normal regimes. Lower = forward-fill needed or row drops."
    )
    return findings


# ---------------------------------------------------------------------------
# Audit 4: Class balance at k=0.5σ per horizon
# ---------------------------------------------------------------------------


def audit_class_balance(sample_months: list[tuple[int, int]], horizons: list[int], k: float) -> dict:
    findings: dict = {
        "section": "4. Class balance at k×σ thresholding",
        "k": k,
        "per_symbol_horizon": [],
        "summary": "",
        "manual_review_required": False,
    }

    rows = []
    for sym in SYMBOLS:
        all_returns: dict[int, list[float]] = {h: [] for h in horizons}
        all_sigmas: list[float] = []
        for year, month in sample_months:
            start = dt.date(year, month, 1)
            if month == 12:
                end = dt.date(year + 1, 1, 1)
            else:
                end = dt.date(year, month + 1, 1)
            try:
                df = read_bars(symbol=sym, timeframe="1m", start=start, end=end)
            except Exception:
                continue
            if len(df) == 0:
                continue
            df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
            df = df.sort_values("ts_event").reset_index(drop=True)
            df["log_return"] = np.log(df["close"] / df["close"].shift(1))
            df["sigma_60"] = df["log_return"].rolling(60).std()
            in_rth = (df["ts_event"].dt.time >= RTH_START_UTC) & (df["ts_event"].dt.time <= RTH_END_UTC)

            for h in horizons:
                df[f"fwd_logret_{h}"] = np.log(df["close"].shift(-h) / df["close"])

            sub = df.loc[in_rth].copy()
            for h in horizons:
                vals = sub[[f"fwd_logret_{h}", "sigma_60"]].dropna()
                # Skip when sigma is 0 (degenerate)
                vals = vals[vals["sigma_60"] > 0]
                all_returns[h].extend((vals[f"fwd_logret_{h}"] / vals["sigma_60"]).tolist())
            all_sigmas.extend(sub["sigma_60"].dropna().tolist())

        for h in horizons:
            arr = np.array(all_returns[h])
            if len(arr) == 0:
                rows.append({"symbol": sym, "horizon_min": h, "status": "no_data"})
                continue
            up = float((arr > k).mean())
            down = float((arr < -k).mean())
            flat = float(1.0 - up - down)
            rows.append({
                "symbol": sym,
                "horizon_min": h,
                "n_samples": int(len(arr)),
                "frac_up": round(up, 4),
                "frac_down": round(down, 4),
                "frac_flat": round(flat, 4),
                "ret_over_sigma_p5": float(np.percentile(arr, 5)),
                "ret_over_sigma_p95": float(np.percentile(arr, 95)),
                "status": "ok",
            })
        print(f"  audit_4 {sym}: balance computed across {len(horizons)} horizons", flush=True)

    findings["per_symbol_horizon"] = rows
    findings["summary"] = (
        f"With k={k}, the up/down/flat fractions should each be 25-40% for the model to "
        "learn well. Heavy flat (>60%) means k is too high for that horizon. "
        "Heavy directional (<10% flat) means k is too low."
    )
    return findings


# ---------------------------------------------------------------------------
# Audit 5: Vol regime distribution across folds
# ---------------------------------------------------------------------------


def audit_vol_regime(folds_cfg: dict) -> dict:
    findings: dict = {
        "section": "5. Vol regime distribution across folds",
        "per_fold_symbol": [],
        "summary": "",
        "manual_review_required": False,
    }

    # Pick test window of each fold to keep work bounded
    rows = []
    for fold in folds_cfg.get("folds", []):
        fid = fold["id"]
        test_start = dt.date.fromisoformat(str(fold["test_start"]))
        test_end = dt.date.fromisoformat(str(fold["test_end"]))
        for sym in SYMBOLS:
            try:
                df = read_bars(symbol=sym, timeframe="1m", start=test_start, end=test_end + dt.timedelta(days=1))
            except Exception:
                continue
            if len(df) == 0:
                continue
            df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
            df = df.sort_values("ts_event").reset_index(drop=True)
            df["log_return"] = np.log(df["close"] / df["close"].shift(1))
            df["sigma_60"] = df["log_return"].rolling(60).std()
            in_rth = (df["ts_event"].dt.time >= RTH_START_UTC) & (df["ts_event"].dt.time <= RTH_END_UTC)
            sub = df.loc[in_rth, "sigma_60"].dropna()
            if len(sub) == 0:
                continue
            # Convert to bps
            sigma_bps = sub * 1e4
            rows.append({
                "fold_id": fid,
                "symbol": sym,
                "n_samples": int(len(sub)),
                "sigma_bps_p10": float(np.percentile(sigma_bps, 10)),
                "sigma_bps_p50": float(np.percentile(sigma_bps, 50)),
                "sigma_bps_p90": float(np.percentile(sigma_bps, 90)),
                "sigma_bps_p99": float(np.percentile(sigma_bps, 99)),
            })
        print(f"  audit_5 fold {fid}: vol regime computed", flush=True)

    findings["per_fold_symbol"] = rows
    findings["summary"] = (
        "σ_60 percentiles per (fold, symbol) in bps (basis points per minute). "
        "If one fold has 3x the median vol of another, the model may struggle to "
        "generalize between regimes. Look for outlier folds."
    )
    return findings


# ---------------------------------------------------------------------------
# Markdown report renderer
# ---------------------------------------------------------------------------


def render_report(findings: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# tsfm_milk_v0 — Iteration 0 Dataset Audit",
        "",
        f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        "",
        "Resolves PLAN.md §9 ambiguities. Pre-requisite for build_dataset.py.",
        "",
        "---",
        "",
    ]

    for f in findings:
        lines.append(f"## {f['section']}")
        lines.append("")
        if f.get("manual_review_required"):
            lines.append("**Status:** MANUAL REVIEW REQUIRED")
        else:
            lines.append("**Status:** auto-resolved")
        lines.append("")
        if f.get("summary"):
            lines.append(f"**Summary:** {f['summary']}")
            lines.append("")

        if f["section"].startswith("1.") and f.get("per_symbol_year"):
            lines.append("**Per-(symbol, year) bar coverage:**")
            lines.append("")
            lines.append("| symbol | year | n_days | <200 RTH | <50 RTH | median RTH bars/day | status |")
            lines.append("|---|---|---|---|---|---|---|")
            for r in f["per_symbol_year"]:
                lines.append(
                    f"| {r['symbol']} | {r['year']} | {r['n_days_with_bars']} | "
                    f"{r['n_days_lt200_rth_bars']} | {r['n_days_lt50_rth_bars']} | "
                    f"{r['median_rth_bars_per_day']} | {r['status']} |"
                )
            lines.append("")
            if f.get("severe_gap_days"):
                lines.append(f"**Severely incomplete days (<50 RTH bars), first 30 of {len(f['severe_gap_days'])}:**")
                lines.append("")
                lines.append("| symbol | date | rth_bars |")
                lines.append("|---|---|---|")
                for r in f["severe_gap_days"][:30]:
                    lines.append(f"| {r['symbol']} | {r['date']} | {r['rth_bars']} |")
                lines.append("")

        if f["section"].startswith("2.") and f.get("per_symbol"):
            lines.append("**Per-symbol (high - low) distribution:**")
            lines.append("")
            lines.append("| symbol | tick_size | n_bars | hl_p50 (pts) | hl_p95 (pts) | hl_p50 (ticks) | hl_p95 (ticks) |")
            lines.append("|---|---|---|---|---|---|---|")
            for r in f["per_symbol"]:
                if r.get("status") != "ok":
                    lines.append(f"| {r['symbol']} | {r['tick_size']} | — | — | — | — | {r.get('status')} |")
                    continue
                lines.append(
                    f"| {r['symbol']} | {r['tick_size']} | {r['n_bars_sampled']:,} | "
                    f"{r['hl_p50']:.3f} | {r['hl_p95']:.3f} | "
                    f"{r['hl_ticks_p50']:.1f} | {r['hl_ticks_p95']:.1f} |"
                )
            lines.append("")

        if f["section"].startswith("3.") and f.get("per_month"):
            lines.append("**Per-month cross-symbol alignment (% of RTH minutes with all 4 symbols):**")
            lines.append("")
            lines.append("| year | month | total RTH minutes | all 4 present | alignment % |")
            lines.append("|---|---|---|---|---|")
            for r in f["per_month"]:
                if r.get("status") != "ok":
                    lines.append(f"| {r['year']} | {r['month']:02d} | — | — | {r.get('status')} |")
                    continue
                lines.append(
                    f"| {r['year']} | {r['month']:02d} | {r['n_minutes_total']:,} | "
                    f"{r['n_minutes_all_4']:,} | {r['alignment_pct']:.2f}% |"
                )
            lines.append("")

        if f["section"].startswith("4.") and f.get("per_symbol_horizon"):
            lines.append(f"**Class balance with k = {f.get('k', 0.5)}:**")
            lines.append("")
            lines.append("| symbol | horizon (min) | n | flat | up | down |")
            lines.append("|---|---|---|---|---|---|")
            for r in f["per_symbol_horizon"]:
                if r.get("status") != "ok":
                    lines.append(f"| {r['symbol']} | {r['horizon_min']} | — | — | — | — |")
                    continue
                lines.append(
                    f"| {r['symbol']} | {r['horizon_min']} | {r['n_samples']:,} | "
                    f"{r['frac_flat']:.2%} | {r['frac_up']:.2%} | {r['frac_down']:.2%} |"
                )
            lines.append("")

        if f["section"].startswith("5.") and f.get("per_fold_symbol"):
            lines.append("**σ_60 (bps per minute) percentiles per (fold, symbol):**")
            lines.append("")
            lines.append("| fold | symbol | n | σ p10 (bps) | σ p50 (bps) | σ p90 (bps) | σ p99 (bps) |")
            lines.append("|---|---|---|---|---|---|---|")
            for r in f["per_fold_symbol"]:
                lines.append(
                    f"| {r['fold_id']} | {r['symbol']} | {r['n_samples']:,} | "
                    f"{r['sigma_bps_p10']:.2f} | {r['sigma_bps_p50']:.2f} | "
                    f"{r['sigma_bps_p90']:.2f} | {r['sigma_bps_p99']:.2f} |"
                )
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append("## Decisions for build_dataset.py")
    lines.append("")
    lines.append("Based on this audit, populate the following in subsequent commits:")
    lines.append("")
    lines.append("1. **Bad-day exclusion list** (audit 1): exclude any (symbol, date) with < 200 RTH bars from anchor sampling, OR forward-fill, OR drop the symbol's row only.")
    lines.append("2. **Slippage config** (audit 2): if hl_ticks_p50 is < 4 or > 40 for any symbol, recheck tick_size. Otherwise default to 1-tick slippage per side.")
    lines.append("3. **Cross-symbol alignment rule** (audit 3): if alignment is < 99%, decide between (a) drop misaligned anchor rows, (b) forward-fill the laggard symbol's last bar.")
    lines.append("4. **Per-horizon k tuning** (audit 4): if a horizon shows < 15% in any direction at k=0.5, consider lowering k for that horizon.")
    lines.append("5. **Vol-stratified evaluation** (audit 5): when reporting fold metrics, also report broken down by σ regime (low/med/high) — folds with very different vol are not directly comparable.")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_audit(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir).resolve()
    report_path = Path(args.report_path).resolve()
    audit_out = out_dir / "audit"
    audit_out.mkdir(parents=True, exist_ok=True)

    folds_cfg = yaml.safe_load((EXPERIMENT_DIR / "walk_forward.yaml").read_text(encoding="utf-8"))
    labels_cfg = yaml.safe_load((EXPERIMENT_DIR / "labels_and_horizons.yaml").read_text(encoding="utf-8"))

    universe_start = dt.date.fromisoformat(str(folds_cfg["folds"][0]["train_start"]))
    universe_end = dt.date.fromisoformat(str(folds_cfg["final_holdout"]["holdout_end"]))

    horizons = list(labels_cfg["horizons_minutes"])
    k = float(labels_cfg["thresholding"]["k"])

    # Sample months — one per quarter spanning the universe (cuts audit work to ~10% of full data).
    sample_months: list[tuple[int, int]] = []
    for year in range(universe_start.year, universe_end.year + 1):
        for month in (3, 6, 9, 12):
            if dt.date(year, month, 1) < universe_start:
                continue
            if dt.date(year, month, 1) > universe_end:
                continue
            sample_months.append((year, month))

    # Sample dates for tick-size audit — first trading day of each sample month.
    sample_dates = [dt.date(y, m, 5) for (y, m) in sample_months]

    findings: list[dict] = []

    print("\n=== AUDIT 1: bar coverage ===")
    try:
        findings.append(audit_bar_coverage(universe_start, universe_end, audit_out))
    except Exception as e:
        findings.append({"section": "1. Bar coverage gaps", "summary": f"audit failed: {e}\n{traceback.format_exc()[:500]}", "manual_review_required": True})

    print("\n=== AUDIT 2: tick size ===")
    try:
        findings.append(audit_tick_size(sample_dates))
    except Exception as e:
        findings.append({"section": "2. Tick size + slippage", "summary": f"audit failed: {e}", "manual_review_required": True})

    print("\n=== AUDIT 3: cross-symbol alignment ===")
    try:
        # Reduce to one month per year for this audit (it's slow)
        align_months = [(y, 6) for y in range(universe_start.year, universe_end.year + 1)]
        findings.append(audit_cross_symbol_alignment(align_months))
    except Exception as e:
        findings.append({"section": "3. Cross-symbol time alignment", "summary": f"audit failed: {e}", "manual_review_required": True})

    print("\n=== AUDIT 4: class balance ===")
    try:
        # Sample a handful of representative months to keep runtime bounded.
        class_months = [
            (2019, 6),
            (2020, 3),   # COVID
            (2021, 11),  # post-COVID
            (2022, 6),   # bear
            (2023, 12),
            (2025, 1),
            (2025, 12),
        ]
        class_months = [m for m in class_months if dt.date(m[0], m[1], 1) >= universe_start and dt.date(m[0], m[1], 1) <= universe_end]
        findings.append(audit_class_balance(class_months, horizons, k))
    except Exception as e:
        findings.append({"section": "4. Class balance", "summary": f"audit failed: {e}", "manual_review_required": True})

    print("\n=== AUDIT 5: vol regime per fold ===")
    try:
        findings.append(audit_vol_regime(folds_cfg))
    except Exception as e:
        findings.append({"section": "5. Vol regime distribution", "summary": f"audit failed: {e}", "manual_review_required": True})

    render_report(findings, report_path)
    print(f"\nWrote {report_path.relative_to(REPO_ROOT)}")

    json_path = audit_out / "findings.json"
    json_path.write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {json_path.relative_to(REPO_ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--audit", action="store_true", help="Run PLAN §9 dataset ambiguity audit")
    p.add_argument("--tests", action="store_true", help="(Not implemented yet)")
    p.add_argument("--out-dir", default=str(EXPERIMENT_DIR / "out"))
    p.add_argument("--report-path", default=str(EXPERIMENT_DIR / "report" / "v0_iter0_dataset_audit.md"))
    args = p.parse_args(argv)

    if args.audit:
        return run_audit(args)
    if args.tests:
        print("--tests not implemented yet.")
        return 2
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
