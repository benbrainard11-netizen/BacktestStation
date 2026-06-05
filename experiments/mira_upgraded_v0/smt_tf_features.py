"""Upgraded-Mira: TIMEFRAME-SYNCHRONIZED SMT. The confirmation TF is MATCHED to the level TF (user's logic:
daily/HTF level -> confirm on 1h; prev-session/intermediate -> 15-30m). Per event x partner:
  smt_tf.<w>.<p>.mag  -- cross-index relative-strength at each ladder rung (30m/1h/4h/1d reference swing)
  smt_tf.matched.<p>  -- the rung MATCHED to this level's TF tier (HTF->1h, mid->30m)
  smt_tf.sync.<p>     -- fraction of rungs where the partner diverges (alignment across TFs)
  smt_tf.sync_all / smt_tf.tier
Self-sufficient (the d1 rung subsumes the proven basic SMT). Separate module, reads index bars READ-ONLY.

Run: backend/.venv/Scripts/python.exe smt_tf_features.py EVENTS_IN PRIMARY EVENTS_OUT
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smt_features import IDX, _load  # noqa: E402  (Bars loader, read-only)

WINDOWS = {"m30": 0.5, "h1": 1.5, "h4": 4.0, "d1": None}   # hours of lookback for the partner's swing; d1 = prior day
TIER = {"previous_rth": "htf", "previous_week": "htf", "daily_gap": "htf",
        "overnight": "mid", "premarket": "mid", "opening_range": "mid", "fvg": "mid", "wick": "mid"}
MATCH = {"htf": "h1", "mid": "m30"}                        # HTF level -> 1h confirm; mid level -> 30m (user's logic)


def build_tf_smt(events: pd.DataFrame, primary: str = "ES.c.0") -> pd.DataFrame:
    s0 = (pd.to_datetime(events["session_date"]).min() - pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    s1 = (pd.to_datetime(events["session_date"]).max() + pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    bars = {s: _load(s, s0, s1) for s in IDX}
    partners = [p for p in IDX if p != primary]
    tags = [p.split(".")[0].lower() for p in partners]
    rows = []
    for _, e in events.iterrows():
        t_touch, t_ext = pd.Timestamp(e["touch_ts_utc"]), pd.Timestamp(e["sweep.5m.sweep_extreme_ts_utc"])
        side, sd = e["smt_anchor_side"], pd.to_datetime(e["session_date"]).date()
        feat: dict = {}
        if pd.isna(t_ext) or side not in ("low", "high"):
            rows.append(feat)
            continue
        p_in = {P: bars[P].extreme(t_touch, t_ext, side)[0] for P in partners}
        for w, hrs in WINDOWS.items():
            if w == "d1":
                r0, r1 = t_touch.normalize() - pd.Timedelta(days=1), t_touch.normalize()
            else:
                r0, r1 = t_touch - pd.Timedelta(hours=hrs), t_touch
            for P, tag in zip(partners, tags):
                p_ref = bars[P].extreme(r0, r1, side)[0]
                a = bars[P].atr.get(sd, np.nan)
                if np.isfinite(p_ref) and np.isfinite(p_in[P]) and np.isfinite(a) and a > 0:
                    raw = (p_in[P] - p_ref) if side == "low" else (p_ref - p_in[P])  # >0 = partner held inside ref = diverged
                    feat[f"smt_tf.{w}.{tag}.mag"] = raw / a
        tier = TIER.get(e["level_family"], "mid")
        feat["smt_tf.tier"] = 1.0 if tier == "htf" else 0.0
        for tag in tags:
            feat[f"smt_tf.matched.{tag}"] = feat.get(f"smt_tf.{MATCH[tier]}.{tag}.mag", np.nan)
            mags = [feat[f"smt_tf.{w}.{tag}.mag"] for w in WINDOWS if f"smt_tf.{w}.{tag}.mag" in feat]
            feat[f"smt_tf.sync.{tag}"] = float(np.mean([m > 0 for m in mags])) if mags else np.nan
        syncs = [feat[f"smt_tf.sync.{tag}"] for tag in tags if np.isfinite(feat.get(f"smt_tf.sync.{tag}", np.nan))]
        feat["smt_tf.sync_all"] = float(np.mean([abs(2 * s - 1) for s in syncs])) if syncs else np.nan  # alignment strength
        rows.append(feat)
    return pd.concat([events.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def main() -> int:
    ev_in = Path(sys.argv[1])
    primary = sys.argv[2] if len(sys.argv) > 2 else "ES.c.0"
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else ev_in.with_name("events_tf_smt.parquet")
    df = build_tf_smt(pd.read_parquet(ev_in), primary)
    df.to_parquet(out)
    tf = [c for c in df.columns if c.startswith("smt_tf.")]
    print(f"events {len(df)}  +{len(tf)} TF-sync features -> {out.name}")
    print(f"  sync_all mean {df['smt_tf.sync_all'].mean():.3f}   htf-tier share {df['smt_tf.tier'].mean():.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
