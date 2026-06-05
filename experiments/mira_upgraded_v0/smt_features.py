"""Upgraded-Mira SMT: cross-index divergence features (classic SMT v1) -- the STRUCTURAL confirmation.

When ES sweeps its reference extreme, do the correlated indices (NQ/YM/RTY) CONFIRM (also take their matching
extreme) or DIVERGE (hold)? Divergence = the reversal signal. Per event x partner x reference-window:
  mag = ATR-normalized distance the partner held INSIDE its reference (>0 = diverged, didn't take it)
  div = mag > 0 (binary)
  sym = are ES's and the partner's reference extremes at the SAME time (symmetrical) or different (unsymmetrical)
Separate module: reads index bars READ-ONLY, never touches the live engine. Reads events_upgraded.parquet.

Run: backend/.venv/Scripts/python.exe experiments/mira_upgraded_v0/smt_features.py [EVENTS_PARQUET]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RT / "backend"))
from app.data.reader import read_bars  # noqa: E402

IDX = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
PARTNERS = ["NQ.c.0", "YM.c.0", "RTY.c.0"]
ET = "America/New_York"
DEFAULT_EV = Path(__file__).resolve().parent / "out" / "events_upgraded.parquet"


def _u(x) -> np.datetime64:
    t = pd.Timestamp(x)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    return t.tz_localize(None).to_datetime64()


class Bars:
    """Fast window-extreme lookups via searchsorted on a sorted UTC index."""

    def __init__(self, b: pd.DataFrame):
        b = b.sort_index()
        self.ts = b.index.tz_convert("UTC").tz_localize(None).values
        self.low, self.high = b["low"].to_numpy(float), b["high"].to_numpy(float)
        et = b.index.tz_convert(ET)
        daily = pd.DataFrame({"hi": b["high"].to_numpy(float), "lo": b["low"].to_numpy(float)},
                             index=et.date).groupby(level=0).agg(hi=("hi", "max"), lo=("lo", "min"))
        self.atr = (daily["hi"] - daily["lo"]).rolling(14, min_periods=3).mean()

    def extreme(self, t0, t1, side: str):
        i0 = int(np.searchsorted(self.ts, _u(t0)))
        i1 = int(np.searchsorted(self.ts, _u(t1), side="right"))
        if i1 <= i0:
            return np.nan, None
        if side == "low":
            j = i0 + int(np.argmin(self.low[i0:i1]))
            return self.low[j], self.ts[j]
        j = i0 + int(np.argmax(self.high[i0:i1]))
        return self.high[j], self.ts[j]


def _load(sym, start, end) -> Bars:
    b = read_bars(symbol=sym, timeframe="1m", start=start, end=end)
    b = b.assign(ts=pd.to_datetime(b["ts_event"], utc=True)).set_index("ts")
    return Bars(b[["high", "low", "close"]].astype(float))


def build_smt(events: pd.DataFrame, primary: str = "ES.c.0") -> pd.DataFrame:
    s0 = (pd.to_datetime(events["session_date"]).min() - pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    s1 = (pd.to_datetime(events["session_date"]).max() + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    bars = {s: _load(s, s0, s1) for s in IDX}
    partners = [s for s in IDX if s != primary]
    rows = []
    for _, e in events.iterrows():
        t_touch, t_ext = pd.Timestamp(e["touch_ts_utc"]), pd.Timestamp(e["sweep.5m.sweep_extreme_ts_utc"])
        side, sd = e["smt_anchor_side"], pd.to_datetime(e["session_date"]).date()
        feat = {}
        if pd.isna(t_ext) or side not in ("low", "high"):
            rows.append(feat)
            continue
        for refname, r0, r1 in [("pday", t_touch.normalize() - pd.Timedelta(days=1), t_touch.normalize()),
                                ("h6", t_touch - pd.Timedelta(hours=6), t_touch)]:
            _, es_ref_t = bars[primary].extreme(r0, r1, side)
            for P in partners:
                tag = P.split(".")[0].lower()
                p_ref, p_ref_t = bars[P].extreme(r0, r1, side)
                p_in, _ = bars[P].extreme(t_touch, t_ext, side)
                a = bars[P].atr.get(sd, np.nan)
                if not (np.isfinite(p_ref) and np.isfinite(p_in) and np.isfinite(a) and a > 0):
                    continue
                raw = (p_in - p_ref) if side == "low" else (p_ref - p_in)   # >0 = partner held inside ref = diverged
                feat[f"smt.{refname}.{tag}.mag"] = raw / a
                feat[f"smt.{refname}.{tag}.div"] = float(raw > 0)
                if es_ref_t is not None and p_ref_t is not None:
                    feat[f"smt.{refname}.{tag}.sym"] = float(abs((es_ref_t - p_ref_t) / np.timedelta64(1, "m")) < 30)
        divs = [v for k, v in feat.items() if k.endswith(".div")]
        feat["smt.any_div"] = float(any(d > 0 for d in divs)) if divs else np.nan
        feat["smt.n_div"] = float(sum(d > 0 for d in divs)) if divs else np.nan
        rows.append(feat)
    return pd.concat([events.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def main() -> int:
    ev_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EV
    primary = sys.argv[2] if len(sys.argv) > 2 else "ES.c.0"
    out_path = Path(sys.argv[3]) if len(sys.argv) > 3 else ev_path.with_name("events_smt.parquet")
    ev = pd.read_parquet(ev_path)
    out = build_smt(ev, primary)
    out.to_parquet(out_path)
    sc = [c for c in out.columns if c.startswith("smt.")]
    print(f"events {len(out)}  +{len(sc)} SMT features -> {out_path.name}")
    print(f"any_div rate {out['smt.any_div'].mean():.3f}   mean n_div {out['smt.n_div'].mean():.2f}")
    print("per-partner pday divergence rate / symmetry rate:")
    for tag in ["nq", "ym", "rty"]:
        d, s = out.get(f"smt.pday.{tag}.div"), out.get(f"smt.pday.{tag}.sym")
        print(f"  {tag}: div {d.mean():.3f}  sym {s.mean():.3f}" if d is not None else f"  {tag}: n/a")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
