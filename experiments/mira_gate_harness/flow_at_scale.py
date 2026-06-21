"""flow_at_scale.py -- FULL-POWER pre-trigger order-flow SELECTION test.

WHY: The whole campaign established that sweep-reclaim STRUCTURE reaches ~breakeven (-0.05R net,
every year, every market) and SELECTION is the entire edge. The fake Mira gate's edge was order
flow -- but POST-trigger (a look-ahead leak; see mira_parity_audit_bench). OPEN QUESTION: does
LEGAL pre-trigger order flow -- the [decision-90s, decision) MBO window -- select the winning
subset? The audited pilot (legal_flow_pilot.py) answered with only 73 trades = underpowered.
This re-runs the IDENTICAL feature + legality machinery on the bar-engine's much larger 2026 combo
trade set (~hundreds of trades), so the design analysis actually has power.

WHAT CHANGED vs the pilot (legal_flow_pilot.py):
  * UNIVERSE = runs/legal_bars_full.parquet (bar engine), not the reclaim parquets. This file has
    decision_ts_utc (bar close = the decision moment) AND entry_ts_utc (next bar open). The LEGAL
    anchor is decision_ts_utc -- the flow window ENDS AT decision, NOT entry (median gap = 60s, the
    bar duration). Using entry would leak the bar's own move into the "pre-trigger" window.
  * FILTERS: status=='entered'; |trail_2R|<=5 AND |fixed_3R|<=5 (drop near-zero-risk corrupt rows);
    the registered COMBO subset depth_tk>8 AND wait_s>=300; year(decision)==2026; the 4 index roots;
    AND the trading_day (== session_date, verified 100% identical, all RTH so no 18:00 rollover) must
    have MBO coverage at D:/data/clean/databento/mbo_trading_day (Jan-Jun 2026, 112 days/symbol).
  * Direction: side is 'high'/'low' (same as the reclaim file). A 'low' level reclaimed => long.
    dir_sign = +1 long (side=='low') / -1 short, exactly as pilot.

REUSED VERBATIM from legal_flow_pilot.py (do not "improve" -- this is the point of the re-run):
  feature defs (aggr_imb via action=='T' ONLY; near_add_imb; c2a_defend [+ near variant]; drift;
  trade_count/vol; *_dir signed by trade direction), the two-window structure (w90 burst + baseline
  for delta / rate-ratio features), and the legality assert (every MBO event ts strictly < the
  decision tick, asserted per window).

ANALYSIS: DESIGN = decision month in {Jan,Feb,Mar} 2026. VALIDATION = {Apr,May,Jun} -- features are
COMPUTED + STORED but NOT analyzed (reserved one-shot). Per feature: meanR(trail_2R) + win-rate by
tercile and by sign, design only. label win = trail_2R > 0. Print a frozen-rule proposal for the
1-2 strongest sign-consistent separators, to be evaluated ONCE on validation later.

Crash-resilient: features cached per (symbol, trading_day) to runs/flow_at_scale_features.parquet
(tmp + atomic replace per day; resumes by skipping cached symbol-days). Predicate-pushdown reads
(pyarrow.dataset on the explicit part file, ts_event filter) -- full-day reads are 25-40GB.

Run:
    backend/.venv/Scripts/python.exe experiments/mira_gate_harness/flow_at_scale.py
Smoke (3 Jan ES days):   ... flow_at_scale.py --smoke
Analyze cached only:     ... flow_at_scale.py --analyze-only
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
CACHE = RUNS / "flow_at_scale_features.parquet"
MBO_BASE = Path(r"D:\data\clean\databento\mbo_trading_day")

SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.1}
BURST_S, BASE_S = 90, 300  # burst [d-90,d) ; baseline [d-300,d-90)  (d = decision tick)
NEAR_TICKS = 4
DESIGN_MONTHS = {1, 2, 3}  # 2026; Apr/May/Jun = reserved validation, stored but NOT analyzed
VALID_MONTHS = {4, 5, 6}
SUBSET_DEPTH_TK, SUBSET_WAIT_S = 8, 300  # the registered frozen-combo deployment subset
RISK_CAP = 5.0  # |trail_2R|, |fixed_3R| <= 5 drops the near-zero-risk corrupt rows
MBO_COLS = ["ts_event", "action", "side", "price", "size"]
KEEP = [
    "symbol",
    "session_date",
    "level_family",
    "level_type",
    "side",
    "level_price",
    "decision_ts_utc",
    "entry_ts_utc",
    "depth_tk",
    "wait_s",
    "trail_2R",
    "fixed_3R",
]
ANALYSIS_FEATURES = [
    "w90_aggr_imb_dir",
    "d_aggr_imb_dir",
    "w90_near_add_imb_dir",
    "d_near_add_imb_dir",
    "w90_c2a_defend",
    "d_c2a_defend",
    "w90_c2a_defend_near",
    "d_c2a_defend_near",
    "w90_trade_count",
    "w90_vol",
    "trade_rate_ratio",
    "vol_rate_ratio",
    "w90_drift_dir_ticks",
    "d_drift_dir_ticks",
]


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


def load_universe(combo: bool = True) -> pd.DataFrame:
    df = pd.read_parquet(UNIVERSE)
    df = df[df["status"] == "entered"].copy()
    # year on the DECISION tick (the legal anchor), not entry
    yr = df["decision_ts_utc"].dt.year
    m = df["symbol"].isin(SYMBOLS) & (yr == 2026)
    m &= df["trail_2R"].abs() <= RISK_CAP
    m &= df["fixed_3R"].abs() <= RISK_CAP
    if combo:  # --all-reclaims drops this registered patience pre-filter -> ~3.6x the anchors
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
    return df.sort_values(["symbol", "trading_day", "decision_ts_utc"]).reset_index(drop=True)


def prep_day(symbol: str, trading_day: str, lo_us: int, hi_us: int) -> dict:
    # Predicate-pushdown read: features need only [min(decision)-310s, max(decision)) per day.
    # Full-day reads (25-40GB) saturate D:. ds.dataset on the explicit file does the row-group
    # pushdown with NO hive partition inference (which collides symbol dict-vs-string column).
    import pyarrow.dataset as pds

    p = MBO_BASE / f"symbol={symbol}" / f"trading_day={trading_day}" / "part-000.parquet"
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
    """Features over events with lo_us <= ts < hi_us. hi_us <= decision_us always (legality)."""
    ts = day["ts"]
    i0, i1 = np.searchsorted(ts, lo_us, "left"), np.searchsorted(ts, hi_us, "left")
    if i1 > i0:  # THE legality assert: every event strictly before the decision tick
        assert ts[i1 - 1] < decision_us, "event at/after decision leaked into pre-trigger window"
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
    return {
        "n_events": int(i1 - i0),
        "trade_count": int(is_T.sum()),
        "vol": float(buy + sell),
        "aggr_imb_dir": dir_sign * _imb(buy, sell),
        "near_add_imb_dir": dir_sign * _imb(add_nb, add_na),
        "c2a_defend": float(can_d / add_d) if add_d > 0 else np.nan,
        "c2a_defend_near": float(can_dn / add_dn) if add_dn > 0 else np.nan,
        "drift_dir_ticks": (dir_sign * (tpx[-1] - tpx[0]) / tick if len(tpx) >= 2 else np.nan),
    }


def trade_features(day: dict, row: pd.Series) -> dict:
    tick = TICK[row["symbol"]]
    dir_sign = 1 if row["side"] == "low" else -1  # low level reclaimed -> long
    # decision tick = bar close = the legal anchor. ns -> us floor; ts < decision_us => ts < decision
    decision_us = int(row["decision_ts_utc"].value // 1_000)
    w90 = window_feats(
        day,
        decision_us - BURST_S * 1_000_000,
        decision_us,
        decision_us,
        row["level_price"],
        dir_sign,
        tick,
    )
    base = window_feats(
        day,
        decision_us - BASE_S * 1_000_000,
        decision_us - BURST_S * 1_000_000,
        decision_us,
        row["level_price"],
        dir_sign,
        tick,
    )
    out = {k: row[k] for k in KEEP}
    out["trading_day"] = row["trading_day"]
    out["dir_sign"] = dir_sign
    out["win"] = bool(row["trail_2R"] > 0)
    out.update({f"w90_{k}": v for k, v in w90.items()})
    out.update({f"base_{k}": v for k, v in base.items()})
    for k in ["aggr_imb_dir", "near_add_imb_dir", "c2a_defend", "c2a_defend_near", "drift_dir_ticks"]:
        out[f"d_{k}"] = w90[k] - base[k]
    base_w = BASE_S - BURST_S
    out["trade_rate_ratio"] = (
        (w90["trade_count"] / BURST_S) / (base["trade_count"] / base_w)
        if base["trade_count"] > 0
        else np.nan
    )
    out["vol_rate_ratio"] = (
        (w90["vol"] / BURST_S) / (base["vol"] / base_w) if base["vol"] > 0 else np.nan
    )
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
            day = prep_day(sym, td, int(dec_us.min() - 310_000_000), int(dec_us.max()))
        except Exception as e:  # missing/broken day file: skip loudly, never fabricate
            print(f"  SKIP {sym} {td}: {type(e).__name__}: {e}")
            skipped.append((sym, td, len(g)))
            continue
        rows = pd.DataFrame([trade_features(day, r) for _, r in g.iterrows()])
        cached = pd.concat([cached, rows], ignore_index=True)
        tmp = CACHE.with_suffix(".tmp.parquet")  # crash-safe: tmp + atomic replace per day
        cached.to_parquet(tmp, index=False)
        tmp.replace(CACHE)
        print(
            f"  [{n}/{len(todo)}] {sym} {td}: {len(rows)} trades "
            f"(w90 ev med={rows['w90_n_events'].median():.0f})"
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
    g = v.groupby(terc).agg(meanR=("trail_2R", "mean"), win=("win", "mean"), n=("trail_2R", "count"))
    if len(g) < 3:
        print(f"    {label:<40} <3 distinct terciles, skipped")
        return None
    spread = g["meanR"].iloc[-1] - g["meanR"].iloc[0]
    cells = "  ".join(
        f"{i}={r['meanR']:+.3f}/wr{r['win']:.0%}(n={int(r['n'])})" for i, r in g.iterrows()
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
    print(
        f"\n{'-' * 100}\nCANDIDATE RULES (DESIGN-ONLY -- Jan+Feb+Mar 2026; ranked by |tercile meanR "
        f"spread|, sign-consistent ALL-vs-by-sign required):"
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
        keep = design[design[feat].notna() & ((design[feat] >= q) if hi else (design[feat] <= q))]
        print(
            f"  #{i} {feat}: design tercile spread {s:+.3f}\n"
            f"     FROZEN-RULE PROPOSAL: take trade only if {feat} {op} {q:.4f}\n"
            f"     -> design meanR {keep['trail_2R'].mean():+.3f} win-rate {keep['win'].mean():.1%} "
            f"(n={len(keep)}) vs baseline {design['trail_2R'].mean():+.3f} "
            f"win-rate {design['win'].mean():.1%} (n={len(design)})"
        )
    if not top:
        print(
            "  none -- no feature shows sign-consistent tercile spread; legal pre-trigger flow "
            "selection would be a NO-GO as constructed (consistent with the audited pilot)."
        )
    print(
        "ONE-SHOT PLAN: freeze the #1 rule verbatim, evaluate ONCE on Apr+May+Jun "
        "(features already cached), report meanR + win-rate + n. No iteration after the look."
    )


def main() -> None:
    global CACHE, UNIVERSE
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="3 Jan ES trading days only")
    ap.add_argument("--analyze-only", action="store_true")
    ap.add_argument("--force", action="store_true", help="ignore feature cache, recompute")
    ap.add_argument("--all-reclaims", action="store_true",
                    help="drop the combo patience pre-filter (~3.6x anchors); separate cache")
    ap.add_argument("--universe", default=None,
                    help="alternate universe parquet (new level families); separate cache by stem")
    args = ap.parse_args()
    if args.universe:
        UNIVERSE = Path(args.universe)
        CACHE = RUNS / f"flow_at_scale_{UNIVERSE.stem}.parquet"
    elif args.all_reclaims:
        CACHE = RUNS / "flow_at_scale_all.parquet"
    if args.analyze_only:
        analyze(pd.read_parquet(CACHE))
        return
    # --universe (new level families) implies all-reclaims, matching flow_at_zone's --universe path
    uni = load_universe(combo=not (args.all_reclaims or bool(args.universe)))
    nmo = pd.to_datetime(uni["trading_day"]).dt.month
    print(
        f"[universe] {len(uni)} combo trades qualify "
        f"(design Jan-Mar={int(nmo.isin(DESIGN_MONTHS).sum())}, "
        f"validation Apr-Jun={int(nmo.isin(VALID_MONTHS).sum())})"
    )
    if args.smoke:
        es_jan = uni[(uni["symbol"] == "ES.c.0") & (uni["trading_day"].str[:7] == "2026-01")]
        days = sorted(es_jan["trading_day"].unique())[:3]
        uni = es_jan[es_jan["trading_day"].isin(days)]
        print(f"[smoke] 3 Jan ES days: {days} -> {len(uni)} trades")
    feats = build_features(uni, force=args.force)
    if args.smoke:
        cols = [
            "trading_day",
            "side",
            "trail_2R",
            "win",
            "w90_n_events",
            "w90_aggr_imb_dir",
            "w90_near_add_imb_dir",
            "w90_c2a_defend",
            "w90_drift_dir_ticks",
            "vol_rate_ratio",
        ]
        days = sorted(uni["trading_day"].unique())
        smoke = feats[(feats["symbol"] == "ES.c.0") & feats["trading_day"].isin(days)]
        print(smoke[cols].to_string(index=False))
    else:
        analyze(feats)


if __name__ == "__main__":
    main()
