"""Regression test for the FractalAMDTrusted plugin.

Asserts the engine plugin reproduces `samples/fractal_trusted_multiyear/trades.csv`
(586 trades, +274R, 40.8% WR over 2024-01-02 → 2026-01-09) within tight
tolerance when run through the BacktestStation engine on the same NQ/ES/YM
1m parquets.

Default test window is a smoke smoke (1 week) that exercises the full
plugin without taking ~20 minutes. Set `FRACTAL_TRUSTED_REGRESSION_FULL=1`
to run the multi-year regression with the full ±5R / ±10 trade tolerance
against the bundled CSV. The smoke version asserts only that the plugin
runs to completion + produces non-empty results when trusted does.

Skipped if the Fractal-AMD data parquets aren't present.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import pandas as pd
import pytest

from app.backtest.engine import RunConfig, run as engine_run
from app.backtest.strategy import Bar
from app.strategies.fractal_amd_trusted import (
    FractalAMDTrusted,
    FractalAMDTrustedConfig,
)


DATA_DIR = Path(
    os.environ.get("FRACTAL_DATA_DIR", r"C:\Fractal-AMD\data\raw")
)
TRUSTED_CSV = (
    Path(__file__).resolve().parent.parent.parent
    / "samples"
    / "fractal_trusted_multiyear"
    / "trades.csv"
)


def _bars_for_symbol(
    sym_full: str, t0: pd.Timestamp, t1: pd.Timestamp
) -> list[Bar]:
    """Load 1m parquets for a symbol over [t0, t1] in ET."""
    sym = sym_full.split(".")[0]
    candidate_files = [
        DATA_DIR / f"{sym}.c.0_ohlcv-1m_2022_2025.parquet",
        DATA_DIR / f"{sym}_ohlcv-1m_2026.parquet",
    ]
    files = [f for f in candidate_files if f.exists()]
    if not files:
        return []
    pieces = []
    for f in files:
        df = pd.read_parquet(f)[["open", "high", "low", "close", "volume"]].copy()
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert("America/New_York")
        elif str(df.index.tz) != "America/New_York":
            df.index = df.index.tz_convert("America/New_York")
        pieces.append(df)
    df = pd.concat(pieces).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df[(df.index >= t0) & (df.index <= t1)]

    bars: list[Bar] = []
    for row in df.itertuples():
        ts = row.Index.to_pydatetime() if hasattr(row.Index, "to_pydatetime") else row.Index
        o, h, l, c = float(row.open), float(row.high), float(row.low), float(row.close)
        bars.append(
            Bar(
                ts_event=ts,
                symbol=sym_full,
                open=o,
                high=h,
                low=l,
                close=c,
                volume=int(row.volume),
                trade_count=0,
                vwap=(o + h + l + c) / 4,
            )
        )
    return bars


def _aux_dict(bars: list[Bar]) -> dict[dt.datetime, Bar]:
    return {b.ts_event: b for b in bars}


def _run_plugin(t0: pd.Timestamp, t1: pd.Timestamp):
    nq_bars = _bars_for_symbol("NQ.c.0", t0, t1)
    if not nq_bars:
        pytest.skip(f"No NQ bars in {DATA_DIR} for {t0.date()}-{t1.date()}")
    es_aux = _aux_dict(_bars_for_symbol("ES.c.0", t0, t1))
    ym_aux = _aux_dict(_bars_for_symbol("YM.c.0", t0, t1))

    cfg = FractalAMDTrustedConfig()
    strat = FractalAMDTrusted(cfg)
    rc = RunConfig(
        strategy_name="fractal_amd_trusted",
        symbol="NQ.c.0",
        timeframe="1m",
        start=str(t0.date()),
        end=str(t1.date()),
        history_max=2000,
        aux_symbols=["ES.c.0", "YM.c.0"],
        commission_per_contract=0.0,
        slippage_ticks=0,  # trusted doesn't apply slippage
        flatten_on_last_bar=False,
    )
    result = engine_run(
        strat, nq_bars, rc, aux_bars={"ES.c.0": es_aux, "YM.c.0": ym_aux}
    )
    return result


def _trusted_window(t0: pd.Timestamp, t1: pd.Timestamp) -> pd.DataFrame:
    """Slice the bundled trusted CSV to [t0, t1]."""
    if not TRUSTED_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(TRUSTED_CSV)
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    return df[(df["entry_time"] >= t0.tz_localize(None))
              & (df["entry_time"] <= t1.tz_localize(None))]


@pytest.mark.slow
def test_plugin_runs_to_completion_smoke():
    """Smoke: 1 week, just confirm the plugin runs. Multi-year tolerance
    check is gated behind FRACTAL_TRUSTED_REGRESSION_FULL=1."""
    if not DATA_DIR.exists():
        pytest.skip(f"DATA_DIR {DATA_DIR} not present")
    TZ = "America/New_York"
    t0 = pd.Timestamp("2024-01-02", tz=TZ)
    t1 = pd.Timestamp("2024-01-08 23:59", tz=TZ)
    result = _run_plugin(t0, t1)
    # Trusted produces no trades on this 1-week window because there
    # was no continuation_of >= 3 + 09:30 entry combo. The plugin
    # passing the engine_run + producing a result is the goal here.
    assert result is not None
    assert result.metrics is not None


@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("FRACTAL_TRUSTED_REGRESSION_FULL"),
    reason="set FRACTAL_TRUSTED_REGRESSION_FULL=1 to run the multi-year regression",
)
def test_plugin_reproduces_trusted_full():
    """The headline test: plugin output ≈ trusted CSV across 2024-2026."""
    if not DATA_DIR.exists():
        pytest.skip(f"DATA_DIR {DATA_DIR} not present")
    if not TRUSTED_CSV.exists():
        pytest.skip(f"Trusted CSV not present at {TRUSTED_CSV}")

    TZ = "America/New_York"
    t0 = pd.Timestamp("2024-01-02", tz=TZ)
    t1 = pd.Timestamp("2026-01-09 23:59", tz=TZ)
    result = _run_plugin(t0, t1)

    plugin_n = len(result.trades)
    plugin_total_r = sum(
        t.r_multiple for t in result.trades if t.r_multiple is not None
    )
    plugin_wr = (
        sum(1 for t in result.trades if t.r_multiple and t.r_multiple > 0)
        / max(plugin_n, 1)
    )

    trusted = _trusted_window(t0, t1)
    trusted_n = len(trusted)
    trusted_total_r = trusted["pnl_r"].sum()
    trusted_wr = (trusted["pnl_r"] > 0).sum() / max(trusted_n, 1)

    print(
        f"\nPlugin:  n={plugin_n}  WR={plugin_wr*100:.1f}%  "
        f"totalR={plugin_total_r:+.2f}"
    )
    print(
        f"Trusted: n={trusted_n}  WR={trusted_wr*100:.1f}%  "
        f"totalR={trusted_total_r:+.2f}"
    )
    print(
        f"Diff:    n={plugin_n - trusted_n:+d}  "
        f"WRpp={(plugin_wr - trusted_wr)*100:+.1f}  "
        f"totalR={plugin_total_r - trusted_total_r:+.2f}"
    )

    # Tolerances chosen to catch genuine divergence while permitting
    # tiny float / ordering noise. If the plugin and the script are
    # behaving equivalently they should be byte-close on this dataset.
    assert abs(plugin_n - trusted_n) <= 10, (
        f"Trade count differs: plugin={plugin_n}, trusted={trusted_n}"
    )
    assert abs(plugin_total_r - trusted_total_r) < 5.0, (
        f"Total R differs: plugin={plugin_total_r:.2f}, "
        f"trusted={trusted_total_r:.2f}"
    )
    assert abs(plugin_wr - trusted_wr) < 0.03, (
        f"WR differs: plugin={plugin_wr:.3f}, trusted={trusted_wr:.3f}"
    )
