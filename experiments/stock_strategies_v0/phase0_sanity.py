"""Phase 0 sanity / tests for the equities-line loaders. Run:
  backend\\.venv\\Scripts\\python.exe experiments\\stock_strategies_v0\\phase0_sanity.py
Exits non-zero on any failure. Covers: loading, RTH filter, earnings join, the
no-lookahead guard (both directions), and MA causality.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

import common as C  # noqa: E402
import loaders as L  # noqa: E402

fails: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ok  " if cond else " FAIL ") + msg)
    if not cond:
        fails.append(msg)


print("== universe ==")
daily_u, etf_u = L.list_universe("daily"), L.list_universe("etf")
check(len(daily_u) > 400, f"daily universe = {len(daily_u)} (>400)")
check({"SPY", "QQQ", "XLK"}.issubset(set(etf_u)), f"etf layer has SPY/QQQ/XLK ({len(etf_u)})")

print("== daily loader ==")
d = L.load_daily("AAPL")
check(list(d.columns) == ["dt", "open", "high", "low", "close", "volume"], "AAPL daily cols")
check(d["dt"].is_monotonic_increasing and not d["dt"].duplicated().any(), "AAPL daily sorted/uniq")
check(d["dt"].min().year <= 2010, f"AAPL daily reaches {d['dt'].min().date()} (<=2010)")

print("== m1 loader (RTH) ==")
m = L.load_m1("AAPL")
check(len(m) > 0, "AAPL m1 loaded")
in_rth = ((m["ms_of_day"] >= C.RTH_OPEN_MS) & (m["ms_of_day"] < C.RTH_CLOSE_MS)).all()
check(bool(in_rth), "all m1 bars within [09:30,16:00) ET")
one = L.load_m1("AAPL", day=m["ts_et"].dt.date.iloc[-1])
check(one["ts_et"].dt.date.nunique() == 1, "m1 day-filter returns a single session")

print("== earnings ==")
e = L.load_earnings("AAPL")
check(len(e) > 0 and "when" in e.columns, "AAPL earnings rows + 'when' col")
check(set(e["when"].unique()).issubset({"AMC", "BMO", "INTRADAY"}), "earnings 'when' vocab")

print("== no-lookahead guard (must raise on violation, pass when legal) ==")
t0, t1 = pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")
raised = False
try:
    C.assert_no_lookahead(t1, t0, "test")  # feature AFTER decision -> must raise
except AssertionError:
    raised = True
check(raised, "assert_no_lookahead RAISES when feature_ts > decision_ts")
ok_legal = True
try:
    C.assert_no_lookahead(t0, t1, "test")  # feature BEFORE decision -> must pass
except AssertionError:
    ok_legal = False
check(ok_legal, "assert_no_lookahead passes when feature_ts <= decision_ts")

print("== history_up_to is causal ==")
asof = d["dt"].iloc[100]
h = L.history_up_to(d, asof)
check(h["dt"].max() <= asof and len(h) == 101, "history_up_to returns only rows <= asof")

print("== MA causality (row D uses only closes <= D) ==")
dm = L.with_mas(d.head(60))
i = 30
manual_ma10 = d["close"].iloc[i - 9 : i + 1].mean()  # closes D-9..D inclusive
check(abs(dm["ma10"].iloc[i] - manual_ma10) < 1e-6, "ma10[D] == mean(close[D-9..D])")
check(pd.isna(dm["ma10"].iloc[8]) and not pd.isna(dm["ma10"].iloc[9]), "ma10 NaN until 10 obs")

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILURE(S): " + "; ".join(fails)))
sys.exit(1 if fails else 0)
