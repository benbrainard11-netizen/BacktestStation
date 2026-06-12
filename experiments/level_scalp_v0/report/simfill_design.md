# Sim-venue design study — SELECTION (2025) only; holdout untouched

Loss model: stop fills at stop + 1 tick (sim slippage); entry/TP at level/target on quote-cross (conservative for sim). Net of commission.

## P3 (pdc ES.c.0)

P3: n=565, days=119, selection-aware p5 of BEST grid cell = +0.93 (any single-cell p5 must beat this hurdle to be believed)

Top 5 by day-block p5:
|   k |   j |   rr |   net |   p5 |   win% |
|----:|----:|-----:|------:|-----:|-------:|
|   2 |   6 | 0.33 |  1.06 | 0.89 |   0.93 |
|   2 |   4 | 0.5  |  1    | 0.85 |   0.9  |
|   2 |   2 | 1    |  0.95 | 0.83 |   0.85 |
|   2 |   8 | 0.25 |  1.01 | 0.83 |   0.94 |
|   2 |  12 | 0.17 |  0.95 | 0.73 |   0.95 |

Top 5 high-RR (k >= 1.5j):
|   k |   j |   rr |   net |    p5 |   win% |
|----:|----:|-----:|------:|------:|-------:|
|  12 |   8 | 1.5  |  0.77 |  0.04 |   0.42 |
|  12 |   6 | 2    |  0.69 | -0.01 |   0.38 |
|   4 |   2 | 2    |  0.15 | -0.1  |   0.49 |
|   6 |   4 | 1.5  |  0.32 | -0.11 |   0.51 |
|  16 |   6 | 2.67 |  0.6  | -0.25 |   0.27 |

- (8,8) first touch (n=1): net +0.69 ticks (n=119)
- (8,8) retest (n>=2): net +0.69 ticks (n=446)
- overshoot through level before 8t rejection: med/p75/p90 = [1.5, 5.5, 10.5] (a stop tighter than ~p75 gets swept on ~25%+ of good rejections)

## P6 (round ES.c.0)

P6: n=686, days=135, selection-aware p5 of BEST grid cell = +1.37 (any single-cell p5 must beat this hurdle to be believed)

Top 5 by day-block p5:
|   k |   j |   rr |   net |   p5 |   win% |
|----:|----:|-----:|------:|-----:|-------:|
|   2 |  16 | 0.12 |  1.45 | 1.33 |   0.99 |
|   2 |   8 | 0.25 |  1.42 | 1.32 |   0.97 |
|   2 |   6 | 0.33 |  1.42 | 1.32 |   0.97 |
|   2 |   4 | 0.5  |  1.38 | 1.28 |   0.95 |
|   2 |  12 | 0.17 |  1.39 | 1.26 |   0.98 |

Top 5 high-RR (k >= 1.5j):
|   k |   j |   rr |   net |    p5 |   win% |
|----:|----:|-----:|------:|------:|-------:|
|   4 |   2 |  2   |  0.41 |  0.18 |   0.53 |
|   6 |   4 |  1.5 |  0.35 |  0.04 |   0.51 |
|   8 |   4 |  2   |  0.31 | -0.05 |   0.43 |
|  12 |   4 |  3   |  0.37 | -0.1  |   0.33 |
|   8 |   2 |  4   |  0.12 | -0.18 |   0.31 |

- (8,8) first touch (n=1): net +0.19 ticks (n=120)
- (8,8) retest (n>=2): net +0.57 ticks (n=566)
- overshoot through level before 8t rejection: med/p75/p90 = [2.5, 10.5, 23.1] (a stop tighter than ~p75 gets swept on ~25%+ of good rejections)

## P7 (pdh+pdl+onh+onl ES.c.0)

P7: n=530, days=137, selection-aware p5 of BEST grid cell = +1.41 (any single-cell p5 must beat this hurdle to be believed)

Top 5 by day-block p5:
|   k |   j |   rr |   net |   p5 |   win% |
|----:|----:|-----:|------:|-----:|-------:|
|   2 |  16 | 0.12 |  1.48 | 1.33 |   0.99 |
|   2 |   4 | 0.5  |  1.41 | 1.31 |   0.96 |
|   2 |  12 | 0.17 |  1.44 | 1.31 |   0.98 |
|   2 |   6 | 0.33 |  1.39 | 1.28 |   0.97 |
|   2 |   8 | 0.25 |  1.41 | 1.28 |   0.97 |

Top 5 high-RR (k >= 1.5j):
|   k |   j |   rr |   net |   p5 |   win% |
|----:|----:|-----:|------:|-----:|-------:|
|  12 |   8 |  1.5 |  0.95 | 0.24 |   0.48 |
|   6 |   4 |  1.5 |  0.61 | 0.19 |   0.54 |
|  16 |   8 |  2   |  0.9  | 0.09 |   0.39 |
|  12 |   6 |  2   |  0.66 | 0.08 |   0.41 |
|   4 |   2 |  2   |  0.28 | 0.03 |   0.51 |

- (8,8) first touch (n=1): net +0.03 ticks (n=142)
- (8,8) retest (n>=2): net +1.54 ticks (n=388)
- overshoot through level before 8t rejection: med/p75/p90 = [2.5, 8.5, 19.5] (a stop tighter than ~p75 gets swept on ~25%+ of good rejections)

## P8 (round RTY.c.0)

P8: n=952, days=138, selection-aware p5 of BEST grid cell = +0.86 (any single-cell p5 must beat this hurdle to be believed)

Top 5 by day-block p5:
|   k |   j |   rr |   net |   p5 |   win% |
|----:|----:|-----:|------:|-----:|-------:|
|   4 |  16 | 0.25 |  1.17 | 0.85 |   0.9  |
|   4 |   6 | 0.67 |  0.83 | 0.59 |   0.78 |
|   4 |  12 | 0.33 |  0.85 | 0.56 |   0.86 |
|   4 |   8 | 0.5  |  0.66 | 0.4  |   0.8  |
|   4 |   2 | 2    |  0.53 | 0.34 |   0.61 |

Top 5 high-RR (k >= 1.5j):
|   k |   j |   rr |   net |    p5 |   win% |
|----:|----:|-----:|------:|------:|-------:|
|   4 |   2 |    2 |  0.53 |  0.34 |   0.61 |
|   8 |   2 |    4 |  0.2  | -0.07 |   0.36 |
|   6 |   2 |    3 | -0.08 | -0.31 |   0.41 |
|  12 |   2 |    6 | -0.2  | -0.51 |   0.23 |
|  16 |   2 |    8 | -0.25 | -0.6  |   0.18 |

- (8,8) first touch (n=1): net +0.23 ticks (n=177)
- (8,8) retest (n>=2): net +0.22 ticks (n=775)
- overshoot through level before 8t rejection: med/p75/p90 = [3.5, 10.5, 25.5] (a stop tighter than ~p75 gets swept on ~25%+ of good rejections)
