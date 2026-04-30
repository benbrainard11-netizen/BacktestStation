"""Standalone characterization run for the Fractal AMD engine plug-in.

What this used to be: a regression test asserting the engine port matched
the trusted multi-year CSV at `samples/fractal_trusted_multiyear/trades.csv`
(586 trades, 40.8% WR, +274R, 2024-01-02 -> 2026-01-09).

Why it changed: on 2026-04-25 we discovered the script that produced that
CSV (`export_trades_tv.py`) does not exist in any repo or git history.
The engine port mirrors `production/live_bot.py` line-for-line, which
diverges from whatever `export_trades_tv.py` did. The Lane-C effort to
port export_trades_tv.py — `fractal_amd_trusted` — was deleted in commit
50d529e (2026-04-29) after we confirmed its +364R apparent edge was
lookahead bias and would never replicate live (see memory
`project_lane_c_trusted_port`). The trusted CSV stays as a fixture for
schema/regression validation; nothing we ship attempts to reproduce it.

What this is now: a characterization run. Drives the FractalAMD engine
plug-in over a configurable window of real NQ/ES/YM 1m parquets and
records the actual metrics the engine produces -- independent of any
trusted-CSV comparison. The test passes if the engine completes without
crashing; the metrics are written to
`backend/tests/_artifacts/fractal_engine_characterization.txt` for human
review.

Marked `slow` because even the smoke window (5 trading days) takes ~2 min
under the engine plug-in's current per-bar overhead. Skipped if
`FRACTAL_DATA_DIR` parquets are not present -- safe in CI / on freshly
cloned dev machines.

Window selection (largest wins):
  FRACTAL_REGRESSION_FULL=1     -> 2024-01-02 -> 2026-01-09 (~hours)
  FRACTAL_REGRESSION_QUARTER=1  -> Q1 2024 (~30+ min)
  default                       -> 5 trading days, smoke (~2 min)
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import pandas as pd
import pytest

from app.backtest.engine import RunConfig, run as engine_run
from app.backtest.strategy import Bar
from app.strategies.fractal_amd import FractalAMD
from app.strategies.fractal_amd.config import FractalAMDConfig


DATA_DIR = Path(
    os.environ.get(
        "FRACTAL_DATA_DIR",
        r"C:\Users\benbr\Documents\trading-bot-main\data\raw",
    )
)
ARTIFACT_DIR = Path(__file__).parent / "_artifacts"

TZ = "America/New_York"

WINDOW_FULL = (
    pd.Timestamp("2024-01-02", tz=TZ),
    pd.Timestamp("2026-01-09 23:59", tz=TZ),
)
WINDOW_Q1_2024 = (
    pd.Timestamp("2024-01-02", tz=TZ),
    pd.Timestamp("2024-03-31 23:59", tz=TZ),
)
WINDOW_SMOKE_WEEK = (
    pd.Timestamp("2024-01-02", tz=TZ),
    pd.Timestamp("2024-01-08 23:59", tz=TZ),
)


def _bars_for_symbol(
    sym_full: str, t0: pd.Timestamp, t1: pd.Timestamp
) -> list[Bar]:
    sym = sym_full.split(".")[0]
    candidate_files = [
        DATA_DIR / f"{sym}.c.0_ohlcv-1m_2022_2025.parquet",
        DATA_DIR / f"{sym}_ohlcv-1m_2026.parquet",
    ]
    files = [f for f in candidate_files if f.exists()]
    if not files:
        return []
    df = pd.concat([pd.read_parquet(f) for f in files]).sort_index()
    df = df[(df.index >= t0) & (df.index <= t1)]

    bars: list[Bar] = []
    for row in df.itertuples():
        ts = row.Index
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()
        o, h, l, c = float(row.open), float(row.high), float(row.low), float(row.close)
        bars.append(
            Bar(
                ts_event=ts,
                symbol=sym_full,
                open=o, high=h, low=l, close=c,
                volume=int(row.volume),
                trade_count=0,
                vwap=(o + h + l + c) / 4,
            )
        )
    return bars


def _aux_dict(bars: list[Bar]) -> dict[dt.datetime, Bar]:
    return {b.ts_event: b for b in bars}


def _summarize(trades) -> dict:
    rs = [t.r_multiple for t in trades if t.r_multiple is not None]
    bulls = [
        t.r_multiple for t in trades
        if t.side.value == "long" and t.r_multiple is not None
    ]
    bears = [
        t.r_multiple for t in trades
        if t.side.value == "short" and t.r_multiple is not None
    ]
    wins = [r for r in rs if r > 0]
    return {
        "count": len(trades),
        "wr": len(wins) / max(len(rs), 1),
        "total_r": sum(rs),
        "bull_r": sum(bulls),
        "bear_r": sum(bears),
        "max_r": max(rs) if rs else 0.0,
        "min_r": min(rs) if rs else 0.0,
    }


def _write_characterization(
    preset: str,
    t0: pd.Timestamp,
    t1: pd.Timestamp,
    summary: dict,
    strat: FractalAMD,
    elapsed_s: float,
    nq_bar_count: int,
) -> Path:
    ARTIFACT_DIR.mkdir(exist_ok=True)
    out = ARTIFACT_DIR / "fractal_engine_characterization.txt"

    from collections import Counter
    setup_status = Counter(s.status for s in strat.setups)

    body = (
        f"Fractal AMD engine plug-in characterization\n"
        f"  preset:    {preset}\n"
        f"  window:    {t0.date()} -> {t1.date()}\n"
        f"  nq bars:   {nq_bar_count}\n"
        f"  runtime:   {elapsed_s:.1f}s\n"
        f"\n"
        f"TRADES\n"
        f"  count:     {summary['count']}\n"
        f"  win_rate:  {summary['wr']:.2%}\n"
        f"  total R:   {summary['total_r']:+.2f}\n"
        f"  bull R:    {summary['bull_r']:+.2f}\n"
        f"  bear R:    {summary['bear_r']:+.2f}\n"
        f"  best R:    {summary['max_r']:+.2f}\n"
        f"  worst R:   {summary['min_r']:+.2f}\n"
        f"\n"
        f"INTERNAL STATE (post-run)\n"
        f"  stage signals:    {len(strat.stage_signals)}\n"
        f"  setups built:     {len(strat.setups)}\n"
        f"  setup status:     {dict(setup_status)}\n"
        f"  fully_scanned:    {len(strat._fully_scanned)}\n"
        f"  aux history:      "
        + ", ".join(
            f"{sym}={len(hist)}" for sym, hist in strat.aux_history.items()
        )
        + "\n"
    )
    out.write_text(body)
    return out


@pytest.mark.slow
def test_fractal_amd_engine_characterization():
    """Run the engine plug-in on a configurable window and record metrics.

    Passes if the engine completes without crashing. Does NOT assert on
    trade count, win rate, or PnL -- those are characterization outputs,
    not gates. Read the artifact at
    `backend/tests/_artifacts/fractal_engine_characterization.txt` for
    the actual numbers.

    The longer-term success bar is "engine port produces a recognizable
    trading strategy over multi-month windows", but evaluating that
    requires (a) optimizing the strategy's per-bar O(n) history copies
    so multi-month runs complete in reasonable time, and (b) deciding
    whether the engine port's output by itself meets the bar for paper
    or live capital -- both of which are out of scope for this test.
    """
    if not DATA_DIR.exists():
        pytest.skip(f"Data dir {DATA_DIR} not present")

    if os.environ.get("FRACTAL_REGRESSION_FULL"):
        t0, t1 = WINDOW_FULL
        preset = "FULL_2024_2026"
    elif os.environ.get("FRACTAL_REGRESSION_QUARTER"):
        t0, t1 = WINDOW_Q1_2024
        preset = "Q1_2024"
    else:
        t0, t1 = WINDOW_SMOKE_WEEK
        preset = "SMOKE_WEEK"

    nq_bars = _bars_for_symbol("NQ.c.0", t0, t1)
    if not nq_bars:
        pytest.skip(f"No NQ bars in {DATA_DIR} for {t0.date()}-{t1.date()}")
    es_aux = _aux_dict(_bars_for_symbol("ES.c.0", t0, t1))
    ym_aux = _aux_dict(_bars_for_symbol("YM.c.0", t0, t1))

    cfg = FractalAMDConfig()
    strat = FractalAMD(cfg)

    rc = RunConfig(
        strategy_name="fractal_amd",
        symbol="NQ.c.0",
        timeframe="1m",
        start=str(t0.date()),
        end=str(t1.date()),
        history_max=2000,
        aux_symbols=["ES.c.0", "YM.c.0"],
        commission_per_contract=0.0,
        slippage_ticks=1,
        flatten_on_last_bar=False,
    )

    import time
    start_t = time.monotonic()
    result = engine_run(
        strat, nq_bars, rc, aux_bars={"ES.c.0": es_aux, "YM.c.0": ym_aux}
    )
    elapsed = time.monotonic() - start_t

    summary = _summarize(result.trades)
    artifact = _write_characterization(
        preset, t0, t1, summary, strat, elapsed, len(nq_bars)
    )

    # The only structural assertion: the engine ran to completion and
    # produced a result object. Everything else is recorded in the
    # artifact for human review, not gated.
    assert result is not None, f"engine_run returned None. See {artifact}."
    assert result.metrics is not None, (
        f"No metrics dict on result. See {artifact}."
    )
