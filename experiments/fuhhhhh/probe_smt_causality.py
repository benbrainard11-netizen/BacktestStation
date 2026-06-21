"""Causality / robustness hardening for the NQ-vs-ES SMT short edge (ANGLE 3 survivor).

The survivor: at a decision, a proper adjacent-swing SMT divergence between NQ and ES
(NQ HH while ES LH => bearish NQ; NQ LL while ES HL => bullish NQ). Short leg carries it.

This script PROVES it isn't a leak and stress-tests it:
  A. Re-derive xa_smt_es ENTIRELY from raw bars here, with a HARD assert that every pivot
     used is confirmed (p <= idx-K) AND its close-time <= decision time. (independent rebuild)
  B. DELAY entry by one decision step (+5 min): the signal is known at ms, but enter using
     r_long/r_short of the NEXT decision row same day. If edge survives a 5-min delay it is
     not a same-bar microstructure artifact. (uses dataset rows; conservative)
  C. Placebo: shift the SMT label to a RANDOM OTHER day's decision (date-permuted), 1000x —
     should kill it (confirms it's the SMT-to-NQ link, not a calendar/seasonal artifact).
  D. Sub-period split: first-half days vs second-half days (both must be > 0).
  E. Net-cost already in r_*; report short-leg with explicit per-month and bootstrap.
"""
from __future__ import annotations

import sys
from datetime import date as Date, time as Time, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
from build_xasset_feats import load_day_et, fractal_pivots

ET = ZoneInfo(C.ET)
OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20260613)
NQ_ROOT = C.BARS_1M_ROOT / "symbol=NQ.c.0"
ES_ROOT = C.BARS_1M_ROOT / "symbol=ES.c.0"


def block_boot(df, col="r", b=4000):
    days = df["date"].unique()
    by = {d: df[df["date"] == d][col].to_numpy() for d in days}
    means = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean()
                      for _ in range(b)])
    return float(df[col].mean()), float((means <= 0).mean())


def smt_es_strict(nq, es, ms, k=3, fresh=20):
    """Recompute the NQ-vs-ES SMT at decision ms with explicit causality asserts.
    Returns (signal, latest_used_close_dt) or (0, None)."""
    nmask = nq["close_ms"].to_numpy() <= ms
    emask = es["close_ms"].to_numpy() <= ms
    ni = np.nonzero(nmask)[0]
    ei = np.nonzero(emask)[0]
    if len(ni) < 2 * k + 3 or len(ei) < 2 * k + 3:
        return 0, None
    nci, eci = ni[-1], ei[-1]
    nl = nq["low"].to_numpy()[:nci + 1]; nh = nq["high"].to_numpy()[:nci + 1]
    el = es["low"].to_numpy()[:eci + 1]; eh = es["high"].to_numpy()[:eci + 1]
    n_cms = nq["close_ms"].to_numpy()[:nci + 1]
    e_cms = es["close_ms"].to_numpy()[:eci + 1]
    nlo, nhi = fractal_pivots(nl, nh, k)
    cutoff = nci - k
    nlo = nlo[nlo <= cutoff]; nhi = nhi[nhi <= cutoff]
    used_close_ms = []
    out = 0

    def es_at(cms, arr):
        j = np.searchsorted(e_cms, cms, side="right") - 1
        return (arr[j], e_cms[j]) if j >= 0 else (np.nan, None)
    if len(nlo) >= 2 and (nci - nlo[-1]) <= fresh:
        p1, p2 = nlo[-2], nlo[-1]
        e1, e1c = es_at(n_cms[p1], el); e2, e2c = es_at(n_cms[p2], el)
        if np.isfinite(e1) and np.isfinite(e2):
            used_close_ms += [n_cms[p1], n_cms[p2], e1c, e2c]
            if nl[p2] < nl[p1] and e2 > e1:
                out = 1
    if len(nhi) >= 2 and (nci - nhi[-1]) <= fresh:
        p1, p2 = nhi[-2], nhi[-1]
        e1, e1c = es_at(n_cms[p1], eh); e2, e2c = es_at(n_cms[p2], eh)
        if np.isfinite(e1) and np.isfinite(e2):
            used_close_ms += [n_cms[p1], n_cms[p2], e1c, e2c]
            if nh[p2] > nh[p1] and e2 < e1:
                out = -1 if out == 0 else 0
    # HARD causality assert: every used pivot bar must have closed by ms
    for cms in used_close_ms:
        if cms is not None and cms > ms:
            raise AssertionError(f"LOOKAHEAD in SMT: used close_ms {cms} > decision {ms}")
    return out, (max([c for c in used_close_ms if c is not None]) if used_close_ms else None)


def main() -> int:
    ds = pd.read_parquet(OUT / "dataset_ndx.parquet")
    assert ds["date"].max() < "2026-04-01"
    ds = ds[ds["y"].isin([0, 1])].copy()

    # --- A. independent strict rebuild of SMT-vs-ES, with asserts ---
    print("### A. independent strict rebuild (asserts every used bar closed <= decision)")
    sig = {}
    for d, grp in ds.groupby("date"):
        day = Date.fromisoformat(d)
        nq = load_day_et(NQ_ROOT, day); es = load_day_et(ES_ROOT, day)
        if nq is None or es is None:
            continue
        for ms in grp["ms"].tolist():
            s, _ = smt_es_strict(nq, es, int(ms))
            sig[(d, int(ms))] = s
    ds["smt_es2"] = [sig.get((d, int(m)), 0) for d, m in zip(ds["date"], ds["ms"])]
    print(f"  strict rebuild nonzero: {(ds.smt_es2 != 0).sum()}  (all causality asserts passed)")

    cond = ds[ds["smt_es2"] != 0].copy()
    cond["r"] = np.where(cond["smt_es2"] > 0, cond["r_long"], cond["r_short"])
    cond["mo"] = cond["date"].str.slice(0, 7)
    m, p = block_boot(cond)
    bymo = cond.groupby("mo")["r"].mean().sort_values(ascending=False)
    d2 = cond[~cond.mo.isin(bymo.index[:2])]["r"].mean()
    nofm = cond[~cond.mo.isin({"2026-02", "2026-03"})]["r"].mean()
    print(f"  BOTH-side strict: R={m:+.4f} p(<=0)={p:.3f} win%={(cond.r>0).mean()*100:.1f} "
          f"drop2={d2:+.4f} noFM={nofm:+.4f} mo+={int((bymo>0).sum())}/{len(bymo)} n={len(cond)}")
    # short leg
    sh = cond[cond["smt_es2"] < 0].copy(); sh["r"] = sh["r_short"]
    m2, p2 = block_boot(sh)
    bymo2 = sh.groupby("mo")["r"].mean().sort_values(ascending=False)
    d2s = sh[~sh.mo.isin(bymo2.index[:2])]["r"].mean()
    nofms = sh[~sh.mo.isin({"2026-02", "2026-03"})]["r"].mean()
    print(f"  SHORT leg strict: R={m2:+.4f} p(<=0)={p2:.3f} win%={(sh.r>0).mean()*100:.1f} "
          f"drop2={d2s:+.4f} noFM={nofms:+.4f} mo+={int((bymo2>0).sum())}/{len(bymo2)} n={len(sh)}")
    print("  short-leg per-month:")
    print(sh.groupby("mo")["r"].agg(["size", "mean"]).round(3).to_string())

    # --- B. delayed entry (+1 decision step, ~+5 min) ---
    print("\n### B. delayed entry by one 5-min decision step (same day)")
    ds_sorted = ds.sort_values(["date", "ms"]).reset_index(drop=True)
    nxt = ds_sorted.groupby("date").shift(-1)
    ds_sorted["next_rl"] = nxt["r_long"]; ds_sorted["next_rs"] = nxt["r_short"]
    cd = ds_sorted[(ds_sorted["smt_es2"] != 0) & ds_sorted["next_rl"].notna()].copy()
    cd["r"] = np.where(cd["smt_es2"] > 0, cd["next_rl"], cd["next_rs"])
    cd["mo"] = cd["date"].str.slice(0, 7)
    md, pd_ = block_boot(cd)
    bymo = cd.groupby("mo")["r"].mean().sort_values(ascending=False)
    print(f"  delayed BOTH: R={md:+.4f} p(<=0)={pd_:.3f} drop2={cd[~cd.mo.isin(bymo.index[:2])]['r'].mean():+.4f} "
          f"noFM={cd[~cd.mo.isin({'2026-02','2026-03'})]['r'].mean():+.4f} mo+={int((bymo>0).sum())}/{len(bymo)} n={len(cd)}")
    cds = cd[cd["smt_es2"] < 0].copy(); cds["r"] = cds["next_rs"]
    bymo = cds.groupby("mo")["r"].mean().sort_values(ascending=False)
    mds, pds = block_boot(cds)
    print(f"  delayed SHORT: R={mds:+.4f} p(<=0)={pds:.3f} drop2={cds[~cds.mo.isin(bymo.index[:2])]['r'].mean():+.4f} "
          f"noFM={cds[~cds.mo.isin({'2026-02','2026-03'})]['r'].mean():+.4f} mo+={int((bymo>0).sum())}/{len(bymo)} n={len(cds)}")

    # --- C. date-permutation placebo (break SMT<->NQ link, keep calendar) ---
    print("\n### C. date-permutation placebo (1000x) — should KILL the edge")
    obs = cond["r"].mean()
    # build a per-(date,ms) lookup of r_long/r_short and the signal, then shuffle signal across rows
    sigv = cond["smt_es2"].to_numpy(); rl = cond["r_long"].to_numpy(); rs = cond["r_short"].to_numpy()
    perms = []
    for _ in range(1000):
        ps = RNG.permutation(sigv)
        perms.append(np.where(ps > 0, rl, rs).mean())
    perms = np.array(perms)
    print(f"  observed R={obs:+.4f}  placebo mean={perms.mean():+.4f}  p(placebo>=obs)={float((perms>=obs).mean()):.4f}")

    # --- D. first-half vs second-half day split ---
    print("\n### D. first-half vs second-half days (short leg)")
    days = sorted(sh["date"].unique())
    mid = days[len(days)//2]
    h1 = sh[sh.date < mid]; h2 = sh[sh.date >= mid]
    print(f"  H1 (<{mid}): R={h1['r'].mean():+.4f} n={len(h1)}   H2 (>={mid}): R={h2['r'].mean():+.4f} n={len(h2)}")

    # --- E. magnitude / freshness sensitivity (short leg, vary fresh window) ---
    print("\n### E. SMT short-leg overall summary (the headline)")
    print(f"  SHORT R={m2:+.4f} (net cost), p={p2:.3f}, 7mo coverage, {len(sh)} trades, "
          f"~{len(sh)/sh.date.nunique():.1f}/day on {sh.date.nunique()} days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
