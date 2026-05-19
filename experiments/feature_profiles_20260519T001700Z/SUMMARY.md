# Feature Profiles — per asset + per asset class

_Generated 2026-05-19T00:17:47.430129Z_

Coverage: 4 features × 23 symbols = 92 profile rows.

Total events analyzed: 2,025,097

## Top-3 features by fwd10 MFE/MAE ratio, per asset class

### bond

| Rank | Feature | n_symbols | fwd10 ratio (mean) | fwd10 hit (mean) | fwd50 ratio (mean) |
|---|---|---:|---:|---:|---:|
| 1 | `swing_pivot` | 4 | 3.6772 | 0.6518 | 1.6585 |
| 2 | `liquidity_sweep` | 4 | 0.999 | 0.4898 | 0.984 |
| 3 | `fvg_formation` | 4 | 0.97 | 0.4632 | 1.0095 |

### energy

| Rank | Feature | n_symbols | fwd10 ratio (mean) | fwd10 hit (mean) | fwd50 ratio (mean) |
|---|---|---:|---:|---:|---:|
| 1 | `swing_pivot` | 5 | 3.6714 | 0.6526 | 1.6144 |
| 2 | `fvg_formation` | 5 | 1.0172 | 0.489 | 1.0172 |
| 3 | `order_block` | 5 | 0.9938 | 0.499 | 0.9874 |

### fx

| Rank | Feature | n_symbols | fwd10 ratio (mean) | fwd10 hit (mean) | fwd50 ratio (mean) |
|---|---|---:|---:|---:|---:|
| 1 | `swing_pivot` | 7 | 4.6853 | 0.6679 | 1.8091 |
| 2 | `liquidity_sweep` | 7 | 1.0237 | 0.4969 | 1.0161 |
| 3 | `order_block` | 7 | 0.9936 | 0.4991 | 1.0089 |

### grain

| Rank | Feature | n_symbols | fwd10 ratio (mean) | fwd10 hit (mean) | fwd50 ratio (mean) |
|---|---|---:|---:|---:|---:|
| 1 | `swing_pivot` | 3 | 4.294 | 0.663 | 1.814 |
| 2 | `liquidity_sweep` | 3 | 1.0087 | 0.4943 | 1.0027 |
| 3 | `fvg_formation` | 3 | 0.994 | 0.476 | 1.004 |

### index

| Rank | Feature | n_symbols | fwd10 ratio (mean) | fwd10 hit (mean) | fwd50 ratio (mean) |
|---|---|---:|---:|---:|---:|
| 1 | `swing_pivot` | 4 | 3.334 | 0.6492 | 1.5962 |
| 2 | `liquidity_sweep` | 4 | 1.0215 | 0.4998 | 1.019 |
| 3 | `order_block` | 4 | 1.0212 | 0.496 | 1.0315 |

## Top-5 symbols per feature (by fwd10 MFE/MAE ratio)

### fvg_formation

| # | Symbol | Class | Events | per_yr | fwd10 ratio | fwd10 hit | fwd50 ratio |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | CL.c.0 | energy | 52,763 | 5862.6 | 1.041 | 0.489 | 1.047 |
| 2 | HO.c.0 | energy | 79,115 | 8790.6 | 1.017 | 0.494 | 1.025 |
| 3 | NG.c.0 | energy | 51,035 | 5670.6 | 1.016 | 0.484 | 1.002 |
| 4 | RB.c.0 | energy | 81,878 | 9097.6 | 1.007 | 0.493 | 1.005 |
| 5 | 6N.c.0 | fx | 57,740 | 6415.6 | 1.007 | 0.485 | 1.006 |

### liquidity_sweep

| # | Symbol | Class | Events | per_yr | fwd10 ratio | fwd10 hit | fwd50 ratio |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | 6A.c.0 | fx | 10,336 | 1148.4 | 1.08 | 0.508 | 1.04 |
| 2 | 6C.c.0 | fx | 9,177 | 1019.7 | 1.055 | 0.499 | 1.037 |
| 3 | ZW.c.0 | grain | 9,138 | 1015.3 | 1.039 | 0.504 | 1.015 |
| 4 | ES.c.0 | index | 10,965 | 1218.3 | 1.032 | 0.493 | 1.025 |
| 5 | NQ.c.0 | index | 10,980 | 1220.0 | 1.03 | 0.494 | 1.023 |

### order_block

| # | Symbol | Class | Events | per_yr | fwd10 ratio | fwd10 hit | fwd50 ratio |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | 6N.c.0 | fx | 9,460 | 1051.1 | 1.042 | 0.509 | 1.035 |
| 2 | NQ.c.0 | index | 9,625 | 1069.4 | 1.041 | 0.496 | 1.049 |
| 3 | 6A.c.0 | fx | 7,693 | 854.8 | 1.035 | 0.513 | 1.036 |
| 4 | BZ.c.0 | energy | 9,333 | 1037.0 | 1.024 | 0.498 | 1.018 |
| 5 | YM.c.0 | index | 9,627 | 1069.7 | 1.022 | 0.503 | 1.016 |

### swing_pivot

| # | Symbol | Class | Events | per_yr | fwd10 ratio | fwd10 hit | fwd50 ratio |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | 6C.c.0 | fx | 9,777 | 1086.3 | 5.724 | 0.675 | 2.038 |
| 2 | 6B.c.0 | fx | 12,595 | 1399.4 | 5.554 | 0.68 | 1.902 |
| 3 | 6A.c.0 | fx | 12,499 | 1388.8 | 5.505 | 0.674 | 1.932 |
| 4 | 6J.c.0 | fx | 13,580 | 1508.9 | 4.865 | 0.675 | 1.827 |
| 5 | ZS.c.0 | grain | 11,193 | 1243.7 | 4.395 | 0.669 | 1.817 |

## How to read this

- `fwd10_ratio_mfe_mae`: mean of (forward-10-candle MFE in thesis direction) / (forward-10-candle MAE against thesis). Higher = the detector's directional thesis tends to play out more than it gets stopped out. 1.0 is symmetric; >1.5 is interesting.
- `fwd10_last_close_thesis_hitrate`: % of events where forward-10-bars later the price moved IN the thesis direction. 0.50 = coin flip; >0.55 is decent.
- These are RAW outcome stats, NOT a backtest. A high-ratio detector still needs a proper trade rule (entry, stop, target) to make money. This profile is the first filter for 'which features are worth simulating on which assets.'
