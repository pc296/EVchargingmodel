# Method
Purpose: plain-language description of the model, scores, cost and optimizer (also shown in the app).
Last updated: 2026-09-28

## Business question
Where should an IONNA-style fast-charging network build its next sites, given a capital budget? The unit of analysis is the U.S. county (3,144 counties, 2025 Census geography).

## 1. County-year panel (2020-2025)
Each row is a county at the end of year *t*. Charging supply is rebuilt from the AFDC station file using each station's open date (15,939 public DC fast stations, assigned to counties by their coordinates). Stations that have since closed are not in today's file, so past supply is slightly undercounted.

Features at year *t*: population (log), 1-year population growth, population density, state battery-EV registrations per 1,000 residents, state electricity price, count of state EV incentives in force, freeway vehicle-miles (log) and interstate miles, existing DC ports and large (4+ port) sites, DC ports per 1,000 estimated EVs, Tesla share of ports, miles from the county centroid to the nearest large site, DC ports within 50 miles, large sites opened in the county during *t*, and large sites opened per million people in the state during *t*.

## 2. Predictive models
- **Model A:** does the county gain at least one new DC site with 4+ ports in year *t+1*? Base rate rose from 10% (2021) to 23% (2025).
- **Model B:** among counties with no 4+ port site, does the first one open in *t+1*? Base rate 4.5% to 8.5% of eligible counties.
- Methods: logistic regression (main, interpretable), Lasso logistic regression, random forest.
- Validation: train on 2021-2023 features (2022-2024 outcomes), test on 2024 features (2025 outcomes). Robustness: 5-fold cross-validation with whole states held out. Out-of-time check: models refit through 2025 outcomes, scored on end-2025 features, compared with openings from January 1 to September 22, 2026.

| Test (2025 outcomes) | ROC AUC | PR AUC | Precision in top N* |
|---|---|---|---|
| A: logistic | 0.884 | 0.738 | 0.642 |
| A: population rank only | 0.852 | 0.712 | 0.624 |
| B: logistic | 0.817 | 0.315 | 0.357 |
| B: population rank only | 0.772 | 0.278 | 0.294 |

*N equals the number of counties that actually got a site (732 for A, 143 for B). States-held-out AUC: 0.878 (A), 0.822 (B). 2026 partial-year check: 0.883 (A), 0.764 (B).

**Interpretation.** Chargers follow people, so population alone ranks counties well. The models add a moderate, consistent lift, larger for first entry. Lasso and random forest do not beat the logistic regression, which suggests the signal is mostly captured by a few smooth relationships (population, traffic, state momentum). Both targets describe where the market has built, not where sites earn a return; the scoring layer below adds supply and cost.

## 3. Scores
Each input is converted to a percentile rank across counties (0 to 1), so weights are comparable.
- **Net Opportunity (0-100)** = weighted mean of: estimated EVs, freeway traffic, population growth, Model A probability, Model B probability, state EV incentives, and electricity price (lower is better). Default weights: 0.25, 0.25, 0.05, 0.20, 0.10, 0.05, 0.10.
- **Future Deployment** = Net Opportunity x (1 - penalty x saturation), where saturation is the average percentile of DC ports per 1,000 EVs and DC ports within 50 miles. Default penalty 0.5.

## 4. Build cost
Default site: 8 DC ports (IONNA's current sites average 8.4).
| Scenario | Per port | Per site fixed | 8-port site | Basis |
|---|---|---|---|---|
| Low | $183,116 | $0 | $1.46M | Median per-port cost across 330 NEVI awards (Paren, 2024), all-in |
| Base | $232,700 | $100,000 | $1.96M | NREL 350 kW equipment + installation, plus a distribution transformer (Borlaug et al., 2026) |
| High | $305,600 | $131,300 | $2.58M | Base x NEVI top-quartile / median ratio (1.31) |

Not included: land, feeder or substation upgrades (NREL: $3M and $5M above 3 MW and 7 MW peak), regional construction cost differences. An optional grant share reduces net capex.

## 5. Budget-constrained selection
Each county can receive up to *M* new sites. The *k*-th site in a county is worth score x decay^(existing IONNA sites + k - 1), so a second site is worth less than the first. The tool maximizes total value subject to total net capex within budget. With one cost per site, picking the highest values is exactly optimal; an integer program (SciPy MILP) is available when costs differ.

## 6. Site economics (indicative)
Annual energy revenue = ports x kWh per port per day x 365 x price. Energy cost = kWh x (state retail price + demand-charge adder). Defaults: 176 kWh/port/day (NREL 2025, 4% capacity factor), state median posted DCFC price from AFDC (national median $0.48/kWh where a state has fewer than 10 priced stations), $0.12/kWh demand-charge adder (NREL). Excludes O&M, lease, fees and taxes.

## 7. Known limitations
- EV registrations are state totals spread by population, so EV adoption does not vary within a state. County-level registration data (Atlas EV Hub) and Census demographics are the planned fix.
- Electricity price is the all-sector state average; the commercial rate and demand charges matter more.
- Traffic covers interstates and other freeways only; 1,377 counties have none (true zeros). Connecticut's 9 planning regions use an allocated statewide total (flagged).
- Utilization is assumed equal across counties; no public county-level usage data exists.
- Recommendations are at county level; marker positions are county centroids.
