"""Multi-timeframe cross-asset direction panel: NQ-vs-ES SMT at 5/15/30/60m + RS divergence.

Extends the 1m adjacent-pivot SMT (which carried the verified short edge) to multiple
timeframes and to a continuous relative-strength divergence. All strictly CAUSAL: per TF,
the SMT at decision t uses only resampled bars CLOSED by t, with fractal pivots confirmed
by t (triggers.smt_dir gates pivots to <= idx-SWING_K). RS divergence uses 1m closes <= t.

One row per (date, ms) of dataset_ndx. Output merges into the direction eval.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\build_xasset_dir_ndx.py
Output: out/xasset_dir_ndx.parquet
"""
from __future__ import annotations

import sys
from datetime import date as Date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D
import triggers as T
from build_events import SESSION_END_MS

OUTDIR = Path(__file__).resolve().parent / "out"
TFS = [5, 15, 30, 60]
RS_WINDOWS = [15, 30, 60]          # minutes, for relative-strength divergence


def resample_tf(df: pd.DataFrame, tf: int) -> pd.DataFrame:
    """Resample 1m bars to tf-min bars labelled by CLOSE time (right-closed)."""
    s = (df.set_index("et").resample(f"{tf}min", label="right", closed="right")
         .agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna())
    return s.reset_index()


def full_session(prev_day: Date, day: Date, root) -> pd.DataFrame | None:
    on = D.overnight_bars(prev_day, day, root=root)
    rth = D.load_bars_sym(root, day)
    rth = rth[(rth["et"] >= D.et_ts(day, 9 * 3600_000 + 30 * 60_000)) &
              (rth["et"] < D.et_ts(day, SESSION_END_MS))] if rth is not None else None
    parts = [b for b in (on, rth) if b is not None]
    return pd.concat(parts, ignore_index=True).sort_values("et") if parts else None


def build_day(day: Date, prev_day: Date, grid_ms: list[int]) -> list[dict]:
    nq = full_session(prev_day, day, C.BARS_1M_NQ)
    es = full_session(prev_day, day, C.BARS_1M)
    if nq is None or es is None:
        return []
    # per-TF causal SMT contexts (NQ primary, ES confirm)
    tf_ctx, tf_et = {}, {}
    for tf in TFS:
        nq_tf, es_tf = resample_tf(nq, tf), resample_tf(es, tf)
        if len(nq_tf) < 8:
            continue
        tf_ctx[tf] = T.DayCtx.build(nq_tf, es_tf)
        tf_et[tf] = pd.DatetimeIndex(nq_tf["et"]).asi8       # int64 ns (UTC) for searchsorted
    # 1m RTH closes for RS divergence (NQ vs ES), aligned
    nq1 = nq.set_index("et")["close"]
    es1 = es.set_index("et")["close"]

    rows = []
    for ms in grid_ms:
        t = D.et_ts(day, ms)
        row = {"date": day.isoformat(), "ms": ms}
        for tf in TFS:
            if tf not in tf_ctx:
                row[f"xsmt_{tf}m"] = 0.0
                continue
            idx = int(np.searchsorted(tf_et[tf], t.value, side="right")) - 1
            row[f"xsmt_{tf}m"] = float(T.smt_dir(tf_ctx[tf], idx)) if idx >= C.SWING_K + 2 else 0.0
        # relative-strength divergence over windows (NQ %ret - ES %ret), causal (closes <= t-1m)
        for w in RS_WINDOWS:
            lo = t - pd.Timedelta(minutes=w + 1)
            hi = t - pd.Timedelta(minutes=1)
            nqw = nq1[(nq1.index >= lo) & (nq1.index <= hi)]
            esw = es1[(es1.index >= lo) & (es1.index <= hi)]
            if len(nqw) >= 2 and len(esw) >= 2 and nqw.iloc[0] > 0 and esw.iloc[0] > 0:
                rs = (nqw.iloc[-1] / nqw.iloc[0] - 1.0) - (esw.iloc[-1] / esw.iloc[0] - 1.0)
                row[f"rs_div_{w}m"] = float(rs * 1e4)   # in bps of relative perf
            else:
                row[f"rs_div_{w}m"] = np.nan
        # multi-TF agreement (sum of TF SMT signs)
        votes = [row[f"xsmt_{tf}m"] for tf in TFS]
        row["xsmt_vote"] = float(sum(votes))
        row["xsmt_nz"] = float(sum(1 for v in votes if v != 0))
        rows.append(row)
    return rows


def main() -> int:
    ds = pd.read_parquet(OUTDIR / "dataset_ndx.parquet", columns=["date", "ms"])
    by_day = {d: sorted(g["ms"].astype(int)) for d, g in ds.groupby("date")}
    days = sorted(by_day)
    all_rows = []
    print(f"building multi-TF cross-asset dir panel over {len(days)} days")
    for i, dstr in enumerate(days):
        day = Date.fromisoformat(dstr)
        prev = Date.fromisoformat(days[i - 1]) if i > 0 else day - pd.Timedelta(days=1).to_pytimedelta()
        all_rows.extend(build_day(day, prev, by_day[dstr]))
        if i and i % 30 == 0:
            print(f"  ...{i}/{len(days)}  {len(all_rows)} rows")

    df = pd.DataFrame(all_rows)
    assert df["date"].max() <= C.DEV_END, "holdout leak"
    out = OUTDIR / "xasset_dir_ndx.parquet"
    df.to_parquet(out)
    print(f"\n{len(df)} rows -> {out}")
    for tf in TFS:
        c = df[f"xsmt_{tf}m"].value_counts().to_dict()
        print(f"  xsmt_{tf}m: {c}")
    print(f"  rs_div NaN share: {df[[f'rs_div_{w}m' for w in RS_WINDOWS]].isna().mean().round(3).to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
