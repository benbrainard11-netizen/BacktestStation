"""Exit-policy sweep — one tick-pass per trade, ALL policies evaluated vectorized.

Motivation (exit autopsy 2026-06-10): time-exits +1.184R/76% win (clock amputates winners);
trail_2R caps the fat tail (top decile = 62% of sumR); stops -1.113 = mechanical floor.

Engine: entry + smt-pivot stop EXACTLY as live (reuses realized_r.drive's entry path), then
post-entry management is evaluated per policy with numpy (cummax hwm, first-hit indices).
VALIDATION GATE: the trail_2R policy must reproduce the cached realized_r (|diff|<=0.02R on
>=95% of trades) or the run aborts — proves the engine before any variant is believed.

Policy params: arm_R (trail arms at this favorable R), trail_R (distance behind hwm),
timeout_min, target_R (fixed target, no trail), be_at_R (move stop to entry at this R).
Costs mirror realized_r.net_r (commission both ways; entry slip; exit slip on stop/trail/time,
none on fixed-target limit fills).

DISCIPLINE: sweep on TRAIN gated trades only; top policies get ONE validation shot on
jan_oos + oos_holdout. Live exit stays locked; results are challenger evidence for Ben.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/exit_sweep.py --dataset train
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import realized_r as RR  # noqa: E402
import feed as feed_mod  # noqa: E402
import gate as G  # noqa: E402

SIG = RR.SIG
OPP = "combined.sweep_setup_event_id"
_NS = 1_000_000_000

POLICIES = {  # name: (arm_R, trail_R, timeout_min, target_R, be_at_R)
    "trail_2R":      (2.0, 1.0,  60, None, None),  # live baseline — must reproduce cache
    "fixed_2R":      (None, None, 60, 2.0, None),
    "fixed_3R":      (None, None, 60, 3.0, None),
    "trail_3R":      (3.0, 1.0,  60, None, None),
    "trail_2R_wide": (2.0, 1.5,  60, None, None),
    "trail_1R":      (1.0, 1.0,  60, None, None),
    "t2_hold120":    (2.0, 1.0, 120, None, None),
    "t2_hold240":    (2.0, 1.0, 240, None, None),
    "t2_be1R":       (2.0, 1.0,  60, None, 1.0),
    "t2_be1R_h120":  (2.0, 1.0, 120, None, 1.0),
}
MAX_TIMEOUT = max(p[2] for p in POLICIES.values())


def entry_for(symbol, direction, trig, trig_ts, arr):
    """Run the live entry path (reclaim wait + smt_pivot stop reset). Returns
    (entry_idx, entry_px, entry_ts_ns, stop_px, risk) or None."""
    ts_ns, bid, ask = arr
    root = symbol.split(".")[0]
    far = trig + 1000.0 if direction == -1 else trig - 1000.0
    trade = SIG.ReclaimTrade(symbol=root, direction=direction, trigger_price=trig,
                             stop_ref_price=far, decision_ts=trig_ts.to_pydatetime(),
                             exit_mode="trail_2R")
    buf = feed_mod.MBP1Buffer(symbol, retain_sec=100_000)
    trig_n = int(trig_ts.value)
    start = int(np.searchsorted(ts_ns, trig_n - 185 * _NS, "left"))
    for pos in range(start, len(ts_ns)):
        tn = int(ts_ns[pos]); b = bid[pos]; a = ask[pos]
        if not (np.isfinite(b) and np.isfinite(a)):
            continue
        buf.append_raw(tn, b, a)
        if tn < trig_n:
            continue
        act = trade.on_quote(pd.Timestamp(tn, tz="UTC").to_pydatetime(), b, a)
        if act.kind == "enter":
            ref = buf.local_extreme(tn, direction, 180)
            if ref is None or not trade.reset_stop(ref):
                return None
            return pos, trade.entry_px, tn, trade.stop_px, trade.risk
        if act.kind == "cancel":
            return None
    return None


def first_true(mask: np.ndarray) -> int:
    idx = int(np.argmax(mask))
    return idx if mask[idx] else -1


def eval_policies(direction, entry_idx, entry_px, entry_ns, stop_px, risk, arr, symbol):
    """Vectorized post-entry evaluation of every policy on one tick pass."""
    # ALL comparisons in PRICE space (long-equivalent fav = +px / -px), exactly as live _manage:
    # R-space division breaks exact ties (e.g. trail level landing on a tick) by 1 ULP.
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
    for name, (arm, trail, tmo, target, be_at) in POLICIES.items():
        tmo_i = first_true(tns - entry_ns >= int(tmo * 60) * _NS)
        end_i = tmo_i if tmo_i >= 0 else len(px) - 1  # data end = forced flat
        lvl = np.full(len(px), stop_fav)  # breakeven shifts the stop to entry once be_at reached
        if be_at is not None:
            be_i = first_true(hwm >= entry_fav + be_at * risk)
            if be_i >= 0:
                lvl[be_i:] = entry_fav
        stop_i = first_true(fav <= lvl)
        cand = [(stop_i, "stop", None)]
        if target is not None:
            cand.append((first_true(fav >= entry_fav + target * risk), "target", float(target)))
        if arm is not None:
            armed = hwm >= entry_fav + arm * risk
            tr_i = first_true(armed & (fav <= hwm - trail * risk))
            cand.append((tr_i, "trail", None))
        cand.append((end_i, "time" if tmo_i >= 0 else "data_end", None))
        live = [(i, rs, fx) for i, rs, fx in cand if i >= 0]
        # Same-tick priority mirrors live _manage's check order: time -> stop -> trail/target.
        prio = {"time": 0, "data_end": 0, "stop": 1}
        i, reason, fixed = min(live, key=lambda t: (t[0], prio.get(t[1], 2)))
        if reason == "stop":
            gross = (float(lvl[i]) - entry_fav) / risk
        elif reason == "target":
            gross = fixed
        else:
            gross = (float(fav[i]) - entry_fav) / risk
        out[name] = (RR.net_r(gross, "stop" if reason == "stop" else
                              ("target" if reason == "target" else "trail"), symbol, risk), reason)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="train")
    ap.add_argument("--limit", type=int, default=0, help="first N trades only (engine smoke test)")
    args = ap.parse_args()

    gate = G.Gate()
    ds = pd.read_parquet(HERE / "data" / f"{args.dataset}.parquet")
    ds["trigger_ts_utc"] = pd.to_datetime(ds["trigger_ts_utc"], utc=True)
    ds["p"] = gate.score(ds)
    gt = (ds[ds.p >= gate.threshold]
          .sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
          .groupby(OPP, sort=False).head(1).copy())
    gt["rr_cache"] = pd.to_numeric(gt["realized_r"], errors="coerce")
    gt = gt[gt["rr_cache"].notna()].copy()
    if args.limit:
        gt = gt.head(args.limit)
    print(f"[{args.dataset}] sweeping {len(gt)} gated trades x {len(POLICIES)} policies", flush=True)

    rows = []
    gt["_date"] = gt["trigger_ts_utc"].dt.date
    for (sym, d), grp in gt.groupby(["symbol", "_date"]):
        lo = grp["trigger_ts_utc"].min() - pd.Timedelta(seconds=200)
        hi = grp["trigger_ts_utc"].max() + pd.Timedelta(minutes=MAX_TIMEOUT + 15)
        arr = RR.load_mbp1(str(sym), lo, hi)
        if arr is None:
            continue
        for i, row in grp.iterrows():
            direction = 1 if str(row["smt_anchor_side"]) == "low" else -1
            ent = entry_for(str(sym), direction, float(row["trigger_price"]), row["trigger_ts_utc"], arr)
            if ent is None:
                continue
            res = eval_policies(direction, ent[0], ent[1], ent[2], ent[3], ent[4], arr, str(sym))
            if not res:
                continue
            rec = {"idx": i, "symbol": str(sym), "rr_cache": float(row["rr_cache"])}
            for name, (r, reason) in res.items():
                rec[name] = r
                rec[f"{name}_reason"] = reason
            rows.append(rec)
    res = pd.DataFrame(rows)
    out = HERE / "runs" / f"exit_sweep_{args.dataset}.parquet"
    res.to_parquet(out, index=False)

    # VALIDATION GATE: engine's trail_2R must reproduce the cached realized_r
    diff = (res["trail_2R"] - res["rr_cache"]).abs()
    ok = float((diff <= 0.02).mean())
    print(f"\nVALIDATION trail_2R vs cache: {100*ok:.1f}% within 0.02R "
          f"(median diff {diff.median():.4f}, n={len(res)})", flush=True)
    if ok < 0.95:
        bad = res[diff > 0.02]
        gt_idx = gt.set_index(gt.index)
        for _, b in bad.iterrows():
            cached_reason = gt_idx.loc[b["idx"], "r_reason"] if b["idx"] in gt_idx.index else "?"
            print(f"  MISMATCH idx={b['idx']} {b['symbol']}: cache={b['rr_cache']:+.3f} ({cached_reason}) "
                  f"engine={b['trail_2R']:+.3f} ({b['trail_2R_reason']})")
        print("ABORT: engine does not reproduce the live baseline — variant numbers untrustworthy.")
        return 2

    print(f"\n=== EXIT-POLICY SWEEP on {args.dataset} gated trades (n={len(res)}) ===")
    base = res["trail_2R"]
    for name in POLICIES:
        r = res[name]
        d = r.mean() - base.mean()
        reasons = res[f"{name}_reason"].value_counts().to_dict()
        print(f"{name:14s} meanR={r.mean():+.3f} (vs base {d:+.3f}) win={100*(r>0).mean():4.1f}% "
              f"sumR={r.sum():+7.1f}  exits={reasons}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
