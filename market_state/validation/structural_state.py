"""STRUCTURAL state — rich/cheap of each symbol vs its cointegrated peer.

Reuses the EXACT validated pair method (xsectional_rv_v0 / energy_rv_v0): reconstruct
log-price from the validated daily-returns panel, rolling 250d hedge-ratio spread
(beta = cov/var), 60d z-score. The z-score is the rich/cheap reading; mean-reversion
lean = -z (a positive spread z is "rich A vs B" -> lean short the spread).

Two responsibilities:
  1. STATE (for the board): the CURRENT z per validated pair, using only data <= the
     last date (no-lookahead). A complex tile LIGHTS because its pairs are cointegration-
     validated (energy/grains/curve/metals); equity/FX pairs stay GREY (null).
  2. EVIDENCE (THE ONE RULE, in THIS codebase): re-earn "lit" with the EXACT validated
     metric -- the OOS Sharpe of the daily-rebalanced continuous mean-reversion book
     (energy_rv_v0/diversified_rv_book.py's net_series). A complex LIGHTS iff its book
     OOS Sharpe clears a floor; equity/FX must NOT. (NOTE: a fixed-horizon z-vs-spread-
     change rank correlation -- run as a secondary harness diagnostic below -- UNDERSTATES
     these edges, because the validated edge lives in the compounding daily-rebalanced P&L,
     not a raw N-day spread-change corr. The strategy Sharpe is the validated judge; the
     harness corr is just a no-lookahead cross-check on direction.)

The pair sets AND the net_series construction are COPIED VERBATIM from
energy_rv_v0/diversified_rv_book.py (validated); no new pairs are invented. Equity/FX
sets are the KNOWN-NULL controls.

Run: backend/.venv/Scripts/python.exe market_state/validation/structural_state.py
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
from harness import forward_test  # noqa: E402

RETURNS = Path("experiments/sync_regime_v0/out/daily_returns.parquet")
BETAWIN, ZWIN, COST_BPS = 250, 60, 2.0   # validated hedge-ratio + z windows + cost (do NOT retune)
FWD_DAYS = 10                     # spread-change lookahead for the secondary harness diagnostic
OOS_START = pd.Timestamp("2023-01-01")
RICH_Z, CHEAP_Z = 1.0, -1.0       # |z|>1 = stretched enough to call rich/cheap
ANN = np.sqrt(252.0)
LIT_OOS_SHARPE = 0.30             # a complex book must clear this OOS Sharpe to LIGHT
MAX_PAIR_HL = 90.0               # AND EVERY pair must mean-revert (max half-life < this).
#   The half-life gate is the memory's discriminator: FX books post high OOS Sharpe but are
#   SPURIOUS TREND not mean-reversion (6J/6N half-life 221d). Sharpe-alone would light FX.
#   We gate on the MAX (not median) pair half-life so a single spurious pair (the memory's
#   "never trade a 455d-half-life spread" rule) disqualifies the whole complex. This cleanly
#   greys FX (max 221d) + equity (max 151d) while keeping energy/grains/curve/metals (max
#   29/39/58/72d). (xsectional_rv_v0 memory.)

# VALIDATED structural complexes (verbatim from energy_rv_v0/diversified_rv_book.py).
COMPLEXES = {
    "energy": [("CL.c.0", "BZ.c.0"), ("CL.c.0", "RB.c.0"), ("CL.c.0", "HO.c.0"),
               ("BZ.c.0", "RB.c.0"), ("BZ.c.0", "HO.c.0")],
    "grains": [("ZC.c.0", "ZS.c.0"), ("ZS.c.0", "ZW.c.0"), ("ZC.c.0", "ZW.c.0")],
    "curve":  [("ZF.c.0", "ZN.c.0"), ("ZN.c.0", "ZB.c.0"), ("ZF.c.0", "ZT.c.0")],
    "metals": [("GC.c.0", "SI.c.0")],
}
# KNOWN-NULL controls (memory: equity pairs too efficient; FX = spuriousness trap).
NULL_COMPLEXES = {
    "equity": [("ES.c.0", "NQ.c.0"), ("ES.c.0", "YM.c.0"), ("NQ.c.0", "RTY.c.0")],
    "fx":     [("6E.c.0", "6B.c.0"), ("6A.c.0", "6C.c.0"), ("6J.c.0", "6N.c.0")],
}


def _spread_z(logp: pd.DataFrame, a: str, b: str) -> tuple[pd.Series, pd.Series]:
    """Rolling hedge-ratio spread + its 60d z-score (validated construction)."""
    A, B = logp[a], logp[b]
    beta = A.rolling(BETAWIN).cov(B) / B.rolling(BETAWIN).var()
    sp = A - beta * B
    z = (sp - sp.rolling(ZWIN).mean()) / sp.rolling(ZWIN).std()
    return sp, z


def net_series(R: pd.DataFrame, logp: pd.DataFrame, a: str, b: str) -> pd.Series:
    """Daily net P&L of the continuous MR position on the A-B spread. VERBATIM validated
    construction (diversified_rv_book.py): lean = -(z/2) clipped to [-1,1], shift(1) to
    trade next bar (no-lookahead), 2bp/leg turnover cost."""
    A, B = logp[a], logp[b]
    beta = A.rolling(BETAWIN).cov(B) / B.rolling(BETAWIN).var()
    sp = A - beta * B
    z = (sp - sp.rolling(ZWIN).mean()) / sp.rolling(ZWIN).std()
    pos = -(z / 2.0).clip(-1.0, 1.0)
    return pos.shift(1) * (R[a] - beta * R[b]) - pos.diff().abs() * (2.0 * COST_BPS) / 1e4


def _adf_halflife(spread: pd.Series) -> tuple[float, float]:
    """Engle-Granger ADF t-stat (no lags) + mean-reversion half-life. VERBATIM from
    xsectional_rv_v0/cointegration_select.py. More-negative ADF + short half-life =
    genuine cointegration (vs spurious trend, which has a huge half-life)."""
    s = spread.dropna()
    ds = s.diff().dropna()
    slag = s.shift(1).loc[ds.index]
    X = np.column_stack([np.ones(len(ds)), slag.to_numpy()])
    y = ds.to_numpy()
    try:
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ b
        s2 = float(resid @ resid) / (len(ds) - 2)
        se = float(np.sqrt(s2 * np.linalg.inv(X.T @ X)[1, 1]))
    except Exception:
        return float("nan"), np.inf
    t = b[1] / se if se > 0 else float("nan")
    hl = float(-np.log(2) / b[1]) if b[1] < 0 else np.inf
    return float(t), hl


def complex_max_halflife(logp: pd.DataFrame, pairs: list[tuple[str, str]]) -> float:
    """Worst (max) IN-SAMPLE pair half-life in a complex (no-lookahead: IS < OOS_START).
    A single long-half-life pair = a spurious-trend contaminant -> disqualifies the complex."""
    hls = []
    for a, b in pairs:
        if a not in logp.columns or b not in logp.columns:
            continue
        A_is = logp[a][logp.index < OOS_START]
        B_is = logp[b][logp.index < OOS_START]
        beta = np.cov(A_is, B_is)[0, 1] / np.var(B_is)
        _, hl = _adf_halflife(A_is - beta * B_is)
        hls.append(hl)
    return float(np.max(hls)) if hls else np.inf


def book_oos_sharpe(R: pd.DataFrame, logp: pd.DataFrame, pairs: list[tuple[str, str]]) -> tuple[float, int]:
    """Equal-weight complex book OOS Sharpe (the validated lighting metric) + n OOS days."""
    cols = [net_series(R, logp, a, b) for a, b in pairs if a in R.columns and b in R.columns]
    if not cols:
        return float("nan"), 0
    bk = pd.concat(cols, axis=1).mean(axis=1)
    oos = bk[bk.index >= OOS_START].dropna()
    if len(oos) < 50 or oos.std() == 0:
        return float("nan"), len(oos)
    return float(oos.mean() / oos.std() * ANN), len(oos)


def _lean(z: float) -> str:
    if not np.isfinite(z):
        return "n/a"
    if z >= RICH_Z:
        return "rich A -> revert DOWN (short spread)"
    if z <= CHEAP_Z:
        return "cheap A -> revert UP (long spread)"
    return "fair (in band)"


def forward_mr_frame(logp: pd.DataFrame, pairs: list[tuple[str, str]]) -> pd.DataFrame:
    """Pooled (z_t -> forward spread change) across a complex's pairs, for the harness.

    Mean-reversion predicts: high z_t -> spread FALLS over the next FWD_DAYS (negative
    change). So signal = z_t, outcome = -(sp[t+FWD] - sp[t]) / sp-vol -> mean-reversion is
    a POSITIVE relationship (high z -> positive 'reversion' outcome). No-lookahead: z_t uses
    only data <= t; the change is strictly forward.
    """
    frames = []
    for a, b in pairs:
        if a not in logp.columns or b not in logp.columns:
            continue
        sp, z = _spread_z(logp, a, b)
        chg = sp.shift(-FWD_DAYS) - sp                       # forward spread change
        scale = sp.diff().rolling(ZWIN).std()                # normalize cross-pair units
        rev = -chg / scale                                   # reversion outcome (high z should -> +)
        f = pd.DataFrame({"signal": z, "outcome": rev}).dropna()
        frames.append(f)
    return pd.concat(frames).sort_index() if frames else pd.DataFrame(columns=["signal", "outcome"])


def current_states(logp: pd.DataFrame) -> dict[str, list[dict]]:
    """Latest-date z per pair per complex (no-lookahead: rolling windows end at the last date)."""
    out: dict[str, list[dict]] = {}
    for name, pairs in {**COMPLEXES, **NULL_COMPLEXES}.items():
        rows = []
        for a, b in pairs:
            if a not in logp.columns or b not in logp.columns:
                continue
            _, z = _spread_z(logp, a, b)
            zc = float(z.dropna().iloc[-1]) if z.dropna().size else float("nan")
            rows.append({"pair": f"{a[:-4]}/{b[:-4]}", "z": zc, "lean": _lean(zc)})
        out[name] = rows
    return out


def evidence(R: pd.DataFrame, logp: pd.DataFrame) -> dict[str, bool]:
    """Re-earn 'lit' with the VALIDATED metric (book OOS Sharpe) + cointegration half-life gate."""
    print("=" * 78)
    print("  STRUCTURAL evidence -- validated MR-book OOS Sharpe + cointegration gate")
    print(f"  (OOS>= {OOS_START.date()}, {COST_BPS}bp/leg; LIT iff Sharpe>= {LIT_OOS_SHARPE} "
          f"AND max pair half-life< {MAX_PAIR_HL:.0f}d)")
    print("=" * 78)
    lit = {}
    for name, pairs in {**COMPLEXES, **NULL_COMPLEXES}.items():
        sh, n = book_oos_sharpe(R, logp, pairs)
        hl = complex_max_halflife(logp, pairs)
        good_sharpe = np.isfinite(sh) and sh >= LIT_OOS_SHARPE
        good_coint = np.isfinite(hl) and hl < MAX_PAIR_HL
        lit[name] = good_sharpe and good_coint
        tag = "LIT " if lit[name] else "grey"
        why = "" if lit[name] else (
            " <- high Sharpe but NOT cointegrated (spurious trend)" if (good_sharpe and not good_coint)
            else " <- Sharpe below floor" if not good_sharpe else "")
        diag = forward_test(forward_mr_frame(logp, pairs), name=name, kind="continuous",
                            oos_start=OOS_START, min_effect=0.0, expect_sign=1)
        print(f"  [{tag}] {name:7} book OOS Sharpe={sh:+.2f} (n={n})  max half-life={hl:5.0f}d"
              f"  [harness z->fwd rho {diag.oos_res.spearman:+.2f}]{why}")
    return lit


def persist(states: dict[str, list[dict]], lit: dict[str, bool], asof) -> None:
    """Write the structural state for the board (parquet, not pickle -- CLAUDE.md rule 6)."""
    out_rows = []
    for name in list(COMPLEXES) + list(NULL_COMPLEXES):
        for row in states[name]:
            out_rows.append({"complex": name, "lit": bool(lit.get(name, False)),
                             "pair": row["pair"], "z": row["z"], "lean": row["lean"]})
    out = pd.DataFrame(out_rows)
    out_path = Path("market_state/out/structural_state.parquet")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.attrs["asof"] = str(asof)
    out.to_parquet(out_path, index=False)
    print(f"  wrote {out_path} ({len(out)} pair-rows, asof {asof})")


def main() -> int:
    R = pd.read_parquet(RETURNS).sort_index()
    R.index = pd.DatetimeIndex(R.index).tz_localize(None)
    logp = R.cumsum()
    asof = R.index[-1].date()

    lit = evidence(R, logp)

    # --- STATE: current rich/cheap board ---
    states = current_states(logp)
    print("\n" + "=" * 78)
    print(f"  STRUCTURAL STATE BOARD   as of {asof}  (z = rich/cheap of A vs cointegrated B)")
    print("=" * 78)
    for name in list(COMPLEXES) + list(NULL_COMPLEXES):
        is_struct = name in COMPLEXES
        if is_struct and lit.get(name):
            flag = "LIT (cointegration-validated)"
        elif is_struct:
            flag = "grey (book OOS Sharpe below floor)"
        else:
            flag = "grey (validated null)"
        print(f"\n  {name.upper():7} [{flag}]")
        for row in states[name]:
            mark = " *" if (is_struct and lit.get(name) and abs(row["z"]) >= RICH_Z) else "  "
            print(f"   {mark}{row['pair']:9} z={row['z']:+5.2f}   {row['lean']}")
    print("\n" + "=" * 78)
    print("  LIT complexes show a current rich/cheap lean; grey = no validated MR edge (equity/FX).")
    print("  '*' = a pair currently stretched (|z|>=1) within a LIT complex = an actionable RV lean.")
    print("=" * 78)
    persist(states, lit, asof)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
