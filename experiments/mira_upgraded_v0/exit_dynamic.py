"""DYNAMIC TARGET test (the user's original idea: target should scale with structure/volatility, not be a flat 3R).
Tick-honest on the same gate-selected trades / MBP-1 paths as exit_lab. Same honest entry + stop (4tk past extreme,
stop = -1R). Each mode just sets a different TARGET (converted to R-equiv on the path); first touch decides.
  fix3        -- baseline (fixed 3R)
  atr0.5/1/1.5-- target = k x prior-day range beyond entry (vol-scaled distance)
  volLoHi     -- target R by vol regime: low 2R / mid 3R / high 4R
  volHiLo     -- reverse: low 4R / mid 3R / high 2R
  struct      -- target = prior-session OPPOSITE extreme (trade to the next liquidity)
Honest tick-R per mode, day-block CI, ES. Beats fix3 => dynamic target adds.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(RT / "backend"))
from app.data.reader import read_mbp1_trading_day  # noqa: E402
from reclaim_entry import DEF, SPEC, boot  # noqa: E402
from smt_economics import wf_gate  # noqa: E402

TARGET, MAXH, BUF = 3.0, 120, 4


def _first(mask):
    idx = np.where(mask)[0]
    return int(idx[0]) if len(idx) else None


def _fixed(Rp, tgtR, cost_r):
    if not (tgtR and tgtR > 0.2):
        return None
    si, ti = _first(Rp <= -1.0), _first(Rp >= tgtR)
    if si is not None and (ti is None or si < ti):
        return -1.0 - cost_r
    if ti is not None:
        return tgtR - cost_r
    return float(Rp[-1]) - cost_r


def trade(e, ts, px, sym, vlo, vhi):
    ptv, cost, tick = SPEC.get(sym, DEF)
    level, extreme = float(e["level_price"]), float(e["sweep.5m.sweep_extreme_price"])
    long = e["smt_anchor_side"] == "low"
    ext_ts = pd.Timestamp(e["sweep.5m.sweep_extreme_ts_utc"]).to_datetime64()
    i0 = int(np.searchsorted(ts, ext_ts))
    i1 = int(np.searchsorted(ts, ext_ts + np.timedelta64(MAXH, "m")))
    w = px[i0:i1]
    if len(w) == 0:
        return None
    cross = np.where(w >= level)[0] if long else np.where(w <= level)[0]
    if len(cross) == 0:
        return None
    wa = w[cross[0]:]
    entry = float(wa[0]) + (tick if long else -tick)
    stop = extreme - BUF * tick if long else extreme + BUF * tick
    risk = (entry - stop) if long else (stop - entry)
    if risk <= 0:
        return None
    Rp = ((wa - entry) / risk) if long else ((entry - wa) / risk)
    cr = cost / (risk * ptv)
    atr = float(e.get("prior_rth_range_pts", np.nan))
    vol = atr
    reg = "low" if vol <= vlo else ("high" if vol >= vhi else "mid")
    struct = float(e.get("prior_rth_high", np.nan)) if long else float(e.get("prior_rth_low", np.nan))
    struct_R = ((struct - entry) / risk) if long else ((entry - struct) / risk)
    modes = {
        "fix3": 3.0,
        "atr0.5": 0.5 * atr / risk if atr > 0 else None,
        "atr1.0": 1.0 * atr / risk if atr > 0 else None,
        "atr1.5": 1.5 * atr / risk if atr > 0 else None,
        "volLoHi": {"low": 2.0, "mid": 3.0, "high": 4.0}[reg],
        "volHiLo": {"low": 4.0, "mid": 3.0, "high": 2.0}[reg],
        "struct": struct_R,
    }
    return {k: _fixed(Rp, v, cr) for k, v in modes.items()}


def main() -> int:
    ev = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out" / "events_es_tf.parquet"
    sym = sys.argv[2] if len(sys.argv) > 2 else "ES.c.0"
    df = pd.read_parquet(ev)
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].reset_index(drop=True)
    df["fam"] = pd.factorize(df["level_family"])[0]
    feats = [c for c in df.columns if c.startswith("smt_tf.")] + ["fam"]
    sel, _, _, _ = wf_gate(df, feats, TARGET)
    sub = df[sel].copy()
    v = sub["prior_rth_range_pts"].to_numpy(float)
    vlo, vhi = np.nanquantile(v, [0.34, 0.67])
    print(f"{sym}: {len(sub)} gate trades, dynamic-target tick-honest (vol cut {vlo:.0f}/{vhi:.0f} pts)...\n")

    pol: dict = {}
    days = []
    for d, g in sub.groupby("day"):
        try:
            mbp = read_mbp1_trading_day(symbol=sym, trading_day=d, columns=["ts_event", "action", "price"])
        except Exception:
            continue
        tr = mbp[(mbp["action"] == "T") & (mbp["price"] > 0)]
        if tr.empty:
            continue
        tsv = pd.to_datetime(tr["ts_event"], utc=True).dt.tz_localize(None).to_numpy()
        pxv = tr["price"].to_numpy(float)
        for _, e in g.iterrows():
            res = trade(e, tsv, pxv, sym, vlo, vhi)
            if res is None:
                continue
            days.append(d)
            for k, val in res.items():
                pol.setdefault(k, []).append(val)

    days = np.array(days, dtype=object)
    print(f"  {len(days)} trades. honest tick-R by target mode [day-block CI] (vs fix3 baseline):")
    rows = []
    for k, vals in pol.items():
        v = np.array([x for x in vals], dtype=float)
        keep = ~np.isnan(v)
        if keep.sum() < 30:
            print(f"    {k:8} thin ({keep.sum()})")
            continue
        m, lo, hi = boot(v[keep], days[keep])
        rows.append((k, m, lo, hi, keep.sum()))
    for k, m, lo, hi, n in sorted(rows, key=lambda x: -x[1]):
        flag = "  <==" if lo > 0 else ""
        print(f"    {k:8} {m:+.2f} [{lo:+.2f},{hi:+.2f}]  n{n}{flag}")
    print("\nREAD: a dynamic mode clearly above fix3 = the structure/vol-adaptive target adds. If fix3 stays on top, "
          "the flat target was right and exits are genuinely done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
