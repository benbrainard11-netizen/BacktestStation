"""Verify the list[Bar] port of compute_continuation_of matches the pandas original.

Loads the same NQ 1m parquet trusted_multiyear_bt.py uses, picks several entry
indices spanning early/mid/late session, runs both implementations, asserts the
feature dicts are bit-identical (or close to it for floats).

If the original isn't available (Fractal-AMD repo not present), the test skips —
it's a regression check against an external reference, not a unit test of the
port in isolation.
"""

from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

import pytest

from app.backtest.strategy import Bar
from app.features._orderflow import (
    compute_continuation_of as port_continuation_of,
)


REPO_ROOT = Path(os.environ.get("FRACTAL_AMD_REPO", r"C:\Fractal-AMD"))
DATA_PATH = REPO_ROOT / "data" / "raw" / "NQ.c.0_ohlcv-1m_2022_2025.parquet"
SRC_DIR = REPO_ROOT / "src"


@pytest.fixture(scope="module")
def reference_function():
    """Original pandas-based compute_continuation_of, imported on demand."""
    if not SRC_DIR.exists():
        pytest.skip(f"Fractal-AMD src/ not present at {SRC_DIR}")
    sys.path.insert(0, str(SRC_DIR))
    try:
        from features.order_flow import compute_continuation_of as ref
    finally:
        sys.path.remove(str(SRC_DIR))
    return ref


@pytest.fixture(scope="module")
def df_and_bars():
    """Load the same parquet trusted uses, slice to one trading day, build both
    a pandas DataFrame (for the reference) and a list[Bar] (for the port)."""
    if not DATA_PATH.exists():
        pytest.skip(f"NQ parquet not present at {DATA_PATH}")
    import pandas as pd

    full = pd.read_parquet(DATA_PATH)[
        ["open", "high", "low", "close", "volume"]
    ].copy()
    # 2024-01-03 — known to have entries in the trusted CSV.
    day_start = pd.Timestamp("2024-01-03", tz="America/New_York")
    day_end = day_start + pd.Timedelta(days=1)
    df = full.loc[day_start:day_end]
    if len(df) < 100:
        pytest.skip("not enough bars on test day")

    bars: list[Bar] = []
    for ts, row in df.iterrows():
        ts_py = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
        bars.append(
            Bar(
                ts_event=ts_py,
                symbol="NQ.c.0",
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
                trade_count=0,
                vwap=(row["open"] + row["high"] + row["low"] + row["close"]) / 4,
            )
        )
    return df, bars


@pytest.mark.parametrize("at_idx", [50, 120, 200, 350])
@pytest.mark.parametrize("direction", ["BEARISH", "BULLISH"])
def test_port_matches_reference(reference_function, df_and_bars, at_idx, direction):
    """Port must produce a feature dict bit-identical (numerically equal) to
    the pandas original on the same window."""
    df, bars = df_and_bars
    if at_idx >= len(bars) - 1:
        pytest.skip("at_idx beyond bars")

    ref = reference_function(df, at_idx, direction, lookback=15, atr=40.0)
    port = port_continuation_of(bars, at_idx, direction, lookback=15, atr=40.0)

    # Same keys present.
    assert set(ref.keys()) == set(port.keys()), (
        f"key set differs at idx={at_idx} dir={direction}: "
        f"ref-only={set(ref) - set(port)}, port-only={set(port) - set(ref)}"
    )

    # Score must match exactly (it's the only field with a hard gate).
    assert ref["co_continuation_score"] == port["co_continuation_score"], (
        f"continuation_score differs at idx={at_idx} dir={direction}: "
        f"ref={ref['co_continuation_score']} port={port['co_continuation_score']}"
    )

    # Float fields: tight tolerance (numpy, same arithmetic, should be exact).
    for k in ref:
        if isinstance(ref[k], (int, bool)):
            assert ref[k] == port[k], f"{k} differs: ref={ref[k]} port={port[k]}"
        else:
            assert ref[k] == pytest.approx(port[k], abs=1e-9, rel=1e-9), (
                f"{k} differs at idx={at_idx} dir={direction}: "
                f"ref={ref[k]} port={port[k]}"
            )
