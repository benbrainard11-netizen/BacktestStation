"""Does orderflow predict NQ direction CONDITIONAL on dealer-gamma regime?

Hypothesis (explains the OOS direction inversion + per-month flip): the orderflow->
direction relationship has OPPOSITE sign in positive vs negative gamma regimes
(negative gamma = dealers amplify = continuation; positive gamma = dampen = reversion).
Pooling across regimes cancels/inverts it OOS. If true, the corr is stable-signed WITHIN
each regime and opposite ACROSS — and a regime-conditioned model recovers direction.

Sign-agnostic: gex_proxy sign convention is suspect (per wall audit), so we only ask
whether the two regimes DIFFER and are internally stable, not which is which.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\diag_direction_regime.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT = Path(__file__).resolve().parent / "out"
DIR_FEATS = ["mbp_sv_1m", "mbp_sv_5m", "mbp_ofi_1m", "mbp_ofi_5m", "mbp_tbi",
             "mbp_ret_1m_tk", "struct_sweep", "struct_smt"]


def corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 30 or np.std(a[m]) < 1e-9:
        return np.nan, int(m.sum())
    return float(np.corrcoef(a[m], b[m])[0, 1]), int(m.sum())


def main() -> int:
    df = pd.read_parquet(OUT / "dataset_ndx.parquet")
    mbp = pd.read_parquet(OUT / "mbp_features_ndx.parquet")
    df = df.merge(mbp, on=["date", "ms"], how="left")
    df["mo"] = df["date"].str.slice(0, 7)

    mv = df[df["y"].isin([0, 1])].copy()       # resolved moves only
    mv["dir"] = mv["y"] * 2 - 1                  # up=+1, down=-1
    feats = [f for f in DIR_FEATS if f in mv.columns]

    # conditioner candidates
    conds = {
        "gamma_sign(+/-)": mv["opt_gamma_sign"] > 0,
        "above_zero_gamma": mv["opt_above_zero_gamma"] > 0.5,
    }

    print(f"resolved moves n={len(mv)} (up={int((mv.dir>0).sum())} down={int((mv.dir<0).sum())})\n")
    print("### corr(feature, direction)  [overall | regime-A | regime-B]  per conditioner")
    for cname, mask in conds.items():
        A, B = mv[mask], mv[~mask]
        print(f"\n-- conditioner = {cname}:  A(true) n={len(A)}  B(false) n={len(B)}")
        print(f"   {'feature':14s} {'overall':>9s} {'regimeA':>9s} {'regimeB':>9s}  {'A-B flip?':>9s}")
        for f in feats:
            co, _ = corr(mv[f], mv["dir"])
            ca, na = corr(A[f], A["dir"])
            cb, nb = corr(B[f], B["dir"])
            flip = "YES" if (np.isfinite(ca) and np.isfinite(cb) and ca * cb < 0 and
                             abs(ca) > 0.02 and abs(cb) > 0.02) else ""
            print(f"   {f:14s} {co:>9.3f} {ca:>9.3f} {cb:>9.3f}  {flip:>9s}")

    # stability WITHIN regime across months for the best feature/conditioner
    print("\n### within-regime stability across months (gamma_sign), feature=mbp_sv_1m")
    if "mbp_sv_1m" in mv.columns:
        for reg, mask in (("gamma+", mv.opt_gamma_sign > 0), ("gamma-", mv.opt_gamma_sign <= 0)):
            sub = mv[mask]
            row = []
            for m, g in sub.groupby("mo"):
                c, n = corr(g["mbp_sv_1m"], g["dir"])
                row.append(f"{m}:{c:+.2f}(n{n})" if np.isfinite(c) else f"{m}:na")
            print(f"  {reg}: " + "  ".join(row))

    # quick directional-book test using the sign-flip conditioning (in-sample signal check)
    print("\n### in-sample directional book gated by regime (sign-agnostic best feature)")
    for f in ["mbp_sv_1m", "mbp_ofi_1m", "mbp_sv_5m"]:
        if f not in mv.columns:
            continue
        # learn sign per regime from the data (in-sample, descriptive — not a strategy yet)
        best = 0.0
        for cname, mask in conds.items():
            r = 0.0
            for sub in (mv[mask], mv[~mask]):
                c, _ = corr(sub[f], sub["dir"])
                if np.isfinite(c):
                    # trade in the corr's direction within the regime: r ~ |corr| * sign consistency
                    sig = np.sign(c) * np.sign(sub[f].fillna(0))
                    r += float((sig * sub["dir"]).mean()) * len(sub)
            r /= len(mv)
            best = max(best, r)
        print(f"  {f}: best regime-gated hit-bias = {best:+.4f} (descriptive, in-sample)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
