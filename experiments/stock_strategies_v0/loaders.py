"""Causal data loaders for the equities line. All loaders return time-sorted frames;
callers still pass features through `common.assert_no_lookahead` at decision time.

  load_daily(t)           -> daily OHLCV (yfinance adjusted), cols: dt, open..volume
  load_etf(t)             -> same, from the ETF layer
  load_m1(t, day=None)    -> ThetaData 1m RTH bars (ts_et, ms_of_day, OHLCV)
  load_earnings(t=None)   -> earnings calendar rows (earnings_dt_et, when, surprise...)
  history_up_to(df, ts)   -> rows with timestamp <= ts (the no-lookahead accessor)
  with_mas(df)            -> add ma10/ma20/ma50/ema200 (causal: row D uses closes <= D)
"""
from __future__ import annotations

from collections import OrderedDict
from functools import lru_cache

import pandas as pd

import common as C

_OHLCV = ["open", "high", "low", "close", "volume"]


def list_universe(layer: str = "daily") -> list[str]:
    """Sorted tickers available in a daily layer (daily/etf/eod)."""
    return sorted(p.stem for p in C.layer_dir(layer).glob("*.parquet"))


@lru_cache(maxsize=512)
def load_daily(ticker: str, layer: str = "daily") -> pd.DataFrame:
    """Daily OHLCV for a ticker. `dt` is a tz-naive midnight Timestamp (the session date).
    Cached; sorted; de-duped on date. Raises FileNotFoundError if absent."""
    p = C.layer_dir(layer) / f"{ticker}.parquet"
    if not p.exists():
        raise FileNotFoundError(f"no {layer} bars for {ticker}: {p}")
    df = pd.read_parquet(p)
    df["dt"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d")
    df = (df[["dt", *_OHLCV]]
          .dropna(subset=_OHLCV)
          .drop_duplicates("dt")
          .sort_values("dt")
          .reset_index(drop=True))
    return df


def load_etf(ticker: str) -> pd.DataFrame:
    return load_daily(ticker, layer="etf")


_m1_cache: "OrderedDict[str, pd.DataFrame]" = OrderedDict()


def load_m1(ticker: str, day=None) -> pd.DataFrame:
    """ThetaData 1-minute RTH bars (ts_et tz-aware ET). Optional `day` filters to one
    session (date-like). LRU-cached per ticker (8)."""
    if ticker not in _m1_cache:
        p = C.STOCKS_M1 / f"{ticker}.parquet"
        if not p.exists():
            raise FileNotFoundError(f"no m1 bars for {ticker}: {p}")
        df = pd.read_parquet(p)
        ts = pd.to_datetime(df["ts_et"])
        df["ts_et"] = ts.dt.tz_localize(C.ET) if ts.dt.tz is None else ts.dt.tz_convert(C.ET)
        df = df.sort_values("ts_et").reset_index(drop=True)
        _m1_cache[ticker] = df
        _m1_cache.move_to_end(ticker)
        while len(_m1_cache) > 8:
            _m1_cache.popitem(last=False)
    df = _m1_cache[ticker]
    if day is not None:
        d = pd.Timestamp(day).date()
        df = df[df["ts_et"].dt.date == d]
    return df.reset_index(drop=True)


@lru_cache(maxsize=1)
def _earnings() -> pd.DataFrame:
    df = pd.read_parquet(C.EARNINGS_CAL)
    df["earnings_dt_et"] = pd.to_datetime(df["earnings_dt_et"], utc=True).dt.tz_convert(C.ET)
    return df.sort_values(["ticker", "earnings_dt_et"]).reset_index(drop=True)


def load_earnings(ticker: str | None = None) -> pd.DataFrame:
    """Earnings calendar; all names or one. Columns include `when` (AMC/BMO/INTRADAY)
    and `surprise_pct`. AMC => the gap is the NEXT session; BMO => the same session."""
    df = _earnings()
    return df[df["ticker"] == ticker].reset_index(drop=True) if ticker else df.copy()


def history_up_to(df: pd.DataFrame, ts, ts_col: str = "dt") -> pd.DataFrame:
    """Rows whose timestamp is <= ts. The causal accessor: never hand a detector rows it
    couldn't have seen at decision time `ts`."""
    return df[df[ts_col] <= pd.Timestamp(ts)]


def with_mas(df: pd.DataFrame, col: str = "close") -> pd.DataFrame:
    """Add ma10/ma20/ma50/ema200. Causal: the value on row D uses only closes through D
    (known at D's close), so it's a legal input for decisions on D+1 (or D's own close)."""
    out = df.copy()
    out["ma10"] = out[col].rolling(10).mean()
    out["ma20"] = out[col].rolling(20).mean()
    out["ma50"] = out[col].rolling(50).mean()
    out["ema200"] = out[col].ewm(span=200, adjust=False).mean()
    return out
