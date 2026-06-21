"""Export recent should-have-fired rows through the actual live replay path.

This is the apples-to-apples path for live under-trading:
    compute_candidates -> frozen Gate(0.5818) -> LiveEngine.consider -> signal entry/exit

Unlike recent_setups_export.py, this does NOT restrict to post_sweep_smt.
The standalone live engine scores every candidate row, so this file does the
same and records whether each candidate gated, armed, entered, and exited.

No live/Rithmic connection is made. Historical Databento MBO trade prints drive
the signal in sim, matching live_runner.replay_session.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ENGINE = REPO / "live_engine" / "engine"
sys.path.insert(0, str(ENGINE))

import detect as D  # noqa: E402
import exec as exec_mod  # noqa: E402
import run as run_mod  # noqa: E402

MBO_CLEAN_ROOT = Path(r"D:\data\clean\databento\mbo_trading_day")
OUTDIR = HERE / "out" / "mira_short_revalidation"
DEFAULT_SYMBOLS = ("ES.c.0", "NQ.c.0", "RTY.c.0", "YM.c.0")
MARG_HI = 0.66


def date_range(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)


def split_symbols(value: str) -> list[str]:
    return [part.strip() for part in value.replace(" ", ",").split(",") if part.strip()]


def direction_from_anchor(anchor_side: object) -> int:
    return 1 if str(anchor_side) == "low" else -1


def direction_label(direction: int) -> str:
    return "long" if int(direction) == 1 else "short"


def as_utc_timestamp(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def trade_prints(symbol: str, day: dt.date) -> pd.DataFrame:
    path = MBO_CLEAN_ROOT / f"symbol={symbol}" / f"trading_day={day.isoformat()}" / "part-000.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["ts_event", "price"])
    df = pd.read_parquet(path, columns=["ts_event", "action", "price"])
    df = df[df["action"].astype(str) == "T"].copy()
    if df.empty:
        return pd.DataFrame(columns=["ts_event", "price"])
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    return df.sort_values("ts_event").reset_index(drop=True)


def base_rows(cands: pd.DataFrame, *, symbol: str, day: dt.date, gate) -> pd.DataFrame:
    c = cands.copy()
    c["trigger_ts_utc"] = pd.to_datetime(c["trigger_ts_utc"], utc=True)
    c = c.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable").reset_index(drop=True)
    c["candidate_idx"] = np.arange(len(c), dtype=int)
    c["date"] = day.isoformat()
    c["symbol"] = symbol
    c["direction_int"] = [direction_from_anchor(x) for x in c["smt_anchor_side"]]
    c["direction"] = [direction_label(x) for x in c["direction_int"]]
    c["gate_score"] = gate.score(c)
    c["gated"] = c["gate_score"] >= gate.threshold
    c["marginal"] = (c["gate_score"] >= gate.threshold) & (c["gate_score"] <= MARG_HI)
    c["armed"] = False
    c["entered"] = False
    c["exited"] = False
    c["cancelled"] = False
    c["blocked_reason"] = None
    c["entry_ts_utc"] = pd.Series([None] * len(c), dtype="object")
    c["exit_ts_utc"] = pd.Series([None] * len(c), dtype="object")
    c["entry_px"] = np.nan
    c["stop_px"] = np.nan
    c["risk_points"] = np.nan
    c["exit_px"] = np.nan
    c["r_signal_gross"] = np.nan
    return c


def replay_symbol_day(symbol: str, day: dt.date, cfg: dict) -> pd.DataFrame:
    cands = D.compute_candidates(symbol, day, day, sweep_quality=None)
    if cands is None or cands.empty:
        return pd.DataFrame()

    engine = run_mod.LiveEngine(cfg, executor=exec_mod.Executor(cfg, live=False))
    rows = base_rows(cands, symbol=symbol, day=day, gate=engine.gate)
    prints = trade_prints(symbol, day)
    if prints.empty:
        rows.loc[rows["gated"], "blocked_reason"] = "no_trade_prints"
        return rows

    trig_arr = rows["trigger_ts_utc"].to_numpy()
    px_arr = prints["price"].astype(float).to_numpy()
    ts_arr = prints["ts_event"].to_numpy()
    armed_idx_by_symbol: dict[str, int] = {}
    in_pos_idx_by_symbol: dict[str, int] = {}
    ci = 0
    n = len(rows)

    for k in range(len(prints)):
        ts = pd.Timestamp(ts_arr[k]).to_pydatetime()
        px = float(px_arr[k])

        while ci < n and trig_arr[ci] <= ts_arr[k]:
            row = rows.iloc[ci]
            idx = int(row["candidate_idx"])
            if not bool(row["gated"]):
                rows.at[idx, "blocked_reason"] = "below_gate"
                ci += 1
                continue
            busy = symbol in engine.open_symbols or symbol in engine.armed
            accepted = engine.consider(row)
            if accepted:
                rows.at[idx, "armed"] = True
                armed_idx_by_symbol[symbol] = idx
            elif busy:
                rows.at[idx, "blocked_reason"] = "symbol_busy"
            else:
                rows.at[idx, "blocked_reason"] = "risk_or_state_block"
            ci += 1

        before = len(engine.exec.orders)
        engine.on_quote(symbol, ts, bid=px, ask=px)
        for order in engine.exec.orders[before:]:
            if order.kind == "enter":
                idx = armed_idx_by_symbol.get(symbol)
                if idx is None:
                    continue
                rows.at[idx, "entered"] = True
                rows.at[idx, "entry_ts_utc"] = as_utc_timestamp(ts)
                rows.at[idx, "entry_px"] = float(order.price)
                rows.at[idx, "stop_px"] = float(order.stop_px)
                rows.at[idx, "risk_points"] = abs(float(order.price) - float(order.stop_px))
                in_pos_idx_by_symbol[symbol] = idx
            elif order.kind == "exit":
                idx = in_pos_idx_by_symbol.pop(symbol, None)
                if idx is None:
                    continue
                rows.at[idx, "exited"] = True
                rows.at[idx, "exit_ts_utc"] = as_utc_timestamp(ts)
                rows.at[idx, "exit_px"] = float(order.price)
                rows.at[idx, "r_signal_gross"] = order.realized_R
                armed_idx_by_symbol.pop(symbol, None)

        for sym, idx in list(armed_idx_by_symbol.items()):
            if sym not in engine.armed and sym not in in_pos_idx_by_symbol and not bool(rows.at[idx, "entered"]):
                rows.at[idx, "cancelled"] = True
                armed_idx_by_symbol.pop(sym, None)

    rows.loc[rows["gated"] & rows["blocked_reason"].isna() & ~rows["armed"], "blocked_reason"] = "trigger_after_last_print"
    rows.loc[rows["armed"] & ~rows["entered"] & ~rows["cancelled"], "blocked_reason"] = "armed_no_entry_before_last_print"
    return rows


OUT_COLS = [
    "date",
    "trigger_ts_utc",
    "symbol",
    "trigger_type",
    "trigger_source",
    "direction",
    "smt_anchor_side",
    "trigger_price",
    "gate_score",
    "gated",
    "marginal",
    "armed",
    "entered",
    "exited",
    "cancelled",
    "blocked_reason",
    "entry_ts_utc",
    "entry_px",
    "stop_px",
    "risk_points",
    "exit_ts_utc",
    "exit_px",
    "r_signal_gross",
]


def daily_counts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[
            "date", "detected", "gated_long", "gated_short", "armed_long", "armed_short",
            "entered_long", "entered_short", "longs_only_armed", "longs_only_entered",
        ])
    rows = []
    for date, g in df.groupby("date", sort=True):
        rows.append({
            "date": date,
            "detected": int(len(g)),
            "gated_long": int((g["gated"] & g["direction"].eq("long")).sum()),
            "gated_short": int((g["gated"] & g["direction"].eq("short")).sum()),
            "armed_long": int((g["armed"] & g["direction"].eq("long")).sum()),
            "armed_short": int((g["armed"] & g["direction"].eq("short")).sum()),
            "entered_long": int((g["entered"] & g["direction"].eq("long")).sum()),
            "entered_short": int((g["entered"] & g["direction"].eq("short")).sum()),
            "longs_only_armed": int((g["armed"] & g["direction"].eq("long")).sum()),
            "longs_only_entered": int((g["entered"] & g["direction"].eq("long")).sum()),
        })
    return pd.DataFrame(rows)


def score_distribution(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, sub in [("all", df), ("longs_only", df[df["direction"].eq("long")])]:
        for basis, g in [("gated", sub[sub["gated"]]), ("armed", sub[sub["armed"]])]:
            rows.append({
                "scope": scope,
                "basis": basis,
                "n": int(len(g)),
                "marginal_n": int(g["marginal"].sum()) if len(g) else 0,
                "marginal_pct": float(g["marginal"].mean()) if len(g) else np.nan,
                "score_min": float(g["gate_score"].min()) if len(g) else np.nan,
                "score_median": float(g["gate_score"].median()) if len(g) else np.nan,
                "score_max": float(g["gate_score"].max()) if len(g) else np.nan,
            })
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, type=dt.date.fromisoformat)
    parser.add_argument("--end", required=True, type=dt.date.fromisoformat)
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    args = parser.parse_args()

    cfg = run_mod.load_config()
    symbols = split_symbols(args.symbols)
    frames = []
    for day in date_range(args.start, args.end):
        for symbol in symbols:
            print(f"[replay-export] {symbol} {day}", flush=True)
            part = replay_symbol_day(symbol, day, cfg)
            if part is not None and len(part):
                frames.append(part)
    if frames:
        df = pd.concat(frames, ignore_index=True)
    else:
        df = pd.DataFrame(columns=OUT_COLS)
    for col in OUT_COLS:
        if col not in df.columns:
            df[col] = np.nan
    df = df[OUT_COLS].sort_values(["trigger_ts_utc", "symbol"], na_position="last").reset_index(drop=True)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    csv = OUTDIR / "recent_live_replay_setups.csv"
    js = OUTDIR / "recent_live_replay_setups.json"
    counts = OUTDIR / "recent_live_replay_daily_counts.csv"
    dist = OUTDIR / "recent_live_replay_gate_distribution.csv"
    armed = OUTDIR / "recent_live_replay_armed_for_live_xref.csv"
    df.to_csv(csv, index=False)
    df.to_json(js, orient="records", date_format="iso", indent=2)
    daily = daily_counts(df)
    daily.to_csv(counts, index=False)
    score_distribution(df).to_csv(dist, index=False)
    df[df["armed"]].to_csv(armed, index=False)

    print(f"\nwrote {len(df)} rows -> {csv}")
    print(f"wrote daily counts -> {counts}")
    print(f"wrote gate distribution -> {dist}")
    print(f"wrote armed xref -> {armed}")
    if not daily.empty:
        print("\nDaily counts:")
        print(daily.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
