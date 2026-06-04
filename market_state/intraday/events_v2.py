"""Event builder v2 -- VOL-SCALED + ZONE-AWARE (Ben's two corrections).

- Thresholds in VOL UNITS (daily ATR), not fixed ticks -> comparable across ES/NQ/RTY/YM + adapts to
  conditions. touch tol = TOL*ATR; break/hold = mult*ATR (swept over MULTS for robustness).
- Levels carry a zone [lo,hi]: lines (PDH/PDL/ONH/ONL/PWC) have lo=hi; the GAP (prior-close<->open) and the
  OPENING RANGE are real zones with width -> touch = ENTER the zone, hold = REJECT off the near edge, break =
  TRAVERSE past the far edge. Zone width enters naturally (break = far edge + mult*ATR).
- CONFLUENCE = how many other levels coincide (within 0.1*ATR) at the touched level = the orthogonal feature.
Reuses the validated OFI machinery (zone_events.cks_ofi_inc) + the level engine (levels.build_levels). ES-only.

Run: backend/.venv/Scripts/python.exe market_state/intraday/events_v2.py [N_DAYS]
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_mbp1  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from levels import build_levels  # noqa: E402
from zone_events import available_days, cks_ofi_inc  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validation"))
from harness import forward_test, print_result  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

W_OFI, HORIZON, COOLDOWN = pd.Timedelta("2s"), pd.Timedelta("30min"), pd.Timedelta("15min")
ATR_WIN = 14
TOL = 0.05  # touch tolerance = TOL * ATR
MULTS = [0.05, 0.10, 0.15, 0.20, 0.30]  # break/hold thresholds in * ATR (robustness sweep); y10 is primary
LINES = ["pdh", "pdl", "onh", "onl", "pwc"]
OUT = Path("market_state/out")
OOS_START = pd.Timestamp("2026-03-01", tz="UTC")


def day_levels(row: pd.Series, sigma: float) -> list[dict]:
    """Per-day level set as zones [lo,hi]; lines have lo=hi. + confluence (others within 0.1*ATR)."""
    Ls = []
    for nm in LINES:
        p = row.get(nm)
        if pd.notna(p):
            Ls.append({"name": nm, "lo": float(p), "hi": float(p), "c": float(p), "after": 0})
    if pd.notna(row.get("pdc")) and pd.notna(row.get("rth_open")):
        lo, hi = sorted([float(row["pdc"]), float(row["rth_open"])])
        Ls.append({"name": "gap", "lo": lo, "hi": hi, "c": (lo + hi) / 2, "after": 0})
    if pd.notna(row.get("orl")) and pd.notna(row.get("orh")):
        lo, hi = float(row["orl"]), float(row["orh"])
        Ls.append({"name": "or", "lo": lo, "hi": hi, "c": (lo + hi) / 2, "after": 585})  # valid after 09:45 ET
    for L in Ls:
        L["confl"] = sum(1 for M in Ls if M is not L and abs(M["c"] - L["c"]) <= 0.1 * sigma)
    return Ls


def label_mults(seg: np.ndarray, lo: float, hi: float, dr: int, sigma: float) -> dict:
    """First-hit hold(0)/break(1) per vol-multiplier on a mid segment measured AFTER the OFI window."""
    out = {}
    for m in MULTS:
        d = m * sigma
        if dr == 1:
            brk, hold = np.where(seg >= hi + d)[0], np.where(seg <= lo - d)[0]
        else:
            brk, hold = np.where(seg <= lo - d)[0], np.where(seg >= hi + d)[0]
        fb = brk[0] if len(brk) else np.inf
        fh = hold[0] if len(hold) else np.inf
        out[f"y{int(m * 100):02d}"] = (1 if fb < fh else 0) if min(fb, fh) < np.inf else None
    return out


def process_day(day: str, row: pd.Series) -> list[dict]:
    sigma = float(row.get("atr", np.nan))
    if not np.isfinite(sigma) or sigma <= 0:
        return []
    Ls = day_levels(row, sigma)
    nxt = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()
    d = read_mbp1(symbol="ES.c.0", start=day, end=nxt, columns=["ts_event", "bid_px", "ask_px", "bid_sz", "ask_sz"])
    if len(d) < 100:
        return []
    bp, ap = d["bid_px"].to_numpy(float), d["ask_px"].to_numpy(float)
    bs, as_ = d["bid_sz"].to_numpy(float), d["ask_sz"].to_numpy(float)
    ok = np.isfinite(bp) & np.isfinite(ap) & (bp > 0) & (ap > 0)
    if ok.sum() < 100:
        return []
    ts = pd.DatetimeIndex(pd.to_datetime(d["ts_event"], utc=True))[ok]
    bp, ap, bs, as_ = bp[ok], ap[ok], bs[ok], as_[ok]
    mid = (bp + ap) / 2.0
    ofi = cks_ofi_inc(bp, bs, ap, as_)
    minute = (ts.tz_convert("America/New_York").hour * 60 + ts.tz_convert("America/New_York").minute).to_numpy()
    tol = TOL * sigma
    rows = []
    for L in Ls:
        band = (mid >= L["lo"] - tol) & (mid <= L["hi"] + tol)
        if L["after"]:
            band &= minute >= L["after"]
        onsets = np.where(band & ~np.r_[False, band[:-1]])[0]
        last_t = None
        for i0 in onsets:
            t0 = ts[i0]
            if last_t is not None and (t0 - last_t) < COOLDOWN:
                continue
            ib = max(0, ts.searchsorted(t0 - pd.Timedelta("60s")) - 1)
            dr = 1 if mid[ib] < L["c"] else -1
            jo = int(ts.searchsorted(t0 + W_OFI, side="right"))
            of = float(ofi[i0:jo].sum()) * dr
            k1 = int(ts.searchsorted(t0 + HORIZON, side="right"))
            labs = label_mults(mid[jo:k1], L["lo"], L["hi"], dr, sigma)
            if labs["y10"] is None:  # require the primary threshold to resolve
                continue
            last_t = t0
            rows.append({"ts": t0, "level": L["name"], "confl": L["confl"], "dir": dr,
                         "ofi_signed": of, "atr": sigma, **labs})
    return rows


def main(n: int | None) -> int:
    lv = build_levels()
    lv["atr"] = (lv["pdh"] - lv["pdl"]).rolling(ATR_WIN).mean()  # 14-day mean prior-day range = the vol unit
    by_date = {ts.date(): row for ts, row in lv.iterrows()}
    days = available_days()
    if n and n < len(days):
        idx = np.linspace(0, len(days) - 1, n).round().astype(int)
        days = [days[i] for i in sorted(set(idx.tolist()))]
    print(f"vol-scaled zone-aware events: {len(days)} days{'  [SAMPLED]' if n else ''}")
    ev = []
    for i, day in enumerate(days):
        row = by_date.get(dt.date.fromisoformat(day))
        if row is None:
            continue
        try:
            ev += process_day(day, row)
        except Exception as e:  # noqa: BLE001
            print(f"  {day}: ERROR {type(e).__name__}: {e}")
        if (i + 1) % 20 == 0:
            print(f"  ..{i + 1}/{len(days)}, {len(ev)} events")

    df = pd.DataFrame(ev)
    if len(df) < 30:
        print(f"\nonly {len(df)} events -- widen sample.")
        return 0
    df = df.set_index("ts").sort_index()
    df.to_parquet(OUT / "events_v2_ES.parquet")
    print(f"\nEVENTS n={len(df)}  break_rate(y10)={df['y10'].mean():.3f}")
    print("  by level:\n" + df["level"].value_counts().to_string())
    print("  confluence dist:\n" + df["confl"].value_counts().sort_index().to_string())
    print("  break_rate by threshold:  " + "  ".join(f"y{int(m*100):02d}={df[f'y{int(m*100):02d}'].mean():.2f}" for m in MULTS))
    print()
    print_result(forward_test(df.rename(columns={"ofi_signed": "signal", "y10": "outcome"})[["signal", "outcome"]],
                              name="ofi->break(y10)", kind="continuous", oos_start=OOS_START, min_effect=0.05, expect_sign=1))
    print_result(forward_test(df.assign(signal=df["confl"]).rename(columns={"y10": "outcome"})[["signal", "outcome"]],
                              name="confluence->break(y10)", kind="continuous", oos_start=OOS_START, min_effect=0.05, expect_sign=0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(int(sys.argv[1]) if len(sys.argv) > 1 else None))
