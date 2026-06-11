"""Entry-policy sweep v2 — answers the live-box memo's test #3 (entry conversion).

v1 was killed by its own adversarial audit (runs/entry_sweep_audit_2026-06-11): live anchors
MAX_ENTRY_WAIT at the TRIGGER (run.py passes decision_ts=trigger_ts), so detection lag BURNS the
window — "wait 10m from arm" is not current live, it's a proposed engine change. v2 models both,
plus live's one-position-per-symbol occupancy and setup retries, on the UN-deduped gated stream.

Policies (shared per-trigger lag, drawn from the measured live lag distribution, seed 42):
  ideal_lag0   lag=0,  window [trig, trig+10m]      cached-realized_r convention; VALIDATION + ceiling
  live_current sampled lag, window [arm, trig+10m]  deployed semantics (lag burns the window)
  window20     sampled lag, window [arm, trig+20m]  one-line live change (MAX_ENTRY_WAIT=20)
  window30     sampled lag, window [arm, trig+30m]  one-line live change (MAX_ENTRY_WAIT=30)
  rearm10      sampled lag, window [arm, arm+10m]   one-line live change (anchor wait at arm)
  market_arm   sampled lag, market fill at first quote >= arm+1s (decision-to-fill latency)

Engine: vectorized entry (first crossing in window; long bid>=trigger fills @ask) -> smt_pivot_180s
stop re-anchor (min bid / max ask over 180s through entry, minus STOP_BUFFER_TICKS) -> exit via
exit_sweep.eval_policies (validated to reproduce live trail_2R 100%, price-space ties, stop-wins).
Occupancy: per symbol, a trigger is BLOCKED if a prior arm (until cancel) or position (until exit)
is active — mirrors run.py already_active + risk.py position_already_open. Costs = realized_r.net_r.

VALIDATION GATES (must pass before any table prints):
  G1 fill-SET agreement: ideal_lag0 (deduped, no occupancy) vs cached realized_r — fill/no-fill
     agreement >= 98%, matched |dR| <= 0.02 on >= 98%, n >= 400.
Reporting: OOS-first (jan_oos + oos_holdout); train labeled in-sample; paired symbol-day block
bootstrap CI on delta-sumR vs live_current; risk_pts distribution per policy (R-denominator check).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/entry_sweep.py
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\backend")
import gate as G  # noqa: E402
import realized_r as RR  # noqa: E402
import exit_sweep as XS  # noqa: E402

SIG = RR.SIG
DATA, RUNS = HERE / "data", HERE / "runs"
LIVE_LOG = Path(r"C:\Users\benbr\BacktestStation\live_engine\analysis_data\mira_candidates_2026-06-11.jsonl")
WINDOWS = ["jan_oos", "train", "oos_holdout"]
OOS = ["jan_oos", "oos_holdout"]
CHAMP_THR = 0.5818010299926861
OPP = "combined.sweep_setup_event_id"
_NS = 1_000_000_000
LATENCY_NS = 1 * _NS          # market-order decision-to-fill latency
STOP_BUF = SIG.STOP_BUFFER_TICKS

# name: (use_lag, window_anchor, window_min, mode)
POLICIES = {
    "ideal_lag0":   (False, "trigger", 10, "touch"),
    "live_current": (True,  "trigger", 10, "touch"),
    "window20":     (True,  "trigger", 20, "touch"),
    "window30":     (True,  "trigger", 30, "touch"),
    "rearm10":      (True,  "arm",     10, "touch"),
    "market_arm":   (True,  "arm",      0, "market"),
}


def live_lag_pool() -> np.ndarray:
    rows = [json.loads(line) for line in LIVE_LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    lags = [(pd.Timestamp(r["ts"]) - pd.Timestamp(r["trigger_ts"])).total_seconds() / 60
            for r in rows if r["ts"][:10] >= "2026-06-08"]
    return np.clip(np.array(sorted(lags)), 0.5, 20.0)


def vec_entry(arr, direction: int, trig: float, win_lo_n: int, win_hi_n: int, mode: str):
    """First fill in [win_lo_n, win_hi_n]. touch: first crossing (long bid>=trig, fill@ask).
    market: first finite quote (trig ignored). Returns (idx, entry_px, entry_ns) or None."""
    ts_ns, bid, ask = arr
    lo = int(np.searchsorted(ts_ns, win_lo_n, "left"))
    hi = int(np.searchsorted(ts_ns, win_hi_n, "right"))
    if lo >= hi:
        return None
    b, a = bid[lo:hi], ask[lo:hi]
    fin = np.isfinite(b) & np.isfinite(a)
    if mode == "market":
        cross = fin
    else:
        cross = fin & ((b >= trig) if direction == 1 else (a <= trig))
    i = int(np.argmax(cross))
    if not cross[i]:
        return None
    gi = lo + i
    return gi, float(ask[gi] if direction == 1 else bid[gi]), int(ts_ns[gi])


def pivot_stop(arr, direction: int, entry_idx: int, entry_px: float, entry_ns: int, symbol: str):
    """smt_pivot_180s re-anchor exactly as feed.MBP1Buffer.local_extreme + signal.reset_stop:
    long ref = min finite bid over (entry-180s, entry]; stop = ref -/+ buffer ticks."""
    ts_ns, bid, ask = arr
    lo = int(np.searchsorted(ts_ns, entry_ns - 180 * _NS, "left"))
    b, a = bid[lo:entry_idx + 1], ask[lo:entry_idx + 1]
    fin = np.isfinite(b) & np.isfinite(a)
    if not fin.any():
        return None
    ref = float(np.min(b[fin])) if direction == 1 else float(np.max(a[fin]))
    tick = SIG.TICK_SIZE[symbol.split(".")[0]]
    stop_px = ref - STOP_BUF * tick if direction == 1 else ref + STOP_BUF * tick
    risk = (entry_px - stop_px) if direction == 1 else (stop_px - entry_px)
    return (stop_px, risk) if risk > 0 else None


def _exit_trail2R(direction, entry_idx, entry_px, entry_ns, stop_px, risk, arr, symbol):
    """trail_2R exit on one tick pass — the exit_sweep.eval_policies logic for the live policy
    (validated to reproduce live 100%), extended to return the EXIT TIMESTAMP for occupancy.
    Price-space comparisons, hwm seeded at entry, same-tick priority time -> stop -> trail."""
    ts_ns, bid, ask = arr
    b2, a2 = bid[entry_idx + 1:], ask[entry_idx + 1:]
    tns = ts_ns[entry_idx + 1:]
    ok = np.isfinite(b2) & np.isfinite(a2)
    px = (b2 if direction == 1 else a2)[ok]
    tns = tns[ok]
    if not len(px):
        return None
    fav = px if direction == 1 else -px
    entry_fav = entry_px if direction == 1 else -entry_px
    stop_fav = stop_px if direction == 1 else -stop_px
    hwm = np.maximum(np.maximum.accumulate(fav), entry_fav)
    tmo_i = XS.first_true(tns - entry_ns >= 60 * 60 * _NS)
    end_i = tmo_i if tmo_i >= 0 else len(px) - 1
    stop_i = XS.first_true(fav <= stop_fav)
    armed = hwm >= entry_fav + 2.0 * risk
    tr_i = XS.first_true(armed & (fav <= hwm - 1.0 * risk))
    cand = [(stop_i, "stop"), (tr_i, "trail"), (end_i, "time" if tmo_i >= 0 else "data_end")]
    prio = {"time": 0, "data_end": 0, "stop": 1}
    i, reason = min(((i, rs) for i, rs in cand if i >= 0), key=lambda t: (t[0], prio.get(t[1], 2)))
    gross = ((stop_fav if reason == "stop" else float(fav[i])) - entry_fav) / risk
    net = RR.net_r(gross, "stop" if reason == "stop" else "trail", symbol, risk)
    return float(net), reason, int(tns[i])


def drive_one(arr, row, lag_min: float, policy: str):
    """One trigger under one policy. Returns dict(filled, net_r, reason, entry/exit info,
    busy_until_ns) — busy_until covers arm->cancel for unfilled, arm->exit for filled."""
    use_lag, anchor, wmin, mode = POLICIES[policy]
    trig_n = int(row.trigger_ts_utc.value)
    arm_n = trig_n + int((lag_min if use_lag else 0.0) * 60 * _NS)
    direction = 1 if row.smt_anchor_side == "low" else -1
    if mode == "market":
        win_lo, win_hi = arm_n + LATENCY_NS, arm_n + LATENCY_NS + 120 * _NS
    else:
        win_lo = arm_n
        win_hi = (trig_n if anchor == "trigger" else arm_n) + wmin * 60 * _NS
    if win_lo > win_hi:
        return dict(filled=False, reason="prearm_expired", busy_until=arm_n, net_r=np.nan)
    ent = vec_entry(arr, direction, float(row.trigger_price), win_lo, win_hi, mode)
    if ent is None:
        return dict(filled=False, reason="expired", busy_until=win_hi, net_r=np.nan)
    gi, entry_px, entry_ns = ent
    ps = pivot_stop(arr, direction, gi, entry_px, entry_ns, str(row.symbol))
    if ps is None:
        return dict(filled=False, reason="cancel_stop", busy_until=entry_ns, net_r=np.nan)
    stop_px, risk = ps
    out = _exit_trail2R(direction, gi, entry_px, entry_ns, stop_px, risk, arr, str(row.symbol))
    if out is None:
        return dict(filled=False, reason="no_post_data", busy_until=entry_ns, net_r=np.nan)
    net, reason, exit_ns = out
    return dict(filled=True, net_r=net, reason=reason, entry_ns=entry_ns, entry_px=entry_px,
                risk=float(risk), busy_until=exit_ns)


def load_triggers() -> pd.DataFrame:
    frames = []
    for w in WINDOWS:
        ds = pd.read_parquet(DATA / f"{w}.parquet")
        ds["trigger_ts_utc"] = pd.to_datetime(ds["trigger_ts_utc"], utc=True)
        ds["champ_score"] = G.Gate().score(ds)
        g = ds[(ds["champ_score"] >= CHAMP_THR) & (ds["symbol"] != "YM.c.0")].copy()
        g["window"] = w
        frames.append(g)
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values(["symbol", "trigger_ts_utc", "trigger_id"], kind="stable").reset_index(drop=True)


def validate(trigs: pd.DataFrame) -> bool:
    """G1: ideal_lag0 on the DEDUPED set, no occupancy, must reproduce cached realized_r."""
    dd = (trigs.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
          .groupby(OPP, sort=False).head(1))
    res = []
    for (sym, d), g in dd.assign(_d=dd["trigger_ts_utc"].dt.date).groupby(["symbol", "_d"]):
        arr = RR.load_mbp1(str(sym), g["trigger_ts_utc"].min() - pd.Timedelta(seconds=200),
                           g["trigger_ts_utc"].max() + pd.Timedelta(minutes=115))
        for row in g.itertuples():
            if arr is None:
                continue
            r = drive_one(arr, row, 0.0, "ideal_lag0")
            res.append((row.Index, r.get("net_r", np.nan), pd.to_numeric(row.realized_r, errors="coerce")))
    cmp = pd.DataFrame(res, columns=["i", "v2", "cache"])
    cmp = cmp[cmp["cache"].notna() | cmp["v2"].notna()]
    n = len(cmp)
    fill_agree = ((cmp["v2"].notna()) == (cmp["cache"].notna())).mean() * 100
    both = cmp[cmp["v2"].notna() & cmp["cache"].notna()]
    close = ((both["v2"] - both["cache"]).abs() <= 0.02)
    print(f"[G1] n={n} (need >=400)  fill-set agreement {fill_agree:.1f}% (need >=98)  "
          f"matched |dR|<=0.02: {close.mean()*100:.1f}% of {len(both)} (need >=98)  "
          f"max|dR|={float((both['v2']-both['cache']).abs().max()):.4f}", flush=True)
    ok = n >= 400 and fill_agree >= 98.0 and close.mean() * 100 >= 98.0
    if not ok:
        bad = both[~close]
        print(bad.head(12).to_string())
    return ok


def run_all(trigs: pd.DataFrame, lags: np.ndarray) -> dict[str, pd.DataFrame]:
    """One pass over (symbol, day) MBP-1 loads; all policies driven per trigger, each with its
    own occupancy state (busy_until) carried across days — mirrors live's per-symbol blocking."""
    rows: dict[str, list] = {p: [] for p in POLICIES}
    for sym, g in trigs.groupby("symbol", sort=False):
        busy = {p: -1 for p in POLICIES}
        for _d, gd in g.assign(_d=g["trigger_ts_utc"].dt.date).groupby("_d", sort=True):
            arr = RR.load_mbp1(str(sym), gd["trigger_ts_utc"].min() - pd.Timedelta(seconds=200),
                               gd["trigger_ts_utc"].max() + pd.Timedelta(minutes=115))
            for row in gd.itertuples():
                lag = float(lags[row.Index])
                base = dict(idx=row.Index, window=row.window, symbol=str(sym),
                            month=str(row.trigger_ts_utc.to_period("M")),
                            day=str(row.trigger_ts_utc.date()), lag=lag)
                for policy in POLICIES:
                    use_lag = POLICIES[policy][0]
                    arm_n = int(row.trigger_ts_utc.value) + int((lag if use_lag else 0.0) * 60 * _NS)
                    if arm_n < busy[policy]:
                        rows[policy].append(dict(**base, filled=False, net_r=np.nan, reason="blocked"))
                        continue
                    if arr is None:
                        rows[policy].append(dict(**base, filled=False, net_r=np.nan, reason="no_data"))
                        continue
                    r = drive_one(arr, row, lag, policy)
                    busy[policy] = max(busy[policy], int(r.pop("busy_until")))
                    rows[policy].append(dict(**base, **r))
    return {p: pd.DataFrame(v) for p, v in rows.items()}


def table(frames: dict[str, pd.DataFrame], windows: list[str], label: str) -> None:
    print(f"\n  == {label} ==")
    print(f"    {'policy':14s} {'trigs':>6s} {'blocked':>7s} {'filled':>6s} {'win%':>6s} "
          f"{'meanR/fill':>10s} {'sumR':>8s} {'R/trig':>7s} {'risk_pts p50':>12s}")
    for name in POLICIES:
        f = frames[name]
        sub = f[f["window"].isin(windows)]
        filled = sub[sub["filled"] == True]  # noqa: E712
        r = filled["net_r"]
        rp = filled["risk"].median() if "risk" in filled and len(filled) else float("nan")
        print(f"    {name:14s} {len(sub):6d} {(sub['reason']=='blocked').sum():7d} {len(filled):6d} "
              f"{(r>0).mean()*100 if len(r) else 0:5.1f}% {r.mean() if len(r) else 0:+10.3f} "
              f"{r.sum():+8.1f} {r.sum()/max(len(sub),1):+7.3f} {rp:12.2f}")


def bootstrap_delta(frames, base: str, chall: str, windows: list[str], nboot=10_000, seed=7):
    """Paired symbol-day block bootstrap of total-R difference (challenger - base)."""
    b = frames[base]; c = frames[chall]
    b = b[b["window"].isin(windows)]; c = c[c["window"].isin(windows)]
    key = lambda f: f.assign(k=f["symbol"] + "|" + f.get("day", f["month"]).astype(str))  # noqa: E731
    bs = key(b).groupby("k")["net_r"].sum(min_count=1).fillna(0.0)
    cs = key(c).groupby("k")["net_r"].sum(min_count=1).fillna(0.0)
    keys = sorted(set(bs.index) | set(cs.index))
    delta = np.array([cs.get(k, 0.0) - bs.get(k, 0.0) for k in keys])
    rng = np.random.default_rng(seed)
    sums = rng.choice(delta, size=(nboot, len(delta)), replace=True).sum(axis=1)
    return float(delta.sum()), float(np.percentile(sums, 2.5)), float(np.percentile(sums, 97.5))


def main() -> int:
    trigs = load_triggers()
    print(f"un-deduped gated no-YM trigger stream: {len(trigs)} "
          f"({trigs.groupby('window').size().to_dict()})", flush=True)
    if not validate(trigs):
        print("VALIDATION FAILED - STOP")
        return 1

    pool = live_lag_pool()
    rng = np.random.default_rng(42)
    lags = rng.choice(pool, size=len(trigs))   # shared across policies (paired design)
    print(f"lag pool: n={len(pool)} median={np.median(pool):.1f}m p90={np.percentile(pool,90):.1f}m; "
          f"sampled per-trigger, shared across policies", flush=True)

    frames = run_all(trigs, lags)
    for name, f in frames.items():
        print(f"  [{name}] filled {(f['filled']==True).sum()}/{len(f)} "
              f"sumR {f['net_r'].sum():+.1f}", flush=True)

    table(frames, OOS, "OOS (jan_oos + oos_holdout) — THE DECISION TABLE")
    table(frames, ["jan_oos"], "jan_oos (OOS)")
    table(frames, ["oos_holdout"], "oos_holdout (OOS)")
    table(frames, ["train"], "train (IN-SAMPLE — context only)")

    print("\n  Paired symbol-day block bootstrap, OOS only: delta total R vs live_current (95% CI):")
    for chall in ["window20", "window30", "rearm10", "market_arm", "ideal_lag0"]:
        d, lo, hi = bootstrap_delta(frames, "live_current", chall, OOS)
        sig = "SIGNIFICANT" if lo > 0 or hi < 0 else "not significant"
        print(f"    {chall:14s} delta={d:+7.1f}R  CI95=[{lo:+7.1f}, {hi:+7.1f}]  {sig}")

    print("\n  Monthly R/trigger (all windows; Feb-May in-sample):")
    months = sorted(frames["live_current"]["month"].unique())
    names = list(POLICIES)
    print(f"    {'month':9s}" + "".join(f"{n:>13s}" for n in names))
    for m in months:
        line = f"    {m:9s}"
        for n in names:
            sub = frames[n][frames[n]["month"] == m]
            line += f"{sub['net_r'].sum()/max(len(sub),1):+13.3f}"
        print(line)

    out = RUNS / "entry_sweep_v2_results.parquet"
    pd.concat([f.assign(policy=n) for n, f in frames.items()], ignore_index=True).to_parquet(out, index=False)
    print(f"\nper-trigger results -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
