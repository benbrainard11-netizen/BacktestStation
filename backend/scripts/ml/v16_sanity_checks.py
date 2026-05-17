"""Two sanity checks on v16 (Sweep reversed +4,362R) trades:

A. Bar-data integrity on top-PnL trades — verify the bars actually traded
   through the simulated entry/target/stop levels.

B. Per-hour-of-day breakdown — does the edge concentrate in liquid US hours
   or illiquid overnight? If illiquid hours dominate, the deploy edge is fake.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.rigorous_backtest_v1 import BarsCache

ROOT = Path(r"C:\Users\benbr\BacktestStation")
TRADES_CSV = ROOT / "experiments" / "backtests" / "2026-05-17_v16_sweep_reversed_verify" / "trades.csv"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-17_v16_sanity_checks"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def check_bar_integrity(trades: pd.DataFrame, bars: BarsCache, n_samples: int = 20) -> pd.DataFrame:
    """For top N winners + random N losers, verify the bars actually went where the sim claims."""
    ex = trades[trades["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    ex["fire_ts"] = pd.to_datetime(ex["fire_ts"], utc=True)
    ex["entry_ts"] = pd.to_datetime(ex["entry_ts"], utc=True)
    ex["exit_ts"] = pd.to_datetime(ex["exit_ts"], utc=True)

    # Top winners by pnl_r
    samples = pd.concat([
        ex.nlargest(n_samples, "pnl_r").assign(group="top_winners"),
        ex.nsmallest(n_samples, "pnl_r").assign(group="top_losers"),
        ex.sample(n=n_samples, random_state=42).assign(group="random"),
    ])

    results = []
    for _, t in samples.iterrows():
        bars_window = bars.get_window(t["symbol"],
                                       t["entry_ts"] - pd.Timedelta(minutes=5),
                                       t["exit_ts"] + pd.Timedelta(minutes=5))
        if bars_window.empty:
            results.append({"fire_ts": t["fire_ts"], "group": t["group"], "issue": "no_bars"})
            continue

        # Find entry bar
        entry_bar = bars_window.loc[bars_window.index == t["entry_ts"]]
        entry_bar_open = entry_bar["open"].iloc[0] if not entry_bar.empty else None

        # Find exit bar
        exit_bar = bars_window.loc[bars_window.index == t["exit_ts"]]
        exit_bar_data = exit_bar.iloc[0] if not exit_bar.empty else None

        # Path bars between entry and exit
        path = bars_window.loc[t["entry_ts"]:t["exit_ts"]]

        # Did the path actually go through the recorded exit price?
        # For target hit on long: path["high"].max() >= target_price
        # For stop hit on long: path["low"].min() <= stop_price
        # For target hit on short: path["low"].min() <= target_price
        # For stop hit on short: path["high"].max() >= stop_price
        target = t["target_price"]
        stop = t["stop_price"]
        direction = t["direction"]
        exit_reason = t["exit_reason"]

        path_high = path["high"].max()
        path_low = path["low"].min()

        # Sanity: entry_bar_open matches recorded entry_price (within 1 tick = 0.25 for NQ)
        entry_match = (abs(entry_bar_open - t["entry_price"]) < 0.5) if entry_bar_open else False

        # Sanity: path covers the exit
        if exit_reason == "target":
            if direction == "long":
                exit_reachable = path_high >= target
            else:
                exit_reachable = path_low <= target
        elif exit_reason == "stop":
            if direction == "long":
                exit_reachable = path_low <= stop
            else:
                exit_reachable = path_high >= stop
        else:
            exit_reachable = True  # time_exit always reachable

        # Volume check: any bars with volume? bars dataset doesn't always include volume
        n_path_bars = len(path)
        hour_of_day = t["entry_ts"].hour

        results.append({
            "fire_ts": t["fire_ts"], "group": t["group"], "symbol": t["symbol"],
            "direction": direction, "exit_reason": exit_reason,
            "pnl_r": t["pnl_r"], "hour_utc": hour_of_day,
            "entry_match": entry_match,
            "exit_reachable": exit_reachable,
            "n_path_bars": n_path_bars,
            "issue": (
                "entry_mismatch" if not entry_match
                else "exit_not_in_path" if not exit_reachable
                else "ok"
            ),
        })

    return pd.DataFrame(results)


def per_hour_breakdown(trades: pd.DataFrame) -> pd.DataFrame:
    """Group trades by hour-of-day (UTC) at entry."""
    ex = trades[trades["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    ex["entry_ts"] = pd.to_datetime(ex["entry_ts"], utc=True)
    ex["hour_utc"] = ex["entry_ts"].dt.hour
    grp = ex.groupby("hour_utc").agg(
        n=("pnl_r", "size"),
        cum_r=("pnl_r", "sum"),
        avg_r=("pnl_r", "mean"),
        win_rate=("pnl_r", lambda s: (s > 0).mean()),
    ).reset_index()
    return grp


def main() -> int:
    print("=== V16 sanity checks ===")
    trades = pd.read_csv(TRADES_CSV)
    print(f"Loaded {len(trades):,} trades from {TRADES_CSV.name}")

    bars = BarsCache()

    print("\n=== Check A: bar-data integrity on top 20 winners / 20 losers / 20 random ===")
    integrity = check_bar_integrity(trades, bars, n_samples=20)
    integrity.to_csv(OUT_DIR / "bar_integrity.csv", index=False, float_format="%.4f")
    print(integrity.to_string(index=False))

    issue_counts = integrity["issue"].value_counts()
    print(f"\nIssue breakdown:\n{issue_counts.to_string()}")

    print("\n=== Check B: per-hour-of-day breakdown (entry hour, UTC) ===")
    by_hour = per_hour_breakdown(trades)
    by_hour.to_csv(OUT_DIR / "per_hour.csv", index=False, float_format="%.4f")
    # US sessions (rough UTC):
    #   00-06 UTC = Asia (Tokyo+evening US ON)
    #   07-13 UTC = London / pre-NY
    #   14-21 UTC = NY session (RTH = 14:30-21:00 UTC)
    #   22-23 UTC = US close / Asia open
    print(by_hour.to_string(index=False))

    # Session rollup
    def session(h):
        if 14 <= h <= 21: return "US_RTH"
        if 7 <= h <= 13: return "EU_pre_NY"
        return "Asia_overnight"
    by_hour["session"] = by_hour["hour_utc"].apply(session)
    by_session = by_hour.groupby("session").agg(
        n=("n", "sum"),
        cum_r=("cum_r", "sum"),
        avg_r=("avg_r", "mean"),
    ).reset_index()
    by_session.to_csv(OUT_DIR / "per_session.csv", index=False, float_format="%.4f")
    print("\n=== Session rollup ===")
    print(by_session.to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
