"""Does REAL dealer GEX condition the reclaim edge? Uses the multi-month ThetaData GEX (total_gex regime,
cross-asset SPX/NDX divergence, walls) -- not the 2025 binary stub. No-lookahead: PRIOR-day GEX (settled OI,
known by morning) conditions the current day's reclaim trades. Reads events_es_tf + gex_levels_{spx,ndx}.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import boot, seq_r  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
GEX = Path(__file__).resolve().parents[1] / "options_signals_v0" / "out"
TARGET = 3.0


def _gex(name: str) -> pd.DataFrame:
    df = pd.read_parquet(GEX / f"gex_levels_{name}.parquet").sort_values("date")
    df["d"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d").dt.date
    return df.set_index("d")


def _split(d: pd.DataFrame, label: str, groups) -> None:
    print(label)
    for name, mask in groups:
        s = d[mask.fillna(False).to_numpy()]
        if len(s) < 20:
            print(f"   {name:22} n<20 ({len(s)})")
            continue
        m, lo, hi = boot(s["r"].to_numpy(), s["day"].to_numpy())
        print(f"   {name:22} {m:+.2f} [{lo:+.2f},{hi:+.2f}]  n{len(s)}")


def main() -> int:
    df = pd.read_parquet(OUT / "events_es_tf.parquet")
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].copy()
    df["r"] = seq_r(df, TARGET)
    spx, ndx = _gex("spx"), _gex("ndx")
    spx_prev, ndx_prev = spx["total_gex"].shift(1), ndx["total_gex"].shift(1)   # prior-day GEX (no lookahead)
    df["spx_gex"] = df["day"].map(spx_prev.to_dict())
    df["ndx_gex"] = df["day"].map(ndx_prev.to_dict())
    d = df.dropna(subset=["spx_gex"]).copy()
    bm, bl, bh = boot(d["r"].to_numpy(), d["day"].to_numpy())
    print(f"ES reclaim events with prior-day GEX: {len(d)}")
    print(f"baseline reclaim R: {bm:+.2f} [{bl:+.2f},{bh:+.2f}]\n")

    _split(d, "by SPX gamma REGIME (prior-day total_gex sign):",
           [("positive (pin/revert)", d["spx_gex"] > 0), ("negative (trend)", d["spx_gex"] <= 0)])

    dd = d.dropna(subset=["ndx_gex"]).copy()
    dd["cross"] = np.sign(dd["spx_gex"]) != np.sign(dd["ndx_gex"])
    print()
    _split(dd, "by CROSS-ASSET GEX divergence (SPX vs NDX gamma sign):",
           [("aligned", ~dd["cross"]), ("DIVERGED", dd["cross"])])

    print("\nby |GEX| magnitude tercile (strong vs weak pinning):")
    d["mag"] = d["spx_gex"].abs()
    d["magt"] = pd.qcut(d["mag"].rank(method="first"), 3, labels=["low", "mid", "high"])
    _split(d, "", [(f"|gex| {t}", d["magt"] == t) for t in ("low", "mid", "high")])

    print("\nREAD: a split with R clearly different from the flat baseline = GEX conditions the edge (real signal "
          "on real data); flat across = the daily-GEX null holds even with the full chain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
