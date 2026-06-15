"""Phase 2d -- resolver-as-CONDITIONER: does the OFI break-classifier gate the reclaim edge?

Pivot after the 2c NULL (the OFI break signal is not a standalone trade). A reclaim long/short bets
the level HOLDS (the sweep was a fake-out); the resolver's event-time OFI AT THE TOUCH answers "is
the break real?" -- a natural EX-ANTE filter. Test: compute touch-time signed OFI on the existing
tick-validated reclaim events (mira_upgraded_v0) and ask whether gating on it LIFTS the honest
sequenced-R OOS by a day-block bootstrap CI.

Reuses (read-only): mira_upgraded_v0/reclaim_entry.py (seq_r, boot, geometry, OOS split) and this
project's OFI kernel (zone_events.cks_ofi_inc via read_mbp1_trading_day). No new strategy; no model
unless a simple gate shows promise.

No-lookahead: OFI uses [touch, touch+2s], which ends minutes before the reclaim entry (asserted).

CAVEAT: reclaim OOS (2026-04-01+) is small (~tens of events); a clean NULL is a likely, acceptable
outcome (the MBO gate already hurt -- feature ceiling). Verify any positive lift adversarially.

Run: backend/.venv/Scripts/python.exe experiments/prop_intraday_resolver_v0/conditioner_test.py
"""

from __future__ import annotations

import _paths  # noqa: F401
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import zone_events as ze
from app.data.reader import read_mbp1_trading_day

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mira_upgraded_v0"))
import reclaim_entry as re_mod  # noqa: E402

W_OFI = pd.Timedelta("2s")
_PEER_COLS = ["ts_event", "bid_px", "ask_px", "bid_sz", "ask_sz"]
_cache: dict = {}


def _day_ofi(symbol: str, trading_day: str):
    """(tsi, ofi) for one symbol-day via the clean reader + the validated CKS kernel; OFI only (no peers)."""
    key = (symbol, trading_day)
    if key in _cache:
        return _cache[key]
    try:
        d = read_mbp1_trading_day(
            symbol=symbol, trading_day=trading_day, columns=_PEER_COLS
        )
    except Exception:
        _cache[key] = None
        return None
    if len(d) < 100:
        _cache[key] = None
        return None
    bp, ap = d["bid_px"].to_numpy(float), d["ask_px"].to_numpy(float)
    bs, asz = d["bid_sz"].to_numpy(float), d["ask_sz"].to_numpy(float)
    ok = np.isfinite(bp) & np.isfinite(ap) & (bp > 0) & (ap > 0)
    if ok.sum() < 100:
        _cache[key] = None
        return None
    tsi = pd.DatetimeIndex(pd.to_datetime(d["ts_event"], utc=True))[ok]
    out = (tsi, ze.cks_ofi_inc(bp[ok], bs[ok], ap[ok], asz[ok]))
    _cache[key] = out
    return out


def _dir(level_side: str) -> int:
    """Break/sweep direction: through a HIGH = up (+1), through a LOW = down (-1)."""
    s = str(level_side).lower()
    if "high" in s or s in ("h", "resistance", "up", "sell"):
        return 1
    return -1


def touch_ofi(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Signed event-time OFI over [touch, touch+2s] per event; + a no-lookahead-OK mask."""
    vals = np.full(len(df), np.nan)
    look_ok = np.ones(len(df), dtype=bool)
    sym = df["symbol"].to_numpy()
    tday = pd.to_datetime(df["session_date"]).dt.date.astype(str).to_numpy()
    tts = pd.to_datetime(df["touch_ts_utc"], utc=True)
    ext = pd.to_datetime(df["sweep.5m.sweep_extreme_ts_utc"], utc=True)
    side = df["level_side"].to_numpy()
    for i in range(len(df)):
        t0, te = tts.iloc[i], ext.iloc[i]
        # Ex-ante iff the OFI window ends at/before the sweep EXTREME -- the reclaim
        # entry is always after the extreme (seq_r brackets off post_extreme bars).
        # This precise guard drops the ~1/3 of events whose touch is logged AFTER
        # the extreme (ambiguous timeline) rather than crudely using whole-minute
        # time_to_reclaim. See report/phase2d_conditioner.md.
        if pd.isna(t0) or pd.isna(te) or (t0 + W_OFI) > te:
            look_ok[i] = False
        r = _day_ofi(sym[i], tday[i])
        if r is None or pd.isna(t0):
            continue
        tsi, ofi = r
        a = int(tsi.searchsorted(t0))
        b = int(tsi.searchsorted(t0 + W_OFI, side="right"))
        if b > a:
            vals[i] = float(ofi[a:b].sum()) * _dir(side[i])
    return vals, look_ok


def main() -> int:
    df = pd.read_parquet(re_mod.EV)
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    df = df[
        df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0
    ].copy()  # confirmation universe
    df["r"] = re_mod.seq_r(df, re_mod.TARGET_R)
    ofi, look_ok = touch_ofi(df)
    df["touch_ofi"] = ofi
    df["look_ok"] = look_ok
    usable = df[df["touch_ofi"].notna() & df["look_ok"]].copy()
    dropped = len(df) - len(usable)
    print(
        f"reclaim confirmation universe n={len(df)}  usable (OFI computed + no-lookahead) n={len(usable)}  "
        f"dropped={dropped}\n"
    )

    oos = usable[usable["day"] >= re_mod.OOS_START].copy()
    print(
        f"OOS (>= {re_mod.OOS_START}) n={len(oos)}  -- small sample, read CIs with care\n"
    )

    for lab, sub in (("FULL", usable), ("OOS", oos)):
        if len(sub) < 10:
            print(f"[{lab}] n<10, skip")
            continue
        pr = float(sub["touch_ofi"].corr(sub["r"]))
        sp = float(sub["touch_ofi"].corr(sub["r"], method="spearman"))
        print(
            f"[{lab}] corr(touch_OFI, reclaim_R): pearson={pr:+.3f} spearman={sp:+.3f}  (n={len(sub)})"
        )

    if len(oos) < 20:
        print(
            "\nOOS too thin for a gate CI; correlation above is the read. VERDICT: inconclusive (need more OOS)."
        )
        return 0

    days = oos["day"].to_numpy()
    bm, bl, bh = re_mod.boot(oos["r"].to_numpy(), days)
    med = float(np.median(oos["touch_ofi"].to_numpy()))
    lo = (
        oos["touch_ofi"].to_numpy() <= med
    )  # low break-OFI = sweep not flow-driven (hypothesis: better reclaim)
    hi = ~lo
    lm, ll, lh = re_mod.boot(oos["r"].to_numpy()[lo], days[lo])
    hm, hl, hh = re_mod.boot(oos["r"].to_numpy()[hi], days[hi])
    print("\nOOS reclaim 2R, day-block CI [5,95]:")
    print(f"  baseline (all)      {bm:+.2f} [{bl:+.2f},{bh:+.2f}]  n={len(oos)}")
    print(
        f"  gate LOW touch-OFI  {lm:+.2f} [{ll:+.2f},{lh:+.2f}]  n={int(lo.sum())}  (hypothesis: fake sweep -> reclaim holds)"
    )
    print(f"  gate HIGH touch-OFI {hm:+.2f} [{hl:+.2f},{hh:+.2f}]  n={int(hi.sum())}")
    lift = lm - bm
    verdict = (
        f"LOW-OFI gate lifts reclaim by {lift:+.2f}R and its CI clears the baseline -> promising, VERIFY adversarially."
        if (ll > 0 and lm > bm)
        else "NULL/inconclusive: no OFI gate clears the baseline with a CI above zero (consistent with the feature-ceiling prior)."
    )
    print(f"\nVERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
