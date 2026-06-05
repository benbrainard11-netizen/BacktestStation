"""TF-synchronized SMT across all 4 assets. For each primary: build TF-SMT, then gate two ways @3R walk-forward:
  daily-only  -- just the d1 ladder rung (~ the proven basic SMT)
  TF-sync     -- full ladder (30m/1h/4h/1d) + tier-matched rung + sync score
Does matching the confirmation TF to the level TF (+ cross-TF alignment) BEAT daily-only? Needs events_<tag>_*full.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import boot  # noqa: E402
from smt_economics import wf_gate  # noqa: E402
from smt_tf_features import build_tf_smt  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
PRIM = [("es", "ES.c.0", "events_es_fvgwick_full.parquet"), ("nq", "NQ.c.0", "events_nq_fw_full.parquet"),
        ("ym", "YM.c.0", "events_ym_fw_full.parquet"), ("rty", "RTY.c.0", "events_rty_fw_full.parquet")]
TARGET = 3.0


def main() -> int:
    print(f"TF-synchronized SMT @ {TARGET}R -- daily-only vs full TF-sync gate (walk-forward pooled OOS):")
    for tag, sym, fn in PRIM:
        reg = OUT / fn
        if not reg.exists():
            print(f"   {tag.upper():4} {fn} missing -- skip")
            continue
        tfp = OUT / f"events_{tag}_tf.parquet"
        if tfp.exists():
            df = pd.read_parquet(tfp)
        else:
            df = build_tf_smt(pd.read_parquet(reg), sym)
            df.to_parquet(tfp)
        df["day"] = pd.to_datetime(df["session_date"]).dt.date
        df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].reset_index(drop=True)
        df["fam"] = pd.factorize(df["level_family"])[0]
        daily = [c for c in df.columns if c.startswith("smt_tf.d1.")] + ["fam"]
        tf = [c for c in df.columns if c.startswith("smt_tf.")] + ["fam"]
        s1, _, r1, d1 = wf_gate(df, daily, TARGET)
        s2, _, r2, d2 = wf_gate(df, tf, TARGET)
        m1, l1, h1 = boot(r1[s1], d1[s1])
        m2, l2, h2 = boot(r2[s2], d2[s2])
        flag = "  <== clears 0" if l2 > 0 else ""
        delta = m2 - m1
        print(f"   {tag.upper():4} daily {m1:+.2f}[{l1:+.2f},{h1:+.2f}]   TF-sync {m2:+.2f}[{l2:+.2f},{h2:+.2f}]"
              f"  (Δ{delta:+.2f}){flag}")
    print("\nREAD: TF-sync clearly > daily-only across assets = matching confirmation TF to level TF adds real signal.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
