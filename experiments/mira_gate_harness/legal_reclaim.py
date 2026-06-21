"""legal_reclaim.py — first HONEST (past-anchored) measurement of the sweep-reclaim structure.

WHY: both prior systems were invalidated for future-anchored features (windows ending at the
5m-window extreme, post-trigger orderflow, future ATR). THE ONE RULE: nothing the strategy decides
on may use data after the decision tick.

CONSTRUCTION (all past-anchored):
  universe : one attempt per (level, touch) from detect.compute_levels (audit-verified legal level
             families). Every other builder column (outcomes, MBO windows, sweep development) is
             DROPPED at load — the strategy never sees them.
  direction: smt_anchor_side low -> long (price swept BELOW the level), high -> short.
  entry    : replay MBP-1 from touch_ts forward (max 60m wait); the sweep must first be VISIBLE in
             the replay stream (long: a tick with bid strictly below the level — without this the
             touch tick itself satisfies bid>=level and every attempt degenerates to an instant
             3-tick-risk entry; the first smoke run proved it), then the first tick where price
             re-crosses the level (long: bid >= level_price) fills at the ask (+1 tick slip in
             costs). The entry has NO knowledge of whether the adverse extreme is final.
  stop     : running adverse extreme SO FAR at the entry tick (long: min bid since touch) -/+ 2
             ticks buffer. risk must be > 0 else skip.
  exits    : trail_2R and fixed_3R evaluated simultaneously — vectorized price-space logic copied
             from exit_sweep.eval_policies (validated 100% vs the live baseline) — 60m max hold,
             costs identical to realized_r.net_r.

LEGALITY CHECKLIST (asserted in code where possible):
  [A] entry uses only ticks <= the entry tick   (forward scan; assert entry_ts >= touch_ts)
  [B] stop uses only ticks <= the entry tick    (prefix min/max ENDING at the entry tick; asserted)
  [C] no level used before level_known_ts_utc   (compute_levels guarantees it; asserted per row)
  [D] no full-window stats anywhere             (cummax + first-hit are causal forward-scan
                                                 encodings: index i depends only on ticks <= i)

Resume: per symbol-day parts in runs/legal_reclaim_parts/ (this box crashes); combined output at
runs/legal_reclaim_<tag>.parquet.

Run (jan): backend/.venv/Scripts/python.exe experiments/mira_gate_harness/legal_reclaim.py
Smoke:     ... legal_reclaim.py --start 2026-01-05 --end 2026-01-06 --symbols ES.c.0 --tag smoke
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
os.environ["BACKTESTSTATION_BACKEND"] = str(ROOT / "live_engine" / "vendor")
os.environ.pop("BS_MIRA_ROOT", None)
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import harness as H  # noqa: E402  (env must be set BEFORE this import; adds MBO day-read cache)
import realized_r as RR  # noqa: E402  (load_mbp1 + net_r costs + TICK map)

D = H.D
RUNS = HERE / "runs"
PARTS = RUNS / "legal_reclaim_parts"
TICK = RR.TICK
_NS = 1_000_000_000
WAIT_MIN = 60      # max wait for the reclaim after the touch
HOLD_MIN = 60      # max hold after entry
STOP_BUF_TK = 2.0  # stop buffer beyond the running adverse extreme
POLICIES = {  # name: (arm_R, trail_R, timeout_min, target_R)
    "trail_2R": (2.0, 1.0, HOLD_MIN, None),
    "fixed_3R": (None, None, HOLD_MIN, 3.0),
}
# The ONLY columns the strategy may see (level identity + timestamps). No outcomes, no features.
LEGAL_COLS = list(D.LEVEL_CORE_COLS)


def first_true(mask: np.ndarray) -> int:
    if not mask.size:
        return -1
    idx = int(np.argmax(mask))
    return idx if mask[idx] else -1


def eval_exits(direction, entry_idx, entry_px, entry_ns, stop_px, risk, arr, symbol) -> dict:
    """Vectorized post-entry evaluation — copied from exit_sweep.eval_policies (no breakeven).
    ALL comparisons in PRICE space (long-equivalent fav = +px / -px), exactly as live _manage.
    [D] legal: cummax/first-hit only encode a causal forward scan — exit index i uses ticks <= i."""
    ts_ns, bid, ask = arr
    b2, a2 = bid[entry_idx + 1:], ask[entry_idx + 1:]
    tns = ts_ns[entry_idx + 1:]
    ok = np.isfinite(b2) & np.isfinite(a2)  # live skips a tick unless BOTH sides are finite
    px = (b2 if direction == 1 else a2)[ok]
    tns = tns[ok]
    if not len(px):
        return {}
    fav = px if direction == 1 else -px
    entry_fav = entry_px if direction == 1 else -entry_px
    stop_fav = stop_px if direction == 1 else -stop_px
    hwm = np.maximum(np.maximum.accumulate(fav), entry_fav)  # live seeds hwm with entry fav
    out = {}
    for name, (arm, trail, tmo, target) in POLICIES.items():
        tmo_i = first_true(tns - entry_ns >= int(tmo * 60) * _NS)
        end_i = tmo_i if tmo_i >= 0 else len(px) - 1  # data end = forced flat
        cand = [(first_true(fav <= stop_fav), "stop", None)]
        if target is not None:
            cand.append((first_true(fav >= entry_fav + target * risk), "target", float(target)))
        if arm is not None:
            armed = hwm >= entry_fav + arm * risk
            cand.append((first_true(armed & (fav <= hwm - trail * risk)), "trail", None))
        cand.append((end_i, "time" if tmo_i >= 0 else "data_end", None))
        live = [(i, rs, fx) for i, rs, fx in cand if i >= 0]
        prio = {"time": 0, "data_end": 0, "stop": 1}  # same-tick priority mirrors live _manage
        i, reason, fixed = min(live, key=lambda t: (t[0], prio.get(t[1], 2)))
        if reason == "stop":
            gross = (stop_fav - entry_fav) / risk
        elif reason == "target":
            gross = fixed
        else:
            gross = (float(fav[i]) - entry_fav) / risk
        cost = "stop" if reason == "stop" else ("target" if reason == "target" else "trail")
        out[name] = (RR.net_r(gross, cost, symbol, risk), reason)
    return out


def replay(arr, touch_ns: int, level_px: float, side: str, symbol: str) -> tuple[str, dict]:
    """One sweep-reclaim attempt, replayed strictly forward from the touch tick."""
    ts_ns, bid, ask = arr
    d = 1 if side == "low" else -1
    tick = TICK[symbol]
    i0 = int(np.searchsorted(ts_ns, touch_ns, "left"))
    iN = int(np.searchsorted(ts_ns, touch_ns + WAIT_MIN * 60 * _NS, "right"))
    if iN <= i0:
        return "no_data", {}
    b, a = bid[i0:iN], ask[i0:iN]
    ok = np.isfinite(b) & np.isfinite(a)
    rel = np.nonzero(ok)[0]
    if not rel.size:
        return "no_data", {}
    bb, aa = b[rel], a[rel]
    # [A] entry = first re-cross tick AFTER the sweep is visible on the book (prefix-OR cummax);
    # [B] adverse = prefix extreme ENDING at that same tick. All causal scans.
    if d == 1:
        swept = np.maximum.accumulate(bb < level_px)  # bid printed strictly BELOW the level yet?
        k = first_true(swept & (bb >= level_px))      # long: bid re-crosses the level from below
        adverse = float(np.minimum.accumulate(bb)[k]) if k >= 0 else np.nan
        assert k < 0 or adverse == float(bb[: k + 1].min())  # [B] no tick after entry in the stop
    else:
        swept = np.maximum.accumulate(aa > level_px)  # ask printed strictly ABOVE the level yet?
        k = first_true(swept & (aa <= level_px))      # short: ask re-crosses the level from above
        adverse = float(np.maximum.accumulate(aa)[k]) if k >= 0 else np.nan
        assert k < 0 or adverse == float(aa[: k + 1].max())
    if k < 0:
        return ("no_sweep", {}) if not bool(swept[-1]) else ("no_entry", {})
    entry_px = float(aa[k] if d == 1 else bb[k])     # fill at the touchable side (long: ask)
    stop_px = adverse - d * STOP_BUF_TK * tick       # beyond the extreme by the buffer
    risk = d * (entry_px - stop_px)
    entry_idx = i0 + int(rel[k])
    entry_ns = int(ts_ns[entry_idx])
    assert entry_ns >= touch_ns                      # [A] decision tick is at/after the touch
    if risk <= 0:
        return "no_risk", {}
    rec = {"entry_ts_utc": pd.Timestamp(entry_ns, tz="UTC"), "entry_px": entry_px,
           "stop_px": float(stop_px), "risk_pts": float(risk), "adverse_px": adverse,
           "wait_s": round((entry_ns - touch_ns) / _NS, 3)}
    ex = eval_exits(d, entry_idx, entry_px, entry_ns, stop_px, risk, arr, symbol)
    if not ex:
        return "no_exit_data", {}
    for name, (r, reason) in ex.items():
        rec[name] = r
        rec[f"{name}_reason"] = reason
    return "entered", rec


def run_day(sym: str, day_levels: pd.DataFrame) -> pd.DataFrame:
    touch = pd.to_datetime(day_levels["touch_ts_utc"], utc=True)
    lo = touch.min() - pd.Timedelta(seconds=1)
    hi = touch.max() + pd.Timedelta(minutes=WAIT_MIN + HOLD_MIN + 15)
    arr = RR.load_mbp1(sym, lo, hi)
    rows = []
    for i, row in day_levels.iterrows():
        ts = pd.Timestamp(touch.loc[i])
        base = {"symbol": sym, "level_family": str(row["level_family"]),
                "level_type": str(row["level_type"]), "level_price": float(row["level_price"]),
                "side": str(row["smt_anchor_side"]), "touch_ts_utc": ts}
        if arr is None:
            status, rec = "no_data", {}
        else:
            status, rec = replay(arr, int(ts.value), float(row["level_price"]),
                                 str(row["smt_anchor_side"]), sym)
        rows.append({**base, "status": status, **rec})
    return pd.DataFrame(rows)


def levels_universe(sym: str, sd: dt.date, ed: dt.date, tag: str) -> pd.DataFrame:
    lp = PARTS / f"levels__{tag}__{sym}.parquet"
    if lp.exists():
        lv = pd.read_parquet(lp)
    else:
        lv = D.compute_levels(sym, sd, ed)
        lv = lv[LEGAL_COLS].copy() if len(lv) else pd.DataFrame(columns=LEGAL_COLS)
        lv.to_parquet(lp, index=False)
    if not len(lv):
        return lv
    known = pd.to_datetime(lv["level_known_ts_utc"], utc=True)
    touch = pd.to_datetime(lv["touch_ts_utc"], utc=True)
    n_bad = int((touch < known).sum())
    assert n_bad == 0, f"{sym}: {n_bad} touches BEFORE level_known_ts_utc — illegal universe"  # [C]
    return lv


def stats(x: pd.Series) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if not len(x):
        return "n=   0"
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():5.1f}% sumR={x.sum():+8.1f}"


def report(df: pd.DataFrame, tag: str) -> None:
    ent = df[df["status"] == "entered"]
    print(f"\n=== LEGAL RECLAIM [{tag}] — {len(df)} attempts, {len(ent)} entered "
          f"(status: {df['status'].value_counts().to_dict()}) ===")
    for pol in POLICIES:
        if pol not in ent.columns:
            continue
        reasons = ent[f"{pol}_reason"].value_counts().to_dict()
        print(f"\n[{pol}]  pooled         {stats(ent[pol])}  exits={reasons}")
        for fam, gf in ent.groupby("level_family"):
            print(f"  {fam:15s} {stats(gf[pol])}")


def main() -> int:
    ap = argparse.ArgumentParser(description="honest past-anchored sweep-reclaim measurement")
    ap.add_argument("--start", default="2026-01-02")
    ap.add_argument("--end", default="2026-02-04")
    ap.add_argument("--symbols", default="ES.c.0,NQ.c.0")
    ap.add_argument("--tag", default="jan")
    args = ap.parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    for s in symbols:
        assert s in TICK, f"unknown symbol {s} (no TICK entry)"
    sd, ed = dt.date.fromisoformat(args.start), dt.date.fromisoformat(args.end)
    PARTS.mkdir(parents=True, exist_ok=True)

    parts = []
    for sym in symbols:
        lv = levels_universe(sym, sd, ed, args.tag)
        print(f"[{sym}] {len(lv)} (level, touch) attempts "
              f"{dict(lv['level_family'].value_counts()) if len(lv) else {}}", flush=True)
        if not len(lv):
            continue
        lv = lv.assign(_d=pd.to_datetime(lv["touch_ts_utc"], utc=True).dt.date)
        for day, g in sorted(lv.groupby("_d"), key=lambda t: t[0]):
            part = PARTS / f"{args.tag}__{sym}__{day}.parquet"
            if part.exists():
                res = pd.read_parquet(part)
                print(f"  {sym} {day}: {len(res)} attempts (CHECKPOINT)", flush=True)
            else:
                res = run_day(sym, g.drop(columns=["_d"]))
                res.to_parquet(part, index=False)  # incremental save — crash loses one day max
                n_ent = int((res["status"] == "entered").sum())
                print(f"  {sym} {day}: {len(res)} attempts -> {n_ent} entered", flush=True)
            parts.append(res)
    if not parts:
        print("no attempts in window")
        return 1
    df = pd.concat(parts, ignore_index=True)
    out = RUNS / f"legal_reclaim_{args.tag}.parquet"
    df.to_parquet(out, index=False)
    report(df, args.tag)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
