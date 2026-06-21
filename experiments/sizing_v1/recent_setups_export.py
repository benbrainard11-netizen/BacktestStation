"""Export per-setup 'should-have-fired' rows for cross-referencing against the live PC's
up/down/reconnect/lockout logs, + the gate-score marginal-band (parity-sensitivity) distribution.

One row per detected post-sweep-SMT setup:
  trigger_ts_utc, symbol, direction(long/short), gate_score, gated, marginal(0.5818-0.66),
  armed(gated & one-per-opportunity), entered(armed & reclaim filled), entry_px, stop_px,
  risk_points, r_trail_2r_net, exit_reason, day_regime, window.

DATA LIMIT: on-disk data ends 2026-05-22; the live window (~May 29-Jun 5) is unreplayable here, so
timestamps below do NOT overlap the live logs. Windows produced:
  jan_oos  : Jan-2026 full OOS (pre-training, real-MBO) -> the large-N reference for the distribution.
  may21_oos: 2026-05-21 (post-training OOS, real-MBO) -> the single most-recent clean day.
To get the ACTUAL live window: pull recent Databento MBO (May23-Jun5) and run --window custom
--start 2026-05-23 --end 2026-06-05. Same schema -> then the timestamp cross-ref works.

No gate retuning, no live connection.
Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/recent_setups_export.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import exit_replay_oos as er  # noqa: E402  -> er.exp (export_2025 b), er.v7, er.exits_for, er.net_R, er.HOLD
import detect as D  # noqa: E402
import gate as G  # noqa: E402

b = er.exp
GATE = G.Gate()
THR = GATE.threshold
OPP = "combined.sweep_setup_event_id"
BARS = Path(r"D:\data\processed\bars\timeframe=1m")
OUTDIR = HERE / "out" / "mira_short_revalidation"
JAN_COMBINED = Path(r"C:\Users\benbr\bs-mira-v15\experiments\mira_v15_gate_validation"
                    r"\work_2026jan_mbo_oos\combined\mira_combined.parquet")
JAN_ENTRIES = Path(r"C:\Users\benbr\bs-mira-v15\experiments\mira_v15_gate_validation"
                   r"\out\mira_2026jan_real_mbo_oos_model_reclaim_2r_entries.parquet")
JAN_TRAIL = OUTDIR / "jan2026_trail_2R.parquet"
MARG_HI = 0.66


def day_ret(symbol: str, date: str) -> float:
    try:
        bb = pd.read_parquet(BARS / f"symbol={symbol}" / f"date={date}",
                             columns=["ts_event", "open", "close"]).sort_values("ts_event")
        o, c = float(bb["open"].iloc[0]), float(bb["close"].iloc[-1])
        return (c - o) / o if o else np.nan
    except Exception:
        return np.nan


def score_flag(cands: pd.DataFrame, window: str) -> pd.DataFrame:
    """Filter post_sweep_smt, score with the live gate, flag gated/marginal/armed."""
    c = cands.copy()
    c["trigger_ts_utc"] = pd.to_datetime(c["trigger_ts_utc"], utc=True)
    mask = ((c["trigger_type"] == "post_sweep_smt") & (c["smt_anchor_side"].isin(["low", "high"]))
            & c["trigger_price"].notna())
    if OPP in c.columns:                                     # match official one-per-opportunity universe
        mask &= c[OPP].notna()
    pss = c[mask].copy()
    if pss.empty:
        return pss
    pss = b.add_filter_flags(pss)                            # no_ym / fav_level / daily_inside (first_entry_row reads these)
    pss["decision_ts_utc"] = pss["trigger_ts_utc"]          # find_entry_pos needs this
    pss["decision_offset_sec"] = b.DECISION_OFFSET_SEC
    pss["gate_score"] = GATE.score(pss)
    pss["direction"] = np.where(pss["smt_anchor_side"] == "low", "long", "short")
    pss["gated"] = pss["gate_score"] >= THR
    pss["marginal"] = (pss["gate_score"] >= THR) & (pss["gate_score"] <= MARG_HI)
    # armed = gated & survives one-per-opportunity (first by trigger_ts, trigger_id)
    pss["armed"] = False
    g = pss[pss["gated"]].copy()
    if not g.empty and OPP in g.columns:
        keep = (g.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
                .groupby(OPP, sort=False).head(1).index)
        pss.loc[keep, "armed"] = True
    elif not g.empty:
        pss.loc[g.index, "armed"] = True
    pss["window"] = window
    pss["date"] = pss["trigger_ts_utc"].dt.date.astype(str)
    pss["day_regime"] = ["down" if (r := day_ret(s, d)) < 0 else ("up" if np.isfinite(r) else "na")
                         for s, d in zip(pss["symbol"], pss["date"])]
    return pss


def attach_R_jan(rows: pd.DataFrame) -> pd.DataFrame:
    """Entered + R for Jan via the validated committed entries + trail replay (no re-fill)."""
    comm = pd.read_parquet(JAN_ENTRIES)
    comm["trigger_ts"] = pd.to_datetime(comm["trigger_ts"], utc=True)
    comm["entry_ts"] = pd.to_datetime(comm["entry_ts"], utc=True)
    tr = pd.read_parquet(JAN_TRAIL)
    tr["entry_ts"] = pd.to_datetime(tr["entry_ts"], utc=True)
    ent = comm.merge(tr[["symbol", "entry_ts", "direction", "r_signal_net", "reason_signal"]],
                     on=["symbol", "entry_ts", "direction"], how="left")
    ent = ent.rename(columns={"trigger_ts": "trigger_ts_utc", "r_signal_net": "r_trail_2r_net",
                              "reason_signal": "exit_reason"})
    key = ["symbol", "trigger_ts_utc"]
    ent = ent.drop_duplicates(subset=key)                    # avoid R fan-out on duplicate trigger_ts
    out = rows.merge(ent[key + ["entry_px", "stop_px", "risk_points", "r_trail_2r_net", "exit_reason"]],
                     on=key, how="left")
    out["entered"] = out["armed"] & out["r_trail_2r_net"].notna()   # entered must be armed
    m = ~out["entered"]
    for col in ["entry_px", "stop_px", "risk_points", "r_trail_2r_net"]:
        out.loc[m, col] = np.nan
    out.loc[m, "exit_reason"] = None
    return out


def attach_R_fill(rows: pd.DataFrame) -> pd.DataFrame:
    """Entered + R by filling the ARMED setups directly (for windows with no committed entries)."""
    rows = rows.copy()
    if rows.empty:
        return rows
    for col in ["entry_px", "stop_px", "risk_points", "r_trail_2r_net"]:
        rows[col] = np.nan
    rows["exit_reason"] = pd.Series([None] * len(rows), dtype="object")
    rows["entered"] = False
    armed = rows[rows["armed"]]
    for (symbol, date), g in armed.groupby(["symbol", "date"]):
        mn = g["trigger_ts_utc"].min() - pd.Timedelta(seconds=185)
        mx = g["trigger_ts_utc"].max() + pd.Timedelta(minutes=12) + er.HOLD
        sd = pd.Timestamp(mn.date(), tz="UTC"); ed = pd.Timestamp(mx.date(), tz="UTC") + pd.Timedelta(days=1)
        try:
            arr = er.v7.load_quote_arrays(str(symbol), sd, ed, mn, mx)
        except Exception:
            continue
        full = rows[(rows.symbol == symbol)]  # find original combined rows for first_entry_row
        for idx, row in g.iterrows():
            src = full.loc[idx]
            entry = b.first_entry_row(src, arr)
            if entry is None:
                continue
            dirn = int(entry["direction"]); E, S, R = entry["entry_px"], entry["stop_px"], entry["risk_points"]
            a = int(np.searchsorted(arr.ts_ns, pd.Timestamp(entry["entry_ts"]).value, "left"))
            z = int(np.searchsorted(arr.ts_ns, pd.Timestamp(entry["entry_ts"]).value + er.HOLD.value, "right"))
            if z <= a:
                continue
            if dirn == 1:
                f = arr.bid[a:z].astype(float); e, s, t2, t3 = E, S, E + 2 * R, E + 3 * R
            else:
                f = (-arr.ask[a:z]).astype(float); e, s, t2, t3 = -E, -S, -E + 2 * R, -E + 3 * R
            f = f[np.isfinite(f)]
            res = er.exits_for(f, e, s, R, t2, t3)
            if not res:
                continue
            gr, rsn = res["trail_2R"]
            rows.at[idx, "entry_px"] = E
            rows.at[idx, "stop_px"] = S
            rows.at[idx, "risk_points"] = R
            rows.at[idx, "r_trail_2r_net"] = er.net_R(gr, rsn, str(symbol), R)
            rows.at[idx, "exit_reason"] = rsn
            rows.at[idx, "entered"] = True
    return rows


def build_jan() -> pd.DataFrame:
    rows = score_flag(pd.read_parquet(JAN_COMBINED), "jan_oos")
    return attach_R_jan(rows)


def build_compute(symbols, days, window) -> pd.DataFrame:
    cache = OUTDIR / f"_cache_{window}.parquet"             # avoid recomputing slow MBO detection on re-runs
    if cache.exists():
        return pd.read_parquet(cache)
    parts = []
    for day in days:
        for s in symbols:
            c = D.compute_candidates(s, day, day, sweep_quality=None)
            if c is not None and len(c):
                scored = score_flag(c, window)
                if scored is not None and len(scored):
                    parts.append(scored)
    if not parts:
        return pd.DataFrame()
    res = attach_R_fill(pd.concat(parts, ignore_index=True))
    OUTDIR.mkdir(parents=True, exist_ok=True)
    res.to_parquet(cache, index=False)
    return res


COLS = ["window", "trigger_ts_utc", "symbol", "direction", "gate_score", "gated", "marginal",
        "armed", "entered", "entry_px", "stop_px", "risk_points", "r_trail_2r_net", "exit_reason",
        "day_regime"]


def distribution(df: pd.DataFrame, window: str) -> None:
    d = df[df.window == window]
    print(f"\n=== {window}: gate-score distribution & parity-sensitivity ===")
    for scope, sub in [("BOTH dirs", d), ("LONGS-only", d[d.direction == "long"])]:
        det = len(sub); gated = sub[sub.gated]; armed = sub[sub.armed]; entered = sub[sub.entered]
        marg = armed[(armed.gate_score >= THR) & (armed.gate_score <= MARG_HI)]
        robust = armed[armed.gate_score > MARG_HI]
        print(f"  [{scope}] detected={det} gated={len(gated)} armed={len(armed)} entered={len(entered)}")
        if len(armed):
            print(f"     ARMED gate-score: min={armed.gate_score.min():.3f} med={armed.gate_score.median():.3f} "
                  f"max={armed.gate_score.max():.3f}")
            print(f"     MARGINAL armed (0.5818-0.66) = {len(marg)}/{len(armed)} "
                  f"({100*len(marg)/len(armed):.0f}%)  parity-ROBUST (>0.66) = {len(robust)} "
                  f"-> a down-drift below 0.5818 could cost up to {len(marg)} arms")
        # fine bins on armed
        if len(armed):
            bins = [THR, 0.60, 0.62, 0.64, 0.66, 0.70, 1.0]
            lbl = ["0.58-0.60", "0.60-0.62", "0.62-0.64", "0.64-0.66", "0.66-0.70", "0.70+"]
            h = pd.cut(armed.gate_score, bins, labels=lbl, include_lowest=True).value_counts().reindex(lbl).fillna(0).astype(int)
            print(f"     armed bins: {dict(zip(lbl, h))}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", default="both", choices=["both", "jan", "may21", "custom"])
    ap.add_argument("--start"); ap.add_argument("--end")
    ap.add_argument("--symbols", default="ES.c.0,NQ.c.0,RTY.c.0,YM.c.0")
    args = ap.parse_args()
    syms = [s.strip() for s in args.symbols.split(",") if s.strip()]
    print(f"gate threshold={THR:.4f}  marginal band=[{THR:.4f}, {MARG_HI}]")

    frames = []
    if args.window in ("both", "jan"):
        frames.append(build_jan())
    if args.window in ("both", "may21"):
        frames.append(build_compute(syms, [dt.date(2026, 5, 21)], "may21_oos"))
    if args.window == "custom":
        days = pd.date_range(args.start, args.end, freq="D").date
        frames.append(build_compute(syms, list(days), f"custom_{args.start}_{args.end}"))
    non_empty = [f for f in frames if f is not None and len(f)]
    if non_empty:
        df = pd.concat(non_empty, ignore_index=True)
    else:
        df = pd.DataFrame(columns=COLS)
    for c in COLS:
        if c not in df.columns:
            df[c] = np.nan
    df = df[COLS].sort_values(["window", "trigger_ts_utc", "symbol"]).reset_index(drop=True)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    csv = OUTDIR / "recent_should_have_fired_setups.csv"
    js = OUTDIR / "recent_should_have_fired_setups.json"
    df.to_csv(csv, index=False)
    df.to_json(js, orient="records", date_format="iso", indent=2)
    print(f"\nwrote {len(df)} setup rows -> {csv}\n             -> {js}")

    for w in df.window.unique():
        distribution(df, w)
    # armed-only convenience file (the rows to cross-ref vs live up/down)
    armed = df[df.armed].copy()
    armed.to_csv(OUTDIR / "recent_armed_setups_for_live_xref.csv", index=False)
    print(f"\narmed-only (cross-ref vs live up/down logs): {len(armed)} rows -> recent_armed_setups_for_live_xref.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
