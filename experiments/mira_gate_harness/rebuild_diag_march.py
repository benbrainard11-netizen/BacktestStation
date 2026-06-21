"""Task-1 diagnostic: single-month MARCH build through the FIXED harness build path.

March is the cleanest probe for the 2026-06-09 silent 0-row train build: Jan builds fine,
Mar/Apr were entirely absent from the monthly CSV. If March builds healthy rows here, the
root cause (missing-SMT-db default -> empty _load_smt_events -> all rows filtered) is
confirmed fixed and the full train window can be rebuilt the same way.

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/rebuild_diag_march.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
# Force the vendored 5m-capable detector stack BEFORE importing harness (no-5m-fork gotcha).
os.environ["BACKTESTSTATION_BACKEND"] = str(ROOT / "live_engine" / "vendor")
os.environ.pop("BS_MIRA_ROOT", None)
sys.path.insert(0, str(HERE))

import harness as H  # noqa: E402

NAME, START, END = "mar_2026", "2026-03-01", "2026-03-31"


def main() -> int:
    df = H.build_dataset(NAME, START, END)
    print(f"\n=== MARCH DIAGNOSTIC RESULT ===")
    print(f"rows={len(df)}  label_pos_rate={df['label'].mean():.4f}")
    print("per-symbol:")
    print(df["symbol"].astype(str).value_counts().to_string())
    print("trigger_type:", df["trigger_type"].astype(str).value_counts().to_dict())
    print("date span:", df["trigger_ts_utc"].min(), "->", df["trigger_ts_utc"].max())
    n_opp = df[H.OPP].nunique()
    print(f"unique sweep opportunities: {n_opp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
