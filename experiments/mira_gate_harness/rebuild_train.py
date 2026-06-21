"""Task-1 final step: rebuild the FULL train window (2026-02-06..05-20) through the fixed
harness build path (explicit SMT db + hard guards). One full-window build — the validated
unit — rather than stitched month chunks, to avoid month-boundary label artifacts.

Pre-flight: data/train.parquet must NOT exist (delete the poisoned empty cache first;
build_dataset returns any existing cache untouched).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/rebuild_train.py
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


def main() -> int:
    cached = H.DATA / "train.parquet"
    if cached.exists():
        raise SystemExit(f"{cached} already exists — delete it first if you intend a rebuild "
                         "(use [System.IO.File]::Delete, the shell delete hook misfires)")
    s, e = H.WINDOWS["train"]
    df = H.build_dataset("train", s, e)
    print(f"\n=== TRAIN REBUILD RESULT ===")
    print(f"rows={len(df)}  label_pos_rate={df['label'].mean():.4f}")
    print("per-symbol:")
    print(df["symbol"].astype(str).value_counts().to_string())
    df["_mo"] = df["trigger_ts_utc"].astype(str).str[:7]
    print("per-month rows:", df.groupby("_mo").size().to_dict())
    print("date span:", df["trigger_ts_utc"].min(), "->", df["trigger_ts_utc"].max())
    print(f"unique sweep opportunities: {df[H.OPP].nunique()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
