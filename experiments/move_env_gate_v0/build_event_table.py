"""Build the v0 market-state event table.

Default input is the parked resolver's causal multi-head table. This script
keeps only the small feature set needed for the pasted research direction:
geometry, MBP-1 event-time flow, cross-index context, and forward labels.

Run:
  backend\\.venv\\Scripts\\python.exe experiments\\move_env_gate_v0\\build_event_table.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
from labels import attach_move_env_labels, label_summary  # noqa: E402

KEEP_COLUMNS = [
    "event_id",
    "event_ts",
    "symbol",
    "session_date",
    "level",
    "dir",
    "ofi_signed",
    "qimb_signed",
    "svol_signed",
    "nq_ofi",
    "rty_ofi",
    "ym_ofi",
    "complex_mean_ofi",
    "complex_ofi_dispersion",
    "es_complex_agree",
    "level_is_pdh",
    "level_is_pdl",
    "y_move",
    "y_favorable_move",
    "y_bad_env",
    "y_chop",
    "y_timeout_mark",
    "y_target_before_stop",
    "realized_R",
    "mae_R",
    "mfe_R",
    "time_to_resolution_sec",
    "feature_end_ts",
    "decision_ts",
    "label_start_ts",
    "label_source",
]


def read_source(path: Path) -> pd.DataFrame:
    """Read parquet/csv/json source tables."""
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".json", ".jsonl"}:
        return pd.read_json(path, lines=suffix == ".jsonl")
    raise ValueError(f"unsupported source suffix: {suffix}")


def event_times(df: pd.DataFrame) -> pd.Series:
    """Find the event timestamp without assuming whether parquet stored an index."""
    if "event_ts" in df.columns:
        return pd.to_datetime(df["event_ts"], utc=True)
    if "ts" in df.columns:
        return pd.to_datetime(df["ts"], utc=True)
    if isinstance(df.index, pd.DatetimeIndex):
        return pd.Series(pd.to_datetime(df.index, utc=True), index=df.index)
    for col in ("decision_ts", "trigger_ts_utc", "touch_ts_utc"):
        if col in df.columns:
            return pd.to_datetime(df[col], utc=True)
    raise ValueError("could not infer event timestamp column")


def normalize_event_table(
    raw: pd.DataFrame,
    *,
    source: Path,
    symbol: str,
    target_r: float,
    bad_r: float,
) -> pd.DataFrame:
    """Return the narrow v0 event table with causal feature blocks."""
    df = raw.copy()
    ts = event_times(df)
    df["event_ts"] = ts.to_numpy()
    df["symbol"] = df.get("symbol", symbol)
    df["session_date"] = pd.to_datetime(df["event_ts"], utc=True).dt.date.astype(str)

    if "event_id" not in df.columns:
        dates = df["session_date"].astype(str)
        df["event_id"] = [f"{symbol}|{d}|{i:06d}" for i, d in enumerate(dates)]

    for col in ("ofi_signed", "qimb_signed", "svol_signed", "nq_ofi", "rty_ofi", "ym_ofi"):
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if "level" not in df.columns:
        df["level"] = "unknown"
    df["level"] = df["level"].astype(str).str.upper()
    df["dir"] = pd.to_numeric(df.get("dir", 0), errors="coerce").fillna(0).astype(int)
    df["level_is_pdh"] = (df["level"] == "PDH").astype("int8")
    df["level_is_pdl"] = (df["level"] == "PDL").astype("int8")

    peers = df[["nq_ofi", "rty_ofi", "ym_ofi"]]
    df["complex_mean_ofi"] = peers.mean(axis=1)
    df["complex_ofi_dispersion"] = peers.std(axis=1).fillna(0.0)
    df["es_complex_agree"] = df["ofi_signed"] * df["complex_mean_ofi"]

    df = attach_move_env_labels(df, target_r=target_r, bad_r=bad_r)
    for col in ("y_target_before_stop", "time_to_resolution_sec"):
        if col not in df.columns:
            df[col] = np.nan

    for col in ("feature_end_ts", "decision_ts", "label_start_ts"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True)
        else:
            df[col] = pd.NaT

    out = df[[c for c in KEEP_COLUMNS if c in df.columns]].copy()
    out["source_file"] = str(source)
    return out.sort_values("event_ts").reset_index(drop=True)


def write_manifest(path: Path, table: pd.DataFrame, source: Path) -> None:
    """Write a compact manifest next to the parquet output."""
    payload = {
        "generated_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "source": str(source),
        "output": str(path),
        "rows": int(len(table)),
        "columns": list(table.columns),
        "labels": label_summary(table),
    }
    path.with_suffix(".manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=C.DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=C.DEFAULT_EVENT_TABLE)
    parser.add_argument("--symbol", default=C.DEFAULT_SYMBOL)
    parser.add_argument("--target-r", type=float, default=C.TARGET_R)
    parser.add_argument("--bad-r", type=float, default=C.BAD_R)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw = read_source(args.source)
    table = normalize_event_table(
        raw,
        source=args.source,
        symbol=args.symbol,
        target_r=args.target_r,
        bad_r=args.bad_r,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(args.out, index=False)
    write_manifest(args.out, table, args.source)
    print(f"wrote {args.out} rows={len(table)}")
    print(label_summary(table))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

