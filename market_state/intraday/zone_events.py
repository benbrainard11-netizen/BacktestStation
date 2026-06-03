"""Stage 1 go/no-go: does event-time order flow predict HOLD vs BREAK at a level on ES?

Detect touches of the prior-day high/low (objective levels), compute event-time Cont-Kukanov-Stoikov
OFI in a short window AT the touch (the research's #1 feature, EXACT on MBP-1), label hold/break with a
triple-barrier, and test OOS via the validated harness (validation/harness.py). Event-time, not 15-min buckets.

This is the GATE: if event-time flow can't separate holds from breaks here, the whole system premise is weak.
Reads ES MBP-1 day-by-day (D:/data, ~2025-05..2026-05). Levels precomputed from 1d bars so days can be sampled.

Run: backend/.venv/Scripts/python.exe market_state/intraday/zone_events.py [N_DAYS]
  (N_DAYS = evenly-sample N days across the range for a quick read; omit = all days)
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_bars, read_mbp1  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validation"))
from harness import forward_test, print_result  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SYM = "ES.c.0"
TICK = 0.25
MBP1_DIR = Path("D:/data/raw/databento/mbp-1/symbol=ES.c.0")
START, END = "2025-04-01", "2026-06-01"
OUT = Path("market_state/out")
OUT.mkdir(parents=True, exist_ok=True)

EPS = 2 * TICK  # "touch" = mid within 2 ticks of the level
W_OFI = pd.Timedelta("2s")  # event-time OFI window AFTER the touch
B = 8 * TICK  # break barrier: price moves 8 ticks (2 pts) THROUGH the level
R = 8 * TICK  # hold barrier: price reverts 8 ticks AGAINST the level
HORIZON = pd.Timedelta("30min")  # max time to resolve
COOLDOWN = pd.Timedelta("15min")  # min gap between counted touches of the same level
OOS_START = pd.Timestamp("2026-03-01", tz="UTC")  # ~last 3 months held out


def available_days() -> list[str]:
    return sorted(d.name.split("=")[-1] for d in MBP1_DIR.iterdir() if d.is_dir())


def precompute_levels() -> dict:
    """Prior-day high/low per trading day, from 1d bars (intraday hi/lo robust to the daily-close roll bug)."""
    b = read_bars(symbol=SYM, timeframe="1d", start=START, end=END)
    ts = pd.to_datetime(b["ts_event"], utc=True)
    df = pd.DataFrame({"date": ts.dt.date, "high": b["high"].to_numpy(), "low": b["low"].to_numpy()})
    df = df.groupby("date").agg(high=("high", "max"), low=("low", "min"))
    df["pdh"], df["pdl"] = df["high"].shift(1), df["low"].shift(1)
    return df[["pdh", "pdl"]].dropna().to_dict("index")


def cks_ofi_inc(bp, bs, ap, as_) -> np.ndarray:
    """Per-update Cont-Kukanov-Stoikov OFI increment from MBP-1 best bid/ask (exact)."""
    e = np.zeros(len(bp))
    b0, b1 = bp[:-1], bp[1:]
    a0, a1 = ap[:-1], ap[1:]
    e[1:] = ((b1 >= b0) * bs[1:] - (b1 <= b0) * bs[:-1] - (a1 <= a0) * as_[1:] + (a1 >= a0) * as_[:-1])
    return e


def label_touch(mid: np.ndarray, i0: int, k1: int, L: float, dr: int):
    """Triple-barrier first-hit over mid[i0:k1]. break=through level (dir), hold=revert. None=timeout."""
    seg = mid[i0:k1]
    if dr == 1:
        brk, hold = np.where(seg >= L + B)[0], np.where(seg <= L - R)[0]
    else:
        brk, hold = np.where(seg <= L - B)[0], np.where(seg >= L + R)[0]
    fb = brk[0] if len(brk) else np.inf
    fh = hold[0] if len(hold) else np.inf
    if fb == np.inf and fh == np.inf:
        return None
    return 1 if fb < fh else 0


def process_day(day: str, pdh: float, pdl: float) -> list[dict]:
    nxt = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()
    d = read_mbp1(symbol=SYM, start=day, end=nxt, columns=["ts_event", "bid_px", "ask_px", "bid_sz", "ask_sz"])
    if len(d) < 100:
        return []
    ts = pd.to_datetime(d["ts_event"], utc=True)
    bp, ap = d["bid_px"].to_numpy(float), d["ask_px"].to_numpy(float)
    bs, as_ = d["bid_sz"].to_numpy(float), d["ask_sz"].to_numpy(float)
    ok = np.isfinite(bp) & np.isfinite(ap) & (bp > 0) & (ap > 0)
    if ok.sum() < 100:
        return []
    ts, bp, ap, bs, as_ = ts[ok], bp[ok], ap[ok], bs[ok], as_[ok]
    mid = (bp + ap) / 2.0
    ofi = cks_ofi_inc(bp, bs, ap, as_)
    tsi = pd.DatetimeIndex(ts)
    rows = []
    for L, role in ((pdh, "PDH"), (pdl, "PDL")):
        in_band = np.abs(mid - L) <= EPS
        onsets = np.where(in_band & ~np.r_[False, in_band[:-1]])[0]
        last_t = None
        for i0 in onsets:
            t0 = tsi[i0]
            if last_t is not None and (t0 - last_t) < COOLDOWN:
                continue
            ib = max(0, tsi.searchsorted(t0 - pd.Timedelta("60s")) - 1)
            dr = 1 if mid[ib] < L else -1
            jo = int(tsi.searchsorted(t0 + W_OFI, side="right"))
            of = float(ofi[i0:jo].sum()) * dr
            k1 = int(tsi.searchsorted(t0 + HORIZON, side="right"))
            lab = label_touch(mid, jo, k1, L, dr)  # outcome measured AFTER the OFI window = no overlap/lookahead
            if lab is None:
                continue
            last_t = t0
            rows.append({"ts": t0, "level": role, "dir": dr, "ofi_signed": of, "label": lab})
    return rows


def main(n_days: int | None) -> int:
    levels = precompute_levels()
    days = available_days()
    if n_days and n_days < len(days):
        idx = np.linspace(0, len(days) - 1, n_days).round().astype(int)  # span the FULL range (incl. OOS tail)
        days = [days[i] for i in sorted(set(idx.tolist()))]
    print(f"levels {len(levels)} days; processing {len(days)} MBP-1 days "
          f"({days[0]}..{days[-1]}){'  [SAMPLED]' if n_days else ''}")
    ev = []
    for i, day in enumerate(days):
        lv = levels.get(dt.date.fromisoformat(day))
        if not lv:
            continue
        try:
            ev += process_day(day, lv["pdh"], lv["pdl"])
        except Exception as e:  # noqa: BLE001
            print(f"  {day}: ERROR {type(e).__name__}: {e}")
        if (i + 1) % 20 == 0:
            print(f"  ..{i + 1}/{len(days)} days, {len(ev)} events")

    df = pd.DataFrame(ev)
    if len(df) < 30:
        print(f"\nonly {len(df)} events -- too few to judge (widen sample).")
        return 0
    df = df.set_index("ts").sort_index()
    df.to_parquet(OUT / "zone_events_ES.parquet")
    print(f"\nEVENTS n={len(df)}  break_rate={df['label'].mean():.3f}  "
          f"(PDH {int((df.level=='PDH').sum())} / PDL {int((df.level=='PDL').sum())})")
    # break rate by OFI tercile (intuition: more break-direction flow -> more breaks?)
    q = pd.qcut(df["ofi_signed"], 3, labels=["low", "mid", "high"], duplicates="drop")
    print("  break rate by signed-OFI tercile:")
    print(df.groupby(q, observed=True)["label"].agg(["mean", "count"]).round(3).to_string())

    frame = df.rename(columns={"ofi_signed": "signal", "label": "outcome"})[["signal", "outcome"]]
    print()
    print_result(forward_test(frame, name="ofi_signed->break[ES]", kind="continuous",
                              oos_start=OOS_START, min_effect=0.05, expect_sign=1))
    print("\n(go/no-go: OOS spearman clearly + and clears 0.05 => event-time flow predicts the resolution.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(int(sys.argv[1]) if len(sys.argv) > 1 else None))
