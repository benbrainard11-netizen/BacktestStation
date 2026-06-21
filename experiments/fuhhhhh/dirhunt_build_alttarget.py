"""ANGLE 2 — alternative CAUSAL direction targets for NQ intraday.

The shipped dataset_ndx.parquet uses ONE direction target: a +-0.10*ATR / 15min
move-race (up-move vs down-move vs chop). That tight symmetric race may be a poor
*direction* target. Here we build a battery of ALTERNATIVE causal direction labels at
the SAME (date, ms) decision points, anchored to the existing dataset rows so the
geo_/struct_/opt_/mbp_ features come along for free. Every label uses ONLY NQ 1m bars
with et in (t, t+H] for the forward window; the decision-time features are unchanged
and already causal. Net-cost R for a long & short bracket is carried per label so the
tradeable eval is honest (rule 3).

Targets built (each y in {0=down,1=up}, plus a tradeable r_long/r_short where bracketed):
  fret_<H>   : SIGN of forward close-to-close return over H minutes (5/30/60/120).
               y=1 if ret>0 else 0 (exactly-flat rows dropped). r_long/r_short are the
               net-cost realized R of simply holding H minutes (R = ret/ref - cost),
               ref = one tick? no -- ref is a fixed risk unit = 0.25*ATR (so R units are
               comparable to the shipped dataset). Tradeable rule = "hold H min in the
               model's predicted direction".
  exthold_<H>: Mira "extreme-hold-move" — over (t,t+H], does price make an
               EXTREME excursion of >= 8 ticks (2 pts) in ONE direction that is NOT
               rebroken back through entry by the end of the window? Up-hold => y=1,
               down-hold => y=0. Bracket: target = entry +- 8t HOLD as a take, stop =
               adverse 0.25*ATR; honest first-touch race. Ambiguous (both sides hold) ->
               dropped. This is a DIRECTIONAL persistence target, not a tight race.
  cont_<H>   : continuation-vs-reversal of the PRE-MOVE. Sign of the last-15min return
               BEFORE t (causal) defines the prevailing direction d. y=1 if the forward
               H-min return continues d (same sign), 0 if it reverses. (Trained only on
               rows with a non-trivial pre-move.) This re-frames "direction" as "does the
               current leg persist" — different signal than naked up/down.

Causality (rule 1): forward window strictly et in (t, t+H], entry = first NQ open at
et >= t; assert_no_lookahead on the feature/decision boundary. HOLDOUT sealed: we anchor
to dataset_ndx rows whose date <= DEV_END, so no date >= 2026-04-01 is ever touched.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\dirhunt_build_alttarget.py
Output: out/dirhunt_alttarget.parquet  (NEVER overwrites dataset_ndx / *_features_ndx)
"""
from __future__ import annotations

import json
import sys
from datetime import date as Date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D
import objectives_labels as OL
from build_events import SESSION_END_MS
from build_events_ndx import sym_rth, load_walls_ndx, ndx_nq_basis

OUT = Path(__file__).resolve().parent / "out"
HOLD_TICKS = 8           # Mira extreme = 8 ticks = 2.0 NQ pts
HORIZONS = (5, 30, 60, 120)
PRE_MIN = 15             # pre-move lookback for continuation target
R_REF_ATR = 0.25         # risk unit for fret R, so R units ~ shipped dataset


def fret_label(fwd: pd.DataFrame, entry: float, ref_pts: float) -> tuple[int | None, float, float]:
    """Sign of forward close-to-close return; net-cost R of a hold-H-min trade.

    ref_pts = the risk unit (0.25*ATR). r_long = (close_end-entry)/ref - cost/ref;
    r_short = -(close_end-entry)/ref - cost/ref. y=1 up, 0 down, None if flat.
    """
    if fwd.empty:
        return None, np.nan, np.nan
    close_end = float(fwd["close"].iloc[-1])
    ret = close_end - entry
    if ret == 0.0:
        return None, np.nan, np.nan
    cost = C.COST_PTS_NQ
    r_long = ret / ref_pts - cost / ref_pts
    r_short = -ret / ref_pts - cost / ref_pts
    return (1 if ret > 0 else 0), r_long, r_short


def exthold_label(fwd: pd.DataFrame, entry: float, hold_pts: float, stop_pts: float
                  ) -> tuple[int | None, float, float]:
    """Extreme-hold: price reaches entry+-hold_pts and CLOSES the window beyond entry on
    that side (not rebroken back through entry). Honest first-touch bracket race:
      up-hold  => target = entry+hold_pts, stop = entry-stop_pts  (long bracket)
      down-hold=> target = entry-hold_pts, stop = entry+stop_pts  (short bracket)
    We resolve BOTH a long and short bracket and require an unambiguous winner:
      y=1 if long reaches target & short does not; y=0 vice versa; None if both/neither.
    r_long/r_short = honest net-cost realized R of those brackets.
    """
    if fwd.empty:
        return None, np.nan, np.nan
    up, dn_for_long = entry + hold_pts, entry - stop_pts
    yl, ce_l, _ = OL.race_label(fwd, up, dn_for_long)          # long: tgt up, stop dn
    up_for_short, dn = entry + stop_pts, entry - hold_pts
    ys, ce_s, _ = OL.race_label(fwd, up_for_short, dn)         # short: stop up, tgt dn
    long_win = (yl == 1)
    short_win = (ys == 0)
    rl, _ = OL.realized_r(yl if yl is not None else 2, entry, up, dn_for_long, ce_l, C.COST_PTS_NQ)
    _, rs = OL.realized_r(ys if ys is not None else 2, entry, up_for_short, dn, ce_s, C.COST_PTS_NQ)
    if long_win and not short_win:
        return 1, rl, rs
    if short_win and not long_win:
        return 0, rl, rs
    return None, rl, rs                                        # both or neither held -> drop


def build():
    # Anchor to the shipped decision points (gives us features + holdout safety for free)
    base = pd.read_parquet(OUT / "dataset_ndx.parquet")
    assert base["date"].max() <= C.DEV_END, "holdout leak in anchor"
    walls = load_walls_ndx()
    all_days = sorted(walls)

    atr_tr = D.AtrTracker()
    atr_by_day: dict[str, float] = {}
    # Replicate the dataset's ATR(14) (days < D) so ref/stop units match the shipped build
    for day in all_days:
        if day.isoformat() > C.DEV_END:
            break
        nq_today = sym_rth(C.BARS_1M_NQ, day)
        if nq_today is None:
            continue
        a = atr_tr.atr()
        if a is not None:
            atr_by_day[day.isoformat()] = a
        atr_tr.push_day(nq_today)

    rows = []
    for day_iso, g in base.groupby("date"):
        day = Date.fromisoformat(day_iso)
        nq = sym_rth(C.BARS_1M_NQ, day)
        if nq is None:
            continue
        atr = atr_by_day.get(day_iso)
        if atr is None:
            continue
        nq = nq.sort_values("et").reset_index(drop=True)
        et = nq["et"]
        for ms in g["ms"].to_numpy():
            ms = int(ms)
            t = D.et_ts(day, ms)
            # entry = first NQ open at et >= t (the decision bar's open), causal
            fut = nq[et >= t]
            if fut.empty:
                continue
            entry = float(fut["open"].iloc[0])
            # build-time lookahead assert: nothing in the feature/decision boundary peeks
            pre_closed = nq[et <= t - pd.Timedelta(minutes=1)]
            if len(pre_closed):
                C.assert_no_lookahead(pre_closed["et"].iloc[-1] + pd.Timedelta(minutes=1), t, "dirhunt")

            rec = {"date": day_iso, "ms": ms}
            # ---- pre-move direction (causal) for continuation target ----
            pre_win = nq[(et <= t) & (et > t - pd.Timedelta(minutes=PRE_MIN))]
            pre_d = 0
            if len(pre_win) >= 3:
                pre_ret = float(pre_win["close"].iloc[-1]) - float(pre_win["open"].iloc[0])
                pre_d = 1 if pre_ret > 0 else (-1 if pre_ret < 0 else 0)
            rec["pre_d"] = pre_d

            for H in HORIZONS:
                end = min(ms + H * 60_000, SESSION_END_MS)
                fwd = nq[(et >= t) & (et < D.et_ts(day, end))]
                if len(fwd) < 2:
                    continue
                # forward-return-sign target
                y, rl, rs = fret_label(fwd, entry, R_REF_ATR * atr)
                if y is not None:
                    rec[f"fret_{H}"] = y
                    rec[f"fret_{H}_rl"] = rl
                    rec[f"fret_{H}_rs"] = rs
                    # continuation: forward ret sign vs pre-move sign
                    if pre_d != 0:
                        fwd_d = 1 if y == 1 else -1
                        rec[f"cont_{H}"] = 1 if fwd_d == pre_d else 0
                # extreme-hold target
                yh, hrl, hrs = exthold_label(fwd, entry, HOLD_TICKS * C.TICK, R_REF_ATR * atr)
                if yh is not None:
                    rec[f"exthold_{H}"] = yh
                    rec[f"exthold_{H}_rl"] = hrl
                    rec[f"exthold_{H}_rs"] = hrs
            rows.append(rec)

    df = pd.DataFrame(rows)
    assert df["date"].max() <= C.DEV_END, "holdout leak"
    OUT.mkdir(exist_ok=True)
    out = OUT / "dirhunt_alttarget.parquet"
    df.to_parquet(out)
    summary = {"rows": len(df), "days": int(df["date"].nunique()),
               "date_min": df["date"].min(), "date_max": df["date"].max()}
    for col in df.columns:
        if col.startswith(("fret_", "exthold_", "cont_")) and not col.endswith(("_rl", "_rs")):
            vc = df[col].dropna()
            summary[col] = {"n": int(len(vc)), "up_rate": round(float(vc.mean()), 4)}
    print(json.dumps(summary, indent=2))
    print(f"\n-> {out}")


if __name__ == "__main__":
    build()
