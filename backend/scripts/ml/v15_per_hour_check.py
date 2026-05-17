"""Per-hour breakdown of v15 FVG zone-reaction trades, to compare with v16
session-concentration findings."""

from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\Users\benbr\BacktestStation")
TRADES_CSV = ROOT / "experiments" / "backtests" / "2026-05-17_v15_fvg_zone_reaction_slippage" / "trades_all_slippage.csv"


def main() -> int:
    df = pd.read_csv(TRADES_CSV)
    # Filter to no_slippage scenario (so numbers are comparable to v16 unfiltered)
    df = df[df["slippage"] == "no_slippage"].copy()
    df = df[df["exit_reason"].isin(["target", "stop", "time_exit"])]
    df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True)
    df["hour_utc"] = df["entry_ts"].dt.hour

    print(f"=== V15 FVG zone-reaction trades (no_slippage scenario) ===")
    print(f"Total trades: {len(df):,}")

    by_hour = df.groupby("hour_utc").agg(
        n=("pnl_r", "size"),
        cum_r=("pnl_r", "sum"),
        avg_r=("pnl_r", "mean"),
        win_rate=("pnl_r", lambda s: (s > 0).mean()),
    ).reset_index()
    print("\n=== Per-hour ===")
    print(by_hour.to_string(index=False, float_format=lambda x: f"{x:.4f}" if isinstance(x, float) else str(x)))

    def session(h):
        if 14 <= h <= 21: return "US_RTH"
        if 7 <= h <= 13: return "EU_pre_NY"
        return "Asia_overnight"
    by_hour["session"] = by_hour["hour_utc"].apply(session)
    by_session = by_hour.groupby("session").agg(
        n=("n", "sum"),
        cum_r=("cum_r", "sum"),
    ).reset_index()
    by_session["pct_trades"] = 100 * by_session["n"] / by_session["n"].sum()
    by_session["pct_r"] = 100 * by_session["cum_r"] / by_session["cum_r"].sum()
    by_session["avg_r"] = by_session["cum_r"] / by_session["n"]
    print("\n=== Session rollup ===")
    print(by_session.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Filter scenario: drop Asia overnight
    filtered = df[~df["hour_utc"].isin([22, 23, 0, 1, 2, 3, 4, 5, 6])]
    print(f"\n=== Filter scenario: drop Asia overnight (hours 22-06 UTC) ===")
    print(f"  Original:  n={len(df):>6} cum_R={df['pnl_r'].sum():+8.1f} avg_R={df['pnl_r'].mean():+6.4f}")
    print(f"  Filtered:  n={len(filtered):>6} cum_R={filtered['pnl_r'].sum():+8.1f} avg_R={filtered['pnl_r'].mean():+6.4f}")
    print(f"  Kept: {100*len(filtered)/len(df):.0f}% of trades, {100*filtered['pnl_r'].sum()/df['pnl_r'].sum():.0f}% of R, {filtered['pnl_r'].mean()/df['pnl_r'].mean():.1f}x avg_R")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
