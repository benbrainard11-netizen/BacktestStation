"""Index-options realized-vs-implied payoff audit -- orchestrator (NO model).

Builds the per-entry table (one ATM straddle per date) then the state->payoff table by
vol_regime x implied_move_rank, with a same-DTE unconditional baseline and HAC significance.
Mode A pricing audit (quotes at close t, settle at expiry). NOT run until the protocol is locked.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from options.expiry_selection import is_am_settled, select_expiry  # noqa: E402
from options.implied_move import (  # noqa: E402
    dte_norm_implied_move, implied_move_ask, implied_move_mid, passes_quote_filter,
    select_atm, straddle_quotes,
)
from options.straddle_proxy import straddle_pnl, straddle_pnl_stressed  # noqa: E402
from validation.significance import summarize  # noqa: E402
from validation.state_buckets import (  # noqa: E402
    assign_buckets, bucket_3, rolling_prior_percentile,
)

# LOCKED primary hypothesis -- the ONLY bucket eligible for PULSE/EDGE (anti bucket-shopping).
# Long-vol thesis: cheap-priced straddles in a VOLATILE regime should under-price the realized move.
PRIMARY_BUCKET = "VOLATILE x cheap"


def expiry_exclusion_report(chain: pd.DataFrame) -> dict:
    """Log how much the fail-closed settlement gate drops (GPT: surface this before trusting a run)."""
    expiries = pd.to_datetime(chain["exp_dt"].unique())
    am = [e for e in expiries if is_am_settled(pd.Timestamp(e))]
    return {
        "am_risk_expiries_excluded_count": len(am),
        "am_risk_expiries_excluded_dates": sorted(pd.Timestamp(e).date() for e in am),
        "total_expiries": len(expiries),
    }


def assemble_entries(chain: pd.DataFrame, underlying: pd.Series, vol_regime: pd.Series) -> pd.DataFrame:
    """One ATM-straddle entry per eligible date. `vol_regime` = canonical date->CALM/NORMAL/VOLATILE
    (validation/vol_regime_adapter). chain cols: date_dt, exp_dt, strike, right, bid, ask."""
    trading_dates = np.array(sorted(underlying.index.values), dtype="datetime64[ns]")
    rows = []
    for t, day in chain.groupby("date_dt"):
        if t not in underlying.index:
            continue
        s_t = float(underlying.loc[t])
        expiry, dte = select_expiry(pd.Timestamp(t), day["exp_dt"], trading_dates)
        if expiry is None or pd.Timestamp(expiry) not in underlying.index:
            continue
        q = day[day["exp_dt"] == expiry][["strike", "right", "bid", "ask"]]
        atm = select_atm(q, s_t)
        if atm is None:
            continue
        sq = straddle_quotes(atm)
        if not passes_quote_filter(sq):
            continue
        s_exp = float(underlying.loc[pd.Timestamp(expiry)])
        pnl = straddle_pnl(atm, s_t, s_exp)
        rows.append({
            "date": t, "expiry": expiry, "dte": dte, "strike": atm["strike"],
            "underlying": s_t, "s_expiry": s_exp,
            "implied_move_ask": implied_move_ask(sq["straddle_ask"], s_t),
            "implied_move_mid": implied_move_mid(sq["straddle_mid"], s_t),
            "dte_norm_im": dte_norm_implied_move(implied_move_mid(sq["straddle_mid"], s_t), dte),
            "realized_move": abs(s_exp - s_t) / s_t,
            "pnl_pct": pnl["pnl_pct"], "pnl_points": pnl["pnl_points"],
            "pnl_pct_stress": straddle_pnl_stressed(atm, s_t, s_exp)["pnl_pct"],
        })
    df = pd.DataFrame(rows).set_index("date").sort_index()
    df["realized_over_implied"] = df["realized_move"] / df["implied_move_mid"]
    return _add_state(df, vol_regime)


def _add_state(entries: pd.DataFrame, vol_regime: pd.Series) -> pd.DataFrame:
    """Attach the canonical vol_regime and the prior-252 implied_move_rank bucket."""
    vr = vol_regime.reindex(entries.index).ffill()
    entries = entries.copy()
    entries["vol_regime"] = vr
    entries["implied_move_rank"] = bucket_3(rolling_prior_percentile(entries["dte_norm_im"]))
    return assign_buckets(entries)


def classify_primary(table: pd.DataFrame) -> dict:
    """Evaluate ONLY the frozen primary bucket (VOLATILE x cheap). All others are diagnostics and
    can never be promoted to a pass after the run -- the anti-bucket-shopping rule."""
    if PRIMARY_BUCKET not in table.index:
        return {"bucket": PRIMARY_BUCKET, "verdict": "ABSENT (no entries in primary bucket)"}
    r = table.loc[PRIMARY_BUCKET]
    pulse = (r["n"] >= 100 and r["mean_pnl_pct"] > 0 and r["edge_vs_dte_baseline"] > 0
             and (r["edge_hac_t"] > 1.5 or abs(r["edge_vs_dte_baseline"]) > r["mde_95"])
             and r["mean_pnl_pct_stress"] > -abs(r["mean_pnl_pct"]))
    edge = pulse and r["edge_hac_t"] > 2 and r["mean_pnl_pct_stress"] > 0
    verdict = "EDGE" if edge else ("PULSE" if pulse else "NO PASS")
    return {"bucket": PRIMARY_BUCKET, "verdict": verdict, "n": int(r["n"]),
            "edge_vs_baseline": r["edge_vs_dte_baseline"], "edge_hac_t": r["edge_hac_t"]}


def dte_matched_baseline(entries: pd.DataFrame) -> pd.Series:
    """Unconditional mean pnl_pct among entries with the SAME dte (the locked baseline)."""
    return entries.groupby("dte")["pnl_pct"].transform("mean")


def bucket_table(entries: pd.DataFrame) -> pd.DataFrame:
    """State->payoff table: n, implied/realized, payoff stats vs same-DTE baseline, HAC."""
    base = dte_matched_baseline(entries)
    e = entries.assign(edge=entries["pnl_pct"] - base)
    out = {}
    for bucket, g in e.groupby("bucket"):
        s = summarize(g["pnl_pct"])
        es = summarize(g["edge"])
        out[bucket] = {
            "n": s["n"], "median_implied": g["implied_move_ask"].median(),
            "median_realized": g["realized_move"].median(),
            "realized_over_implied": g["realized_over_implied"].median(),
            "mean_pnl_pct": s["mean"], "hac_t": s["hac_t"], "mde_95": s["mde_95"],
            "edge_vs_dte_baseline": es["mean"], "edge_hac_t": es["hac_t"],
            "mean_pnl_pct_stress": g["pnl_pct_stress"].mean(),
            "median_dte": g["dte"].median(), "dte_min": int(g["dte"].min()),
            "dte_max": int(g["dte"].max()), "median_realized_over_implied": g["realized_over_implied"].median(),
        }
    return pd.DataFrame(out).T


def main() -> None:  # pragma: no cover - run step, reads the cache; gated on lock
    raise NotImplementedError(
        "Run gate (after docs/INDEX_OPTIONS_AUDIT_PROTOCOL.md is LOCKED): "
        "1) options/chain_loader.build_spx_chain(out/spx_eod_chain.parquet); "
        "2) validation/vol_regime_adapter.build_vol_regime(out/vol_regime.parquet)  # CANONICAL regime; "
        "3) expiry_exclusion_report(chain) -> log am-excluded counts; "
        "4) assemble_entries(chain, underlying, vol_regime) -> bucket_table -> classify_primary; "
        "5) write reports/. Same-DTE baseline is computed within the reported slice. "
        "ONLY 'VOLATILE x cheap' is eligible for PULSE/EDGE; all other buckets are diagnostics."
    )
