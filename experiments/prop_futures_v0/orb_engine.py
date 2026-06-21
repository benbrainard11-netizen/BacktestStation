"""orb_engine — honest, day-flat opening-range-breakout / range-expansion backtester.

Research-grade, vectorized-per-day. Built for prop_futures_v0 Phase C. Mirrors the canonical
broker fill rules (backend/app/backtest/broker.py) so results are comparable to the engine:

  * Breakout entry: a buy-stop at OR_high+buffer (sell-stop at OR_low-buffer). It triggers on the
    first RTH bar (after the OR window, before the cutoff) whose high>=trigger (low<=trigger).
    Fill = trigger + slip for longs, gap-aware: if the bar OPENS beyond the trigger, fill at the
    open (worse) + slip. NO look at any future bar to decide the fill.
  * Stop/target: bracket checked bar-by-bar from the ENTRY bar onward. If a single bar touches
    BOTH stop and target -> CONSERVATIVE, stop wins (CLAUDE.md rule 8). Stop fills slip 1 tick
    worse; target is a resting limit (no slip); EOD flatten fills at the session-close bar close.
  * Day-flat: any open position is force-closed at the last RTH bar of the session.
  * Costs: entry slip + stop slip (in the fill prices) + round-trip commission (subtracted in $).
    R is measured against the REALISED initial risk (entry_fill -> stop), so cost-in-R scales with
    the stop size honestly.

The vol GATE is strictly causal: proxies are 'or_width' (the OR range itself, known at OR close)
or 'prior_atr' (mean RTH range over the prior N trading days). The gate THRESHOLD must be derived
on the design window only and passed in (gate_threshold) — the engine just applies proxy>=thr.

CLI self-test:  python orb_engine.py --selftest
Single run:     python orb_engine.py --symbol CL.c.0 --start 2016-01-01 --end 2025-06-09
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

# canonical specs (CLAUDE.md rule 7) — CL/NG/MCL added there for this study
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
try:
    from app.backtest.instruments import lookup as _spec_lookup
except Exception:  # pragma: no cover - fallback if path differs
    _spec_lookup = None

BARS_ROOT = Path(r"D:\data\processed\bars\timeframe=1m")
ET = "America/New_York"


@dataclass(frozen=True)
class Spec:
    tick_size: float
    contract_value: float  # $ per point per contract
    commission_per_contract: float = 2.0  # round-trip $

    @property
    def tick_value(self) -> float:
        return self.tick_size * self.contract_value


def get_spec(symbol: str) -> Spec:
    if _spec_lookup is not None:
        s = _spec_lookup(symbol)
        if s is not None:
            return Spec(s.tick_size, s.contract_value, s.commission_per_contract)
    raise ValueError(f"no spec for {symbol}; add it to backend/app/backtest/instruments.py")


@dataclass(frozen=True)
class ORBConfig:
    or_minutes: int = 15           # opening-range length
    entry_cutoff_min: int = 150    # minutes after open to stop taking NEW breakouts (150 -> 12:00)
    buffer_ticks: int = 1          # break must exceed OR edge by this many ticks
    stop_mode: str = "opp_or"      # "opp_or" (other OR edge) | "or_frac" (frac*OR_width from entry)
    stop_or_frac: float = 1.0
    target_R: float = 1.0          # target = entry +/- target_R*risk; <=0 -> EOD-only exit
    direction: str = "both"        # "both" | "long" | "short"
    slip_ticks: int = 1            # adverse slip on entry and on stop exits
    session_open: str = "09:30"
    session_close: str = "16:00"
    vol_gate: str = "none"         # "none" | "or_width" | "prior_atr"
    gate_threshold: float = float("nan")  # absolute proxy threshold (ticks); derived on design data


# ----------------------------------------------------------------------------- data

def build_dataset(symbol: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """Load 1m bars, convert to ET, tag ET calendar date + minutes-from-midnight. 24h kept."""
    base = BARS_ROOT / f"symbol={symbol}"
    df = pd.read_parquet(base, columns=["ts_event", "open", "high", "low", "close", "volume"])
    df = df.dropna(subset=["open", "high", "low", "close"]).sort_values("ts_event")
    ts = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert(ET)
    df["et"] = ts
    df["date_et"] = ts.dt.normalize()
    df["mod"] = ts.dt.hour * 60 + ts.dt.minute  # minute-of-day, ET
    if start:
        df = df[df["date_et"] >= pd.Timestamp(start, tz=ET)]
    if end:
        df = df[df["date_et"] <= pd.Timestamp(end, tz=ET)]
    return df.reset_index(drop=True)


def _hhmm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


# ----------------------------------------------------------------------------- per-day

def _rth_day_ranges(df: pd.DataFrame, open_m: int, close_m: int) -> pd.Series:
    """Per-ET-date RTH range (high-low) in price, for the prior-ATR proxy."""
    rth = df[(df["mod"] >= open_m) & (df["mod"] < close_m)]
    g = rth.groupby("date_et")
    return (g["high"].max() - g["low"].min())


def simulate_trade(m, o, hi, lo, cl, ei, is_long, entry, stop, target, use_target, slip_px, spec,
                   close_m, start_at_entry=False):
    """Honest day-flat trade management (CLAUDE.md rule 8). Shared by run_orb and families.py.

    Manages from the bar AFTER entry (ei+1) to the last RTH bar (< close_m). Single bar touching
    BOTH stop and target -> conservative STOP. Stop slips adversely; target is a resting limit (no
    slip); EOD flatten at the last RTH close. Returns a trade dict, or None if risk is degenerate.
    The entry bar is skipped (OHLC can't order the intrabar path) — verified not load-bearing for
    breakout entries. For a FADE entered AT a breakout level with a tight stop just beyond, the
    breakout bar can blow through the stop intrabar, so pass start_at_entry=True to check the entry
    bar's range too (honest — does not flatter the fade).
    """
    eod_idx = np.flatnonzero(m < close_m)
    last_i = eod_idx[-1] if len(eod_idx) else ei
    exit_price = None
    reason = None
    for j in range(ei if start_at_entry else ei + 1, last_i + 1):
        stop_hit = lo[j] <= stop <= hi[j]
        tgt_hit = use_target and (lo[j] <= target <= hi[j])
        if stop_hit and tgt_hit:
            exit_price, reason = stop - slip_px * (1 if is_long else -1), "stop_ambig"  # conservative
            break
        if stop_hit:
            exit_price, reason = stop - slip_px * (1 if is_long else -1), "stop"
            break
        if tgt_hit:
            exit_price, reason = target, "target"  # resting limit, no slip
            break
    if exit_price is None:
        exit_price, reason = cl[last_i], "eod"  # day-flat
    gross_pts = (exit_price - entry) if is_long else (entry - exit_price)
    risk_pts = (entry - stop) if is_long else (stop - entry)
    if risk_pts <= 0:
        return None
    net_dollars = gross_pts * spec.contract_value - spec.commission_per_contract
    return {"entry": entry, "stop": stop, "target": target if use_target else np.nan,
            "exit": exit_price, "reason": reason, "risk_ticks": risk_pts / spec.tick_size,
            "gross_R": gross_pts / risk_pts, "net_R": net_dollars / (risk_pts * spec.contract_value),
            "net_dollars": net_dollars}


def run_orb(df: pd.DataFrame, spec: Spec, cfg: ORBConfig) -> pd.DataFrame:
    """Run the ORB family over all days in df. Returns one row per TRADE (no-trade days omitted)."""
    tick = spec.tick_size
    open_m = _hhmm(cfg.session_open)
    close_m = _hhmm(cfg.session_close)
    or_end_m = open_m + cfg.or_minutes
    cutoff_m = open_m + cfg.entry_cutoff_min
    buf = cfg.buffer_ticks * tick
    slip = cfg.slip_ticks * tick

    # prior-ATR proxy: mean of the prior 14 RTH-day ranges (shifted, causal), in ticks
    day_range = _rth_day_ranges(df, open_m, close_m)
    prior_atr = (day_range.shift(1).rolling(14, min_periods=5).mean() / tick)

    rows = []
    for date, day in df.groupby("date_et", sort=True):
        m = day["mod"].to_numpy()
        o = day["open"].to_numpy(); hi = day["high"].to_numpy()
        lo = day["low"].to_numpy(); cl = day["close"].to_numpy()
        et = day["et"].to_numpy()

        or_mask = (m >= open_m) & (m < or_end_m)
        if or_mask.sum() < max(1, cfg.or_minutes // 2):
            continue  # incomplete OR (holiday/half-day) -> skip
        or_high = hi[or_mask].max(); or_low = lo[or_mask].min()
        or_width_ticks = (or_high - or_low) / tick

        # causal vol gate
        if cfg.vol_gate != "none" and not np.isnan(cfg.gate_threshold):
            if cfg.vol_gate == "or_width":
                proxy = or_width_ticks
            elif cfg.vol_gate == "prior_atr":
                proxy = prior_atr.get(date, np.nan)
            else:
                proxy = np.nan
            if np.isnan(proxy) or proxy < cfg.gate_threshold:
                continue

        # entry window: after OR, before cutoff, within RTH
        win = (m >= or_end_m) & (m < cutoff_m) & (m < close_m)
        if not win.any():
            continue
        wi = np.flatnonzero(win)
        long_trig = or_high + buf
        short_trig = or_low - buf

        # first bar that breaks each side
        li = next((i for i in wi if hi[i] >= long_trig), None) if cfg.direction in ("both", "long") else None
        si = next((i for i in wi if lo[i] <= short_trig), None) if cfg.direction in ("both", "short") else None
        if li is None and si is None:
            continue
        if li is not None and si is not None:
            if li == si:
                continue  # one bar broke both edges -> ambiguous, skip
            is_long = li < si
        else:
            is_long = li is not None
        ei = li if is_long else si
        trig = long_trig if is_long else short_trig

        # gap-aware entry fill: if the bar opened beyond the trigger, fill at the open (worse)
        if is_long:
            entry = max(o[ei], trig) + slip
        else:
            entry = min(o[ei], trig) - slip

        # stop / target
        if cfg.stop_mode == "opp_or":
            stop = or_low if is_long else or_high
        else:  # or_frac
            w = or_width_ticks * tick * cfg.stop_or_frac
            stop = entry - w if is_long else entry + w
        risk = (entry - stop) if is_long else (stop - entry)
        if risk <= 0:
            continue  # degenerate (entry already through the stop side)
        target = (entry + cfg.target_R * risk) if is_long else (entry - cfg.target_R * risk)
        use_target = cfg.target_R > 0

        # honest day-flat management via the shared core (rule-8 stop-wins, EOD flatten)
        tr = simulate_trade(m, o, hi, lo, cl, ei, is_long, entry, stop, target,
                            use_target, slip, spec, close_m)
        if tr is None:
            continue
        tr.update({"date": pd.Timestamp(date).date(), "year": pd.Timestamp(date).year,
                   "side": "long" if is_long else "short", "or_width_ticks": or_width_ticks})
        rows.append(tr)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- metrics

def summarize(trades: pd.DataFrame) -> dict:
    if trades is None or len(trades) == 0:
        return {"n": 0, "net_R": float("nan"), "win": float("nan"), "net_R_h1": float("nan"),
                "net_R_h2": float("nan"), "net_R_ex2020": float("nan"), "worst_year": float("nan")}
    t = trades.sort_values("date").reset_index(drop=True)
    half = len(t) // 2
    by_year = t.groupby("year")["net_R"].mean()
    return {
        "n": int(len(t)),
        "net_R": float(t["net_R"].mean()),
        "win": float((t["net_R"] > 0).mean()),
        "net_R_h1": float(t.iloc[:half]["net_R"].mean()) if half else float("nan"),
        "net_R_h2": float(t.iloc[half:]["net_R"].mean()) if half else float("nan"),
        "net_R_ex2020": float(t[t["year"] != 2020]["net_R"].mean()),
        "worst_year": float(by_year.min()),
        "trades_per_year": float(len(t) / max(1, t["year"].nunique())),
    }


def derive_gate_threshold(df: pd.DataFrame, spec: Spec, cfg: ORBConfig, pctile: float) -> float:
    """Design-window proxy distribution -> absolute threshold at `pctile`. Causal by construction."""
    open_m = _hhmm(cfg.session_open); close_m = _hhmm(cfg.session_close)
    or_end_m = open_m + cfg.or_minutes; tick = spec.tick_size
    if cfg.vol_gate == "or_width":
        vals = []
        for _, day in df.groupby("date_et"):
            m = day["mod"].to_numpy()
            om = (m >= open_m) & (m < or_end_m)
            if om.sum() < max(1, cfg.or_minutes // 2):
                continue
            vals.append((day["high"].to_numpy()[om].max() - day["low"].to_numpy()[om].min()) / tick)
        return float(np.nanpercentile(vals, pctile * 100)) if vals else float("nan")
    if cfg.vol_gate == "prior_atr":
        dr = _rth_day_ranges(df, open_m, close_m)
        pa = (dr.shift(1).rolling(14, min_periods=5).mean() / tick).dropna()
        return float(np.nanpercentile(pa, pctile * 100)) if len(pa) else float("nan")
    return float("nan")


# ----------------------------------------------------------------------------- self-test

def _synth_day(date_str, open_px, path, tick=0.01):
    """Build a one-day 1m frame (ET) from a price path starting at 09:30, 24h not needed for test."""
    base = pd.Timestamp(date_str + " 09:30", tz=ET)
    rows = []
    px = open_px
    for i, step in enumerate(path):
        o = px; c = px + step
        h = max(o, c) + tick; l = min(o, c) - tick
        rows.append({"ts_event": (base + pd.Timedelta(minutes=i)).tz_convert("UTC"),
                     "open": o, "high": h, "low": l, "close": c, "volume": 100})
        px = c
    df = pd.DataFrame(rows)
    ts = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert(ET)
    df["et"] = ts; df["date_et"] = ts.dt.normalize(); df["mod"] = ts.dt.hour * 60 + ts.dt.minute
    return df


def selftest():
    spec = Spec(0.01, 1000.0, 2.0)  # CL-like
    cfg = ORBConfig(or_minutes=5, entry_cutoff_min=60, buffer_ticks=1, stop_mode="opp_or",
                    target_R=2.0, direction="both", slip_ticks=1)
    ok = True

    # 1) trend-up day: flat OR then steady ramp -> long breakout hits 2R target
    path = [0.0]*5 + [0.05]*40  # OR ~ flat, then +5c/min ramp
    t = run_orb(_synth_day("2021-03-01", 50.00, path, 0.01), spec, cfg)
    cond = len(t) == 1 and t.iloc[0]["side"] == "long" and t.iloc[0]["reason"] == "target" and t.iloc[0]["gross_R"] >= 1.99
    print(f"[1] trend-up -> long target 2R: {'PASS' if cond else 'FAIL'}  {None if t.empty else t.iloc[0].to_dict()}")
    ok &= cond

    # 2) break-up then crash: small breakout on the entry bar, next bar collapses through the
    #    stop without reaching target -> stopped, net_R < 0
    path = [0.0]*5 + [0.03, -0.10] + [0.0]*30
    t = run_orb(_synth_day("2021-03-02", 50.00, path, 0.01), spec, cfg)
    cond = len(t) == 1 and t.iloc[0]["side"] == "long" and t.iloc[0]["reason"].startswith("stop") and t.iloc[0]["net_R"] < 0
    print(f"[2] break-then-crash -> stop <0R: {'PASS' if cond else 'FAIL'}  {None if t.empty else t.iloc[0].to_dict()}")
    ok &= cond

    # 3) no breakout (range-bound, never exceeds OR by buffer) -> no trade
    path = [0.0]*5 + [0.005, -0.005]*20
    t = run_orb(_synth_day("2021-03-03", 50.00, path, 0.01), spec, cfg)
    cond = len(t) == 0
    print(f"[3] range-bound -> no trade: {'PASS' if cond else 'FAIL'}  (n={len(t)})")
    ok &= cond

    # 4) costs make net_R < gross_R always (commission + slip)
    path = [0.0]*5 + [0.05]*40
    t = run_orb(_synth_day("2021-03-04", 50.00, path, 0.01), spec, cfg)
    cond = len(t) == 1 and t.iloc[0]["net_R"] < t.iloc[0]["gross_R"]
    print(f"[4] net_R < gross_R (costs bite): {'PASS' if cond else 'FAIL'}")
    ok &= cond

    print(f"\nSELFTEST: {'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--symbol"); ap.add_argument("--start"); ap.add_argument("--end")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if a.symbol:
        df = build_dataset(a.symbol, a.start, a.end)
        spec = get_spec(a.symbol)
        t = run_orb(df, spec, ORBConfig())
        print(f"{a.symbol}: {len(df.date_et.unique())} days, {len(t)} trades")
        import json
        print(json.dumps(summarize(t), indent=2, default=str))
