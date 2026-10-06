# CHANGELOG
Purpose: human-readable, reverse-chronological record of every meaningful change (Keep a Changelog style).
Last updated: 2026-09-28

## [Unreleased]
### Changed
- Walkthrough notebook text edited by Pat (shorter explanations, table of contents). Duplicate cost-scenario cell removed; dollar signs escaped so Colab no longer renders text between them as math; corrected the note on the integer program (not used by the app). Code unchanged; results identical.
### Fixed
- App data cache now keyed on a content hash of the data files, so redeployed data replaces cached data (the corrected map file was not reaching the live app).
### Fixed
- Both app maps drew no counties: county GeoJSON feature ids were row numbers instead of FIPS codes; regenerated with FIPS ids and without the empty Falls Church shape (which crashed Plotly). Verified by offline render.
### Fixed
- County-types map rendered blank: each trace had a constant value, so Plotly's color range collapsed; set zmin/zmax explicitly.
### Fixed
- Baseline rankings now give tied values their average rank (was row order); Target B freeway baseline AUC 0.753 -> 0.746, Target A 0.841 -> 0.843. Model metrics unchanged.
- Removed the app's "Exact optimizer" checkbox, which had no effect because every site has the same cost; per-port cost input no longer rounded.
### Added
- Test that every label equals the next year's outcome; traceability report (reports/Traceability_Report.docx) with its facts generator and build script.
### Fixed
- Corrected three figures in docs (open-date gaps, incentive-date gaps, IONNA mean ports) found while building the traceability report.
### Fixed
- Walkthrough runs on Google Colab: new chunk 0 installs numbers-parser and clones the public repo for data; tested from an empty folder.
### Added
- Submission walkthrough: `analysis/ev_charging_model_walkthrough.py` (12 annotated chunks) and executed notebook; figures in `reports/figures/`; full run output in `reports/walkthrough_output.txt`; reproduction test (ADR-0012).

## [0.1.0] - 2026-09-28
Save point: first deployed version.
### Added
- Deployed to Streamlit Community Cloud: https://evchargingmodel-ui5fwbrdxjotcghzbovdvf.streamlit.app/ (map verified: 3,144 counties, IONNA and recommended markers render).
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
