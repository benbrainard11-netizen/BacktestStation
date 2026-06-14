"""Layer 1 -- opportunity generator (objective intraday level-touch events).

Phase 1 reproduce: ES, PDH/PDL only. This does NOT reimplement the Stage-1 math
-- it reuses the exact kernels from market_state/intraday/zone_events.py
(cks_ofi_inc, peer_ofi_stream, label_touch, precompute_levels, available_days)
and only re-expresses the per-day orchestration into the project's layers.

Reader path (Step 1b):
  reader="raw"          -> read_mbp1([day, nxt) UTC calendar window  -- the Stage-1 path
  reader="trading_day"  -> read_mbp1_trading_day (CME session window, the repo's
                           data-discipline default per docs/MBO_TRADING_DAY_CONTRACT.md)
Same numeric kernels either way; only the per-day row WINDOW differs. Level set
(PDH/PDL from zone_events.precompute_levels) is unchanged.
"""

from __future__ import annotations

import _paths  # noqa: F401  (sys.path bootstrap; must be first)
import datetime as _dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

import zone_events as ze
from app.data.reader import read_mbp1_trading_day

_MBP1_COLS = [
    "ts_event",
    "bid_px",
    "ask_px",
    "bid_sz",
    "ask_sz",
    "action",
    "side",
    "size",
]
_PEER_COLS = ["ts_event", "bid_px", "ask_px", "bid_sz", "ask_sz"]


@dataclass(frozen=True)
class DayContext:
    """Per-day MBP-1 arrays for one symbol (post finite-mask), plus peer OFI streams."""

    tsi: pd.DatetimeIndex
    mid: np.ndarray
    ofi: np.ndarray
    strade: np.ndarray  # signed aggressor trade size per row
    bid_sz: np.ndarray
    ask_sz: np.ndarray
    peers: dict  # {"nq": (DatetimeIndex, ofi_array), ...}; missing peer -> absent


def precompute_levels() -> dict:
    """PDH/PDL per trading day (reuse zone_events; the Phase-1 reference source)."""
    return ze.precompute_levels()


def available_days() -> list[str]:
    return ze.available_days()


def _peer_ofi_stream_td(sym: str, trading_day: str):
    """Trading-day-window twin of zone_events.peer_ofi_stream (reuses cks_ofi_inc)."""
    d = read_mbp1_trading_day(symbol=sym, trading_day=trading_day, columns=_PEER_COLS)
    if len(d) < 100:
        return None
    bp, ap = d["bid_px"].to_numpy(float), d["ask_px"].to_numpy(float)
    bs, asz = d["bid_sz"].to_numpy(float), d["ask_sz"].to_numpy(float)
    ok = np.isfinite(bp) & np.isfinite(ap) & (bp > 0) & (ap > 0)
    if ok.sum() < 100:
        return None
    ts = pd.DatetimeIndex(pd.to_datetime(d["ts_event"], utc=True))[ok]
    return ts, ze.cks_ofi_inc(bp[ok], bs[ok], ap[ok], asz[ok])


def load_day(symbol: str, day: str, reader: str = "trading_day") -> DayContext | None:
    """Build the DayContext for ``symbol`` on ``day``.

    Data prep mirrors zone_events.process_day exactly (same finite mask, same CKS
    OFI, same signed-trade rule, same peer streams) -- only the read WINDOW differs
    by ``reader``. Returns None when the day has too little data (matches the
    original's <100 guards).
    """
    if reader == "trading_day":
        d = read_mbp1_trading_day(symbol=symbol, trading_day=day, columns=_MBP1_COLS)
        peer_src = lambda p: _peer_ofi_stream_td(p, day)  # noqa: E731
    elif reader == "raw":
        nxt = (_dt.date.fromisoformat(day) + _dt.timedelta(days=1)).isoformat()
        d = ze.read_mbp1(symbol=symbol, start=day, end=nxt, columns=_MBP1_COLS)
        peer_src = lambda p: ze.peer_ofi_stream(p, day, nxt)  # noqa: E731
    else:
        raise ValueError(f"unknown reader {reader!r}; use 'raw' or 'trading_day'")

    if len(d) < 100:
        return None
    ts = pd.to_datetime(d["ts_event"], utc=True)
    bp, ap = d["bid_px"].to_numpy(float), d["ask_px"].to_numpy(float)
    bs, asz = d["bid_sz"].to_numpy(float), d["ask_sz"].to_numpy(float)
    act, sd, sz = (
        d["action"].to_numpy(),
        d["side"].to_numpy(),
        d["size"].to_numpy(float),
    )
    ok = np.isfinite(bp) & np.isfinite(ap) & (bp > 0) & (ap > 0)
    if ok.sum() < 100:
        return None
    ts, bp, ap, bs, asz = ts[ok], bp[ok], ap[ok], bs[ok], asz[ok]
    act, sd, sz = act[ok], sd[ok], sz[ok]
    mid = (bp + ap) / 2.0
    ofi = ze.cks_ofi_inc(bp, bs, ap, asz)
    strade = np.where(
        act == "T", np.where(sd == "B", 1.0, np.where(sd == "A", -1.0, 0.0)) * sz, 0.0
    )
    peers = {}
    for p in ze.PEERS:
        r = peer_src(p)
        if r is not None:
            peers[p.split(".")[0].lower()] = r
    return DayContext(
        tsi=pd.DatetimeIndex(ts),
        mid=mid,
        ofi=ofi,
        strade=strade,
        bid_sz=bs,
        ask_sz=asz,
        peers=peers,
    )


def iter_candidates(ctx: DayContext, pdh: float, pdl: float):
    """Yield (i0, t0, role, level_price, dir) for every PDH/PDL touch onset.

    A touch = mid within EPS of the level; onset = first row entering the band.
    dir = break direction (1 up, -1 down) inferred from the mid 60s before the
    touch. Cooldown is NOT applied here -- the driver applies it (it is coupled
    with label resolution in the Stage-1 reference). Order: all PDH, then PDL.
    """
    for L, role in ((pdh, "PDH"), (pdl, "PDL")):
        in_band = np.abs(ctx.mid - L) <= ze.EPS
        onsets = np.where(in_band & ~np.r_[False, in_band[:-1]])[0]
        for i0 in onsets:
            t0 = ctx.tsi[i0]
            ib = max(0, ctx.tsi.searchsorted(t0 - pd.Timedelta("60s")) - 1)
            dr = 1 if ctx.mid[ib] < L else -1
            yield int(i0), t0, role, float(L), dr
