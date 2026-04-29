"""Diagnostic: how much of plug's edge depends on the +1-bar lookahead in
the CO gate?

Runs plug Jan 2026 in two modes:
  - co_lookahead=True   (default, trusted-faithful — CO scored at entry bar)
  - co_lookahead=False  (live-faithful — CO scored at touch bar)

For each mode, records every CO-gate evaluation (passed and failed), the
score, and the bar it was scored at. Then reports:
  1. Plug trade-list under each mode (count, WR, total R)
  2. Plug score distribution at the gate (how many at CO=3, =4, =5+)
  3. How many trades "survive" both modes (i.e., didn't depend on lookahead)
  4. Day-by-day comparison vs the live bot harness CSV

This tells us: is the trusted edge fragile to ±1 bar of CO data, or robust?
"""
from __future__ import annotations

import datetime as dt
import os
from collections import Counter
from pathlib import Path

import pandas as pd

from app.backtest.engine import RunConfig, run as engine_run
from app.backtest.strategy import Bar
from app.strategies.fractal_amd_trusted import (
    FractalAMDTrusted,
    FractalAMDTrustedConfig,
)


DATA_DIR = Path(os.environ.get("FRACTAL_DATA_DIR", r"C:\Fractal-AMD\data\raw"))
TZ = "America/New_York"
T0 = pd.Timestamp(os.environ.get("CO_T0", "2026-01-02"), tz=TZ)
T1 = pd.Timestamp(os.environ.get("CO_T1", "2026-01-31") + " 23:59", tz=TZ)
_LB_T0 = os.environ.get("CO_T0", "2026-01-02")
_LB_T1 = os.environ.get("CO_T1", "2026-01-31")
LIVE_BOT_OUT = Path(
    f"C:/Fractal-AMD/outputs/live_engine_bt_{_LB_T0}_{_LB_T1}__val_930.csv"
)


def _bars(sym, t0, t1):
    s = sym.split(".")[0]
    files = [
        DATA_DIR / f"{s}.c.0_ohlcv-1m_2022_2025.parquet",
        DATA_DIR / f"{s}_ohlcv-1m_2026.parquet",
    ]
    pieces = []
    for f in files:
        if not f.exists():
            continue
        df = pd.read_parquet(f)[["open", "high", "low", "close", "volume"]].copy()
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(TZ)
        elif str(df.index.tz) != TZ:
            df.index = df.index.tz_convert(TZ)
        pieces.append(df)
    df = pd.concat(pieces).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df[(df.index >= t0) & (df.index <= t1)]
    out = []
    for row in df.itertuples():
        ts = row.Index.to_pydatetime() if hasattr(row.Index, "to_pydatetime") else row.Index
        o, h, l, c = float(row.open), float(row.high), float(row.low), float(row.close)
        out.append(Bar(
            ts_event=ts, symbol=sym, open=o, high=h, low=l, close=c,
            volume=int(row.volume), trade_count=0, vwap=(o + h + l + c) / 4,
        ))
    return out


def run_plug(co_lookahead: bool):
    """Run plug Jan 2026 with the chosen CO timing. Returns (trades_df,
    co_log) where co_log is a list of (entry_ts, direction, co_score,
    accepted_by_gate) tuples for EVERY entry attempt (gated and ungated).
    """
    nq = _bars("NQ.c.0", T0, T1)
    es = {b.ts_event: b for b in _bars("ES.c.0", T0, T1)}
    ym = {b.ts_event: b for b in _bars("YM.c.0", T0, T1)}
    cfg = FractalAMDTrustedConfig(co_lookahead=co_lookahead)
    strat = FractalAMDTrusted(cfg)

    # Wrap _try_enter to record every CO-checked entry attempt with its
    # score. Strategy's _try_enter sets self._last_co_score before the
    # gate test; we read it immediately after the call returns.
    co_log: list[tuple] = []
    original_try_enter = strat._try_enter

    def wrapped_try_enter(setup, bar, context):
        intent = original_try_enter(setup, bar, context)
        score = getattr(strat, "_last_co_score", None)
        if score is not None:
            co_log.append((
                bar.ts_event,
                setup.stage.direction,
                int(score),
                intent is not None,
            ))
            strat._last_co_score = None  # one-shot read
        return intent

    strat._try_enter = wrapped_try_enter

    rc = RunConfig(
        strategy_name="fractal_amd_trusted",
        symbol="NQ.c.0", timeframe="1m",
        start=str(T0.date()), end=str(T1.date()),
        history_max=2000, aux_symbols=["ES.c.0", "YM.c.0"],
        commission_per_contract=0.0, slippage_ticks=0,
        flatten_on_last_bar=False,
    )
    result = engine_run(strat, nq, rc, aux_bars={"ES.c.0": es, "YM.c.0": ym})

    rows = []
    for t in result.trades:
        ts = pd.Timestamp(t.entry_ts)
        if ts.tzinfo is None:
            ts = ts.tz_localize(TZ)
        else:
            ts = ts.tz_convert(TZ)
        rows.append({
            "entry_ts": ts,
            "direction": "BEARISH" if t.side.value == "short" else "BULLISH",
            "pnl_r": t.r_multiple,
        })
    return pd.DataFrame(rows), co_log


def summarize_trades(label: str, df: pd.DataFrame):
    if df.empty:
        print(f"{label}: 0 trades")
        return
    print(f"{label}: {len(df)} trades  WR={(df.pnl_r>0).mean()*100:.1f}%  totalR={df.pnl_r.sum():+.2f}")


def co_distribution(label: str, co_log: list[tuple]):
    """How many gate evaluations landed at each score? Borderline-3 vs 4 vs 5+?"""
    if not co_log:
        print(f"{label}: empty co_log")
        return
    accepted = [s for (_, _, s, ok) in co_log if ok]
    rejected = [s for (_, _, s, ok) in co_log if not ok]
    print(f"\n{label} CO gate evaluations:")
    print(f"  total checks: {len(co_log)}  passed: {len(accepted)}  rejected: {len(rejected)}")
    if accepted:
        c = Counter(accepted)
        print(f"  accepted scores: {dict(sorted(c.items()))}")
        borderline = sum(c[s] for s in c if s in (3, 4))
        comfortable = sum(c[s] for s in c if s >= 5)
        print(f"    borderline (3-4): {borderline}/{len(accepted)} = {borderline/len(accepted)*100:.0f}%")
        print(f"    comfortable (5+): {comfortable}/{len(accepted)} = {comfortable/len(accepted)*100:.0f}%")
    if rejected:
        c = Counter(rejected)
        print(f"  rejected scores: {dict(sorted(c.items()))}")


def day_compare(label_a: str, df_a: pd.DataFrame, label_b: str, df_b: pd.DataFrame, *, verbose=False):
    if df_a.empty and df_b.empty:
        print(f"\n{label_a} vs {label_b}: both empty")
        return
    if df_a.empty:
        df_a = pd.DataFrame(columns=["entry_ts", "direction", "pnl_r"])
    if df_b.empty:
        df_b = pd.DataFrame(columns=["entry_ts", "direction", "pnl_r"])
    a = df_a.copy()
    b = df_b.copy()
    a["day"] = a.entry_ts.dt.date
    b["day"] = b.entry_ts.dt.date
    a_by = a.groupby("day").size()
    b_by = b.groupby("day").size()
    days = sorted(set(a_by.index) | set(b_by.index))
    diffs = 0
    for day in days:
        na = a_by.get(day, 0)
        nb = b_by.get(day, 0)
        if na != nb:
            diffs += 1
            if verbose:
                p_today = a[a.day == day]
                l_today = b[b.day == day]
                p_str = "; ".join(
                    f"{r.entry_ts.strftime('%H:%M')} {r.direction[:4]} R={r.pnl_r:+.1f}"
                    for _, r in p_today.iterrows()
                )
                l_str = "; ".join(
                    f"{r.entry_ts.strftime('%H:%M')} {r.direction[:4]} R={r.pnl_r:+.1f}"
                    for _, r in l_today.iterrows()
                )
                print(f"  {day} ({label_a}={na} {label_b}={nb})")
                print(f"    {label_a}: {p_str or '(none)'}")
                print(f"    {label_b}: {l_str or '(none)'}")
    print(f"\n{label_a} vs {label_b} day-by-day: {diffs}/{len(days)} divergent days")


def main():
    print("=" * 72)
    print(f"CO LOOKAHEAD DIAGNOSTIC  Jan 2026")
    print("=" * 72)

    print("\n>>> Running plug WITH lookahead (trusted-faithful)...")
    plug_la, log_la = run_plug(co_lookahead=True)
    summarize_trades("plug_lookahead", plug_la)

    print("\n>>> Running plug WITHOUT lookahead (live-faithful, CO at touch bar)...")
    plug_no, log_no = run_plug(co_lookahead=False)
    summarize_trades("plug_no_lookahead", plug_no)

    co_distribution("plug_lookahead", log_la)
    co_distribution("plug_no_lookahead", log_no)

    print("\n" + "=" * 72)
    print("TRADE OVERLAP")
    print("=" * 72)
    if plug_la.empty or plug_no.empty:
        print("(at least one mode had 0 trades — skipping overlap)")
    else:
        # Match on (day, direction, pnl_r) — same trade if it hit the same way
        # on the same day in the same direction. Looser than entry-ts match
        # since +/-1 minute drift is expected from CO timing change.
        la_keys = {
            (r.entry_ts.date(), r.direction, round(r.pnl_r, 2))
            for _, r in plug_la.iterrows()
        }
        no_keys = {
            (r.entry_ts.date(), r.direction, round(r.pnl_r, 2))
            for _, r in plug_no.iterrows()
        }
        overlap = la_keys & no_keys
        only_la = la_keys - no_keys
        only_no = no_keys - la_keys
        print(f"  plug_lookahead trades:    {len(la_keys)}")
        print(f"  plug_no_lookahead trades: {len(no_keys)}")
        print(f"  overlap (same day/dir/R): {len(overlap)}")
        print(f"  only in plug_lookahead:    {len(only_la)}")
        print(f"  only in plug_no_lookahead: {len(only_no)}")

    # vs live bot harness output
    if LIVE_BOT_OUT.exists():
        lb = pd.read_csv(LIVE_BOT_OUT)
        lb["entry_ts"] = pd.to_datetime(lb["date"] + " " + lb["entry_time"]).dt.tz_localize(TZ)
        lb = lb[["entry_ts", "direction", "pnl_r"]]
        print("\n" + "=" * 72)
        print("DAY-BY-DAY DIVERGENCE vs LIVE BOT")
        print("=" * 72)
        summarize_trades("live_bot       ", lb)
        day_compare("plug_lookahead   ", plug_la, "live_bot         ", lb)
        print()
        print(">>> plug_no_lookahead vs live_bot — DETAIL (this should match if CO timing is the only diff)")
        day_compare("plug_no_la", plug_no, "live_bot  ", lb, verbose=True)

    print("\nInterpretation:")
    print("  - If plug_no_lookahead has similar R/WR to plug_lookahead,")
    print("    the trusted edge is robust and live can match it.")
    print("  - If most accepted plug_lookahead trades have CO=3,")
    print("    the gate is on a knife's edge; one bar of data flips many calls.")
    print("  - If plug_no_lookahead matches the live bot output by day,")
    print("    we have the fix: tell plug to drop lookahead and live = plug.")


if __name__ == "__main__":
    main()
