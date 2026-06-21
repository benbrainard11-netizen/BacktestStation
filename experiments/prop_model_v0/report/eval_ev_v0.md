# Layer 1 — eval-EV per firm at PINNED per-trade edge (0 / +0.05R / +0.10R)

## EV per campaign ($) by edge level
edge_r      0.00    0.05     0.10
firm                             
apex       354.0  2239.0   5652.0
lucid     1031.0  2987.0   8724.0
mffu       929.0  2528.0   7716.0
topstep    989.0  3034.0   9838.0
tpt        365.0  1642.0   6205.0
tradeify   535.0  3083.0  10966.0

## Best config per firm x edge
    firm  p_pass  days_to_pass  cost_to_funded  v_funded      ev          shape  risk  edge_r  excluded  fleet_cap
 topstep   0.346           5.4           291.0    1279.0   989.0 p0.500/R1.0/n2   900    0.00     False          5
 topstep   0.327           4.1           299.0    3332.0  3034.0 p0.525/R1.0/n4   900    0.05     False          5
 topstep   0.409           4.2           269.0   10107.0  9838.0 p0.550/R1.0/n4   900    0.10     False          5
   lucid   0.444           6.8           267.0    1298.0  1031.0 p0.500/R1.0/n2   900    0.00     False         10
   lucid   0.422          35.3           274.0    3261.0  2987.0 p0.525/R1.0/n4   150    0.05     False         10
   lucid   0.690          33.1           214.0    8938.0  8724.0 p0.550/R1.0/n4   150    0.10     False         10
    apex   0.249          14.2           461.0     814.0   354.0 p0.500/R1.0/n2   400    0.00     False         20
    apex   0.160          21.8           660.0    2899.0  2239.0 p0.525/R1.0/n4   150    0.05     False         20
    apex   0.368          20.0           344.0    5996.0  5652.0 p0.440/R1.5/n4   150    0.10     False         20
    mffu   0.438           6.5           359.0    1288.0   929.0 p0.500/R1.0/n2   900    0.00     False          5
    mffu   0.427          35.9           368.0    2896.0  2528.0 p0.525/R1.0/n4   150    0.05     False          5
    mffu   0.707          33.3           222.0    7938.0  7716.0 p0.550/R1.0/n4   150    0.10     False          5
tradeify   0.286          10.6           382.0     917.0   535.0 p0.500/R1.0/n2   600    0.00     False          5
tradeify   0.449          18.8           262.0    3344.0  3083.0 p0.525/R1.0/n4   250    0.05     False          5
tradeify   0.632          17.0           200.0   11167.0 10966.0 p0.550/R1.0/n4   250    0.10     False          5
     tpt   0.308           6.7           683.0    1047.0   365.0 p0.500/R1.0/n2   900    0.00      True          5
     tpt   0.415          35.6           950.0    2592.0  1642.0 p0.525/R1.0/n4   150    0.05      True          5
     tpt   0.696          33.3           618.0    6823.0  6205.0 p0.550/R1.0/n4   150    0.10      True          5

ev = expected $ per campaign (fees in; funded life capped 252d; trader split
applied). Conservative: losses-first intraday breaches, iid trades, fixed
risk, greedy payouts. Apex at street fee $90 (list $450: ev -$360).
TPT excluded from fleet (bots banned) — reference row only.