"""Quote Databento cost across time windows / schemas / symbols so the cost curve is concrete."""
import os
import databento as db

c = db.Historical(key=os.environ["DATABENTO_API_KEY"])


def q(syms, sch, s, e, label):
    try:
        cost = c.metadata.get_cost(dataset="GLBX.MDP3", symbols=syms, stype_in="continuous",
                                   schema=sch, start=s, end=e)
        print(f"{label:52s} ${cost:,.2f}")
    except Exception as ex:
        print(f"{label:52s} ERR {type(ex).__name__}: {ex}")


print("=== MBP-1 (top-of-book; what we pulled for crypto) ===")
q(["ETH.c.0", "BTC.c.0", "MBT.c.0"], "mbp-1", "2025-05-01", "2026-06-10", "crypto 3sym 13mo (WHAT WE PULLED = $9.43)")
q(["BTC.c.0"], "mbp-1", "2018-01-01", "2026-06-10", "BTC alone, full history 2018+")
q(["ETH.c.0", "BTC.c.0", "MBT.c.0"], "mbp-1", "2021-01-01", "2026-06-10", "crypto 3sym, full history 2021+")
q(["ES.c.0"], "mbp-1", "2025-05-01", "2026-06-10", "ES alone 13mo (high-volume compare)")
q(["ES.c.0"], "mbp-1", "2015-01-01", "2026-06-10", "ES alone, FULL 11yr")
q(["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"], "mbp-1", "2015-01-01", "2026-06-10", "4 indices MBP-1, FULL 11yr")
print("=== MBO (full order book; the heavy one) ===")
q(["ES.c.0"], "mbo", "2025-05-01", "2026-06-10", "ES MBO, 13mo")
q(["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"], "mbo", "2024-01-01", "2026-06-10", "4 indices MBO, 2.5yr")
