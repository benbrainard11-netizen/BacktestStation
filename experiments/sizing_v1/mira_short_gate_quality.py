"""Does the frozen 0.5818 gate actually select GOOD shorts, or does it generalize poorly to
the short side (it was implicitly fit in a long-biased regime where shorts exited at ~0R)?

Method: take ALL Jan-2026 post-sweep-SMT candidates the gate scored (969), reproduce the
official fill (v11 entry + smt_pivot_180s stop via base.first_entry_row), compute realized R
with the honest vectorized exit engine (trail_2R + costs), then for SHORTS test whether the
gate score p discriminates outcome:
  * corr(p, R) for shorts
  * mean R for gated (p>=0.5818) vs rejected (p<0.5818) shorts
  * R by gate-score quartile (monotone lift = the gate ranks shorts well)

No retuning. If the gate doesn't separate good shorts, that is the finding.

Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/mira_short_gate_quality.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exit_replay_oos as er  # noqa: E402

b = er.exp  # export_2025_oos_entries module (fill machinery + scoring helpers)

ARTIFACT = Path(r"C:\Users\benbr\bs-mira-v15\experiments\mira_v15_gate_validation"
                r"\artifacts\mira_structure_smt_final_2026.joblib")
COMBINED = Path(r"C:\Users\benbr\bs-mira-v15\experiments\mira_v15_gate_validation"
                r"\work_2026jan_mbo_oos\combined\mira_combined.parquet")
OOS_START, OOS_END_EXCL = "2026-01-01", "2026-02-06"
OUT = HERE / "out" / "mira_short_revalidation" / "jan2026_gate_quality_candidates.parquet"


def score_all() -> pd.DataFrame:
    """All post-sweep-SMT Jan candidates with the frozen gate score p (no gate cut, no dedup)."""
    bundle = joblib.load(ARTIFACT)
    assert bundle["train_window"]["start"] == "2026-02-06", "wrong frozen window"
    df = pd.read_parquet(COMBINED).copy()
    df["candidate_row_id"] = np.arange(len(df), dtype=np.int64)
    for c in ["touch_ts_utc", "trigger_ts_utc", "known_extreme.ts_utc", "trigger.price_ts_utc"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, errors="coerce")
    oos = df[
        df["trigger_ts_utc"].ge(pd.Timestamp(OOS_START, tz="UTC"))
        & df["trigger_ts_utc"].lt(pd.Timestamp(OOS_END_EXCL, tz="UTC"))
        & df["trigger_type"].eq("post_sweep_smt")
        & df["smt_anchor_side"].isin(["low", "high"])
        & df["symbol"].notna()
        & df[b.OPPORTUNITY_COL].notna()
    ].copy()
    oos["decision_offset_sec"] = b.DECISION_OFFSET_SEC
    oos["decision_ts_utc"] = oos["trigger_ts_utc"]
    for c in ["trigger_price", "known_extreme.price", "level_price"]:
        if c in oos.columns:
            oos[c] = pd.to_numeric(oos[c], errors="coerce")
    oos = oos[oos["trigger_price"].notna()].copy()
    x, _missing = b.prepare_score_matrix(oos, bundle)
    oos["p"] = bundle["model"].predict_proba(x)[:, 1]
    oos = b.add_filter_flags(oos)
    return oos, float(bundle["threshold"])


def fill_and_exit(oos: pd.DataFrame) -> pd.DataFrame:
    """Reproduce the official fill for every candidate, then realized R (trail_2R, net)."""
    oos = oos.copy()
    oos["trigger_date"] = oos["trigger_ts_utc"].dt.date
    recs = []
    groups = list(oos.groupby(["symbol", "trigger_date"], sort=True))
    for i, ((symbol, day), g) in enumerate(groups, 1):
        min_ts = g["trigger_ts_utc"].min() - pd.Timedelta(seconds=185)
        max_ts = g["trigger_ts_utc"].max() + pd.Timedelta(minutes=12) + er.HOLD
        sd = pd.Timestamp(min_ts.date(), tz="UTC")
        ed = pd.Timestamp(max_ts.date(), tz="UTC") + pd.Timedelta(days=1)
        if i % 20 == 0:
            print(f"  [{i}/{len(groups)}] {symbol} {day}", flush=True)
        try:
            arr = er.v7.load_quote_arrays(str(symbol), sd, ed, min_ts, max_ts)
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {symbol} {day}: {type(exc).__name__}", flush=True)
            continue
        for _, row in g.iterrows():
            entry = b.first_entry_row(row, arr)
            if entry is None:
                continue
            d = int(entry["direction"])
            E, S, R = entry["entry_px"], entry["stop_px"], entry["risk_points"]
            e_ns = pd.Timestamp(entry["entry_ts"]).value
            start = int(np.searchsorted(arr.ts_ns, e_ns, "left"))
            end = int(np.searchsorted(arr.ts_ns, e_ns + er.HOLD.value, "right"))
            if end <= start:
                continue
            if d == 1:
                f = arr.bid[start:end].astype(float); e, s, t2, t3 = E, S, E + 2 * R, E + 3 * R
            else:
                f = (-arr.ask[start:end]).astype(float); e, s, t2, t3 = -E, -S, -E + 2 * R, -E + 3 * R
            f = f[np.isfinite(f)]
            res = er.exits_for(f, e, s, R, t2, t3)
            if not res:
                continue
            gross, reason = res["trail_2R"]
            recs.append({"symbol": symbol, "direction": d, "p": float(row["p"]),
                         "risk_points": R, "r_net": er.net_R(gross, reason, str(symbol), R),
                         "reason": reason})
    return pd.DataFrame(recs)


def main() -> int:
    oos, thr = score_all()
    print(f"scored {len(oos)} post_sweep_smt candidates "
          f"(longs={int((oos.smt_anchor_side=='low').sum())} shorts={int((oos.smt_anchor_side=='high').sum())}), "
          f"threshold={thr:.4f}")
    res = fill_and_exit(oos)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    res.to_parquet(OUT, index=False)
    print(f"filled+exited {len(res)} candidates -> {OUT}\n")

    for nm, sub in [("ALL", res), ("LONGS", res[res.direction == 1]), ("SHORTS", res[res.direction == -1])]:
        gated = sub[sub.p >= thr]["r_net"]
        rej = sub[sub.p < thr]["r_net"]
        cc = sub[["p", "r_net"]].corr().iloc[0, 1] if len(sub) > 2 else np.nan
        print(f"### {nm} (n={len(sub)}) ###")
        print(f"   corr(p, R) = {cc:+.3f}")
        print(f"   GATED   p>={thr:.4f}: n={len(gated):3d} meanR={gated.mean():+.3f} win%={100*(gated>0).mean():.1f}")
        print(f"   REJECTED p< {thr:.4f}: n={len(rej):3d} meanR={rej.mean():+.3f} win%={100*(rej>0).mean():.1f}")
        # quartile lift
        if len(sub) >= 8:
            sub = sub.copy()
            sub["q"] = pd.qcut(sub["p"], 4, labels=["Q1lo", "Q2", "Q3", "Q4hi"], duplicates="drop")
            qlift = sub.groupby("q", observed=True)["r_net"].agg(["count", "mean"])
            print(f"   by gate-score quartile:\n{qlift.round(3).to_string()}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
