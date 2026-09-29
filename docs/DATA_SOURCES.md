# DATA SOURCES
Purpose: every input file, where it came from, its vintage, and known issues.
Last updated: 2026-09-28

| File (data/raw or data/external) | Source | Vintage | Geography | Used for | Known issues |
|---|---|---|---|---|---|
| afdc_stations_2026-09-22.csv | U.S. DOE AFDC station locator download | Snapshot 2026-09-22 | Station (lat/lon) | Supply by county and year, IONNA sites, posted prices | Only stations that exist today; closed stations missing (past supply undercounted). 86 DC stations lack open dates (treated as pre-2020). Pricing is free text; 642 DC stations have a parseable $/kWh. |
| census_pop_2020_2025.xlsx | U.S. Census Bureau, Vintage 2025 county estimates (CO-EST2025-POP) | 2020-2025 | County | Population, growth, density | None material. |
| hpms_2024_road_utilization.csv | FHWA HPMS 2024 (data.transportation.gov), aggregated by team | 2024 | County | Freeway vehicle-miles, interstate miles | Covers F_SYSTEM 1-2 only. 1,377 counties have no such roads (set to 0, not imputed). CT uses legacy counties in HPMS. |
| hpms_2024_road_utilization_imputed.csv | Team file derived from above | 2024 | County | CT planning-region traffic only (statewide total allocated by population share) | Neighbor imputation of zero counties in this file is not used (see ADR-0006). |
| afdc_registrations_by_state.csv | AFDC Vehicle Registration Counts by State | Latest AFDC release in folder (labelled 2025 in team log; confirm year) | State | BEV per 1,000 residents | Rounded to nearest 100. Single year only; no county detail. |
| eia_state_profile_2024.csv | EIA State Electricity Profiles 2024 | 2024 | State | Electricity price | All-sector average, not commercial rate. |
| afdc_laws_incentives.numbers | AFDC Laws and Incentives download | Snapshot 2026-09-22 | State | Count of EV incentives in force by year | Current records only; repealed incentives mostly absent. 30% lack an enacted date (treated as in force for all years). |
| afdc_ionna_dcfc_by_county_prior.csv | Team file (Deliverable 2) | 2026-09 | County | County name/FIPS crosswalk; reconciliation check | Uses 4 legacy FIPS (crosswalked in io.py). Port totals differ slightly from the spatial join (75,594 vs 77,189 DC ports) because the join also counts temporarily unavailable stations. |
| us_atlas_2023_counties-10m.json | npm `@severo_bo/us-atlas-2023` (Census GENZ2023 cartographic boundaries as TopoJSON) | 2023 | County polygons | Spatial join, centroids, areas, maps | Simplified; Falls Church city, VA has no polygon (centroid set manually; its stations fall into neighbors). 16 coastal stations snapped to nearest county within 5 km. |

## Literature and cost sources
- Borlaug, B., Caristo, V., Ouren, F., Yang, F., Wood, E., Roberson, L. (2026). Economics of electric vehicle corridor fast charging in the United States. *Advances in Applied Energy*, 21. https://www.sciencedirect.com/science/article/pii/S2666792425000514 (NREL; peer reviewed).
- Paren (2024-10-31). NEVI DC fast charging station average project cost: $915,000. Analysis of 330 NEVI awards. https://www.paren.app/blog/nevi-dc-fast-charging-station-total-project-cost-averages-915-000 (industry data vendor; not peer reviewed).
- Schey, S., Chu, K., Smart, J. (2022). Breakdown of Electric Vehicle Supply Equipment Installation Costs. INL/RPT-22-68598. https://inldigitallibrary.inl.gov/sites/sti/sti/Sort_63124.pdf (cross-check on hardware and installation ranges).

## Planned additions (not yet obtained; build environment cannot reach these hosts)
- Atlas EV Hub county/ZIP registrations for reporting states.
- Census ACS 5-year county tables (income, education, homeownership, housing type).
- AFDC state registration counts for earlier years (for time-varying EV features).
- EIA commercial electricity price by state (EIA-861 or Electric Power Monthly Table 5.6.A).
- BEA Regional Price Parities by state (regional cost multiplier).
