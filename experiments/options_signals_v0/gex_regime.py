"""THE test the $75 bought: does dealer GEX condition next-day ES behavior?

The free VIX proxy conditioned realized vol (expected) but NOT trendiness (the pin-vs-trend gate; corr
+0.007). Real dealer gamma is the sharper signal. Thesis: POSITIVE gamma (dealers suppress) -> next-day
ES is calmer + more MEAN-REVERTING (low trendiness); NEGATIVE gamma (dealers amplify) -> more volatile +
more TRENDING. So expect corr(GEX, trendiness) NEGATIVE and corr(GEX, realized_vol) NEGATIVE.

No-lookahead: GEX from day t-1 (settled OI, known by morning t) -> predicts day t's ES. n~246 (2025 only,
small -- suggestive not definitive).

Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/gex_regime.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("experiments/options_signals_v0/out")


def main() -> int:
    gex = pd.read_parquet(OUT / "spx_gex_daily.parquet")
    gex.index = pd.to_datetime(gex.index).tz_localize(None).normalize()
    es = pd.read_parquet(OUT / "es_daily_intraday.parquet").set_index("date")
    es.index = pd.to_datetime(es.index).tz_localize(None).normalize()

    g = gex[["gex", "put_share"]].shift(1)                 # t-1 GEX -> day t (no lookahead)
    m = es.join(g, how="inner").dropna(subset=["eff", "rv", "gex"])
    print(f"merged {len(m)} days {m.index.min().date()}..{m.index.max().date()}")
    print("(eff = intraday trendiness: high=trend/low=mean-revert; rv = realized vol)\n")

    m = m.copy()
    m["bucket"] = pd.qcut(m["gex"], 3, labels=["neg-gamma (trend?)", "mid", "pos-gamma (pin?)"])
    print(m.groupby("bucket", observed=True).agg(
        n=("eff", "size"), trendiness=("eff", "mean"), realized_vol=("rv", "mean"),
        abs_move=("absret", "mean")).to_string(float_format=lambda x: f"{x:.4f}"))
    ce, cv = m["gex"].corr(m["eff"]), m["gex"].corr(m["rv"])
    print(f"\ncorr(GEX, trendiness) = {ce:+.3f}   (thesis: NEGATIVE = pos-gamma pins, neg-gamma trends)")
    print(f"corr(GEX, realized_vol) = {cv:+.3f}   (thesis: NEGATIVE = pos-gamma suppresses vol)")

    pos, neg = m[m["gex"] > 0], m[m["gex"] < 0]
    print(f"\npositive-gamma days (n={len(pos)}): trendiness {pos['eff'].mean():.4f}  vol {pos['rv'].mean():.4f}")
    print(f"negative-gamma days (n={len(neg)}): trendiness {neg['eff'].mean():.4f}  vol {neg['rv'].mean():.4f}")

    print("\n--- vs the FREE VIX proxy (which got trendiness corr +0.007) ---")
    better = abs(ce) > 0.10
    print("VERDICT: " + (
        f"GEX conditions trendiness (corr {ce:+.3f}) where VIX couldn't -> the regime gate is REAL, "
        "worth wiring as a live filter on the index strategies."
        if better else
        f"GEX trendiness corr {ce:+.3f} -- still weak, like the proxy. The pin-vs-trend gate does NOT show "
        "up even with real dealer gamma (n small, but discouraging). Vol-conditioning is the only robust part."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
