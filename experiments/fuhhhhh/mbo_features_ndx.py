"""Causal MBO order-book FLOW features for NQ (the new, leak-free 'compass' inputs).

The old Mira bookproxy features were built around a [trigger-30s, +60s] window — the +60s
forward peek was the look-ahead the 2026-06-11 audit killed. These are CAUSAL BY
CONSTRUCTION: every window is [t-W, t) (backward only), so no forward data can enter.
A no-lookahead assert guards it (rule 1).

What they capture that MBP-1 (top-of-book) cannot: PASSIVE book flow near the touch --
who is ADDING vs PULLING depth on each side, churn, and trade absorption. That 'stacking /
withdrawal' intent is the closest causal read on direction.

Banded near the running last-trade price (+-NEAR_TICKS), so deep-book noise is excluded.

Heavy: ~16M MBO events/day. Engine mirrors mbp_features (cumsum arrays + window diffs).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date

import numpy as np
import pyarrow.parquet as pq

import common as C
import data_io as D

NEAR_TICKS = 12                       # band: events within +-12 ticks (3 NQ pts) of last trade
WINDOWS_NS = {"30s": 30 * 10**9, "2m": 120 * 10**9}
PRELOAD_MIN = 10
KSCALE = 1e-3                          # contracts -> thousands


@dataclass
class MboDay:
    ts: np.ndarray
    last_tp: np.ndarray               # running last trade price (ffill)
    cum_add_b: np.ndarray
    cum_add_a: np.ndarray
    cum_cxl_b: np.ndarray
    cum_cxl_a: np.ndarray
    cum_exec: np.ndarray              # executed size (T/F)


def load_day(day: Date, root=None) -> MboDay | None:
    path = (root or C.MBO_CLEAN_NQ) / f"trading_day={day.isoformat()}" / "part-000.parquet"
    if not path.exists():
        return None
    lo = D.et_ts(day, (9 * 60 + 35 - PRELOAD_MIN) * 60_000)
    hi = D.et_ts(day, (15 * 60 + 46) * 60_000)
    tbl = pq.ParquetFile(path).read(columns=["ts_event", "action", "side", "price", "size", "sequence"])
    ts_all = tbl["ts_event"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    m = (ts_all >= lo.value) & (ts_all < hi.value)
    if m.sum() < 5000:
        return None
    seq = tbl["sequence"].to_numpy().astype(np.int64)[m]
    ts = ts_all[m]
    order = np.lexsort((seq, ts))
    ts = ts[order]
    assert np.all(np.diff(ts) >= 0), "MBO not ts-sorted after lexsort"
    action = tbl["action"].to_numpy(zero_copy_only=False)[m][order]
    side = tbl["side"].to_numpy(zero_copy_only=False)[m][order]
    price = tbl["price"].to_numpy().astype(np.float64)[m][order]
    size = tbl["size"].to_numpy().astype(np.float64)[m][order]

    is_add, is_cxl = action == "A", action == "C"
    is_exec = (action == "T") | (action == "F")
    bid, ask = side == "B", side == "A"

    # running last trade price (ffill); near-touch band defined per event causally
    tp = np.where(is_exec, price, np.nan)
    idx = np.where(~np.isnan(tp), np.arange(len(tp)), 0)
    np.maximum.accumulate(idx, out=idx)
    last_tp = tp[idx]
    near = np.isfinite(last_tp) & (np.abs(price - last_tp) <= NEAR_TICKS * C.TICK)

    def cum(mask):
        return np.where(mask, size, 0.0).cumsum()

    return MboDay(
        ts=ts, last_tp=last_tp,
        cum_add_b=cum(is_add & bid & near), cum_add_a=cum(is_add & ask & near),
        cum_cxl_b=cum(is_cxl & bid & near), cum_cxl_a=cum(is_cxl & ask & near),
        cum_exec=cum(is_exec),
    )


def _wd(cum, i, j):
    return float(cum[i] - (cum[j] if j >= 0 else 0.0))


def features_at(a: MboDay, t_ns: int) -> dict[str, float] | None:
    i = int(np.searchsorted(a.ts, t_ns, side="right")) - 1
    if i < 200:
        return None
    assert a.ts[i] <= t_ns, "MBO lookahead"      # rule 1
    f: dict[str, float] = {}
    for w, wns in WINDOWS_NS.items():
        j = int(np.searchsorted(a.ts, t_ns - wns, side="right")) - 1
        ab, aa = _wd(a.cum_add_b, i, j), _wd(a.cum_add_a, i, j)
        cb, ca = _wd(a.cum_cxl_b, i, j), _wd(a.cum_cxl_a, i, j)
        ex = _wd(a.cum_exec, i, j)
        addtot, cxltot = ab + aa, cb + ca
        f[f"mbo_add_imb_{w}"] = (ab - aa) / addtot if addtot > 0 else 0.0
        f[f"mbo_cxl_imb_{w}"] = (cb - ca) / cxltot if cxltot > 0 else 0.0
        # net resting build (adds minus pulls), bid vs ask
        net_b, net_a = ab - cb, aa - ca
        den = abs(net_b) + abs(net_a)
        f[f"mbo_netbuild_imb_{w}"] = (net_b - net_a) / den if den > 0 else 0.0
        f[f"mbo_pull_bid_{w}"] = cb / (ab + 1.0)
        f[f"mbo_pull_ask_{w}"] = ca / (aa + 1.0)
        f[f"mbo_churn_{w}"] = (addtot + cxltot) / (ex + 1.0)
        f[f"mbo_addflow_{w}"] = (ab - aa) * KSCALE
        if w == "2m":
            # absorption: executed volume relative to price travel (high vol / low move = absorb)
            mv = abs(a.last_tp[i] - a.last_tp[j]) / C.TICK if j >= 0 and np.isfinite(a.last_tp[j]) else np.nan
            f["mbo_absorb_2m"] = ex / (1.0 + mv) * KSCALE if np.isfinite(mv) else np.nan
            f["mbo_exec_2m"] = ex * KSCALE
    return f


ZCOLS = ("mbo_netbuild_imb_30s", "mbo_add_imb_30s", "mbo_addflow_2m", "mbo_churn_30s")
MIN_PRIOR = 8


def add_day_zscores(rows: list[dict]) -> None:
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
