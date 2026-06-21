"""Normalize real strategy/setup rows into a gate-test table.

Default mode includes only non-quarantined strategy artifacts. Mira exports are
kept behind an explicit flag because the frozen Mira gate has a known lookahead
risk from post-trigger/bookproxy features.

Run:
  backend\\.venv\\Scripts\\python.exe experiments\\move_env_gate_v0\\build_strategy_event_table.py
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402


def _read(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _parse_time(values: pd.Series, *, naive_tz: str = "UTC") -> pd.Series:
    ts = pd.to_datetime(values, errors="coerce")
    if getattr(ts.dt, "tz", None) is None:
        return ts.dt.tz_localize(naive_tz).dt.tz_convert("UTC")
    return ts.dt.tz_convert("UTC")


def _direction_int(values: pd.Series) -> pd.Series:
    text = values.astype(str).str.lower()
    return np.where(text.isin(["long", "bullish", "1"]), 1, -1)


def _base_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["event_ts"] = pd.to_datetime(out["event_ts"], utc=True)
    out["hour"] = out["event_ts"].dt.hour.astype("int16")
    out["weekday"] = out["event_ts"].dt.weekday.astype("int16")
    out["month_num"] = out["event_ts"].dt.month.astype("int16")
    risk = pd.to_numeric(out.get("risk_points", np.nan), errors="coerce")
    out["risk_points"] = risk
    out["risk_log"] = np.log1p(risk.clip(lower=0)).replace([np.inf, -np.inf], np.nan)
    return out


def _attach_trade_labels(
    df: pd.DataFrame,
    *,
    move_r: float,
    bad_r: float,
    label_source: str,
) -> pd.DataFrame:
    out = df.copy()
    r = pd.to_numeric(out["realized_R"], errors="coerce")
    out["y_good_trade"] = np.where(r.notna(), (r > 0).astype("int8"), np.nan)
    out["y_trade_loss"] = np.where(r.notna(), (r < 0).astype("int8"), np.nan)
    out["y_bad_env"] = np.where(r.notna(), (r <= -bad_r).astype("int8"), np.nan)
    out["y_move"] = np.where(r.notna(), (r.abs() >= move_r).astype("int8"), np.nan)
    out["y_chop"] = np.where(r.notna(), (r.abs() < move_r).astype("int8"), np.nan)
    out["label_source"] = label_source
    return out


def normalize_fractal(path: Path, *, move_r: float, bad_r: float) -> pd.DataFrame:
    raw = _read(path)
    out = pd.DataFrame()
    out["event_ts"] = _parse_time(raw["entry_time"], naive_tz="America/New_York")
    out["exit_ts"] = _parse_time(raw["exit_time"], naive_tz="America/New_York")
    out["strategy"] = "Fractal AMD"
    out["source_kind"] = "fractal_trusted_multiyear_trades"
    out["source_status"] = "usable"
    out["source_caveat"] = ""
    out["symbol"] = "NQ"
    out["direction"] = raw["direction"].astype(str).str.lower().map(
        {"bullish": "long", "bearish": "short"}
    )
    out["direction_int"] = _direction_int(out["direction"])
    out["setup_type"] = "fractal_amd"
    out["baseline_action"] = "entered"
    out["baseline_trade"] = True
    out["entered"] = True
    out["realized_R"] = pd.to_numeric(raw["pnl_r"], errors="coerce")
    out["risk_points"] = pd.to_numeric(raw["risk"], errors="coerce")
    out["exit_reason"] = raw.get("exit_reason")
    out["gate_score"] = np.nan
    out["existing_gate_passed"] = np.nan
    out["source_file"] = str(path)
    out = _base_features(out)
    out = _attach_trade_labels(out, move_r=move_r, bad_r=bad_r, label_source="trade_pnl_r")
    out["event_id"] = [f"fractal|{i:06d}" for i in range(len(out))]
    return out


def normalize_mira_recent(path: Path, *, move_r: float, bad_r: float) -> pd.DataFrame:
    raw = _read(path)
    out = pd.DataFrame()
    out["event_ts"] = _parse_time(raw["trigger_ts_utc"])
    out["exit_ts"] = _parse_time(raw["exit_ts_utc"]) if "exit_ts_utc" in raw else pd.NaT
    out["strategy"] = "Mira"
    out["source_kind"] = "mira_recent_live_replay_candidates"
    out["source_status"] = "quarantined_lookahead_risk"
    out["source_caveat"] = "Frozen Mira gate/replay uses post-trigger bookproxy features."
    out["symbol"] = raw["symbol"].astype(str)
    out["direction"] = raw["direction"].astype(str).str.lower()
    out["direction_int"] = _direction_int(out["direction"])
    out["setup_type"] = raw.get("trigger_type", "unknown").astype(str)
    out["baseline_action"] = np.select(
        [raw["entered"].astype(bool), raw["armed"].astype(bool), raw["gated"].astype(bool)],
        ["entered", "armed", "gated"],
        default="rejected",
    )
    out["baseline_trade"] = raw["entered"].astype(bool)
    out["entered"] = raw["entered"].astype(bool)
    out["realized_R"] = pd.to_numeric(raw.get("r_signal_gross", np.nan), errors="coerce")
    out["risk_points"] = pd.to_numeric(raw.get("risk_points", np.nan), errors="coerce")
    out["exit_reason"] = raw.get("blocked_reason")
    out["gate_score"] = pd.to_numeric(raw.get("gate_score", np.nan), errors="coerce")
    out["existing_gate_passed"] = raw.get("gated", False).astype(bool).astype("int8")
    out["source_file"] = str(path)
    out = _base_features(out)
    out = _attach_trade_labels(
        out,
        move_r=move_r,
        bad_r=bad_r,
        label_source="live_replay_entered_r_only",
    )
    out["event_id"] = [f"mira_recent|{i:06d}" for i in range(len(out))]
    return out


def normalize_mira_jan(path: Path, *, move_r: float, bad_r: float) -> pd.DataFrame:
    raw = _read(path)
    out = pd.DataFrame()
    out["event_ts"] = _parse_time(raw["entry_ts"])
    out["exit_ts"] = pd.NaT
    out["strategy"] = "Mira"
    out["source_kind"] = "mira_jan_replay_trades"
    out["source_status"] = "quarantined_lookahead_risk"
    out["source_caveat"] = "Frozen Mira gate/replay uses post-trigger bookproxy features."
    out["symbol"] = raw["symbol"].astype(str)
    out["direction"] = np.where(pd.to_numeric(raw["direction"]) == 1, "long", "short")
    out["direction_int"] = pd.to_numeric(raw["direction"], errors="coerce").fillna(0).astype(int)
    out["setup_type"] = "post_sweep_smt_reclaim"
    out["baseline_action"] = "entered"
    out["baseline_trade"] = True
    out["entered"] = True
    out["realized_R"] = pd.to_numeric(raw["r_signal_net"], errors="coerce")
    out["risk_points"] = pd.to_numeric(raw.get("risk_points", np.nan), errors="coerce")
    out["exit_reason"] = raw.get("reason_signal")
    out["gate_score"] = np.nan
    out["existing_gate_passed"] = np.nan
    out["source_file"] = str(path)
    out = _base_features(out)
    out = _attach_trade_labels(out, move_r=move_r, bad_r=bad_r, label_source="replay_net_R")
    out["event_id"] = [f"mira_jan|{i:06d}" for i in range(len(out))]
    return out


def build_sources(
    source: str,
    *,
    move_r: float,
    bad_r: float,
    include_quarantined_mira: bool,
) -> pd.DataFrame:
    frames = []
    choices = {
        "fractal": (C.FRACTAL_TRADES, normalize_fractal),
        "mira-recent": (C.MIRA_RECENT_REPLAY, normalize_mira_recent),
        "mira-jan": (C.MIRA_JAN_TRAIL, normalize_mira_jan),
    }
    if source == "all":
        selected = {"fractal": choices["fractal"]}
        if include_quarantined_mira:
            selected = choices
    else:
        selected = {source: choices[source]}
    for _name, (path, func) in selected.items():
        if not path.exists():
            print(f"skip missing source: {path}")
            continue
        frames.append(func(path, move_r=move_r, bad_r=bad_r))
    if not frames:
        raise FileNotFoundError("no strategy sources were available")
    table = pd.concat(frames, ignore_index=True)
    return table.sort_values(["source_kind", "event_ts", "event_id"]).reset_index(drop=True)


def manifest(table: pd.DataFrame, path: Path) -> dict:
    rows = []
    for (strategy, source), group in table.groupby(["strategy", "source_kind"], dropna=False):
        r = pd.to_numeric(group["realized_R"], errors="coerce")
        rows.append(
            {
                "strategy": strategy,
                "source_kind": source,
                "source_status": str(group["source_status"].iloc[0]),
                "source_caveat": str(group["source_caveat"].iloc[0]),
                "rows": int(len(group)),
                "labeled_rows": int(r.notna().sum()),
                "baseline_trades": int(group["baseline_trade"].sum()),
                "mean_R_labeled": None if r.notna().sum() == 0 else float(r.mean()),
            }
        )
    return {
        "generated_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "output": str(path),
        "rows": int(len(table)),
        "sources": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["all", "fractal", "mira-recent", "mira-jan"], default="all")
    parser.add_argument(
        "--include-quarantined-mira",
        action="store_true",
        help="Opt in to Mira sources despite the known post-trigger/bookproxy lookahead risk.",
    )
    parser.add_argument("--out", type=Path, default=C.DEFAULT_STRATEGY_TABLE)
    parser.add_argument("--move-r", type=float, default=C.TRADE_MOVE_R)
    parser.add_argument("--bad-r", type=float, default=C.BAD_R)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    table = build_sources(
        args.source,
        move_r=args.move_r,
        bad_r=args.bad_r,
        include_quarantined_mira=args.include_quarantined_mira,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(args.out, index=False)
    payload = manifest(table, args.out)
    args.out.with_suffix(".manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    print(f"wrote {args.out} rows={len(table)}")
    for row in payload["sources"]:
        mean = row["mean_R_labeled"]
        mean_s = "nan" if mean is None or math.isnan(mean) else f"{mean:+.3f}"
        print(
            f"  {row['source_kind']}: rows={row['rows']} labeled={row['labeled_rows']} "
            f"baseline_trades={row['baseline_trades']} meanR={mean_s} "
            f"status={row['source_status']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
