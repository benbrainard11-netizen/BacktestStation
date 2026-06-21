"""Quote MBO (full order book) cost for crypto symbols across windows."""
import os
import databento as db

c = db.Historical(key=os.environ["DATABENTO_API_KEY"])


def q(syms, s, e, label):
    try:
        cost = c.metadata.get_cost(dataset="GLBX.MDP3", symbols=syms, stype_in="continuous",
                                   schema="mbo", start=s, end=e)
        print(f"{label:50s} ${cost:,.2f}")
    except Exception as ex:
        print(f"{label:50s} ERR {type(ex).__name__}: {ex}")


print("=== CRYPTO MBO (full order book) ===")
q(["BTC.c.0"], "2025-05-01", "2026-06-10", "BTC MBO, 13mo (match what we pulled mbp1)")
q(["ETH.c.0", "BTC.c.0", "MBT.c.0"], "2025-05-01", "2026-06-10", "crypto 3sym MBO, 13mo")
q(["BTC.c.0"], "2018-01-01", "2026-06-10", "BTC MBO, full history 2018+")
q(["ETH.c.0", "BTC.c.0", "MBT.c.0"], "2021-01-01", "2026-06-10", "crypto 3sym MBO, full history")
print("=== compare: crypto MBP-1 we pulled = $9.73 ; ES MBO 13mo = $305.85 ===")
