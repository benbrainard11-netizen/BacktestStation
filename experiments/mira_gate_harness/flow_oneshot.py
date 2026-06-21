"""ONE-SHOT validation of the frozen pre-trigger flow rule (w90_drift_dir_ticks >= 29.3333)
on the untouched Apr-Jun 2026 validation set. No other rule, no re-mining. This is the single shot."""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
df = pd.read_parquet(HERE / "runs" / "flow_at_scale_features.parquet")
df["decision_ts_utc"] = pd.to_datetime(df["decision_ts_utc"], utc=True)
df["mo"] = df["decision_ts_utc"].dt.month
val = df[df["mo"].isin([4, 5, 6])].copy()


def st(x):
    x = pd.to_numeric(x, errors="coerce").dropna()
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():4.1f}% sumR={x.sum():+6.1f}"


RULE = "w90_drift_dir_ticks"
THR = 29.3333
passed = val[val[RULE] >= THR]
print(f"VALIDATION (Apr-Jun 2026, n={len(val)}) — frozen rule {RULE} >= {THR}")
print(f"  ALL validation   {st(val['trail_2R'])}")
print(f"  RULE PASSES      {st(passed['trail_2R'])}")
print(f"  rule fails       {st(val[val[RULE] < THR]['trail_2R'])}")
print("  (design reference: rule-pass +0.073/46.6%/n=148 vs baseline -0.044)")
