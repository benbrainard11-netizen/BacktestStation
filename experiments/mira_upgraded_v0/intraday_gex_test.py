"""Does FULL near-term intraday GEX (REAL open interest, re-priced at the entry-minute spot) condition the
reclaim edge? This is the clean version of the 0DTE test -- 0DTE had ~0 OI and proxied positioning with volume;
here OI is the actual dealer book across every expiration <= 30d. Signals at the entry minute (no lookahead):
net GEX sign (>=0 long-gamma/pin/mean-revert, <0 short-gamma/squeeze/trend) and spot-vs-zero-gamma side. Plus
the decision test: does adding the intraday-GEX features to the proven SMT-TF walk-forward gate lift OOS R, or
is it redundant? Reads events_es_tf + intraday_gex_spx.parquet.
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


def _diff_boot(d: pd.DataFrame, name: str, a_mask, b_mask, nb: int = 3000) -> None:
    """Day-block bootstrap of mean(R|a) - mean(R|b): is the split itself significant (not two noisy groups)?"""
    r = d["r"].to_numpy()
    days = d["day"].to_numpy()
    a = a_mask.fillna(False).to_numpy()
    b = b_mask.fillna(False).to_numpy()
    uniq = np.unique(days)
    di = {x: np.where(days == x)[0] for x in uniq}
    rng = np.random.default_rng(0)
    diffs = []
    for _ in range(nb):
        idx = np.concatenate([di[x] for x in rng.choice(uniq, len(uniq), True)])
        ra, rb = r[idx][a[idx]], r[idx][b[idx]]
        if len(ra) > 5 and len(rb) > 5:
            diffs.append(ra.mean() - rb.mean())
    diffs = np.array(diffs)
    obs = r[a].mean() - r[b].mean()
    lo, hi = np.percentile(diffs, 5), np.percentile(diffs, 95)
    flag = "  <== clears 0" if lo > 0 else ("  <== clears 0 (neg)" if hi < 0 else "  (straddles 0)")
    print(f"   {name:28} {obs:+.2f}  90% CI [{lo:+.2f},{hi:+.2f}]{flag}")


def _split(d: pd.DataFrame, label: str, groups) -> None:
    print(label)
    for name, mask in groups:
        s = d[mask.fillna(False).to_numpy()]
        if len(s) < 20:
            print(f"   {name:24} n<20 ({len(s)})")
            continue
        m, lo, hi = boot(s["r"].to_numpy(), s["day"].to_numpy())
        print(f"   {name:24} {m:+.2f} [{lo:+.2f},{hi:+.2f}]  n{len(s)}")


def main() -> int:
    df = pd.read_parquet(OUT / "events_es_tf.parquet")
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].copy()
    df["r"] = seq_r(df, TARGET)
    df["fam"] = pd.factorize(df["level_family"])[0]
    t = pd.to_datetime(df["touch_ts_utc"], utc=True).dt.tz_convert("America/New_York")
    df["day"] = t.dt.date
    df["t"] = t.dt.tz_localize(None)                                           # naive ET entry time

    g = pd.read_parquet(GEX / "intraday_gex_spx.parquet")
    g["gdt"] = (pd.to_datetime(g["date"].astype(int).astype(str), format="%Y%m%d")
                + pd.to_timedelta(g["ms_of_day"].astype(int), unit="ms")).astype("datetime64[ns]")  # naive ET
    g = g.sort_values("gdt")
    # latest-known GEX at/just-before the entry minute -- strictly no-lookahead, robust to 5-min spacing
    d = pd.merge_asof(df.sort_values("t"), g[["gdt", "net_gex", "zero_gamma", "spot"]],
                      left_on="t", right_on="gdt", direction="backward",
                      tolerance=pd.Timedelta("10min")).rename(
                      columns={"net_gex": "g_net_gex", "zero_gamma": "g_zero_gamma", "spot": "g_spot"})
    d = d.dropna(subset=["g_net_gex"]).reset_index(drop=True)
    bm, bl, bh = boot(d["r"].to_numpy(), d["day"].to_numpy())
    print(f"reclaim events with intraday near-term GEX at entry: {len(d)}  ({d['day'].nunique()} days)")
    print(f"baseline reclaim R: {bm:+.2f} [{bl:+.2f},{bh:+.2f}]\n")

    _split(d, "by net-gamma sign at the entry minute (REAL OI):",
           [("long-gamma (>=0, pin)", d["g_net_gex"] >= 0), ("short-gamma (<0, squeeze)", d["g_net_gex"] < 0)])

    d["zg_side"] = d["g_spot"] - d["g_zero_gamma"]                     # >0 spot above flip (long-gamma side)
    print()
    _split(d, "by spot vs zero-gamma flip:",
           [("above flip (>0)", d["zg_side"] > 0), ("below flip (<0)", d["zg_side"] < 0)])

    print("\nday-block bootstrap of the DIFFERENCE (is the split real, not two noisy groups?):")
    _diff_boot(d, "short-gamma - long-gamma", d["g_net_gex"] < 0, d["g_net_gex"] >= 0)
    _diff_boot(d, "below-flip - above-flip", d["zg_side"] < 0, d["zg_side"] > 0)

    # decision test: does intraday GEX add to the proven SMT-TF gate?
    print("\nSMT-TF gate, with vs without intraday-GEX features (walk-forward OOS):")
    base = [c for c in d.columns if c.startswith("smt_tf.")] + ["fam"]
    d["zg_dist"] = d["zg_side"].abs()
    combos = [("SMT-TF only", base), ("SMT-TF + intraday GEX", base + ["g_net_gex", "zg_side", "zg_dist"])]
    if len(d) < 160:
        print(f"   thin ({len(d)}) -- need the full-range pull")
        return 0
    for nm, feats in combos:
        feats = [c for c in feats if c in d.columns]
        sel, oos, rr, dday = wf_gate(d, feats, TARGET, r=d["r"].to_numpy())
        if oos.sum() < 10 or sel.sum() < 5:
            print(f"   {nm:24} thin folds")
            continue
        gm, gl, gh = boot(rr[sel], dday[sel])
        print(f"   {nm:24} GATE {gm:+.2f} [{gl:+.2f},{gh:+.2f}]  n{int(sel.sum())}")
    print("\nREAD: a split clearly off baseline, or the +GEX gate beating SMT-TF-only out of sample = real OI "
          "positioning adds signal. Flat/overlapping = even real near-term GEX is redundant to structure+SMT; "
          "bank the proven reclaim edge and stop mining options.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
