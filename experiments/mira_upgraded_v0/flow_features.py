"""Intraday options-FLOW feature panel -- what the $160 sub is actually for.

Merges the LIVE 0DTE flow (net gamma/vanna/charm built from today's cumulative volume) with the near-term
standing-book GEX (zero-gamma / walls, re-priced on live spot), then builds FLOW features = how dealer
positioning EVOLVES intraday: changes over 15/30/60 min (the hedging flow), distances to every level in ATR,
plus price/time context. Forward returns (30/60/120 min, in ATR) are the targets. STRICT no-lookahead: every
feature uses data <= T (cumulative-volume greeks, prior-day OI, within-day diffs, trailing-shifted normalizers);
targets use > T. Output: out/flow_panel.parquet  ->  feeds flow_model.py.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.indexers import FixedForwardWindowIndexer

GEX = Path(__file__).resolve().parents[1] / "options_signals_v0" / "out"
OUT = Path(__file__).resolve().parent / "out"
BARS = {"15": 3, "30": 6, "60": 12}            # 5-min bars per lookback window
FWD = {"30": 6, "60": 12, "120": 24}           # forward-return horizons
ATR_WIN, SCALE_WIN, CLOSE_MS = 14, 20, 57_600_000


def _atr(df: pd.DataFrame) -> pd.Series:
    rng = df.groupby("date")["spot"].agg(lambda s: float(s.max() - s.min()))
    return rng.rolling(ATR_WIN, min_periods=5).mean().shift(1)            # prior-day, no lookahead


def _scale(df: pd.DataFrame, col: str) -> pd.Series:
    da = df.groupby("date")[col].apply(lambda s: float(s.abs().mean()))
    return da.rolling(SCALE_WIN, min_periods=5).mean().shift(1)           # trailing 20d, no lookahead


def build() -> pd.DataFrame:
    d0 = pd.read_parquet(GEX / "dte0_intraday_spx.parquet").rename(
        columns={"net_gex": "ng0", "net_vanna": "nv", "net_charm": "nc", "pin": "pin0"})
    nt = pd.read_parquet(GEX / "intraday_gex_spx.parquet").rename(columns={"net_gex": "ngN", "pin": "pinN"})[
        ["date", "ms_of_day", "ngN", "zero_gamma", "call_wall", "put_wall", "pinN"]]
    df = (d0.merge(nt, on=["date", "ms_of_day"], how="inner")
          .sort_values(["date", "ms_of_day"]).reset_index(drop=True))
    df["atr"] = df["date"].map(_atr(df[["date", "spot"]]))
    df = df[df["atr"] > 0].reset_index(drop=True)

    for nm, col in [("d_zg", "zero_gamma"), ("d_pin0", "pin0"), ("d_pinN", "pinN"),
                    ("d_cw", "call_wall"), ("d_pw", "put_wall")]:
        df[nm] = (df["spot"] - df[col]) / df["atr"]                       # distance to level, ATR units (scale-free)
    df["ng0_sign"] = np.sign(df["ng0"])
    df["ngN_sign"] = np.sign(df["ngN"])

    for col in ["ng0", "nv", "nc", "ngN"]:                               # normalized level + intraday FLOW (the point)
        sc = df["date"].map(_scale(df, col)).replace(0, np.nan)
        df[f"{col}_n"] = df[col] / sc
        for k, b in BARS.items():
            df[f"d{col}_{k}"] = df.groupby("date")[col].diff(b) / sc      # Δ over last k min, normalized, within-day

    df["tod"] = df["ms_of_day"] / 3_600_000.0
    df["min_to_close"] = (CLOSE_MS - df["ms_of_day"]) / 60_000.0
    for k, b in BARS.items():
        df[f"ret_{k}"] = df.groupby("date")["spot"].diff(b) / df["atr"]   # recent momentum, ATR units
    df["ret_open"] = (df["spot"] - df.groupby("date")["spot"].transform("first")) / df["atr"]
    for k, b in BARS.items():                                            # recent realized vol (range) -- the bar to beat
        gmx = df.groupby("date")["spot"].transform(lambda s: s.rolling(b, min_periods=2).max())
        gmn = df.groupby("date")["spot"].transform(lambda s: s.rolling(b, min_periods=2).min())
        df[f"rv_{k}"] = (gmx - gmn) / df["atr"]
    for k, b in FWD.items():
        df[f"fwd_{k}"] = (df.groupby("date")["spot"].shift(-b) - df["spot"]) / df["atr"]   # DIRECTION target, no lookahead
        fi = FixedForwardWindowIndexer(window_size=b)
        fmx = df.groupby("date")["spot"].transform(lambda s: s.rolling(fi, min_periods=2).max())
        fmn = df.groupby("date")["spot"].transform(lambda s: s.rolling(fi, min_periods=2).min())
        df[f"fwdrange_{k}"] = (fmx - fmn) / df["atr"]                     # VOL target (forward range), no lookahead

    OUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT / "flow_panel.parquet")
    return df


def main() -> int:
    df = build()
    feats = [c for c in df.columns if c.startswith(("d", "ng", "nv", "nc", "ret", "tod", "min"))
             and not c.startswith("fwd")]
    print(f"flow panel: {len(df)} rows over {df['date'].nunique()} days -> out/flow_panel.parquet")
    print(f"features ({len(feats)}): {', '.join(feats)}")
    print(f"fwd target coverage: fwd_60 non-null {df['fwd_60'].notna().mean():.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
