"""Do Ben's FVG + Order-Block CONFIRMATIONS separate winning reclaims from losing ones?

CONTEXT
-------
Structure alone (sweep-reclaim) is breakeven across the full 12-year legal set
(runs/legal_bars_full.parquet). The hypothesized edge is the *confirmation*: after a sweep
of a level, did price actually print a bar-pattern that confirms the reclaim before we
committed at the legal anchor (decision_ts_utc = bar close)? This is a BARS-ONLY study, so
all 12 years are usable (no MBO needed).

UNIVERSE
--------
legal_bars_full.parquet, status=='entered', |trail_2R|<=5 & |fixed_3R|<=5 (drop corrupt),
the 4 index roots (ES/NQ/YM/RTY). The FULL set (all years 2015..2026), not just 2026.

CONFIRMATION FEATURES (per trade, on resampled TF bars in {1m,5m,15m,30m})
--------------------------------------------------------------------------
Only bars that CLOSED at-or-before decision_ts_utc are eligible (a TF candle floored at `t`
closes at `t + tf_min`; legal iff `t + tf_min <= decision_ts_utc`). Asserted.

 1. OB confirmation (Ben's exact rule, for a LONG that swept a low):
      - sweep candle = first TF candle (closed at/after touch) whose LOW first took the level
        (low <= level_price).
      - OB candle = that sweep candle IF it closed down (close<open); ELSE the most recent
        down-close candle strictly before the sweep candle.
      - ob_confirm = 1 if some candle that closes AT-OR-BEFORE decision closes ABOVE the OB
        candle's OPEN. Mirror for short (swept high; OB = up-close; confirm = close below OB open).
      Also record ob_confirm_dist_bars (#bars after the sweep candle that the confirm landed).
 2. FVG formed: fvg = 1 if a directional FVG formed in [touch, decision] on TF -- bullish FVG
    for a long = a 3-candle pattern candle[i-1].high < candle[i+1].low (gap up), all three
    closing at/before decision. Mirror bearish for short.
 3. TF-MATCHED versions: match confirmation TF to the level family --
      deep   (previous_rth/previous_week/prior_month) -> 15m
      mid    (overnight/opening_range/daily_gap)      ->  5m
      shallow(asia_session/london_session/premarket)  ->  1m
    Emit ob_confirm_matched, fvg_matched, and the matched-TF timing/which-tf columns.

ANALYSIS
--------
design     = ODD years (2015/17/19/21/23/25)
validation = EVEN years (2016/18/20/22/24/26) -- computed + stored but NOT analyzed (one-shot).
On DESIGN only: for each confirmation feature, meanR(trail_2R) + win-rate + n for confirmed(=1)
vs not(=0), and the lift. Which TF separates best? Does TF-matching beat a fixed TF? Print the
strongest confirmation as a FROZEN rule for the reserved one-shot validation.
Also a confirm-timing decay table (ob_confirm_dist_bars buckets).

Crash-resilient: caches per symbol-YEAR to runs/bar_confirm_parts/, concats to runs/bar_confirm.parquet.

Run (smoke):  backend/.venv/Scripts/python.exe experiments/mira_gate_harness/bar_confirmations.py --smoke
Run (full):   backend/.venv/Scripts/python.exe experiments/mira_gate_harness/bar_confirmations.py
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
PARTS = RUNS / "bar_confirm_parts"
OUT = RUNS / "bar_confirm.parquet"
UNIVERSE = RUNS / "legal_bars_full.parquet"

# reuse the proven bars loader / resampler from the smt_ltf_bench module
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
from smt_bench import load_1m, resample_tf  # noqa: E402

ROOTS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
TFS = ["1m", "5m", "15m", "30m"]
TF_MIN = {"1m": 1, "5m": 5, "15m": 15, "30m": 30}

# level family -> matched confirmation TF (deep/mid/shallow)
FAMILY_TF = {
    "previous_rth": "15m", "previous_week": "15m", "prior_month": "15m",   # deep
    "overnight": "5m", "opening_range": "5m", "daily_gap": "5m",           # mid
    "asia_session": "1m", "london_session": "1m", "premarket": "1m",       # shallow
}

DESIGN_YEARS = {2015, 2017, 2019, 2021, 2023, 2025}  # odd
ONE_NS = 1_000_000_000


# --------------------------------------------------------------------------------------
# per-TF confirmation computation for ONE trade
# --------------------------------------------------------------------------------------
def _confirm_one_tf(
    tf_bars: pd.DataFrame,
    side: str,
    level_price: float,
    touch_ns: int,
    decision_ns: int,
    tf: str,
) -> dict:
    """Compute (ob_confirm, ob_confirm_dist_bars, fvg) for a single trade on one TF.

    tf_bars: resampled bars for this symbol/window, index = floor ts (UTC ns via .asi8).
    LEGALITY: a candle floored at t closes at t + tf_min; eligible iff that close <= decision.
    """
    tf_ms = TF_MIN[tf]
    close_off = tf_ms * 60 * ONE_NS  # ns from floor-open to close

    idx_ns = tf_bars.index.asi8
    o = tf_bars["open"].to_numpy(float)
    h = tf_bars["high"].to_numpy(float)
    lo = tf_bars["low"].to_numpy(float)
    c = tf_bars["close"].to_numpy(float)
    close_ns = idx_ns + close_off  # actual close timestamp of each candle

    # eligible = candle CLOSED at-or-before decision (legality)
    legal = close_ns <= decision_ns
    if not legal.any():
        return {"ob_confirm": 0, "ob_confirm_dist_bars": np.nan, "fvg": 0,
                "ob_n_legal": 0, "ob_swept": 0}

    # ---- LEGALITY ASSERT: no candle used straddles or post-dates decision ----
    assert close_ns[legal].max() <= decision_ns, "legality violation: candle closes after decision"

    n = len(idx_ns)

    # ===== 1. OB confirmation =====
    # sweep candle = first LEGAL candle that closes at/after touch AND took the level.
    #   (we require close >= touch so the sweep is a bar that finished within [touch, decision])
    if side == "low":   # LONG: swept a low (low <= level)
        took = lo <= level_price
    else:               # SHORT: swept a high (high >= level)
        took = h >= level_price
    sweep_elig = legal & took & (close_ns >= touch_ns)
    sweep_idx = int(np.argmax(sweep_elig)) if sweep_elig.any() else -1

    ob_confirm = 0
    ob_dist = np.nan
    if sweep_idx >= 0:
        # OB candle = sweep candle if it closed in the OB direction, else most recent such candle before.
        if side == "low":
            down_close = c < o   # OB for a long = a DOWN-close candle (supply absorbed on the sweep)
        else:
            down_close = c > o   # OB for a short = an UP-close candle
        if down_close[sweep_idx]:
            ob_idx = sweep_idx
        else:
            prev = np.where(down_close[:sweep_idx])[0]
            ob_idx = int(prev[-1]) if len(prev) else -1
        if ob_idx >= 0:
            ob_open = o[ob_idx]
            # confirm = some LEGAL candle (at/after sweep candle) closes beyond the OB open.
            # scan candles from sweep_idx..last-legal; pick first confirming close.
            last_legal = int(np.where(legal)[0][-1])
            for j in range(sweep_idx, last_legal + 1):
                if not legal[j]:
                    continue
                if side == "low":
                    hit = c[j] > ob_open
                else:
                    hit = c[j] < ob_open
                if hit:
                    ob_confirm = 1
                    ob_dist = j - sweep_idx
                    break

    # ===== 2. FVG formed in [touch, decision] on this TF =====
    # bullish (long): candle[i-1].high < candle[i+1].low, all 3 legal & closing in [touch, decision].
    fvg = 0
    last_legal_i = int(np.where(legal)[0][-1]) if legal.any() else -1
    if last_legal_i >= 2:
        for i in range(1, last_legal_i):  # i is the middle candle; needs i-1,i,i+1
            i1, i3 = i - 1, i + 1
            if i3 > last_legal_i:
                break
            # all three legal AND the 3-candle pattern completes within [touch, decision]
            if not (legal[i1] and legal[i] and legal[i3]):
                continue
            if close_ns[i3] < touch_ns:   # pattern must complete at/after the touch
                continue
            if side == "low":
                if h[i1] < lo[i3]:        # gap up
                    fvg = 1
                    break
            else:
                if lo[i1] > h[i3]:        # gap down
                    fvg = 1
                    break

    return {"ob_confirm": ob_confirm, "ob_confirm_dist_bars": ob_dist, "fvg": fvg,
            "ob_n_legal": int(legal.sum()), "ob_swept": int(sweep_idx >= 0)}


# --------------------------------------------------------------------------------------
# one symbol-year part
# --------------------------------------------------------------------------------------
def build_symbol_year(uni: pd.DataFrame, symbol: str, year: int, verbose: bool = False) -> pd.DataFrame:
    trades = uni[(uni["symbol"] == symbol) & (uni["_year"] == year)].copy()
    if trades.empty:
        return pd.DataFrame()

    # load 1m bars padded so the sweep candle's full TF window + a small lead-in are present.
    # pad lo by 2 days (catches multi-day-old level reclaims via prior down-close OB candle search)
    start = f"{year - (1 if year == 2015 else 0)}-12-25" if False else f"{year}-01-01"
    # simpler: pad with prior ~3 days; load whole calendar year +- buffer
    lo_start = (pd.Timestamp(f"{year}-01-01", tz="UTC") - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
    hi_end = f"{year}-12-31"
    bars1m = load_1m(symbol, lo_start, hi_end)
    if bars1m.empty:
        if verbose:
            print(f"    {symbol} {year}: NO BARS, skip ({len(trades)} trades dropped)", flush=True)
        return pd.DataFrame()

    # pre-resample each TF once for the whole year
    tf_frames = {tf: resample_tf(bars1m, TF_MIN[tf]) for tf in TFS}
    tf_idx_ns = {tf: tf_frames[tf].index.asi8 for tf in TFS}

    out_rows = []
    for _, t in trades.iterrows():
        touch_ns = int(t["touch_ts_utc"].value)
        decision_ns = int(t["decision_ts_utc"].value)
        side = t["side"]
        lvl = float(t["level_price"])
        fam = t["level_family"]
        matched_tf = FAMILY_TF.get(fam)

        row = {
            "symbol": symbol, "year": year, "session_date": t["session_date"],
            "level_family": fam, "level_type": t["level_type"], "side": side,
            "level_price": lvl, "touch_ts_utc": t["touch_ts_utc"],
            "decision_ts_utc": t["decision_ts_utc"], "trail_2R": float(t["trail_2R"]),
            "fixed_3R": float(t["fixed_3R"]), "matched_tf": matched_tf,
        }

        # slice each TF to a small window around the trade for speed:
        # candles with close in [touch - 6h, decision]; the OB prior-down-close search needs lead-in.
        win_lo = touch_ns - 6 * 3600 * ONE_NS
        for tf in TFS:
            tf_ms = TF_MIN[tf]
            close_off = tf_ms * 60 * ONE_NS
            close_ns = tf_idx_ns[tf] + close_off
            sel = (close_ns >= win_lo) & (close_ns <= decision_ns)
            sub = tf_frames[tf].iloc[sel]
            r = _confirm_one_tf(sub, side, lvl, touch_ns, decision_ns, tf)
            row[f"ob_confirm_{tf}"] = r["ob_confirm"]
            row[f"ob_confirm_dist_bars_{tf}"] = r["ob_confirm_dist_bars"]
            row[f"fvg_{tf}"] = r["fvg"]

        # matched-TF confirmations (already computed above; just project)
        if matched_tf is not None:
            row["ob_confirm_matched"] = row[f"ob_confirm_{matched_tf}"]
            row["ob_confirm_dist_bars_matched"] = row[f"ob_confirm_dist_bars_{matched_tf}"]
            row["fvg_matched"] = row[f"fvg_{matched_tf}"]
        else:
            row["ob_confirm_matched"] = np.nan
            row["ob_confirm_dist_bars_matched"] = np.nan
            row["fvg_matched"] = np.nan
        out_rows.append(row)

    return pd.DataFrame(out_rows)


# --------------------------------------------------------------------------------------
# universe load
# --------------------------------------------------------------------------------------
def load_universe(smoke: bool) -> pd.DataFrame:
    df = pd.read_parquet(UNIVERSE)
    df = df[df["status"] == "entered"].copy()
    df = df[df["symbol"].isin(ROOTS)]
    df = df[(df["trail_2R"].abs() <= 5) & (df["fixed_3R"].abs() <= 5)]
    df = df[df["level_family"].isin(FAMILY_TF.keys())]  # all 9 families covered; defensive
    df["_year"] = pd.to_datetime(df["session_date"]).dt.year
    df = df.dropna(subset=["touch_ts_utc", "decision_ts_utc"])
    # touch must precede decision (sanity)
    df = df[df["touch_ts_utc"] <= df["decision_ts_utc"]]
    if smoke:
        df = df[(df["symbol"] == "ES.c.0") & (df["_year"] == 2019)]
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------------------
# build (with per symbol-year caching)
# --------------------------------------------------------------------------------------
def build(smoke: bool, rebuild: bool) -> pd.DataFrame:
    PARTS.mkdir(parents=True, exist_ok=True)
    uni = load_universe(smoke)
    print(f"universe (entered, clean, 4 roots): {len(uni)} trades", flush=True)
    pairs = sorted(uni.groupby(["symbol", "_year"]).size().index.tolist())
    print(f"symbol-year parts: {len(pairs)}", flush=True)

    t0 = time.time()
    parts = []
    for symbol, year in pairs:
        tag = "smoke_" if smoke else ""
        part_path = PARTS / f"{tag}{symbol.replace('.', '_')}_{year}.parquet"
        if part_path.exists() and not rebuild:
            parts.append(pd.read_parquet(part_path))
            print(f"  cached  {symbol} {year}", flush=True)
            continue
        df = build_symbol_year(uni, symbol, int(year), verbose=True)
        if not df.empty:
            df.to_parquet(part_path, index=False)
            parts.append(df)
        n = len(df)
        print(f"  built   {symbol} {year}: {n} rows ({time.time()-t0:.0f}s)", flush=True)

    if not parts:
        raise SystemExit("no parts built")
    full = pd.concat(parts, ignore_index=True)
    out_path = RUNS / ("bar_confirm_smoke.parquet" if smoke else "bar_confirm.parquet")
    full.to_parquet(out_path, index=False)
    print(f"\nwrote {out_path}  ({len(full)} rows)", flush=True)
    return full


# --------------------------------------------------------------------------------------
# analysis (DESIGN years only)
# --------------------------------------------------------------------------------------
def _feat_split(df: pd.DataFrame, feat: str) -> dict | None:
    sub = df.dropna(subset=[feat, "trail_2R"])
    if sub.empty:
        return None
    yes = sub[sub[feat] == 1]
    no = sub[sub[feat] == 0]
    if len(yes) == 0 or len(no) == 0:
        return {"feature": feat, "n_yes": len(yes), "n_no": len(no),
                "meanR_yes": np.nan, "meanR_no": np.nan, "lift_R": np.nan,
                "win_yes": np.nan, "win_no": np.nan, "lift_win": np.nan,
                "rate_confirmed": round(len(yes) / len(sub), 3)}
    return {
        "feature": feat, "n_yes": len(yes), "n_no": len(no),
        "meanR_yes": round(yes["trail_2R"].mean(), 4),
        "meanR_no": round(no["trail_2R"].mean(), 4),
        "lift_R": round(yes["trail_2R"].mean() - no["trail_2R"].mean(), 4),
        "win_yes": round((yes["trail_2R"] > 0).mean(), 3),
        "win_no": round((no["trail_2R"] > 0).mean(), 3),
        "lift_win": round((yes["trail_2R"] > 0).mean() - (no["trail_2R"] > 0).mean(), 3),
        "rate_confirmed": round(len(yes) / len(sub), 3),
    }


def analyze(full: pd.DataFrame) -> None:
    design = full[full["year"].isin(DESIGN_YEARS)].copy()
    valid = full[~full["year"].isin(DESIGN_YEARS)].copy()
    print("\n" + "=" * 92)
    print(f"ANALYSIS — DESIGN (odd years) n={len(design)} | validation (even, RESERVED) n={len(valid)}")
    print("=" * 92)
    print(f"DESIGN years present: {sorted(design['year'].unique())}")
    print(f"baseline (all design): meanR={design['trail_2R'].mean():.4f}  "
          f"win={ (design['trail_2R']>0).mean():.3f}  n={len(design)}")

    feats = [f"ob_confirm_{tf}" for tf in TFS] + [f"fvg_{tf}" for tf in TFS] + \
            ["ob_confirm_matched", "fvg_matched"]
    rows = [r for f in feats if (r := _feat_split(design, f)) is not None]
    rep = pd.DataFrame(rows)
    pd.set_option("display.width", 220); pd.set_option("display.max_columns", None)
    print("\n--- confirmation vs outcome (DESIGN only) ---")
    print(rep.to_string(index=False))

    # which TF separates best (by R-lift), OB and FVG separately
    ob = rep[rep["feature"].str.startswith("ob_confirm_") & rep["feature"].str.contains("m")]
    fv = rep[rep["feature"].str.startswith("fvg_") & rep["feature"].str.contains("m")]
    print("\n--- best separating TF (by lift_R) ---")
    for name, grp in [("OB", ob), ("FVG", fv)]:
        g = grp.dropna(subset=["lift_R"])
        if len(g):
            b = g.loc[g["lift_R"].idxmax()]
            print(f"  {name}: {b['feature']}  lift_R={b['lift_R']:+.4f}  "
                  f"(yes {b['meanR_yes']:+.3f} n{int(b['n_yes'])} vs no {b['meanR_no']:+.3f} n{int(b['n_no'])})")

    # does TF-matching beat the fixed TFs?
    m_ob = rep[rep["feature"] == "ob_confirm_matched"]
    m_fv = rep[rep["feature"] == "fvg_matched"]
    print("\n--- TF-matched vs fixed (lift_R) ---")
    if len(m_ob):
        ob_fix = ob.dropna(subset=["lift_R"])["lift_R"].max() if len(ob.dropna(subset=["lift_R"])) else np.nan
        print(f"  OB  matched lift_R={float(m_ob['lift_R'].iloc[0]):+.4f}  vs best fixed {ob_fix:+.4f}")
    if len(m_fv):
        fv_fix = fv.dropna(subset=["lift_R"])["lift_R"].max() if len(fv.dropna(subset=["lift_R"])) else np.nan
        print(f"  FVG matched lift_R={float(m_fv['lift_R'].iloc[0]):+.4f}  vs best fixed {fv_fix:+.4f}")

    # strongest confirmation overall -> frozen rule
    best = rep.dropna(subset=["lift_R"]).sort_values("lift_R", ascending=False)
    if len(best):
        b = best.iloc[0]
        print("\n" + "=" * 92)
        print("FROZEN RULE for reserved one-shot (validation = even years; DO NOT analyze yet):")
        print(f"  feature = {b['feature']}")
        print(f"  DESIGN edge: meanR_confirmed={b['meanR_yes']:+.4f} (n={int(b['n_yes'])}) "
              f"vs not={b['meanR_no']:+.4f} (n={int(b['n_no'])}); lift_R={b['lift_R']:+.4f}, "
              f"lift_win={b['lift_win']:+.3f}, confirm_rate={b['rate_confirmed']}")
        print("=" * 92)

    # confirm-timing decay (OB) on the matched feature, DESIGN only
    print("\n--- OB confirm-timing decay (DESIGN, ob_confirm_dist_bars_matched) ---")
    dd = design.dropna(subset=["ob_confirm_dist_bars_matched"]).copy()
    if len(dd):
        dd["bucket"] = pd.cut(dd["ob_confirm_dist_bars_matched"],
                              bins=[-0.5, 0.5, 1.5, 2.5, 4.5, 8.5, 1e9],
                              labels=["0", "1", "2", "3-4", "5-8", "9+"])
        tab = dd.groupby("bucket").agg(n=("trail_2R", "size"),
                                       meanR=("trail_2R", "mean"),
                                       win=("trail_2R", lambda s: (s > 0).mean()))
        tab["meanR"] = tab["meanR"].round(4); tab["win"] = tab["win"].round(3)
        print(tab.to_string())
        # compare to no-confirm
        nc = design[design["ob_confirm_matched"] == 0]
        print(f"  (no OB confirm: meanR={nc['trail_2R'].mean():+.4f} n={len(nc)})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="ES 2019 only")
    ap.add_argument("--rebuild", action="store_true", help="ignore cached parts")
    ap.add_argument("--analyze-only", action="store_true",
                    help="skip build; load existing bar_confirm[_smoke].parquet and analyze")
    args = ap.parse_args()

    if args.analyze_only:
        p = RUNS / ("bar_confirm_smoke.parquet" if args.smoke else "bar_confirm.parquet")
        full = pd.read_parquet(p)
        print(f"loaded {p} ({len(full)} rows)")
    else:
        full = build(args.smoke, args.rebuild)

    # confirm-rate sanity (always)
    print("\n--- confirmation rates (sanity, ALL years in this run) ---")
    san = []
    for f in [f"ob_confirm_{tf}" for tf in TFS] + [f"fvg_{tf}" for tf in TFS] + \
             ["ob_confirm_matched", "fvg_matched"]:
        s = full[f].dropna()
        san.append({"feature": f, "n": len(s), "rate_1": round(float(s.mean()), 3) if len(s) else np.nan})
    print(pd.DataFrame(san).to_string(index=False))

    analyze(full)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
