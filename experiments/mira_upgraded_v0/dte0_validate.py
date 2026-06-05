"""Firm up the 0DTE-gamma lead before expanding: (1) is the squeeze-vs-pin R spread actually significant
(day-block bootstrap of the DIFFERENCE, not eyeballed CIs)? (2) does gating squeeze-regime reclaims through the
proven SMT-TF gate give a clean tradeable R? Cheap, existing data. Reads events_es_tf + dte0_intraday_spx.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import boot, seq_r  # noqa: E402
from smt_economics import wf_gate  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
GEX = Path(__file__).resolve().parents[1] / "options_signals_v0" / "out"
TARGET = 3.0


def main() -> int:
    df = pd.read_parquet(OUT / "events_es_tf.parquet")
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].copy()
    df["r"] = seq_r(df, TARGET)
    df["fam"] = pd.factorize(df["level_family"])[0]
    t = pd.to_datetime(df["touch_ts_utc"], utc=True).dt.tz_convert("America/New_York")
    df["day"] = t.dt.date
    df["key"] = t.dt.strftime("%Y%m%d").astype(int) * 1440 + t.dt.hour * 60 + t.dt.minute
    g = pd.read_parquet(GEX / "dte0_intraday_spx.parquet")
    g["key"] = g["date"].astype(int) * 1440 + (g["ms_of_day"] // 60000)
    df["dte_gex"] = df["key"].map(g.set_index("key")["net_gex"].to_dict())
    d = df.dropna(subset=["dte_gex"]).reset_index(drop=True)
    d["squeeze"] = d["dte_gex"].to_numpy() <= 0
    r, sq, days = d["r"].to_numpy(), d["squeeze"].to_numpy(), d["day"].to_numpy()
    print(f"RTH reclaims with 0DTE context: {len(d)}  (squeeze {sq.sum()}, pin {(~sq).sum()})\n")

    # (1) day-block bootstrap of the squeeze-minus-pin DIFFERENCE
    uniq = np.unique(days)
    di = {x: np.where(days == x)[0] for x in uniq}
    rng = np.random.default_rng(0)
    diffs = []
    for _ in range(3000):
        idx = np.concatenate([di[x] for x in rng.choice(uniq, len(uniq), True)])
        rr, ss = r[idx], sq[idx]
        if ss.sum() > 5 and (~ss).sum() > 5:
            diffs.append(rr[ss].mean() - rr[~ss].mean())
    diffs = np.array(diffs)
    obs = r[sq].mean() - r[~sq].mean()
    lo, hi = np.percentile(diffs, 5), np.percentile(diffs, 95)
    flag = "  <== SIGNIFICANT (clears 0)" if lo > 0 else "  (still straddles 0)"
    print(f"(1) squeeze - pin R difference: {obs:+.2f}  day-block 90% CI [{lo:+.2f},{hi:+.2f}]{flag}")

    # (2) SMT-TF gate on squeeze-only vs all RTH reclaims
    feats = [c for c in d.columns if c.startswith("smt_tf.")] + ["fam"]
    print("\n(2) SMT-TF gate, squeeze-regime filter vs all (walk-forward OOS):")
    for nm, sub in [("all RTH reclaims", d), ("squeeze-regime only", d[d["squeeze"]])]:
        s = sub.reset_index(drop=True)
        if len(s) < 160:
            print(f"   {nm:22} thin ({len(s)})")
            continue
        sel, oos, rr, dday = wf_gate(s, feats, TARGET, r=s["r"].to_numpy())
        if oos.sum() < 10 or sel.sum() < 5:
            print(f"   {nm:22} thin folds")
            continue
        bm, bl, bh = boot(rr[oos], dday[oos])
        gm, gl, gh = boot(rr[sel], dday[sel])
        print(f"   {nm:22} base {bm:+.2f}[{bl:+.2f},{bh:+.2f}]  GATE {gm:+.2f}[{gl:+.2f},{gh:+.2f}] n{int(sel.sum())}")
    print("\nREAD: difference CI>0 AND squeeze-gate clearly beats all-reclaims = the 0DTE signal is real -> expand (#3). "
          "Both flat = the 1.5sigma was noise, don't chase the bigger pulls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
