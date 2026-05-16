"""Quick FX per-year stability check.

The cross-asset screening showed FX is the profitable cross-asset lane
(+84R), with 6C/6N/6E as standouts. But is that result stable year-to-
year, or 1-2 lucky years carrying the rest?

This script reads the existing trades.csv from cross_asset_screening
and breaks down FX results per (symbol, year). No new compute needed.
"""

from pathlib import Path
import json

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(r"C:\Users\benbr\BacktestStation")
IN = ROOT / "experiments" / "backtests" / "2026-05-16_cross_asset_screening" / "trades.csv"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_fx_stability"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FX_SYMBOLS = ["6A.c.0", "6B.c.0", "6C.c.0", "6E.c.0", "6J.c.0", "6N.c.0", "6S.c.0"]

df = pd.read_csv(IN)
df = df[df["exit_reason"].isin(["target", "stop", "time_exit"])]
fx = df[df["symbol"].isin(FX_SYMBOLS)].copy()
print(f"FX trades (executed): {len(fx)}")
print(f"FX cum_R total: {fx['pnl_r'].sum():+.1f}")
print(f"FX win rate: {(fx['pnl_r'] > 0).mean():.3f}")

# Per (symbol, year).
print("\n=== Per-symbol × per-year cum_R ===")
pivot = fx.pivot_table(index="symbol", columns="test_year", values="pnl_r", aggfunc="sum", fill_value=0)
pivot["total"] = pivot.sum(axis=1)
pivot["years_positive"] = (pivot.drop(columns="total") > 0).sum(axis=1)
pivot = pivot.sort_values("total", ascending=False)
pivot.to_csv(OUT_DIR / "fx_per_symbol_per_year.csv", float_format="%.4f")
print(pivot.to_string(float_format=lambda x: f"{x:+.2f}"))

# Per-symbol summary stats.
print("\n=== Per-symbol summary ===")
rows = []
for sym, g in fx.groupby("symbol"):
    n = len(g)
    wins = int((g["pnl_r"] > 0).sum())
    cum_r = float(g["pnl_r"].sum())
    cumr_series = g.sort_values("fire_ts")["pnl_r"].cumsum()
    max_dd = float((cumr_series.cummax() - cumr_series).max()) if n else 0.0
    years_pos = int(g.groupby("test_year")["pnl_r"].sum().gt(0).sum())
    rows.append({
        "symbol": sym, "n_trades": n, "wins": wins, "win_rate": wins / n if n else 0.0,
        "cum_r": cum_r, "avg_r": cum_r / n if n else 0.0,
        "max_dd_r": max_dd, "years_positive": years_pos,
        "years_tested": int(g["test_year"].nunique()),
    })
per_sym = pd.DataFrame(rows).sort_values("cum_r", ascending=False)
per_sym.to_csv(OUT_DIR / "fx_per_symbol_summary.csv", index=False, float_format="%.4f")
print(per_sym.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

# Per-symbol equity curves.
fig, ax = plt.subplots(figsize=(13, 7))
for sym, g in fx.groupby("symbol"):
    g_sorted = g.sort_values("fire_ts").copy()
    g_sorted["cum_r"] = g_sorted["pnl_r"].cumsum()
    ax.plot(g_sorted["fire_ts"], g_sorted["cum_r"],
            label=f"{sym} (n={len(g)}, R={g_sorted['cum_r'].iloc[-1]:+.1f})", linewidth=1.5)
ax.axhline(0, color="black", linewidth=0.5)
ax.set_xlabel("date"); ax.set_ylabel("cumulative R")
ax.set_title("FX equity curves — v8a rules + broad rejection labels, 22-symbol matrix")
ax.legend(loc="best", fontsize=9)
ax.grid(True, alpha=0.3)
plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
plt.tight_layout()
fig.savefig(OUT_DIR / "fx_equity_curves.png", dpi=120)
plt.close(fig)

# Verdict.
solid_fx = per_sym[(per_sym["cum_r"] > 0) & (per_sym["years_positive"] >= 4)]
verdict = {
    "n_fx_symbols_tested": int(len(per_sym)),
    "n_fx_symbols_positive": int((per_sym["cum_r"] > 0).sum()),
    "n_fx_symbols_robust": int((per_sym["years_positive"] >= 4).sum()),
    "n_fx_symbols_solid_and_robust": int(len(solid_fx)),
    "solid_robust_symbols": solid_fx["symbol"].tolist(),
    "total_fx_cum_r": float(per_sym["cum_r"].sum()),
    "verdict": (
        "FX EDGE CONFIRMED — multiple stable contributors" if len(solid_fx) >= 3 else
        "FX EDGE PARTIAL — only 1-2 stable symbols, may be noise" if len(solid_fx) >= 1 else
        "FX EDGE UNCONFIRMED — looks like a few lucky years"
    ),
}
(OUT_DIR / "verdict.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
print(f"\n=== VERDICT ===")
print(json.dumps(verdict, indent=2))
