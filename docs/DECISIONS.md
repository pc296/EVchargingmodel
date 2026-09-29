# DECISIONS
Purpose: append-only Architecture Decision Record log. Never edit past entries; supersede them.
Last updated: 2026-09-28

## ADR-0001: Governance files live in /docs
- Date: 2026-09-28. Status: accepted.
- Context: Streamlit Cloud expects the app entry point and requirements at repo root.
- Decision: governance and method docs go in `/docs`; root holds README, app, requirements.
- Alternatives: all at root (cluttered).
- Consequences: GOVERNANCE.md notes the location.

## ADR-0002: Two supervised targets on a county-year panel
- Date: 2026-09-28. Status: accepted (owner approved options A and B).
- Context: Deliverable 1 target ("county has a station") is 1 for about 60% of counties and mostly encodes current state. Deliverable 2 conflated score and label.
- Decision: Target A = county gains at least one new DC fast-charging site with 4+ DC ports in year t+1. Target B = same event, restricted to counties with no 4+ port site at end of year t (first entry). Features observed at end of year t.
- Alternatives: count of new ports (Poisson/NB), hurdle model, IONNA-only target, D1 target. See chat record 2026-09-28.
- Consequences: both targets learn where the market has built, not profitability; scoring layer handles supply and cost.

## ADR-0003: Temporal validation
- Date: 2026-09-28. Status: accepted.
- Decision: train on label years 2022-2024 (features 2021-2023), test on label year 2025 (features 2024). Leave-states-out CV as robustness.
- Alternatives: random 70/30 split (leaks time and geography).

## ADR-0004: County geography from 2023 Census cartographic boundaries
- Date: 2026-09-28. Status: accepted.
- Context: Census servers are unreachable from the build environment; Connecticut now uses 9 planning regions.
- Decision: use the npm package `@severo_bo/us-atlas-2023` (redistribution of Census GENZ2023 county boundaries), which has CT planning regions and matches the Vintage 2025 population file.
- Consequences: boundaries are simplified (10m); a few stations on borders may fall in a neighboring county. Tested via reconciliation against the prior county file.

## ADR-0005: Station-to-county assignment by spatial join
- Date: 2026-09-28. Status: accepted.
- Decision: point-in-polygon join on AFDC latitude/longitude, replacing the AI address categorization used in Deliverable 2. Points outside all polygons go to the nearest county within 5 km, else are dropped and logged.

## ADR-0006: Traffic measure
- Date: 2026-09-28. Status: accepted.
- Decision: use HPMS 2024 daily vehicle-miles on Interstates and other freeways/expressways (F_SYSTEM 1-2), with counties lacking such roads set to 0 (structural zero), not imputed. Drop "Future AADT". Log-transform VMT. Distance from county centroid to nearest freeway-bearing county is added as a corridor-access proxy.
- Alternatives: summed AADT (invalid), neighbor imputation of zeros (inflates rural traffic).

## ADR-0007: R is a cross-check, not a runtime dependency
- Date: 2026-09-28. Status: accepted (owner approved).
- Decision: `R/cross_check.R` refits the logistic and L1 models with glmnet and pROC on the exported panel and writes a comparison report.

## ADR-0008: Tesla Superchargers count as full competitors
- Date: 2026-09-28. Status: accepted (owner approved).

## ADR-0009: Build cost scenarios from published sources
- Date: 2026-09-28. Status: accepted.
- Decision: default site = 8 DC ports (IONNA's current mean is 8.4 ports/site). Per-port costs from NREL (Borlaug et al., 2026) and Paren's analysis of 330 NEVI awards; low/base/high scenarios defined in METHODOLOGY.md. Users can edit ports per site and per-port cost in the app.
- Alternatives: single point estimate (hides uncertainty).
- Consequences: no regional cost adjustment until a regional index (BEA RPP) is added; flagged as a known gap.

## ADR-0010: Hosting on Streamlit Community Cloud
- Date: 2026-09-28. Status: accepted (owner approved).

## ADR-0011: Unattended build scope
- Date: 2026-09-28. Status: accepted.
- Context: owner asked to keep building past Phase 0 without stopping for confirmation.
- Decision: the master prompt's "stop after governance" gate is waived for this session; open questions are logged as `proposed` ADRs and flagged.
