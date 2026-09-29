# CHANGELOG
Purpose: human-readable, reverse-chronological record of every meaningful change (Keep a Changelog style).
Last updated: 2026-09-28

## [Unreleased]
### Added
- County-year panel 2020-2025 rebuilt from AFDC open dates; spatial join to 2023 Census counties (ADR-0004, 0005).
- Models A and B (logistic, Lasso, random forest) with temporal test, state-held-out CV, 2026 partial-year check.
- R cross-check (`R/cross_check.R`, `reports/r_cross_check.md`): PASS for both targets.
- Cost scenarios (Low/Base/High) from NREL and NEVI award data; indicative site economics.
- Scoring (Net Opportunity, Future Deployment), budget optimizer (top-N exact with equal costs, greedy, MILP).
- Streamlit app with map, ranked list, CSV download, economics, model performance, county explorer, method tab.
- Tests (19) for scoring, optimizer, cost, loaders, spatial join, and pipeline outputs.
### Changed
- Traffic: freeway vehicle-miles with structural zeros, replacing summed AADT and neighbor imputation (ADR-0006).
- Station-to-county assignment by coordinates instead of AI address matching.
- Governance layer in `/docs` (GOVERNANCE, PREFLIGHT, POSTFLIGHT, ARCHITECTURE, CONVENTIONS, DECISIONS, TESTING, LESSONS, CHANGELOG, DATA_SOURCES, METHODOLOGY).
- Raw inputs copied into `data/raw/`; 2023 Census county boundaries (us-atlas 2023 redistribution) in `data/external/`.
