"""Read OHLCV 1-min parquet files from the Fractal local archive.

Never writes. Two parquet files per symbol cover the life of the data
archive (2022-2025 historical + 2026 rolling). Both are concatenated and
trimmed to the requested window.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.paths import fractal_ohlcv_dir


class CandlesUnavailableError(Exception):
    """Raised when OHLCV files for a symbol cannot be located/read."""


def _paths_for_symbol(symbol: str) -> list[Path]:
    root = fractal_ohlcv_dir()
    symbol = symbol.upper()
    candidates = [
        root / f"{symbol}.c.0_ohlcv-1m_2022_2025.parquet",
        root / f"{symbol}_ohlcv-1m_2026.parquet",
        # Fallback: any file matching the pattern (future years etc.)
    ]
    return [p for p in candidates if p.exists()]


def load_ohlcv_1m(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Return a DataFrame of 1-min bars for `symbol` covering `[start, end]`.

    Index is the bar open timestamp (tz-aware, America/New_York). Columns:
    open, high, low, close, volume.
    """
    paths = _paths_for_symbol(symbol)
    if not paths:
        raise CandlesUnavailableError(
            f"No OHLCV parquet files for {symbol} in {fractal_ohlcv_dir()}"
        )

    frames: list[pd.DataFrame] = []
    for path in paths:
        try:
            df = pd.read_parquet(path, columns=None)
        except Exception as exc:
            raise CandlesUnavailableError(f"Failed to read {path}: {exc}") from exc
        frames.append(df)

    combined = pd.concat(frames)
    combined = combined[~combined.index.duplicated(keep="first")].sort_index()

    # Normalize timezone to America/New_York. Files vary: 2022-2025 is ET,
    # 2026 file arrives UTC in the Fractal pipeline.
    combined = _normalize_tz(combined)

    # Keep only the requested window (buffered by ±1 day for gap detection
    # at the edges).
    window_start = pd.Timestamp(start, tz=combined.index.tz) - pd.Timedelta(days=1)
    window_end = pd.Timestamp(end, tz=combined.index.tz) + pd.Timedelta(days=1)
    return combined.loc[window_start:window_end]


def _normalize_tz(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the index is tz-aware in America/New_York."""
    if df.index.tz is None:
        # Older files may be naive-local or naive-utc. Safest assumption:
        # UTC, then convert.
        df.index = df.index.tz_localize("UTC").tz_convert("America/New_York")
    elif str(df.index.tz) != "America/New_York":
        df.index = df.index.tz_convert("America/New_York")
    return df


def available_symbols() -> list[str]:
    """Best-effort inventory of which symbols have OHLCV parquet files."""
    root = fractal_ohlcv_dir()
    if not root.exists():
        return []
    symbols: set[str] = set()
    for path in root.iterdir():
        name = path.name
        if "_ohlcv-1m" not in name:
            continue
        # e.g. NQ.c.0_ohlcv-1m_2022_2025.parquet or NQ_ohlcv-1m_2026.parquet
        base = name.split("_ohlcv-1m")[0]
        symbols.add(base.split(".")[0].upper())
    return sorted(symbols)


def count_bars_in_range(
    df: pd.DataFrame, start: datetime, end: datetime
) -> dict[str, Any]:
    """Small summary of a candle slice: total bars, first/last timestamp."""
    if df.empty:
        return {"total_bars": 0, "first_ts": None, "last_ts": None}
    window = df.loc[
        pd.Timestamp(start, tz=df.index.tz) : pd.Timestamp(end, tz=df.index.tz)
    ]
    return {
        "total_bars": int(len(window)),
        "first_ts": window.index.min().isoformat() if len(window) else None,
        "last_ts": window.index.max().isoformat() if len(window) else None,
    }
