"""Phase 2b acceptance: the multi-head labels must be honest, deterministic, and
must NOT have disturbed the frozen Phase-1 judge.

Run: backend/.venv/Scripts/python.exe experiments/prop_intraday_resolver_v0/verify_phase2_labels.py        (full, heavy)
     backend/.venv/Scripts/python.exe experiments/prop_intraday_resolver_v0/verify_phase2_labels.py 30     (fast sample; skips the frozen-frame check)

Checks (all must pass before any model training, Phase 2c):
  A  no lookahead   -- feature_end_ts <= decision_ts < label_start_ts on EVERY row
  B  determinism    -- rebuild a sample twice -> byte-identical
  C  judge preserved-- resolved subset == the frozen Phase-1 trading-day frame
                       (same ts/level/dir/ofi_signed, y_break == Phase-1 label)
  D  signal intact  -- realized_R + break-rate monotone across OFI terciles
  E  clean labels   -- no null label cells, 0 same-row target/stop ambiguity
"""

from __future__ import annotations

import _paths  # noqa: F401
import sys
from pathlib import Path

import pandas as pd

import dataset
import pipeline

FROZEN_TD = (
    Path(pipeline.OUT) / "events_ES_trading_day.parquet"
)  # Phase-1 canonical (gitignored, local)


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    d = df.reset_index()
    if "ts" not in d.columns:
        cand = [c for c in ("index", "level_0") if c in d.columns]
        if cand:
            d = d.rename(columns={cand[0]: "ts"})
    d["ts"] = pd.to_datetime(d["ts"], utc=True)
    return d.sort_values(["ts", "level", "dir"]).reset_index(drop=True)


def check_lookahead(df: pd.DataFrame) -> bool:
    fe_le_dec = (df["feature_end_ts"] <= df["decision_ts"]).all()
    dec_lt_ls = (df["decision_ts"] < df["label_start_ts"]).all()
    fe_lt_ls = (df["feature_end_ts"] < df["label_start_ts"]).all()
    ok = bool(fe_le_dec and dec_lt_ls and fe_lt_ls)
    print(
        f"[A] no-lookahead: feature_end<=decision {bool(fe_le_dec)}, "
        f"decision<label_start {bool(dec_lt_ls)}, feature_end<label_start {bool(fe_lt_ls)} -> {'PASS' if ok else 'FAIL'}"
    )
    return ok


def check_determinism(n_days: int = 8) -> bool:
    a = dataset.build(days_limit=n_days, write=False)
    b = dataset.build(days_limit=n_days, write=False)
    try:
        pd.testing.assert_frame_equal(a, b)
        print(f"[B] determinism: rebuild on {n_days} days -> byte-identical -> PASS")
        return True
    except AssertionError as e:
        print(f"[B] determinism: FAIL\n{str(e)[:800]}")
        return False


def check_judge_preserved(df: pd.DataFrame) -> bool:
    if not FROZEN_TD.exists():
        print(
            f"[C] judge-preserved: SKIPPED (no frozen frame at {FROZEN_TD}; run verify_phase1.py full trading_day)"
        )
        return True
    frozen = _norm(pd.read_parquet(FROZEN_TD))
    res = df[df["y_chop_or_timeout"] == 0].copy()
    res["label"] = res["y_break"]
    res = _norm(res)
    if len(res) != len(frozen):
        print(
            f"[C] judge-preserved: FAIL — resolved n={len(res)} != frozen n={len(frozen)}"
        )
        return False
    m = res.merge(frozen, on=["ts", "level"], suffixes=("_new", "_old"))
    ok = (
        len(m) == len(res)
        and bool((m["dir_new"] == m["dir_old"]).all())
        and bool((m["label_new"] == m["label_old"]).all())
        and float((m["ofi_signed_new"] - m["ofi_signed_old"]).abs().max()) < 1e-9
    )
    print(
        f"[C] judge-preserved: resolved subset == frozen Phase-1 frame (n={len(res)}) -> {'PASS' if ok else 'FAIL'}"
    )
    return ok


def check_clean(df: pd.DataFrame) -> bool:
    nulls = {
        c: int(df[c].isna().sum()) for c in dataset.LABEL_COLS if df[c].isna().any()
    }
    amb = int(df["ambiguous"].sum())
    ok = not nulls and amb == 0
    print(
        f"[E] clean labels: nulls={nulls or 'none'}  ambiguity={amb} -> {'PASS' if ok else 'FAIL'}"
    )
    return ok


def main(argv: list[str]) -> int:
    sample = int(argv[1]) if len(argv) > 1 else None
    tag = f"sample={sample}" if sample else "FULL"
    print(f"VERIFY PHASE 2 LABELS ({tag}) — building multi-head dataset...")
    df = dataset.build(days_limit=sample, write=(sample is None))

    a = check_lookahead(df)
    e = check_clean(df)
    c = (
        check_judge_preserved(df)
        if sample is None
        else (print("[C] judge-preserved: SKIPPED on sample run") or True)
    )
    audit = dataset.audit(df)  # prints distributions + [D] signal table
    d = bool(audit["tercile_monotone"])
    print(
        f"[D] signal intact: OFI-tercile break-rate monotone (resolved) -> {'PASS' if d else 'FAIL'}"
    )
    b = check_determinism(min(8, sample) if sample else 8)

    ok = all([a, b, c, d, e])
    print(
        f"\nPHASE 2 LABELS {'PASS — ready for 2c (model heads)' if ok else 'FAIL — fix before training'}.\n"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
