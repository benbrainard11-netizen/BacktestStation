"""flow_at_zone.py -- STRUCTURE-ANCHORED order-flow selection (Ben's idea).

WHY (vs flow_at_scale.py): flow_at_scale measured GENERIC pre-trigger drift in a fixed
[decision-90s, decision) time window. That treats order flow as a free-floating burst. Ben's
idea is SPATIAL: the structure (an Order Block or FVG) is a PRICE ZONE. When price retraces
INTO that zone before the decision, the order-book reading AT the zone is what tells you whether
the zone HOLDS (continuation -> winner) or FAILS. So instead of "last 90s anywhere", we measure
MBO flow ONLY while the trade is printing inside the zone bounds. The structure anchors WHERE to
read the book; the book reading predicts whether the reclaim works.

WHAT THIS IS:
  * UNIVERSE = identical to flow_at_scale: runs/legal_bars_full.parquet, status=='entered',
    |trail_2R|<=5 & |fixed_3R|<=5, the registered COMBO subset (depth_tk>8 AND wait_s>=300),
    year(decision)==2026, 4 index roots, AND the trading_day has MBO coverage. (864 trades.)
  * For EACH trade, detect whether an OB or FVG zone formed in [touch, decision) on TF in {5m,15m}
    (5m won bar_confirmations.py; 15m kept as a check), using the EXACT sweep-candle / OB-candle /
    FVG-gap logic from bar_confirmations.py. Emit the ZONE PRICE BOUNDS:
        OB zone  (long, swept low) : [OB_candle.low, OB_candle.open]   (order-block body/lower range)
        FVG zone (long)            : [candle1.high, candle3.low]       (the gap)
      Mirror for shorts (OB up-close: [open, high]; FVG: [candle3.high, candle1.low]).
    Only a SUBSET of trades form a zone -- that is the analyzable population (expect ~5-15%).
  * IN-ZONE FLOW, over MBO events in [touch, decision) whose trade PRICE is inside the zone bounds
    (+/- 1 tick). All such events are pre-decision (LEGAL; asserted). dir_sign = +1 long
    (side=='low') / -1 short, exactly as flow_at_scale.

ANALYSIS (DESIGN = Jan+Feb+Mar 2026; VALIDATION = Apr+May+Jun computed+stored but NOT analyzed):
  * BASELINE-OF-ZONE: meanR of zone-formed trades vs no-zone trades -- did forming a zone already
    matter, BEFORE any flow reading?
  * Then, among ZONE-FORMED design trades only: per in-zone feature, meanR(trail_2R) + win by
    tercile and by sign. Does the FLOW within the zone add MORE separation on top of zone-formed?
  * Frozen-rule proposal for the strongest in-zone separator (one-shot on validation later).

REUSE:
  * MBO read / legality / aggr-delta-absorption machinery from flow_at_scale.py (prep_day pushdown,
    the per-window legality assert, action=='T' aggressor defs, signed-by-direction).
  * Zone detection from bar_confirmations.py (OB sweep-candle rule + FVG 3-candle gap, multi-TF,
    close<=decision legality) -- but emitting BOUNDS, not a confirm flag.
  * Bars via smt_bench (load_1m, resample_tf).

Crash-resilient: features cached per (symbol, trading_day) to runs/flow_at_zone_features.parquet
(tmp + atomic replace per day; resumes by skipping cached symbol-days). Predicate-pushdown MBO read
[min(touch)-margin, max(decision)).

Run:
    backend/.venv/Scripts/python.exe experiments/mira_gate_harness/flow_at_zone.py
Smoke (5 Jan ES days):   ... flow_at_zone.py --smoke
Analyze cached only:     ... flow_at_zone.py --analyze-only
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
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
from smt_bench import load_1m, resample_tf  # noqa: E402

RUNS = HERE / "runs"
UNIVERSE = RUNS / "legal_bars_full.parquet"
CACHE = RUNS / "flow_at_zone_features.parquet"
COMBO_ONLY = True  # flipped off by --all-reclaims (drops the depth>8 & wait>=5m patience pre-filter)
MBO_BASE = Path(r"D:\data\clean\databento\mbo_trading_day")

SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.1}
ZONE_TFS = ["5m", "15m"]  # 5m won bar_confirmations; 15m kept as a check
TF_MIN = {"5m": 5, "15m": 15}
ONE_NS = 1_000_000_000

DESIGN_MONTHS = {
    1,
    2,
    3,
}  # 2026; Apr/May/Jun reserved validation, stored but NOT analyzed
VALID_MONTHS = {4, 5, 6}
SUBSET_DEPTH_TK, SUBSET_WAIT_S = 8, 300  # registered frozen-combo deployment subset
RISK_CAP = 5.0
ZONE_TOL_TICKS = 1.0  # price counted "in zone" if within bounds +/- 1 tick (per spec)
REVISIT_GAP_US = (
    30_000_000  # price must leave the zone >=30s to count as a distinct revisit
)

MBO_COLS = ["ts_event", "action", "side", "price", "size"]
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

# the in-zone flow features analyzed (the primary TF = 5m; 15m emitted as a check)
IN_ZONE_FEATURES = [
    "zone_vol",
    "zone_delta_dir",
    "zone_aggr_imb_dir",
    "zone_absorption",
    "zone_revisits",
    "zone_add_refill_dir",
    "zone_n_events",
]


# ======================================================================================
# universe (identical gate to flow_at_scale.py) + MBO coverage
# ======================================================================================
def _covered_days() -> dict[str, set[str]]:
    cov: dict[str, set[str]] = {}
    for sym in SYMBOLS:
        sd = MBO_BASE / f"symbol={sym}"
        days = set()
        if sd.exists():
            for p in sd.glob("trading_day=*"):
                if (p / "part-000.parquet").exists():
                    days.add(p.name.split("=", 1)[1])
        cov[sym] = days
    return cov


def load_universe() -> pd.DataFrame:
    df = pd.read_parquet(UNIVERSE)
    df = df[df["status"] == "entered"].copy()
    yr = df["decision_ts_utc"].dt.year
    m = df["symbol"].isin(SYMBOLS) & (yr == 2026)
    m &= df["trail_2R"].abs() <= RISK_CAP
    m &= df["fixed_3R"].abs() <= RISK_CAP
    if COMBO_ONLY:  # --all-reclaims drops this registered patience pre-filter -> ~3.6x anchors
        m &= (df["depth_tk"] > SUBSET_DEPTH_TK) & (df["wait_s"] >= SUBSET_WAIT_S)
    df = df[m].copy()
    df = df.dropna(subset=["touch_ts_utc", "decision_ts_utc"])
    df = df[df["touch_ts_utc"] <= df["decision_ts_utc"]]
    df["trading_day"] = df["session_date"]
    cov = _covered_days()
    keep = df.apply(lambda r: r["trading_day"] in cov.get(r["symbol"], set()), axis=1)
    dropped = (~keep).sum()
    df = df[keep].copy()
    if dropped:
        print(f"[universe] dropped {dropped} trades with no MBO coverage")
    df = df.drop_duplicates(subset=["symbol", "decision_ts_utc", "level_price", "side"])
    return df.sort_values(["symbol", "trading_day", "decision_ts_utc"]).reset_index(
        drop=True
    )


# ======================================================================================
# ZONE DETECTION (OB body range / FVG gap) -- reuses bar_confirmations.py logic, emits BOUNDS.
# Returns (lo_px, hi_px, kind, formed_close_ns) for the FIRST zone, or None.
#
# TWO refinements over bar_confirmations' confirm-flag, so the zone is a real SPATIAL anchor (Ben's
# point) and not trivially-always-true (a bare OB-candle exists ~always):
#   (1) OB candle must OVERLAP the swept level (its body comes within OB_LEVEL_TOL ticks of the
#       level). bar_confirmations' fallback could grab a down-close candle 70+ ticks away; that is
#       not "the order block AT the level". The sweep candle itself is always allowed.
#   (2) The zone is only counted if price later RETRACES into it (handled by the caller via the 1m
#       retrace gate) -- "when price retraces into it" is the literal event. This is what makes the
#       analyzable set SMALL (~5-15%), as expected.
# Legality: only candles whose CLOSE <= decision are eligible. Bounds come from CLOSED candles only.
# ======================================================================================
OB_LEVEL_TOL_TICKS = (
    6.0  # (fallback only) OB candle body must come within this many ticks of level
)
OB_FALLBACK = (
    False  # if True, allow OB = most-recent prior down-close candle near the level
)


def _detect_zone_tf(
    tf_bars: pd.DataFrame,
    side: str,
    level_price: float,
    touch_ns: int,
    decision_ns: int,
    tf: str,
    tick: float,
) -> tuple[float, float, str, int] | None:
    tf_min = TF_MIN[tf]
    close_off = tf_min * 60 * ONE_NS
    idx_ns = tf_bars.index.asi8
    o = tf_bars["open"].to_numpy(float)
    h = tf_bars["high"].to_numpy(float)
    lo = tf_bars["low"].to_numpy(float)
    c = tf_bars["close"].to_numpy(float)
    close_ns = idx_ns + close_off

    legal = close_ns <= decision_ns
    if not legal.any():
        return None
    assert (
        close_ns[legal].max() <= decision_ns
    ), "zone legality: candle closes after decision"
    tol = OB_LEVEL_TOL_TICKS * tick + 1e-9

    # ---- OB zone (bar_confirmations sweep-candle / OB-candle rule) ----
    # sweep candle = first LEGAL candle that took the level AND closed at/after touch.
    if side == "low":  # LONG: swept a low
        took = lo <= level_price
    else:  # SHORT: swept a high
        took = h >= level_price
    sweep_elig = legal & took & (close_ns >= touch_ns)
    sweep_idx = int(np.argmax(sweep_elig)) if sweep_elig.any() else -1

    if sweep_idx >= 0:
        # OB candle = the SWEEP candle itself when it closed in the OB direction (the spec's
        # canonical zone: a down-close [long] candle right at the sweep -> [low, open]). The
        # bar_confirmations prior-down-close FALLBACK is OFF by default: with the fallback, an OB
        # candle exists ~always (a down-close near the level is mechanically present at a sweep),
        # so the "zone formed" gate became trivially ~90% true and zones ran 30+ ticks wide. The
        # restrictive rule makes "a clean OB formed AT the sweep" a genuinely selective event
        # (the small analyzable subset the study is after). OB_FALLBACK=True restores the broad
        # definition for sensitivity checks.
        ob_dir = (
            (c < o) if side == "low" else (c > o)
        )  # long OB = down-close; short OB = up-close
        if ob_dir[sweep_idx]:
            ob_idx = sweep_idx
        elif OB_FALLBACK:
            prev = np.where(ob_dir[:sweep_idx])[0]
            ob_idx = -1
            for j in prev[::-1]:
                b_lo, b_hi = min(o[j], c[j]), max(o[j], c[j])
                if (b_lo - tol) <= level_price <= (b_hi + tol):
                    ob_idx = int(j)
                    break
        else:
            ob_idx = -1
        if ob_idx >= 0:
            # OB zone bounds: long [OB.low, OB.open]; short [OB.open, OB.high]
            if side == "low":
                z_lo, z_hi = lo[ob_idx], o[ob_idx]
            else:
                z_lo, z_hi = o[ob_idx], h[ob_idx]
            if z_hi >= z_lo:
                return (float(z_lo), float(z_hi), "ob", int(close_ns[ob_idx]))

    # ---- FVG zone (3-candle gap, all legal, completing at/after touch) ----
    last_legal_i = int(np.where(legal)[0][-1])
    if last_legal_i >= 2:
        for i in range(1, last_legal_i):  # i = middle candle; uses i-1,i,i+1
            i1, i3 = i - 1, i + 1
            if i3 > last_legal_i:
                break
            if not (legal[i1] and legal[i] and legal[i3]):
                continue
            if close_ns[i3] < touch_ns:  # pattern must complete at/after the touch
                continue
            if side == "low":
                if h[i1] < lo[i3]:  # bullish gap: zone [candle1.high, candle3.low]
                    return (float(h[i1]), float(lo[i3]), "fvg", int(close_ns[i3]))
            else:
                if lo[i1] > h[i3]:  # bearish gap: zone [candle3.high, candle1.low]
                    return (float(h[i3]), float(lo[i1]), "fvg", int(close_ns[i3]))
    return None


# ======================================================================================
# MBO day read (predicate pushdown) -- reused from flow_at_scale.py
# ======================================================================================
def prep_day(symbol: str, trading_day: str, lo_us: int, hi_us: int) -> dict:
    import pyarrow.dataset as pds

    p = (
        MBO_BASE
        / f"symbol={symbol}"
        / f"trading_day={trading_day}"
        / "part-000.parquet"
    )
    ts_lo = pd.Timestamp(lo_us, unit="us", tz="UTC")
    ts_hi = pd.Timestamp(hi_us, unit="us", tz="UTC")
    df = (
        pds.dataset(p)
        .to_table(
            columns=MBO_COLS,
            filter=(pds.field("ts_event") >= ts_lo) & (pds.field("ts_event") < ts_hi),
        )
        .to_pandas()
    )
    ts = df["ts_event"].astype("int64").to_numpy()  # microseconds since epoch
    assert np.all(np.diff(ts) >= 0), f"ts_event not sorted {symbol} {trading_day}"
    return {
        "ts": ts,
        "px": df["price"].to_numpy(np.float64),
        "sz": df["size"].to_numpy(np.float64),
        "is_T": (df["action"] == "T").to_numpy(),
        "is_A": (df["action"] == "A").to_numpy(),
        "is_C": (df["action"] == "C").to_numpy(),
        "bid": (df["side"] == "B").to_numpy(),
        "ask": (df["side"] == "A").to_numpy(),
    }


def _imb(a: float, b: float) -> float:
    return (a - b) / (a + b) if (a + b) > 0 else np.nan


# ======================================================================================
# IN-ZONE FLOW features over MBO events in [touch, decision) with price inside zone bounds.
# ======================================================================================
def zone_flow_feats(
    day: dict,
    touch_us: int,
    decision_us: int,
    z_lo: float,
    z_hi: float,
    dir_sign: int,
    tick: float,
) -> dict:
    """Flow over events with touch_us <= ts < decision_us AND price within [z_lo,z_hi] +/- 1 tick.

    LEGALITY: hi bound is decision_us (events strictly pre-decision). Asserted.
    Defending side: for a long (dir_sign=+1) defenders sit on the BID (resting buys hold the floor);
    for a short, on the ASK. Refill proxy = add-size / cancel-size on the defending side in zone.
    """
    ts = day["ts"]
    i0 = np.searchsorted(ts, touch_us, "left")
    i1 = np.searchsorted(ts, decision_us, "left")
    if i1 > i0:
        assert (
            ts[i1 - 1] < decision_us
        ), "event at/after decision leaked into in-zone window"
    sl = slice(i0, i1)
    tss = ts[sl]
    px, sz = day["px"][sl], day["sz"][sl]
    is_T, is_A, is_C = day["is_T"][sl], day["is_A"][sl], day["is_C"][sl]
    bid, ask = day["bid"][sl], day["ask"][sl]

    tol = ZONE_TOL_TICKS * tick + 1e-9
    in_zone = (px >= z_lo - tol) & (px <= z_hi + tol)
    n_events = int(in_zone.sum())
    if n_events == 0:
        return {
            "zone_vol": 0.0,
            "zone_delta_dir": 0.0,
            "zone_aggr_imb_dir": np.nan,
            "zone_absorption": np.nan,
            "zone_revisits": 0,
            "zone_add_refill_dir": np.nan,
            "zone_n_events": 0,
        }

    zt = is_T & in_zone  # trade prints inside the zone
    buy = sz[zt & bid].sum()  # aggressive buy (lifts ask -> tagged bid side? see note)
    sell = sz[zt & ask].sum()
    # NOTE on aggressor side: in Databento MBO trade prints, `side` is the aggressor's resting
    # opposite -- we follow flow_at_scale's convention verbatim (T & bid => buy-tagged, T & ask =>
    # sell-tagged) so signs are consistent across the two studies. dir_sign aligns it to the trade.
    zone_vol = float(buy + sell)
    zone_delta_dir = float(dir_sign * (buy - sell))
    zone_aggr_imb_dir = dir_sign * _imb(buy, sell)

    # absorption = volume traded in zone / (1 + ticks price traversed while in zone).
    # high = a lot of size changed hands without price moving much => zone absorbed/held.
    zpx = px[in_zone]
    span_ticks = (np.nanmax(zpx) - np.nanmin(zpx)) / tick if len(zpx) else 0.0
    zone_absorption = float(zone_vol / (1.0 + span_ticks))

    # revisits = DISTINCT times price entered the zone. A rising edge on the raw tick-level mask
    # counts micro-jitter (thousands of boundary crossings); debounce by REVISIT_GAP_US -- a new
    # revisit is counted only after price has been OUT of the zone for at least that gap.
    iz = in_zone
    enter_idx = (
        np.where(iz[1:] & ~iz[:-1])[0] + 1
    )  # first in-zone event of each crossing
    if iz[0]:
        enter_idx = np.r_[0, enter_idx]
    if len(enter_idx) == 0:
        zone_revisits = 0
    else:
        enter_ts = tss[enter_idx]
        # collapse entries closer than the debounce gap into one revisit
        zone_revisits = 1 + int((np.diff(enter_ts) >= REVISIT_GAP_US).sum())

    # refill proxy: A (add) size vs C (cancel) size on the DEFENDING side within the zone.
    defend = bid if dir_sign == 1 else ask
    add_d = sz[is_A & defend & in_zone].sum()
    can_d = sz[is_C & defend & in_zone].sum()
    zone_add_refill_dir = float(add_d / can_d) if can_d > 0 else np.nan

    return {
        "zone_vol": zone_vol,
        "zone_delta_dir": zone_delta_dir,
        "zone_aggr_imb_dir": zone_aggr_imb_dir,
        "zone_absorption": zone_absorption,
        "zone_revisits": zone_revisits,
        "zone_add_refill_dir": zone_add_refill_dir,
        "zone_n_events": n_events,
    }


# ======================================================================================
# per-day: resample bars once, detect zones, compute in-zone flow.
# ======================================================================================
def _resample_for_day(symbol: str, trading_day: str) -> dict:
    """1m bars for the trading_day (+/- pad) resampled to each zone TF, plus the raw 1m frame
    (used for the retrace gate). Pad lo 12h for OB lead-in."""
    d0 = pd.Timestamp(trading_day, tz="UTC")
    lo = (d0 - pd.Timedelta(hours=12)).strftime("%Y-%m-%d")
    hi = (d0 + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    bars = load_1m(symbol, lo, hi)
    if bars.empty:
        return {}
    out = {tf: resample_tf(bars, TF_MIN[tf]) for tf in ZONE_TFS}
    out["1m"] = bars
    return out


def _retraced(
    bars1m: pd.DataFrame,
    z_lo: float,
    z_hi: float,
    formed_close_ns: int,
    decision_ns: int,
    tick: float,
) -> bool:
    """Did price RE-ENTER the zone bounds AFTER the zone candle closed, before decision?
    Uses LEGAL 1m bars (open at-or-after formed_close, close <= decision). A 1m bar overlaps the
    zone if its [low,high] intersects [z_lo,z_hi] +/- 1 tick. This is the spatial 'retrace into it'
    event; with it, zone formation becomes the SMALL analyzable subset."""
    if bars1m is None or not len(bars1m):
        return False
    idx_ns = bars1m.index.asi8
    close_ns = idx_ns + 60 * ONE_NS  # 1m close
    sel = (idx_ns >= formed_close_ns) & (close_ns <= decision_ns)
    if not sel.any():
        return False
    sub = bars1m.iloc[sel]
    tol = ZONE_TOL_TICKS * tick + 1e-9
    h = sub["high"].to_numpy(float)
    lo = sub["low"].to_numpy(float)
    overlap = (h >= z_lo - tol) & (lo <= z_hi + tol)
    return bool(overlap.any())


def trade_features(day: dict, tf_frames: dict, row: pd.Series) -> dict:
    tick = TICK[row["symbol"]]
    dir_sign = 1 if row["side"] == "low" else -1  # low level reclaimed -> long
    touch_ns = int(row["touch_ts_utc"].value)
    decision_ns = int(row["decision_ts_utc"].value)
    touch_us = touch_ns // 1_000
    decision_us = (
        decision_ns // 1_000
    )  # us floor; ts_us < decision_us => ts < decision tick
    bars1m = tf_frames.get("1m")

    out = {k: row[k] for k in KEEP}
    out["trading_day"] = row["trading_day"]
    out["dir_sign"] = dir_sign
    out["win"] = bool(row["trail_2R"] > 0)

    for tf in ZONE_TFS:
        tag = tf
        tf_b = tf_frames.get(tf)
        zone = None
        if tf_b is not None and len(tf_b):
            # slice to a small window around the trade for speed (close in [touch-6h, decision])
            close_ns = tf_b.index.asi8 + TF_MIN[tf] * 60 * ONE_NS
            sel = (close_ns >= touch_ns - 6 * 3600 * ONE_NS) & (close_ns <= decision_ns)
            sub = tf_b.iloc[sel]
            zone = _detect_zone_tf(
                sub,
                row["side"],
                float(row["level_price"]),
                touch_ns,
                decision_ns,
                tf,
                tick,
            )
        # retrace gate: a zone counts only if price re-entered it before decision (spatial event)
        retraced = zone is not None and _retraced(
            bars1m, zone[0], zone[1], zone[3], decision_ns, tick
        )
        if zone is None or not retraced:
            out[f"zone_{tag}_has"] = 0
            out[f"zone_{tag}_kind"] = None
            out[f"zone_{tag}_lo"] = np.nan
            out[f"zone_{tag}_hi"] = np.nan
            for f in IN_ZONE_FEATURES:
                out[f"{tag}_{f}"] = np.nan
            continue
        z_lo, z_hi, kind, _ = zone
        out[f"zone_{tag}_has"] = 1
        out[f"zone_{tag}_kind"] = kind
        out[f"zone_{tag}_lo"] = z_lo
        out[f"zone_{tag}_hi"] = z_hi
        ff = zone_flow_feats(day, touch_us, decision_us, z_lo, z_hi, dir_sign, tick)
        for f in IN_ZONE_FEATURES:
            out[f"{tag}_{f}"] = ff[f]
    return out


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
            # MBO read window: from earliest touch (-margin) to latest decision. In-zone flow uses
            # [touch, decision); pad lo a touch for searchsorted safety.
            touch_us = g["touch_ts_utc"].astype("int64") // 1_000
            dec_us = g["decision_ts_utc"].astype("int64") // 1_000
            day = prep_day(sym, td, int(touch_us.min() - 5_000_000), int(dec_us.max()))
            tf_frames = _resample_for_day(sym, td)
        except Exception as e:  # missing/broken day: skip loudly, never fabricate
            print(f"  SKIP {sym} {td}: {type(e).__name__}: {e}")
            skipped.append((sym, td, len(g)))
            continue
        rows = pd.DataFrame(
            [trade_features(day, tf_frames, r) for _, r in g.iterrows()]
        )
        cached = pd.concat([cached, rows], ignore_index=True)
        tmp = CACHE.with_suffix(
            ".tmp.parquet"
        )  # crash-safe: tmp + atomic replace per day
        cached.to_parquet(tmp, index=False)
        tmp.replace(CACHE)
        nz5 = int(rows["zone_5m_has"].sum()) if "zone_5m_has" in rows else 0
        print(
            f"  [{n}/{len(todo)}] {sym} {td}: {len(rows)} trades, {nz5} formed a 5m zone"
        )
    if skipped:
        print(
            f"[build] WARNING: skipped {len(skipped)} symbol-days "
            f"({sum(s[2] for s in skipped)} trades): {skipped}"
        )
    return cached


# ======================================================================================
# ANALYSIS -- DESIGN months only; zone-formed subset only for the flow tables.
# ======================================================================================
def _bucket_table(d: pd.DataFrame, feat: str, label: str) -> float | None:
    """meanR(trail_2R) + win by tercile and by sign; return top-bottom meanR spread."""
    v = d[[feat, "trail_2R", "win"]].dropna(subset=[feat, "trail_2R"])
    if len(v) < 20:
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


def analyze(feats: pd.DataFrame) -> None:
    mo = pd.to_datetime(feats["trading_day"]).dt.month
    yr = pd.to_datetime(feats["trading_day"]).dt.year
    design = feats[(yr == 2026) & mo.isin(DESIGN_MONTHS)].copy()
    valid = feats[(yr == 2026) & mo.isin(VALID_MONTHS)].copy()
    print(
        f"\n{'=' * 100}\nANALYSIS -- DESIGN Jan+Feb+Mar 2026 ({len(design)} trades). "
        f"VALIDATION Apr+May+Jun stored, NOT analyzed ({len(valid)} trades, reserved one-shot)."
    )

    # ---- zone-formation rates (5m primary, 15m check) ----
    for tf in ZONE_TFS:
        col = f"zone_{tf}_has"
        if col not in design:
            continue
        n_z = int(design[col].sum())
        rate = n_z / len(design) if len(design) else 0.0
        kinds = (
            design.loc[design[col] == 1, f"zone_{tf}_kind"].value_counts().to_dict()
            if n_z
            else {}
        )
        print(
            f"  [{tf}] zone-formed (design): {n_z}/{len(design)} = {rate:.1%}  kinds={kinds}"
        )

    # ---- BASELINE-OF-ZONE: did forming a zone already matter (before flow)? ----
    print(
        f"\n{'-' * 100}\nDID FORMING A ZONE ALREADY MATTER (design, 5m) -- before any flow reading:"
    )
    z = design[design["zone_5m_has"] == 1]
    nz = design[design["zone_5m_has"] == 0]
    print(
        f"  zone-formed : meanR={z['trail_2R'].mean():+.3f}  win={z['win'].mean():.1%}  n={len(z)}\n"
        f"  no-zone     : meanR={nz['trail_2R'].mean():+.3f}  win={nz['win'].mean():.1%}  n={len(nz)}\n"
        f"  lift(zone - no-zone): {z['trail_2R'].mean() - nz['trail_2R'].mean():+.3f}R"
    )

    # ---- IN-ZONE FLOW among zone-formed design trades (5m) ----
    if len(z) < 20:
        print(
            f"\n[5m] only {len(z)} zone-formed design trades -- too few to size in-zone flow "
            f"selection. (Zone formation is the binding constraint, as expected ~5-15%.)"
        )
        _frozen_proposal({}, z)
        return
    print(
        f"\n{'-' * 100}\nIN-ZONE FLOW among 5m zone-formed design trades only (n={len(z)}); "
        f"does the book reading AT the zone add MORE separation:"
    )
    ranks = {}
    for f in IN_ZONE_FEATURES:
        col = f"5m_{f}"
        if col not in z:
            continue
        s = _bucket_table(z, col, f)
        if s is not None and s != 0:
            ranks[col] = s
    _frozen_proposal(ranks, z)


def _frozen_proposal(ranks: dict, z: pd.DataFrame) -> None:
    print(
        f"\n{'-' * 100}\nFROZEN-RULE PROPOSAL (DESIGN-only; ranked by |tercile meanR spread|, "
        "sign-consistent):"
    )
    if not ranks:
        print(
            "  none -- no in-zone flow feature shows usable tercile spread among zone-formed "
            "trades (in-zone flow selection NO-GO as constructed, or N too small)."
        )
        print(
            "ONE-SHOT PLAN: if a rule below is shown, freeze it verbatim and evaluate ONCE on "
            "Apr+May+Jun (cached). No iteration after the look."
        )
        return
    consistent = {}
    for feat, s in ranks.items():
        v = z[[feat, "trail_2R"]].dropna()
        pos, neg = v[v[feat] > 0]["trail_2R"], v[v[feat] <= 0]["trail_2R"]
        if len(pos) < 8 or len(neg) < 8:
            consistent[feat] = (
                s  # keep (sign split unavailable, e.g. always-positive feature)
            )
            continue
        if np.sign(pos.mean() - neg.mean()) == np.sign(s) != 0:
            consistent[feat] = s
    top = sorted(consistent.items(), key=lambda kv: -abs(kv[1]))[:2]
    for i, (feat, s) in enumerate(top, 1):
        v = z[feat].dropna()
        hi = s > 0
        q = v.quantile(2 / 3) if hi else v.quantile(1 / 3)
        op = ">=" if hi else "<="
        keep = z[z[feat].notna() & ((z[feat] >= q) if hi else (z[feat] <= q))]
        print(
            f"  #{i} {feat}: design tercile spread {s:+.3f}\n"
            f"     FROZEN-RULE: among zone-formed, take only if {feat} {op} {q:.4f}\n"
            f"     -> design meanR {keep['trail_2R'].mean():+.3f} win {keep['win'].mean():.1%} "
            f"(n={len(keep)}) vs zone-formed baseline {z['trail_2R'].mean():+.3f} "
            f"win {z['win'].mean():.1%} (n={len(z)})"
        )
    print(
        "ONE-SHOT PLAN: freeze the #1 rule verbatim, evaluate ONCE on Apr+May+Jun zone-formed "
        "(features cached). No iteration after the look."
    )


# ======================================================================================
def main() -> None:
    global CACHE, COMBO_ONLY, UNIVERSE
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="5 Jan ES trading days only")
    ap.add_argument("--analyze-only", action="store_true")
    ap.add_argument(
        "--force", action="store_true", help="ignore feature cache, recompute"
    )
    ap.add_argument("--all-reclaims", action="store_true",
                    help="drop the combo patience pre-filter (~3.6x anchors); separate cache")
    ap.add_argument("--universe", default=None,
                    help="alternate universe parquet (new level families); separate cache by stem")
    args = ap.parse_args()
    if args.universe:
        UNIVERSE = Path(args.universe)
        COMBO_ONLY = False
        CACHE = RUNS / f"flow_at_zone_{UNIVERSE.stem}.parquet"
    elif args.all_reclaims:
        COMBO_ONLY = False
        CACHE = RUNS / "flow_at_zone_all.parquet"
    if args.analyze_only:
        analyze(pd.read_parquet(CACHE))
        return
    uni = load_universe()
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
        n5 = int(smoke["zone_5m_has"].sum())
        n15 = int(smoke["zone_15m_has"].sum())
        print(
            f"\n[smoke] {len(smoke)} ES trades; {n5} formed a 5m zone, {n15} a 15m zone"
        )
        cols = [
            "trading_day",
            "side",
            "trail_2R",
            "win",
            "zone_5m_has",
            "zone_5m_kind",
            "zone_5m_lo",
            "zone_5m_hi",
            "5m_zone_n_events",
            "5m_zone_vol",
            "5m_zone_delta_dir",
            "5m_zone_absorption",
            "5m_zone_revisits",
        ]
        cols = [c for c in cols if c in smoke.columns]
        print(smoke[cols].to_string(index=False))
        zf = smoke[smoke["zone_5m_has"] == 1]
        if len(zf):
            print(
                f"\n[smoke] zone-formed in-zone flow non-null check: "
                f"n_events>0 on {(zf['5m_zone_n_events'] > 0).sum()}/{len(zf)}"
            )
    else:
        analyze(feats)


if __name__ == "__main__":
    main()
