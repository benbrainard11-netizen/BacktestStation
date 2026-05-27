"""Validate v0 MBO features on the clean trading-day cache.

Uses the canonical trading-day reader (per docs/MBO_TRADING_DAY_CONTRACT.md):

    from app.data import read_mbo_trading_day

Each trading day is a clean 23-hour Globex slice (18:00 ET prev day →
17:00 ET trading-day date) with snapshot carry-in rows already removed.

Tests 3 of the 5 PLAN.md §2.I features that don't require maintained book
state (the other 2 — iceberg_refills, l2_to_l5_imbalance — need book
reconstruction and are deferred to Phase 2 build_features.py).

Features computed at each 1-minute boundary inside the trading day:
  1. cancel_rate_60s            — count(C) in last 60s / 60
  2. add_to_cancel_ratio_60s    — count(A) / count(C) in last 60s
  3. seconds_since_aggr_spike   — time since last 1-sec bin with aggressive
                                  trade volume > p95 of the day (proxy for
                                  mbo__seconds_since_side_sweep)

Approach (per symbol × trading_day):
  1. Read clean MBO via read_mbo_trading_day(symbol, trading_day)
  2. Bin events to 1-second resolution: n_adds, n_cancels, agg_trade_vol
  3. Rolling 60-second sum for cancel_rate and add_to_cancel
  4. Compute seconds-since-spike against day's p95 threshold
  5. Sample the 3 features at each 1-min boundary inside RTH (13:30-20:00 UTC)
  6. Join to forward |mid move| at +5min and +15min via 1m bars
  7. Decile lift analysis: bucket by feature decile, mean forward |move|

Output:
  out/mbo_v0_validation.parquet     — per-row feature + forward-move table
  report/v0_iter0_mbo_validation.md — decile tables per (feature × horizon × symbol)
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

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]

sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.data import read_mbo_trading_day  # noqa: E402
from app.data.reader import read_bars  # noqa: E402
from app.research.sessions import globex_day_for_trading_date  # noqa: E402

DEFAULT_SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]

# RTH = 13:30 - 20:00 UTC (09:30 - 16:00 ET, standard).
# Close enough for this validation — we're not training a model here, just
# looking at decile lift in forward mid moves.
RTH_START_UTC = dt.time(13, 30)
RTH_END_UTC = dt.time(20, 0)

TICK_SIZES = {
    "ES.c.0": 0.25,
    "NQ.c.0": 0.25,
    "YM.c.0": 1.0,
    "RTY.c.0": 0.10,
}


# ---------------------------------------------------------------------------
# Data loading (clean trading-day layer)
# ---------------------------------------------------------------------------


def load_mbo_for_trading_day(symbol: str, trading_day: dt.date) -> pd.DataFrame | None:
    """Load clean MBO for a single trading day. Returns None if missing."""
    try:
        df = read_mbo_trading_day(symbol=symbol, trading_day=trading_day)
    except FileNotFoundError:
        return None
    except ValueError as e:
        # weekend / invalid trading-day label
        if "Monday-Friday" in str(e):
            return None
        raise
    if df is None or len(df) == 0:
        return None
    return df


def load_bars_for_trading_day(symbol: str, trading_day: dt.date) -> pd.DataFrame | None:
    """Load 1m bars covering the trading day's full 23-hour Globex period."""
    period = globex_day_for_trading_date(trading_day)
    try:
        bars = read_bars(
            symbol=symbol,
            timeframe="1m",
            start=period.start_utc,
            end=period.end_utc,
        )
    except FileNotFoundError:
        return None
    if bars is None or len(bars) == 0:
        return None
    return bars


# ---------------------------------------------------------------------------
# Feature computation
# ---------------------------------------------------------------------------


def compute_v0_features(mbo: pd.DataFrame, symbol: str, trading_day: dt.date) -> pd.DataFrame:
    """Compute the 3 testable v0 MBO features at each 1-min RTH boundary."""

    mbo = mbo.copy()
    if "ts_event" not in mbo.columns:
        raise ValueError("MBO missing ts_event")
    mbo["ts_event"] = pd.to_datetime(mbo["ts_event"], utc=True)
    mbo["t1s"] = mbo["ts_event"].dt.floor("1s")

    # Counts per (t1s, action).
    grp = mbo.groupby(["t1s", "action"], sort=False).size().unstack(fill_value=0)
    for col in ["A", "C", "T", "M", "F"]:
        if col not in grp.columns:
            grp[col] = 0
    grp = grp[["A", "C", "T", "M", "F"]].sort_index()
    grp.columns = ["n_adds", "n_cancels", "n_trades", "n_modifies", "n_fills"]

    # Aggressive trade volume per 1s bin.
    trades = mbo[mbo["action"] == "T"]
    if len(trades) > 0:
        size_per_sec = trades.groupby("t1s")["size"].sum().astype("float64")
    else:
        size_per_sec = pd.Series(dtype="float64")
    grp["agg_trade_vol"] = size_per_sec.reindex(grp.index, fill_value=0.0)

    if len(grp) == 0:
        return pd.DataFrame()

    # Fill quiet seconds with zero so rolling sums are stable.
    start = grp.index.min()
    end = grp.index.max()
    full_idx = pd.date_range(start, end, freq="1s", tz="UTC")
    grp = grp.reindex(full_idx, fill_value=0)
    grp.index.name = "t1s"

    roll = grp.rolling("60s")
    grp["cancel_rate_60s"] = roll["n_cancels"].sum() / 60.0
    grp["adds_60s"] = roll["n_adds"].sum()
    grp["cancels_60s"] = roll["n_cancels"].sum()

    eps = 1.0
    grp["add_to_cancel_ratio_60s"] = grp["adds_60s"] / (grp["cancels_60s"] + eps)

    # Aggressive-volume spike threshold: 95th pct over non-zero values today.
    nonzero_vol = grp.loc[grp["agg_trade_vol"] > 0, "agg_trade_vol"]
    threshold = float(nonzero_vol.quantile(0.95)) if len(nonzero_vol) >= 30 else float("inf")
    grp["is_spike"] = (grp["agg_trade_vol"] >= threshold).astype("int8")

    grp["last_spike_t"] = pd.Series(grp.index.where(grp["is_spike"] == 1, pd.NaT), index=grp.index)
    grp["last_spike_t"] = grp["last_spike_t"].ffill()
    grp["seconds_since_aggr_spike"] = (
        (grp.index - grp["last_spike_t"]).dt.total_seconds().fillna(3600.0).clip(0, 3600)
    )

    # Sample at 1-min boundaries inside the RTH window.
    min_idx = pd.date_range(start.ceil("1min"), end.floor("1min"), freq="1min", tz="UTC")
    sample = grp.reindex(min_idx).copy()
    sample.index.name = "ts_decision"

    in_rth = (sample.index.time >= RTH_START_UTC) & (sample.index.time <= RTH_END_UTC)
    sample = sample.loc[in_rth].copy()

    keep = ["cancel_rate_60s", "add_to_cancel_ratio_60s", "seconds_since_aggr_spike"]
    sample = sample[keep].reset_index()
    sample["symbol"] = symbol
    sample["trading_day"] = trading_day.isoformat()
    return sample


# ---------------------------------------------------------------------------
# Forward-move join
# ---------------------------------------------------------------------------


def join_forward_moves(features: pd.DataFrame, bars: pd.DataFrame, tick_size: float) -> pd.DataFrame:
    bars = bars.copy().sort_values("ts_event").reset_index(drop=True)
    bars["mid_close"] = bars["close"]
    bars_aligned = bars.set_index("ts_event")[["mid_close"]]
    bars_aligned = bars_aligned[~bars_aligned.index.duplicated(keep="last")]
    bars_aligned = bars_aligned.sort_index()

    features = features.copy()
    features["ts_decision"] = pd.to_datetime(features["ts_decision"], utc=True)
    features = features.sort_values("ts_decision").reset_index(drop=True)

    features_idx = features["ts_decision"]
    mid_at_t = bars_aligned.reindex(features_idx, method="ffill")["mid_close"].to_numpy()

    out = features.copy()
    out["mid_at_t"] = mid_at_t
    for h in (5, 15):
        target_ts = features_idx + pd.Timedelta(minutes=h)
        fwd = bars_aligned.reindex(target_ts, method="bfill")["mid_close"].to_numpy()
        out[f"fwd_mid_{h}m"] = fwd
        out[f"abs_move_{h}m_ticks"] = np.abs(fwd - mid_at_t) / tick_size
    return out


# ---------------------------------------------------------------------------
# Decile analysis
# ---------------------------------------------------------------------------


def decile_table(df: pd.DataFrame, feature: str, target: str) -> pd.DataFrame:
    sub = df[[feature, target]].dropna()
    if len(sub) < 200:
        return pd.DataFrame()
    try:
        sub = sub.copy()
        sub["decile"] = pd.qcut(sub[feature], 10, labels=False, duplicates="drop")
    except (ValueError, IndexError):
        return pd.DataFrame()
    return sub.groupby("decile").agg(
        n=(target, "count"),
        mean_target=(target, "mean"),
        median_target=(target, "median"),
        feat_min=(feature, "min"),
        feat_max=(feature, "max"),
    ).reset_index()


def trading_day_range(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            yield cur
        cur += dt.timedelta(days=1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    p.add_argument("--start", default="2026-01-02", help="first trading day, inclusive")
    p.add_argument("--end", default="2026-05-21", help="last trading day, inclusive")
    p.add_argument("--out-dir", default=str(EXPERIMENT_DIR / "out"))
    p.add_argument("--report-path", default=str(EXPERIMENT_DIR / "report" / "v0_iter0_mbo_validation.md"))
    p.add_argument("--max-days-per-symbol", type=int, default=10_000, help="Cap for dry-run")
    args = p.parse_args(argv)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = Path(args.report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)

    all_rows: list[pd.DataFrame] = []
    skipped: list[tuple[str, str, str]] = []
    processed: dict[str, int] = {sym: 0 for sym in args.symbols}

    for sym in args.symbols:
        tick = TICK_SIZES.get(sym, 0.25)
        for td in trading_day_range(start, end):
            if processed[sym] >= args.max_days_per_symbol:
                break
            mbo = load_mbo_for_trading_day(sym, td)
            if mbo is None:
                skipped.append((sym, td.isoformat(), "no_mbo"))
                continue
            try:
                feats = compute_v0_features(mbo, sym, td)
            except Exception as e:
                skipped.append((sym, td.isoformat(), f"feature_error:{type(e).__name__}"))
                continue
            if feats.empty:
                skipped.append((sym, td.isoformat(), "empty_features"))
                continue

            bars = load_bars_for_trading_day(sym, td)
            if bars is None or len(bars) == 0:
                feats["mid_at_t"] = np.nan
                for h in (5, 15):
                    feats[f"fwd_mid_{h}m"] = np.nan
                    feats[f"abs_move_{h}m_ticks"] = np.nan
                all_rows.append(feats)
                processed[sym] += 1
                print(f"  {sym} {td}: features only (no bars)", flush=True)
                continue
            try:
                joined = join_forward_moves(feats, bars, tick_size=tick)
                all_rows.append(joined)
                processed[sym] += 1
                print(f"  {sym} {td}: {len(joined)} rows", flush=True)
            except Exception as e:
                skipped.append((sym, td.isoformat(), f"join_error:{type(e).__name__}"))
                continue

    if not all_rows:
        print("ERROR: no rows produced. Skipped sample:", skipped[:30])
        return 1

    df = pd.concat(all_rows, ignore_index=True)
    parquet_path = out_dir / "mbo_v0_validation.parquet"
    df.to_parquet(parquet_path, index=False)
    print(f"\nWrote {parquet_path.relative_to(REPO_ROOT)} ({len(df):,} rows)")

    features = ["cancel_rate_60s", "add_to_cancel_ratio_60s", "seconds_since_aggr_spike"]
    horizons = (5, 15)

    deciles: dict = {}
    per_symbol_deciles: dict = {}
    for feat in features:
        for h in horizons:
            target = f"abs_move_{h}m_ticks"
            tbl = decile_table(df, feat, target)
            if not tbl.empty:
                deciles[f"{feat}__abs_move_{h}m_ticks"] = tbl.to_dict(orient="records")
            for sym in args.symbols:
                sub = df[df["symbol"] == sym]
                tbl_s = decile_table(sub, feat, target)
                if not tbl_s.empty:
                    per_symbol_deciles.setdefault(sym, {})[f"{feat}__abs_move_{h}m_ticks"] = tbl_s.to_dict(orient="records")

    lines = [
        "# risk_conditioner_v0 — Iteration 0 MBO Feature Validation",
        "",
        f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        "",
        "Validates 3 of 5 v0 MBO features (PLAN.md §2.I) by computing them on the",
        "clean MBO trading-day cache (D:/data/clean/databento/mbo_trading_day/) per",
        "docs/MBO_TRADING_DAY_CONTRACT.md.",
        "",
        "Features tested:",
        "  1. `cancel_rate_60s` — count(C) in last 60s / 60",
        "  2. `add_to_cancel_ratio_60s` — count(A) / count(C) in last 60s",
        "  3. `seconds_since_aggr_spike` — seconds since last 1-sec bin with",
        "     aggressive trade vol > day's p95 (proxy for side_sweep)",
        "",
        f"Trading-day range: {args.start} → {args.end}  |  symbols: {', '.join(args.symbols)}",
        f"Total rows: {len(df):,}  |  skipped entries: {len(skipped)}",
        "",
        "---",
        "",
        "## Decile lift — pooled across all symbols",
        "",
    ]
    for feat in features:
        for h in horizons:
            key = f"{feat}__abs_move_{h}m_ticks"
            recs = deciles.get(key, [])
            if not recs:
                continue
            lines.append(f"### {feat} → mean |move| at +{h}m (ticks)")
            lines.append("")
            lines.append("| decile | n | feat range | mean | median |")
            lines.append("|---|---|---|---|---|")
            for r in recs:
                lines.append(
                    f"| {int(r['decile'])} | {int(r['n']):,} | "
                    f"[{r['feat_min']:.3f}, {r['feat_max']:.3f}] | "
                    f"{r['mean_target']:.2f} | {r['median_target']:.2f} |"
                )
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Per-symbol decile lift")
    lines.append("")
    for sym in args.symbols:
        sym_data = per_symbol_deciles.get(sym, {})
        if not sym_data:
            continue
        lines.append(f"### {sym}")
        lines.append("")
        for feat in features:
            for h in horizons:
                key = f"{feat}__abs_move_{h}m_ticks"
                recs = sym_data.get(key, [])
                if not recs:
                    continue
                lines.append(f"**{feat} → mean |move| at +{h}m (ticks)**")
                lines.append("")
                lines.append("| decile | n | mean | median |")
                lines.append("|---|---|---|---|")
                for r in recs:
                    lines.append(
                        f"| {int(r['decile'])} | {int(r['n']):,} | "
                        f"{r['mean_target']:.2f} | {r['median_target']:.2f} |"
                    )
                lines.append("")

    if skipped:
        lines.append("---")
        lines.append("")
        lines.append("## Skipped (symbol, trading_day, reason)")
        lines.append("")
        sk_df = pd.DataFrame(skipped, columns=["symbol", "trading_day", "reason"])
        by_reason = sk_df.groupby("reason").size().sort_values(ascending=False).to_dict()
        for reason, n in by_reason.items():
            lines.append(f"- {reason}: {n}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Interpretation guide")
    lines.append("")
    lines.append("- **Strong feature**: top decile mean / bottom decile mean ratio ≥ 1.5,")
    lines.append("  monotonic or near-monotonic trend, holds across symbols.")
    lines.append("- **Weak feature**: ratio < 1.2 or U-shape with no clear direction.")
    lines.append("- A feature strong pooled but weak per-symbol is suspicious (cross-symbol")
    lines.append("  heteroskedasticity, not per-symbol risk).")
    lines.append("- The 2 untested features (iceberg_refills, l2_to_l5_imbalance) need")
    lines.append("  book reconstruction — validated in Phase 2 (build_features.py).")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {report_path.relative_to(REPO_ROOT)}")

    summary_path = out_dir / "mbo_v0_validation_summary.json"
    summary = {
        "n_rows": int(len(df)),
        "n_symbols": int(df["symbol"].nunique()),
        "n_trading_days": int(df["trading_day"].nunique()),
        "skipped_count": len(skipped),
        "decile_keys": list(deciles.keys()),
        "data_source": "D:/data/clean/databento/mbo_trading_day/",
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {summary_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise
    except Exception:
        traceback.print_exc()
        raise
