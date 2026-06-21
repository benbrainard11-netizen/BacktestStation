"""legal_flow_full.py -- pre-trigger flow RE-TEST at full power (verdict #2, 2026-06-12).

The 6/11 pilot run (legal_flow_pilot.py) died on an Arrow read bug: 179/191 symbol-days were
skipped, its "no signal" analysis saw only 73 ES trades, NO rule was frozen, and the validation
set was never read. This is the SAME registered experiment at full power, not a re-mine.

UNIVERSE: runs/legal_bars_full.parquet (the audited 12yr bar engine), status=='entered',
2026 only, |R|<=5 corrupt-row guard, FROZEN COMBO subset (depth = risk_pts/tick - 2 > 8tk
AND wait_s >= 300 -- the summarize_full_bars.py definition, night-report sec16) = 886 trades
(768 after dedup), 4 symbols ES/NQ/YM/RTY, baseline trail_2R ~= -0.03 (breakeven-minus-costs).

PROTOCOL (declared 2026-06-12 BEFORE any feature was computed on this universe):
  DESIGN     = Jan+Feb+Mar 2026 (~500 trades). Mineable.
  VALIDATION = Apr 1 - Jun 9 2026 (~386 trades). Features cached, NEVER analyzed at design time.
  Candidate bar: pooled-design tercile spread with the SAME SIGN on both symbol pools
  (ES+NQ and YM+RTY). #1 by |pooled spread| is frozen VERBATIM to
  runs/flow_full_frozen_rule.json by the design stage; --validate reads that file and takes
  the ONE look. No iteration after the look. If no candidate passes the bar -> NO-GO,
  validation never read.

FEATURES / WINDOWS / LEGALITY: identical to the pilot (imported from it) -- burst [e-90s,e),
baseline [e-300s,e-90s), every event asserted strictly before the entry decision time
(= the entry bar's open; the gate is implementable by watching flow until the bar boundary).

Run (build + design):  backend/.venv/Scripts/python.exe experiments/mira_gate_harness/legal_flow_full.py
One-shot validation:   ... legal_flow_full.py --validate
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import legal_flow_pilot as P  # noqa: E402  feature math + build loop reused verbatim

RUNS = HERE / "runs"
LEDGER = RUNS / "legal_bars_full.parquet"
FROZEN = RUNS / "flow_full_frozen_rule.json"
P.TICK.update({"YM.c.0": 1.0, "RTY.c.0": 0.10})       # pilot was ES/NQ only
P.CACHE = RUNS / "flow_full_features.parquet"          # fresh cache; pilot cache untouched
ET = ZoneInfo("America/New_York")
DESIGN_MONTHS = {1, 2, 3}
VALID_MONTHS = {4, 5, 6}
POOLS = {"ES+NQ": ("ES.c.0", "NQ.c.0"), "YM+RTY": ("YM.c.0", "RTY.c.0")}


def load_universe() -> pd.DataFrame:
    df = pd.read_parquet(LEDGER)
    df = df[df["status"] == "entered"].copy()
    df = df[(df["trail_2R"].abs() <= 5) & (df["fixed_3R"].abs() <= 5)]  # corrupt-row guard
    depth = df["risk_pts"] / df["symbol"].map(P.TICK) - 2               # summarizer combo def
    ts = pd.to_datetime(df["entry_ts_utc"], utc=True)
    df = df[(ts.dt.year == 2026) & (depth > 8) & (df["wait_s"] >= 300)]
    df = df.drop_duplicates(subset=["symbol", "entry_ts_utc", "level_price", "side"]).copy()
    et = df["entry_ts_utc"].dt.tz_convert(ET)
    df["trading_day"] = et.dt.strftime("%Y-%m-%d")  # RTH entries -> calendar date = trading day
    return df.sort_values(["symbol", "trading_day", "entry_ts_utc"]).reset_index(drop=True)


def _months(feats: pd.DataFrame, months: set[int]) -> pd.DataFrame:
    td = pd.to_datetime(feats["trading_day"])
    return feats[(td.dt.year == 2026) & td.dt.month.isin(months)].copy()


def design(feats: pd.DataFrame) -> None:
    d = _months(feats, DESIGN_MONTHS)
    n_val = len(_months(feats, VALID_MONTHS))
    print(f"\n{'=' * 100}\nDESIGN -- Jan+Feb+Mar 2026, {len(d)} combo trades "
          f"({n_val} Apr-Jun trades cached but EXCLUDED -- reserved one-shot validation).")
    print(f"baseline meanR trail_2R: pooled={d['trail_2R'].mean():+.3f} (n={len(d)})  " +
          "  ".join(f"{k}={d[d['symbol'].isin(v)]['trail_2R'].mean():+.3f}"
                    f"(n={len(d[d['symbol'].isin(v)])})" for k, v in POOLS.items()))
    ranks: dict[str, float] = {}
    for feat in P.ANALYSIS_FEATURES:
        print(f"  {feat}")
        s_all = P._bucket_table(d, feat, "DESIGN pooled")
        s_pool = [P._bucket_table(d[d["symbol"].isin(v)], feat, f"pool {k}")
                  for k, v in POOLS.items()]
        if (s_all is not None and all(s is not None for s in s_pool)
                and all(np.sign(s) == np.sign(s_all) != 0 for s in s_pool)):
            ranks[feat] = s_all
    print(f"\n{'-' * 100}\nCANDIDATES (sign-consistent pooled + both symbol pools, "
          f"ranked by |pooled tercile spread|):")
    if not ranks:
        print("  none -- NO-GO. Pre-trigger flow shows no sign-consistent separation on the "
              "honest combo stream. Validation set stays unread.")
        return
    order = sorted(ranks.items(), key=lambda kv: -abs(kv[1]))
    for feat, s in order:
        print(f"  {feat:28s} pooled spread {s:+.3f}")
    feat, s = order[0]
    v = d[feat].dropna()
    q = float(v.quantile(2 / 3) if s > 0 else v.quantile(1 / 3))
    op = ">=" if s > 0 else "<="
    keep = d[d[feat].notna() & ((d[feat] >= q) if s > 0 else (d[feat] <= q))]
    rule = {"feature": feat, "op": op, "threshold": q, "design_spread": s,
            "design_keep_meanR": float(keep["trail_2R"].mean()), "design_keep_n": len(keep),
            "design_base_meanR": float(d["trail_2R"].mean()), "design_n": len(d),
            "frozen_at": "design stage, legal_flow_full.py", "validated": False}
    FROZEN.write_text(json.dumps(rule, indent=2))
    print(f"\nFROZEN RULE #1 -> {FROZEN.name}: take trade only if {feat} {op} {q:.4f}\n"
          f"  design: kept meanR {rule['design_keep_meanR']:+.3f} (n={len(keep)}) vs "
          f"baseline {rule['design_base_meanR']:+.3f} (n={len(d)})\n"
          f"ONE-SHOT PLAN: --validate evaluates this file's rule ONCE on Apr 1 - Jun 9. "
          f"No iteration after the look.")


def validate(feats: pd.DataFrame) -> None:
    rule = json.loads(FROZEN.read_text())
    assert not rule.get("validated"), "one-shot already spent -- no second look"
    feat, op, q = rule["feature"], rule["op"], rule["threshold"]
    val = _months(feats, VALID_MONTHS)
    keep = val[val[feat].notna() & ((val[feat] >= q) if op == ">=" else (val[feat] <= q))]
    print(f"\n{'=' * 100}\nONE-SHOT VALIDATION -- Apr 1 - Jun 9 2026 ({len(val)} trades), "
          f"frozen rule: {feat} {op} {q:.4f}")
    bs = val["trail_2R"]
    ks = keep["trail_2R"]
    print(f"  baseline meanR {bs.mean():+.3f} win {100 * (bs > 0).mean():.1f}% (n={len(bs)})")
    print(f"  KEPT     meanR {ks.mean():+.3f} win {100 * (ks > 0).mean():.1f}% (n={len(ks)})  "
          f"sumR {ks.sum():+.1f}")
    for k, v in POOLS.items():
        kk = keep[keep["symbol"].isin(v)]
        print(f"    {k:7s} kept meanR {kk['trail_2R'].mean():+.3f} (n={len(kk)})")
    td = pd.to_datetime(keep["trading_day"])
    for m, g in keep.groupby(td.dt.month):
        print(f"    month {m}: meanR {g['trail_2R'].mean():+.3f} (n={len(g)})")
    rule["validated"] = True
    rule["validation_meanR"] = float(ks.mean()) if len(ks) else None
    rule["validation_n"] = len(ks)
    rule["validation_base_meanR"] = float(bs.mean())
    rule["validation_base_n"] = len(bs)
    FROZEN.write_text(json.dumps(rule, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="spend the one shot (Apr-Jun)")
    ap.add_argument("--analyze-only", action="store_true", help="design analysis from cache")
    args = ap.parse_args()
    if args.validate:
        validate(pd.read_parquet(P.CACHE))
        return
    uni = load_universe()
    print(f"[universe] {len(uni)} deduped 2026 combo trades, "
          f"{uni.groupby(['symbol', 'trading_day']).ngroups} symbol-days")
    feats = pd.read_parquet(P.CACHE) if args.analyze_only else P.build_features(uni)
    design(feats)


if __name__ == "__main__":
    main()
