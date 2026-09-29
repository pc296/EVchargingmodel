# TESTING
Purpose: test strategy and the definition of "verified".
Last updated: 2026-09-28

- Framework: `pytest`. Run `pytest -q` from repo root.
- New logic ships with tests. No exceptions for scoring, cost, or optimizer code, since those drive recommendations.
- Unit tests (`tests/test_*.py`): pure functions on small synthetic frames (scoring math, knapsack optimizer, cost scaling, panel label logic, spatial join on known points).
- Integration tests (`tests/test_pipeline_outputs.py`): run against `data/processed/` outputs; check row counts (one row per county per year), key uniqueness, no NaN in model features, value ranges, and reconciliation totals (e.g., station counts by state match the raw file).
- Model verification: metrics are computed on a held-out later year only; R cross-check (`R/cross_check.R`) must reproduce Python logistic coefficients and AUC within tolerance (coef abs diff < 0.01 on standardized features, AUC diff < 0.005).
- Coverage expectation: every module in `src/evcharge/` has at least one test; decision-driving functions are covered on edge cases (zero budget, budget below cheapest site, ties).
- "Verified" means: tests pass, pipeline runs end to end from raw files, and any number quoted in docs matches the current processed output.
