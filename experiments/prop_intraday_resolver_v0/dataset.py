"""Phase 2a/2b -- canonical multi-head resolver dataset (builder + audit).

Produces the labeled event frame the multi-head resolver will train on, while
PRESERVING the frozen Phase-1 judge: the resolved subset (y_chop_or_timeout==0)
is byte-identical to the canonical trading-day frame, because cooldown advances
ONLY on resolved touches (exactly as Phase 1) -- chop/timeout rows are purely
additive. No model training here (Phase 2c+). Output goes to out/ (gitignored).

Builds nothing new from scratch: reuses events.load_day / iter_candidates,
features.build_features, and labels.label_event_multihead.
"""

from __future__ import annotations

import _paths  # noqa: F401
import datetime as _dt
from pathlib import Path

import numpy as np
import pandas as pd

import events
import features
import labels
import zone_events as ze

OUT = Path(__file__).resolve().parent / "out"

LABEL_COLS = [
    "y_break",
    "y_hold",
    "y_chop_or_timeout",
    "y_target_before_stop",
    "realized_R",
    "mae_R",
    "mfe_R",
    "time_to_resolution_sec",
    "y_tail_1R",
    "y_tail_2R",
]
FEATURE_COLS = [
    "ofi_signed",
    "qimb_signed",
    "svol_signed",
    "nq_ofi",
    "rty_ofi",
    "ym_ofi",
]


def _process_day_multihead(ctx, pdh: float, pdl: float) -> list[dict]:
    """One day's multi-head rows. Cooldown advances ONLY on resolved touches, so
    the resolved subset reproduces Phase 1; chop/timeout rows are kept (not
    dropped) as the chop class."""
    rows: list[dict] = []
    last_t = {"PDH": None, "PDL": None}
    for i0, t0, role, L, dr in events.iter_candidates(ctx, pdh, pdl):
        lt = last_t[role]
        if lt is not None and (t0 - lt) < ze.COOLDOWN:
            continue
        lab = labels.label_event_multihead(ctx, t0, L, dr)
        if lab is None:
            continue  # unlabelable (no post-decision data); NOT a chop, just degenerate
        feats = features.build_features(ctx, i0, t0, dr)
        if lab["branch_resolved"]:
            last_t[role] = (
                t0  # cooldown clock matches Phase 1 -> resolved subset preserved
            )
        rows.append({"ts": t0, "level": role, "dir": dr, **feats, **lab})
    return rows


def build(
    reader="trading_day", days_limit=None, write=True, out_name=None
) -> pd.DataFrame:
    """Build the canonical multi-head dataset (ES, PDH/PDL). reader defaults to the
    canonical trading-day window. days_limit evenly samples N days for a fast smoke."""
    if out_name is None:
        out_name = f"dataset_ES_{reader}.parquet"
    levels = events.precompute_levels()
    days = events.available_days()
    if days_limit and days_limit < len(days):
        idx = np.linspace(0, len(days) - 1, days_limit).round().astype(int)
        days = [days[i] for i in sorted(set(idx.tolist()))]

    rows: list[dict] = []
    for k, day in enumerate(days):
        if reader == "trading_day" and _dt.date.fromisoformat(day).weekday() >= 5:
            continue
        lv = levels.get(_dt.date.fromisoformat(day))
        if not lv:
            continue
        ctx = events.load_day(ze.SYM, day, reader=reader)
        if ctx is None:
            continue
        rows.extend(_process_day_multihead(ctx, lv["pdh"], lv["pdl"]))
        if (k + 1) % 20 == 0:
            print(f"  ..{k + 1}/{len(days)} days, {len(rows)} rows")

    df = pd.DataFrame(rows).set_index("ts").sort_index()
    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        df.to_parquet(OUT / out_name)
    return df


def audit(df: pd.DataFrame) -> dict:
    """Print + return the Phase-2b label audit: balance, nulls, ambiguity, and
    distributions by session hour / level side / OFI tercile (signal preservation)."""
    from zoneinfo import ZoneInfo

    et = ZoneInfo("America/New_York")
    n = len(df)
    resolved = df[df["y_chop_or_timeout"] == 0]
    print(f"\n=== LABEL AUDIT (n={n}) ===")
    print(
        f"branch:  break={df['y_break'].mean():.3f}  hold={df['y_hold'].mean():.3f}  "
        f"chop/timeout={df['y_chop_or_timeout'].mean():.3f}  (resolved n={len(resolved)})"
    )
    print(f"y_target_before_stop rate: {df['y_target_before_stop'].mean():.3f}")
    print(
        f"tail rates:  >1R={df['y_tail_1R'].mean():.3f}   >2R={df['y_tail_2R'].mean():.3f}"
    )
    print(
        f"realized_R: mean={df['realized_R'].mean():+.3f}  "
        f"[p5={df['realized_R'].quantile(.05):+.2f}, p50={df['realized_R'].median():+.2f}, "
        f"p95={df['realized_R'].quantile(.95):+.2f}]"
    )
    print(
        f"mae_R: mean={df['mae_R'].mean():.3f} p95={df['mae_R'].quantile(.95):.2f}   "
        f"mfe_R: mean={df['mfe_R'].mean():.3f} p95={df['mfe_R'].quantile(.95):.2f}"
    )
    print(
        f"time_to_resolution_sec: median={df['time_to_resolution_sec'].median():.0f}  "
        f"mean={df['time_to_resolution_sec'].mean():.0f}"
    )

    nulls = {c: int(df[c].isna().sum()) for c in LABEL_COLS if df[c].isna().any()}
    print(f"null label cells: {nulls or 'none'}")
    print(
        f"same-row target+stop ambiguity: {int(df['ambiguous'].sum())} (expected 0 on tick mid)"
    )

    et_hour = pd.to_datetime(df.index, utc=True).tz_convert(et).hour
    print("\nby ET hour (count):")
    print(pd.Series(et_hour).value_counts().sort_index().to_string())
    print("\nby level side:")
    print(df["level"].value_counts().to_string())

    # Signal preservation: the established OFI ordering (Phase 1) is BREAK-RATE on
    # the RESOLVED subset (the judge's frame) -- that is the gated check. realized_R
    # is the naive +-8tick/30min trade economics, reported as a finding only: it is
    # ~flat across terciles, which is expected and is the motivation for Phase 2e
    # (turning the break edge into a real trade policy), NOT a label defect.
    print(
        "\nOFI tercile -> signal preservation (RESOLVED subset; break-rate is the judge's ordering):"
    )
    q = pd.qcut(
        resolved["ofi_signed"], 3, labels=["low", "mid", "high"], duplicates="drop"
    )
    tab = (
        resolved.assign(_q=q)
        .groupby("_q", observed=True)
        .agg(
            n=("y_break", "size"),
            break_rate=("y_break", "mean"),
            mean_realized_R=("realized_R", "mean"),
            tbs_rate=("y_target_before_stop", "mean"),
        )
    )
    print(tab.round(3).to_string())
    br = tab["break_rate"].to_numpy()
    monotone = bool(len(br) == 3 and np.all(np.diff(br) > 0))
    rr = tab["mean_realized_R"].to_numpy()
    rr_monotone = bool(len(rr) == 3 and np.all(np.diff(rr) > 0))
    print(f"break-rate monotone increasing across OFI terciles (resolved): {monotone}")
    print(
        f"  (info) realized_R monotone: {rr_monotone} -- naive +-8tick/30min economics; "
        "~flat is expected, the Phase-2e question"
    )
    return {
        "n": n,
        "n_resolved": int(len(resolved)),
        "nulls": nulls,
        "ambiguous": int(df["ambiguous"].sum()),
        "tercile_monotone": monotone,
        "realized_R_monotone": rr_monotone,
    }
