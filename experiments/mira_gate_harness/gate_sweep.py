"""Gate-threshold sweep on the frozen champion — answers the live-box memo's test #2.

Scores the FULL candidate population of each locked window with the frozen gate, applies the
harness gating convention (threshold, then ONE trade per combined.sweep_setup_event_id — first
by trigger time), and sweeps the arm threshold. realized_r is the cached live-faithful replay
(trail_2R exit, entry+stop exactly as deployed; computed by compute_full_r.py). Parity replay
2026-06-11 proved live scores == replay scores (mean delta +0.005), so thresholds transfer.

Decision framing: lowering the gate ADDS trades = dedup_set(lower_gate) minus dedup_set(0.5818).
The flip is judged on the ADDED set's economics + monthly consistency, not the blended total
(the blend always looks fine because the champion-gated core dominates).

Caveats stated up front:
  * realized_r exit = trail_2R. Live flipped to fixed_2R on 2026-06-10; exit_sweep.py showed the
    two within noise on gated trades (fixed_3R beats both). Exit is a separate, already-swept
    axis; it does not move WHERE the gate sits.
  * train window (Feb 6 - May 20) is the champion's training period -> in-sample-ish. True OOS
    = jan_oos + oos_holdout; the verdict weighs OOS.
  * Harness datasets include YM; live trades ES/NQ/RTY (no_ym). Headline = no-YM view.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/gate_sweep.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\backend")
import gate as G  # noqa: E402

DATA = HERE / "data"
RUNS = HERE / "runs"
WINDOWS = ["jan_oos", "train", "oos_holdout"]          # june_oos: 6/30 realized_r filled — too thin
CHAMP_THR = 0.5818010299926861
DECISION_GATES = [0.50, 0.55, CHAMP_THR, 0.62]
FINE_GRID = np.round(np.arange(0.45, 0.70, 0.01), 4)
OPP = "combined.sweep_setup_event_id"
DPR = 300.0  # live eval profile $/R


def load_scored(name: str) -> pd.DataFrame:
    ds = pd.read_parquet(DATA / f"{name}.parquet")
    ds["trigger_ts_utc"] = pd.to_datetime(ds["trigger_ts_utc"], utc=True)
    ds["champ_score"] = G.Gate().score(ds)
    ds["realized_r"] = pd.to_numeric(ds["realized_r"], errors="coerce")
    ds["window"] = name
    return ds


def gated_deduped(ds: pd.DataFrame, thr: float) -> pd.DataFrame:
    """Exact harness convention: threshold first, then one trade per sweep-setup event."""
    g = ds[ds["champ_score"] >= thr]
    return g.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable").groupby(OPP, sort=False).head(1)


def stats(g: pd.DataFrame, weeks: float) -> dict:
    r = g["realized_r"].dropna()
    if r.empty:
        return dict(n=0, n_filled=0, tpw=0.0, win=np.nan, mean_r=np.nan, sum_r=0.0, maxdd=np.nan)
    cum = r.sort_index().cumsum()
    maxdd = float((cum.cummax() - cum).max())
    return dict(n=len(g), n_filled=len(r), tpw=len(r) / weeks, win=float((r > 0).mean()),
                mean_r=float(r.mean()), sum_r=float(r.sum()), maxdd=maxdd)


def fmt(name: str, s: dict) -> str:
    if s["n_filled"] == 0:
        return f"    {name:26s} n=0"
    return (f"    {name:26s} n={s['n_filled']:4d}  {s['tpw']:5.1f}/wk  win {s['win']*100:4.1f}%  "
            f"meanR {s['mean_r']:+.3f}  sumR {s['sum_r']:+8.1f}  maxDD {s['maxdd']:6.1f}R  "
            f"(${s['sum_r']*DPR:+,.0f})")


def weeks_of(sub: pd.DataFrame) -> float:
    return max(sub["trigger_ts_utc"].dt.date.nunique(), 1) / 5.0


def main() -> int:
    frames = [load_scored(w) for w in WINDOWS]
    allds = pd.concat(frames, ignore_index=True).sort_values("trigger_ts_utc").reset_index(drop=True)
    print(f"scored {len(allds)} candidates across {WINDOWS} "
          f"(realized_r filled: {allds['realized_r'].notna().sum()})")

    # ---- sanity anchor: champion gate + harness dedupe must reproduce the night report ----
    jan = gated_deduped(allds[allds["window"] == "jan_oos"], CHAMP_THR)
    jr = jan["realized_r"].dropna()
    ok = 130 <= len(jr) <= 145 and abs(jr.mean() - 0.456) <= 0.03
    print(f"[anchor] jan_oos @champion deduped: n={len(jr)} meanR={jr.mean():+.3f} "
          f"(harness anchor: 139 / +0.456) -> {'OK' if ok else 'MISMATCH - STOP'}")
    if not ok:
        return 1

    for no_ym in (True, False):
        ds = allds[allds["symbol"] != "YM.c.0"] if no_ym else allds
        tag = "no_ym (LIVE config: ES/NQ/RTY)" if no_ym else "all 4 symbols (harness)"
        print(f"\n{'=' * 104}\nSWEEP — {tag}\n{'=' * 104}")
        for w in WINDOWS + ["ALL"]:
            sub = ds if w == "ALL" else ds[ds["window"] == w]
            weeks = weeks_of(sub)
            print(f"  -- {w}  ({sub['trigger_ts_utc'].dt.date.nunique()} trading days) --")
            for thr in DECISION_GATES:
                lab = f"gate >= {thr:.4f}" + ("  << champion" if abs(thr - CHAMP_THR) < 1e-9 else "")
                print(fmt(lab, stats(gated_deduped(sub, thr), weeks)))

        print(f"\n  ADDED TRADES vs champion ({tag}) — dedup_set(gate) minus dedup_set(0.5818):")
        for w in WINDOWS + ["ALL"]:
            sub = ds if w == "ALL" else ds[ds["window"] == w]
            weeks = weeks_of(sub)
            champ_idx = set(gated_deduped(sub, CHAMP_THR).index)
            print(f"  -- {w} --")
            for thr in (0.50, 0.55):
                added = gated_deduped(sub, thr)
                added = added[~added.index.isin(champ_idx)]
                print(fmt(f"added by gate {thr:.2f}", stats(added, weeks)))

        print(f"\n  0.55-flip ADDED trades, MONTHLY ({tag}):")
        champ_idx = set(gated_deduped(ds, CHAMP_THR).index)
        added = gated_deduped(ds, 0.55)
        added = added[~added.index.isin(champ_idx)].copy()
        added["month"] = added["trigger_ts_utc"].dt.to_period("M").astype(str)
        for m, g in added.groupby("month"):
            r = g["realized_r"].dropna()
            tag_m = " (in-sample)" if "2026-02" <= m <= "2026-05" else " (OOS)"
            print(f"    {m}{tag_m}: n={len(r):3d}  win {(r > 0).mean()*100:4.1f}%  "
                  f"meanR {r.mean():+.3f}  sumR {r.sum():+7.1f}")

    # ---- fine curve -> CSV (no-YM view) ----
    rows = []
    ds = allds[allds["symbol"] != "YM.c.0"]
    for w in WINDOWS + ["ALL"]:
        sub = ds if w == "ALL" else ds[ds["window"] == w]
        weeks = weeks_of(sub)
        for thr in FINE_GRID:
            rows.append({"window": w, "gate": thr, **stats(gated_deduped(sub, thr), weeks)})
    out = RUNS / "gate_sweep_curve.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nfine curve (0.45..0.69 x windows, no-YM, deduped) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
