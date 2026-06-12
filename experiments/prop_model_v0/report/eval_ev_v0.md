# Layer 1 — eval-EV per firm at PINNED per-trade edge (0 / +0.05R / +0.10R)

## EV per campaign ($) by edge level
edge_r      0.00    0.05     0.10
firm                             
apex       346.0  2041.0   5137.0
lucid     6235.0  9800.0  17587.0
mffu       617.0  2116.0   7010.0
topstep    701.0  2163.0   7177.0
tpt        210.0  1270.0   5478.0
tradeify  2687.0  5909.0  10651.0

## Best config per firm x edge
    firm  p_pass  days_to_pass  cost_to_funded  v_funded      ev          shape  risk  edge_r  excluded  fleet_cap
 topstep   0.316           4.8           304.0    1005.0   701.0 p0.500/R1.0/n2   900    0.00     False          5
 topstep   0.273           3.5           328.0    2491.0  2163.0 p0.525/R1.0/n4   900    0.05     False          5
 topstep   0.320           3.6           302.0    7479.0  7177.0 p0.550/R1.0/n4   900    0.10     False          5
   lucid   0.494           4.8           252.0    6486.0  6235.0 p0.400/R1.5/n2   900    0.00     False         10
   lucid   0.566           4.8           235.0   10035.0  9800.0 p0.420/R1.5/n2   900    0.05     False         10
   lucid   0.653           6.1           219.0   17807.0 17587.0 p0.550/R1.0/n2   900    0.10     False         10
    apex   0.223          14.0           502.0     848.0   346.0 p0.500/R1.0/n2   400    0.00     False         20
    apex   0.169          21.9           632.0    2673.0  2041.0 p0.525/R1.0/n4   150    0.05     False         20
    apex   0.360          19.9           349.0    5487.0  5137.0 p0.440/R1.5/n4   150    0.10     False         20
    mffu   0.451           6.6           348.0     965.0   617.0 p0.500/R1.0/n2   900    0.00     False          5
    mffu   0.430          36.2           365.0    2481.0  2116.0 p0.525/R1.0/n4   150    0.05     False          5
    mffu   0.699          32.9           224.0    7235.0  7010.0 p0.550/R1.0/n4   150    0.10     False          5
tradeify   0.318           3.0           349.0    3036.0  2687.0 p0.400/R1.5/n2   900    0.00     False          5
tradeify   0.383           4.9           298.0    6207.0  5909.0 p0.525/R1.0/n2   900    0.05     False          5
tradeify   0.464           4.8           255.0   10905.0 10651.0 p0.550/R1.0/n2   900    0.10     False          5
     tpt   0.270           6.4           760.0     970.0   210.0 p0.500/R1.0/n2   900    0.00      True          5
     tpt   0.413          34.8           953.0    2224.0  1270.0 p0.525/R1.0/n4   150    0.05      True          5
     tpt   0.689          33.0           623.0    6101.0  5478.0 p0.550/R1.0/n4   150    0.10      True          5

ev = expected $ per campaign (fees in; funded life capped 252d; trader split
applied). Conservative: losses-first intraday breaches, iid trades, fixed
risk, greedy payouts. Apex at street fee $90 (list $450: ev -$360).
TPT excluded from fleet (bots banned) — reference row only.