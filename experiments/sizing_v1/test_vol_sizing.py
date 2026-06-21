"""Sanity test for vol_targeted sizing (the keystone).

Verifies: (1) hard drawdown safety — realized risk never exceeds the risk budget;
(2) vol-targeting — higher ATR -> fewer contracts; (3) conviction -> more contracts;
(4) drawdown headroom -> fewer near the limit; (5) no-ATR fallback = 1 lot.
Also shows the prop reality: minis vs micros on small vs large accounts.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sizing import size_position, POINT_VALUE

P = {"stop_atr_mult": 0.5, "risk_per_trade_pct": 0.004, "max_dd_risk_pct": 0.10, "conviction_scale": True}
HI = np.array([0.20, 0.70, 0.10])   # high directional conviction
LO = np.array([0.45, 0.50, 0.05])   # low conviction (just over a 0.45 threshold)
THR = 0.45


def vt(p, atr, pv, ddb, bal, params=P, cap=50):
    return size_position(method="vol_targeted", p_proba=p, threshold=THR, params=params,
                         max_position_size=cap, ctx={"atr": atr, "point_value": pv, "dd_buffer": ddb, "balance": bal})


def budget(ddb, bal, params=P):
    return min(params["risk_per_trade_pct"] * bal, params["max_dd_risk_pct"] * ddb)


print(f"{'scenario':38s} {'contracts':>9s} {'$risk/ctr':>9s} {'budget$':>8s} {'realized$':>9s}")
rows = [
    ("NQ mini  50k/$2k DD  conf.70 atr300", HI, 300, POINT_VALUE["NQ.c.0"], 2000, 50000),
    ("MNQ micro 50k/$2k DD conf.70 atr300", HI, 300, POINT_VALUE["MNQ.c.0"], 2000, 50000),
    ("MNQ micro 150k/$10k  conf.70 atr300", HI, 300, POINT_VALUE["MNQ.c.0"], 10000, 150000),
    ("MNQ micro 150k/$10k  conf.70 atr150", HI, 150, POINT_VALUE["MNQ.c.0"], 10000, 150000),  # low vol
    ("MNQ micro 150k/$10k  conf.70 atr450", HI, 450, POINT_VALUE["MNQ.c.0"], 10000, 150000),  # high vol
    ("MNQ micro 150k/$10k  conf.50 atr300", LO, 300, POINT_VALUE["MNQ.c.0"], 10000, 150000),  # low conf
    ("MNQ micro NEAR DD $500  conf.70    ", HI, 300, POINT_VALUE["MNQ.c.0"], 500, 150000),     # near limit
    ("NQ mini tight stop .15atr 150k/$10k", HI, 300, POINT_VALUE["NQ.c.0"], 10000, 150000, {**P, "stop_atr_mult": 0.15}),
]
results = {}
for r in rows:
    name, p, atr, pv, ddb, bal = r[:6]
    params = r[6] if len(r) > 6 else P
    c = vt(p, atr, pv, ddb, bal, params)
    rpc = params["stop_atr_mult"] * atr * pv
    b = budget(ddb, bal, params)
    realized = c * rpc
    results[name.strip()] = c
    flag = "  !! OVER BUDGET" if realized > b + 1e-6 else ""
    print(f"{name:38s} {c:>9d} {rpc:>9.0f} {b:>8.0f} {realized:>9.0f}{flag}")
    assert realized <= b + 1e-6, f"DRAWDOWN SAFETY VIOLATED: {name}"

# fallback: no atr -> 1
fb = vt(HI, None, POINT_VALUE["NQ.c.0"], 10000, 150000)
print(f"\nno-ATR fallback contracts = {fb} (expect 1)")

print("\n--- invariants ---")
k = list(results)
assert results["MNQ micro 150k/$10k  conf.70 atr150"] >= results["MNQ micro 150k/$10k  conf.70 atr450"], "vol-targeting broken (hi-vol should size smaller)"
print("  ok: higher ATR -> fewer contracts (vol-targeting)")
assert results["MNQ micro 150k/$10k  conf.70 atr300"] >= results["MNQ micro 150k/$10k  conf.50 atr300"], "conviction scaling broken"
print("  ok: higher conviction -> more contracts")
assert results["MNQ micro 150k/$10k  conf.70 atr300"] > results["MNQ micro NEAR DD $500  conf.70"], "drawdown cap not binding near limit"
print("  ok: smaller drawdown buffer -> fewer contracts (DD cap binds)")
assert fb == 1, "no-atr fallback should be 1"
print("  ok: no-ATR fallback = 1 lot")
print("  ok: NO scenario exceeded its risk budget (hard drawdown safety holds)")
print("\nALL CHECKS PASSED")
