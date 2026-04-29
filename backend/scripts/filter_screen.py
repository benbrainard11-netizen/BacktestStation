"""Screen simple no-lookahead filters on the live bot's existing 2.25y CSV.

Don't re-run the engine — just take the trades we already have and slice
by various filters (hour, direction, htf_tf, ltf_tf, monthly) to see if
any subset has positive expectation. If a clean filter exists, we can
add it to live with no code surgery.

The base CSV is `live_engine_bt_2024-01-02_2026-01-31__val_930.csv` —
written by the harness after the check_touch + RTH-overlap fixes.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

CSV = Path("C:/Fractal-AMD/outputs/live_engine_bt_2024-01-02_2026-01-31__val_930.csv")


def summarize(df, label):
    if len(df) == 0:
        print(f"{label}: 0 trades")
        return
    n = len(df)
    wr = (df.pnl_r > 0).mean() * 100
    total_r = df.pnl_r.sum()
    avg_r = total_r / n
    cum = df.pnl_r.cumsum().reset_index(drop=True)
    dd = (cum - cum.cummax()).min()
    print(f"{label}: n={n:>4} WR={wr:>5.1f}% totalR={total_r:>+7.1f}R avgR={avg_r:>+5.2f} maxDD={-dd:.1f}R")


def main():
    df = pd.read_csv(CSV)
    df["entry_dt"] = pd.to_datetime(df["date"] + " " + df["entry_time"])
    df["hour"] = df["entry_dt"].dt.hour
    df["minute"] = df["entry_dt"].dt.minute
    df["dow"] = df["entry_dt"].dt.day_name()
    df["month"] = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)

    print(f"=== Base ({CSV.name}) ===")
    summarize(df, "ALL                ")

    print("\n=== By hour ===")
    for h in sorted(df["hour"].unique()):
        summarize(df[df["hour"] == h], f"hour={h:02d}            ")

    print("\n=== By direction ===")
    for d in df["direction"].unique():
        summarize(df[df["direction"] == d], f"dir={d}        ")

    print("\n=== By LTF ===")
    for tf in df["ltf_tf"].unique():
        summarize(df[df["ltf_tf"] == tf], f"ltf={tf}             ")

    print("\n=== By HTF ===")
    for tf in df["htf_tf"].unique():
        summarize(df[df["htf_tf"] == tf], f"htf={tf}        ")

    print("\n=== By risk bucket ===")
    df["risk_bkt"] = pd.cut(df["risk"], bins=[0, 8, 12, 18, 25, 50, 200], right=False)
    for bkt in df["risk_bkt"].cat.categories:
        sub = df[df["risk_bkt"] == bkt]
        summarize(sub, f"risk={str(bkt):<14}")

    print("\n=== By DOW ===")
    for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        summarize(df[df["dow"] == d], f"dow={d:<10}")

    print("\n=== Hour x Direction (top R) ===")
    pivot = df.groupby(["hour", "direction"]).agg(
        n=("pnl_r", "size"), wr=("pnl_r", lambda s: (s > 0).mean() * 100),
        total_r=("pnl_r", "sum"),
    ).sort_values("total_r", ascending=False).head(15)
    print(pivot.to_string())


if __name__ == "__main__":
    main()
