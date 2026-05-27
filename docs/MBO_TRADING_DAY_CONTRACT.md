# MBO Trading Day Contract

Use this for MIRA, backtests, and orderflow research:

```text
D:\data\clean\databento\mbo_trading_day\symbol=ES.c.0\trading_day=2026-04-22\part-000.parquet
```

Each file is one full CME equity-index futures trading day:

```text
18:00 ET previous calendar day -> 17:00 ET trading-day date
```

For example, `trading_day=2026-04-22` is:

```text
2026-04-21 18:00 ET -> 2026-04-22 17:00 ET
2026-04-21 22:00 UTC -> 2026-04-22 21:00 UTC
```

## What Not To Use

Do not point model code directly at:

```text
D:\data\raw\databento\mbo\symbol=ES.c.0\date=2026-04-22\part-000.parquet
```

Those raw files are UTC-calendar storage partitions. They are valid source
files, but they are not trading days. They can also contain MBO snapshot
carry-in rows whose `ts_event` predates the UTC file date.

## Reader Rule

For Python code, use:

```python
from app.data import read_mbo_trading_day

df = read_mbo_trading_day(symbol="ES.c.0", trading_day="2026-04-22")
```

The reader prefers the clean trading-day cache when present.

For R2/collaborator code, use the client wrapper:

```python
from bsdata import load_mbo_trading_day

df = load_mbo_trading_day(symbol="ES.c.0", trading_day="2026-04-22")
```

The R2 key is the same clean contract:

```text
clean/databento/mbo_trading_day/symbol=ES.c.0/trading_day=2026-04-22/part-000.parquet
```

The cache manifest lives at:

```text
D:\data\clean\databento\mbo_trading_day\manifest_final.csv
```

It records row counts, file sizes, and any known source caveats. As of the
Jan-May 2026 build, only `trading_day=2026-05-18` has a source caveat:
Databento returned no data for the required Sunday UTC source date
`2026-05-17`, so that trading day starts with the first available Monday UTC
events.

## Snapshot Rule

The clean cache is for live orderflow/event research. It drops rows from a raw
UTC partition when `ts_event` is outside that raw partition's own UTC day. That
removes Databento MBO snapshot carry-in rows from the next file.

If a future project needs full L3 book reconstruction, build a separate
snapshot-aware reader that intentionally seeds the book with `R`/`A` snapshot
messages before applying live deltas.

## Level Naming Rule

Use explicit names:

```text
prev_td_high / prev_td_low       = previous full Globex trading day
prev_rth_high / prev_rth_low     = previous cash RTH only
curr_td_asia_high / low          = completed Asia in current trading day
curr_td_london_high / low        = completed London in current trading day
prev_td_asia_high / low          = Asia from previous trading day
```

Do not call a previous RTH level `PDH` or `PDL`.
