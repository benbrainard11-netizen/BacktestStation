"""Touch detection on MBP-1 mid against valid_from-bearing level instances.

PLAN compliance baked in:
  rule A1 — every emitted touch asserts touch_onset_ts >= valid_from (and < valid_to);
  Phase 0 — 15-min cooldown keyed off RAW onsets unconditionally (zone_events.py's
            post-label cooldown is future-dependent sample selection; not imported);
  rule 3  — detection on MBP-1 mid only; bars never price touches.

NO reaction outcomes here: the power table publishes touch counts BEFORE any reaction
stat is unblinded (PLAN rule C21). The atlas stage adds outcomes in a later script.

Importable; no CLI.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from spec import APPROACH_WIN, COOLDOWN, EPS_TICKS, REPO, TICK, tod_bucket

import sys  # noqa: E402

sys.path.insert(0, str(REPO / "backend"))
from app.data.reader import read_mbp1_trading_day  # noqa: E402

ET = ZoneInfo("America/New_York")


def load_day_quotes(sym: str, trading_day: dt.date):
    """(ts[ns, naive-UTC], bid, ask, mid) for the Globex trading day; None if empty."""
    t = read_mbp1_trading_day(
        symbol=sym,
        trading_day=trading_day,
        columns=["ts_event", "bid_px", "ask_px", "bid_sz", "ask_sz"],
    )
    if len(t) < 100:
        return None
    ts = pd.DatetimeIndex(pd.to_datetime(t["ts_event"], utc=True)).tz_localize(None)
    bid = np.asarray(t["bid_px"], dtype=float)
    ask = np.asarray(t["ask_px"], dtype=float)
    bsz = np.asarray(t["bid_sz"], dtype=float)
    asz = np.asarray(t["ask_sz"], dtype=float)
    ok = np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (ask > 0)
    if ok.sum() < 100:
        return None
    ts = pd.DatetimeIndex(ts[ok])
    bid, ask, bsz, asz = bid[ok], ask[ok], bsz[ok], asz[ok]
    return ts, bid, ask, (bid + ask) / 2.0, bsz, asz


def onsets_with_cooldown(
    ts: pd.DatetimeIndex,
    mid: np.ndarray,
    level: float,
    eps: float,
    cooldown: pd.Timedelta,
    i_lo: int,
    i_hi: int,
) -> list[int]:
    """Onset indices of |mid - level| <= eps within [i_lo, i_hi), cooldown on RAW onsets.

    The cooldown consumes EVERY onset (counted or not) — whether a touch later
    "resolves" can never influence which touches enter the sample.
    """
    seg = np.abs(mid[i_lo:i_hi] - level) <= eps
    if not seg.any():
        return []
    onset = seg & ~np.r_[i_lo > 0 and abs(mid[i_lo - 1] - level) <= eps, seg[:-1]]
    idx = np.flatnonzero(onset) + i_lo
    kept: list[int] = []
    last: pd.Timestamp | None = None
    for i in idx:
        t0 = ts[i]
        if last is None or (t0 - last) >= cooldown:
            kept.append(int(i))
        last = t0  # ALWAYS advances — raw-onset cooldown (suppressed onsets extend it)
    return kept


def detect_touches(
    sym: str, trading_day: dt.date, instances: pd.DataFrame, quotes
) -> list[dict]:
    """Touch records for one (symbol, trading day). `instances` = that day's levels."""
    ts, bid, ask, mid, bsz, asz = quotes
    day_med_bsz = float(np.median(bsz)) or 1.0
    day_med_asz = float(np.median(asz)) or 1.0
    tick = TICK[sym]
    eps = EPS_TICKS * tick
    cd = pd.Timedelta(COOLDOWN)
    appr = pd.Timedelta(APPROACH_WIN)
    rows: list[dict] = []
    inst_px = instances["price"].to_numpy(float)
    inst_fam = instances["family"].to_numpy()
    inst_vf = instances["valid_from"].to_numpy()
    for inst in instances.itertuples(index=False):
        i_lo = int(ts.searchsorted(pd.Timestamp(inst.valid_from)))
        i_hi = int(ts.searchsorted(pd.Timestamp(inst.valid_to)))
        if i_hi - i_lo < 2:
            continue
        for n, i0 in enumerate(
            onsets_with_cooldown(ts, mid, inst.price, eps, cd, i_lo, i_hi), 1
        ):
            t0 = ts[i0]
            assert t0 >= pd.Timestamp(
                inst.valid_from
            ), (  # rule A1 — never trips silently
                f"touch before valid_from: {inst.level_id} {t0} < {inst.valid_from}"
            )
            ia = max(i_lo, int(ts.searchsorted(t0 - appr)) - 1)
            a_mid = mid[ia]
            from_below = a_mid < inst.price
            # MECHANISMS #2b — the at-touch wall: size displayed on the side DEFENDING
            # the level (approach from below -> asks defend; from above -> bids defend).
            defend = float(asz[i0]) if from_below else float(bsz[i0])
            defend_med = day_med_asz if from_below else day_med_bsz
            # rule A6 confluence: OTHER families with a level within 2 ticks that
            # already EXIST at t0 (valid_from <= t0) — future levels can't vote.
            conf = int(
                len(
                    set(
                        inst_fam[
                            (np.abs(inst_px - inst.price) <= eps)
                            & (inst_vf <= np.datetime64(t0))
                            & (inst_fam != inst.family)
                        ]
                    )
                )
            )
            et_min = t0.tz_localize("UTC").tz_convert(ET)
            rows.append(
                {
                    "symbol": sym,
                    "trading_day": trading_day,
                    "family": inst.family,
                    "level_id": inst.level_id,
                    "level_key": inst.level_key,
                    "price": inst.price,
                    "t0": t0,
                    "touch_n": n,
                    "side": "below" if from_below else "above",
                    "approach_ticks_min": float((mid[i0] - a_mid) / tick),
                    "spread_ticks": float((ask[i0] - bid[i0]) / tick),
                    "defend_sz": defend,
                    "defend_sz_norm": defend / defend_med,
                    "confluence": conf,
                    "tod_bucket": tod_bucket(et_min.hour * 60 + et_min.minute),
                    "i0": int(i0),  # tick index of onset (outcome stage anchors here)
                    "i_hi": i_hi,  # validity end index (day/level truncation bound)
                }
            )
    return rows
