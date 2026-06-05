"""Upgraded-Mira SMT v2: cross-index FILL divergence -- FVG and session-gap, as SEPARATE ablatable groups.

Your "SMT fill": one asset trades into an FVG/gap, a correlated one doesn't. Two types, kept separate:
  smt_fvg.{asset}.*  -- depth the asset's sweep penetrated a recent 5m 3-candle imbalance (ATR-norm)
  smt_gap.{asset}.*  -- RTH open-vs-prior-close gap size + how much filled by the touch
Computed for ES + NQ/YM/RTY so the gate sees the cross-index fill STRUCTURE (ES fills, partner doesn't).
Separate module, reads index bars READ-ONLY. Reads events_smt.parquet (already has classic-SMT), adds fill groups.

Run: backend/.venv/Scripts/python.exe experiments/mira_upgraded_v0/smt_fill_features.py [EVENTS_PARQUET]
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
ET = "America/New_York"
DEFAULT_EV = Path(__file__).resolve().parent / "out" / "events_smt.parquet"


def _u(x) -> np.datetime64:
    t = pd.Timestamp(x)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    return t.tz_localize(None).to_datetime64()


class Asset:
    def __init__(self, df: pd.DataFrame):
        df = df.sort_index()
        self.ts = df.index.tz_convert("UTC").tz_localize(None).values
        self.high, self.low = df["high"].to_numpy(float), df["low"].to_numpy(float)
        et = df.index.tz_convert(ET)
        self.dates = np.array(et.date)
        tod = et.hour * 60 + et.minute
        rth = (tod >= 570) & (tod < 960)
        d = pd.DataFrame({"date": et.date, "o": df["open"].to_numpy(float), "c": df["close"].to_numpy(float),
                          "h": df["high"].to_numpy(float), "l": df["low"].to_numpy(float), "rth": rth})
        g = d[d["rth"]].groupby("date")
        self.rth_open = g["o"].first()
        self.rth_close = g["c"].last()
        daily = d.groupby("date").agg(hi=("h", "max"), lo=("l", "min"))
        self.atr = (daily["hi"] - daily["lo"]).rolling(14, min_periods=3).mean()
        self.c5 = df[["open", "high", "low", "close"]].resample("5min").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        self.c5h, self.c5l = self.c5["high"].to_numpy(float), self.c5["low"].to_numpy(float)
        self.c5ts = self.c5.index.tz_convert("UTC").tz_localize(None).values

    def extreme(self, t0, t1, side):
        i0 = int(np.searchsorted(self.ts, _u(t0)))
        i1 = int(np.searchsorted(self.ts, _u(t1), side="right"))
        if i1 <= i0:
            return np.nan
        return float(self.low[i0:i1].min()) if side == "low" else float(self.high[i0:i1].max())

    def atr_of(self, sd):
        a = self.atr.get(sd, np.nan)
        return a if (np.isfinite(a) and a > 0) else np.nan

    def gap_feat(self, sd, prior_sd, t_open, t_touch):
        op, pc = self.rth_open.get(sd, np.nan), self.rth_close.get(prior_sd, np.nan)
        a = self.atr_of(sd)
        if not (np.isfinite(op) and np.isfinite(pc) and np.isfinite(a)):
            return np.nan, np.nan
        gap = op - pc
        if abs(gap) < 1e-9:
            return 0.0, 0.0
        if gap > 0:  # gap up -> fills by trading down toward pc
            lo = self.extreme(t_open, t_touch, "low")
            fill = np.clip((op - lo) / gap, 0, 1) if np.isfinite(lo) else 0.0
        else:        # gap down -> fills by trading up toward pc
            hi = self.extreme(t_open, t_touch, "high")
            fill = np.clip((hi - op) / (-gap), 0, 1) if np.isfinite(hi) else 0.0
        return gap / a, float(fill)

    def fvg_feat(self, sd, side, t0, t1, extreme):
        a = self.atr_of(sd)
        if not np.isfinite(a) or not np.isfinite(extreme):
            return np.nan, np.nan
        i0 = int(np.searchsorted(self.c5ts, _u(t0)))
        i1 = int(np.searchsorted(self.c5ts, _u(t1), side="right"))
        depth = 0.0
        for i in range(max(i0, 1), min(i1, len(self.c5h) - 1)):
            if self.c5l[i + 1] > self.c5h[i - 1]:          # gap-up void
                lo, hi = self.c5h[i - 1], self.c5l[i + 1]
            elif self.c5h[i + 1] < self.c5l[i - 1]:        # gap-down void
                lo, hi = self.c5h[i + 1], self.c5l[i - 1]
            else:
                continue
            if lo <= extreme <= hi:                        # sweep penetrated this imbalance
                pen = (hi - extreme) if side == "low" else (extreme - lo)
                depth = max(depth, pen / a)
        return depth, float(depth > 0)


def _load(sym, s0, s1) -> Asset:
    b = read_bars(symbol=sym, timeframe="1m", start=s0, end=s1)
    b = b.assign(ts=pd.to_datetime(b["ts_event"], utc=True)).set_index("ts")
    return Asset(b[["open", "high", "low", "close"]].astype(float))


def build_fill(events: pd.DataFrame) -> pd.DataFrame:
    s0 = (pd.to_datetime(events["session_date"]).min() - pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    s1 = (pd.to_datetime(events["session_date"]).max() + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    A = {s: _load(s, s0, s1) for s in IDX}
    rows = []
    for _, e in events.iterrows():
        t_touch, t_ext = pd.Timestamp(e["touch_ts_utc"]), pd.Timestamp(e["sweep.5m.sweep_extreme_ts_utc"])
        side, sd = e["smt_anchor_side"], pd.to_datetime(e["session_date"]).date()
        psd = pd.to_datetime(e["prior_session_date"]).date() if pd.notna(e.get("prior_session_date")) else None
        feat = {}
        if pd.isna(t_ext) or side not in ("low", "high"):
            rows.append(feat)
            continue
        t_open = t_touch.normalize() + pd.Timedelta(hours=13, minutes=30)   # ~RTH open in UTC (approx)
        for sym in IDX:
            tag = sym.split(".")[0].lower()
            ex = A[sym].extreme(t_touch, t_ext, side)
            depth, into = A[sym].fvg_feat(sd, side, t_touch - pd.Timedelta(hours=6), t_ext, ex)
            feat[f"smt_fvg.{tag}.depth"], feat[f"smt_fvg.{tag}.into"] = depth, into
            if psd is not None:
                gsz, gfl = A[sym].gap_feat(sd, psd, t_open, t_touch)
                feat[f"smt_gap.{tag}.size"], feat[f"smt_gap.{tag}.fill"] = gsz, gfl
        rows.append(feat)
    return pd.concat([events.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def main() -> int:
    ev_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EV
    out = build_fill(pd.read_parquet(ev_path))
    out_path = ev_path.with_name("events_smtfill.parquet")
    out.to_parquet(out_path)
    fvg = [c for c in out.columns if c.startswith("smt_fvg.")]
    gap = [c for c in out.columns if c.startswith("smt_gap.")]
    print(f"events {len(out)}  +{len(fvg)} FVG +{len(gap)} gap features -> {out_path.name}")
    print(f"  es into-FVG rate {out['smt_fvg.es.into'].mean():.3f}   "
          f"es gap |size| median {out['smt_gap.es.size'].abs().median():.2f}atr  "
          f"es gap-fill median {out['smt_gap.es.fill'].median():.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
