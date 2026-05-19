"""V30 — Per-feature × per-asset behavior profile + asset-class roll-up.

For every (feature_name × primary_symbol) pair with events on disk,
compute a behavior profile from the events + outcomes JSON. Then
aggregate per asset class.

Goal: answer "does this detector work on this asset?" and
       "which features work on each asset class?" at a glance.

Metrics per (feature, symbol):
  count      : total events
  per_year   : events per calendar year
  pct_up     : % events with thesis_direction == "up"
  fwd10_mfe  : mean MFE (in thesis direction) over forward 10 candles, pts
  fwd10_mae  : mean MAE (against thesis) over forward 10 candles, pts
  fwd10_ratio: mean MFE / mean MAE  (>1 favorable)
  fwd10_hit  : % events where last_close_vs_reference_pts > 0
  fwd50_*    : same at 50-candle horizon
  hour_mode  : most common UTC hour
  spread     : coefficient of variation across years (consistency)

Per asset class:
  avg / std of each metric across symbols in the class
  highlights: best 5 (feature, symbol) by fwd10_ratio per class

OUTPUT:
  experiments/feature_profiles_<run_id>/
    per_feature_per_symbol.csv
    per_asset_class.csv
    SUMMARY.md
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Asset-class taxonomy
ASSET_CLASS = {
    "ES.c.0": "index", "NQ.c.0": "index", "YM.c.0": "index", "RTY.c.0": "index",
    "6A.c.0": "fx", "6B.c.0": "fx", "6C.c.0": "fx", "6E.c.0": "fx",
    "6J.c.0": "fx", "6N.c.0": "fx", "6S.c.0": "fx",
    "CL.c.0": "energy", "BZ.c.0": "energy", "HO.c.0": "energy",
    "RB.c.0": "energy", "NG.c.0": "energy",
    "ZC.c.0": "grain", "ZS.c.0": "grain", "ZW.c.0": "grain",
    "ZB.c.0": "bond", "ZF.c.0": "bond", "ZN.c.0": "bond", "ZT.c.0": "bond",
}


def _parse_outcomes(raw) -> dict | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except (ValueError, TypeError):
            return None
    return None


# Detectors whose anchor is by-definition the price extreme.
# For these, MAE-against-thesis is structurally near-zero (44% near-zero
# for swing_pivot vs 1.3% for order_block) and the MFE/MAE ratio is
# inflated by construction, NOT by predictive edge. Flag accordingly.
PIVOT_ANCHORED_FEATURES = frozenset({"swing_pivot", "equal_levels"})


def _metric_reliability(feature: str) -> str:
    """Tag the feature's MFE/MAE-ratio interpretability."""
    if feature in PIVOT_ANCHORED_FEATURES:
        return "pivot_anchored__mae_inflated"  # ratio structurally too high
    return "reactive__comparable"


def _build_one_profile(events: pd.DataFrame, feature: str, symbol: str) -> dict:
    """Compute one row of the profile for a (feature, symbol)."""
    n = len(events)
    if n == 0:
        return {}

    events = events.copy()
    events["bar_end_utc"] = pd.to_datetime(events["bar_end_utc"], utc=True)
    years = sorted(events["bar_end_utc"].dt.year.unique())
    n_years = len(years)
    per_year = n / max(n_years, 1)
    hour_mode = int(events["bar_end_utc"].dt.hour.mode()[0])

    # Parse outcomes once
    parsed = events["outcomes"].apply(_parse_outcomes)
    has_out = parsed.notna()
    n_with_outcomes = int(has_out.sum())

    if n_with_outcomes == 0:
        return {
            "feature": feature, "symbol": symbol,
            "asset_class": ASSET_CLASS.get(symbol, "other"),
            "metric_reliability": _metric_reliability(feature),
            "count": n, "n_years": n_years, "per_year": round(per_year, 1),
            "n_with_outcomes": 0,
            "hour_mode_utc": hour_mode,
        }

    # Extract metrics from outcomes
    thesis_up = parsed.apply(lambda d: d.get("thesis_direction") == "up" if d else False)
    pct_up = float(thesis_up.sum() / n_with_outcomes)

    def _extract(d, key, sub):
        if not d:
            return None
        block = d.get(key)
        if not isinstance(block, dict):
            return None
        return block.get(sub)

    fwd10_mfe = parsed.apply(lambda d: _extract(d, "forward_10_candles", "mfe_pts_in_thesis"))
    fwd10_mae = parsed.apply(lambda d: _extract(d, "forward_10_candles", "mae_pts_against_thesis"))
    fwd10_last = parsed.apply(lambda d: _extract(d, "forward_10_candles", "last_close_vs_reference_pts"))
    fwd50_mfe = parsed.apply(lambda d: _extract(d, "forward_50_candles", "mfe_pts_in_thesis"))
    fwd50_mae = parsed.apply(lambda d: _extract(d, "forward_50_candles", "mae_pts_against_thesis"))
    fwd50_last = parsed.apply(lambda d: _extract(d, "forward_50_candles", "last_close_vs_reference_pts"))

    # Fallback for detectors whose outcomes JSON lacks
    # `last_close_vs_reference_pts` (e.g., swing_pivot): derive it from
    # last_close - reference_close. We have both fields in forward_*_candles.
    def _derive_last_minus_ref(d, horizon_key):
        block = d.get(horizon_key) if isinstance(d, dict) else None
        if not isinstance(block, dict):
            return None
        lc = block.get("last_close")
        rc = block.get("reference_close")
        if lc is None or rc is None:
            return None
        try:
            return float(lc) - float(rc)
        except (TypeError, ValueError):
            return None

    if fwd10_last.notna().mean() < 0.5:
        # Mostly missing; derive
        fwd10_last = parsed.apply(lambda d: _derive_last_minus_ref(d, "forward_10_candles"))
    if fwd50_last.notna().mean() < 0.5:
        fwd50_last = parsed.apply(lambda d: _derive_last_minus_ref(d, "forward_50_candles"))

    # NOTE on direction interpretation: forward_*_candles.last_close_vs_reference_pts
    # is signed in PRICE direction, not thesis direction. We need to multiply by
    # thesis sign to get "did the thesis play out?" Up thesis = +1, Down = -1.
    thesis_sign = thesis_up.map({True: 1.0, False: -1.0})

    fwd10_last_thesis = fwd10_last * thesis_sign
    fwd50_last_thesis = fwd50_last * thesis_sign

    def _safe_mean(s):
        s = pd.to_numeric(s, errors="coerce").dropna()
        return float(s.mean()) if len(s) else None

    def _safe_hit(s):
        s = pd.to_numeric(s, errors="coerce").dropna()
        return float((s > 0).mean()) if len(s) else None

    fwd10_mfe_mean = _safe_mean(fwd10_mfe)
    fwd10_mae_mean = _safe_mean(fwd10_mae)
    fwd10_ratio = (
        fwd10_mfe_mean / fwd10_mae_mean if fwd10_mae_mean and fwd10_mae_mean > 0 else None
    )
    fwd50_mfe_mean = _safe_mean(fwd50_mfe)
    fwd50_mae_mean = _safe_mean(fwd50_mae)
    fwd50_ratio = (
        fwd50_mfe_mean / fwd50_mae_mean if fwd50_mae_mean and fwd50_mae_mean > 0 else None
    )

    return {
        "feature": feature,
        "symbol": symbol,
        "asset_class": ASSET_CLASS.get(symbol, "other"),
        "metric_reliability": _metric_reliability(feature),
        "count": n,
        "n_years": n_years,
        "per_year": round(per_year, 1),
        "n_with_outcomes": n_with_outcomes,
        "pct_thesis_up": round(pct_up, 3),
        "hour_mode_utc": hour_mode,
        "fwd10_mfe_pts_mean": round(fwd10_mfe_mean, 4) if fwd10_mfe_mean is not None else None,
        "fwd10_mae_pts_mean": round(fwd10_mae_mean, 4) if fwd10_mae_mean is not None else None,
        "fwd10_ratio_mfe_mae": round(fwd10_ratio, 3) if fwd10_ratio is not None else None,
        "fwd10_last_close_thesis_mean": round(_safe_mean(fwd10_last_thesis), 4) if _safe_mean(fwd10_last_thesis) is not None else None,
        "fwd10_last_close_thesis_hitrate": round(_safe_hit(fwd10_last_thesis), 3) if _safe_hit(fwd10_last_thesis) is not None else None,
        "fwd50_mfe_pts_mean": round(fwd50_mfe_mean, 4) if fwd50_mfe_mean is not None else None,
        "fwd50_mae_pts_mean": round(fwd50_mae_mean, 4) if fwd50_mae_mean is not None else None,
        "fwd50_ratio_mfe_mae": round(fwd50_ratio, 3) if fwd50_ratio is not None else None,
        "fwd50_last_close_thesis_mean": round(_safe_mean(fwd50_last_thesis), 4) if _safe_mean(fwd50_last_thesis) is not None else None,
        "fwd50_last_close_thesis_hitrate": round(_safe_hit(fwd50_last_thesis), 3) if _safe_hit(fwd50_last_thesis) is not None else None,
    }


def build_profiles(repo_root: Path, features: list[str]) -> pd.DataFrame:
    """For each feature, scan ALL its event parquets, group by symbol,
    compute profile."""
    rows: list[dict] = []
    events_root = repo_root / "data" / "research_events"

    for feature in features:
        feature_dir = events_root / f"feature_name={feature}"
        if not feature_dir.exists():
            print(f"  {feature}: no events directory, skipping")
            continue

        all_files = sorted(feature_dir.glob("event_year=*/*.parquet"))
        if not all_files:
            print(f"  {feature}: no parquets")
            continue

        print(f"  {feature}: reading {len(all_files)} files...", end=" ", flush=True)
        # Load needed columns only
        frames = []
        for path in all_files:
            try:
                df = pd.read_parquet(
                    path,
                    columns=[
                        "primary_symbol",
                        "bar_end_utc",
                        "side",
                        "outcomes",
                    ],
                )
            except Exception as exc:
                print(f"\n    error reading {path}: {exc}")
                continue
            frames.append(df)
        if not frames:
            print("empty")
            continue
        all_events = pd.concat(frames, ignore_index=True)
        print(f"loaded {len(all_events):,} events")

        # Group by primary_symbol
        for sym, sub in all_events.groupby("primary_symbol"):
            profile = _build_one_profile(sub, feature=feature, symbol=str(sym))
            if profile:
                rows.append(profile)

    return pd.DataFrame(rows)


def asset_class_rollup(per_sym: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per (feature, asset_class)."""
    numeric_cols = [
        c for c in per_sym.columns
        if c not in ("feature", "symbol", "asset_class")
    ]
    out_rows: list[dict] = []
    for (feature, aclass), grp in per_sym.groupby(["feature", "asset_class"]):
        row = {
            "feature": feature,
            "asset_class": aclass,
            "n_symbols": len(grp),
            "symbols": ",".join(sorted(grp["symbol"])),
        }
        for col in numeric_cols:
            vals = pd.to_numeric(grp[col], errors="coerce").dropna()
            if vals.empty:
                continue
            row[f"{col}__mean"] = round(float(vals.mean()), 4)
            row[f"{col}__std"] = round(float(vals.std()), 4) if len(vals) > 1 else 0.0
        out_rows.append(row)
    return pd.DataFrame(out_rows)


def write_summary_md(per_sym: pd.DataFrame, per_class: pd.DataFrame, out_dir: Path) -> None:
    lines: list[str] = []
    lines.append("# Feature Profiles — per asset + per asset class")
    lines.append("")
    lines.append(f"_Generated {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")}Z_")
    lines.append("")
    lines.append(f"Coverage: {per_sym['feature'].nunique()} features × "
                 f"{per_sym['symbol'].nunique()} symbols = "
                 f"{len(per_sym):,} profile rows.")
    lines.append("")
    lines.append("Total events analyzed: "
                 f"{int(per_sym['count'].sum()):,}")
    lines.append("")

    # Per asset class: top-3 features by fwd10_ratio mean
    if "fwd10_ratio_mfe_mae__mean" in per_class.columns:
        lines.append("## Top-3 features by fwd10 MFE/MAE ratio, per asset class")
        lines.append("")
        for aclass in sorted(per_class["asset_class"].unique()):
            sub = per_class[per_class["asset_class"] == aclass].copy()
            sub = sub.dropna(subset=["fwd10_ratio_mfe_mae__mean"]).sort_values(
                "fwd10_ratio_mfe_mae__mean", ascending=False
            ).head(3)
            if sub.empty:
                continue
            lines.append(f"### {aclass}")
            lines.append("")
            lines.append("| Rank | Feature | n_symbols | fwd10 ratio (mean) | fwd10 hit (mean) | fwd50 ratio (mean) |")
            lines.append("|---|---|---:|---:|---:|---:|")
            for i, row in enumerate(sub.itertuples(), 1):
                lines.append(
                    f"| {i} | `{row.feature}` | {row.n_symbols} | "
                    f"{getattr(row, 'fwd10_ratio_mfe_mae__mean', None)} | "
                    f"{getattr(row, 'fwd10_last_close_thesis_hitrate__mean', None)} | "
                    f"{getattr(row, 'fwd50_ratio_mfe_mae__mean', None)} |"
                )
            lines.append("")

    # Per feature: top-5 symbols by fwd10_ratio
    if "fwd10_ratio_mfe_mae" in per_sym.columns:
        lines.append("## Top-5 symbols per feature (by fwd10 MFE/MAE ratio)")
        lines.append("")
        for feature in sorted(per_sym["feature"].unique()):
            sub = per_sym[per_sym["feature"] == feature].copy()
            sub = sub.dropna(subset=["fwd10_ratio_mfe_mae"]).sort_values(
                "fwd10_ratio_mfe_mae", ascending=False
            ).head(5)
            if sub.empty:
                continue
            lines.append(f"### {feature}")
            lines.append("")
            lines.append("| # | Symbol | Class | Events | per_yr | fwd10 ratio | fwd10 hit | fwd50 ratio |")
            lines.append("|---|---|---|---:|---:|---:|---:|---:|")
            for i, row in enumerate(sub.itertuples(), 1):
                lines.append(
                    f"| {i} | {row.symbol} | {row.asset_class} | "
                    f"{row.count:,} | {row.per_year} | "
                    f"{row.fwd10_ratio_mfe_mae} | "
                    f"{getattr(row, 'fwd10_last_close_thesis_hitrate', None)} | "
                    f"{getattr(row, 'fwd50_ratio_mfe_mae', None)} |"
                )
            lines.append("")

    lines.append("## How to read this")
    lines.append("")
    lines.append("- `fwd10_ratio_mfe_mae`: mean of (forward-10-candle MFE in thesis direction) / "
                 "(forward-10-candle MAE against thesis). Higher = the detector's directional "
                 "thesis tends to play out more than it gets stopped out. 1.0 is symmetric; >1.5 "
                 "is interesting.")
    lines.append("- `fwd10_last_close_thesis_hitrate`: % of events where forward-10-bars later "
                 "the price moved IN the thesis direction. 0.50 = coin flip; >0.55 is decent.")
    lines.append("- These are RAW outcome stats, NOT a backtest. A high-ratio detector still "
                 "needs a proper trade rule (entry, stop, target) to make money. This profile "
                 "is the first filter for 'which features are worth simulating on which assets.'")
    lines.append("")

    (out_dir / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", default=None,
                        help="Comma-separated feature names. Default: all 14.")
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir) if args.out_dir else (
        repo_root / "experiments" / f"feature_profiles_{run_id}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    default_features = [
        "fvg_formation",
        "order_block",
        "liquidity_sweep",
        "swing_pivot",
        "displacement_candle",
        "opening_gap_levels",
        "opening_range_breakout",
        "first_third_range",
        "interval_true_range",
        "volume_profile",
        "forming_volume_profile",
        "time_profile",
        "psp_candle_divergence",
        "smt_htf_reference_divergence",
    ]
    features = args.features.split(",") if args.features else default_features

    print(f"=== V30 — Feature behavior profiles ===")
    print(f"Run ID:   {run_id}")
    print(f"Features: {features}")
    print(f"Out dir:  {out_dir}")
    print()

    per_sym = build_profiles(repo_root, features)
    print(f"\nBuilt {len(per_sym)} profile rows.")

    per_sym_path = out_dir / "per_feature_per_symbol.csv"
    per_sym.to_csv(per_sym_path, index=False)
    print(f"  wrote: {per_sym_path}")

    per_class = asset_class_rollup(per_sym)
    per_class_path = out_dir / "per_asset_class.csv"
    per_class.to_csv(per_class_path, index=False)
    print(f"  wrote: {per_class_path}")

    write_summary_md(per_sym, per_class, out_dir)
    print(f"  wrote: {out_dir / 'SUMMARY.md'}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
