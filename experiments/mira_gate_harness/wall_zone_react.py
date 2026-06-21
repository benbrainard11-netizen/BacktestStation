"""PHASE 2+3: does a LTF zone (1m FVG / 3m OB+FVG / 5m OB+FVG) AT the wall turn the flat wall
reaction into an edge? (Ben: "just reacting off them with their 1m fvg or 5m/3m orderblock or fvg")

Reads runs/legal_bars_wall_full.parquet (Phase 1: full-history wall-reclaim attempts, honest R).
For each ENTERED wall reclaim, detect whether an OB or FVG zone formed AT the wall in [touch, decision)
on TF in {1m,3m,5m} using flow_at_zone's EXACT zone detector (bars-only, OB=rejection candle body,
FVG=3-candle gap, retrace-gated) -> zone-formed flags. Then test the zone-confirmation lift vs the
flat wall baseline, by TF / kind / year / symbol, with a SHUFFLE-FLAG null.

Bars-only -> runs the FULL history (no MBO). Cached per (symbol, session_date).
Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/wall_zone_react.py [--analyze-only]
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "backend"))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
import flow_at_zone as FZ  # noqa: E402  (_detect_zone_tf, _retraced, TICK, ONE_NS)
from smt_bench import load_1m, resample_tf  # noqa: E402

RUNS = HERE / "runs"
UNIVERSE = RUNS / "legal_bars_wall_full.parquet"
CACHE = RUNS / "wall_zone_react_feats.parquet"
ZONE_TFS = ["1m", "3m", "5m"]
FZ.TF_MIN.update({"1m": 1, "3m": 3, "5m": 5})  # detector reads FZ.TF_MIN[tf]
TICK = FZ.TICK
ONE_NS = FZ.ONE_NS
POL = "trail_2R"


def _resample(symbol: str, day: str) -> dict:
    d0 = pd.Timestamp(day, tz="UTC")
    lo = (d0 - pd.Timedelta(hours=12)).strftime("%Y-%m-%d")
    hi = (d0 + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    bars = load_1m(symbol, lo, hi)
    if bars.empty:
        return {}
    out = {tf: resample_tf(bars, FZ.TF_MIN[tf]) for tf in ZONE_TFS}
    out["1m_raw"] = bars
    return out


def detect_row(frames: dict, row) -> dict:
    sym = row["symbol"]
    tick = TICK[sym]
    touch_ns = int(pd.Timestamp(row["touch_ts_utc"]).value)
    decision_ns = int(pd.Timestamp(row["decision_ts_utc"]).value)
    bars1m = frames.get("1m_raw")
    out = {"any_zone": 0}
    for tf in ZONE_TFS:
        tf_b = frames.get(tf)
        zone = None
        if tf_b is not None and len(tf_b):
            close_ns = tf_b.index.asi8 + FZ.TF_MIN[tf] * 60 * ONE_NS
            sel = (close_ns >= touch_ns - 6 * 3600 * ONE_NS) & (close_ns <= decision_ns)
            sub = tf_b.iloc[sel]
            if len(sub):
                zone = FZ._detect_zone_tf(sub, row["side"], float(row["level_price"]),
                                          touch_ns, decision_ns, tf, tick)
        retraced = zone is not None and FZ._retraced(bars1m, zone[0], zone[1], zone[3],
                                                     decision_ns, tick)
        has = 1 if (zone is not None and retraced) else 0
        out[f"z_{tf}"] = has
        out[f"z_{tf}_kind"] = zone[2] if has else None
        if has:
            out["any_zone"] = 1
    return out


def build(force: bool = False) -> pd.DataFrame:
    uni = pd.read_parquet(UNIVERSE)
    uni = uni[(uni["status"] == "entered") & (uni["level_family"] == "gamma_wall")].copy()
    uni = uni[(pd.to_numeric(uni["trail_2R"], errors="coerce").abs() < 50) &
              (pd.to_numeric(uni["risk_tk"], errors="coerce") >= 0.5)]
    uni["session_date"] = uni["session_date"].astype(str)
    cached = pd.read_parquet(CACHE) if CACHE.exists() and not force else pd.DataFrame()
    done = (set(map(tuple, cached[["symbol", "session_date"]].drop_duplicates().to_numpy()))
            if len(cached) else set())
    groups = uni.groupby(["symbol", "session_date"], sort=True)
    todo = [k for k in groups.groups if k not in done]
    print(f"[build] {len(uni)} wall reclaims / {groups.ngroups} symbol-days "
          f"({len(done)} cached, {len(todo)} to compute)", flush=True)
    for n, (sym, day) in enumerate(todo, 1):
        g = groups.get_group((sym, day))
        try:
            frames = _resample(sym, day)
        except Exception as e:
            print(f"  SKIP {sym} {day}: {type(e).__name__}: {e}", flush=True)
            continue
        if not frames:
            continue
        recs = []
        for _, r in g.iterrows():
            base = {k: r[k] for k in ["symbol", "session_date", "level_type", "side",
                                      "level_price", "trail_2R", "fixed_3R"]}
            base.update(detect_row(frames, r))
            recs.append(base)
        cached = pd.concat([cached, pd.DataFrame(recs)], ignore_index=True)
        if n % 200 == 0 or n == len(todo):
            tmp = CACHE.with_suffix(".tmp.parquet")
            cached.to_parquet(tmp, index=False)
            tmp.replace(CACHE)
            print(f"  [{n}/{len(todo)}] cached", flush=True)
    tmp = CACHE.with_suffix(".tmp.parquet")
    cached.to_parquet(tmp, index=False)
    tmp.replace(CACHE)
    return cached


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):5d} R={x.mean():+.3f} win={100*(x>0).mean():4.1f}%" if len(x) else "n=    0"


def lift(d, col, val=1):
    a = pd.to_numeric(d[d[col] == val][POL], errors="coerce").dropna()
    b = pd.to_numeric(d[d[col] == 0][POL], errors="coerce").dropna()
    return (a.mean() - b.mean()) if (len(a) and len(b)) else np.nan


def analyze(d: pd.DataFrame) -> None:
    d = d[pd.to_numeric(d["trail_2R"], errors="coerce").abs() < 50].copy()
    d["yr"] = pd.to_datetime(d["session_date"]).dt.year
    print(f"\n{'='*92}\nWALL + LTF-ZONE REACTION  (n={len(d)} wall reclaims, {sorted(d['yr'].unique())})")
    print(f"  wall baseline (all)        {st(d[POL])}")

    print(f"\n=== (1) does a LTF zone AT the wall lift the reaction? [{POL}] ===")
    print(f"  ANY zone (1m/3m/5m): formed {st(d[d['any_zone']==1][POL])} | "
          f"none {st(d[d['any_zone']==0][POL])} | lift {lift(d,'any_zone'):+.3f}")
    for tf in ZONE_TFS:
        c = f"z_{tf}"
        print(f"  {tf} zone           : formed {st(d[d[c]==1][POL])} | "
              f"none {st(d[d[c]==0][POL])} | lift {lift(d,c):+.3f}")

    print(f"\n=== (2) by ZONE KIND (ob vs fvg, any TF -> use 5m then 3m then 1m kind) ===")
    d["kind"] = d["z_5m_kind"].fillna(d["z_3m_kind"]).fillna(d["z_1m_kind"])
    for k in ["ob", "fvg"]:
        sub = d[d["kind"] == k]
        print(f"  {k:4s}: {st(sub[POL])} | vs no-zone {st(d[d['any_zone']==0][POL])}")

    print(f"\n=== (3) per-YEAR (ANY-zone lift) + per-SYMBOL + call/put ===")
    for y in sorted(d["yr"].unique()):
        s = d[d["yr"] == y]
        print(f"  {y}: zone {st(s[s['any_zone']==1][POL])} | lift {lift(s,'any_zone'):+.3f}")
    for s, g in d.groupby("symbol"):
        print(f"  {s:8s}: zone {st(g[g['any_zone']==1][POL])} | lift {lift(g,'any_zone'):+.3f}")
    for lt, g in d.groupby("level_type"):
        print(f"  {lt} ({'call/short' if lt=='gwc' else 'put/long'}): "
              f"zone {st(g[g['any_zone']==1][POL])} | lift {lift(g,'any_zone'):+.3f}")

    print(f"\n=== (4) SHUFFLE-FLAG NULL: permute the any_zone flag within symbol, N=300 ===")
    rng = np.random.default_rng(11)
    real = lift(d, "any_zone")
    null = []
    for _ in range(300):
        dd = d.copy()
        dd["any_zone"] = dd.groupby("symbol")["any_zone"].transform(
            lambda s: rng.permutation(s.to_numpy()))
        null.append(lift(dd, "any_zone"))
    null = np.array([x for x in null if np.isfinite(x)])
    z = (real - null.mean()) / null.std() if null.std() > 0 else np.nan
    print(f"  real lift {real:+.4f} | null {null.mean():+.4f} +/- {null.std():.4f} | "
          f"z={z:+.2f} p(null>=real)={float((null>=real).mean()):.3f}")

    print(f"\n=== (5) DESIGN 2018-2022 vs OOS 2023-2026 (ANY-zone lift) ===")
    des, oos = d[d["yr"] <= 2022], d[d["yr"] >= 2023]
    print(f"  design lift {lift(des,'any_zone'):+.3f} (zone n {int((des['any_zone']==1).sum())}) | "
          f"OOS lift {lift(oos,'any_zone'):+.3f} (zone n {int((oos['any_zone']==1).sum())})")


def main() -> int:
    if "--analyze-only" in sys.argv:
        analyze(pd.read_parquet(CACHE))
        return 0
    d = build(force="--force" in sys.argv)
    analyze(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
