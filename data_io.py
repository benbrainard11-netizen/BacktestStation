"""data_io — one consistent call to load anything in the warehouse.

Hides the per-dataset path / partition-key / date-format quirks so research code never hard-codes a
path. Everything returns a pandas DataFrame. Canonical inventory: docs/DATA_MANIFEST.md.

    from data_io import load_futures, load_stock, load_option_panel, load_walls, load_mbp1, load_mbo, datasets
    datasets()                                  # print the menu of what's available
    es  = load_futures("ES.c.0", "2026-06-09")  # one day (or omit date for all)
    nq  = load_futures("NQ.c.0")                 # whole history
    spx = load_option_panel("SPXW", 20250515)    # one day, all minutes/strikes (date = int YYYYMMDD)
    w   = load_walls("NDX")                      # daily gamma walls
    nvda= load_stock("NVDA")                     # 1m stock bars (tf="eod" for daily)

Index->future map: SPX/SPXW->ES, NDX/NDXP->NQ, RUT/RUTW->RTY, DJX->YM.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

D = Path(r"D:\data")
EXP = Path(__file__).resolve().parent / "experiments"

# derived gamma-wall files live in two experiment dirs; map index -> file
_WALLS = {
    "NDX": EXP / "fuhhhhh" / "out" / "walls_ndx.parquet",
    "SPX": EXP / "fuhhhhh" / "out" / "walls_v2.parquet",
    "RUT": EXP / "options_signals_v0" / "out" / "walls_rut.parquet",
    "DJX": EXP / "options_signals_v0" / "out" / "walls_djx.parquet",
}
_AUX = EXP / "options_signals_v0" / "out"


def _hive(path: Path, field: str, value):
    """Load a hive dataset, optionally filtered to one partition value."""
    dset = ds.dataset(str(path), format="parquet", partitioning="hive")
    if value is None:
        return dset.to_table().to_pandas()
    return dset.to_table(filter=ds.field(field) == value).to_pandas()


def load_futures(symbol: str, date: str | None = None) -> pd.DataFrame:
    """Futures 1-min bars. symbol e.g. 'ES.c.0'. date 'YYYY-MM-DD' (one day) or None (all). UTC clock."""
    base = D / "processed" / "bars" / "timeframe=1m" / f"symbol={symbol}"
    return pd.read_parquet(base / f"date={date}") if date else _hive(base, "date", None)


def load_stock(ticker: str, tf: str = "m1") -> pd.DataFrame:
    """Stock bars (NDX-100 universe, 2023-06+). tf='m1' (1-min, ET via ts_et) or 'eod'."""
    return pd.read_parquet(D / "processed" / "stocks" / tf / f"{ticker}.parquet")


# option panels grew past D: — they live on E: (Data2). Prefer whichever drive actually holds them,
# so tests don't care about the physical location (E: after the deep-history rebuild, D: before it).
_PANEL_BASES = [Path(r"E:\data\processed\option_panels\panel"), D / "processed" / "option_panels" / "panel"]


def _panel_base() -> Path:
    for b in _PANEL_BASES:
        if b.exists() and any(b.glob("root=*")):
            return b
    return _PANEL_BASES[-1]


def load_option_panel(root: str, date: int | None = None) -> pd.DataFrame:
    """Model-ready intraday option panel (IV/greeks/underlying/prior-OI). root e.g. 'SPXW','NDX'.
    date = int YYYYMMDD (one day) or None (whole root — large). Query by (root, date)."""
    return _hive(_panel_base() / f"root={root}", "date", date)


def load_mbp1(symbol: str, date: str | None = None) -> pd.DataFrame:
    """MBP-1 top-of-book + trades (Databento). date 'YYYY-MM-DD' or None."""
    base = D / "raw" / "databento" / "mbp-1" / f"symbol={symbol}"
    return pd.read_parquet(base / f"date={date}") if date else _hive(base, "date", None)


def load_mbo(symbol: str, trading_day: str | None = None) -> pd.DataFrame:
    """MBO full order book (Databento). NOTE the partition key is 'trading_day' (YYYY-MM-DD), not 'date'."""
    base = D / "clean" / "databento" / "mbo_trading_day" / f"symbol={symbol}"
    return (
        pd.read_parquet(base / f"trading_day={trading_day}")
        if trading_day
        else _hive(base, "trading_day", None)
    )


def load_walls(index: str) -> pd.DataFrame:
    """Daily dealer-gamma walls for an index ('NDX'/'SPX'/'RUT'/'DJX'), or a single stock ticker."""
    f = _WALLS.get(index.upper(), _AUX / f"walls_{index.lower()}.parquet")
    return pd.read_parquet(f)


def load_aux(kind: str, name: str) -> pd.DataFrame:
    """Aux EOD: kind in {'vol_indices','index_eod','dividends'}; name e.g. 'VIX','SPX','NVDA'."""
    return pd.read_parquet(_AUX / kind / f"{name}.parquet")


def datasets() -> None:
    """Print the menu of loaders + a one-line example each."""
    print("data_io loaders (all return a DataFrame):")
    print(
        "  load_futures(symbol, date=None)      futures 1m bars    e.g. load_futures('ES.c.0','2026-06-09')"
    )
    print("  load_stock(ticker, tf='m1')          stock 1m/eod       e.g. load_stock('NVDA')")
    print("  load_option_panel(root, date=None)   intraday options   e.g. load_option_panel('SPXW',20250515)")
    print("  load_mbp1(symbol, date=None)         top-of-book+trades e.g. load_mbp1('ES.c.0','2026-06-09')")
    print("  load_mbo(symbol, trading_day=None)   full order book    e.g. load_mbo('ES.c.0','2026-06-09')")
    print("  load_walls(index)                    daily gamma walls  e.g. load_walls('NDX')")
    print("  load_aux(kind, name)                 vol/index/divs     e.g. load_aux('vol_indices','VIX')")
    print("\nFull inventory + coverage: docs/DATA_MANIFEST.md")


if __name__ == "__main__":
    datasets()
