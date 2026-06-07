"""Does rebuilding the gate around CONFIRMATION beat the current magnitude gate, OUT OF SAMPLE?

We found the SMT edge is really a confirmation/flush effect. The current gate feeds the raw signed magnitudes
(smt_tf.*). Here we engineer confirmation-centric features and pit three walk-forward gates against each other on
all 4 markets:
  CURRENT  = smt_tf.* (today's gate: raw magnitudes + matched/sync/tier)
  CONFIRM  = engineered confirmation features only (how many cousins confirmed, collective flush depth, breadth)
  BOTH     = current + confirmation
CONFIRM/BOTH clearly > CURRENT OOS -> the reframe improves the edge. Equal -> the gate already captured it (the
finding is interpretation, not extra alpha). Honest sequenced R, day-block CI. Reads events_<asset>_tf.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=RuntimeWarning)   # nanmean/nanmin on all-NaN rows -> NaN (trees handle it)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import boot, seq_r  # noqa: E402
from smt_economics import wf_gate  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
TARGET = 3.0
ASSETS = [("ES", "events_es_tf.parquet"), ("NQ", "events_nq_tf.parquet"),
          ("YM", "events_ym_tf.parquet"), ("RTY", "events_rty_tf.parquet")]
RUNGS = ["m30", "h1", "h4", "d1"]


def add_confirm(df: pd.DataFrame) -> pd.DataFrame:
    """Confirmation-centric features from the existing per-cousin magnitudes (mag<0 = cousin took its level)."""
    allmag = [c for c in df.columns if c.startswith("smt_tf.") and c.endswith(".mag")]
    for w in RUNGS:
        cols = [c for c in df.columns if c.startswith(f"smt_tf.{w}.") and c.endswith(".mag")]
        if not cols:
            continue
        M = df[cols].to_numpy(float)
        df[f"conf.nconf_{w}"] = (M < 0).sum(axis=1)                         # cousins that confirmed at this rung
        df[f"conf.flush_{w}"] = np.nanmean(M, axis=1)                       # collective depth (negative = flush)
        df[f"conf.minmag_{w}"] = np.nanmin(M, axis=1)                       # deepest single confirmation
    Mall = df[allmag].to_numpy(float)
    df["conf.breadth"] = (Mall < 0).mean(axis=1)                           # fraction of all cells confirmed
    df["conf.flush_all"] = np.nanmean(Mall, axis=1)
    d1 = [c for c in df.columns if c.startswith("smt_tf.d1.") and c.endswith(".mag")]
    df["conf.allconf_d1"] = (~(df[d1].to_numpy(float) > 0)).all(axis=1).astype(float)   # none held = all confirmed
    return df


def main() -> int:
    print(f"CONFIRMATION-rebuilt gate vs CURRENT gate @ {TARGET}R -- walk-forward OOS gated R [day-block CI]:\n")
    for asset, fn in ASSETS:
        if not (OUT / fn).exists():
            print(f"{asset}: {fn} missing -- skip")
            continue
        df = pd.read_parquet(OUT / fn)
        df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].reset_index(drop=True)
        df["day"] = pd.to_datetime(df["session_date"]).dt.date
        df["fam"] = pd.factorize(df["level_family"])[0]
        df["r"] = seq_r(df, TARGET)
        df = add_confirm(df)
        cur = [c for c in df.columns if c.startswith("smt_tf.")] + ["fam"]
        conf = [c for c in df.columns if c.startswith("conf.")] + ["fam"]
        both = [c for c in df.columns if c.startswith(("smt_tf.", "conf."))] + ["fam"]
        line = f"{asset}:"
        for lab, feats in [("CURRENT", cur), ("CONFIRM", conf), ("BOTH", both)]:
            sel, oos, r, day = wf_gate(df, feats, TARGET, r=df["r"].to_numpy())
            if sel.sum() < 10:
                line += f"  {lab} thin"
                continue
            gm, gl, gh = boot(r[sel], day[sel])
            line += f"  {lab} {gm:+.2f}[{gl:+.2f},{gh:+.2f}]n{int(sel.sum())}"
        print(line)
    print("\nREAD: CONFIRM/BOTH clearly above CURRENT across markets = the confirmation reframe adds alpha (build the "
          "gate around it). Roughly equal = the magnitude gate already encodes confirmation; finding is interpretation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
