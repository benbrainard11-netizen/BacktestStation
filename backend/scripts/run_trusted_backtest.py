"""Run the TRUSTED multi-year Fractal AMD backtest from inside BacktestStation.

This is the strategy that produced `samples/fractal_trusted_multiyear/trades.csv`
(586 trades, 40.8% WR, +274R over 2024-2026). The original script lives at
`C:\\Fractal-AMD\\scripts\\trusted_multiyear_bt.py` and was thought lost on
2026-04-25; the 2026-04-28 PM session re-discovered it (it's in the original
local `Fractal-AMD` repo, not the GitHub-deployed `FractalAMD-`).

Why this script exists in BacktestStation:
- Gives you a one-command way to verify the trusted strategy still reproduces
  +274R any time. No hunting through repos.
- Acts as the reference for the eventual engine plugin port at
  `app/strategies/fractal_amd_trusted/`. When the plugin produces something
  different, this script tells you what the right answer should be.

What it does NOT do:
- Replace the engine plugin. The strategy is still imported from the original
  `C:/Fractal-AMD/src/features/` modules; we're just wrapping the canonical
  script in a place where it's discoverable. The eventual engine plugin port
  will reimplement the strategy as a proper `Strategy` subclass for live use.

Usage:
    cd backend && .venv\\Scripts\\python -m scripts.run_trusted_backtest
    # outputs to backend/tests/_artifacts/trusted_multiyear_run.csv

Environment overrides:
    FRACTAL_AMD_REPO    default C:/Fractal-AMD/
    TRUSTED_START_DATE  default 2024-01-01
    TRUSTED_END_DATE    default 2026-03-31
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path


def main() -> int:
    repo_root = Path(os.environ.get("FRACTAL_AMD_REPO", r"C:\Fractal-AMD"))
    start_date = os.environ.get("TRUSTED_START_DATE", "2024-01-01")
    end_date = os.environ.get("TRUSTED_END_DATE", "2026-03-31")

    src_dir = repo_root / "src"
    data_dir = repo_root / "data" / "raw"

    if not src_dir.exists():
        print(f"ERROR: Fractal-AMD src/ not found at {src_dir}.", file=sys.stderr)
        print(
            "Set FRACTAL_AMD_REPO env var to the repo root.", file=sys.stderr
        )
        return 1
    if not data_dir.exists():
        print(f"ERROR: Fractal-AMD data/raw/ not found at {data_dir}.", file=sys.stderr)
        return 1

    sys.path.insert(0, str(src_dir))

    import pandas as pd
    from features.candle_patterns import detect_rejection
    from features.fvg_detector import (
        detect_fvgs,
        find_nearest_unfilled_fvg,
        resample_bars,
    )
    from features.order_flow import compute_continuation_of
    from features.smt_detector import detect_smt_at_level
    from features.stage_detector import _candle_bounds, _get_ohlc

    BUFFER = 5
    MAX_HOLD = 120

    def load_symbol(symbol: str) -> pd.DataFrame:
        hist_path = data_dir / f"{symbol}.c.0_ohlcv-1m_2022_2025.parquet"
        recent_path = data_dir / f"{symbol}_ohlcv-1m_2026.parquet"
        hist = pd.read_parquet(hist_path)[
            ["open", "high", "low", "close", "volume"]
        ].copy()
        recent = pd.read_parquet(recent_path)[
            ["open", "high", "low", "close", "volume"]
        ].copy()
        recent.index = recent.index.tz_convert("America/New_York")
        df = pd.concat([hist, recent])
        df = df[~df.index.duplicated(keep="first")].sort_index()
        return df

    print(f"Loading data from {data_dir}...")
    t0 = time.time()
    nq = load_symbol("NQ")
    es = load_symbol("ES")
    ym = load_symbol("YM")
    print(f"  loaded in {time.time() - t0:.1f}s | NQ {len(nq):,} bars")

    mask_start = pd.Timestamp(start_date, tz="America/New_York") - pd.Timedelta(
        days=2
    )
    mask_end = pd.Timestamp(end_date, tz="America/New_York") + pd.Timedelta(days=1)
    nq = nq.loc[mask_start:mask_end]
    es = es.loc[mask_start:mask_end]
    ym = ym.loc[mask_start:mask_end]
    print(f"  trimmed to {start_date}..{end_date} | NQ {len(nq):,} bars")

    def find_ltf_smt(nq_d, es_d, ym_d, exp_s, exp_e, d, day):
        for tf, mins in [("15m", 15), ("5m", 5)]:
            candles = _candle_bounds(day, tf)
            rel = [
                (s, e)
                for s, e in candles
                if s >= exp_s and e <= exp_e + pd.Timedelta(minutes=1)
            ]
            for i in range(1, len(rel)):
                cs, ce = rel[i]
                rs, re = rel[i - 1]
                ro = {}
                for lb, dfa in [("nq", nq_d), ("es", es_d), ("ym", ym_d)]:
                    ro[lb] = _get_ohlc(dfa, rs, re)
                if any(v is None for v in ro.values()):
                    continue
                bc = {
                    "nq": nq_d.loc[(nq_d.index >= cs) & (nq_d.index < ce)],
                    "es": es_d.loc[(es_d.index >= cs) & (es_d.index < ce)],
                    "ym": ym_d.loc[(ym_d.index >= cs) & (ym_d.index < ce)],
                }
                if any(len(b) == 0 for b in bc.values()):
                    continue
                if d == "BEARISH":
                    lv = {k: v["high"] for k, v in ro.items()}
                    s = detect_smt_at_level(bc, lv, "high", cs, ce)
                    if s.has_smt and s.direction == "BEARISH":
                        return [
                            {
                                "tf": tf,
                                "tf_min": mins,
                                "ref_start": rs,
                                "candle_end": ce,
                            }
                        ]
                else:
                    lv = {k: v["low"] for k, v in ro.items()}
                    s = detect_smt_at_level(bc, lv, "low", cs, ce)
                    if s.has_smt and s.direction == "BULLISH":
                        return [
                            {
                                "tf": tf,
                                "tf_min": mins,
                                "ref_start": rs,
                                "candle_end": ce,
                            }
                        ]
        return []

    dates = sorted(set(nq.index.normalize().strftime("%Y-%m-%d")))
    dates = [d for d in dates if start_date <= d <= end_date]
    trades: list[dict] = []
    print(f"\nRunning trusted backtest on {len(dates)} days...")
    t0 = time.time()
    progress = max(1, len(dates) // 20)

    for di, date in enumerate(dates):
        if di % progress == 0:
            print(
                f"  day {di}/{len(dates)} ({date}) "
                f"{time.time() - t0:.0f}s elapsed | {len(trades)} trades"
            )
        try:
            day = pd.Timestamp(date, tz="America/New_York")
            prev = day - pd.Timedelta(days=1)
            nq_d = nq.loc[prev.replace(hour=18) : day.replace(hour=17)]
            es_d = es.loc[prev.replace(hour=18) : day.replace(hour=17)]
            ym_d = ym.loc[prev.replace(hour=18) : day.replace(hour=17)]
            if len(nq_d) < 60:
                continue

            htf_stages = []
            for tf in ["session", "1H"]:
                candles = _candle_bounds(day, tf)
                for i in range(1, len(candles)):
                    cs, ce = candles[i]
                    rs, re = candles[i - 1]
                    rejs = detect_rejection(nq_d, es_d, ym_d, cs, ce, rs, re, tf)
                    smts = []
                    ro = {}
                    for lb, dfa in [("nq", nq_d), ("es", es_d), ("ym", ym_d)]:
                        ro[lb] = _get_ohlc(dfa, rs, re)
                    if all(v is not None for v in ro.values()):
                        bc = {
                            "nq": nq_d.loc[(nq_d.index >= cs) & (nq_d.index < ce)],
                            "es": es_d.loc[(es_d.index >= cs) & (es_d.index < ce)],
                            "ym": ym_d.loc[(ym_d.index >= cs) & (ym_d.index < ce)],
                        }
                        if all(len(b) > 0 for b in bc.values()):
                            hl = {k: v["high"] for k, v in ro.items()}
                            s = detect_smt_at_level(bc, hl, "high", cs, ce)
                            if s.has_smt and s.direction == "BEARISH":
                                smts.append("BEARISH")
                            ll = {k: v["low"] for k, v in ro.items()}
                            s = detect_smt_at_level(bc, ll, "low", cs, ce)
                            if s.has_smt and s.direction == "BULLISH":
                                smts.append("BULLISH")
                    for d in ["BEARISH", "BULLISH"]:
                        hs = d in smts
                        hr = any(r.direction == d for r in rejs)
                        if hs or hr:
                            htf_stages.append(
                                {
                                    "tf": tf,
                                    "direction": d,
                                    "candle_start": cs,
                                    "candle_end": ce,
                                }
                            )

            rth_s = day.replace(hour=9, minute=30)
            rth_e = day.replace(hour=16)
            entries_today: set = set()
            n_today = 0

            for stage in htf_stages:
                direction = stage["direction"]
                exp_s = stage["candle_end"]
                dur = stage["candle_end"] - stage["candle_start"]
                exp_e = exp_s + dur * 2
                sc_s = max(exp_s, rth_s)
                sc_e = min(exp_e, rth_e)
                if sc_s >= sc_e:
                    continue

                ltf_sigs = find_ltf_smt(nq_d, es_d, ym_d, exp_s, exp_e, direction, day)
                if not ltf_sigs:
                    continue

                for ltf in ltf_sigs:
                    le = ltf["candle_end"]
                    lm = ltf["tf_min"]
                    fss = ltf["ref_start"]
                    fse = min(le + pd.Timedelta(minutes=lm * 5), rth_e)
                    s1m = nq_d.loc[(nq_d.index >= fss) & (nq_d.index < fse)]
                    if len(s1m) < lm * 3:
                        continue
                    ltf_bars = resample_bars(s1m, lm)
                    if len(ltf_bars) < 3:
                        continue
                    fvgs = detect_fvgs(
                        ltf_bars, direction, min_gap_pct=0.3, expiry_bars=60
                    )
                    if not fvgs:
                        continue

                    ess = max(le, rth_s)
                    ese = min(le + pd.Timedelta(minutes=60 * lm), rth_e)
                    eb = nq_d.loc[(nq_d.index >= ess) & (nq_d.index < ese)]
                    if len(eb) < 5:
                        continue

                    waiting = False
                    pending = None
                    for j in range(len(eb)):
                        bt = eb.index[j]
                        bar = eb.iloc[j]
                        bcl = float(bar["close"])
                        bhv = float(bar["high"])
                        blv = float(bar["low"])
                        bsi = int((bt - fss).total_seconds() / 60 / lm)

                        if waiting and pending is not None:
                            ep = float(bar["open"])
                            et = bt
                            if et.hour < 9 or et.hour >= 14:
                                waiting = False
                                pending = None
                                continue
                            ek = (direction, et.floor("15min"))
                            if ek in entries_today:
                                waiting = False
                                pending = None
                                continue
                            if n_today >= 2:
                                waiting = False
                                pending = None
                                continue
                            ai = nq_d.index.get_loc(et)
                            if isinstance(ai, slice):
                                ai = ai.start
                            co = compute_continuation_of(
                                nq_d, ai, direction, lookback=15, atr=40.0
                            )
                            cos = co.get("co_continuation_score", 0) if co else 0
                            if cos < 3:
                                waiting = False
                                pending = None
                                continue

                            if direction == "BEARISH":
                                stop = pending.high + BUFFER
                                risk = stop - ep
                            else:
                                stop = pending.low - BUFFER
                                risk = ep - stop
                            if risk <= 0 or risk > 150:
                                waiting = False
                                pending = None
                                continue

                            eig = nq.index.get_loc(et)
                            if isinstance(eig, slice):
                                eig = eig.start
                            xr = "timeout"
                            pr = 0.0
                            exit_time = et
                            exit_price = ep
                            for k in range(
                                eig + 1, min(eig + MAX_HOLD + 1, len(nq))
                            ):
                                kh = float(nq.iloc[k]["high"])
                                kl = float(nq.iloc[k]["low"])
                                if direction == "BEARISH":
                                    if kh >= stop:
                                        xr = "SL"
                                        pr = -1.0
                                        exit_price = stop
                                        exit_time = nq.index[k]
                                        break
                                    if kl <= ep - risk * 3:
                                        xr = "3R"
                                        pr = 3.0
                                        exit_price = ep - risk * 3
                                        exit_time = nq.index[k]
                                        break
                                else:
                                    if kl <= stop:
                                        xr = "SL"
                                        pr = -1.0
                                        exit_price = stop
                                        exit_time = nq.index[k]
                                        break
                                    if kh >= ep + risk * 3:
                                        xr = "3R"
                                        pr = 3.0
                                        exit_price = ep + risk * 3
                                        exit_time = nq.index[k]
                                        break
                            if xr == "timeout":
                                li = min(eig + MAX_HOLD, len(nq) - 1)
                                exit_price = float(nq.iloc[li]["close"])
                                exit_time = nq.index[li]
                                pr = (
                                    (ep - exit_price) / risk
                                    if direction == "BEARISH"
                                    else (exit_price - ep) / risk
                                )

                            trades.append(
                                {
                                    "entry_time": et,
                                    "entry_price": ep,
                                    "exit_time": exit_time,
                                    "exit_price": exit_price,
                                    "stop": stop,
                                    "tp": (
                                        ep - risk * 3
                                        if direction == "BEARISH"
                                        else ep + risk * 3
                                    ),
                                    "risk": risk,
                                    "direction": direction,
                                    "exit_reason": xr,
                                    "pnl_r": pr,
                                    "fvg_high": pending.high,
                                    "fvg_low": pending.low,
                                }
                            )
                            entries_today.add(ek)
                            n_today += 1
                            waiting = False
                            pending = None
                            break

                        waiting = False
                        pending = None
                        nearest = find_nearest_unfilled_fvg(fvgs, bcl, bsi, 60)
                        if nearest is None:
                            continue
                        entered = False
                        if direction == "BULLISH":
                            if blv <= nearest.high and bhv >= nearest.low:
                                entered = True
                        else:
                            if bhv >= nearest.low and blv <= nearest.high:
                                entered = True
                        if entered:
                            waiting = True
                            pending = nearest
        except Exception:
            pass

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s — {len(trades)} total trades")

    if not trades:
        print("NO TRADES.")
        return 0

    df = pd.DataFrame(trades)
    wins = (df["pnl_r"] > 0).sum()
    total_r = df["pnl_r"].sum()
    cum = df["pnl_r"].cumsum()
    max_dd = (cum - cum.cummax()).min()
    print()
    print("=" * 70)
    print(
        f"OVERALL: {len(df)} trades | {wins / len(df) * 100:.1f}% WR | "
        f"{total_r:+.1f}R | avg {df['pnl_r'].mean():+.2f}R | maxDD {max_dd:.1f}R"
    )
    print("=" * 70)

    artifact_dir = Path(__file__).resolve().parent.parent / "tests" / "_artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    out_path = artifact_dir / "trusted_multiyear_run.csv"
    out = df.copy()
    out["entry_time"] = out["entry_time"].dt.strftime("%Y-%m-%d %H:%M")
    out["exit_time"] = out["exit_time"].dt.strftime("%Y-%m-%d %H:%M")
    out.to_csv(out_path, index=False)
    print(f"Wrote trades to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
