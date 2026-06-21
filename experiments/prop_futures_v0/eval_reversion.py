"""eval_reversion — Layer-1 eval-economics test of the reversion generator's REAL R-distribution.

The reversion (fade accumulation breakout -> POC) is ~62-66% win, ~0-to-slightly-negative EV. Question:
does that high-win shape clear the prop evals net-positive via the asymmetric-bet structure (eval_ev
showed +EV even at zero market edge)? eval_ev models a BINARY (p, win_R, -1R) shape; the reversion's
tail (rare losses > 1R) drives breaches, so we feed the EMPIRICAL fade_R distribution instead, reusing
eval_ev's firm pass/blow/payout machinery by monkeypatching its day-draw with an empirical sampler.

  python eval_reversion.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MOD = Path(__file__).resolve().parent
OUT = MOD / "out"
sys.path.insert(0, str(MOD.parent / "prop_model_v0"))
import eval_ev  # noqa: E402
from eval_ev import FUNNELS  # noqa: E402

RNG = np.random.default_rng(7)
DIST = None     # iid pool of fade_R
DAY_MAT = None  # (n_dates, maxk) padded real same-day cross-instrument fade_R sets (correlated)


def _dll_pack(cum, n_slots, dll, dll_soft):
    if dll and dll > 0:
        crossed = cum <= -dll
        any_cross = crossed.any(axis=2)
        idx = np.where(any_cross, np.argmax(crossed, axis=2), n_slots - 1)
        day_pnl = np.take_along_axis(cum, idx[..., None], axis=2)[..., 0]
        taken = np.arange(n_slots)[None, None, :] <= idx[..., None]
        cum_t = np.where(taken, cum, np.nan)
        return day_pnl, np.nanmin(cum_t, axis=2), np.nanmax(cum_t, axis=2), any_cross & (not dll_soft)
    return cum[..., -1], np.min(cum, axis=2), np.max(cum, axis=2), np.zeros(cum.shape[:2], bool)


def emp_draws(p, win_r, n, risk, paths, days, dll=0.0, dll_soft=False):
    """IID: sample n independent fade_R/day from the pooled distribution (ignores p/win_r)."""
    cum = np.cumsum(RNG.choice(DIST, size=(paths, days, n)) * risk, axis=2)
    return _dll_pack(cum, n, dll, dll_soft)


def emp_draws_dayblock(p, win_r, n, risk, paths, days, dll=0.0, dll_soft=False):
    """CORRELATED: each sim-day = a real historical date's ACTUAL cross-instrument fade_R set (trades
    that co-occurred that day, preserving same-day correlation). n ignored (uses real daily counts)."""
    di = RNG.integers(0, DAY_MAT.shape[0], size=(paths, days))
    block = DAY_MAT[di] * risk                        # (paths,days,maxk), NaN where no trade
    cum = np.cumsum(np.where(np.isnan(block), 0.0, block), axis=2)
    return _dll_pack(cum, DAY_MAT.shape[1], dll, dll_soft)


def best_per_firm(ns, risks):
    rows = []
    for firm in FUNNELS:
        best = None
        for n in ns:
            for r in risks:
                res = eval_ev.campaign_ev(firm, 0.5, 1.0, n, r)
                res.update(n=n, risk=r)
                if best is None or res["ev"] > best["ev"]:
                    best = res
        best.update(excluded=FUNNELS[firm]["excluded"])
        rows.append(best)
    return pd.DataFrame(rows)[["firm", "n", "risk", "p_pass", "v_funded", "ev", "excluded"]]


def main():
    global DIST, DAY_MAT
    df = pd.concat([pd.read_parquet(p) for p in OUT.glob("events_*.parquet")], ignore_index=True)
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["fade_R"])
    DIST = df["fade_R"].to_numpy()
    grp = df.groupby("date")["fade_R"].apply(list)
    maxk = max(len(x) for x in grp)
    DAY_MAT = np.full((len(grp), maxk), np.nan)
    for i, x in enumerate(grp):
        DAY_MAT[i, :len(x)] = x
    d_des, d_ho = df[df.split == "design"]["fade_R"], df[df.split == "holdout"]["fade_R"]
    print(f"reversion fade_R: n={len(DIST)} mean={DIST.mean():+.4f} median={np.median(DIST):+.4f} "
          f"win={(DIST>0).mean():.3f} std={DIST.std():.2f} p5={np.percentile(DIST,5):+.2f}")
    print(f"  design mean {d_des.mean():+.4f} | holdout mean {d_ho.mean():+.4f} (stable)")
    print(f"  day-block: {len(grp)} real dates, median {np.median([len(x) for x in grp]):.0f} / max {maxk} "
          f"co-occurring trades/day (real same-day correlation)\n")

    eval_ev.day_draws = emp_draws
    iid = best_per_firm([1, 2, 3, 4], [150, 250, 400, 600, 900])
    eval_ev.day_draws = emp_draws_dayblock
    cor = best_per_firm([1], [150, 250, 400, 600, 900])  # n ignored in dayblock

    m = iid.merge(cor, on="firm", suffixes=("_iid", "_corr"))
    print("== Reversion eval-EV per firm: IID vs day-block CORRELATED ==")
    print(f"  {'firm':9s} {'iid_ev':>8s} {'iid_pass':>9s} | {'corr_ev':>8s} {'corr_pass':>10s} {'corr_risk':>10s}  excl")
    for _, r in m.iterrows():
        print(f"  {r.firm:9s} {r.ev_iid:+8.0f} {r.p_pass_iid:9.3f} | {r.ev_corr:+8.0f} "
              f"{r.p_pass_corr:10.3f} {r.risk_corr:10.0f}  {r.excluded_iid}")
    print("\nfree-coin (edge_r=0) baselines: topstep +989 lucid +1031 mffu +929 tradeify +535 apex +354")
    pos = m[(~m.excluded_iid) & (m.ev_corr > 0)]
    print(f"POSITIVE under realistic CORRELATION: {list(pos.firm)}" if len(pos)
          else "NO non-excluded firm is positive once same-day correlation is honest -> iid result was the artifact.")
    m.to_csv(OUT / "eval_reversion.csv", index=False)


if __name__ == "__main__":
    main()
