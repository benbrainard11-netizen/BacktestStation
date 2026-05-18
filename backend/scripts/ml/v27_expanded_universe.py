"""V27 — Expanded-universe walk-forward (post-lock, NOT a locked test).

Runs OB strict + Sweep reversed (filtered) on an expanded symbol
universe to see how much of v20's concurrency haircut (gate 4 fail)
can be recovered by adding symbols.

NOT A LOCKED TEST. This is *research after* the locked walk-forward
result. We are NOT changing the v20 conclusion; we're investigating
whether the deploy-candidate could be expanded to a wider universe
before paper-trading.

INPUT: same lockfile + same simulator + same trade rule + same fill
model as v20. Only thing changed: the symbol filter.

USAGE:
    python backend/scripts/ml/v27_expanded_universe.py \
        --symbols NQ.c.0,ES.c.0,YM.c.0

DEFAULT SYMBOLS: NQ + ES + YM (all three are already in the v20
anchor matrices; YM was just not enabled by v20's hardcoded filter).

OUTPUT:
  experiments/expanded_universe_2026_05_17/
    config.yaml           (the symbols + windows we ran)
    results/
      trades_<window>_<family>_<slippage>.csv
      rollup.csv
      single_account_sim.json
      single_account_sim.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time as time_mod
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ml.rigorous_backtest_v1 import (  # noqa: E402
    BarsCache,
    Signal,
    SYMBOL_COL,
    SIDE_COL,
    TIME_COL_CANDIDATES,
)
from scripts.ml.rigorous_backtest_v9_ob import V8A_STOP  # noqa: E402
from scripts.ml.v10_raw_ob_slippage import (  # noqa: E402
    Slippage,
    simulate_v7_slip,
    resolve_dir,
)

# Mirror v20's helpers — but parameterized symbols.
from scripts.ml.v20_locked_walkforward import (  # noqa: E402
    all_events_picks_any_year,
    filter_picks_to_window,
    _family_key,
    compute_stats,
)


ROOT = Path(r"C:\Users\benbr\BacktestStation")
LOCKFILE_PATH = ROOT / "experiments" / "locked_walkforward_2026_05_17" / "lockfile.yaml"
OUT_BASE = ROOT / "experiments" / "expanded_universe_2026_05_17"
OUT_DIR = OUT_BASE / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# Same windows as v20.
WINDOWS = {
    "locked_holdout_1": (
        pd.Timestamp("2018-01-01", tz="UTC"),
        pd.Timestamp("2019-12-31 19:55:00", tz="UTC"),
    ),
    "locked_holdout_2": (
        pd.Timestamp("2026-01-01", tz="UTC"),
        pd.Timestamp("2026-05-15 23:59:59", tz="UTC"),
    ),
}

# v20's primary fill model. We DON'T re-run the stress tests here —
# we only need primary_2tick for the v25 single-account sim input.
PRIMARY_SLIPPAGE = Slippage(
    "primary_2tick", entry_ticks=2.0, stop_ticks=2.0, time_exit_ticks=2.0
)

# Survivor families from v20.
SURVIVOR_FAMILIES = (
    "OB strict",
    "Sweep reversed (filtered)",
)

# Sweep hour filter (per lockfile)
SWEEP_DROP_HOURS = {22, 23, 0, 1, 2, 3, 4, 5, 6}


def simulate_picks_for_symbols(
    picks: pd.DataFrame,
    bars: BarsCache,
    *,
    symbols: set[str],
    variant,
    slip: Slippage,
    reverse: bool,
    hour_filter: dict | None,
) -> pd.DataFrame:
    """Run the simulator over the picks filtered to the given symbol set."""
    picks = picks[picks["symbol"].isin(symbols)].copy()
    if picks.empty:
        return pd.DataFrame()

    picks["natural_dir"] = picks["anchor_side"].apply(resolve_dir)
    if reverse:
        picks["direction"] = picks["natural_dir"].apply(
            lambda d: "long" if d == "short" else "short"
        )
    else:
        picks["direction"] = picks["natural_dir"]

    trades = []
    for _, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_v7_slip(
            bars, row["symbol"], row["fire_ts"], row["direction"], variant, slip
        )
        trades.append({
            "slippage": slip.name,
            "test_year": int(row["fire_ts"].year),
            "symbol": row["symbol"],
            "anchor_side": row["anchor_side"],
            "direction": row["direction"],
            "fire_ts": row["fire_ts"],
            **sim,
        })
    td = pd.DataFrame(trades)
    if td.empty:
        return td

    if hour_filter and hour_filter.get("type") == "drop_utc_hours":
        drop_hours = set(hour_filter["hours"])
        td["entry_hour_utc"] = pd.to_datetime(
            td["entry_ts"], utc=True, errors="coerce"
        ).dt.hour
        before = len(td)
        td = td[~td["entry_hour_utc"].isin(drop_hours)].copy()
        print(f"      hour-filter dropped {before - len(td)} of {before} trades")
    return td


def build_survivor_signals(lockfile: dict) -> list[dict]:
    out = []
    for fam in lockfile["candidate"]["families"]:
        if fam["family"] not in SURVIVOR_FAMILIES:
            continue
        anchors_path = Path(
            lockfile["data"]["anchor_matrices"][_family_key(fam["family"])]
        )
        sig = Signal(
            name=fam["family"],
            anchors_dir=anchors_path.parent,
            matrix_file=anchors_path.stem,
            snapshot=fam["snapshot"],
            side=fam["side"],
            label=fam["label"],
            direction_rule=fam["direction_rule"],
        )
        out.append({
            "name": fam["family"],
            "signal": sig,
            "reverse": fam.get("direction_reversed", False),
            "hour_filter": fam.get("hour_filter"),
        })
    return out


def run_single_account_sim(
    trades_path_pattern: str, *, cap_total: int, per_symbol_cap: int
) -> dict:
    """v25-style single-account sim against the new (expanded-universe)
    trades. Walks chronologically, applies caps."""
    import glob

    frames = []
    for path in sorted(glob.glob(trades_path_pattern)):
        df = pd.read_csv(path)
        df = df.dropna(subset=["pnl_r", "entry_ts", "exit_ts"]).copy()
        # Family name reconstructable from filename
        fn = Path(path).name
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
        return {"error": "no trade files matched"}
    trades = (
        pd.concat(frames, ignore_index=True)
        .sort_values(["entry_ts", "family", "symbol"], kind="stable")
        .reset_index(drop=True)
    )

    open_positions: list[dict] = []
    taken_rows: list[dict] = []
    blocked = {"per_symbol": 0, "total_cap": 0}

    for _, row in trades.iterrows():
        open_positions = [p for p in open_positions if p["exit_ts"] > row["entry_ts"]]
        same_symbol = sum(1 for p in open_positions if p["symbol"] == row["symbol"])
        if same_symbol >= per_symbol_cap:
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

    per_family = {}
    per_symbol = {}
    if not taken_df.empty:
        per_family = (
            taken_df.groupby("family")["pnl_r"]
            .agg(["sum", "count"])
            .rename(columns={"sum": "cum_r", "count": "n"})
            .to_dict(orient="index")
        )
        per_symbol = (
            taken_df.groupby("symbol")["pnl_r"]
            .agg(["sum", "count"])
            .rename(columns={"sum": "cum_r", "count": "n"})
            .to_dict(orient="index")
        )

    return {
        "cap_total": cap_total,
        "per_symbol_cap": per_symbol_cap,
        "n_trades_candidate": int(len(trades)),
        "n_trades_taken": int(len(taken_df)),
        "blocked_per_symbol": blocked["per_symbol"],
        "blocked_total_cap": blocked["total_cap"],
        "cum_r_independent_baseline": round(cum_r_total, 2),
        "cum_r_single_account": round(cum_r_taken, 2),
        "retention": round(cum_r_taken / cum_r_total, 4) if cum_r_total else 0.0,
        "per_family": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in per_family.items()},
        "per_symbol": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in per_symbol.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--symbols",
        default="NQ.c.0,ES.c.0,YM.c.0",
        help="Comma-separated symbol list. Default: NQ + ES + YM.",
    )
    args = parser.parse_args()
    symbols = set(s.strip() for s in args.symbols.split(",") if s.strip())
    print(f"=== V27 — Expanded-universe walk-forward ===")
    print(f"Symbols: {sorted(symbols)}")
    print(f"Lockfile: {LOCKFILE_PATH}")
    print()

    with open(LOCKFILE_PATH) as f:
        lockfile = yaml.safe_load(f)

    families = build_survivor_signals(lockfile)
    print(f"Survivor families: {[f['name'] for f in families]}")

    # Save the config used for this run
    config = {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "symbols": sorted(symbols),
        "windows": {k: (str(v[0]), str(v[1])) for k, v in WINDOWS.items()},
        "families": [f["name"] for f in families],
        "trade_rule": "v8a (per lockfile)",
        "fill_model": "primary_2tick",
        "note": "Post-lock research. NOT a locked test. v20 result stays frozen.",
    }
    (OUT_BASE / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))

    bars = BarsCache()
    t0 = time_mod.time()
    rollup_rows = []

    for win_name, (win_start, win_end) in WINDOWS.items():
        print(f"\n{'=' * 70}")
        print(f"WINDOW: {win_name}  [{win_start} -> {win_end}]")
        print(f"{'=' * 70}")

        for fam in families:
            print(f"\n--- Family: {fam['name']} ---")
            all_picks = all_events_picks_any_year(fam["signal"])
            if all_picks.empty:
                print(f"  no events for {fam['name']}; skipping")
                continue

            # Available symbols in this anchor matrix
            available = set(all_picks["symbol"].unique())
            usable = symbols & available
            print(f"  anchor-matrix symbols: {sorted(available)}")
            print(f"  requested AND available: {sorted(usable)}")
            if not usable:
                print(f"  no overlap; skipping")
                continue

            window_picks = filter_picks_to_window(all_picks, win_start, win_end)
            print(f"  events in window (any symbol): {len(window_picks):,}")

            td = simulate_picks_for_symbols(
                window_picks,
                bars,
                symbols=usable,
                variant=V8A_STOP,
                slip=PRIMARY_SLIPPAGE,
                reverse=fam["reverse"],
                hour_filter=fam["hour_filter"],
            )
            if td.empty:
                print(f"  no trades produced; skipping rollup row")
                continue

            stats = compute_stats(td)
            print(f"  stats: n={stats['n']:,} cum_R={stats['cum_r']:.2f} "
                  f"avg_R={stats['avg_r']:.4f} per_symbol={stats['per_symbol_cum_r']}")

            slug = (
                fam["name"]
                .replace(" ", "_")
                .replace("(", "")
                .replace(")", "")
            )
            out_path = (
                OUT_DIR
                / f"trades_{win_name}_{slug}_primary_2tick.csv"
            )
            td.to_csv(out_path, index=False)
            rollup_rows.append({
                "window": win_name,
                "family": fam["name"],
                **stats,
            })

    rollup = pd.DataFrame(rollup_rows)
    rollup.to_csv(OUT_DIR / "rollup.csv", index=False)
    print(f"\n  wrote rollup: {OUT_DIR / 'rollup.csv'}")

    # ---- Single-account sim against the new universe ----
    print(f"\n{'=' * 70}")
    print(f"SINGLE-ACCOUNT SIM (v25-style) on expanded universe")
    print(f"{'=' * 70}")

    pattern = str(OUT_DIR / "trades_*_primary_2tick.csv")
    sims = {}
    for cap_total in (1, 3, 5, 10):
        sim = run_single_account_sim(
            pattern, cap_total=cap_total, per_symbol_cap=1
        )
        sims[f"cap_total_{cap_total}"] = sim
        print(
            f"\n  cap_total={cap_total}, per_symbol=1:"
            f"\n    candidate={sim['n_trades_candidate']}, "
            f"taken={sim['n_trades_taken']}, "
            f"blocked_per_sym={sim['blocked_per_symbol']}, "
            f"blocked_total={sim['blocked_total_cap']}"
            f"\n    cum_R(taken)={sim['cum_r_single_account']:.2f} of "
            f"baseline={sim['cum_r_independent_baseline']:.2f} "
            f"→ retention={sim['retention']*100:.1f}%"
        )

    out_json = OUT_DIR / "single_account_sim.json"
    out_json.write_text(json.dumps(sims, indent=2, default=str))
    print(f"\n  wrote: {out_json}")

    elapsed = time_mod.time() - t0
    print(f"\nDone in {elapsed/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
