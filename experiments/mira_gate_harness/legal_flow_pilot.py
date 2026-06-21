"""legal_flow_pilot.py -- does PRE-TRIGGER order flow separate winners from losers?

WHY: both invalidated systems used POST-decision features. This pilot uses MBO windows that end
STRICTLY BEFORE the entry decision tick -- legal by construction (asserted per window).

UNIVERSE: runs/legal_reclaim_jan.parquet + runs/legal_reclaim_train.parquet, status=='entered'
(honest past-anchored reclaim trades, ES.c.0+NQ.c.0, Jan-May 2026). Long = side=='low'.

WINDOWS (per trade, entry_ts = decision tick):
  burst    [entry-90s,  entry)   -- the flow right before the trigger
  baseline [entry-300s, entry-90s) -- prior norm, for burst-relative (delta / rate-ratio) features
Every event in both windows is asserted ts_event < entry_ts.

FEATURES (clean MBO trading days, docs/MBO_TRADING_DAY_CONTRACT.md):
  1. aggr_imb        (buyVol-sellVol)/totalVol over action=='T' ONLY. Databento GLBX: T side =
                     AGGRESSOR; F side = RESTING order side, so adding F would double-count volume
                     AND flip the sign (verified in data: T vol 1.51M ~= F vol 1.53M on 2026-01-02).
  2. near_add_imb    add (A) size within NEAR_TICKS of level_price, bid-side minus ask-side, / total
  3. c2a_defend      cancel size / add size on the book side defending the trade (long: bid).
                     Whole-window + a near-level variant (far book is full of junk-price resting
                     algo orders -- A prices span 1.0..69103 on an ES day).
  4. trade_count, vol  activity level (T events)
  5. drift_dir_ticks (last T px - first T px)/tick, signed toward trade direction (+ = with trade)
  _dir features are multiplied by dir_sign (+1 long / -1 short) so + always = supportive of trade.
  M (modify) events ignored everywhere (partial cancels via M are out of pilot scope).

ANALYSIS: DESIGN MONTHS = Jan+Feb+Mar 2026 ONLY. Apr/May features are computed + stored but NEVER
analyzed here -- they are the reserved one-shot validation set. Per feature: trail_2R meanR by
tercile and by sign, overall and within the frozen-combo subset (risk>8 ticks & wait>=300s).
Candidates ranked by tercile spread on the SUBSET with sign-agreement on ALL required.

Resume: cache at runs/flow_pilot_features.parquet, per (symbol, trading_day) groups (box crashes).

Run (full build + design analysis):
    backend/.venv/Scripts/python.exe experiments/mira_gate_harness/legal_flow_pilot.py
Smoke (3 Jan ES days):            ... legal_flow_pilot.py --smoke
Analyze cached features only:     ... legal_flow_pilot.py --analyze-only
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.data import read_mbo_trading_day  # noqa: E402

RUNS = HERE / "runs"
CACHE = RUNS / "flow_pilot_features.parquet"
UNIVERSE_FILES = ["legal_reclaim_jan.parquet", "legal_reclaim_train.parquet"]
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25}
ET = ZoneInfo("America/New_York")
BURST_S, BASE_S = 90, 300  # burst [e-90,e) ; baseline [e-300,e-90)
NEAR_TICKS = 4
DESIGN_MONTHS = {
    1,
    2,
    3,
}  # 2026; Apr/May = reserved validation, stored but NOT analyzed
SUBSET_RISK_TICKS, SUBSET_WAIT_S = 8, 300  # the frozen-combo deployment subset
MBO_COLS = ["ts_event", "action", "side", "price", "size"]
KEEP = [
    "symbol",
    "level_family",
    "level_type",
    "level_price",
    "side",
    "entry_ts_utc",
    "risk_pts",
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


def load_universe() -> pd.DataFrame:
    parts = [pd.read_parquet(RUNS / f) for f in UNIVERSE_FILES]
    df = pd.concat(parts, ignore_index=True)
    df = df[df["status"] == "entered"].copy()
    df = df.drop_duplicates(subset=["symbol", "entry_ts_utc", "level_price", "side"])
    et = df["entry_ts_utc"].dt.tz_convert(ET)
    td = et.dt.normalize() + pd.to_timedelta((et.dt.hour >= 18).astype(int), unit="D")
    df["trading_day"] = td.dt.strftime("%Y-%m-%d")
    return df.sort_values(["symbol", "trading_day", "entry_ts_utc"]).reset_index(
        drop=True
    )


def prep_day(symbol: str, trading_day: str, lo_us: int | None = None, hi_us: int | None = None) -> dict:
    # Predicate-pushdown read: the features only need [min(entry)-310s, max(entry)) per day.
    # Full-day reads (25-40GB) were ~35min/day and saturated D: (starved the archive pull).
    if lo_us is not None:
        import pyarrow.dataset as pds

        p = (Path(r"D:\data\clean\databento\mbo_trading_day") / f"symbol={symbol}"
             / f"trading_day={trading_day}" / "part-000.parquet")
        ts_lo = pd.Timestamp(lo_us, unit="us", tz="UTC")
        ts_hi = pd.Timestamp(hi_us, unit="us", tz="UTC")
        # pq.read_table(file, filters=...) infers hive partitioning from the PATH, and the
        # inferred `symbol` field (dictionary) collides with the file's physical string column
        # (ArrowTypeError) -- this killed 179/191 days of the 6/11 run. ds.dataset on the
        # explicit file does the same row-group pushdown with no partition inference.
        df = pds.dataset(p).to_table(
            columns=MBO_COLS,
            filter=(pds.field("ts_event") >= ts_lo) & (pds.field("ts_event") < ts_hi),
        ).to_pandas()
    else:
        df = read_mbo_trading_day(symbol=symbol, trading_day=trading_day, columns=MBO_COLS)
    ts = (
        df["ts_event"].astype("int64").to_numpy()
    )  # microseconds since epoch (us dtype)
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
    entry_us: int,
    level_px: float,
    dir_sign: int,
    tick: float,
) -> dict:
    """Features over events with lo_us <= ts < hi_us. hi_us <= entry_us always (legality)."""
    ts = day["ts"]
    i0, i1 = np.searchsorted(ts, lo_us, "left"), np.searchsorted(ts, hi_us, "left")
    if (
        i1 > i0
    ):  # THE legality assert: every event strictly before the entry decision tick
        assert (
            ts[i1 - 1] < entry_us
        ), "event at/after entry leaked into pre-trigger window"
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
        "drift_dir_ticks": (
            dir_sign * (tpx[-1] - tpx[0]) / tick if len(tpx) >= 2 else np.nan
        ),
    }


def trade_features(day: dict, row: pd.Series) -> dict:
    tick = TICK[row["symbol"]]
    dir_sign = 1 if row["side"] == "low" else -1  # low level reclaimed -> long
    entry_us = int(
        row["entry_ts_utc"].value // 1_000
    )  # ns -> us floor; ts<entry_us => ts<entry
    w90 = window_feats(
        day,
        entry_us - BURST_S * 1_000_000,
        entry_us,
        entry_us,
        row["level_price"],
        dir_sign,
        tick,
    )
    base = window_feats(
        day,
        entry_us - BASE_S * 1_000_000,
        entry_us - BURST_S * 1_000_000,
        entry_us,
        row["level_price"],
        dir_sign,
        tick,
    )
    out = {k: row[k] for k in KEEP}
    out["trading_day"] = row["trading_day"]
    out.update({f"w90_{k}": v for k, v in w90.items()})
    out.update({f"base_{k}": v for k, v in base.items()})
    for k in [
        "aggr_imb_dir",
        "near_add_imb_dir",
        "c2a_defend",
        "c2a_defend_near",
        "drift_dir_ticks",
    ]:
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
            ent_us = (g["entry_ts_utc"].astype("int64") // 1_000)
            day = prep_day(sym, td, int(ent_us.min() - 310_000_000), int(ent_us.max()))
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
            f"(w90 ev med={rows['w90_n_events'].median():.0f})"
        )
    if skipped:
        print(
            f"[build] WARNING: skipped {len(skipped)} symbol-days "
            f"({sum(s[2] for s in skipped)} trades): {skipped}"
        )
    return cached


def _bucket_table(d: pd.DataFrame, feat: str, label: str) -> float | None:
    """Print meanR(trail_2R) by tercile + sign for one feature; return top-bottom spread."""
    v = d[[feat, "trail_2R"]].dropna()
    if len(v) < 30:
        print(f"    {label:<42} n={len(v)} (too few, skipped)")
        return None
    try:
        terc = pd.qcut(v[feat], 3, labels=["T1_lo", "T2", "T3_hi"], duplicates="drop")
    except ValueError:
        print(f"    {label:<42} degenerate distribution, skipped")
        return None
    g = v.groupby(terc)["trail_2R"].agg(["mean", "count"])
    if len(g) < 3:
        print(f"    {label:<42} <3 distinct terciles, skipped")
        return None
    spread = g["mean"].iloc[-1] - g["mean"].iloc[0]
    cells = "  ".join(
        f"{i}={r['mean']:+.3f}(n={int(r['count'])})" for i, r in g.iterrows()
    )
    pos, neg = v[v[feat] > 0]["trail_2R"], v[v[feat] <= 0]["trail_2R"]
    sign = (
        f"  sign: >0={pos.mean():+.3f}(n={len(pos)}) <=0={neg.mean():+.3f}(n={len(neg)})"
        if len(pos) >= 10 and len(neg) >= 10
        else ""
    )
    print(f"    {label:<42} {cells}  spread={spread:+.3f}{sign}")
    return float(spread)


def analyze(feats: pd.DataFrame) -> None:
    td = pd.to_datetime(feats["trading_day"])
    design = feats[(td.dt.year == 2026) & td.dt.month.isin(DESIGN_MONTHS)].copy()
    held = len(feats) - len(design)
    print(
        f"\n{'=' * 100}\nANALYSIS -- DESIGN MONTHS Jan+Feb+Mar 2026 ONLY ({len(design)} trades). "
        f"{held} Apr/May trades stored but EXCLUDED (reserved one-shot validation)."
    )
    risk_ticks = design["risk_pts"] / design["symbol"].map(TICK)
    sub = design[(risk_ticks > SUBSET_RISK_TICKS) & (design["wait_s"] >= SUBSET_WAIT_S)]
    print(
        f"baseline meanR trail_2R: ALL={design['trail_2R'].mean():+.3f} (n={len(design)})   "
        f"SUBSET depth>{SUBSET_RISK_TICKS}tk+wait>={SUBSET_WAIT_S}s="
        f"{sub['trail_2R'].mean():+.3f} (n={len(sub)})"
    )
    ranks = {}
    for feat in ANALYSIS_FEATURES:
        print(f"  {feat}")
        s_all = _bucket_table(design, feat, "ALL design")
        s_sub = _bucket_table(
            sub, feat, f"SUBSET depth>{SUBSET_RISK_TICKS}tk wait>={SUBSET_WAIT_S}s"
        )
        if (
            s_all is not None
            and s_sub is not None
            and np.sign(s_all) == np.sign(s_sub) != 0
        ):
            ranks[feat] = (s_sub, s_all)
    print(
        f"\n{'-' * 100}\nCANDIDATE RULES (DESIGN-ONLY -- Jan+Feb+Mar; ranked by |subset tercile "
        f"spread|, sign-agreement ALL vs SUBSET required):"
    )
    top = sorted(ranks.items(), key=lambda kv: -abs(kv[1][0]))[:2]
    for i, (feat, (s_sub, s_all)) in enumerate(top, 1):
        v = sub[feat].dropna()
        q = v.quantile(2 / 3) if s_sub > 0 else v.quantile(1 / 3)
        op = ">=" if s_sub > 0 else "<="
        keep = sub[
            sub[feat].notna() & (sub[feat] >= q if s_sub > 0 else sub[feat] <= q)
        ]
        print(
            f"  #{i} {feat}: subset spread {s_sub:+.3f} (all {s_all:+.3f})\n"
            f"     FROZEN-RULE PROPOSAL: take trade only if {feat} {op} {q:.4f} "
            f"(design subset tercile edge) -> design-subset meanR {keep['trail_2R'].mean():+.3f} "
            f"(n={len(keep)}) vs baseline {sub['trail_2R'].mean():+.3f} (n={len(sub)})"
        )
    if not top:
        print(
            "  none -- no feature shows sign-consistent tercile spread; pre-trigger flow pilot "
            "would be a NO-GO as constructed."
        )
    print(
        "ONE-SHOT PLAN: freeze the #1 rule verbatim, evaluate ONCE on Apr/May "
        "(features already cached), report meanR + n. No iteration after the look."
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
            "trail_2R",
            "w90_n_events",
            "w90_aggr_imb_dir",
            "w90_near_add_imb_dir",
            "w90_c2a_defend",
            "w90_drift_dir_ticks",
            "d_aggr_imb_dir",
            "vol_rate_ratio",
        ]
        smoke = feats[(feats["symbol"] == "ES.c.0") & feats["trading_day"].isin(days)]
        print(smoke[cols].to_string(index=False))
    else:
        analyze(feats)


if __name__ == "__main__":
    main()
