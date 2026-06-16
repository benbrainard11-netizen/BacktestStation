"""Validate every options-walls file's derived `spot` against the matching index FUTURE
(independent ground truth), since derived spot (parity-forward for NDX, daily median
underlying for RUT/DJX/SPX) can be noisy. NQ~=NDX, RTY~=RUT, YM~=Dow=DJX*100, ES~=SPX.

Reports per index: coverage, median spot/future ratio, % of days within 8%, and the worst
outliers. A genuine basis is <~2%; a 15-30% gap = a contaminated day. Run BEFORE trusting walls.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

BARS = Path(r"D:\data\processed\bars\timeframe=1m")
EXP = Path(__file__).resolve().parents[1]

# walls_file, future symbol, spot = future_close * scale
SPECS = [
    ("NDX", EXP / "fuhhhhh/out/walls_ndx.parquet",            "NQ.c.0",  1.0),
    ("SPX", EXP / "fuhhhhh/out/walls_v2.parquet",             "ES.c.0",  1.0),
    ("RUT", EXP / "options_signals_v0/out/walls_rut.parquet", "RTY.c.0", 1.0),
    ("DJX", EXP / "options_signals_v0/out/walls_djx.parquet", "YM.c.0",  0.01),
]


def fut_daily_close(symbol: str) -> pd.Series:
    """Last 1m close per UTC date -> Series indexed by int yyyymmdd."""
    d = ds.dataset(BARS / f"symbol={symbol}", format="parquet").to_table(columns=["ts_event", "close"]).to_pandas()
    d["date"] = pd.to_datetime(d["ts_event"]).dt.strftime("%Y%m%d").astype(int)
    return d.sort_values("ts_event").groupby("date")["close"].last()


def main() -> int:
    for name, wf, sym, scale in SPECS:
        if not wf.exists():
            print(f"\n{name}: MISSING {wf}")
            continue
        w = pd.read_parquet(wf)[["date", "spot"]].copy()
        w["date"] = w["date"].astype(int)
        fc = fut_daily_close(sym)
        proxy = (fc * scale).rename("proxy")
        m = w.merge(proxy, left_on="date", right_index=True, how="left").dropna(subset=["proxy"])
        m["ratio"] = m["spot"] / m["proxy"]
        within = (m["ratio"].sub(1).abs() < 0.08).mean()
        matched = len(m)
        yrs = pd.to_datetime(m["date"].astype(str), format="%Y%m%d").dt.year
        print(f"\n=== {name}  ({len(w)} wall-days, {matched} matched to {sym}) ===")
        print(f"  years: {sorted(yrs.unique().tolist())}")
        print(f"  spot range {w['spot'].min():.1f}..{w['spot'].max():.1f}   future*scale range {proxy.min():.1f}..{proxy.max():.1f}")
        print(f"  median spot/future ratio = {m['ratio'].median():.4f}   within 8%: {within:.1%}")
        bad = m[m["ratio"].sub(1).abs() >= 0.08].sort_values("ratio")
        if len(bad):
            print(f"  OUTLIERS (|ratio-1|>=8%): {len(bad)} days ({len(bad)/matched:.1%})")
            show = pd.concat([bad.head(4), bad.tail(4)]).drop_duplicates()
            for _, r in show.iterrows():
                print(f"    {int(r['date'])}: spot={r['spot']:.1f} future*scale={r['proxy']:.1f} ratio={r['ratio']:.3f}")
        else:
            print("  no outliers — clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
