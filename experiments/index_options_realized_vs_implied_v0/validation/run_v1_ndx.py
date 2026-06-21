"""v1 NDX independent-product replication runner (NO model). Tests ONE hypothesis:
short RICH ATM straddles outperform short CHEAP and same-DTE unconditional short, after bid/ask + tail.

Rank-only (CHEAP/MID/RICH) -- NOT regime-conditioned (regime was the failed v0 primary). Naked short
straddle is the audit MEASURING INSTRUMENT only. main() raises until V1_NDX_REPLICATION_PROTOCOL is LOCKED.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from options.expiry_selection import select_expiry  # noqa: E402
from options.implied_move import (  # noqa: E402
    dte_norm_implied_move, implied_move_mid, passes_quote_filter, select_atm, straddle_quotes,
)
from options.straddle_proxy import short_straddle_pnl, short_straddle_pnl_stressed  # noqa: E402
from validation.significance import summarize  # noqa: E402
from validation.state_buckets import bucket_3, rolling_prior_percentile  # noqa: E402
from validation.tail_metrics import tail_report  # noqa: E402

SPEC = dict(dte_lo=1, dte_hi=7, rank_window=252, min_n_rich=250, atm_band=0.04, start="2018-01-01")
RANKS = ["cheap", "mid", "rich"]


def assemble_short_entries(chain: pd.DataFrame, underlying: pd.Series) -> pd.DataFrame:
    """One short ATM-straddle entry per eligible NDX date. underlying = NQ close (date_dt -> level)."""
    import numpy as np
    trading_dates = np.array(sorted(underlying.index.values), dtype="datetime64[ns]")
    rows = []
    for t, day in chain.groupby("date_dt"):
        if t not in underlying.index:
            continue
        s_t = float(underlying.loc[t])
        expiry, dte = select_expiry(pd.Timestamp(t), day["exp_dt"], trading_dates,
                                    SPEC["dte_lo"], SPEC["dte_hi"])
        if expiry is None or pd.Timestamp(expiry) not in underlying.index:
            continue
        atm = select_atm(day[day["exp_dt"] == expiry][["strike", "right", "bid", "ask"]], s_t)
        if atm is None:
            continue
        sq = straddle_quotes(atm)
        if not passes_quote_filter(sq):
            continue
        s_exp = float(underlying.loc[pd.Timestamp(expiry)])
        sp = short_straddle_pnl(atm, s_t, s_exp)
        im = implied_move_mid(sq["straddle_mid"], s_t)
        rows.append({"date": t, "dte": dte, "underlying": s_t,
                     "pnl_pct": sp["pnl_pct"], "pnl_R": sp["pnl_R"],
                     "pnl_pct_stress": short_straddle_pnl_stressed(atm, s_t, s_exp)["pnl_pct"],
                     "dte_norm": dte_norm_implied_move(im, dte)})
    df = pd.DataFrame(rows).set_index("date").sort_index()
    df["implied_move_rank"] = bucket_3(rolling_prior_percentile(df["dte_norm"], SPEC["rank_window"]))
    return df


def rank_bucket_table(entries: pd.DataFrame) -> pd.DataFrame:
    """Per rank bucket: short P&L, excess over same-DTE unconditional short (HAC), and tail bundle."""
    base = entries.groupby("dte")["pnl_pct"].transform("mean")  # same-DTE unconditional short
    e = entries.assign(excess=entries["pnl_pct"] - base)
    out = {}
    for r in RANKS:
        g = e[e["implied_move_rank"] == r]
        if g.empty:
            continue
        exc = summarize(g["excess"])
        row = {"n": len(g), "mean_pnl_pct": g["pnl_pct"].mean(),
               "excess_vs_sameDTE": exc["mean"], "excess_hac_t": exc["hac_t"], "mde_95": exc["mde_95"],
               "mean_pnl_pct_stress": g["pnl_pct_stress"].mean(), "median_dte": g["dte"].median()}
        row.update(tail_report(g["pnl_pct"], g["pnl_R"]))
        out[r] = row
    return pd.DataFrame(out).T


def classify_rich(table: pd.DataFrame) -> dict:
    """PULSE/EDGE on RICH-short, per the locked gates. RICH must beat CHEAP and same-DTE baseline."""
    if "rich" not in table.index or "cheap" not in table.index:
        return {"verdict": "ABSENT", "reason": "missing rich/cheap bucket"}
    r, c = table.loc["rich"], table.loc["cheap"]
    rich_minus_cheap = r["mean_pnl_pct"] - c["mean_pnl_pct"]
    pulse = (r["n"] >= SPEC["min_n_rich"] and r["mean_pnl_pct"] > 0 and r["excess_vs_sameDTE"] > 0
             and rich_minus_cheap > 0
             and (r["excess_hac_t"] > 1.5 or abs(r["excess_vs_sameDTE"]) > r["mde_95"])
             and r["mean_pnl_pct_stress"] >= 0
             and r["mean_over_abs_cvar5"] >= 0.03 and r["p_R_lt_-3"] <= 0.05 and r["p_R_lt_-5"] <= 0.02)
    edge = (pulse and r["excess_hac_t"] > 2 and r["mean_over_abs_cvar5"] >= 0.07
            and r["p_R_lt_-3"] <= 0.03 and r["p_R_lt_-5"] <= 0.01)
    tail_fail = r["mean_pnl_pct"] > 0 and r["mean_over_abs_cvar5"] < 0.03
    verdict = "EDGE" if edge else "PULSE" if pulse else (
        "VRP exists but naked expression NOT harvestable (tail)" if tail_fail else "NO PASS")
    return {"verdict": verdict, "n_rich": int(r["n"]), "rich_minus_cheap": rich_minus_cheap,
            "excess_vs_sameDTE": r["excess_vs_sameDTE"], "excess_hac_t": r["excess_hac_t"],
            "mean_over_abs_cvar5": r["mean_over_abs_cvar5"]}


def main() -> None:  # pragma: no cover - run step, gated on lock
    raise NotImplementedError(
        "Run gate (after docs/V1_NDX_REPLICATION_PROTOCOL.md is LOCKED): "
        "1) nq_close = NQ.c.0 daily close (Series by int YYYYMMDD) for the ATM/underlying proxy; "
        "2) options/chain_loader.build_ndx_chain(out/ndx_eod_chain.parquet, nq_close); "
        "3) underlying = NQ close by date_dt; assemble_short_entries -> rank_bucket_table -> classify_rich; "
        "4) report (incl. drop-worst-5-expiries, year-by-year, 2018-19/2020-22/2023-26, tail by bucket). "
        "STOP rule: if NDX fails/unresolved, the index-options line is SHELVED -- no RUT/DJX/SPX recuts."
    )
