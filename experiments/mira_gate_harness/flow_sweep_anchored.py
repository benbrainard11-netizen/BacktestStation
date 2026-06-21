"""flow_sweep_anchored.py -- SWEEP-ANCHORED pre-trigger order-flow SELECTION test.

WHY (Ben's idea): flow_at_scale.py windows order flow over a FIXED [decision-90s, decision) slice --
an arbitrary "last 90 seconds before the bar closes". But the actual manipulation->reaction starts at
the SWEEP (the moment the level was first touched), not 90s before the decision. So anchor the flow
window at the sweep: [touch_ts_utc, decision_ts_utc) captures the FULL order-flow reaction from the
sweep until the decision, not an arbitrary tail slice. This is the principled window.

LEGALITY: touch_ts_utc < decision_ts_utc by construction within the registered COMBO subset (verified:
in the depth_tk>8 AND wait_s>=300 universe all 878 trades have touch < decision; the general entered
set does NOT, which is exactly why the per-window assert stays). The flow window ENDS AT decision (the
bar close = the legal anchor), so it never sees the decision tick or anything after it. We keep the
SAME per-window legality assert as flow_at_scale: every MBO event ts strictly < the decision tick.

THREE WINDOWS per trade (compute all 3 to COMPARE, but the analysis picks ONE principled winner --
sweep_anchored -- we are NOT window-shopping 20 variants):
  1. sweep_anchored  sw_   : [touch, decision)            -- the new principled window (len = wait_s-60)
  2. last90          l90_  : [decision-90s, decision)     -- the flow_at_scale baseline, direct compare
  3. last30          l30_  : [decision-30s, decision)     -- shorter, tests "fresher = better"
Same features over each (aggr_imb_dir, near_add_imb_dir, c2a_defend[_near], drift_dir_ticks,
trade_count, vol). drift/vol are RATE-NORMALIZED where window length varies: every window also emits a
per-second drift (drift_dir_per_s = drift_dir_ticks / window_seconds) so the long sweep window isn't
mechanically larger than the 30s/90s ones. window_seconds is recorded per window.

TWO ADDITIONS (vs flow_at_scale):
  A. wait_s (sweep->entry seconds; sweep->decision = wait_s-60) included as an analysis feature.
  B. TIME-DECAY TEST (Ben's hypothesis: later confirmation = weaker, connects to the ~10s edge
     half-life finding): bucket trades by wait_s (<5min, 5-15min, 15-60min, >=60min) and report
     meanR/win-rate per bucket -- does the edge fade the longer after the sweep you confirm?

EVERYTHING ELSE reused VERBATIM from flow_at_scale.py: the universe (runs/legal_bars_full.parquet,
status=='entered', risk cap, COMBO depth_tk>8 & wait_s>=300, 2026, 4 index roots, MBO-coverage gate),
the MBO predicate-pushdown read, the feature math (window_feats), the DESIGN(Jan-Mar)/VALIDATION
(Apr-Jun) split (validation COMPUTED + STORED, NOT analyzed -- one-shot reserved), and the legality
assert. ONLY the read lower bound is widened: it must now cover the sweep-anchored window, so it is
min( min(touch_us), min(decision_us)-310s ) - margin (NOT just min(decision)-310s).

ANALYSIS: DESIGN = decision/touch month in {Jan,Feb,Mar} 2026. Per windowed feature: meanR(trail_2R) +
win-rate by tercile and by sign, design only. Frozen-rule proposal for the strongest sign-consistent
separator across ALL the windowed features (sw_/l90_/l30_) PLUS wait_s. Plus the wait_s decay table.
VALIDATION Apr-Jun computed + stored, NOT analyzed.

Crash-resilient: features cached per (symbol, trading_day) to runs/flow_sweep_features.parquet (tmp +
atomic replace per day; resumes by skipping cached symbol-days). Full-day reads are 25-40GB.

Run:
    backend/.venv/Scripts/python.exe experiments/mira_gate_harness/flow_sweep_anchored.py
Smoke (3 Jan ES days):   ... flow_sweep_anchored.py --smoke
Analyze cached only:     ... flow_sweep_anchored.py --analyze-only
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

RUNS = HERE / "runs"
UNIVERSE = RUNS / "legal_bars_full.parquet"
CACHE = RUNS / "flow_sweep_features.parquet"
MBO_BASE = Path(r"D:\data\clean\databento\mbo_trading_day")

SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.1}
LAST90_S, LAST30_S = (
    90,
    30,
)  # the two fixed-tail comparison windows; sweep window len = wait_s-60
NEAR_TICKS = 4
DESIGN_MONTHS = {
    1,
    2,
    3,
}  # 2026; Apr/May/Jun = reserved validation, stored but NOT analyzed
VALID_MONTHS = {4, 5, 6}
SUBSET_DEPTH_TK, SUBSET_WAIT_S = 8, 300  # the registered frozen-combo deployment subset
RISK_CAP = 5.0  # |trail_2R|, |fixed_3R| <= 5 drops the near-zero-risk corrupt rows
READ_MARGIN_US = 310_000_000  # read lower-bound safety margin (310s, same scale as flow_at_scale base)
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
# Per-window feature stems shared across the 3 windows.
_STEMS = [
    "aggr_imb_dir",
    "near_add_imb_dir",
    "c2a_defend",
    "c2a_defend_near",
    "drift_dir_ticks",
    "drift_dir_per_s",
    "trade_count",
    "vol",
]
# Analysis features: the principled sweep window + the two fixed-tail comparators + wait_s decay axis.
ANALYSIS_FEATURES = (
    [f"sw_{s}" for s in _STEMS]
    + [f"l90_{s}" for s in _STEMS]
    + [f"l30_{s}" for s in _STEMS]
    + ["wait_s"]
)


def _covered_days() -> dict[str, set[str]]:
    """{symbol -> set of trading_days that have an MBO part file}. Coverage gate."""
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
    # year on the DECISION tick (the legal anchor), not entry
    yr = df["decision_ts_utc"].dt.year
    m = df["symbol"].isin(SYMBOLS) & (yr == 2026)
    m &= df["trail_2R"].abs() <= RISK_CAP
    m &= df["fixed_3R"].abs() <= RISK_CAP
    m &= (df["depth_tk"] > SUBSET_DEPTH_TK) & (df["wait_s"] >= SUBSET_WAIT_S)
    df = df[m].copy()
    # trading_day key for the MBO partition. session_date == ET-derived trading_day here (verified
    # 100% identical; all entries are RTH 9-16 ET so no 18:00 overnight rollover).
    df["trading_day"] = df["session_date"]
    # MBO-coverage gate
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


def prep_day(symbol: str, trading_day: str, lo_us: int, hi_us: int) -> dict:
    # Predicate-pushdown read. For the sweep-anchored window the lower bound must reach the EARLIEST
    # touch (the sweep), so the caller passes lo = min(min(touch), min(decision)-310s) - margin.
    # Full-day reads (25-40GB) saturate D:. ds.dataset on the explicit file does the row-group
    # pushdown with NO hive partition inference (which collides symbol dict-vs-string column).
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


def window_feats(
    day: dict,
    lo_us: int,
    hi_us: int,
    decision_us: int,
    level_px: float,
    dir_sign: int,
    tick: float,
) -> dict:
    """Features over events with lo_us <= ts < hi_us. hi_us <= decision_us always (legality).

    drift_dir_per_s rate-normalizes drift by the window length so the long sweep window is not
    mechanically larger than the fixed 30s/90s tails. window_seconds is recorded for transparency.
    """
    ts = day["ts"]
    i0, i1 = np.searchsorted(ts, lo_us, "left"), np.searchsorted(ts, hi_us, "left")
    if i1 > i0:  # THE legality assert: every event strictly before the decision tick
        assert (
            ts[i1 - 1] < decision_us
        ), "event at/after decision leaked into pre-trigger window"
    sl = slice(i0, i1)
    px, sz = day["px"][sl], day["sz"][sl]
    is_T, is_A, is_C = day["is_T"][sl], day["is_A"][sl], day["is_C"][sl]
    bid, ask = day["bid"][sl], day["ask"][sl]
    defend = bid if dir_sign == 1 else ask

    buy, sell = sz[is_T & bid].sum(), sz[is_T & ask].sum()
    near = np.abs(px - level_px) <= NEAR_TICKS * tick + 1e-9
    add_nb, add_na = sz[is_A & near & bid].sum(), sz[is_A & near & ask].sum()
    add_d, can_d = sz[is_A & defend].sum(), sz[is_C & defend].sum()
    add_dn, can_dn = sz[is_A & defend & near].sum(), sz[is_C & defend & near].sum()
    tpx = px[is_T]
    win_s = max((hi_us - lo_us) / 1_000_000.0, 1e-9)
    drift = dir_sign * (tpx[-1] - tpx[0]) / tick if len(tpx) >= 2 else np.nan
    return {
        "window_seconds": float(win_s),
        "n_events": int(i1 - i0),
        "trade_count": int(is_T.sum()),
        "vol": float(buy + sell),
        "aggr_imb_dir": dir_sign * _imb(buy, sell),
        "near_add_imb_dir": dir_sign * _imb(add_nb, add_na),
        "c2a_defend": float(can_d / add_d) if add_d > 0 else np.nan,
        "c2a_defend_near": float(can_dn / add_dn) if add_dn > 0 else np.nan,
        "drift_dir_ticks": drift,
        "drift_dir_per_s": (drift / win_s if not np.isnan(drift) else np.nan),
    }


def trade_features(day: dict, row: pd.Series) -> dict:
    tick = TICK[row["symbol"]]
    dir_sign = 1 if row["side"] == "low" else -1  # low level reclaimed -> long
    # decision tick = bar close = the legal anchor. ns -> us floor; ts < decision_us => ts < decision
    decision_us = int(row["decision_ts_utc"].value // 1_000)
    touch_us = int(row["touch_ts_utc"].value // 1_000)
    # legality (universe-level): touch must precede the decision. True for all COMBO rows; assert it.
    assert (
        touch_us < decision_us
    ), "touch >= decision -- sweep window would be empty/illegal"

    # 1) sweep_anchored [touch, decision) -- the principled window
    sw = window_feats(
        day, touch_us, decision_us, decision_us, row["level_price"], dir_sign, tick
    )
    # 2) last90 [decision-90s, decision) -- flow_at_scale baseline, direct comparison
    l90 = window_feats(
        day,
        decision_us - LAST90_S * 1_000_000,
        decision_us,
        decision_us,
        row["level_price"],
        dir_sign,
        tick,
    )
    # 3) last30 [decision-30s, decision) -- "fresher = better" test
    l30 = window_feats(
        day,
        decision_us - LAST30_S * 1_000_000,
        decision_us,
        decision_us,
        row["level_price"],
        dir_sign,
        tick,
    )

    out = {k: row[k] for k in KEEP}
    out["trading_day"] = row["trading_day"]
    out["dir_sign"] = dir_sign
    out["win"] = bool(row["trail_2R"] > 0)
    out.update({f"sw_{k}": v for k, v in sw.items()})
    out.update({f"l90_{k}": v for k, v in l90.items()})
    out.update({f"l30_{k}": v for k, v in l30.items()})
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
            dec_us = g["decision_ts_utc"].astype("int64") // 1_000
            tch_us = g["touch_ts_utc"].astype("int64") // 1_000
            # widen the read lower bound to cover the sweep-anchored window: the EARLIEST of either
            # the first touch or (first decision - 310s), minus a safety margin.
            lo = int(min(tch_us.min(), dec_us.min() - READ_MARGIN_US) - READ_MARGIN_US)
            day = prep_day(sym, td, lo, int(dec_us.max()))
        except Exception as e:  # missing/broken day file: skip loudly, never fabricate
            print(f"  SKIP {sym} {td}: {type(e).__name__}: {e}")
            skipped.append((sym, td, len(g)))
            continue
        rows = pd.DataFrame([trade_features(day, r) for _, r in g.iterrows()])
        cached = pd.concat([cached, rows], ignore_index=True)
        tmp = CACHE.with_suffix(
            ".tmp.parquet"
        )  # crash-safe: tmp + atomic replace per day
        cached.to_parquet(tmp, index=False)
        tmp.replace(CACHE)
        print(
            f"  [{n}/{len(todo)}] {sym} {td}: {len(rows)} trades "
            f"(sw ev med={rows['sw_n_events'].median():.0f}, "
            f"l90 ev med={rows['l90_n_events'].median():.0f})"
        )
    if skipped:
        print(
            f"[build] WARNING: skipped {len(skipped)} symbol-days "
            f"({sum(s[2] for s in skipped)} trades): {skipped}"
        )
    return cached


def _bucket_table(d: pd.DataFrame, feat: str, label: str) -> float | None:
    """Print meanR(trail_2R) + win-rate by tercile and by sign; return top-bottom meanR spread."""
    v = d[[feat, "trail_2R", "win"]].dropna(subset=[feat, "trail_2R"])
    if len(v) < 30:
        print(f"    {label:<40} n={len(v)} (too few, skipped)")
        return None
    try:
        terc = pd.qcut(v[feat], 3, labels=["T1_lo", "T2", "T3_hi"], duplicates="drop")
    except ValueError:
        print(f"    {label:<40} degenerate distribution, skipped")
        return None
    g = v.groupby(terc).agg(
        meanR=("trail_2R", "mean"), win=("win", "mean"), n=("trail_2R", "count")
    )
    if len(g) < 3:
        print(f"    {label:<40} <3 distinct terciles, skipped")
        return None
    spread = g["meanR"].iloc[-1] - g["meanR"].iloc[0]
    cells = "  ".join(
        f"{i}={r['meanR']:+.3f}/wr{r['win']:.0%}(n={int(r['n'])})"
        for i, r in g.iterrows()
    )
    pos, neg = v[v[feat] > 0], v[v[feat] <= 0]
    sign = (
        f"  sign>0={pos['trail_2R'].mean():+.3f}/wr{pos['win'].mean():.0%}(n={len(pos)}) "
        f"<=0={neg['trail_2R'].mean():+.3f}/wr{neg['win'].mean():.0%}(n={len(neg)})"
        if len(pos) >= 10 and len(neg) >= 10
        else ""
    )
    print(f"    {label:<40} {cells}  spread={spread:+.3f}{sign}")
    return float(spread)


def _wait_decay_table(d: pd.DataFrame) -> None:
    """ADDITION B: does the edge fade the longer after the sweep you confirm? Bucket by wait_s."""
    print(
        f"\n{'-' * 100}\nTIME-DECAY (Ben's hypothesis: later confirmation = weaker; ~10s edge "
        f"half-life). meanR(trail_2R) + win-rate by wait_s bucket (DESIGN Jan-Mar only):"
    )
    bins = [0, 300, 900, 3600, np.inf]
    labels = ["<5min", "5-15min", "15-60min", ">=60min"]
    b = pd.cut(d["wait_s"], bins=bins, labels=labels, right=False)
    g = d.groupby(b).agg(
        meanR=("trail_2R", "mean"), win=("win", "mean"), n=("trail_2R", "count")
    )
    for i, r in g.iterrows():
        nn = int(r["n"]) if not np.isnan(r["n"]) else 0
        if nn == 0:
            print(f"    {str(i):<12} (empty)")
        else:
            print(
                f"    {str(i):<12} meanR={r['meanR']:+.3f}  win-rate={r['win']:.1%}  n={nn}"
            )


def analyze(feats: pd.DataFrame) -> None:
    mo = pd.to_datetime(feats["trading_day"]).dt.month
    yr = pd.to_datetime(feats["trading_day"]).dt.year
    design = feats[(yr == 2026) & mo.isin(DESIGN_MONTHS)].copy()
    valid = feats[(yr == 2026) & mo.isin(VALID_MONTHS)].copy()
    print(
        f"\n{'=' * 100}\nANALYSIS -- DESIGN MONTHS Jan+Feb+Mar 2026 ONLY ({len(design)} trades). "
        f"VALIDATION Apr+May+Jun stored but NOT analyzed ({len(valid)} trades, reserved one-shot)."
    )
    print(
        f"baseline (design): meanR trail_2R={design['trail_2R'].mean():+.3f} "
        f"win-rate={design['win'].mean():.1%} (n={len(design)})"
    )
    ranks = {}
    for feat in ANALYSIS_FEATURES:
        print(f"  {feat}")
        s = _bucket_table(design, feat, "design")
        if s is not None and s != 0:
            ranks[feat] = s
    _wait_decay_table(design)
    print(
        f"\n{'-' * 100}\nCANDIDATE RULES (DESIGN-ONLY -- Jan+Feb+Mar 2026; across ALL windowed "
        f"features sw_/l90_/l30_ + wait_s; ranked by |tercile meanR spread|, sign-consistent "
        f"ALL-vs-by-sign required):"
    )
    # require sign-consistency between tercile spread direction and by-sign direction
    consistent = {}
    for feat, s in ranks.items():
        v = design[[feat, "trail_2R"]].dropna()
        pos, neg = v[v[feat] > 0]["trail_2R"], v[v[feat] <= 0]["trail_2R"]
        if len(pos) < 10 or len(neg) < 10:
            continue
        sign_dir = np.sign(pos.mean() - neg.mean())
        if sign_dir == np.sign(s) != 0:
            consistent[feat] = s
    top = sorted(consistent.items(), key=lambda kv: -abs(kv[1]))[:2]
    for i, (feat, s) in enumerate(top, 1):
        v = design[feat].dropna()
        hi = s > 0
        q = v.quantile(2 / 3) if hi else v.quantile(1 / 3)
        op = ">=" if hi else "<="
        keep = design[
            design[feat].notna() & ((design[feat] >= q) if hi else (design[feat] <= q))
        ]
        print(
            f"  #{i} {feat}: design tercile spread {s:+.3f}\n"
            f"     FROZEN-RULE PROPOSAL: take trade only if {feat} {op} {q:.4f}\n"
            f"     -> design meanR {keep['trail_2R'].mean():+.3f} win-rate {keep['win'].mean():.1%} "
            f"(n={len(keep)}) vs baseline {design['trail_2R'].mean():+.3f} "
            f"win-rate {design['win'].mean():.1%} (n={len(design)})"
        )
    if not top:
        print(
            "  none -- no feature shows sign-consistent tercile spread; sweep-anchored pre-trigger "
            "flow selection would be a NO-GO as constructed."
        )
    print(
        "ONE-SHOT PLAN: freeze the #1 rule verbatim, evaluate ONCE on Apr+May+Jun "
        "(features already cached), report meanR + win-rate + n. No iteration after the look."
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="3 Jan ES trading days only")
    ap.add_argument("--analyze-only", action="store_true")
    ap.add_argument(
        "--force", action="store_true", help="ignore feature cache, recompute"
    )
    args = ap.parse_args()
    if args.analyze_only:
        analyze(pd.read_parquet(CACHE))
        return
    uni = load_universe()
    nmo = pd.to_datetime(uni["trading_day"]).dt.month
    print(
        f"[universe] {len(uni)} combo trades qualify "
        f"(design Jan-Mar={int(nmo.isin(DESIGN_MONTHS).sum())}, "
        f"validation Apr-Jun={int(nmo.isin(VALID_MONTHS).sum())})"
    )
    if args.smoke:
        es_jan = uni[
            (uni["symbol"] == "ES.c.0") & (uni["trading_day"].str[:7] == "2026-01")
        ]
        days = sorted(es_jan["trading_day"].unique())[:3]
        uni = es_jan[es_jan["trading_day"].isin(days)]
        print(f"[smoke] 3 Jan ES days: {days} -> {len(uni)} trades")
    feats = build_features(uni, force=args.force)
    if args.smoke:
        cols = [
            "trading_day",
            "side",
            "wait_s",
            "trail_2R",
            "win",
            "sw_window_seconds",
            "sw_n_events",
            "sw_aggr_imb_dir",
            "sw_drift_dir_ticks",
            "sw_drift_dir_per_s",
            "l90_n_events",
            "l90_aggr_imb_dir",
            "l30_n_events",
        ]
        days = sorted(uni["trading_day"].unique())
        smoke = feats[(feats["symbol"] == "ES.c.0") & feats["trading_day"].isin(days)]
        print(smoke[cols].to_string(index=False))
    else:
        analyze(feats)


if __name__ == "__main__":
    main()
