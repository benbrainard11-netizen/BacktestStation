"""SPX EOD option-chain loader from the ThetaData greeks cache.

The cache (bulk_hist_option_eod_greeks) is hash-keyed and mixes underlyings by strike band, so we
classify SPX by strike band (reusing the walls-builder rule: SPX [1800,8500], excluding [1800,3000)
for year>=2024 where that sub-band is RUT). SPX greeks rows carry bid/ask/underlying_price/IV.

Reading ~4900 files is heavy, so the run consolidates once to out/spx_eod_chain.parquet, then the
audit reads that. This module is NOT exercised by the test suite (tests use synthetic chains).
"""

from __future__ import annotations

import glob
import os

import pandas as pd

GREEKS_DIR = r"D:\data\raw\thetadata\bulk_hist_option_eod_greeks"
KEEP_COLS = ["date", "expiration", "strike", "right", "bid", "ask",
             "underlying_price", "implied_vol"]


def spx_band_mask(df: pd.DataFrame) -> pd.Series:
    """SPX strike-band classifier (walls-builder rule), year-aware to exclude the RUT sub-band."""
    year = (df["date"] // 10000).astype(int)
    in_band = (df["strike"] >= 1800) & (df["strike"] <= 8500)
    not_rut = ~((year >= 2024) & (df["strike"] < 3000))
    return in_band & not_rut


# Keep only near-ATM strikes when consolidating: the audit needs the ATM strike +- a few, so a tight
# band shrinks 26M SPX rows to a tiny, fast chain WITHOUT changing ATM selection (nearest-3 well within).
ATM_BAND = 0.04


def _read_one(path: str, atm_band: float = ATM_BAND) -> pd.DataFrame:
    df = pd.read_parquet(path, columns=[c for c in KEEP_COLS if c != "right"] + ["right"])
    df = df[spx_band_mask(df)]
    if atm_band is not None:
        u = df["underlying_price"]
        df = df[(u > 0) & ((df["strike"] - u).abs() <= atm_band * u)]
    # EOD snapshot: one quote per (date, expiration, strike, right)
    return df.drop_duplicates(["date", "expiration", "strike", "right"], keep="last")


def build_spx_chain(out_path: str, cache_dir: str = GREEKS_DIR, atm_band: float = ATM_BAND) -> pd.DataFrame:
    """Consolidate the near-ATM SPX EOD chain to a single tidy parquet. RUN STEP (heavy I/O)."""
    parts = []
    for f in sorted(glob.glob(os.path.join(cache_dir, "*.parquet"))):
        try:
            part = _read_one(f, atm_band)
            if len(part):
                parts.append(part)
        except Exception:  # pragma: no cover - skip unreadable shards
            continue
    chain = pd.concat(parts, ignore_index=True)
    # same option-date appears across multiple cache shards -> dedup globally
    chain = chain.drop_duplicates(["date", "expiration", "strike", "right"], keep="last")
    chain["date_dt"] = pd.to_datetime(chain["date"], format="%Y%m%d")
    chain["exp_dt"] = pd.to_datetime(chain["expiration"], format="%Y%m%d")
    chain = chain.sort_values(["date", "expiration", "strike", "right"])
    chain.to_parquet(out_path, index=False)
    return chain


def load_spx_chain(path: str) -> pd.DataFrame:
    """Read the consolidated SPX chain (call build_spx_chain first)."""
    return pd.read_parquet(path)


# --- v1: NDX raw-price chain (no vendor greeks; quotes only; underlying via NQ close) ---

NDX_RAW_DIR = r"D:\data\raw\thetadata\bulk_hist_option_eod"
NDX_COLS = ["date", "expiration", "strike", "right", "bid", "ask"]


def build_ndx_chain(out_path: str, nq_close: pd.Series, cache_dir: str = NDX_RAW_DIR,
                    atm_band: float = ATM_BAND) -> pd.DataFrame:
    """Consolidate the near-ATM NDX EOD chain. `nq_close` = Series indexed by int YYYYMMDD (NQ.c.0
    daily close = NDX underlying proxy). The ATM-band-around-NQ-close filter also separates NDX from
    the SPX rows that share these files (SPX close is far from NQ close). RUN STEP (heavy I/O)."""
    parts = []
    for f in sorted(glob.glob(os.path.join(cache_dir, "*.parquet"))):
        try:
            df = pd.read_parquet(f, columns=NDX_COLS)
            df = df[df["strike"] >= 4000]  # NDX-level strikes only (drops SPX/RUT)
            u = df["date"].map(nq_close)
            df = df[(u > 0) & ((df["strike"] - u).abs() <= atm_band * u)]
            df = df.assign(underlying=u[df.index])
            if len(df):
                parts.append(df.drop_duplicates(["date", "expiration", "strike", "right"], keep="last"))
        except Exception:  # pragma: no cover
            continue
    chain = pd.concat(parts, ignore_index=True)
    chain = chain.drop_duplicates(["date", "expiration", "strike", "right"], keep="last")
    chain["date_dt"] = pd.to_datetime(chain["date"], format="%Y%m%d")
    chain["exp_dt"] = pd.to_datetime(chain["expiration"], format="%Y%m%d")
    chain.to_parquet(out_path, index=False)
    return chain.sort_values(["date", "expiration", "strike", "right"])


def underlying_daily(chain: pd.DataFrame) -> pd.Series:
    """One underlying close per date (median over rows guards stray values)."""
    s = chain.groupby("date_dt")["underlying_price"].median()
    return s.sort_index()
