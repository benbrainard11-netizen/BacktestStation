"""Mira gate — champion/challenger harness (ADDITIVE; touches no live artifact).

WHY: a durable structure to evolve the gate model over time. Champion = the frozen live gate.
Challenger = any new feature set / model. A challenger is PROMOTED only if it beats the champion on a
FROZEN out-of-sample holdout. Everything is cached + versioned so artifacts are never re-derived or
lost (the gate-validation work dir got cleaned mid-session — this prevents that).

THREE PARTS:
  1. build_dataset(name,start,end): regenerate the labeled 139-feature candidate matrix via the real
     detect pipeline (MBO bookproxy etc.), compute the gate's label (extreme_hold_move@60m), cache to
     data/<name>.parquet + a manifest (params + git SHA + row hash). Idempotent.
  2. eval_model(scorer, ds): OOS metrics on a dataset — AUC, gated count, gated success-rate (precision
     at the threshold), base rate, lift. Label-based (fast, no fill sim); realized-R is a later add-on.
  3. scoreboard: append every champion/challenger eval with its config -> runs/scoreboard.csv.

WINDOWS (locked): champion train = 2026-02-06..05-20; OOS holdout = 2026-05-21..06-05 (post-training,
fresh); Jan-2026 = secondary pre-training OOS. Data ends 2026-06-05.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/harness.py --eval-champion --oos jan_smoke
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\backend")
import detect as D  # noqa: E402
import gate as G  # noqa: E402
import build_trigger_candidates as BTC  # noqa: E402

DATA = HERE / "data"; RUNS = HERE / "runs"
SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}
OPP = "combined.sweep_setup_event_id"
MIN_AWAY_TK, REBREAK_TK, FWD_MIN = 8.0, 1.0, 60
WINDOWS = {  # name -> (start, end)  [locked]
    "train": ("2026-02-06", "2026-05-20"),
    "oos_holdout": ("2026-05-21", "2026-06-05"),
    "jan_oos": ("2026-01-02", "2026-02-04"),
    "jan_smoke": ("2026-01-05", "2026-01-09"),
    "june_oos": ("2026-06-08", "2026-06-09"),
    "sample2025": ("2025-03-10", "2025-03-14"),  # A3 quote sample week (bar-touch, no MBO era)
}

# SMT events DB — EXPLICIT per window. detect.py's silent default is live_engine/data/meta.sqlite,
# which does NOT exist on this machine; _load_smt_events returns EMPTY for a missing path, so a build
# "succeeds" with 0 post_sweep_smt rows (the 2026-06-09 empty-train bug). Repo meta.sqlite has 5m SMT
# through 2026-05-22 only; windows past that need a 5m re-scan db (fix_holdout_5m.py).
SMT_DB_MAIN = Path(r"C:\Users\benbr\BacktestStation\data\meta.sqlite")
# 5m-VALID coverage per db, DATE-RESOLVED (name-keyed mapping bit us 2026-06-10: a window named
# "holdout_wall" fell through to meta.sqlite, which has no 5m after 2026-05-22 -> degraded build).
SMT_5M_RANGES = [
    (DATA / "sample2025_smt5m.sqlite", "2025-03-10", "2025-03-15"),  # A3 quote sample week
    (SMT_DB_MAIN, "2026-01-01", "2026-05-22"),
    (DATA / "holdout_smt5m.sqlite", "2026-05-21", "2026-06-06"),
    (DATA / "june_smt5m.sqlite", "2026-06-08", "2026-06-10"),
]


def _smt_db_for(name: str, start: str, end: str) -> Path:
    env = os.environ.get("MIRA_SMT_DB")
    if env:
        return Path(env)
    for db, lo, hi in SMT_5M_RANGES:
        if start >= lo and end <= hi:
            return db
    raise RuntimeError(
        f"window {name} {start}..{end} not fully covered by any 5m-valid SMT db "
        f"({[(d.name, lo, hi) for d, lo, hi in SMT_5M_RANGES]}) — split the window or re-scan")


def _smt_count(db: Path, start: str, end: str) -> int:
    end_excl = (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    with sqlite3.connect(db) as con:
        return con.execute(
            "SELECT count(*) FROM research_events WHERE feature_name IN "
            "('smt_prev_candle_divergence','smt_htf_reference_divergence') "
            "AND bar_end_utc >= ? AND bar_end_utc < ?", (start, end_excl)).fetchone()[0]

# --- MBO day-read cache (prevents the per-trigger full-file re-read I/O storm / hang) ---
_V0 = BTC.v0; _ORIG_RMW = _V0._read_mbo_window; _MC: dict = {}; _MO: list = []


def _cached_rmw(*, data_root, symbol, start_ts, end_ts):
    s = pd.Timestamp(start_ts).tz_convert("UTC") if pd.Timestamp(start_ts).tzinfo else pd.Timestamp(start_ts, tz="UTC")
    e = pd.Timestamp(end_ts).tz_convert("UTC") if pd.Timestamp(end_ts).tzinfo else pd.Timestamp(end_ts, tz="UTC")
    if s.date() != (e - pd.Timedelta(microseconds=1)).date():
        return _ORIG_RMW(data_root=data_root, symbol=symbol, start_ts=start_ts, end_ts=end_ts)
    key = (str(symbol), s.date())
    if key not in _MC:
        d0 = pd.Timestamp(s.date(), tz="UTC")
        full = _ORIG_RMW(data_root=data_root, symbol=symbol, start_ts=d0, end_ts=d0 + pd.Timedelta(days=1))
        if len(full):
            full = full.copy(); full["ts_event"] = pd.to_datetime(full["ts_event"], utc=True)
        _MC[key] = full; _MO.append(key)
        while len(_MO) > 2:
            _MC.pop(_MO.pop(0), None)
    df = _MC[key]
    return df if df is None or not len(df) else df[(df["ts_event"] >= s) & (df["ts_event"] < e)]


_V0._read_mbo_window = _cached_rmw

# Cache the (huge) SMT-DB load across the per-symbol detect calls in one build.
# Keyed by db path: one process may build windows backed by DIFFERENT SMT dbs (train vs oos_holdout).
_ORIG_LOAD_SMT = BTC._load_smt_events
_SMT_CACHE: dict = {}


def _cached_load_smt(db_path):
    key = str(db_path)
    if key not in _SMT_CACHE:
        _SMT_CACHE[key] = _ORIG_LOAD_SMT(db_path)
    return _SMT_CACHE[key]


BTC._load_smt_events = _cached_load_smt


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=HERE).decode().strip()
    except Exception:
        return "nogit"


def _label(cands: pd.DataFrame, bars1m: dict) -> pd.Series:
    """extreme_hold_move@60m on the PRIMARY symbol: (extreme NOT rebroken >1tk) AND (moved >=8tk) in [t,t+60m].
    Direct column access (itertuples is unsafe here: >255 cols + leading-underscore col -> positional)."""
    out = np.full(len(cands), np.nan)
    sym = cands["symbol"].astype(str).to_numpy()
    side = cands["smt_anchor_side"].astype(str).to_numpy()
    ext = pd.to_numeric(cands["_known_extreme_price"], errors="coerce").to_numpy()
    ts = pd.to_datetime(cands["trigger_ts_utc"], utc=True).to_numpy()
    for i in range(len(cands)):
        s = sym[i]
        if s not in bars1m or not np.isfinite(ext[i]):
            continue
        t = pd.Timestamp(ts[i])
        b = bars1m[s]
        sub = b[(b.index >= t.floor("min")) & (b.index < t + pd.Timedelta(minutes=FWD_MIN))]
        if sub.empty:
            continue
        hi = float(sub["high"].max()); lo = float(sub["low"].min()); tk = TICK[s]; e = float(ext[i])
        away = (hi - e) if side[i] == "low" else (e - lo)
        rebr = (e - lo) if side[i] == "low" else (hi - e)
        out[i] = float((rebr <= REBREAK_TK * tk) and (away >= MIN_AWAY_TK * tk))
    return pd.Series(out, index=cands.index)


def build_dataset(name: str, start: str, end: str) -> pd.DataFrame:
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / f"{name}.parquet"
    smt_db = _smt_db_for(name, start, end)
    if path.exists():
        mpath = DATA / f"{name}.manifest.json"
        recorded = json.loads(mpath.read_text()).get("smt_db") if mpath.exists() else None
        if recorded is not None and Path(recorded) != smt_db:
            print(f"[build_dataset {name}] CACHE POISONED: built with smt_db={Path(recorded).name}, "
                  f"resolver says {smt_db.name} — deleting + rebuilding", flush=True)
            path.unlink()
            mpath.unlink()
        else:
            return pd.read_parquet(path)
    sd, ed = pd.Timestamp(start).date(), pd.Timestamp(end).date()
    if not smt_db.exists():
        raise RuntimeError(f"SMT db missing: {smt_db} — refusing to build {name} "
                           "(a missing db silently yields 0 post_sweep_smt rows)")
    n_smt = _smt_count(smt_db, start, end)
    if n_smt == 0:
        raise RuntimeError(f"SMT db {smt_db} has 0 SMT events in {start}..{end} — "
                           f"build {name} would silently produce 0 rows")
    print(f"[build_dataset {name}] {start}..{end} — regenerating via detect "
          f"(smt_db={smt_db.name}, {n_smt} SMT events in window)...", flush=True)
    # Per-symbol checkpoints: this box hard-crashes (5x since 6/7); a crash mid-build now
    # only loses the symbol in progress instead of the whole window.
    ck = DATA / "_parts"
    ck.mkdir(exist_ok=True)
    parts = []
    for s in SYMBOLS:
        cp = ck / f"{name}__{s}.parquet"
        if cp.exists():
            c = pd.read_parquet(cp)
            print(f"  {s}: {len(c)} candidate rows (CHECKPOINT)", flush=True)
        else:
            c = D.compute_candidates(s, sd, ed, sweep_quality=None, smt_db=smt_db)
            if c is not None and len(c):
                c.to_parquet(cp, index=False)
            print(f"  {s}: {0 if c is None else len(c)} candidate rows", flush=True)
        if c is not None and len(c):
            parts.append(c)
    if not parts:
        raise RuntimeError("no candidates")
    df = pd.concat(parts, ignore_index=True)
    df["trigger_ts_utc"] = pd.to_datetime(df["trigger_ts_utc"], utc=True)
    df = df[(df.trigger_type == "post_sweep_smt") & df.smt_anchor_side.isin(["low", "high"])
            & df.trigger_price.notna() & df[OPP].notna()].copy()
    # Label = the pipeline's OWN forward outcome (extreme_hold_move@60m), already computed by
    # build_trigger_candidates._target_features and carried into the combined. No bar recompute needed.
    LABEL_COL = "target.60m.extreme_hold_move"
    if LABEL_COL not in df.columns:
        raise RuntimeError(f"missing label column {LABEL_COL}")
    df["label"] = pd.to_numeric(df[LABEL_COL], errors="coerce")
    df = df[df["label"].notna()].reset_index(drop=True)
    if df.empty:
        raise RuntimeError(f"{name}: 0 rows after post_sweep_smt/label filters — "
                           "NOT caching an empty dataset (would poison downstream evals as 'no setups')")
    df.to_parquet(path, index=False)
    for s in SYMBOLS:  # window cached whole — clear the per-symbol checkpoints
        cp = ck / f"{name}__{s}.parquet"
        if cp.exists():
            cp.unlink()
    manifest = {"name": name, "start": start, "end": end, "smt_db": str(smt_db), "rows": int(len(df)),
                "label_pos_rate": round(float(df["label"].mean()), 4), "git_sha": _git_sha(),
                "row_hash": hashlib.sha256(pd.util.hash_pandas_object(df[["symbol", "trigger_ts_utc"]]).values.tobytes()).hexdigest()[:16],
                "label": "extreme_hold_move@60m", "horizons_min": FWD_MIN}
    (DATA / f"{name}.manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    print(f"  -> {len(df)} labeled rows (pos={manifest['label_pos_rate']}) cached at {path}", flush=True)
    return df


def eval_model(scores: np.ndarray, ds: pd.DataFrame, threshold: float) -> dict:
    """Label metrics (AUC on full pop) + gated metrics AFTER one-per-opportunity dedup (the validated
    tradeable methodology: among gated, keep first by trigger_ts/trigger_id per sweep opportunity)."""
    from sklearn.metrics import roc_auc_score
    labels = ds["label"].to_numpy()
    base = float(np.mean(labels))
    auc = float(roc_auc_score(labels, scores)) if len(np.unique(labels)) > 1 else float("nan")
    g = ds.loc[scores >= threshold].copy()
    if OPP in g.columns and "trigger_id" in g.columns and not g.empty:
        g = (g.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
             .groupby(OPP, sort=False).head(1))
    gl = g["label"].to_numpy()
    g_succ = float(gl.mean()) if len(gl) else float("nan")
    out = {"n": int(len(labels)), "base_rate": round(base, 4), "auc": round(auc, 4),
           "gated_n": int(len(g)), "gated_success": round(g_succ, 4),
           "lift_vs_base": round(g_succ - base, 4)}
    if "realized_r" in g.columns:
        rr = pd.to_numeric(g["realized_r"], errors="coerce").dropna()
        out.update({"R_n": int(len(rr)), "R_mean": round(float(rr.mean()), 3) if len(rr) else None,
                    "R_win": round(float((rr > 0).mean()), 3) if len(rr) else None,
                    "R_sum": round(float(rr.sum()), 1) if len(rr) else None})
    return out


def train_challenger(train_ds: pd.DataFrame, mode: str, gate) -> tuple:
    """Train a challenger RF on the train dataset, same feature space as the champion.
    modes: 'retrain_same' (reproducibility baseline) | 'drop_smt' (confirm SMT low-importance).
    Returns (pipeline, kept_columns, prev_q75_threshold). Encoding reuses the gate's encoder so the
    feature space is identical; threshold = q75 of train scores (the champion's prev_q75 method)."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    X = gate._encode(train_ds); y = train_ds["label"].astype(int)
    cols = list(X.columns)
    if mode == "drop_smt":
        cols = [c for c in cols if "smt" not in c.lower()]
    X = X[cols]
    pipe = Pipeline([("imp", SimpleImputer(strategy="median")),
                     ("rf", RandomForestClassifier(n_estimators=250, max_depth=5, min_samples_leaf=20,
                                                   class_weight="balanced_subsample", random_state=2605, n_jobs=1))])
    pipe.fit(X, y)
    thr = float(pd.Series(pipe.predict_proba(X)[:, 1]).quantile(0.75))
    return pipe, cols, thr


def score_challenger(pipe, cols, ds: pd.DataFrame, gate) -> np.ndarray:
    return pipe.predict_proba(gate._encode(ds)[cols])[:, 1]


def scoreboard_append(row: dict) -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    row = {**row, "ts_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    p = RUNS / "scoreboard.csv"
    df = pd.concat([pd.read_csv(p), pd.DataFrame([row])], ignore_index=True) if p.exists() else pd.DataFrame([row])
    df.to_csv(p, index=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", help="window name to (re)build")
    ap.add_argument("--eval-champion", action="store_true")
    ap.add_argument("--challenger", choices=["retrain_same", "drop_smt"], help="train+eval a challenger")
    ap.add_argument("--train", default="train", help="train window name (for --challenger)")
    ap.add_argument("--oos", default="oos_holdout", help="window name to evaluate on")
    args = ap.parse_args()

    if args.build:
        s, e = WINDOWS[args.build]
        build_dataset(args.build, s, e)
        return 0

    if args.eval_champion:
        s, e = WINDOWS[args.oos]
        ds = build_dataset(args.oos, s, e)
        gate = G.Gate()
        scores = gate.score(ds)
        m = eval_model(scores, ds, gate.threshold)
        print(f"\n=== CHAMPION (frozen gate) on OOS={args.oos} ===\n  {m}")
        scoreboard_append({"ts_utc": "stamp_after", "model": "champion_frozen", "oos": args.oos,
                           "threshold": round(gate.threshold, 4), **m, "git_sha": _git_sha()})
        print(f"  appended to {RUNS / 'scoreboard.csv'}")

    if args.challenger:
        ts, te = WINDOWS[args.train]; os_, oe = WINDOWS[args.oos]
        train_ds = build_dataset(args.train, ts, te)
        oos_ds = build_dataset(args.oos, os_, oe)
        gate = G.Gate()
        pipe, cols, thr = train_challenger(train_ds, args.challenger, gate)
        scores = score_challenger(pipe, cols, oos_ds, gate)
        m = eval_model(scores, oos_ds, thr)
        print(f"\n=== CHALLENGER '{args.challenger}' (train={args.train}) on OOS={args.oos} ===\n  {m}  thr={thr:.4f}")
        scoreboard_append({"ts_utc": "stamp_after", "model": f"challenger_{args.challenger}", "oos": args.oos,
                           "threshold": round(thr, 4), **m, "git_sha": _git_sha()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
