"""Frozen-champion OOS robustness and localization diagnostic.

This runner intentionally does not train anything. It loads the frozen champion gate,
validates the known anchor windows first, then scores non-overlapping monthly slices
and rolling two-week slices with the same gate/dedupe/R machinery as the harness.

Outputs:
  runs/monthly_oos_slices.csv
  runs/champion_cumulative_r.csv
"""
from __future__ import annotations

import datetime as dt
import math
import os
import sys
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNS = HERE / "runs"
DATA = HERE / "data"

# HARD CONSTRAINT: force the live vendored detector stack before importing harness.
# An externally-set BACKTESTSTATION_BACKEND can point at the repo backend, whose SMT
# detector is missing 5m and produces a false degraded-edge read.
os.environ["BACKTESTSTATION_BACKEND"] = str(ROOT / "live_engine" / "vendor")
os.environ.pop("BS_MIRA_ROOT", None)

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "live_engine" / "engine"))

import gate as G  # noqa: E402
import harness as H  # noqa: E402
import realized_r as RR  # noqa: E402

OPP = H.OPP
SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]

ANCHORS = [
    {
        "name": "jan_oos",
        "start": "2026-01-02",
        "end": "2026-02-04",
        "expect": {"gated_n": 139, "R_n": 138, "R_mean": 0.456, "R_sum": 63.0},
    },
    {
        "name": "oos_holdout",
        "start": "2026-05-21",
        "end": "2026-06-05",
        "expect": {"gated_n": 83, "R_n": 83, "R_mean": 0.298, "R_sum": 24.8},
    },
]

MONTHS = [
    ("month_2026_01", "2026-01-01", "2026-01-31"),
    ("month_2026_02", "2026-02-01", "2026-02-28"),
    ("month_2026_03", "2026-03-01", "2026-03-31"),
    ("month_2026_04", "2026-04-01", "2026-04-30"),
    ("month_2026_05", "2026-05-01", "2026-05-31"),
    ("month_2026_06", "2026-06-01", "2026-06-05"),
]

# Build from the harness' validated source windows, then derive calendar months
# and rolling windows by timestamp. Direct calendar-month builds can produce
# target-label artifacts at month boundaries; these source windows are the units
# the harness was designed and validated around.
SOURCE_WINDOWS = [
    ("jan_oos", "2026-01-02", "2026-02-04"),
    ("train", "2026-02-06", "2026-05-20"),
    ("oos_holdout", "2026-05-21", "2026-06-05"),
]

TOL = {"gated_n": 1, "R_n": 2, "R_mean": 0.01, "R_sum": 1.0}


def _date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def _fmt(x, digits: int = 3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NA"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    return f"{float(x):+.{digits}f}"


def _safe_to_parquet(df: pd.DataFrame, path: Path) -> None:
    df.to_parquet(path, index=False)


def purge_stale_cache(name: str, start: str, end: str) -> None:
    """Remove a generated cache if its manifest belongs to another window."""
    manifest = DATA / f"{name}.manifest.json"
    if not manifest.exists():
        return
    try:
        meta = json.loads(manifest.read_text())
    except Exception:
        meta = {}
    if meta.get("start") == start and meta.get("end") == end:
        return
    for path in (DATA / f"{name}.parquet", manifest):
        if path.exists():
            path.unlink()


def ensure_scored_realized(name: str, start: str, end: str, gate: G.Gate) -> pd.DataFrame:
    """Load/build a cached dataset, score it, and add realized_r for selected rows.

    realized_r is only needed for the frozen champion's gated/deduped rows in this
    diagnostic. Computing it on the full candidate population is much slower and
    does not change any reported metric.
    """
    purge_stale_cache(name, start, end)
    ds = H.build_dataset(name, start, end)
    ds = ds.copy()
    ds["trigger_ts_utc"] = pd.to_datetime(ds["trigger_ts_utc"], utc=True)
    scored = score_dataset(ds, gate)
    if "r_reason" not in scored.columns:
        scored["r_reason"] = None
    if "realized_r" not in scored.columns:
        scored["realized_r"] = np.nan
        selected = gated_deduped(scored, gate)
        print(
            f"[realized] computing {name} {start}..{end}: "
            f"{len(selected)} gated/deduped rows",
            flush=True,
        )
        if not selected.empty:
            computed = RR.compute(selected.drop(columns=["_score"], errors="ignore"))
            scored.loc[computed.index, "realized_r"] = computed["realized_r"]
            scored.loc[computed.index, "r_reason"] = computed["r_reason"]
        _safe_to_parquet(scored.drop(columns=["_score"], errors="ignore"), DATA / f"{name}.parquet")
    return scored


def score_dataset(ds: pd.DataFrame, gate: G.Gate) -> pd.DataFrame:
    out = ds.copy()
    if out.empty:
        out["_score"] = pd.Series(dtype=float)
    else:
        out["_score"] = gate.score(out)
    return out


def gated_deduped(scored: pd.DataFrame, gate: G.Gate) -> pd.DataFrame:
    """Return rows selected by the exact harness dedupe convention."""
    g = scored.loc[scored["_score"].to_numpy() >= gate.threshold].copy()
    if OPP in g.columns and "trigger_id" in g.columns and not g.empty:
        g = g.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable").groupby(OPP, sort=False).head(1)
    return g


def eval_scored(scored: pd.DataFrame, gate: G.Gate) -> dict:
    return H.eval_model(scored["_score"].to_numpy(), scored, gate.threshold)


def summarize_realized(rows: pd.DataFrame) -> dict:
    rr = pd.to_numeric(rows.get("realized_r", pd.Series(dtype=float)), errors="coerce").dropna()
    if rr.empty:
        return {"R_n": 0, "R_mean": np.nan, "R_win": np.nan, "R_sum": np.nan}
    return {
        "R_n": int(len(rr)),
        "R_mean": float(rr.mean()),
        "R_win": float((rr > 0).mean()),
        "R_sum": float(rr.sum()),
    }


def validation_diff(actual: dict, expected: dict) -> list[str]:
    diffs = []
    for k, exp in expected.items():
        act = actual.get(k)
        tol = TOL[k]
        if act is None or (isinstance(act, float) and not np.isfinite(act)):
            diffs.append(f"{k}: actual={act} expected={exp} tol={tol}")
            continue
        if abs(float(act) - float(exp)) > tol:
            diffs.append(f"{k}: actual={act} expected={exp} diff={float(act) - float(exp):+.3f} tol={tol}")
    return diffs


def validate_anchors(gate: G.Gate) -> dict[str, pd.DataFrame]:
    print("\n=== VALIDATION GATES ===", flush=True)
    out: dict[str, pd.DataFrame] = {}
    failures = []
    for spec in ANCHORS:
        ds = ensure_scored_realized(spec["name"], spec["start"], spec["end"], gate)
        metrics = eval_scored(ds, gate)
        out[spec["name"]] = ds
        diffs = validation_diff(metrics, spec["expect"])
        status = "PASS" if not diffs else "FAIL"
        print(
            f"{status} {spec['name']} {spec['start']}..{spec['end']} "
            f"gated={metrics.get('gated_n')} R_n={metrics.get('R_n')} "
            f"meanR={_fmt(metrics.get('R_mean'))} sumR={_fmt(metrics.get('R_sum'), 1)}",
            flush=True,
        )
        if diffs:
            failures.append((spec["name"], diffs))
    if failures:
        print("\nABORT: known anchors did not reproduce. New slice numbers would be suspect.", flush=True)
        for name, diffs in failures:
            print(f"\n{name} diffs:", flush=True)
            for d in diffs:
                print(f"  - {d}", flush=True)
        raise SystemExit(2)
    return out


def rolling_windows() -> list[tuple[str, str, str]]:
    start = _date("2026-01-02")
    final = _date("2026-06-05")
    cur = start
    windows = []
    while cur <= final - dt.timedelta(days=6):
        end = min(cur + dt.timedelta(days=13), final)
        name = f"roll2w_{cur.isoformat().replace('-', '')}_{end.isoformat().replace('-', '')}"
        windows.append((name, cur.isoformat(), end.isoformat()))
        cur += dt.timedelta(days=7)
    return windows


def slice_by_dates(scored: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    s = pd.Timestamp(start, tz="UTC")
    e = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    return scored[(scored["trigger_ts_utc"] >= s) & (scored["trigger_ts_utc"] < e)].copy()


def slice_row(
    scored: pd.DataFrame,
    gate: G.Gate,
    *,
    kind: str,
    name: str,
    start: str,
    end: str,
    scope: str,
    symbol: str | None = None,
) -> dict:
    sub = scored if symbol is None else scored[scored["symbol"].astype(str) == symbol].copy()
    if sub.empty:
        metrics = {
            "n": 0,
            "base_rate": np.nan,
            "auc": np.nan,
            "gated_n": 0,
            "gated_success": np.nan,
            "lift_vs_base": np.nan,
            "R_n": 0,
            "R_mean": np.nan,
            "R_win": np.nan,
            "R_sum": np.nan,
        }
    else:
        metrics = eval_scored(sub, gate)
    return {
        "slice_kind": kind,
        "slice_name": name,
        "start": start,
        "end": end,
        "scope": scope,
        "symbol": symbol or "ALL",
        "candidate_rows": metrics.get("n"),
        "label_base_rate": metrics.get("base_rate"),
        "auc": metrics.get("auc"),
        "gated_count": metrics.get("gated_n"),
        "gated_label_success": metrics.get("gated_success"),
        "realized_filled": metrics.get("R_n", 0),
        "realized_mean_r": metrics.get("R_mean"),
        "realized_win_rate": metrics.get("R_win"),
        "realized_sum_r": metrics.get("R_sum"),
    }


def print_slice_table(rows: list[dict], title: str) -> None:
    print(f"\n=== {title} ===", flush=True)
    header = f"{'slice':32s} {'scope':9s} {'cand':>6s} {'auc':>7s} {'gated':>6s} {'R_n':>5s} {'meanR':>8s} {'win':>7s} {'sumR':>8s}"
    print(header, flush=True)
    for r in rows:
        if r["scope"] != "all":
            continue
        win = r["realized_win_rate"]
        win_s = "NA" if win is None or not np.isfinite(float(win)) else f"{100 * float(win):.1f}%"
        print(
            f"{r['slice_name'][:32]:32s} {r['scope']:9s} {int(r['candidate_rows']):6d} "
            f"{_fmt(r['auc'], 3):>7s} {int(r['gated_count']):6d} {int(r['realized_filled']):5d} "
            f"{_fmt(r['realized_mean_r'], 3):>8s} {win_s:>7s} {_fmt(r['realized_sum_r'], 1):>8s}",
            flush=True,
        )


def build_sources(gate: G.Gate) -> list[pd.DataFrame]:
    out = []
    for name, start, end in SOURCE_WINDOWS:
        print(f"\n[source] {name} {start}..{end}", flush=True)
        out.append(ensure_scored_realized(name, start, end, gate))
    return out


def metric_rows_for_slices(full: pd.DataFrame, gate: G.Gate) -> list[dict]:
    rows: list[dict] = []
    for kind, specs in [
        ("month", MONTHS),
        ("rolling_2w", rolling_windows()),
    ]:
        for name, start, end in specs:
            sub = slice_by_dates(full, start, end)
            rows.append(slice_row(sub, gate, kind=kind, name=name, start=start, end=end, scope="all"))
            for sym in SYMBOLS:
                rows.append(slice_row(sub, gate, kind=kind, name=name, start=start, end=end, scope="symbol", symbol=sym))
    return rows


def realized_trade_set(scored: pd.DataFrame, gate: G.Gate) -> pd.DataFrame:
    gt = gated_deduped(scored, gate).copy()
    gt["realized_r"] = pd.to_numeric(gt["realized_r"], errors="coerce")
    gt = gt[gt["realized_r"].notna()].copy()
    gt = gt.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable").reset_index(drop=True)
    return gt


def print_aggregate(name: str, rows: pd.DataFrame) -> None:
    st = summarize_realized(rows)
    win = st["R_win"]
    win_s = "NA" if not np.isfinite(win) else f"{100 * win:.1f}%"
    print(
        f"{name:18s} N={st['R_n']:4d} meanR={_fmt(st['R_mean'])} "
        f"win={win_s:>6s} sumR={_fmt(st['R_sum'], 1)}",
        flush=True,
    )


def aggregate_report(trades: pd.DataFrame) -> None:
    print("\n=== GO/NO-GO AGGREGATES ===", flush=True)
    print_aggregate("all-in", trades)

    feb_on = trades[trades["trigger_ts_utc"].dt.date >= _date("2026-02-01")]
    print_aggregate("drop-Jan", feb_on)

    for sym in SYMBOLS:
        print_aggregate(f"drop-{sym.split('.')[0]}", trades[trades["symbol"].astype(str) != sym])

    rr = trades["realized_r"].dropna().sort_values(ascending=False)
    if rr.empty:
        print("concentration     NA", flush=True)
        return
    total = float(rr.sum())
    top_n = max(1, int(math.ceil(0.10 * len(rr))))
    top_share = float(rr.head(top_n).sum() / total) if total else np.nan
    ex_top5 = float(rr.iloc[5:].sum()) if len(rr) > 5 else 0.0
    print(
        f"concentration     top_decile_n={top_n} top_decile_share={_fmt(top_share, 3)} "
        f"sumR_ex_top5={_fmt(ex_top5, 1)}",
        flush=True,
    )


def write_cumulative(trades: pd.DataFrame) -> Path:
    out = trades[
        [
            "trigger_ts_utc",
            "trigger_id",
            "symbol",
            "smt_anchor_side",
            "trigger_price",
            "_score",
            "label",
            "realized_r",
            "r_reason",
        ]
    ].copy()
    out["running_sumR"] = out["realized_r"].cumsum()
    path = RUNS / "champion_cumulative_r.csv"
    out.to_csv(path, index=False)
    return path


def write_slice_csv(rows: Iterable[dict]) -> Path:
    path = RUNS / "monthly_oos_slices.csv"
    pd.DataFrame(list(rows)).to_csv(path, index=False)
    return path


def main() -> int:
    RUNS.mkdir(parents=True, exist_ok=True)
    gate = G.Gate()
    print(f"frozen champion threshold={gate.threshold:.10f}", flush=True)

    validate_anchors(gate)

    sources = build_sources(gate)
    full = pd.concat(sources, ignore_index=True)
    full = full.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable").reset_index(drop=True)
    full = full.drop_duplicates(
        subset=["symbol", "trigger_ts_utc", "trigger_id", OPP],
        keep="first",
    ).reset_index(drop=True)

    rows = metric_rows_for_slices(full, gate)
    slice_path = write_slice_csv(rows)
    print_slice_table([r for r in rows if r["slice_kind"] == "month"], "MONTHLY SLICES")
    print_slice_table([r for r in rows if r["slice_kind"] == "rolling_2w"], "ROLLING 2W SLICES")

    trades = realized_trade_set(full, gate)
    aggregate_report(trades)
    cumulative_path = write_cumulative(trades)

    print("\n=== NOTES ===", flush=True)
    print("- AUC flat across slices while realized R falls = ranker is fine; edge/regime or label-to-P&L link is the issue.", flush=True)
    print("- AUC degrading across slices = the ranker itself is decaying.", flush=True)
    print("- sumR dominated by Jan, one symbol, or the top decile = fragile base.", flush=True)
    print(f"\nwrote {slice_path}", flush=True)
    print(f"wrote {cumulative_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
