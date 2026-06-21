"""Reproduce the Jan-2026 WITH-MBO OOS realized R with the SAME honest exit
machinery used on the MBO-free 909 (exit_replay_oos.py).

This is the apples-to-apples test the milk plan hinges on. The MBO-free 2025 OOS
entry set scored -0.11R/trade (a loser). The Jan-2026 with-MBO entry set (139
entries, 2026-01-02..2026-02-04, a genuine PRE-training backward OOS slice -- the
frozen model trained 2026-02-06..2026-05-20) is claimed to be +0.38R. That number
was never run through this exact exit logic; it is reproduced here so the
comparison is honest (identical stop-wins-ties fills, identical stressed costs).

Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/replay_jan_withmbo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exit_replay_oos as er  # noqa: E402  reuse exits_for / net_R / v7 / HOLD

JAN = Path(
    r"C:/Users/benbr/bs-mira-v15/experiments/mira_v15_gate_validation/out/"
    r"mira_2026jan_real_mbo_oos_model_reclaim_2r_entries.parquet"
)
OUT = HERE / "out" / "mira_oos_withmbo" / "jan2026_withmbo_exits.parquet"
MBOFREE = HERE / "out" / "mira_oos_mbofree" / "oos_exits.parquet"
VARIANTS = ["fixed_2R", "fixed_3R", "trail_2R", "scale_2R"]


def norm_dir(v) -> int:
    if isinstance(v, str):
        return 1 if v.lower().startswith("l") else -1
    return int(v)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(JAN)
    df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True)
    df["direction"] = df["direction"].map(norm_dir)
    df["entry_date"] = df["entry_ts"].dt.date
    print(f"loaded {len(df)} Jan with-MBO entries  "
          f"{df['entry_ts'].min()} -> {df['entry_ts'].max()}", flush=True)
    print(f"symbols: {df['symbol'].value_counts().to_dict()}", flush=True)

    recs = []
    skipped = 0
    groups = list(df.groupby(["symbol", "entry_date"], sort=True))
    for gi, ((symbol, _d), g) in enumerate(groups, 1):
        min_ts = g["entry_ts"].min() - pd.Timedelta(seconds=10)
        max_ts = g["entry_ts"].max() + er.HOLD + pd.Timedelta(minutes=2)
        sd = pd.Timestamp(min_ts.date(), tz="UTC")
        ed = pd.Timestamp(max_ts.date(), tz="UTC") + pd.Timedelta(days=1)
        try:
            arr = er.v7.load_quote_arrays(str(symbol), sd, ed, min_ts, max_ts)
        except Exception as exc:  # noqa: BLE001
            skipped += len(g)
            print(f"  skip {symbol} {_d} ({len(g)}): {type(exc).__name__}: {exc}", flush=True)
            continue
        ts_ns = arr.ts_ns
        for _, row in g.iterrows():
            e_ns = row["entry_ts"].value
            start = int(np.searchsorted(ts_ns, e_ns, "left"))
            end = int(np.searchsorted(ts_ns, e_ns + er.HOLD.value, "right"))
            if end <= start:
                skipped += 1
                continue
            direction = int(row["direction"])
            E, S, R = float(row["entry_px"]), float(row["stop_px"]), float(row["risk_points"])
            if direction == 1:
                f = arr.bid[start:end].astype(float)
                e, s, t2, t3 = E, S, E + 2 * R, E + 3 * R
            else:
                f = (-arr.ask[start:end]).astype(float)
                e, s, t2, t3 = -E, -S, -E + 2 * R, -E + 3 * R
            f = f[np.isfinite(f)]
            res = er.exits_for(f, e, s, R, t2, t3)
            if not res:
                skipped += 1
                continue
            rec = {k: row.get(k) for k in ["entry_ts", "symbol", "direction", "risk_points"]}
            for v in VARIANTS:
                gross, reason = res[v]
                rec[f"r_{v}"] = er.net_R(gross, reason, str(symbol), R)
                rec[f"reason_{v}"] = reason
            recs.append(rec)

    out = pd.DataFrame(recs)
    out.to_parquet(OUT, index=False)
    print(f"\nwrote {OUT}  ({len(out)} replayed, {skipped} skipped of {len(df)})\n", flush=True)
    print(f"{'variant':10s} {'n':>5s} {'win%':>6s} {'meanR':>8s} {'medR':>7s} {'sumR':>8s}  exit mix")
    for v in VARIANTS:
        r = out[f"r_{v}"]
        mix = out[f"reason_{v}"].value_counts().to_dict()
        print(f"{v:10s} {len(r):>5d} {100*(r>0).mean():>5.1f}% {r.mean():>+8.3f} "
              f"{r.median():>+7.3f} {r.sum():>+8.1f}  {mix}")

    if MBOFREE.exists():
        m = pd.read_parquet(MBOFREE)
        print(f"\n--- MBO-FREE 2025 baseline (same machinery) ---")
        print(f"trail_2R: n={len(m)}  mean={m['r_trail_2R'].mean():+.3f}R  "
              f"win={100*(m['r_trail_2R']>0).mean():.1f}%")
        print(f"\nVERDICT: with-MBO trail_2R = {out['r_trail_2R'].mean():+.3f}R vs "
              f"MBO-free {m['r_trail_2R'].mean():+.3f}R  "
              f"(delta {out['r_trail_2R'].mean()-m['r_trail_2R'].mean():+.3f}R)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
