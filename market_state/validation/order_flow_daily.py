"""DAILY order-flow feature for ES from MBP-1 -> forward-tested through the harness.

HONEST PRIORS (do NOT manufacture a daily edge):
  - Mira's MBO edge is INTRADAY (tsfm_milk_v0); bar-based daily order flow tested DEAD
    (orderflow_divergence_v0); the MBP-1 window is ~13 months = ~270 trading days = LOW power.
  - The likely + ACCEPTABLE conclusion is: "daily order flow does NOT forward-predict" ->
    the ORDER-FLOW tile stays GREY with a now-evidenced reason, and order flow is reserved
    as an INTRADAY axis for a future intraday view.

What we build (well-defined, no-lookahead):
  Per UTC date d, from ES MBP-1 events:
    - net_signed_vol  = sum over TRADE events of (+size if aggressor B, -size if A)
    - signed_imb      = net_signed_vol / total_trade_vol     (scale-free)
    - ofi             = Cont-Kukanov order-flow imbalance from best bid/ask size+price changes
    - close           = last trade price of d ; ret_d = log(close_d / close_{d-1})
  Feature at d uses ONLY day-d events (known by d's close). Outcomes are STRICTLY day d+1:
    - next-day return  ret_{d+1}
    - next-day abs return |ret_{d+1}|  (a vol proxy)
  We deliberately aggregate the feature AND the return from the SAME MBP-1 source + UTC-date
  boundary, so there is no cross-source roll/boundary contamination. (UTC date splits the
  Globex session, but feature and outcome share the boundary, so the test is internally clean.)

Two-step: `extract` (slow, day-by-day, caches out/of_daily_ES.parquet) then `test` (fast).
Run extract once:  backend/.venv/Scripts/python.exe market_state/validation/order_flow_daily.py extract
Then the test:     backend/.venv/Scripts/python.exe market_state/validation/order_flow_daily.py test
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, "backend")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.data.reader import read_mbp1  # noqa: E402
from harness import forward_test, print_result  # noqa: E402

SYMBOL = "ES.c.0"
MBP1_ROOT = Path("D:/data/raw/databento/mbp-1/symbol=ES.c.0")
CACHE = Path("market_state/out/of_daily_ES.parquet")
OF_COLS = ["action", "side", "price", "size", "bid_px", "ask_px", "bid_sz", "ask_sz"]
OOS_FRAC = 2.0 / 3.0   # ~13mo window -> hold out the last third as OOS (task rule)
MIN_FWD_EFFECT = 0.10  # OOS Spearman floor to call a daily-OF relationship REAL
# UTC-date partitioning gives Sunday-Globex-open + holidays their own THIN partitions (median
# ~19k trade vol vs ~1.18M on real days). Those are not full sessions -> drop them so the daily
# return + OF features aren't holiday noise. Floor at 100k contracts (well below real-day median).
MIN_TRADE_VOL = 100_000


def _partition_dates() -> list[dt.date]:
    out = []
    for p in sorted(MBP1_ROOT.glob("date=*")):
        try:
            out.append(dt.date.fromisoformat(p.name.split("=", 1)[1]))
        except ValueError:
            continue
    return out


def _daily_features(df: pd.DataFrame) -> dict:
    """All scalar order-flow features for one day's MBP-1 events."""
    is_trade = df["action"].to_numpy() == "T"
    side = df["side"].to_numpy()
    size = df["size"].to_numpy().astype(float)
    sgn = np.where(side == "B", 1.0, np.where(side == "A", -1.0, 0.0))
    tvol = float(size[is_trade].sum())
    net = float((sgn[is_trade] * size[is_trade]).sum())

    bpx, apx = df["bid_px"].to_numpy(), df["ask_px"].to_numpy()
    bsz, asz = df["bid_sz"].to_numpy().astype(float), df["ask_sz"].to_numpy().astype(float)
    # Cont-Kukanov OFI on the best level: bid contributes +size on up-tick / -prev on down-tick.
    d_bid = np.where(bpx[1:] > bpx[:-1], bsz[1:], np.where(bpx[1:] < bpx[:-1], -bsz[:-1], bsz[1:] - bsz[:-1]))
    d_ask = np.where(apx[1:] < apx[:-1], asz[1:], np.where(apx[1:] > apx[:-1], -asz[:-1], asz[1:] - asz[:-1]))
    ofi = float(np.nansum(d_bid - d_ask))

    tpx = df["price"].to_numpy()[is_trade]
    close = float(tpx[-1]) if tpx.size else float("nan")
    return {"net_signed_vol": net, "total_trade_vol": tvol,
            "signed_imb": net / tvol if tvol > 0 else float("nan"),
            "ofi": ofi, "close": close, "n_events": int(len(df))}


def extract() -> int:
    dates = _partition_dates()
    print(f"extracting daily order flow for {SYMBOL}: {len(dates)} partitions "
          f"({dates[0]}..{dates[-1]})")
    rows = []
    for i, d in enumerate(dates):
        nxt = d + dt.timedelta(days=1)
        df = read_mbp1(symbol=SYMBOL, start=d.isoformat(), end=nxt.isoformat(), columns=OF_COLS)
        if len(df) == 0:
            continue
        feat = _daily_features(df)
        feat["date"] = pd.Timestamp(d)
        rows.append(feat)
        if (i + 1) % 25 == 0 or i == len(dates) - 1:
            print(f"  {i + 1}/{len(dates)}  {d}  events={feat['n_events']:,}  "
                  f"signed_imb={feat['signed_imb']:+.3f}  ofi={feat['ofi']:,.0f}")
    out = pd.DataFrame(rows).set_index("date").sort_index()
    out["ret"] = np.log(out["close"]).diff()  # close-to-close, same-source boundary
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(CACHE)
    print(f"\nwrote {CACHE}  ({len(out)} days)")
    # sanity: same-day imbalance vs same-day return SHOULD be positive (buyers lift price),
    # measured on REAL sessions only (thin Sunday/holiday partitions excluded).
    real = out[out["total_trade_vol"] >= MIN_TRADE_VOL].copy()
    real["ret"] = np.log(real["close"]).diff()
    same = real[["signed_imb", "ret"]].dropna()
    print(f"SANITY corr(signed_imb_d, ret_d) = {same['signed_imb'].corr(same['ret']):+.3f} "
          f"(expect >0; validates the aggressor-sign convention), n={len(same)} real sessions "
          f"({len(out) - len(real)} thin partitions excluded)")
    return 0


def _frame(of: pd.DataFrame, sig: str, out_col: str) -> pd.DataFrame:
    f = pd.DataFrame({"signal": of[sig], "outcome": of[out_col]}).dropna()
    return f


def test() -> int:
    if not CACHE.exists():
        print(f"missing {CACHE} -- run `extract` first.")
        return 1
    raw = pd.read_parquet(CACHE).sort_index()
    n_raw = len(raw)
    of = raw[raw["total_trade_vol"] >= MIN_TRADE_VOL].copy()
    # recompute close-to-close return on the FILTERED (real-session) series so ret/ret_next
    # bridge consecutive real days, not a thin Sunday partition.
    of["ret"] = np.log(of["close"]).diff()
    print(f"  dropped {n_raw - len(of)} thin partitions (<{MIN_TRADE_VOL:,} trade vol; "
          f"Sunday-Globex/holidays); {len(of)} real sessions remain.")
    of["ret_next"] = of["ret"].shift(-1)            # STRICTLY next day
    of["absret_next"] = of["ret"].shift(-1).abs()   # next-day vol proxy
    of["signed_imb_abs"] = of["signed_imb"].abs()
    of["ret_same"] = of["ret"]  # for the contemporaneous pipe-validation control
    split = of.index[int(len(of) * OOS_FRAC)]
    print("=" * 78)
    print(f"  ORDER-FLOW daily tile -- ES MBP-1 {of.index.min().date()}..{of.index.max().date()}, "
          f"n={len(of)} days (OOS>= {split.date()})")
    print("=" * 78)

    # The CONTROL is CONTEMPORANEOUS (signed_imb_d -> ret_d, same day): it must be clearly
    # positive (buyers lift price), proving the OF extraction + aggressor-sign + return pipe
    # are correct. It is NOT a forward test -- this 270-day window is too short to demonstrate
    # forward vol persistence OOS (verified: filtered 5d-vol persistence is fragile here, which
    # is itself the low-power message). So the control validates the PIPE, not forward skill.
    tests = [
        ("signed_imb -> next-day return", "signed_imb", "ret_next", 1, False),
        ("ofi -> next-day return", "ofi", "ret_next", 1, False),
        ("net_signed_vol -> next-day return", "net_signed_vol", "ret_next", 1, False),
        ("|signed_imb| -> next-day |return| (vol)", "signed_imb_abs", "absret_next", 1, False),
        ("CONTROL (same-day pipe): signed_imb_d -> ret_d", "signed_imb", "ret_same", 1, True),
    ]
    any_pass, control_pass = False, False
    for name, sig, out_col, sign, is_ctrl in tests:
        r = forward_test(_frame(of, sig, out_col), name=name, kind="continuous",
                         oos_start=split, min_effect=(0.05 if is_ctrl else MIN_FWD_EFFECT),
                         expect_sign=sign)
        print_result(r)
        if is_ctrl:
            control_pass = (r.verdict == "PASS")
        else:
            any_pass = any_pass or (r.verdict == "PASS")

    _verdict(any_pass, control_pass)
    return 0


def _verdict(any_pass: bool, control_pass: bool) -> None:
    print("\n" + "=" * 78)
    if any_pass:
        print("  ORDER-FLOW tile: a daily OF relationship PASSED -- investigate before trusting "
              "(prior says NULL; n is small).")
    else:
        print("  ORDER-FLOW tile stays GREY: daily order flow does NOT forward-predict next-day")
        print("  return or vol OOS at this (~13mo, ~270-day) sample. Consistent with the prior --")
        print("  order flow is an INTRADAY axis (Mira's MBO edge), not a daily tile. EVIDENCED null.")
    ctrl_msg = ("same-day pipe CONTROL PASSED (signed_imb_d -> ret_d positive) -> the OF "
                "extraction + sign convention + return are CORRECT, so the forward null is a "
                "true null, not a broken pipe. (270 days is too short to also demo forward vol "
                "persistence OOS -- that low power is part of the honest message.)"
                if control_pass else
                "WARNING: even the same-day pipe control failed -- the OF extraction may be wrong; "
                "do not trust the null until this is understood.")
    print(f"  {ctrl_msg}")
    print("=" * 78)


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "test"
    if cmd == "extract":
        return extract()
    if cmd == "test":
        return test()
    print("usage: order_flow_daily.py [extract|test]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
