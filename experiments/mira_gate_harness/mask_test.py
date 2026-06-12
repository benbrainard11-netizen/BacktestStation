"""Bookproxy mask test — can a bar-close-feasible gate (no +60s post-trigger orderflow) still
select a sub-10s-edge trade set? Decides PLAN_fast_arm_path step 3 (see ANSWER_ripe_sec doc).

Method:
  * MASKED gate: the frozen champion scored with its 15 cluster.bookproxy.* features set to NaN
    -> SimpleImputer(median) substitutes the TRAINING MEDIAN (the pipeline's own
    feature-unavailable path). This is predict-time ablation: a LOWER-BOUND proxy for a properly
    retrained 124-feature "fast gate" (stated caveat — ablation can underprice a retrain).
  * EQUAL SELECTIVITY: masked threshold set so the masked gate passes the SAME COUNT of
    train-window candidates as the champion (apples-to-apples trade frequency).
  * NEGATIVE CONTROL: same procedure masking 15 RANDOM non-bookproxy numeric features (seed 7).
    If the control degrades lag-0 R as much as the bookproxy mask, the test is uninformative;
    if bookproxy-mask hurts far more, the conclusion is specific to post-trigger orderflow.
  * Each gate's un-deduped no-YM trigger stream runs the VALIDATED lag ladder
    (entry_sweep.drive_one — G1 bit-exact vs cached realized_r) at 0/5/10/30/60s rungs with
    per-symbol occupancy. Champion reference rungs: runs/lag_ladder_subminute.log (same engine).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/mask_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import entry_sweep as ES  # noqa: E402
import gate as G  # noqa: E402

DATA, RUNS = HERE / "data", HERE / "runs"
WINDOWS = ["jan_oos", "train", "oos_holdout"]
OOS = ["jan_oos", "oos_holdout"]
LAGS = [0.0, 0.083, 0.167, 0.5, 1.0]
_NS = ES._NS

gate = G.Gate()
BOOKPROXY = [c for c in gate.raw_features if c.startswith("cluster.bookproxy.")]
assert len(BOOKPROXY) == 15, f"expected 15 bookproxy features, got {len(BOOKPROXY)}"


def load_all() -> pd.DataFrame:
    frames = []
    for w in WINDOWS:
        ds = pd.read_parquet(DATA / f"{w}.parquet")
        ds["trigger_ts_utc"] = pd.to_datetime(ds["trigger_ts_utc"], utc=True)
        ds["window"] = w
        frames.append(ds)
    return pd.concat(frames, ignore_index=True)


def masked_scores(ds: pd.DataFrame, cols: list[str]) -> np.ndarray:
    df = ds.copy()
    for c in cols:
        if c in df.columns:
            df[c] = np.nan
    return gate.score(df)


def equal_selectivity_threshold(scores: np.ndarray, train_mask: np.ndarray, n_target: int) -> float:
    s = np.sort(scores[train_mask])[::-1]
    return float(s[n_target - 1])


def ladder(trigs: pd.DataFrame, label: str) -> dict[float, pd.DataFrame]:
    rows: dict[float, list] = {L: [] for L in LAGS}
    for sym, g in trigs.groupby("symbol", sort=False):
        busy = {L: -1 for L in LAGS}
        for _d, gd in g.assign(_d=g["trigger_ts_utc"].dt.date).groupby("_d", sort=True):
            arr = ES.RR.load_mbp1(str(sym), gd["trigger_ts_utc"].min() - pd.Timedelta(seconds=200),
                                  gd["trigger_ts_utc"].max() + pd.Timedelta(minutes=115))
            for row in gd.itertuples():
                for L in LAGS:
                    arm_n = int(row.trigger_ts_utc.value) + int(L * 60 * _NS)
                    if arm_n < busy[L]:
                        rows[L].append(dict(window=row.window, filled=False, net_r=np.nan, reason="blocked"))
                        continue
                    if arr is None:
                        rows[L].append(dict(window=row.window, filled=False, net_r=np.nan, reason="no_data"))
                        continue
                    r = ES.drive_one(arr, row, L, "live_current")
                    busy[L] = max(busy[L], int(r.pop("busy_until")))
                    rows[L].append(dict(window=row.window, **r))
    out = {L: pd.DataFrame(v) for L, v in rows.items()}
    print(f"\n  == {label}: lag rungs ==")
    for scope, wins in [("OOS", OOS), ("train(IS)", ["train"])]:
        for L in LAGS:
            f = out[L]
            sub = f[f["window"].isin(wins)]
            filled = sub[sub["filled"] == True]  # noqa: E712
            r = filled["net_r"]
            print(f"    {scope:9s} lag={L*60:4.0f}s  n={len(sub):4d} filled={len(filled):4d} "
                  f"win={(r>0).mean()*100 if len(r) else 0:4.1f}%  meanR/fill={r.mean() if len(r) else 0:+7.3f}  "
                  f"R/trig={r.sum()/max(len(sub),1):+7.3f}", flush=True)
    return out


def main() -> int:
    allds = load_all()
    print(f"population: {len(allds)}", flush=True)
    champ = gate.score(allds)
    train_mask = (allds["window"] == "train").to_numpy()
    n_champ_train = int((champ[train_mask] >= gate.threshold).sum())

    rng = np.random.default_rng(7)
    numeric_pool = [c for c in gate._numeric_raw if c not in BOOKPROXY]
    control_cols = sorted(rng.choice(numeric_pool, size=15, replace=False))
    print(f"champion train passers: {n_champ_train}  (threshold {gate.threshold:.4f})")
    print(f"control-masked features: {control_cols}")

    sets = {}
    for label, cols in [("masked_bookproxy", BOOKPROXY), ("masked_control15", control_cols)]:
        sc = masked_scores(allds, cols)
        d = np.abs(sc - champ)
        thr = equal_selectivity_threshold(sc, train_mask, n_champ_train)
        sel = sc >= thr
        champ_sel = champ >= gate.threshold
        jac = (sel & champ_sel).sum() / max((sel | champ_sel).sum(), 1)
        print(f"\n[{label}] mean|dScore|={d.mean():.4f}  thr={thr:.4f}  "
              f"passers all-windows: {int(sel.sum())} vs champion {int(champ_sel.sum())}  "
              f"jaccard={jac:.3f}", flush=True)
        assert d.mean() > 1e-4, "mask had no effect on scores — masking is broken"
        trigs = allds[sel & (allds["symbol"] != "YM.c.0")].copy()
        trigs = trigs.sort_values(["symbol", "trigger_ts_utc", "trigger_id"], kind="stable").reset_index(drop=True)
        print(f"[{label}] no-YM trigger stream: {len(trigs)} ({trigs.groupby('window').size().to_dict()})")
        sets[label] = ladder(trigs, label)

    print("\nReference (champion gate, same engine/rungs): runs/lag_ladder_subminute.log — "
          "OOS R/trig: 0s +0.244 / 5s +0.176 / 10s +0.094 / 30s +0.039 / 60s -0.052")
    for label, frames in sets.items():
        pd.concat([f.assign(lag_fixed=L) for L, f in frames.items()], ignore_index=True) \
            .to_parquet(RUNS / f"mask_test_{label}.parquet", index=False)
    print(f"per-trigger results -> {RUNS}/mask_test_*.parquet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
