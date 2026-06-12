# Sim fill ground-truth protocol (Ben runs this on the Lucid sim — ~10 minutes)

Goal: pin down the THREE numbers the sim-venue spec depends on. Use MES/M2K or 1-lot
ES/RTY on an EVAL or practice account you don't mind marking up. Do it during RTH on a
quiet-ish stretch. Have the DOM visible so you can see prints at your price.

## Test 1 — does a TOUCH fill a resting limit? (the big one)
1. Pick a price 4–8 ticks below the current bid. Rest a BUY LIMIT there.
2. Wait for price to come down and TAG your price (best bid = your price, maybe a few
   prints AT it) WITHOUT trading through (price bounces off it).
3. Record which of these was true at the moment you got filled (or didn't):
   - [ ] filled the instant the bid/last reached my price (touch-fill — most generous)
   - [ ] filled when trades PRINTED at my price (trade-at-price)
   - [ ] only filled when price traded THROUGH my price (strictest — same as our real-FIFO lower bound)
   - [ ] not filled at all on a clean tap
4. Repeat 3–5 times (different levels). One observation is luck; five is a rule.

## Test 2 — stop slippage
1. While in a position from test 1, leave a stop 4–8 ticks away.
2. When it triggers, compare fill price vs stop price. Record the slippage in ticks
   over 3–5 stop-outs — including at least one during a fast move if you can.
   (Our real-FIFO model charged the observed gapped quote ≈ +1.5–2 ticks; if sim gives
   you the stop price flat, that alone is worth ~2 ticks/trade.)

## Test 3 — target limit
1. In a position, rest your take-profit limit 2 ticks away (the income-shape target).
2. Does it fill when price touches the target once, or does it need prints/trade-through?
   This decides whether the 2-tick-target cells (+1.4 net, 97–99% win) are real in sim.

## Also note
- Which feed/engine the 20 copied accounts actually run (Rithmic vs Tradovate vs
  ProjectX) — fill engines differ and the copier's follower accounts may differ from
  the leader.
- Whether fills differ between eval and funded-sim stages.

Report back the three checkboxes + slippage numbers and the sim-spec manifest gets
pinned to the verified rule (no holdout spent until then).
