"""Phase 1 acceptance + regression guards.

Modes:
  smoke [N]            -- fast (default N=6 days). PINNED to reader="raw": for each
                          sampled day, compare our decomposed path against
                          zone_events.process_day ROW-FOR-ROW. This is the Step-1a
                          faithfulness guard -- it proves the spine reproduces
                          market_state Stage 1, and must stay green forever.
  full [raw|td]        -- reproduce the whole event frame for a reader (default
                          trading_day, the canonical reader) and compare to its
                          reference (raw -> market_state/out/zone_events_ES.parquet;
                          trading_day -> local out/, gitignored). Prints §2/§3.
  compare              -- Step-1b audit: build the trading_day frame and diff it
                          against the raw reference row-by-row, with an ET-hour
                          breakdown of what moved (session-boundary correction).

Run: backend/.venv/Scripts/python.exe experiments/prop_intraday_resolver_v0/verify_phase1.py smoke
     backend/.venv/Scripts/python.exe experiments/prop_intraday_resolver_v0/verify_phase1.py compare
"""

from __future__ import annotations

import _paths  # noqa: F401
import datetime as _dt
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import events
import pipeline
import resolver
import zone_events as ze

REF_PARQUET = "market_state/out/zone_events_ES.parquet"
DATA_COLS = [
    "level",
    "dir",
    "ofi_signed",
    "qimb_signed",
    "svol_signed",
    "nq_ofi",
    "rty_ofi",
    "ym_ofi",
    "label",
]
ET = ZoneInfo("America/New_York")


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize to a row-aligned frame: ts as a column, sorted by (ts, level, dir)."""
    d = df.reset_index()
    if "ts" not in d.columns:
        cand = [c for c in ("index", "level_0") if c in d.columns]
        if cand:
            d = d.rename(columns={cand[0]: "ts"})
    d["ts"] = pd.to_datetime(d["ts"], utc=True)
    return d.sort_values(["ts", "level", "dir"]).reset_index(drop=True)


def _compare(a: pd.DataFrame, b: pd.DataFrame, label: str) -> bool:
    a, b = _norm(a), _norm(b)
    ok = True
    if len(a) != len(b):
        print(f"  [{label}] LENGTH MISMATCH: pipeline={len(a)} reference={len(b)}")
        ok = False
    missing = (set(DATA_COLS) - set(a.columns)) | (set(DATA_COLS) - set(b.columns))
    if missing:
        print(f"  [{label}] MISSING COLUMNS: {sorted(missing)}")
        return False
    n = min(len(a), len(b))
    cols = ["ts"] + DATA_COLS
    try:
        pd.testing.assert_frame_equal(
            a.iloc[:n][cols],
            b.iloc[:n][cols],
            check_like=True,
            check_dtype=False,
            rtol=1e-6,
            atol=1e-9,
        )
        if ok:
            print(f"  [{label}] EXACT MATCH on {n} rows, {len(DATA_COLS)} columns")
    except AssertionError as e:
        ok = False
        print(f"  [{label}] VALUE MISMATCH:\n{str(e)[:1500]}")
    return ok


def smoke(n: int = 6) -> int:
    levels = events.precompute_levels()
    days = events.available_days()
    idx = np.linspace(0, len(days) - 1, n).round().astype(int)
    sample = [days[i] for i in sorted(set(idx.tolist()))]
    print(
        f"SMOKE: decomposed pipeline vs zone_events.process_day on {len(sample)} days "
        f"({sample[0]}..{sample[-1]})"
    )
    a_rows, b_rows = [], []  # a = ours, b = original
    for day in sample:
        lv = levels.get(_dt.date.fromisoformat(day))
        if not lv:
            continue
        b_rows += ze.process_day(day, lv["pdh"], lv["pdl"])
        ctx = events.load_day(ze.SYM, day, reader="raw")  # pinned: this proves the
        if ctx is not None:  # decomposition == market_state
            a_rows += pipeline._process_day(ctx, lv["pdh"], lv["pdl"])
    A, B = pd.DataFrame(a_rows), pd.DataFrame(b_rows)
    print(f"  rows: pipeline={len(A)}  original={len(B)}")
    ok = _compare(A, B, "smoke")
    print("SMOKE PASS\n" if ok else "SMOKE FAIL\n")
    return 0 if ok else 1


def _ref_path(reader: str):
    # raw -> the market_state Stage-1 parquet (audit); trading_day -> local canonical (gitignored)
    return (
        REF_PARQUET
        if reader == "raw"
        else str(pipeline.OUT / "events_ES_trading_day.parquet")
    )


def full(reader: str = "trading_day") -> int:
    print(
        f"FULL [{reader}]: running pipeline.run_research over all days (heavy step)..."
    )
    df = pipeline.run_research(reader=reader, write=False)
    refpath = _ref_path(reader)
    if pd.io.common.file_exists(refpath):
        ref = pd.read_parquet(refpath)
        print(f"\nframe check: pipeline n={len(df)}  reference n={len(ref)}")
        ok = _compare(df, ref, f"full-{reader}")
    else:
        from pathlib import Path

        Path(refpath).parent.mkdir(parents=True, exist_ok=True)
        (
            df.set_index("ts").to_parquet(refpath)
            if "ts" in df.columns
            else df.to_parquet(refpath)
        )
        print(
            f"\nno reference yet — wrote {refpath} as the canonical {reader} frame (n={len(df)})"
        )
        ok = True
    print("\nReproduced SPEC §2 (per-feature forward test):")
    resolver.per_feature_forward_test(df)
    print("\nReproduced SPEC §3 (judge):")
    resolver.judge(df)
    print(
        f"\nFULL [{reader}] PASS.\n"
        if ok
        else f"\nFULL [{reader}] FAIL — frame differs from reference.\n"
    )
    return 0 if ok else 1


def compare_readers() -> int:
    """Step 1b: build the trading-day frame and diff it against the raw reference,
    row by row, with an ET-hour breakdown of what moved (and why)."""
    print("COMPARE: building TRADING-DAY frame (full scan, heavy)...")
    clean = pipeline.run_research(
        reader="trading_day", write=True, out_name="events_ES_trading_day.parquet"
    )
    raw = pd.read_parquet(REF_PARQUET)
    a, b = _norm(clean), _norm(raw)  # a = trading_day, b = raw reference

    print(
        f"\nrow counts: trading_day={len(a)}  raw_reference={len(b)}  delta={len(a) - len(b):+d}"
    )
    a = a.assign(key=list(zip(a["ts"], a["level"])))
    b = b.assign(key=list(zip(b["ts"], b["level"])))
    ka, kb = set(a["key"]), set(b["key"])
    only_clean = a[a["key"].isin(ka - kb)]
    only_raw = b[b["key"].isin(kb - ka)]
    print(
        f"  only in trading_day: {len(only_clean)}   only in raw: {len(only_raw)}   "
        f"common (ts,level): {len(ka & kb)}"
    )

    m = a.merge(b, on=["ts", "level"], suffixes=("_c", "_r"))
    label_flip = m[m["label_c"] != m["label_r"]]
    dir_flip = m[m["dir_c"] != m["dir_r"]]
    ofi_chg = m[(m["ofi_signed_c"] - m["ofi_signed_r"]).abs() > 1e-6]
    print(
        f"  common rows: label flip={len(label_flip)}  dir flip={len(dir_flip)}  "
        f"ofi changed={len(ofi_chg)}"
    )

    moved = pd.concat(
        [only_clean.assign(src="only_clean"), only_raw.assign(src="only_raw")]
    )
    if len(moved):
        moved = moved.assign(
            et_hour=pd.to_datetime(moved["ts"], utc=True).dt.tz_convert(ET).dt.hour
        )
        print(
            "\n  only/moved rows by ET hour (confirms session-boundary re-attribution):"
        )
        print(
            moved.groupby(["et_hour", "src"]).size().unstack(fill_value=0).to_string()
        )

    print("\nTRADING-DAY reproduced SPEC §2:")
    resolver.per_feature_forward_test(clean)
    print("\nTRADING-DAY reproduced SPEC §3:")
    resolver.judge(clean)

    identical = (len(a) == len(b)) and not (ka ^ kb) and len(label_flip) == 0
    print(
        "\nIDENTICAL — reader swap is a no-op; safe to make trading_day the default.\n"
        if identical
        else "\nMOVED — reader swap changed the event set (expected: session-boundary "
        "re-attribution). Review the ET-hour table + numbers above before committing.\n"
    )
    return 0 if identical else 3


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "smoke"
    if mode == "smoke":
        return smoke(int(argv[2]) if len(argv) > 2 else 6)
    if mode == "full":
        return full(argv[2] if len(argv) > 2 else "trading_day")
    if mode == "compare":
        return compare_readers()
    print(
        f"unknown mode {mode!r}; use 'smoke [N]', 'full [raw|trading_day]', or 'compare'"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
