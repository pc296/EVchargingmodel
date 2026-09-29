# ARCHITECTURE
Purpose: living map of components, responsibilities, data flow and boundaries.
Last updated: 2026-09-28

## Overview
Offline pipeline (Python, with an R cross-check) turns raw public data into a county-year panel, trains two classifiers, and writes compact scored tables. A Streamlit app reads only those processed tables, lets users set weights, cost scenario and budget, and returns a map plus a ranked, budget-constrained list.

```
data/raw/*  ─┐
data/external/counties (2023 Census via us-atlas) ─┤
             ▼
src/evcharge/io.py        load + clean each source (one function per source)
src/evcharge/geo.py       station -> county spatial join, centroids, distances
src/evcharge/panel.py     county x year panel 2020-2025, labels A and B
src/evcharge/model.py     logistic (baseline), L1-logistic, random forest; temporal split
src/evcharge/cost.py      site build-cost scenarios (low/base/high) from cited sources
src/evcharge/scoring.py   normalized features -> Net Opportunity + Future Deployment scores
src/evcharge/optimize.py  budget-constrained selection (MILP, greedy check)
             ▼
scripts/run_pipeline.py   orchestrates all of the above, writes data/processed/*
R/cross_check.R           refits models in R, compares with Python (reports/r_cross_check.md)
tests/                    pytest: unit (scoring, optimizer, cost, io, geo) + pipeline output checks
             ▼
streamlit_app.py          UI: sliders, budget, map (plotly), ranked table, downloads
```

## Boundaries
- The app never reads `data/raw/`; it reads `data/processed/app_counties.parquet`, `data/processed/model_metrics.json`, and the county GeoJSON.
- All modeling happens offline; the app only re-weights precomputed, normalized features and runs the optimizer (fast, under 1 second for ~3,100 counties).
- R is not a runtime dependency of the app.
- Pipeline-only packages (statsmodels, geopandas, numbers-parser) are in requirements-dev.txt; `model.py` imports statsmodels lazily so the app can import feature labels without it.

## External dependencies
pandas, numpy, scikit-learn, statsmodels, scipy (MILP), geopandas/shapely (pipeline only), plotly, streamlit, pyarrow, numbers-parser (pipeline only). R: glmnet, pROC.
