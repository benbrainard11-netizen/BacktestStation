"""MBP-1 order-flow feature engine (mbp_ block) — Iteration 1.

Top-of-book only: absorption/sweep-style quantities are PROXIES, not full-depth truth.
At decision time t, every feature uses events with ts_event <= t (asserted). Windows
end exactly at t. Raw flow sums are scaled to thousands of contracts.

Scope is deliberately tight (~30 features): top-of-book imbalance, Cont-style OFI,
aggressive trade flow, price/flow divergence, spread/intensity, and objective-relative
interactions. Skipped on purpose (logged, not silent): depth-replenishment proxies and
cross-day time-of-day normalization (within-day causal z instead).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date

import numpy as np
import pyarrow.parquet as pq

import common as C
import data_io as D

LARGE_LOT = 10  # registered: a "large" trade is >= 10 contracts
WINDOWS_NS = {"10s": 10 * 10**9, "30s": 30 * 10**9, "1m": 60 * 10**9, "5m": 300 * 10**9}
PRELOAD_MIN = 10  # load from 09:25 ET so 09:35 decisions have full 5m+ lookback
KSCALE = 1e-3  # contracts -> thousands


@dataclass
class DayArrays:
    ts: np.ndarray          # int64 ns, sorted
    bid_px: np.ndarray
    ask_px: np.ndarray
    bid_sz: np.ndarray
    ask_sz: np.ndarray
    cum_vol: np.ndarray     # trades only, cumulative contracts
    cum_sv: np.ndarray      # signed (aggressor) volume
    cum_tc: np.ndarray      # trade count
    cum_lrg_net: np.ndarray  # signed count of large trades
    cum_lrg_n: np.ndarray
    cum_ofi: np.ndarray     # Cont top-of-book order-flow imbalance
    cum_q: np.ndarray       # non-trade (book-update) event count
    cum_tbi: np.ndarray     # cumulative top-book imbalance (for window means)


def load_day(day: Date, root=None) -> DayArrays | None:
    path = (root or C.MBP1_ES) / f"date={day.isoformat()}" / "part-000.parquet"
    if not path.exists():
        return None
    lo = D.et_ts(day, (9 * 60 + 35 - PRELOAD_MIN) * 60_000)
    hi = D.et_ts(day, (15 * 60 + 46) * 60_000)
    tbl = pq.ParquetFile(path).read(
        columns=["ts_event", "action", "side", "size", "bid_px", "ask_px", "bid_sz", "ask_sz", "sequence"]
    )
    ts_all = tbl["ts_event"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    m = (ts_all >= lo.value) & (ts_all < hi.value)
    if m.sum() < 1000:
        return None
    # deterministic exchange ordering: the mirror's sort is unstable across same-ns
    # events, which makes OFI path-dependent — re-order by (ts, sequence) (review M1)
    seq = tbl["sequence"].to_numpy().astype(np.int64)[m]
    ts = ts_all[m]
    order = np.lexsort((seq, ts))
    ts = ts[order]
    assert np.all(np.diff(ts) >= 0), "MBP partition not ts-sorted after lexsort"  # review L1
    action = tbl["action"].to_numpy(zero_copy_only=False)[m][order]
    side = tbl["side"].to_numpy(zero_copy_only=False)[m][order]
    size = tbl["size"].to_numpy().astype(np.float64)[m][order]
    bid_px = tbl["bid_px"].to_numpy().astype(np.float64)[m][order]
    ask_px = tbl["ask_px"].to_numpy().astype(np.float64)[m][order]
    bid_sz = tbl["bid_sz"].to_numpy().astype(np.float64)[m][order]
    ask_sz = tbl["ask_sz"].to_numpy().astype(np.float64)[m][order]

    is_t = action == "T"
    sgn = np.where(side == "B", 1.0, np.where(side == "A", -1.0, 0.0))
    tvol = np.where(is_t, size, 0.0)
    sv = np.where(is_t, size * sgn, 0.0)
    lrg = is_t & (size >= LARGE_LOT)

    # Cont-style OFI from consecutive best-quote states
    ofi = np.zeros(len(ts))
    db, da = np.diff(bid_px), np.diff(ask_px)
    ofi[1:] = (
        bid_sz[1:] * (db >= 0) - bid_sz[:-1] * (db <= 0)
        - (ask_sz[1:] * (da <= 0) - ask_sz[:-1] * (da >= 0))
    )

    denom = bid_sz + ask_sz
    tbi = np.where(denom > 0, (bid_sz - ask_sz) / denom, 0.0)
    return DayArrays(
        ts=ts, bid_px=bid_px, ask_px=ask_px, bid_sz=bid_sz, ask_sz=ask_sz,
        cum_vol=tvol.cumsum(), cum_sv=sv.cumsum(), cum_tc=is_t.astype(np.float64).cumsum(),
        cum_lrg_net=np.where(lrg, sgn, 0.0).cumsum(), cum_lrg_n=lrg.astype(np.float64).cumsum(),
        cum_ofi=ofi.cumsum(), cum_q=(~is_t).astype(np.float64).cumsum(), cum_tbi=tbi.cumsum(),
    )


def _wdiff(cum: np.ndarray, i_hi: int, i_lo: int) -> float:
    return float(cum[i_hi] - (cum[i_lo] if i_lo >= 0 else 0.0))


def features_at(a: DayArrays, t_ns: int) -> dict[str, float] | None:
    """Raw mbp_ features at decision time t. Returns None if no events <= t."""
    i = int(np.searchsorted(a.ts, t_ns, side="right")) - 1
    if i < 50:
        return None
    assert a.ts[i] <= t_ns, "MBP lookahead: event after decision time"  # rule 1
    f: dict[str, float] = {}
    bsz, asz = a.bid_sz[i], a.ask_sz[i]
    f["mbp_tbi"] = (bsz - asz) / (bsz + asz) if (bsz + asz) > 0 else np.nan
    f["mbp_spread_tk"] = (a.ask_px[i] - a.bid_px[i]) / C.TICK
    mid_now = (a.ask_px[i] + a.bid_px[i]) / 2.0

    for wname, wns in WINDOWS_NS.items():
        j = int(np.searchsorted(a.ts, t_ns - wns, side="right")) - 1
        f[f"mbp_ofi_{wname}"] = _wdiff(a.cum_ofi, i, j) * KSCALE
        f[f"mbp_sv_{wname}"] = _wdiff(a.cum_sv, i, j) * KSCALE
        if wname in ("10s", "1m"):
            mid_then = (a.ask_px[j] + a.bid_px[j]) / 2.0 if j >= 0 else np.nan
            f[f"mbp_ret_{wname}_tk"] = (mid_now - mid_then) / C.TICK
        if wname == "1m":
            vol = _wdiff(a.cum_vol, i, j)
            tc = _wdiff(a.cum_tc, i, j)
            nrow = i - j
            f["mbp_vol_1m"] = vol * KSCALE
            f["mbp_tc_1m"] = tc  # raw count (KSCALE is for contracts — review L3)
            f["mbp_avg_sz_1m"] = vol / tc if tc > 0 else np.nan
            f["mbp_quote_rate_1m"] = _wdiff(a.cum_q, i, j) / 60.0
            f["mbp_qt_ratio_1m"] = _wdiff(a.cum_q, i, j) / max(tc, 1.0)
            f["mbp_tbi_mean_1m"] = _wdiff(a.cum_tbi, i, j) / nrow if nrow > 0 else np.nan
        if wname == "5m":
            f["mbp_lrg_net_5m"] = _wdiff(a.cum_lrg_net, i, j)
            f["mbp_lrg_n_5m"] = _wdiff(a.cum_lrg_n, i, j)
    return f


# columns given a causal within-day z-score (>= MIN_PRIOR prior grid points, else NaN)
ZCOLS = ("mbp_ofi_1m", "mbp_sv_1m", "mbp_vol_1m", "mbp_tbi", "mbp_ret_1m_tk")
MIN_PRIOR = 8


def add_day_zscores(rows: list[dict]) -> None:
    """In place: z of row k computed from rows[:k] only (causal within the day)."""
    for col in ZCOLS:
        vals = np.array([r.get(col, np.nan) for r in rows], dtype=float)
        for k, r in enumerate(rows):
            prior = vals[:k]
            prior = prior[np.isfinite(prior)]
            if len(prior) < MIN_PRIOR or not np.isfinite(vals[k]):
                r[col + "_z"] = np.nan
                continue
            sd = prior.std()
            r[col + "_z"] = (vals[k] - prior.mean()) / sd if sd > 1e-9 else np.nan


def add_objective_interactions(row: dict, dist_up_atr: float, dist_dn_atr: float) -> None:
    """Flow/book pressure scaled by proximity of the objective it pushes toward."""
    svz, tbi = row.get("mbp_sv_1m_z", np.nan), row.get("mbp_tbi", np.nan)
    row["mbp_svz_x_invup"] = svz / (dist_up_atr + 0.1)
    row["mbp_svz_x_invdn"] = -svz / (dist_dn_atr + 0.1)
    row["mbp_tbi_x_invup"] = tbi / (dist_up_atr + 0.1)
    row["mbp_tbi_x_invdn"] = -tbi / (dist_dn_atr + 0.1)
    retz, volz = row.get("mbp_ret_1m_tk_z", np.nan), row.get("mbp_vol_1m_z", np.nan)
    row["mbp_impulse_1m"] = retz * volz
    row["mbp_div_1m"] = retz - row.get("mbp_sv_1m_z", np.nan)
