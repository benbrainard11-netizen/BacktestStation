"""Phase 2c key-question diagnostic (no model, no new data, no feature expansion).

Reads the canonical multi-head dataset (out/, gitignored) and answers the gating
question: is the high-OFI bucket losing because it never gets enough MFE, or
because it gets MFE the naive +-8tick/30m exit fails to capture?

VERIFIED VERDICT (2026-06-14, adversarial 3-lens panel): NULL after costs. The
honest 1R/1R race is negative in every ex-ante OFI bucket, corr(OFI, realized_R)
~= 0 (OFI is a volatility proxy, not a directional R edge), MFE ~= MAE (no
asymmetry), and alternative geometry is un-adjudicable on the summary (no tick
ordering). See report/phase2c_policy.md. The Phase-1 OFI->break classifier still
stands; it just does not define a standalone trade.

Run: backend/.venv/Scripts/python.exe experiments/prop_intraday_resolver_v0/diag_policy.py
"""

from __future__ import annotations

import _paths  # noqa: F401
from pathlib import Path

import numpy as np
import pandas as pd

import dataset

P = Path(dataset.OUT) / "dataset_ES_trading_day.parquet"

AGG = dict(
    n=("realized_R", "size"),
    frac_break=("y_break", "mean"),
    frac_chop=("y_chop_or_timeout", "mean"),
    tbs_rate=("y_target_before_stop", "mean"),
    avg_R=("realized_R", "mean"),
    med_R=("realized_R", "median"),
    avg_MFE_R=("mfe_R", "mean"),
    avg_MAE_R=("mae_R", "mean"),
    pMFE_ge05=("mfe_ge_05", "mean"),
    pMFE_ge1=("mfe_ge_1", "mean"),
    pMAE_ge1=("mae_ge_1", "mean"),
)


def _flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["mfe_ge_05"] = (df["mfe_R"] >= 0.5).astype(float)
    df["mfe_ge_1"] = (df["mfe_R"] >= 1.0).astype(float)
    df["mae_ge_1"] = (df["mae_R"] >= 1.0).astype(float)
    df["branch"] = np.where(
        df["y_break"] == 1, "break", np.where(df["y_hold"] == 1, "hold", "chop")
    )
    return df


def main() -> int:
    df = _flags(pd.read_parquet(P))
    print(f"loaded {len(df)} rows from {P.name}\n")

    for nq, names in ((3, ["low", "mid", "high"]), (5, ["q1", "q2", "q3", "q4", "q5"])):
        q = pd.qcut(df["ofi_signed"], nq, labels=names, duplicates="drop")
        tab = df.assign(_q=q).groupby("_q", observed=True).agg(**AGG)
        print(f"=== ALL events by OFI {'tercile' if nq == 3 else 'quintile'} ===")
        print(tab.round(3).to_string(), "\n")

    q3 = pd.qcut(df["ofi_signed"], 3, labels=["low", "mid", "high"], duplicates="drop")
    bx = df.assign(_q=q3).groupby(["_q", "branch"], observed=True).agg(**AGG)
    print("=== OFI tercile x branch (MFE/MAE focus) ===")
    print(bx.round(3).to_string(), "\n")

    # KEY QUESTION -- the honest, EX-ANTE, ordering-true test (adversarially verified
    # 2026-06-14). Bucket ONLY on ex-ante ofi_signed. The only TRUE stop-vs-target
    # ordering in the summary is y_target_before_stop (a 1R/1R race); realized_R is
    # capped at +-1, so the large MFE/MAE MAGNITUDES are NOT capturable by this label
    # and cannot adjudicate any target>1R geometry (no tick path / no MFE-vs-MAE
    # ordering). Conditioning on the branch outcome (y_break/y_hold) is post-hoc and
    # untradeable -- shown only as a leaky upper bound.
    COST_R = 0.25  # ~2 ticks of the 8-tick R, round-trip
    print(
        "=== KEY QUESTION: honest 1R/1R break-direction race by OFI tercile (ex-ante) ==="
    )
    race = (
        df.assign(_q=q3)
        .groupby("_q", observed=True)
        .agg(
            n=("realized_R", "size"),
            tbs_rate=("y_target_before_stop", "mean"),
            gross_R=("realized_R", "mean"),
        )
    )
    race["net_R_after_cost"] = race["gross_R"] - COST_R
    print(race.round(3).to_string())
    pr = float(df["ofi_signed"].corr(df["realized_R"]))
    sp = float(df["ofi_signed"].corr(df["realized_R"], method="spearman"))
    best_net = float(race["net_R_after_cost"].max())
    leaky = df[(q3 == "high") & (df["branch"] == "break")]["realized_R"].mean()
    print(
        f"\ncorr(OFI, realized_R): pearson={pr:+.3f} spearman={sp:+.3f}  "
        "(~0 -> OFI is a volatility proxy, not a directional R edge)"
    )
    print(f"best bucket net_R after {COST_R}R cost = {best_net:+.3f}")
    print(
        f"  (leaky upper bound, NOT tradeable) high-OFI & break-only avg_realized_R={leaky:+.3f}"
    )
    if best_net <= 0:
        verdict = (
            "NULL after costs. No ex-ante OFI bucket clears zero on the honest 1R/1R race; "
            "OFI gives no directional R-tilt (corr~0, vol proxy); MFE~=MAE so no asymmetry to harvest. "
            "Alternative target/stop/entry geometry is NOT adjudicable on this summary -> needs a "
            "tick-level (MBP-1) honest-bracket re-sim with ex-ante confirmation/reclaim entry."
        )
    else:
        verdict = f"some bucket clears zero net ({best_net:+.3f}) -> confirm with tick-level re-sim before trusting."
    print(f"\nVERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
