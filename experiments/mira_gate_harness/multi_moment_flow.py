"""multi_moment_flow.py -- MULTI-MOMENT order-flow selection (Ben's idea).

WHY: the edge in this campaign is CONSISTENTLY order flow. Bar-based / structure-only signals
top out at breakeven (sweep-reclaim ~ -0.05R every year/market); the things that have ADDED value
were all flow reads -- legal pre-trigger DRIFT (+0.086, flow_at_scale) and the in-zone RETRACE
refill (zone flow ~+0.12..+0.155, flow_at_zone). Enriching the order-flow read is the priority.

flow_at_zone read the book at ONE beat of the sequence: the RETRACE into the OB/FVG zone. But a
sweep->reclaim is a SEQUENCE with several order-book moments. This module reads the MBO book at
THREE beats and asks WHICH moment(s) separate winners -- does sweep-aggression or formation flow
ADD to the validated retrace zone-flow?

THE THREE FLOW MOMENTS (each emits the SAME 6-feature set; all strictly < decision, asserted):
  1. SWEEP   (sw_*): flow in [touch_ts, touch_ts + 60s) -- the immediate thrust that TOOK the level.
     (No explicit sweep_extreme column exists in the universe, so we use the +60s thrust window per
     spec.) TIME-bounded only (no zone): captures "was the run INTO the level aggressive/convincing"
     vs a slow drift. The level price is the spatial anchor here, not a zone.
  2. FORMATION (fm_*): flow during the 5m candle that FORMED the OB/FVG zone -- the candle's
     [open_ts, close_ts). PRICE-bounded to the zone bounds. Only defined when a zone formed. Captures
     the order book WHEN the reversal STRUCTURE was built.
  3. RETRACE  (rt_*): the in-zone flow on retrace -- imported VERBATIM from flow_at_zone.zone_flow_feats
     (the validated refill signal). Not reinvented.

Direction signed throughout: dir_sign = +1 long (side=='low', a low level reclaimed) / -1 short.
Features prefixed sw_/fm_/rt_. A few natural INTERACTIONS are emitted (e.g. sweep aggression *
low retrace-refill, sweep aggression * formation delta).

LEGALITY (the #1 correctness rule here): every MBO event in every window has ts_event < decision_us
(asserted PER window). Zone/formation candles are CLOSED <= decision (asserted in zone detection).
The sweep window hi-bound is min(touch+60s, decision). Predicate-pushdown MBO read
[min(touch)-margin, max(decision)). NO post-decision data anywhere.

UNIVERSE: identical to flow_at_zone -- runs/legal_bars_full.parquet, status=='entered', |R|<=5,
the registered combo subset (depth_tk>8 AND wait_s>=300), year(decision)==2026, 4 index roots,
trading_day has MBO coverage. (Reuses flow_at_zone.load_universe verbatim.)

ANALYSIS: DESIGN = Jan+Feb+Mar 2026. VALIDATION = Apr+May+Jun computed+stored but NOT analyzed.
Per feature (ALL three moments): meanR(trail_2R) + win by tercile and by sign, among ZONE-FORMED
design trades (the analyzable population -- formation/retrace need a zone; sweep is defined for all
but reported on the same zone-formed subset so the three moments are comparable on one population).
Reports the best feature of EACH moment, plus the PDH/PDL (previous_rth) subset separately (it was
the descriptively-best level family). Frozen-rule proposal for (a) the single strongest feature and
(b) the best 2-moment combo. One-shot evaluation on validation later, no iteration after the look.

Crash-safe: features cached per (symbol, trading_day) to runs/multi_moment_features.parquet
(tmp + atomic replace per day; resumes by skipping cached symbol-days).

Run:
    backend/.venv/Scripts/python.exe experiments/mira_gate_harness/multi_moment_flow.py
Smoke (5 Jan ES days):   ... multi_moment_flow.py --smoke
Analyze cached only:     ... multi_moment_flow.py --analyze-only
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(HERE))  # import flow_at_zone as a module

# REUSE everything from flow_at_zone: universe gate, MBO read+legality, zone detection, retrace
# gate, the validated in-zone (retrace) feature fn, and shared constants. Do NOT re-implement.
import flow_at_zone as fz  # noqa: E402

RUNS = fz.RUNS
CACHE = RUNS / "multi_moment_features.parquet"

SYMBOLS = fz.SYMBOLS
TICK = fz.TICK
ONE_NS = fz.ONE_NS
ZONE_TOL_TICKS = fz.ZONE_TOL_TICKS
NEAR_TICKS = 4  # for the sweep window the "in-zone" anchor is the level +/- NEAR_TICKS
DESIGN_MONTHS = fz.DESIGN_MONTHS
VALID_MONTHS = fz.VALID_MONTHS

SWEEP_THRUST_S = 60  # [touch, touch+60s): the immediate sweep thrust (no sweep_extreme col)
ZONE_TF = "5m"  # 5m won bar_confirmations; formation candle is read on 5m
TF_MIN = fz.TF_MIN

PDH_PDL_FAMILY = "previous_rth"  # the descriptively-best level family (PDH/PDL)

# the 6 features each moment emits (same shape as flow_at_zone's in-zone set, un-prefixed)
FLOW_FEATURES = [
    "vol",
    "delta_dir",
    "aggr_imb_dir",
    "absorption",
    "add_refill_dir",
    "n_events",
]
MOMENTS = ["sw", "fm", "rt"]  # sweep / formation / retrace

# columns carried through from the universe row
KEEP = [
    "symbol",
    "session_date",
    "level_family",
    "level_type",
    "side",
    "level_price",
    "touch_ts_utc",
    "decision_ts_utc",
    "entry_ts_utc",
    "depth_tk",
    "wait_s",
    "trail_2R",
    "fixed_3R",
]


# ======================================================================================
# GENERIC in-window flow features. Same 6-feature set as flow_at_zone's zone_flow_feats, but
# parameterised by an arbitrary [lo_us, hi_us) window AND an optional price band [px_lo, px_hi].
#   * RETRACE moment delegates to fz.zone_flow_feats VERBATIM (the validated signal) -- NOT this fn.
#   * SWEEP moment: time window [touch, touch+60s), price band = level +/- NEAR_TICKS (the thrust at
#     the level; a band, not a formed zone -- captures the run INTO the level).
#   * FORMATION moment: time window [open_ts, close_ts) of the formation 5m candle, price band = the
#     zone bounds (the book while the structure was being built).
# Definitions mirror flow_at_scale / flow_at_zone exactly so signs are consistent across studies:
#   T & bid => buy-tagged, T & ask => sell-tagged; *_dir signed by dir_sign; absorption = vol /
#   (1 + ticks traversed in band); add_refill_dir = add-size / cancel-size on the DEFENDING side
#   (bid for longs, ask for shorts) within the band.
# LEGALITY: hi_us <= decision_us is the caller's contract; this fn asserts the last in-window event
# is strictly < decision_us.
# ======================================================================================
def window_flow_feats(
    day: dict,
    lo_us: int,
    hi_us: int,
    decision_us: int,
    px_lo: float,
    px_hi: float,
    dir_sign: int,
    tick: float,
) -> dict:
    ts = day["ts"]
    i0 = np.searchsorted(ts, lo_us, "left")
    i1 = np.searchsorted(ts, hi_us, "left")
    if i1 > i0:
        assert ts[i1 - 1] < decision_us, "event at/after decision leaked into a flow window"
    sl = slice(i0, i1)
    px, sz = day["px"][sl], day["sz"][sl]
    is_T, is_A, is_C = day["is_T"][sl], day["is_A"][sl], day["is_C"][sl]
    bid, ask = day["bid"][sl], day["ask"][sl]

    tol = ZONE_TOL_TICKS * tick + 1e-9
    in_band = (px >= px_lo - tol) & (px <= px_hi + tol)
    n_events = int(in_band.sum())
    if n_events == 0:
        return {
            "vol": 0.0,
            "delta_dir": 0.0,
            "aggr_imb_dir": np.nan,
            "absorption": np.nan,
            "add_refill_dir": np.nan,
            "n_events": 0,
        }

    bt = is_T & in_band
    buy = sz[bt & bid].sum()
    sell = sz[bt & ask].sum()
    vol = float(buy + sell)
    delta_dir = float(dir_sign * (buy - sell))
    aggr_imb_dir = dir_sign * fz._imb(buy, sell)

    bpx = px[in_band]
    span_ticks = (np.nanmax(bpx) - np.nanmin(bpx)) / tick if len(bpx) else 0.0
    absorption = float(vol / (1.0 + span_ticks))

    defend = bid if dir_sign == 1 else ask
    add_d = sz[is_A & defend & in_band].sum()
    can_d = sz[is_C & defend & in_band].sum()
    add_refill_dir = float(add_d / can_d) if can_d > 0 else np.nan

    return {
        "vol": vol,
        "delta_dir": delta_dir,
        "aggr_imb_dir": aggr_imb_dir,
        "absorption": absorption,
        "add_refill_dir": add_refill_dir,
        "n_events": n_events,
    }


def _nan_feats() -> dict:
    return {
        "vol": np.nan,
        "delta_dir": np.nan,
        "aggr_imb_dir": np.nan,
        "absorption": np.nan,
        "add_refill_dir": np.nan,
        "n_events": 0,
    }


# ======================================================================================
# Detect the 5m zone AND return the formation candle's [open_ns, close_ns). flow_at_zone's
# _detect_zone_tf returns the zone bounds + the formation candle's CLOSE ns; we recover the OPEN ns
# as close_ns - TF duration (the candle index is its open). We re-run detection here (rather than
# threading another return value through fz) so the reused fz code stays untouched.
# ======================================================================================
def detect_zone_with_formation(
    tf_frames: dict, row: pd.Series, touch_ns: int, decision_ns: int, tick: float
):
    """Returns (z_lo, z_hi, kind, formed_close_ns, formed_open_ns, retraced) or None."""
    tf_b = tf_frames.get(ZONE_TF)
    bars1m = tf_frames.get("1m")
    if tf_b is None or not len(tf_b):
        return None
    close_ns = tf_b.index.asi8 + TF_MIN[ZONE_TF] * 60 * ONE_NS
    sel = (close_ns >= touch_ns - 6 * 3600 * ONE_NS) & (close_ns <= decision_ns)
    sub = tf_b.iloc[sel]
    zone = fz._detect_zone_tf(
        sub,
        row["side"],
        float(row["level_price"]),
        touch_ns,
        decision_ns,
        ZONE_TF,
        tick,
    )
    if zone is None:
        return None
    z_lo, z_hi, kind, formed_close_ns = zone
    formed_open_ns = formed_close_ns - TF_MIN[ZONE_TF] * 60 * ONE_NS  # candle index = open
    retraced = fz._retraced(bars1m, z_lo, z_hi, formed_close_ns, decision_ns, tick)
    return (z_lo, z_hi, kind, formed_close_ns, formed_open_ns, bool(retraced))


# ======================================================================================
# per-trade: read the book at all three moments.
# ======================================================================================
def trade_features(day: dict, tf_frames: dict, row: pd.Series) -> dict:
    tick = TICK[row["symbol"]]
    dir_sign = 1 if row["side"] == "low" else -1
    touch_ns = int(row["touch_ts_utc"].value)
    decision_ns = int(row["decision_ts_utc"].value)
    touch_us = touch_ns // 1_000
    decision_us = decision_ns // 1_000
    level_px = float(row["level_price"])

    out = {k: row[k] for k in KEEP}
    out["trading_day"] = row["trading_day"]
    out["dir_sign"] = dir_sign
    out["win"] = bool(row["trail_2R"] > 0)

    # ---- detect 5m zone + formation candle window + retrace flag ----
    zinfo = detect_zone_with_formation(tf_frames, row, touch_ns, decision_ns, tick)
    has_zone = zinfo is not None and zinfo[5]  # retraced
    out["zone_5m_has"] = 1 if has_zone else 0
    if zinfo is not None:
        z_lo, z_hi, kind, formed_close_ns, formed_open_ns, _ = zinfo
        out["zone_5m_kind"] = kind
        out["zone_5m_lo"] = z_lo
        out["zone_5m_hi"] = z_hi
    else:
        z_lo = z_hi = formed_close_ns = formed_open_ns = None
        out["zone_5m_kind"] = None
        out["zone_5m_lo"] = np.nan
        out["zone_5m_hi"] = np.nan

    # ============================ MOMENT 1: SWEEP (sw_*) ============================
    # [touch, min(touch+60s, decision)); price band = level +/- NEAR_TICKS. Defined for ALL trades
    # (does not require a zone). hi-bound clamps at decision for legality.
    sw_hi_us = min(touch_us + SWEEP_THRUST_S * 1_000_000, decision_us)
    band = NEAR_TICKS * tick
    if sw_hi_us > touch_us:
        sw = window_flow_feats(
            day,
            touch_us,
            sw_hi_us,
            decision_us,
            level_px - band,
            level_px + band,
            dir_sign,
            tick,
        )
    else:
        sw = _nan_feats()  # touch == decision (degenerate); no legal sweep window
    for f in FLOW_FEATURES:
        out[f"sw_{f}"] = sw[f]

    # ============================ MOMENT 2: FORMATION (fm_*) ============================
    # flow during the 5m candle that FORMED the zone: [open_ns, close_ns); price band = zone bounds.
    # Only when a (retraced) zone formed. close_ns <= decision (zone legality) so the window is legal.
    if has_zone:
        fm_lo_us = formed_open_ns // 1_000
        fm_hi_us = formed_close_ns // 1_000
        # defensive legality clamp (zone detection already guarantees close_ns <= decision_ns)
        fm_hi_us = min(fm_hi_us, decision_us)
        if fm_hi_us > fm_lo_us:
            fm = window_flow_feats(
                day, fm_lo_us, fm_hi_us, decision_us, z_lo, z_hi, dir_sign, tick
            )
        else:
            fm = _nan_feats()
    else:
        fm = _nan_feats()
    for f in FLOW_FEATURES:
        out[f"fm_{f}"] = fm[f]

    # ============================ MOMENT 3: RETRACE (rt_*) ============================
    # the validated in-zone refill read -- delegate to flow_at_zone.zone_flow_feats VERBATIM.
    # It returns the zone_* feature names; remap to the shared FLOW_FEATURES schema (prefixed rt_).
    if has_zone:
        rt_raw = fz.zone_flow_feats(
            day, touch_us, decision_us, z_lo, z_hi, dir_sign, tick
        )
        rt = {
            "vol": rt_raw["zone_vol"],
            "delta_dir": rt_raw["zone_delta_dir"],
            "aggr_imb_dir": rt_raw["zone_aggr_imb_dir"],
            "absorption": rt_raw["zone_absorption"],
            "add_refill_dir": rt_raw["zone_add_refill_dir"],
            "n_events": rt_raw["zone_n_events"],
        }
        out["rt_revisits"] = rt_raw["zone_revisits"]  # extra (carried, not in the shared 6)
    else:
        rt = _nan_feats()
        out["rt_revisits"] = 0
    for f in FLOW_FEATURES:
        out[f"rt_{f}"] = rt[f]

    # ============================ NATURAL INTERACTIONS ============================
    # sweep aggression INTO the level x weak retrace refill: a convincing run that took the level
    # combined with a thin defense on retrace -> the reclaim is more likely to fail to hold (or, if
    # sign flips, to mark a real exhaustion reversal). We emit the product; analysis reads the sign.
    sw_aggr = out["sw_aggr_imb_dir"]
    rt_refill = out["rt_add_refill_dir"]
    fm_delta = out["fm_delta_dir"]
    out["ix_sweep_aggr_x_retrace_refill"] = (
        sw_aggr * rt_refill
        if np.isfinite(sw_aggr) and np.isfinite(rt_refill)
        else np.nan
    )
    out["ix_sweep_aggr_x_formation_delta"] = (
        sw_aggr * fm_delta
        if np.isfinite(sw_aggr) and np.isfinite(fm_delta)
        else np.nan
    )
    # sweep vol relative to formation vol -- did the thrust dwarf the structure build?
    out["ix_sweep_vol_x_formation_absorption"] = (
        out["sw_vol"] * out["fm_absorption"]
        if np.isfinite(out["sw_vol"]) and np.isfinite(out["fm_absorption"])
        else np.nan
    )
    return out


# ======================================================================================
# build (crash-safe, per symbol-day cache; same pattern as flow_at_zone)
# ======================================================================================
def build_features(uni: pd.DataFrame, force: bool = False) -> pd.DataFrame:
    cached = pd.read_parquet(CACHE) if CACHE.exists() and not force else pd.DataFrame()
    done = (
        set(map(tuple, cached[["symbol", "trading_day"]].drop_duplicates().to_numpy()))
        if len(cached)
        else set()
    )
    groups = uni.groupby(["symbol", "trading_day"], sort=True)
    todo = [k for k in groups.groups if k not in done]
    print(
        f"[build] {len(uni)} trades / {groups.ngroups} symbol-days "
        f"({len(done)} cached, {len(todo)} to compute)"
    )
    skipped = []
    for n, (sym, td) in enumerate(todo, 1):
        g = groups.get_group((sym, td))
        try:
            touch_us = g["touch_ts_utc"].astype("int64") // 1_000
            dec_us = g["decision_ts_utc"].astype("int64") // 1_000
            day = fz.prep_day(
                sym, td, int(touch_us.min() - 5_000_000), int(dec_us.max())
            )
            tf_frames = fz._resample_for_day(sym, td)
        except Exception as e:  # missing/broken day: skip loudly, never fabricate
            print(f"  SKIP {sym} {td}: {type(e).__name__}: {e}")
            skipped.append((sym, td, len(g)))
            continue
        rows = pd.DataFrame(
            [trade_features(day, tf_frames, r) for _, r in g.iterrows()]
        )
        cached = pd.concat([cached, rows], ignore_index=True)
        tmp = CACHE.with_suffix(".tmp.parquet")
        cached.to_parquet(tmp, index=False)
        tmp.replace(CACHE)
        nz = int(rows["zone_5m_has"].sum()) if "zone_5m_has" in rows else 0
        # how many of the zone-formed trades have all three moments populated
        if nz:
            zf = rows[rows["zone_5m_has"] == 1]
            n3 = int(
                ((zf["sw_n_events"] > 0) & (zf["fm_n_events"] > 0) & (zf["rt_n_events"] > 0)).sum()
            )
        else:
            n3 = 0
        print(
            f"  [{n}/{len(todo)}] {sym} {td}: {len(rows)} trades, {nz} zone-formed, "
            f"{n3} have all 3 moments"
        )
    if skipped:
        print(
            f"[build] WARNING: skipped {len(skipped)} symbol-days "
            f"({sum(s[2] for s in skipped)} trades): {skipped}"
        )
    return cached


# ======================================================================================
# ANALYSIS -- DESIGN months only; zone-formed subset (all 3 moments comparable on one population).
# ======================================================================================
def _bucket_table(d: pd.DataFrame, feat: str, label: str, min_n: int = 20) -> float | None:
    """meanR(trail_2R) + win by tercile and by sign; return top-bottom meanR spread."""
    if feat not in d:
        return None
    v = d[[feat, "trail_2R", "win"]].dropna(subset=[feat, "trail_2R"])
    if len(v) < min_n:
        print(f"    {label:<34} n={len(v)} (too few, skipped)")
        return None
    try:
        terc = pd.qcut(v[feat], 3, labels=["T1_lo", "T2", "T3_hi"], duplicates="drop")
    except ValueError:
        print(f"    {label:<34} degenerate distribution, skipped")
        return None
    g = v.groupby(terc).agg(
        meanR=("trail_2R", "mean"), win=("win", "mean"), n=("trail_2R", "count")
    )
    if len(g) < 3:
        print(f"    {label:<34} <3 distinct terciles, skipped")
        return None
    spread = g["meanR"].iloc[-1] - g["meanR"].iloc[0]
    cells = "  ".join(
        f"{i}={r['meanR']:+.3f}/wr{r['win']:.0%}(n={int(r['n'])})"
        for i, r in g.iterrows()
    )
    pos, neg = v[v[feat] > 0], v[v[feat] <= 0]
    sign = (
        f"  >0={pos['trail_2R'].mean():+.3f}/wr{pos['win'].mean():.0%}(n={len(pos)}) "
        f"<=0={neg['trail_2R'].mean():+.3f}/wr{neg['win'].mean():.0%}(n={len(neg)})"
        if len(pos) >= 8 and len(neg) >= 8
        else ""
    )
    print(f"    {label:<34} {cells}  spread={spread:+.3f}{sign}")
    return float(spread)


def _moment_block(z: pd.DataFrame, moment: str, label: str) -> dict:
    print(f"\n  --- {label} moment ({moment}_*) ---")
    ranks = {}
    for f in FLOW_FEATURES:
        col = f"{moment}_{f}"
        s = _bucket_table(z, col, f)
        if s is not None and s != 0:
            ranks[col] = s
    return ranks


def analyze(feats: pd.DataFrame) -> None:
    mo = pd.to_datetime(feats["trading_day"]).dt.month
    yr = pd.to_datetime(feats["trading_day"]).dt.year
    design = feats[(yr == 2026) & mo.isin(DESIGN_MONTHS)].copy()
    valid = feats[(yr == 2026) & mo.isin(VALID_MONTHS)].copy()
    print(
        f"\n{'=' * 100}\nANALYSIS -- DESIGN Jan+Feb+Mar 2026 ({len(design)} trades). "
        f"VALIDATION Apr+May+Jun stored, NOT analyzed ({len(valid)} trades, reserved one-shot)."
    )

    z = design[design["zone_5m_has"] == 1].copy()
    nz = design[design["zone_5m_has"] == 0]
    print(
        f"\nzone-formed (design): {len(z)}/{len(design)} = "
        f"{len(z) / max(len(design), 1):.1%}  kinds={z['zone_5m_kind'].value_counts().to_dict()}"
    )
    print(
        f"  zone-formed meanR={z['trail_2R'].mean():+.3f} win={z['win'].mean():.1%} (n={len(z)}); "
        f"no-zone meanR={nz['trail_2R'].mean():+.3f} win={nz['win'].mean():.1%} (n={len(nz)}); "
        f"lift={z['trail_2R'].mean() - nz['trail_2R'].mean():+.3f}R"
    )
    if len(z) < 20:
        print(
            f"\n[only {len(z)} zone-formed design trades -- too few for multi-moment selection. "
            f"Zone formation is the binding constraint, as expected.]"
        )
        return

    # ---- coverage of each moment on the zone-formed population ----
    print(
        f"\nmoment population coverage among zone-formed design trades (n={len(z)}):"
    )
    for m in MOMENTS:
        nev = (z[f"{m}_n_events"] > 0).sum()
        print(f"    {m}_*: {int(nev)}/{len(z)} have >0 events")

    # ---- THE QUESTION: which moment(s) separate winners? per-moment tercile/sign tables ----
    print(
        f"\n{'-' * 100}\nMULTI-MOMENT SEPARATION (zone-formed design, n={len(z)}) -- "
        f"does sweep-aggression or formation flow ADD to the validated retrace zone-flow?"
    )
    moment_ranks = {
        "sw": _moment_block(z, "sw", "SWEEP (thrust into level)"),
        "fm": _moment_block(z, "fm", "FORMATION (zone-build candle)"),
        "rt": _moment_block(z, "rt", "RETRACE (validated in-zone refill)"),
    }
    print(f"\n  --- INTERACTIONS ---")
    ix_ranks = {}
    for col in [
        "ix_sweep_aggr_x_retrace_refill",
        "ix_sweep_aggr_x_formation_delta",
        "ix_sweep_vol_x_formation_absorption",
    ]:
        s = _bucket_table(z, col, col.replace("ix_", ""))
        if s is not None and s != 0:
            ix_ranks[col] = s

    # ---- best feature of EACH moment ----
    print(f"\n{'-' * 100}\nBEST FEATURE OF EACH MOMENT (|tercile meanR spread|):")
    best_per_moment = {}
    for m, label in [("sw", "SWEEP"), ("fm", "FORMATION"), ("rt", "RETRACE")]:
        r = moment_ranks[m]
        if r:
            feat = max(r, key=lambda k: abs(r[k]))
            best_per_moment[m] = (feat, r[feat])
            print(f"    {label:<10} -> {feat:<22} spread={r[feat]:+.3f}")
        else:
            print(f"    {label:<10} -> (no usable separator)")

    # ---- PDH/PDL (previous_rth) subset, reported SEPARATELY ----
    _pdh_pdl_subset(z)

    # ---- frozen-rule proposals: strongest single feature + best 2-moment combo ----
    _frozen_proposals(z, moment_ranks, ix_ranks, best_per_moment)


def _pdh_pdl_subset(z: pd.DataFrame) -> None:
    print(
        f"\n{'-' * 100}\nPDH/PDL ({PDH_PDL_FAMILY}) SUBSET -- descriptively-best level family, "
        f"reported separately:"
    )
    zp = z[z["level_family"] == PDH_PDL_FAMILY].copy()
    if len(zp) < 12:
        print(
            f"  only {len(zp)} zone-formed {PDH_PDL_FAMILY} design trades -- descriptive only:"
        )
        if len(zp):
            print(
                f"  meanR={zp['trail_2R'].mean():+.3f} win={zp['win'].mean():.1%} (n={len(zp)})"
            )
        return
    print(
        f"  {PDH_PDL_FAMILY} zone-formed baseline: meanR={zp['trail_2R'].mean():+.3f} "
        f"win={zp['win'].mean():.1%} (n={len(zp)})"
    )
    for m in MOMENTS:
        best, bspread = None, 0.0
        for f in FLOW_FEATURES:
            col = f"{m}_{f}"
            s = _bucket_table(zp, col, f"{m}_{f}", min_n=12)
            if s is not None and abs(s) > abs(bspread):
                best, bspread = col, s
        if best:
            print(f"    [{m}] best {PDH_PDL_FAMILY} separator: {best} spread={bspread:+.3f}")


def _frozen_proposals(
    z: pd.DataFrame, moment_ranks: dict, ix_ranks: dict, best_per_moment: dict
) -> None:
    print(
        f"\n{'-' * 100}\nFROZEN-RULE PROPOSALS (DESIGN-only; sign-consistent; |tercile spread|):"
    )
    # pool every feature across moments + interactions, keep sign-consistent ones
    pooled = {}
    for r in (*moment_ranks.values(), ix_ranks):
        pooled.update(r)
    consistent = {}
    for feat, s in pooled.items():
        v = z[[feat, "trail_2R"]].dropna()
        pos, neg = v[v[feat] > 0]["trail_2R"], v[v[feat] <= 0]["trail_2R"]
        if len(pos) < 8 or len(neg) < 8:
            consistent[feat] = s  # always-positive feature (e.g. vol); keep on tercile evidence
            continue
        if np.sign(pos.mean() - neg.mean()) == np.sign(s) != 0:
            consistent[feat] = s
    if not consistent:
        print(
            "  none -- no multi-moment feature shows usable sign-consistent tercile spread among "
            "zone-formed trades (multi-moment selection NO-GO as constructed, or N too small)."
        )
        print(
            "ONE-SHOT PLAN: nothing to freeze. If a rule appears on a future run, freeze it verbatim "
            "and evaluate ONCE on Apr+May+Jun (cached)."
        )
        return

    # (a) strongest SINGLE feature
    feat, s = max(consistent.items(), key=lambda kv: abs(kv[1]))
    q, op, keep = _rule_from(z, feat, s)
    print(
        f"  (a) STRONGEST SINGLE: {feat} (design spread {s:+.3f})\n"
        f"      FROZEN-RULE: among zone-formed, take only if {feat} {op} {q:.4f}\n"
        f"      -> design meanR {keep['trail_2R'].mean():+.3f} win {keep['win'].mean():.1%} "
        f"(n={len(keep)}) vs zone-formed baseline {z['trail_2R'].mean():+.3f} "
        f"win {z['win'].mean():.1%} (n={len(z)})"
    )

    # (b) best 2-MOMENT combo: strongest feature from two DIFFERENT moments, AND-ed.
    moment_best = []
    for m in MOMENTS:
        if m in best_per_moment:
            bf, bs = best_per_moment[m]
            if bf in consistent:
                moment_best.append((m, bf, consistent[bf]))
    moment_best.sort(key=lambda t: -abs(t[2]))
    if len(moment_best) >= 2:
        (m1, f1, s1), (m2, f2, s2) = moment_best[0], moment_best[1]
        q1, op1, _ = _rule_from(z, f1, s1)
        q2, op2, _ = _rule_from(z, f2, s2)
        cond1 = (z[f1] >= q1) if s1 > 0 else (z[f1] <= q1)
        cond2 = (z[f2] >= q2) if s2 > 0 else (z[f2] <= q2)
        keep2 = z[z[f1].notna() & z[f2].notna() & cond1 & cond2]
        print(
            f"  (b) BEST 2-MOMENT COMBO: [{m1}] {f1} {op1} {q1:.4f}  AND  [{m2}] {f2} {op2} {q2:.4f}\n"
            f"      -> design meanR "
            f"{keep2['trail_2R'].mean() if len(keep2) else float('nan'):+.3f} "
            f"win {keep2['win'].mean() if len(keep2) else float('nan'):.1%} (n={len(keep2)}) "
            f"vs zone-formed baseline {z['trail_2R'].mean():+.3f} (n={len(z)})"
        )
    else:
        print(
            "  (b) BEST 2-MOMENT COMBO: <2 moments produced a sign-consistent separator -- "
            "no honest 2-moment combo to freeze."
        )
    print(
        "ONE-SHOT PLAN: freeze (a) and (b) verbatim, evaluate ONCE on Apr+May+Jun zone-formed "
        "(features cached). No iteration after the look."
    )


def _rule_from(z: pd.DataFrame, feat: str, s: float):
    """High tercile if spread>0 else low tercile -> (threshold, op, kept-frame)."""
    v = z[feat].dropna()
    hi = s > 0
    q = v.quantile(2 / 3) if hi else v.quantile(1 / 3)
    op = ">=" if hi else "<="
    keep = z[z[feat].notna() & ((z[feat] >= q) if hi else (z[feat] <= q))]
    return q, op, keep


# ======================================================================================
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="5 Jan ES trading days only")
    ap.add_argument("--analyze-only", action="store_true")
    ap.add_argument("--force", action="store_true", help="ignore feature cache, recompute")
    args = ap.parse_args()
    if args.analyze_only:
        analyze(pd.read_parquet(CACHE))
        return
    uni = fz.load_universe()
    nmo = pd.to_datetime(uni["trading_day"]).dt.month
    print(
        f"[universe] {len(uni)} combo+MBO 2026 trades qualify "
        f"(design Jan-Mar={int(nmo.isin(DESIGN_MONTHS).sum())}, "
        f"validation Apr-Jun={int(nmo.isin(VALID_MONTHS).sum())})"
    )
    if args.smoke:
        es_jan = uni[
            (uni["symbol"] == "ES.c.0") & (uni["trading_day"].str[:7] == "2026-01")
        ]
        days = sorted(es_jan["trading_day"].unique())[:5]
        uni = es_jan[es_jan["trading_day"].isin(days)]
        print(f"[smoke] 5 Jan ES days: {days} -> {len(uni)} trades")
    feats = build_features(uni, force=args.force)
    if args.smoke:
        days = sorted(uni["trading_day"].unique())
        smoke = feats[
            (feats["symbol"] == "ES.c.0") & feats["trading_day"].isin(days)
        ].copy()
        nz = int(smoke["zone_5m_has"].sum())
        zf = smoke[smoke["zone_5m_has"] == 1]
        all3 = (
            int(((zf["sw_n_events"] > 0) & (zf["fm_n_events"] > 0) & (zf["rt_n_events"] > 0)).sum())
            if len(zf)
            else 0
        )
        print(
            f"\n[smoke] {len(smoke)} ES trades; {nz} formed a 5m zone; "
            f"{all3}/{len(zf)} zone-formed have ALL 3 moments populated"
        )
        cols = [
            "trading_day",
            "side",
            "level_family",
            "trail_2R",
            "win",
            "zone_5m_has",
            "zone_5m_kind",
            "sw_n_events",
            "sw_aggr_imb_dir",
            "fm_n_events",
            "fm_delta_dir",
            "rt_n_events",
            "rt_add_refill_dir",
        ]
        cols = [c for c in cols if c in smoke.columns]
        print(smoke[cols].to_string(index=False))
        # per-moment non-null sanity on zone-formed
        if len(zf):
            for m in MOMENTS:
                print(
                    f"[smoke] {m}_* events>0 on {(zf[f'{m}_n_events'] > 0).sum()}/{len(zf)} "
                    f"zone-formed"
                )
    else:
        analyze(feats)


if __name__ == "__main__":
    main()
