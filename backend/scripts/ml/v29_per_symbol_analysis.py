"""V29 — Per-symbol cum_R analysis + liquidity filter.

Consumes the trades_* CSVs from v28's multi-symbol run. Computes:
  - Per-symbol cum_R and avg_R (across both families combined)
  - Per-asset-class roll-up
  - Liquidity profile per symbol (median 1m volume during RTH)
  - Recommended execution universe: symbols with positive cum_R AND
    median RTH volume >= threshold

Then re-runs the single-account portfolio sim from gate 4 but on the
expanded liquid-execution universe to see if retention crosses 70%.

USAGE:
  python backend/scripts/ml/v29_per_symbol_analysis.py \
      --trades-dir D:/BacktestStationData/slim_anchors_2018_2019_universe/v28_simulation_results \
      --bars-window-start 2018-01-01 --bars-window-end 2020-01-01
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.data.reader import read_bars  # noqa: E402


# Rough asset-class taxonomy
ASSET_CLASS = {
    "ES.c.0": "index", "NQ.c.0": "index", "YM.c.0": "index", "RTY.c.0": "index",
    "6A.c.0": "fx", "6B.c.0": "fx", "6C.c.0": "fx", "6E.c.0": "fx",
    "6J.c.0": "fx", "6N.c.0": "fx", "6S.c.0": "fx",
    "CL.c.0": "energy", "BZ.c.0": "energy", "HO.c.0": "energy",
    "RB.c.0": "energy", "NG.c.0": "energy",
    "ZC.c.0": "grain", "ZS.c.0": "grain", "ZW.c.0": "grain",
    "ZB.c.0": "bond", "ZF.c.0": "bond", "ZN.c.0": "bond", "ZT.c.0": "bond",
}

VOLUME_LIQUIDITY_THRESHOLD = 25  # median 1m volume during RTH


def load_trades(trades_dir: Path) -> pd.DataFrame:
    """Load every trades_*.csv in the v28 output dir."""
    frames = []
    for path in sorted(trades_dir.glob("trades_*.csv")):
        df = pd.read_csv(path)
        df = df.dropna(subset=["pnl_r", "entry_ts", "exit_ts"]).copy()
        fn = path.name
        if "OB_strict" in fn:
            df["family"] = "OB strict"
        elif "Sweep_reversed" in fn:
            df["family"] = "Sweep reversed (filtered)"
        else:
            df["family"] = "unknown"
        df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True)
        df["exit_ts"] = pd.to_datetime(df["exit_ts"], utc=True)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def per_symbol_summary(trades: pd.DataFrame) -> pd.DataFrame:
    grp = trades.groupby("symbol").agg(
        n_trades=("pnl_r", "count"),
        cum_r=("pnl_r", "sum"),
        avg_r=("pnl_r", "mean"),
        win_rate=("pnl_r", lambda s: (s > 0).mean()),
    ).reset_index()
    grp["asset_class"] = grp["symbol"].map(ASSET_CLASS).fillna("other")
    return grp.sort_values("cum_r", ascending=False).reset_index(drop=True)


def per_family_per_symbol(trades: pd.DataFrame) -> pd.DataFrame:
    return (
        trades.groupby(["family", "symbol"])["pnl_r"]
        .agg(["sum", "count", "mean"])
        .rename(columns={"sum": "cum_r", "count": "n", "mean": "avg_r"})
        .reset_index()
        .sort_values(["family", "cum_r"], ascending=[True, False])
    )


def per_asset_class(per_symbol: pd.DataFrame) -> pd.DataFrame:
    return (
        per_symbol.groupby("asset_class")
        .agg(symbols=("symbol", list),
             n_symbols=("symbol", "count"),
             n_trades=("n_trades", "sum"),
             cum_r=("cum_r", "sum"),
             avg_r=("avg_r", "mean"))
        .reset_index()
        .sort_values("cum_r", ascending=False)
    )


def compute_liquidity_profile(symbols: list[str], start: date, end: date) -> pd.DataFrame:
    """For each symbol, compute median 1m volume during US RTH
    (14:30-21:00 UTC = 9:30-16:00 ET, approximately)."""
    rows = []
    for sym in symbols:
        try:
            bars = read_bars(symbol=sym, timeframe="1m", start=start, end=end)
        except Exception as exc:
            rows.append({"symbol": sym, "error": str(exc)})
            continue
        if bars.empty:
            rows.append({"symbol": sym, "median_rth_volume": 0,
                         "median_all_volume": 0, "n_bars": 0})
            continue
        bars["ts_event"] = pd.to_datetime(bars["ts_event"], utc=True)
        hours = bars["ts_event"].dt.hour
        rth = bars[(hours >= 14) & (hours < 21)]
        rows.append({
            "symbol": sym,
            "n_bars": len(bars),
            "n_bars_rth": len(rth),
            "median_rth_volume": float(rth["volume"].median()) if not rth.empty else 0,
            "median_all_volume": float(bars["volume"].median()),
            "mean_rth_volume": float(rth["volume"].mean()) if not rth.empty else 0,
        })
    return pd.DataFrame(rows)


def single_account_sim(
    trades: pd.DataFrame, *, cap_total: int, per_symbol_cap: int
) -> dict:
    """v25-style single-account sim."""
    trades = trades.sort_values(["entry_ts", "family", "symbol"], kind="stable").reset_index(drop=True)
    open_positions: list[dict] = []
    taken_rows: list[dict] = []
    blocked = {"per_symbol": 0, "total_cap": 0}

    for _, row in trades.iterrows():
        open_positions = [p for p in open_positions if p["exit_ts"] > row["entry_ts"]]
        same = sum(1 for p in open_positions if p["symbol"] == row["symbol"])
        if same >= per_symbol_cap:
            blocked["per_symbol"] += 1
            continue
        if len(open_positions) >= cap_total:
            blocked["total_cap"] += 1
            continue
        open_positions.append({"symbol": row["symbol"], "exit_ts": row["exit_ts"]})
        taken_rows.append(row.to_dict())

    taken_df = pd.DataFrame(taken_rows) if taken_rows else pd.DataFrame()
    cum_r_total = float(trades["pnl_r"].sum())
    cum_r_taken = float(taken_df["pnl_r"].sum()) if not taken_df.empty else 0.0

    return {
        "cap_total": cap_total,
        "per_symbol_cap": per_symbol_cap,
        "n_candidate": int(len(trades)),
        "n_taken": int(len(taken_df)),
        "blocked_per_symbol": blocked["per_symbol"],
        "blocked_total_cap": blocked["total_cap"],
        "cum_r_baseline": round(cum_r_total, 2),
        "cum_r_single_account": round(cum_r_taken, 2),
        "retention": round(cum_r_taken / cum_r_total, 4) if cum_r_total else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades-dir", required=True)
    parser.add_argument("--bars-window-start", required=True)
    parser.add_argument("--bars-window-end", required=True)
    parser.add_argument("--liquidity-threshold", type=int, default=VOLUME_LIQUIDITY_THRESHOLD)
    args = parser.parse_args()

    trades_dir = Path(args.trades_dir)
    out_dir = trades_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== V29 — Per-symbol analysis + liquidity filter ===")
    print(f"Trades dir: {trades_dir}")
    print()

    trades = load_trades(trades_dir)
    print(f"Loaded {len(trades):,} trades total")

    baseline = float(trades["pnl_r"].sum())
    print(f"Independent baseline cum_R: {baseline:.2f}")
    print()

    per_sym = per_symbol_summary(trades)
    print("Per-symbol summary (top 15):")
    print(per_sym.head(15).to_string(index=False))
    print()
    per_sym.to_csv(out_dir / "v29_per_symbol.csv", index=False)

    per_fam_sym = per_family_per_symbol(trades)
    per_fam_sym.to_csv(out_dir / "v29_per_family_per_symbol.csv", index=False)

    pac = per_asset_class(per_sym)
    print("Per asset class:")
    print(pac.to_string(index=False))
    print()
    pac.to_csv(out_dir / "v29_per_asset_class.csv", index=False)

    # Liquidity profile
    print("Computing liquidity profile from 1m bars...")
    symbols = per_sym["symbol"].tolist()
    bars_start = date.fromisoformat(args.bars_window_start)
    bars_end = date.fromisoformat(args.bars_window_end)
    liq = compute_liquidity_profile(symbols, bars_start, bars_end)
    print(liq.sort_values("median_rth_volume", ascending=False).to_string(index=False))
    print()
    liq.to_csv(out_dir / "v29_liquidity.csv", index=False)

    # Merge edge + liquidity
    combo = per_sym.merge(liq, on="symbol", how="left")
    combo["liquid_enough"] = combo["median_rth_volume"] >= args.liquidity_threshold
    combo["positive_edge"] = combo["cum_r"] > 0
    combo["execute"] = combo["liquid_enough"] & combo["positive_edge"]
    print("Merged edge + liquidity:")
    print(combo[["symbol", "asset_class", "n_trades", "cum_r", "avg_r",
                  "median_rth_volume", "liquid_enough", "positive_edge", "execute"]].to_string(index=False))
    print()
    combo.to_csv(out_dir / "v29_combo.csv", index=False)

    # Sub-universes:
    full_universe = combo["symbol"].tolist()
    liquid_universe = combo.loc[combo["liquid_enough"], "symbol"].tolist()
    edge_universe = combo.loc[combo["positive_edge"], "symbol"].tolist()
    deploy_universe = combo.loc[combo["execute"], "symbol"].tolist()

    print(f"Universes:")
    print(f"  Full:    {len(full_universe)} symbols")
    print(f"  Liquid:  {len(liquid_universe)} symbols  {sorted(liquid_universe)}")
    print(f"  Edge>0:  {len(edge_universe)} symbols  {sorted(edge_universe)}")
    print(f"  Deploy:  {len(deploy_universe)} symbols  {sorted(deploy_universe)}")
    print()

    # Single-account sim across the 4 universes
    print("Single-account sim across universes (cap_total=many, per_symbol=1):")
    results = {}
    for name, syms in [("full", full_universe), ("liquid", liquid_universe),
                       ("edge", edge_universe), ("deploy", deploy_universe)]:
        sub = trades[trades["symbol"].isin(syms)]
        if sub.empty:
            results[name] = {"empty": True}
            continue
        # cap_total = len(syms) so the only effective cap is per-symbol=1
        sim = single_account_sim(sub, cap_total=len(syms), per_symbol_cap=1)
        results[name] = {"universe_size": len(syms), **sim}
        print(f"  {name:>8} ({len(syms)} syms): "
              f"candidate={sim['n_candidate']}, "
              f"taken={sim['n_taken']}, "
              f"cum_R={sim['cum_r_single_account']:.2f} of "
              f"baseline={sim['cum_r_baseline']:.2f} "
              f"→ retention={sim['retention']*100:.1f}%")
    print()

    (out_dir / "v29_summary.json").write_text(
        json.dumps({
            "trades_dir": str(trades_dir),
            "bars_window": [args.bars_window_start, args.bars_window_end],
            "liquidity_threshold": args.liquidity_threshold,
            "n_trades_total": int(len(trades)),
            "baseline_cum_r": round(baseline, 2),
            "universes": {k: results[k] for k in results},
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        }, indent=2, default=str)
    )
    print(f"Wrote: {out_dir / 'v29_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
