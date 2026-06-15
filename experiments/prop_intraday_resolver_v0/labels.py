"""Layer 2b -- triple-barrier labeler (binary + multi-head).

Both labelers measure outcomes STRICTLY AFTER the feature window (jo = first row
at/after t0+W_OFI); features use [i0, jo), labels use [jo, k1). No overlap.

label_event           -- Phase 1 binary hold(0)/break(1)/None, reuses ze.label_touch.
label_event_multihead -- Phase 2 full head set. TWO coordinate frames, both honest:

  branch (level-relative, == the frozen Phase-1 judge):
    ze.label_touch first-hit of L+B (break) vs L-R (hold) over [jo,k1).
    -> y_break / y_hold / y_chop_or_timeout

  trade economics (entry-relative, break-direction frame, 1R = B = 8 ticks):
    entry = mid at the decision boundary (mid[jo]); target = entry+dr*B,
    stop = entry-dr*R (symmetric); first-hit over [jo,k1).
    -> y_target_before_stop, realized_R, mae_R, mfe_R, time_to_resolution_sec,
       y_tail_1R, y_tail_2R

The two frames differ by up to the touch tolerance (entry is within ~EPS of L),
so an event can be branch=chop yet have the entry-relative trade resolve, or
vice versa -- they answer different questions (did the LEVEL break vs did a
TRADE entered at the decision hit target/stop). Same-row target+stop is
impossible on a scalar mid, so label-stage ambiguity is 0; honest fill ambiguity
(CLAUDE.md rule 8) is a Phase-4 tick-fill concern, not a label concern.
"""

from __future__ import annotations

import _paths  # noqa: F401

import numpy as np

import zone_events as ze


def label_event(ctx, t0, level_price: float, dr: int):
    """Binary hold/break for one touch, or None on timeout. Outcome AFTER the window."""
    jo = int(ctx.tsi.searchsorted(t0 + ze.W_OFI, side="right"))
    k1 = int(ctx.tsi.searchsorted(t0 + ze.HORIZON, side="right"))
    return ze.label_touch(ctx.mid, jo, k1, level_price, dr)


def label_event_multihead(ctx, t0, level_price: float, dr: int):
    """Full multi-head label dict for one touch, or None if unlabelable.

    None means no post-decision data (degenerate end-of-window touch) -- distinct
    from chop/timeout (which IS a labeled class). See module docstring for frames.
    """
    tsi, mid = ctx.tsi, ctx.mid
    decision = t0 + ze.W_OFI
    jo = int(tsi.searchsorted(decision, side="right"))
    k1 = int(tsi.searchsorted(t0 + ze.HORIZON, side="right"))
    if jo >= len(mid) or jo >= k1:
        return None  # no rows strictly after the decision boundary -> unlabelable

    # --- branch (level-relative): matches the frozen Phase-1 judge exactly ---
    branch = ze.label_touch(mid, jo, k1, level_price, dr)  # 1 break, 0 hold, None chop

    # --- trade economics (entry-relative, break-direction frame) ---
    seg = mid[jo:k1]
    entry = float(mid[jo])
    r_unit = ze.B  # 8 ticks in price (== ze.R; symmetric box)
    fav = dr * (seg - entry)  # favorable excursion (price) in the break direction
    mfe_r = float(fav.max()) / r_unit
    mae_r = float((-fav).max()) / r_unit  # >= 0 (fav[0] == 0)

    hit_t = np.where(fav >= ze.B)[0]
    hit_s = np.where(fav <= -ze.R)[0]
    ft = int(hit_t[0]) if len(hit_t) else None
    fs = int(hit_s[0]) if len(hit_s) else None
    ambiguous = int(
        ft is not None and fs is not None and ft == fs
    )  # impossible on scalar mid
    if ft is not None and (fs is None or ft < fs):
        tbs, res_idx, realized_r = 1, ft, 1.0
    elif fs is not None:
        tbs, res_idx, realized_r = (
            0,
            fs,
            -1.0,
        )  # stop first (ties -> stop, conservative)
    else:
        tbs, res_idx, realized_r = (
            0,
            len(seg) - 1,
            float(fav[-1]) / r_unit,
        )  # timeout: final mark

    ttr_sec = float((tsi[jo + res_idx] - tsi[jo]).total_seconds())

    return {
        "y_break": int(branch == 1),
        "y_hold": int(branch == 0),
        "y_chop_or_timeout": int(branch is None),
        "y_target_before_stop": int(tbs),
        "realized_R": realized_r,
        "mae_R": mae_r,
        "mfe_R": mfe_r,
        "time_to_resolution_sec": ttr_sec,
        "y_tail_1R": int(mae_r > 1.0),
        "y_tail_2R": int(mae_r > 2.0),
        "branch_resolved": int(branch is not None),
        "ambiguous": ambiguous,
        # boundary stamps for the lookahead audit (verify_phase2_labels.py):
        "feature_end_ts": tsi[jo - 1] if jo > 0 else tsi[0],
        "label_start_ts": tsi[jo],
        "decision_ts": decision,
    }
