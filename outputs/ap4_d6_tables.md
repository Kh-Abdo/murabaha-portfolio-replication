# AP4 tables — `ap4_d6` (generated from `ap4_d6_results.json`; do not edit by hand)

Settings: `{"assets": ["Immobilière", "Automobile", "Equipement"], "rf_base": 0.045, "bounds_base": {"lower": [0.02, 0.02, 0.02], "upper": [0.7, 1.0, 1.0]}, "oos_start_months": 36, "rolling_window": 36, "n_boot": 1000, "block_length": 6, "seed": 42, "drop_first_row_zero": true}`


## Baseline

| Case | RE | Auto | Equip+Raw | E[R] % | Vol % | Growth SR | Binding |
|---|---|---|---|---|---|---|---|
| Baseline | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |

## Rf grid

| Rf | RE | Auto | Equip+Raw | E[R] % | Vol % | Growth SR | Rf % |
|---|---|---|---|---|---|---|---|
| 0% | 66.59 | 9.60 | 23.81 | 34.86 | 4.99 | 6.987 | 0.00 |
| 2% (v2 floor) | 64.88 | 9.78 | 25.34 | 35.47 | 5.08 | 6.590 | 2.00 |
| 3% | 63.92 | 9.88 | 26.20 | 35.81 | 5.13 | 6.394 | 3.00 |
| 4.5% (v2 ceiling, baseline) | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | 4.50 |
| PSIA 24m median, unclipped | 51.46 | 11.22 | 37.32 | 40.27 | 5.94 | 4.888 | 11.21 |
| PSIA 24m mean, unclipped | 2.00 | 13.81 | 84.19 | 59.09 | 10.68 | 3.555 | 21.13 |

## Cap / floor grid

| Case | RE | Auto | Equip+Raw | E[R] % | Vol % | Growth SR | Binding |
|---|---|---|---|---|---|---|---|
| cap 0.50, floor 0.00 | 50.00 | 17.83 | 32.17 | 38.08 | 5.54 | 6.059 | Immobilière@cap |
| cap 0.50, floor 0.01 | 50.00 | 17.83 | 32.17 | 38.08 | 5.54 | 6.059 | Immobilière@cap |
| cap 0.50, floor 0.02 | 50.00 | 17.83 | 32.17 | 38.08 | 5.54 | 6.059 | Immobilière@cap |
| cap 0.50, floor 0.05 | 50.00 | 17.83 | 32.17 | 38.08 | 5.54 | 6.059 | Immobilière@cap |
| cap 0.60, floor 0.00 | 60.00 | 11.57 | 28.43 | 36.68 | 5.27 | 6.102 | Immobilière@cap |
| cap 0.60, floor 0.01 | 60.00 | 11.57 | 28.43 | 36.68 | 5.27 | 6.102 | Immobilière@cap |
| cap 0.60, floor 0.02 | 60.00 | 11.57 | 28.43 | 36.68 | 5.27 | 6.102 | Immobilière@cap |
| cap 0.60, floor 0.05 | 60.00 | 11.57 | 28.43 | 36.68 | 5.27 | 6.102 | Immobilière@cap |
| cap 0.70, floor 0.00 | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |
| cap 0.70, floor 0.01 | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |
| cap 0.70, floor 0.02 | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |
| cap 0.70, floor 0.05 | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |
| cap 0.80, floor 0.00 | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |
| cap 0.80, floor 0.01 | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |
| cap 0.80, floor 0.02 | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |
| cap 0.80, floor 0.05 | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |
| cap 1.00, floor 0.00 | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |
| cap 1.00, floor 0.01 | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |
| cap 1.00, floor 0.02 | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |
| cap 1.00, floor 0.05 | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | none |

## Clip grid

| Clip | RE | Auto | Equip+Raw | E[R] % | Vol % | Growth SR | Equip clipped | μ Equip % | Binding |
|---|---|---|---|---|---|---|---|---|---|
| ±5% | 43.45 | 14.16 | 42.39 | 32.58 | 3.70 | 7.595 | 46 | 44.06 | none |
| ±10% | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 | 17 | 65.70 | none |
| ±15% | 70.00 | 9.50 | 20.50 | 35.05 | 5.41 | 5.645 | 4 | 73.03 | Immobilière@cap |
| ±20% | 70.00 | 11.65 | 18.35 | 34.39 | 5.51 | 5.423 | 2 | 75.19 | Immobilière@cap |
| none | 70.00 | 24.64 | 5.36 | 28.37 | 5.26 | 4.535 | 0 | 87.21 | Immobilière@cap |

## Gap-month variants

| Case | RE | Auto | Equip+Raw | E[R] % | Vol % | Growth SR |
|---|---|---|---|---|---|---|
| main | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 |
| low | 61.44 | 9.80 | 28.77 | 36.85 | 5.35 | 6.051 |
| high | 62.79 | 10.38 | 26.83 | 36.06 | 5.14 | 6.144 |
| log_linear_interpolation | 62.57 | 11.15 | 26.28 | 35.82 | 5.07 | 6.177 |

## Estimation variants

| Case | RE | Auto | Equip+Raw | E[R] % | Vol % | Growth SR |
|---|---|---|---|---|---|---|
| v2 first-row zero kept (78 rows) | 62.01 | 10.09 | 27.90 | 36.03 | 5.34 | 5.901 |
| simple instead of log returns | 60.26 | 10.88 | 28.86 | 37.49 | 5.39 | 6.115 |
| Ledoit-Wolf covariance | 48.39 | 17.14 | 34.47 | 39.02 | 5.66 | 6.098 |
| Bayes-Stein mean | 64.06 | 9.87 | 26.07 | 35.18 | 5.12 | 5.988 |
| Bayes-Stein mean + Ledoit-Wolf cov | 49.84 | 17.25 | 32.91 | 37.63 | 5.56 | 5.960 |

## In-sample benchmarks

| Portfolio | RE | Auto | Equip+Raw | E[R] % | Vol % | Growth SR |
|---|---|---|---|---|---|---|
| max-Sharpe (baseline) | 62.32 | 10.06 | 27.63 | 36.39 | 5.22 | 6.104 |
| minimum variance | 70.00 | 20.33 | 9.67 | 28.98 | 4.53 | 5.409 |
| equal weight | 33.33 | 33.33 | 33.33 | 38.28 | 5.79 | 5.840 |
| risk parity (ERC, bounded) | 48.01 | 30.74 | 21.25 | 33.46 | 5.04 | 5.745 |
| risk parity (ERC, unbounded) | 48.01 | 30.74 | 21.25 | 33.46 | 5.04 | 5.745 |
| actual book Dec 2025 | 78.59 | 6.15 | 15.26 | 31.47 | 4.60 | 5.866 |
| actual book average | 86.06 | 6.88 | 7.06 | 28.16 | 4.41 | 5.360 |

## Block bootstrap

| Percentile | Immobilière | Automobile | Equipement |
|---|---|---|---|
| p5 | 38.40 | 2.00 | 18.18 |
| p25 | 52.40 | 5.71 | 23.14 |
| p50 | 61.42 | 11.61 | 26.66 |
| p75 | 68.73 | 18.76 | 30.90 |
| p95 | 70.00 | 32.45 | 40.25 |

Resampled mean weights: {'Immobilière': 0.5896, 'Automobile': 0.1347, 'Equipement': 0.2757}; RE largest in 94.0%; RE at 70% cap in 20.4%; at 2% floor: {'Immobilière': 0.0, 'Automobile': 0.102, 'Equipement': 0.0}; growth SR percentiles {'p5': 5.565, 'p25': 6.008, 'p50': 6.388, 'p75': 6.813, 'p95': 7.716}

## QP frontier vs MC cloud

{
 "n_points": 40,
 "max_sharpe_on_frontier_grid": 6.103777922030056,
 "tangency_from_optimiser": 6.104108673070354,
 "mc_cloud_best_sharpe": 6.1039426457521655,
 "mc_points_above_minvar_return": 6711,
 "mc_excess_vol_vs_frontier_pct_points": {
  "median": 0.09934925901610991,
  "p95": 1.5423639272433989,
  "min": -0.001989300694874019
 },
 "mc_share_within_10bp_of_frontier": 0.5012665772612129
}

## Out of sample, 2022-08 to 2025-12 (41 months)

### expanding window

| Strategy | Avg RE / Auto / Eq | Return % | Vol % | Growth SR | Unclipped SR | Turnover/yr | SR @50bp |
|---|---|---|---|---|---|---|---|
| max-Sharpe | 64.6 / 3.1 / 32.2 | 26.77 | 3.07 | 7.244 | 6.677 | 0.163 | 7.222 |
| max-Sharpe LW+BS | 43.7 / 13.2 / 43.1 | 30.16 | 3.94 | 6.515 | 6.044 | 0.264 | 6.488 |
| minimum variance | 70.0 / 15.6 / 14.4 | 22.04 | 1.72 | 10.203 | 9.748 | 0.139 | 10.155 |
| risk parity (bounded) | 48.3 / 28.3 / 23.4 | 24.41 | 2.39 | 8.316 | 7.615 | 0.131 | 8.284 |
| equal weight | 33.3 / 33.3 / 33.3 | 27.10 | 3.14 | 7.192 | 6.452 | 0.161 | 7.167 |
| actual book | 83.3 / 5.8 / 10.9 | 20.00 | 1.62 | 9.594 | 9.008 | 0.003 | 9.593 |

### rolling window

| Strategy | Avg RE / Auto / Eq | Return % | Vol % | Growth SR | Unclipped SR | Turnover/yr | SR @50bp |
|---|---|---|---|---|---|---|---|
| max-Sharpe | 60.8 / 13.0 / 26.2 | 26.22 | 2.84 | 7.638 | 7.383 | 0.797 | 7.412 |
| max-Sharpe LW+BS | 44.5 / 19.9 / 35.6 | 29.03 | 3.62 | 6.771 | 6.402 | 0.829 | 6.609 |
| minimum variance | 66.8 / 23.3 / 9.9 | 20.37 | 2.02 | 7.865 | 7.536 | 0.523 | 7.670 |
| risk parity (bounded) | 52.2 / 29.9 / 17.8 | 22.50 | 2.16 | 8.324 | 7.838 | 0.477 | 8.138 |
| equal weight | 33.3 / 33.3 / 33.3 | 27.10 | 3.14 | 7.192 | 6.452 | 0.161 | 7.167 |
| actual book | 83.3 / 5.8 / 10.9 | 20.00 | 1.62 | 9.594 | 9.008 | 0.003 | 9.593 |

## Time variation

| Pair | Min | Median | Max | Last | Full sample |
|---|---|---|---|---|---|
| Immobilière-Automobile | -0.14 | 0.19 | 0.58 | 0.58 | 0.47 |
| Immobilière-Equipement | -0.32 | -0.03 | 0.50 | 0.15 | 0.25 |
| Automobile-Equipement | -0.69 | -0.19 | 0.32 | 0.28 | -0.02 |

## Split sample

| Period | RE | Auto | Equip+Raw | E[R] % | Vol % | Growth SR |
|---|---|---|---|---|---|---|
| 2019-08..2022-09 | 68.86 | 2.00 | 29.14 | 49.21 | 5.24 | 8.530 |
| 2022-10..2025-12 | 70.00 | 14.98 | 15.02 | 21.41 | 1.64 | 10.328 |
