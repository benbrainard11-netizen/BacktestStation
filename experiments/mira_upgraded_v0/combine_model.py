"""CUT 1 -- does COMBINING all the data beat the SMT-only gate? (early sweep-reversal confirmation, foundation step)

We have, per event: SMT (proven), sweep-shape, 112 MBO orderflow feats, level type, + we add double-sweep context
and vol/time, + join SPX GEX. Throwing them all at one model would just overfit (~200 feats, ~2k events, 4 mirages
already). So we ABLATE: start from SMT, add one family at a time, and see which actually lifts the walk-forward
gated R. If the full stack beats SMT-only across markets -> combining adds signal (then cut 2 = push entry earlier).
If not -> SMT is the edge and the rest is noise. Honest seq_r, walk-forward, per market, day-block CI.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=RuntimeWarning)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import boot, seq_r  # noqa: E402
from smt_economics import wf_gate  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
GEX = Path(__file__).resolve().parents[1] / "options_signals_v0" / "out"
TARGET = 3.0
ASSETS = [("ES", "events_es_tf.parquet"), ("NQ", "events_nq_tf.parquet"),
          ("YM", "events_ym_tf.parquet"), ("RTY", "events_rty_tf.parquet")]


def add_double(df: pd.DataFrame) -> pd.DataFrame:
    """Double-sweep context (over ALL sweeps this session): deeper 2nd same-side grab / prior opposite-side purge."""
    d = df.sort_values("touch_ts_utc").reset_index(drop=True)
    t = pd.to_datetime(d["touch_ts_utc"]).to_numpy()
    sd = d["session_date"].astype(str).to_numpy()
    side = d["smt_anchor_side"].to_numpy()
    ext = d["sweep.5m.sweep_extreme_price"].to_numpy(float)
    n = len(d)
    manip, opp, nprior = np.zeros(n), np.zeros(n), np.zeros(n)
    for s in np.unique(sd):
        order = np.where(sd == s)[0]
        order = order[np.argsort(t[order])]
        for ii, k in enumerate(order):
            prior = order[:ii]
            if len(prior) == 0:
                continue
            dt = (t[k] - t[prior]) / np.timedelta64(1, "m")
            same = prior[(side[prior] == side[k]) & (dt > 0) & (dt <= 120)]
            if prior[(side[prior] != side[k]) & (dt > 0) & (dt <= 120)].size:
                opp[k] = 1.0
            nprior[k] = len(same)
            if len(same):
                pe = ext[same]
                deeper = (ext[k] < np.nanmin(pe)) if side[k] == "low" else (ext[k] > np.nanmax(pe))
                manip[k] = 1.0 if deeper else 0.5
    d["dbl.manip"], d["dbl.opp"], d["dbl.nprior"] = manip, opp, nprior
    return d


def add_vol(df: pd.DataFrame) -> pd.DataFrame:
    t = pd.to_datetime(df["touch_ts_utc"], utc=True).dt.tz_convert("America/New_York")
    df["vol.tod"] = t.dt.hour + t.dt.minute / 60.0
    df["vol.prior_range"] = df.get("prior_rth_range_pts", np.nan)
    df["vol.touch_vol"] = df.get("touch_bar_volume", np.nan)
    df["vol.depth"] = df.get("sweep.5m.max_through_pts", np.nan)        # sweep depth -- known at the extreme
    return df


def add_gex(df: pd.DataFrame) -> pd.DataFrame:
    p = GEX / "intraday_gex_spx.parquet"
    if not p.exists():
        return df
    g = pd.read_parquet(p)
    g["ts"] = (pd.to_datetime(g["date"].astype(int).astype(str), format="%Y%m%d")
               + pd.to_timedelta(g["ms_of_day"].astype(int), unit="ms")).astype("datetime64[ns]")
    g["gex.net"] = g["net_gex"]
    g["gex.zg_dist"] = g["spot"] - g["zero_gamma"]
    g["gex.cw_dist"] = g["spot"] - g["call_wall"]
    g["gex.pw_dist"] = g["spot"] - g["put_wall"]
    g["gex.pin_dist"] = g["spot"] - g["pin"]
    gg = g[["ts", "gex.net", "gex.zg_dist", "gex.cw_dist", "gex.pw_dist", "gex.pin_dist"]].dropna(subset=["ts"]).sort_values("ts")
    df["ts"] = pd.to_datetime(df["touch_ts_utc"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    df = df.sort_values("ts")
    return pd.merge_asof(df, gg, on="ts", direction="backward", tolerance=pd.Timedelta("15min"))


def main() -> int:
    print(f"CUT 1 -- combine ablation @ {TARGET}R, walk-forward gated OOS R [day-block CI]. Does adding each family lift SMT?\n")
    for asset, fn in ASSETS:
        if not (OUT / fn).exists():
            print(f"{asset}: missing")
            continue
        full = add_double(pd.read_parquet(OUT / fn))
        df = full[full["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].copy()
        df = add_vol(df)
        df = add_gex(df).reset_index(drop=True)
        df["day"] = pd.to_datetime(df["session_date"]).dt.date
        df["fam"] = pd.factorize(df["level_family"])[0]
        df["r"] = seq_r(df, TARGET)
        def num(pre):
            return [c for c in df.columns if c.startswith(pre) and pd.api.types.is_numeric_dtype(df[c])]
        # STRICT no-lookahead whitelist: drop forward windows (sweep.15m/60m/120m, mbo.post_*, post_extreme, y.*)
        F = {"smt": num("smt_tf."),
             "mbo": [c for c in num("mbo.") if ".pre_" in c],          # pre-event orderflow only
             "dbl": num("dbl."), "vol": num("vol."), "gex": num("gex.")}
        base = ["fam"] + F["smt"]
        steps = [("SMT", base)]
        for fam in ["mbo", "dbl", "vol", "gex"]:                        # MARGINAL: each family added to SMT alone
            steps.append((f"SMT+{fam}", base + F[fam]))
        steps.append(("SMT+ALL", base + F["mbo"] + F["dbl"] + F["vol"] + F["gex"]))
        print(f"{asset} (n={len(df)} reclaims, {len(steps[-1][1])} feats in full):")
        for lab, feats in steps:
            sel, oos, r, day = wf_gate(df, feats, TARGET, r=df["r"].to_numpy())
            if sel.sum() < 10:
                print(f"   {lab:8} thin")
                continue
            gm, gl, gh = boot(r[sel], day[sel])
            print(f"   {lab:8} {gm:+.2f} [{gl:+.2f},{gh:+.2f}]  n{int(sel.sum())}")
        print()
    print("READ: each '+family' clearly above SMT (CIs separating) across markets = combining adds signal -> cut 2 "
          "(push entry earlier). Flat/within-noise = SMT is the edge, the rest overfits. MBO is the one to watch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
