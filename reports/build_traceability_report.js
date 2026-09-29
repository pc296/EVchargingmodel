// Builds reports/Traceability_Report.docx from reports/traceability_facts.json.
// Every figure in the report is read from the facts file, which is regenerated from the repo's
// processed outputs by reports/traceability_facts.py. Formatting follows the owner's standing rules:
// Times New Roman, single spacing, bold+underlined section titles, no Heading styles, no title block.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, LevelFormat, BorderStyle, Footer, PageNumber, TabStopType,
  Math: OMath, MathRun, MathFraction, MathSubScript, MathSuperScript, MathSubSuperScript, MathSum,
  MathRadical, MathRoundBrackets,
} = require("docx");

const F = JSON.parse(fs.readFileSync(path.join(__dirname, "traceability_facts.json"), "utf8"));
const M = F.metrics;
const FONT = "Times New Roman";
const PAGE_W = 12240, MARGIN = 1440, TEXT_W = PAGE_W - 2 * MARGIN; // 9360 DXA
const fmt = (x, d = 3) => Number(x).toFixed(d);
const pct = (x, d = 1) => (100 * Number(x)).toFixed(d) + "%";
const int = (x) => Number(x).toLocaleString("en-US");
const usd = (x) => "$" + Math.round(Number(x)).toLocaleString("en-US");

// ---------- text helpers ----------
function runs(text, base = {}) {
  // **bold** and __bold+underline__ inline markup
  const out = [];
  const re = /(\*\*[^*]+\*\*|__[^_]+__)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, font: FONT, ...base }));
    else out.push(new TextRun({ text: t.slice(2, -2), bold: true, underline: { type: "single" }, font: FONT, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  return out;
}
const SZ = 22; // 11 pt body
const P = (text, opts = {}) => new Paragraph({
  spacing: { before: 0, after: 120, line: 240, lineRule: "auto" }, alignment: opts.align,
  children: runs(text, { size: opts.size || SZ, italics: opts.italics }),
});
const H1 = (text) => new Paragraph({
  spacing: { before: 300, after: 140, line: 240, lineRule: "auto" }, keepNext: true,
  children: [new TextRun({ text, font: FONT, size: 28, bold: true, underline: { type: "single" } })],
});
const H2 = (text) => new Paragraph({
  spacing: { before: 200, after: 100, line: 240, lineRule: "auto" }, keepNext: true,
  children: [new TextRun({ text, font: FONT, size: 24, bold: true, underline: { type: "single" } })],
});
const B = (text, level = 0) => new Paragraph({
  numbering: { reference: "bullets", level }, spacing: { before: 0, after: 60, line: 240, lineRule: "auto" },
  children: runs(text, { size: SZ }),
});
const NOTE = (text) => P(text, { size: 18, italics: true });

// ---------- tables ----------
const border = { style: BorderStyle.SINGLE, size: 4, color: "8C8C8C" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(headers, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const scale = TEXT_W / total;
  const w = widths.map((x) => Math.floor(x * scale));
  w[w.length - 1] += TEXT_W - w.reduce((a, b) => a + b, 0);
  const size = opts.size || 18;
  const cell = (text, i, header) => new TableCell({
    borders, width: { size: w[i], type: WidthType.DXA },
    shading: header ? { fill: "E7E6E6", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: String(text).split("\n").map((line) => new Paragraph({
      spacing: { before: 0, after: 0, line: 240, lineRule: "auto" },
      children: runs(line, { size, bold: header || undefined, font: (opts.mono && !header && i === opts.monoCol) ? "Courier New" : FONT }),
    })),
  });
  return new Table({
    width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: w,
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false)) })),
    ],
  });
}
const SPACER = () => new Paragraph({ spacing: { before: 0, after: 120 }, children: [] });

// ---------- math helpers ----------
const r = (t) => new MathRun(t);
const sub = (b, s) => new MathSubScript({ children: [r(b)], subScript: [r(s)] });
const sup = (b, s) => new MathSuperScript({ children: typeof b === "string" ? [r(b)] : b, superScript: [r(s)] });
const subsup = (b, s, p) => new MathSubSuperScript({ children: [r(b)], subScript: [r(s)], superScript: [r(p)] });
const frac = (n, d) => new MathFraction({ numerator: n, denominator: d });
// docx-js omits <m:sup> when an n-ary has no upper limit (schema requires it); fixed after packing.
const sum = (s, p, children) => new MathSum({ children, subScript: s ? [r(s)] : undefined, superScript: p ? [r(p)] : undefined });
const br = (children) => new MathRoundBrackets({ children });
const sqrt = (children) => new MathRadical({ children });
let eqNo = 0;
const EQ = (children) => {
  eqNo += 1;
  return new Paragraph({
    spacing: { before: 60, after: 120, line: 240, lineRule: "auto" },
    tabStops: [{ type: TabStopType.CENTER, position: TEXT_W / 2 }, { type: TabStopType.RIGHT, position: TEXT_W }],
    children: [new TextRun({ text: "\t", font: FONT }), new OMath({ children }),
               new TextRun({ text: `\t(${eqNo})`, font: FONT, size: SZ })],
  });
};

// ---------- content ----------
const shortSha = F.commit.slice(0, 7);
const c = [];

// 1 -------------------------------------------------------------------------------------------
c.push(H1("1. Purpose, Scope and Version"));
c.push(P("This report documents how the county-level EV fast-charging site selection model and its companion application were built, so that a reader can trace every result to a data source, a stated assumption, or a specific piece of code and test. It covers the data pipeline, the two predictive models, the scoring method, the build-cost scenarios, the budget-constrained site selection, and the indicative site economics. It does not repeat the business write-up."));
c.push(table(["Item", "Value"], [
  ["Project", "County-level screen for new DC fast-charging sites for an IONNA-style network (Data Analytics final project, Duke University)"],
  ["Team", "Pat Cronin, TJ Mei, Arohi Singh"],
  ["Code repository", "https://github.com/pc296/evchargingmodel (branch main)"],
  ["Version documented", `Commit ${shortSha} (${F.commit}), ${F.commit_date}`],
  ["Live application", "https://evchargingmodel-ui5fwbrdxjotcghzbovdvf.streamlit.app/"],
  ["Primary data snapshot", "AFDC station file downloaded 2026-09-22; AFDC Laws and Incentives snapshot of the same date"],
  ["Report date", "2026-09-29"],
  ["Not covered", "Branch design/ionna-palette (visual styling only; no change to data, models or results; pending owner approval)"],
], [2200, 7160]));
c.push(SPACER());
c.push(P("**Identifiers used in this report.** D-nn: data source (Section 3). T-nn: data preparation step (Section 4). A-nn: assumption (Section 5). Equations are numbered in parentheses (Section 6). ADR-nnnn: architecture decision record in docs/DECISIONS.md (Section 8). File paths are relative to the repository root."));

// 2 -------------------------------------------------------------------------------------------
c.push(H1("2. Task Understanding and Requirement Traceability"));
c.push(P("**Business problem.** IONNA, a DC fast-charging network founded by eight automakers, must decide where to build next. Each site costs roughly $1.5 to $2.6 million (Section 6.7), so poor placement ties up capital in low-use assets. The analysis answers two questions: which counties are most attractive for a new large fast-charging site, and which set of counties gives the most value for a given capital budget."));
c.push(P("**Analytical approach.** A county-by-year panel (2020 to 2025) is built from public data. Two classifiers predict whether a county gains a new large DC fast-charging site the following year (Target A) and whether a county without one gets its first (Target B). The predicted probabilities are combined with demand, supply and cost inputs into two scores, and a budget-constrained selection picks sites. An application exposes the weights, cost scenario and budget to the user."));
c.push(table(["ID", "Requirement (source)", "Where addressed", "Evidence"], [
  ["R-01", "Business understanding (course instructions)", "Section 2; docs/METHODOLOGY.md s.1; app header", "Problem statement and use case"],
  ["R-02", "Data understanding, sources, bias (course)", "Section 3; docs/DATA_SOURCES.md", "Source register, known issues, bias direction in Section 5"],
  ["R-03", "Data preparation and integration (course)", "Section 4; src/evcharge/io.py, geo.py, panel.py", `Preparation log with counts; ${int(F.panel_rows)}-row panel`],
  ["R-04", "Build and evaluate a predictive model (course)", "Sections 6.4-6.5, 7; src/evcharge/model.py", "Logistic, Lasso and random forest; temporal test; baselines"],
  ["R-05", "Visualization to explain facts (course)", "App maps and charts; reports/figures/01-04; k-means county types", "Four figures; interactive maps"],
  ["R-06", "Evaluation measures and ROI business case (course)", "Section 7; app Site economics tab; eq. (20)-(21)", "ROC AUC, PR AUC, precision at N, Brier; payback"],
  ["R-07", "Deployment, issues, ethics, risks (course)", "Live app; Section 9", "Deployed URL; limitations and risks"],
  ["R-08", "Submit data and documented code (course)", "GitHub repo; analysis/ev_charging_model_walkthrough.py and .ipynb", "Annotated walkthrough reproduces app metrics (tests/test_walkthrough.py)"],
  ["R-09", "App with tunable weights, map, budget-constrained list, cost synthesized from real data (owner)", "streamlit_app.py; Sections 6.6-6.8", "Weights, budget, cost scenario controls; CSV export"],
  ["R-10", "Python, with R where necessary (owner)", "R/cross_check.R", "reports/r_cross_check.md: PASS for both targets"],
  ["R-11", "Governance markdown per master prompt (owner)", "docs/GOVERNANCE.md and eight companion files", "Preflight, postflight, decisions, lessons, changelog"],
], [700, 2900, 3160, 2600]));

// 3 -------------------------------------------------------------------------------------------
c.push(H1("3. Data Source Register"));
c.push(P("All inputs are public. Files are stored unmodified in data/raw/ and data/external/. SHA-256 fingerprints (Table 3.2) let a reader confirm they hold identical files."));
c.push(H2("3.1 Sources used"));
const f = F.files;
const rc = (n) => f[n] && f[n].rows ? `${int(f[n].rows)} x ${f[n].cols}` : "n/a (binary)";
c.push(table(["ID", "Source and publisher", "File", "Vintage", "Unit", "Rows x cols", "Used for"], [
  ["D-01", "Alternative Fuel Stations, U.S. DOE Alternative Fuels Data Center (AFDC)", "afdc_stations_2026-09-22.csv", "Snapshot 2026-09-22", "Station", rc("afdc_stations_2026-09-22.csv"), "Charging supply by county and year; IONNA sites; posted prices"],
  ["D-02", "County population estimates, U.S. Census Bureau (CO-EST2025-POP)", "census_pop_2020_2025.xlsx", "Vintage 2025 (2020-2025)", "County", rc("census_pop_2020_2025.xlsx"), "Population, growth, density; state totals"],
  ["D-03", "Highway Performance Monitoring System, FHWA, aggregated to county by team", "hpms_2024_road_utilization.csv", "2024", "County", rc("hpms_2024_road_utilization.csv"), "Freeway vehicle-miles, freeway and interstate miles"],
  ["D-04", "Team file derived from D-03", "hpms_2024_road_utilization_imputed.csv", "2024", "County", rc("hpms_2024_road_utilization_imputed.csv"), "Connecticut planning-region traffic only (T-06)"],
  ["D-05", "Vehicle Registration Counts by State, AFDC", "afdc_registrations_by_state.csv", "Latest release (team log: 2025; see A-02)", "State", rc("afdc_registrations_by_state.csv"), "Battery-EV registrations per 1,000 residents"],
  ["D-06", "State Electricity Profiles, U.S. Energy Information Administration", "eia_state_profile_2024.csv", "2024", "State", rc("eia_state_profile_2024.csv"), "Average retail electricity price"],
  ["D-07", "Laws and Incentives download, AFDC", "afdc_laws_incentives.numbers", "Snapshot 2026-09-22", "Record", "1,645 records", "Count of state EV incentives in force by year"],
  ["D-08", "Team county file (Deliverable 2), built from D-01", "afdc_ionna_dcfc_by_county_prior.csv", "2026-09", "County", rc("afdc_ionna_dcfc_by_county_prior.csv"), "County name-to-FIPS crosswalk; reconciliation check"],
  ["D-09", "Census cartographic county boundaries (GENZ2023) as TopoJSON, npm package @severo_bo/us-atlas-2023", "us_atlas_2023_counties-10m.json", "2023", "County polygon", "3,233 polygons", "Spatial join, centroids, land area, maps"],
], [560, 2000, 1750, 1150, 800, 900, 2200], { size: 16 }));
c.push(SPACER());
c.push(table(["ID", "Literature source (cost and economics inputs)", "Used for", "Credibility"], [
  ["L-01", "Borlaug, B., Caristo, V., Ouren, F., Yang, F., Wood, E., Roberson, L. (2026). Economics of electric vehicle corridor fast charging in the United States. Advances in Applied Energy, 21.", "Per-port equipment and installation cost; transformer cost; utilization (kWh/port/day); demand-charge cost gap", "Peer-reviewed; National Renewable Energy Laboratory authors"],
  ["L-02", "Paren (2024-10-31). NEVI DC fast charging station average project cost: $915,000. Analysis of 330 NEVI award applications.", "Low scenario per-port cost; top-quartile to median ratio for High scenario", "Industry data vendor; not peer reviewed; based on public award filings"],
  ["L-03", "Schey, S., Chu, K., Smart, J. (2022). Breakdown of Electric Vehicle Supply Equipment Installation Costs. INL/RPT-22-68598.", "Cross-check of hardware and installation ranges only", "U.S. national laboratory report"],
], [560, 4200, 2600, 2000], { size: 16 }));
c.push(H2("3.2 File fingerprints (SHA-256)"));
const hashRows = Object.entries(f).map(([n, i]) => [n, i.sha256, int(i.bytes)]);
c.push(table(["File", "SHA-256", "Bytes"], hashRows, [2900, 5300, 1160], { size: 14, mono: true, monoCol: 1 }));
c.push(H2("3.3 Inputs reviewed and not used"));
c.push(table(["File (project folder)", "Reason not used"], [
  ["Cleaned Data_ByCounty.xlsx (Deliverable 2)", "Traffic column sums AADT across road segments (not a valid traffic measure); EV registrations allocated by population. Rebuilt from D-01 to D-08."],
  ["HPMS_Spatial_NHS_Sections_-_2024_AADT_Filled.csv", "Summed segment AADT; Future AADT below current AADT in 2,314 counties. Replaced by vehicle-miles from D-03."],
  ["FHWA HM-37 state tables (two .xlsx files)", "State-level mileage by AADT bucket; county-level HPMS (D-03) is finer."],
  ["afdc_charging_infrastructure_by_state_2026-09-19.csv", "State totals; county supply is derived directly from station coordinates (D-01)."],
  ["afdc_state_laws_incentives_counts_current.csv", "Counts all laws for all fuels; replaced by EV incentive records from D-07."],
  ["extraction_status_and_sources.csv", "Team extraction log; used only to confirm source URLs and vintages."],
], [3600, 5760]));

// 4 -------------------------------------------------------------------------------------------
c.push(H1("4. Data Preparation Log"));
c.push(P("Steps run in the order listed each time scripts/run_pipeline.py executes. Counts are produced by the code at the documented commit."));
const s = F.dc_status;
c.push(table(["ID", "Step and rule", "Count or effect", "Code"], [
  ["T-01", "County frame. Start from D-08 county list; remap legacy FIPS codes to 2025 geography: 02270 to 02158 (Kusilvak), 46113 to 46102 (Oglala Lakota), 02261 split into 02063 (Chugach) and 02066 (Copper River), 51515 (Bedford City, absorbed 2013) dropped.", "3,144 unique counties (50 states + DC)", "io.load_county_keys"],
  ["T-02", "Population matching. Census file has names but no FIPS; names normalized (lower case, spaces removed) before joining; any unmatched county stops the run.", "42 names differed: 41 in case or spacing only, 1 renamed (Petersburg Borough, AK, listed as Petersburg Census Area); 0 unmatched", "io.load_population"],
  ["T-03", "Station filter. Keep public stations with at least one DC fast port; keep status open (E) or temporarily unavailable (T); drop planned (P); drop records named as non-public.", `${int(F.stations_all_rows)} rows; ${int(F.dc_rows)} with DC ports (E ${int(s.E)}, T ${int(s.T)}, P ${int(s.P)}); ${F.nonpublic_dropped} non-public dropped`, "panel.prepare_stations"],
  ["T-04", "Spatial join. Point-in-polygon on station coordinates against D-09; points outside all polygons snap to nearest county within 5 km; others dropped.", `${int(F.assign.within)} within; ${int(F.assign.snapped)} snapped; ${F.pr_dropped} dropped (Puerto Rico, out of scope). Final: ${int(F.stations_used)} stations, ${int(F.stations_ports)} DC ports`, "geo.assign_county"],
  ["T-05", "Open dates. Stations with no open date are treated as opened before the panel (year 2010).", `${F.open_year_imputed} station affected`, "panel.prepare_stations"],
  ["T-06", "Traffic. Counties with no Interstate or other freeway (functional class 1-2) set to 0 vehicle-miles (structural zero), not imputed. Connecticut planning regions take the statewide total allocated by population share (D-04). Chugach and Copper River set to 0. Flag traffic_imputed.", `${int(F.no_freeway)} zero-freeway counties (1,377 current counties in D-03, which also lists the retired Bedford City, plus 2 Alaska areas); ${F.traffic_imputed} flagged (9 CT, 2 AK)`, "io.load_traffic"],
  ["T-07", "Geometry fallback. Falls Church city, VA has no polygon after simplification; published centroid and 2.0 sq mi area used; its stations fall into neighboring counties.", "1 county", "geo.load_counties"],
  ["T-08", "EV registrations. State battery-EV count divided by 2025 state population (sum of D-02 counties).", "51 state rates", "panel.build_panel"],
  ["T-09", "Incentives. From 1,645 law records keep technology ELEC, type State Incentives or Incentives, state not US, status not archived or expired.", `${int(F.ev_incentives_n)} records; ${int(F.inc_missing_date)} (${pct(F.inc_missing_date / F.ev_incentives_n, 0)}) lack an enacted date`, "io.load_incentives"],
  ["T-10", "Prices. Parse $/kWh from AFDC pricing text (valid range $0.05-$1.50); state median where a state has 10 or more priced stations, else national median.", `${int(F.price_parsed)} stations parsed; national median $${fmt(M.dcfc_price_national_median, 2)}/kWh; ${int(F.price_imputed_counties)} counties use the national median`, "scripts/run_pipeline.py"],
  ["T-11", "Panel. One row per county per year 2020-2025 at end of year; supply cumulative by open year. A separate snapshot row per county (2026-09-22) holds current supply for the app and is not part of the panel count.", `${int(F.panel_rows)} rows x ${F.panel_cols} columns`, "panel.build_panel"],
  ["T-12", "Reconciliation against the team's Deliverable 2 county file (D-08).", `DC ports ${int(F.stations_ports)} vs ${int(F.prior_ports)} (+${int(F.stations_ports - F.prior_ports)}, ${pct((F.stations_ports - F.prior_ports) / F.prior_ports)}); IONNA sites ${F.ionna_sites} vs ${F.prior_ionna_sites}. Difference: this pipeline counts temporarily unavailable stations.`, "Computed by reports/traceability_facts.py; tests/test_pipeline_outputs.py checks no in-scope station is lost"],
], [620, 4300, 2900, 1540], { size: 16 }));

// 5 -------------------------------------------------------------------------------------------
c.push(H1("5. Assumptions Register"));
c.push(P("Each assumption lists why it was made, its likely effect on results, and whether it was tested. \"Team judgment\" marks choices without an external source; these are exposed as adjustable inputs in the application where possible."));
const A = [
  ["A-01", "EV adoption is uniform within a state: county BEVs = state BEVs per 1,000 residents x county population (eq. 2).", "County registration data not obtained (D-05 is state level).", "Understates urban and high-income county demand; overstates rural. Within a state, EV demand ranks counties by population only.", "Not tested. Planned fix: Atlas EV Hub county data plus Census ACS predictors."],
  ["A-02", "The D-05 registration vintage represents current adoption and is held constant across 2020-2025.", "Only one vintage in hand; the team log labels it 2025 but the year is unconfirmed.", "EV feature has no time variation, so the models cannot learn from adoption growth.", "Not tested. Open item: confirm vintage; add annual history."],
  ["A-03", "Stations in the 2026-09-22 file represent historical supply.", "AFDC file lists current stations only.", "Closed stations are missing, so past supply and some past new-site events are slightly undercounted.", "Not tested."],
  ["A-04", "Open date marks entry into service; the one station without a date predates 2020.", "Only 1 affected station.", "Negligible.", "Count checked (T-05)."],
  ["A-05", "Temporarily unavailable (T) stations count as supply; planned (P) stations do not.", "T stations are built capacity.", "Supply 2.1% above the team's earlier count (T-12).", "Reconciled (T-12)."],
  ["A-06", "A \"large\" site has 4 or more DC fast ports.", "IONNA sites average " + fmt(F.ionna_mean_ports, 2) + " ports (D-01); four ports is the minimum under federal NEVI standards (23 CFR 680).", "Defines both targets; a higher threshold would lower base rates.", "Not tested at other thresholds."],
  ["A-07", "Counties with no Interstate or other freeway have zero freeway traffic.", "Absence of the road class is a true zero, not missing data.", "Correct by construction; replaces Deliverable 2 imputation that inflated rural traffic.", "Unit test (tests/test_io_geo.py)."],
  ["A-08", "Connecticut planning-region traffic = statewide total x population share.", "HPMS 2024 reports legacy CT counties.", "Small error for 9 of 3,144 counties.", "Flagged in data (traffic_imputed)."],
  ["A-09", "Traffic (2024) and electricity price (2024) are constant over 2020-2025.", "Single vintages in hand.", "No time variation for these features.", "Not tested."],
  ["A-10", "EV incentive records without an enacted date were in force in every year; the count of records measures policy support.", `${pct(F.inc_missing_date / F.ev_incentives_n, 0)} of records lack a date; value of incentives not available.`, "Incentive feature is mostly static and ignores incentive size.", "Not tested."],
  ["A-11", "The county centroid represents county location; distances are great-circle, not road distance.", "Sub-county siting data not in scope.", "Distances approximate; larger error for large western counties.", "Not tested."],
  ["A-12", "Tesla Superchargers are full competitors.", "Owner decision (ADR-0008); Tesla network open to other brands.", "Raises measured saturation where Tesla is dense.", "Not tested at partial weights."],
  ["A-13", "Nearby supply is measured within 50 miles.", "Spacing used by the federal NEVI corridor program.", "Defines one saturation input.", "Not tested at other radii."],
  ["A-14", "Features at end of year t are known when deciding; outcomes are observed in t+1.", "Prevents look-ahead bias.", "Honest forecast evaluation.", "Enforced in panel.py (label shifted one year); tests check 2025 labels are empty, B is defined only where L = 0, and every label equals the next year's outcome."],
  ["A-15", "Relationships learned from 2022-2024 outcomes hold for 2025 and 2026.", "Standard for forecasting.", "Market growth may shift the base rate; ranking metrics are less sensitive than calibration.", "Tested: 2025 test year and 2026 partial-year check (Section 7)."],
  ["A-16", "County-year rows are treated as independent when fitting.", "Standard logistic regression.", "Repeated observations of the same county understate coefficient standard errors; p-values are optimistic.", "Predictive accuracy checked with states held out; p-values read as indicative only."],
  ["A-17", "Where the market has built is a proxy for where sites are attractive.", "No public profitability or utilization data by county.", "Models may favor crowded markets; handled by the saturation penalty (eq. 16).", "Not testable with public data."],
  ["A-18", "Score inputs are made comparable as percentile ranks and combined linearly with default weights 0.25, 0.25, 0.05, 0.20, 0.10, 0.05, 0.10.", "Team judgment.", "Rankings depend on weights; state-level inputs move all counties in a state together (default picks lean toward Texas).", "User-adjustable in app; not formally tested."],
  ["A-19", "Saturation penalty = 0.5; saturation = mean percentile of DC ports per 1,000 EVs and DC ports within 50 miles.", "Team judgment.", "Higher penalty shifts picks toward underserved counties.", "User-adjustable in app."],
  ["A-20", "The k-th new site in a county is worth 0.5^(existing IONNA sites + k - 1) of the county score; at most 2 new sites per county by default.", "Team judgment; diminishing returns within a market.", "Spreads picks across counties.", "User-adjustable in app."],
  ["A-21", "A site has 8 DC ports; cost = ports x per-port cost + fixed site cost; land, feeder and substation upgrades and regional cost differences are excluded.", "L-01, L-02; IONNA average site size.", "Costs likely understated where grid upgrades or high land costs apply.", "Three scenarios (Section 6.7)."],
  ["A-22", "High scenario = Base x 1.31 (NEVI top-quartile / median project cost).", "L-02 cost dispersion.", "Brackets upper-range projects.", "Scenario in app."],
  ["A-23", "No grant funding by default (grant share 0%).", "NEVI availability varies by state and over time.", "Conservative capital need.", "User-adjustable in app."],
  ["A-24", "Utilization is 176 kWh per port per day in every county.", "L-01 national 2025 average (4% capacity factor).", "Payback understated for strong counties and overstated for weak ones.", "User-adjustable in app."],
  ["A-25", "Charging price = state median posted $/kWh, or national median where fewer than 10 priced stations.", "D-01 pricing text.", `${int(F.price_imputed_counties)} counties use the national median $${fmt(M.dcfc_price_national_median, 2)}.`, "User can switch to a flat price. Parser reads the first $/kWh figure only; session, idle and membership fees are ignored."],
  ["A-26", "Energy cost = state average retail price + $0.12/kWh adder for demand charges.", "Adder = gap in L-01 levelized cost between stations with and without demand charges ($0.43 vs $0.31/kWh), used as a proxy.", "Approximation; the gap reflects all costs, not only demand charges.", "User-adjustable in app."],
  ["A-27", "Economics exclude O&M, lease, network and payment fees, taxes and storage; payback is simple and undiscounted.", "Screening purpose.", "Payback understated relative to a full pro forma.", "Stated in app."],
  ["A-28", "Model probabilities use end-2025 features while current supply uses the 2026-09-22 snapshot; the snapshot reuses 2025 population and growth.", "2026 is a partial year, so it cannot serve as a feature year.", "Minor timing mismatch.", "Not tested."],
  ["A-29", "Each station's current DC port count, and therefore its large-site status, applies from its open year.", "The station file has no port history.", "A site that expanded later counts as large from opening, slightly overstating early large-site events.", "Not tested."],
  ["A-30", "Connecticut Interstate miles equal its freeway miles in the allocated totals.", "HPMS legacy-county data does not split the allocation by road class.", "Small overstatement of Interstate miles for 9 counties.", "Flagged (traffic_imputed)."],
  ["A-31", "Networks are identified by name: Tesla where the network name contains \"Tesla\"; IONNA by exact name.", "AFDC network field.", "Misspelled or rebranded network names would be misclassified.", "Spot-checked: 180 IONNA sites."],
  ["A-32", "Score percentiles are ranked across all 3,144 counties, even when the app user filters by state or minimum population.", "Keeps scores comparable across filters.", "Filtered views show national, not within-filter, percentiles.", "By design."],
];
c.push(table(["ID", "Assumption", "Rationale or source", "Likely effect", "Tested?"], A, [560, 2850, 2200, 2150, 1600], { size: 16 }));

// 6 -------------------------------------------------------------------------------------------
c.push(H1("6. Model Specification and Equations"));
c.push(H2("6.1 Notation"));
c.push(P("County i, state s(i), year t. P: population; A: land area (sq mi); Q: DC fast ports open by end of year; L: large sites (4+ DC ports) open by end of year; n: large sites opened during the year; R: state battery-EV registrations. Logs use the natural base; ln1p(x) = ln(1 + x)."));
c.push(H2("6.2 Feature construction"));
c.push(P("Population growth and density:"));
c.push(EQ([sub("g", "i,t"), r(" = "), frac([sub("P", "i,t")], [sub("P", "i,t−1")]), r(" − 1,    "), sub("density", "i,t"), r(" = ln"), br([r("max"), br([sub("P", "i,t"), r("/"), sub("A", "i"), r(", 0.1")])])]));
c.push(P("State BEV rate and estimated county EVs (assumption A-01):"));
c.push(EQ([sub("b", "s"), r(" = 1000 · "), frac([sub("R", "s")], [sub("P", "s,2025")]), r(",    "), sub("E", "i,t"), r(" = "), sub("b", "s(i)"), r(" · "), frac([sub("P", "i,t")], [r("1000")])]));
c.push(P("Local supply density:"));
c.push(EQ([sub("ρ", "i,t"), r(" = 1000 · "), frac([sub("Q", "i,t")], [r("max"), br([sub("E", "i,t"), r(", 1")])])]));
c.push(P("Great-circle distance between points (latitude φ, longitude λ, Earth radius 3,958.8 miles), and distance from county centroid to the nearest large site open by year t:"));
c.push(EQ([r("d = 2R · arcsin"), sqrt([sup("sin", "2"), br([frac([r("Δφ")], [r("2")])]), r(" + cos"), sub("φ", "1"), r(" cos"), sub("φ", "2"), r(" "), sup("sin", "2"), br([frac([r("Δλ")], [r("2")])])])]));
c.push(EQ([sub("D", "i,t"), r(" = "), sub("min", "j ∈ large, open ≤ t"), r(" d"), br([r("i, j")])]));
c.push(P("DC ports within 50 miles and state build momentum:"));
c.push(EQ([subsup("N", "i,t", "50"), r(" = "), sum("j: d(i,j) ≤ 50, open ≤ t", null, [sub("q", "j")]), r(",    "), sub("m", "st"), r(" = "), sup("10", "6"), r(" · "), frac([sum("i ∈ s", null, [sub("n", "i,t")])], [sum("i ∈ s", null, [sub("P", "i,t")])])]));
c.push(P("The 17 model features (vector x_it) are:"));
c.push(table(["Feature", "Definition", "Source"], [
  ["log_pop", "ln P_it", "D-02"], ["pop_growth", "g_it, eq. (1)", "D-02"], ["log_density", "eq. (1)", "D-02, D-09"],
  ["bev_per_1k", "b_s, eq. (2)", "D-05, D-02"], ["elec_price_c_kwh", "State average retail price, cents/kWh", "D-06"],
  ["ev_incentives", "State EV incentive records enacted by t (A-10)", "D-07"], ["log_fwy_vmt", "ln1p(daily freeway vehicle-miles)", "D-03"],
  ["has_freeway", "1 if county has Interstate or freeway miles", "D-03"], ["log_interstate_miles", "ln1p(Interstate miles)", "D-03"],
  ["log_dcfc_ports", "ln1p(Q_it)", "D-01"], ["log_large_sites", "ln1p(L_it)", "D-01"], ["log_ports_per_1k_bev", "ln1p(ρ_it), eq. (3)", "D-01, D-05"],
  ["tesla_share", "Tesla DC ports / Q_it (0 if Q_it = 0)", "D-01"], ["log_dist_large_dcfc", "ln1p(D_it), eq. (5)", "D-01, D-09"],
  ["log_ports_50mi", "ln1p(N50_it), eq. (6)", "D-01, D-09"], ["log_new_large_t", "ln1p(n_it)", "D-01"], ["state_new_large_per_1m", "m_st, eq. (6)", "D-01, D-02"],
], [2600, 4760, 2000], { size: 16 }));
c.push(H2("6.3 Targets"));
c.push(EQ([subsup("y", "i,t", "A"), r(" = 1"), br([sub("n", "i,t+1"), r(" > 0")]), r(",    "), subsup("y", "i,t", "B"), r(" = 1"), br([sub("n", "i,t+1"), r(" > 0")]), r("  defined only where  "), sub("L", "i,t"), r(" = 0")]));
c.push(P("Feature years t = 2020-2024 have labels (outcome years 2021-2025). 2025 features have no label and are used for scoring."));
c.push(H2("6.4 Classifiers"));
c.push(P("**Logistic regression (primary).** Features are standardized with training-sample means and standard deviations, z_k = (x_k - μ_k) / σ_k, and the model is fitted by maximum likelihood (scikit-learn, C = 10^6, effectively unpenalized; statsmodels for standard errors):"));
c.push(EQ([r("Pr"), br([sub("y", "i,t"), r(" = 1 ∣ "), sub("x", "i,t")]), r(" = "), frac([r("1")], [r("1 + exp"), br([r("−"), sub("β", "0"), r(" − "), sum("k=1", "K", [sub("β", "k"), r(" "), sub("z", "i,t,k")])])])]));
c.push(EQ([sub("θ", "k"), r(" = exp"), br([sub("β", "k")]), r(",    95% interval: exp"), br([sub("β", "k"), r(" ± 1.96 "), sub("SE", "k")])]));
c.push(P("θ_k is the odds ratio for a one-standard-deviation increase in feature k."));
c.push(P("**Lasso logistic regression.** Same form with an L1 penalty (scikit-learn formulation); C chosen from 20 values by 5-fold cross-validated ROC AUC on the training years (folds stratified by row, not grouped by county, so a county can appear on both sides of a fold):"));
c.push(EQ([sub("min", "β"), r("  "), sum("k", null, [r("∣"), sub("β", "k"), r("∣")]), r(" + C "), sum("i,t", null, [r("ℓ"), br([sub("y", "i,t"), r(", "), sub("p", "i,t")])]), r(",    ℓ(y, p) = −y ln p − (1 − y) ln(1 − p)")]));
c.push(P(`Selected C: ${fmt(M.A.lasso_C, 4)} (Target A), ${fmt(M.B.lasso_C, 4)} (Target B).`));
c.push(P("**Random forest.** 400 classification trees on bootstrap samples, minimum 20 observations per leaf, 50% of features considered at each split, seed 42; the predicted probability is the mean of the trees' leaf class frequencies. Importance is measured as the drop in test ROC AUC when a feature is randomly permuted (5 repeats)."));
c.push(H2("6.5 Validation design and metrics"));
c.push(P(`Training: feature years 2021-2023 (Target A: ${int(F.train.A_n)} rows, ${int(F.train.A_pos)} positives; Target B: ${int(F.train.B_n)} rows, ${int(F.train.B_pos)} positives). Test: feature year 2024, outcomes 2025. Feature year 2020 is excluded because population growth requires a prior year. Robustness: 5-fold cross-validation grouped by state over feature years 2021-2024. Out-of-time check: models refit on feature years 2021-2024, scored on end-2025 features, compared with large sites opened 2026-01-01 to 2026-09-22.`));
c.push(EQ([r("AUC = Pr"), br([sub("p", "(1)"), r(" > "), sub("p", "(0)")])]));
c.push(EQ([r("Brier = "), frac([r("1")], [r("n")]), sum("i", null, [sup([br([sub("p", "i"), r(" − "), sub("y", "i")])], "2")])]));
c.push(EQ([r("PR AUC = "), sum("n", null, [br([sub("R", "n"), r(" − "), sub("R", "n−1")]), r(" "), sub("V", "n")])]));
c.push(P("In (11)-(13), p_(1) and p_(0) are the predicted probabilities of a randomly chosen county with and without the event; R_n and V_n are recall and precision at the n-th threshold. Precision at N is the share of actual positives among the N highest-ranked counties, with N equal to the number of actual positives."));
c.push(P("Baselines rank counties by a single variable (population, freeway vehicle-miles, existing DC ports) converted to percentile ranks; tied values share their average rank."));
c.push(H2("6.6 Scores"));
c.push(P("For each score input k with value x_ik, the percentile rank across the 3,144 counties (average rank for ties) is:"));
c.push(EQ([sub("u", "ik"), r(" = "), frac([r("rank"), br([sub("x", "ik")])], [r("n")]), r("  (higher is better),    "), sub("u", "ik"), r(" = 1 − "), frac([r("rank"), br([sub("x", "ik")])], [r("n")]), r(" + "), frac([r("1")], [r("n")]), r("  (lower is better)")]));
c.push(EQ([sub("NOS", "i"), r(" = 100 · "), frac([sum("k", null, [sub("w", "k"), r(" "), sub("u", "ik")])], [sum("k", null, [sub("w", "k")])])]));
c.push(EQ([sub("S", "i"), r(" = "), frac([sub("u", "i,ρ"), r(" + "), sub("u", "i,N50")], [r("2")]), r(",    "), sub("FDS", "i"), r(" = "), sub("NOS", "i"), r(" · "), br([r("1 − λ "), sub("S", "i")]), r(",   λ = 0.5")]));
c.push(table(["Score input k", "Variable", "Direction", "Default weight w_k"], [
  ["Estimated EVs", "E_i", "Higher", "0.25"], ["Freeway traffic", "daily freeway vehicle-miles", "Higher", "0.25"],
  ["Population growth", "g_i", "Higher", "0.05"], ["Market momentum", "Model A probability", "Higher", "0.20"],
  ["Whitespace entry", "Model B probability (0 where L_i > 0)", "Higher", "0.10"], ["Policy", "EV incentive count", "Higher", "0.05"],
  ["Power cost", "Electricity price", "Lower", "0.10"],
], [2400, 3500, 1300, 2160], { size: 16 }));
c.push(H2("6.7 Build cost"));
c.push(EQ([sub("C", "site"), r(" = "), br([sub("c", "port"), r(" · K + "), sub("F", "site")]), r(" · m · "), br([r("1 − γ")])]));
c.push(P("K = ports per site (default 8); m = regional multiplier (1.0; no regional adjustment); γ = grant share (default 0)."));
const bp = 141900 + 90800, tq = 1053624 / 802267;
c.push(table(["Scenario", "Per port c_port", "Fixed F_site", "8-port site", "Basis"], [
  ["Low", usd(183116), "$0", usd(183116 * 8), "Median NEVI award cost per port, all-in (L-02)"],
  ["Base", usd(bp), usd(100000), usd(bp * 8 + 100000), "NREL 350 kW equipment $141,900 + installation $90,800; distribution transformer (L-01)"],
  ["High", usd(bp * tq), usd(100000 * tq), usd((bp * 8 + 100000) * tq), `Base x ${fmt(tq, 3)} (NEVI top-quartile $1,053,624 / median $802,267, L-02)`],
], [1000, 1500, 1300, 1400, 4160], { size: 16 }));
c.push(H2("6.8 Budget-constrained site selection"));
c.push(P("Each county i may receive new sites k = 1..M (default M = 2). With V_i the chosen score (FDS or NOS), h_i the county's existing IONNA sites, and δ the value retained by each additional site (default 0.5):"));
c.push(EQ([sub("v", "ik"), r(" = "), sub("V", "i"), r(" · "), sup("δ", "h_i + k − 1")]));
c.push(EQ([sub("max", "x"), r("  "), sum("i,k", null, [sub("v", "ik"), r(" "), sub("x", "ik")]), r("   s.t.   "), sum("i,k", null, [sub("C", "ik"), r(" "), sub("x", "ik")]), r(" ≤ B,   "), sub("x", "ik"), r(" ≤ "), sub("x", "i,k−1"), r(",   "), sub("x", "ik"), r(" ∈ {0, 1}")]));
c.push(P("When all sites cost the same (the default), selecting the ⌊B / C_site⌋ highest values v_ik is exactly optimal, because v_ik falls with k and every item has equal cost. The application uses one cost per site, so this rule is what it applies. A value-per-dollar heuristic and the exact integer program (SciPy milp, HiGHS solver) are implemented in src/evcharge/optimize.py and unit-tested for future use with unequal costs, but the application does not call them today."));
c.push(H2("6.9 Indicative site economics"));
c.push(EQ([r("kWh = K · q · 365,    Rev = kWh · "), sub("p", "s"), r(",    Cost = kWh · "), br([frac([sub("e", "s")], [r("100")]), r(" + a")])]));
c.push(EQ([r("GM = Rev − Cost,    Payback = "), frac([sub("C", "site")], [r("GM")]), r("  (if GM > 0)")]));
c.push(P(`q = kWh per port per day (default ${176}); p_s = state median posted price ($/kWh); e_s = state retail electricity price (cents/kWh); a = demand-charge adder (default $0.12/kWh).`));

// 7 -------------------------------------------------------------------------------------------
c.push(H1("7. Validation Evidence"));
c.push(H2("7.1 Test-year results (feature year 2024, outcomes 2025)"));
const mrow = (name, d) => [name, fmt(d.roc_auc), fmt(d.pr_auc), fmt(d.precision_at_n_positives), d.brier == null ? "n/a" : fmt(d.brier)];
const names = { logit: "Logistic regression", lasso: "Lasso logistic", forest: "Random forest", rank_by_population: "Baseline: population", rank_by_freeway_vmt: "Baseline: freeway traffic", rank_by_existing_ports: "Baseline: existing ports" };
for (const t of ["A", "B"]) {
  const d = M[t]; const lg = d.test.logit;
  c.push(P(`**Target ${t}** (${t === "A" ? "new large site" : "first large site"}): ${int(lg.n)} test counties, ${int(lg.positives)} positives, base rate ${pct(lg.base_rate)}.`));
  c.push(table(["Method", "ROC AUC", "PR AUC", "Precision at N", "Brier"],
    [...Object.entries(d.test), ...Object.entries(d.baselines)].map(([k, v]) => mrow(names[k], v)), [3160, 1550, 1550, 1550, 1550], { size: 16 }));
  c.push(SPACER());
}
c.push(P(`Lasso retained ${F.lasso_nonzero_A} of 17 features for Target A and ${F.lasso_nonzero_B} of 17 for Target B. Neither Lasso nor the random forest improved materially on logistic regression.`));
c.push(H2("7.2 Robustness and out-of-time checks"));
const cv = (t, k) => M[t].cv_by_state[k];
c.push(table(["Check", "Target A", "Target B"], [
  ["States held out, logistic: mean ROC AUC (range)", `${fmt(cv("A", "logit").mean_auc)} (${fmt(cv("A", "logit").min_auc)}-${fmt(cv("A", "logit").max_auc)})`, `${fmt(cv("B", "logit").mean_auc)} (${fmt(cv("B", "logit").min_auc)}-${fmt(cv("B", "logit").max_auc)})`],
  ["States held out, random forest: mean ROC AUC (range)", `${fmt(cv("A", "forest").mean_auc)} (${fmt(cv("A", "forest").min_auc)}-${fmt(cv("A", "forest").max_auc)})`, `${fmt(cv("B", "forest").mean_auc)} (${fmt(cv("B", "forest").min_auc)}-${fmt(cv("B", "forest").max_auc)})`],
  ["2026 partial year (Jan 1 - Sep 22), ROC AUC", fmt(M.live_2026_partial.roc_auc_A), fmt(M.live_2026_partial.roc_auc_B)],
], [4760, 2300, 2300], { size: 16 }));
c.push(P(`2026 base rate for Target A: ${pct(M.live_2026_partial.base_rate)} of counties (partial year).`));
c.push(H2("7.3 Logistic regression coefficients"));
const feats = Object.keys(M.A.logit_coefficients);
const orow = (k) => {
  const a = M.A.logit_coefficients[k], b = M.B.logit_coefficients[k];
  const cell = (v) => v ? `${fmt(v.odds_ratio_per_sd, 2)} (${fmt(v.ci_lo, 2)}-${fmt(v.ci_hi, 2)})` : "dropped (constant)";
  const pv = (v) => v ? (v.p_value < 0.001 ? "<0.001" : fmt(v.p_value, 3)) : "";
  return [k, cell(a), pv(a), cell(b), pv(b)];
};
c.push(table(["Feature", "A: OR per SD (95% CI)", "A: p", "B: OR per SD (95% CI)", "B: p"], feats.map(orow), [2600, 2200, 950, 2200, 1410], { size: 16 }));
c.push(NOTE("Odds ratios are per one standard deviation of the training sample. For Target B, existing large sites and new large sites this year are always zero and are dropped. has_freeway and log_fwy_vmt must be read together (a county without freeway has log VMT of 0), so the has_freeway odds ratio below 1 reflects coding, not a negative effect. p-values are optimistic because county-years are not independent (A-16)."));
c.push(H2("7.4 Independent reimplementation in R"));
c.push(table(["Check", "Target A", "Target B", "Tolerance", "Result"], [
  ["Logistic test ROC AUC, R (glm) vs Python", "0.8839 vs 0.8839", "0.8173 vs 0.8172", "< 0.005", "Pass"],
  ["Max absolute coefficient difference (standardized)", "0.00005", "0.00005", "< 0.01", "Pass"],
  ["Lasso test ROC AUC, R (glmnet) vs Python", "0.8843 vs 0.8850", "0.8187 vs 0.8180", "Information", "Consistent"],
], [3160, 1700, 1700, 1200, 1600], { size: 16 }));
c.push(P("R 4.3.3 with glmnet 4.1.8 and pROC 1.18.5, run by R/cross_check.R on the exported panel; output in reports/r_cross_check.md. The two Lasso fits select different penalties (different grids and selection rules): for Target A glmnet kept 17 of 17 features against 8 in scikit-learn; for Target B glmnet kept 8 of 14 non-constant features against 10 of 17. Test AUCs agree within 0.001."));
c.push(H2("7.5 Automated tests"));
c.push(table(["Test file", "What it verifies"], [
  ["tests/test_scoring_optimize.py (9 tests)", "Percentile direction; score bounds and penalty; zero-weight error; per-site value decay with existing sites; equal-cost selection is top N; integer program respects budget and order; budget below one site; cost scenarios; economics arithmetic"],
  ["tests/test_io_geo.py (5 tests)", "Price parsing; county crosswalk (3,144 unique, legacy codes removed); traffic structural zeros; distance on a known pair (Durham-Raleigh); spatial join on a known point"],
  ["tests/test_pipeline_outputs.py (6 tests)", "Panel shape and unique keys; label definitions; labels equal the next year's outcome; cumulative supply; no in-scope stations lost in the spatial join; app table ranges, including that the model beats the population baseline"],
  ["tests/test_walkthrough.py (1 slow test)", "The annotated submission walkthrough reproduces the pipeline's test ROC AUC for all three methods and both targets"],
], [3200, 6160], { size: 16 }));
c.push(P("Result at the documented commit: 20 passed and 1 skipped by default; the slow test passes when run with RUN_SLOW=1 (21 of 21)."));

// 8 -------------------------------------------------------------------------------------------
c.push(H1("8. Decision Log and Changes from Deliverable 2"));
c.push(H2("8.1 Recorded decisions"));
c.push(table(["Decision", "Status"], [
  ...F.adrs.map((a) => [a, "Accepted"]),
  ["ADR-0013: Visual style drawn from IONNA's public site, without brand assets", "Proposed (branch design/ionna-palette)"],
], [7360, 2000], { size: 16 }));
c.push(P("Full context, alternatives and consequences for each decision are in docs/DECISIONS.md; mistakes found and the rules adopted are in docs/LESSONS.md."));
c.push(H2("8.2 Changes from Deliverable 2"));
c.push(table(["Area", "Deliverable 2", "Current", "Reason"], [
  ["Target", "Score described as the dependent variable; label implied as \"county has a station\"", "Target A: new 4+ port site in t+1; Target B: first such site", "About 60% of counties already had a station; the label recorded the present"],
  ["Observation", "County, single cross-section", "County x year panel, 2020-2025", "A next-year target needs history; enables testing on a later year"],
  ["Validation", "Random 70/30 split", "Train 2021-2023, test 2024; states held out; 2026 check", "Random splits leak time and geography"],
  ["Traffic", "Sum of segment AADT; 234 counties filled from population neighbors", "Freeway vehicle-miles; 1,379 structural zeros; CT allocated", "Summed AADT depends on segmentation; zeros are not missing"],
  ["Future AADT", "Planned feature", "Dropped", "Below current AADT in 2,314 counties"],
  ["Station to county", "AI categorization of addresses", "Point-in-polygon on coordinates", "Reproducible and auditable"],
  ["EV registrations", "State totals allocated by population", "Unchanged (A-01), stated as a limitation", "County data not yet obtained"],
  ["Electricity, incentives", "\"Potentially\" included", "Included (all-sector price; EV incentive records)", "Completes planned feature set"],
  ["Outputs", "Net Opportunity and Future Deployment scores", "Same two scores, defined by eq. (15)-(16), plus cost and budget selection", "Owner requirement for a capital-constrained list"],
], [1300, 2600, 2700, 2760], { size: 16 }));

// 9 -------------------------------------------------------------------------------------------
c.push(H1("9. Limitations, Risks and Open Items"));
[
  "**Models describe past build decisions, not profitability.** Neither target observes utilization or revenue. Counties the market has avoided for good reasons may still score low; counties crowded with competitors can score high on Model A. The saturation penalty and weights are the user's lever.",
  "**Lift over simple rules is moderate.** Population alone reaches ROC AUC 0.852 (A) and 0.772 (B); the models reach 0.884 and 0.817. The value of the models is consistent incremental ranking, not discovery of hidden markets.",
  "**State-level inputs dominate within-state differences** for EV adoption, electricity price and incentives (A-01, A-09, A-10). This concentrates default recommendations in some states, notably Texas.",
  "**Costs exclude land, major grid upgrades and regional differences** (A-21). Sites needing feeder or substation work can cost several million dollars more (L-01).",
  "**Equity and access.** Following past build patterns can reinforce gaps in rural and lower-income areas. Users can raise the saturation penalty or the whitespace-entry weight to counter this; an explicit equity input is not included.",
  "**Site-level placement is out of scope.** Recommendations are counties; markers sit at county centroids.",
  "**Open data items:** county-level EV registrations (Atlas EV Hub) and Census ACS demographics; annual AFDC registration history; confirmation of the D-05 vintage; EIA commercial electricity prices; BEA Regional Price Parities for regional cost adjustment.",
].forEach((t) => c.push(B(t)));

// 10 ------------------------------------------------------------------------------------------
c.push(H1("10. Reproducibility"));
const v = F.versions;
c.push(table(["Component", "Version"], [
  ["Python", v.python], ["pandas / numpy", `${v.pandas} / ${v.numpy}`], ["scikit-learn / statsmodels / scipy", `${v.sklearn} / ${v.statsmodels} / ${v.scipy}`],
  ["geopandas / plotly / streamlit", `${v.geopandas} / ${v.plotly} / ${v.streamlit}`], ["R / glmnet / pROC", "4.3.3 / 4.1.8 / 1.18.5"], ["Random seed", "42 (all stochastic steps)"],
], [4680, 4680], { size: 16 }));
c.push(SPACER());
c.push(P("Commands, run from the repository root:"));
[
  "pip install -r requirements-dev.txt",
  "python scripts/run_pipeline.py  (rebuilds data/processed/ from data/raw/; about 90 seconds)",
  "pytest -q  (add RUN_SLOW=1 to include the walkthrough reproduction test)",
  "Rscript R/cross_check.R  (writes reports/r_cross_check.md)",
  "python analysis/ev_charging_model_walkthrough.py  (self-contained annotated version; also runs in Google Colab)",
  "streamlit run streamlit_app.py  (local copy of the application)",
].forEach((t) => c.push(B(t)));
c.push(P("Governance: every change follows docs/PREFLIGHT.md and docs/POSTFLIGHT.md; changes are recorded in docs/CHANGELOG.md."));

// 11 ------------------------------------------------------------------------------------------
c.push(H1("11. References"));
[
  "Borlaug, B., Caristo, V., Ouren, F., Yang, F., Wood, E., Roberson, L. (2026). Economics of electric vehicle corridor fast charging in the United States. Advances in Applied Energy, 21. https://www.sciencedirect.com/science/article/pii/S2666792425000514",
  "Federal Highway Administration (2024). Highway Performance Monitoring System, HPMS Spatial Data 2024. https://data.transportation.gov",
  "Indian Type Foundry (2026). Fontshare ITF Free Font License, version 2.0. https://www.fontshare.com/licenses/itf-ffl (application styling only)",
  "Paren (2024, October 31). NEVI DC fast charging station average project cost: $915,000. https://www.paren.app/blog/nevi-dc-fast-charging-station-total-project-cost-averages-915-000",
  "Schey, S., Chu, K., Smart, J. (2022). Breakdown of Electric Vehicle Supply Equipment Installation Costs. Idaho National Laboratory, INL/RPT-22-68598. https://inldigitallibrary.inl.gov/sites/sti/sti/Sort_63124.pdf",
  "U.S. Census Bureau (2026). Annual Estimates of the Resident Population for Counties: April 1, 2020 to July 1, 2025 (CO-EST2025-POP). https://www.census.gov/data/developers/data-sets/popest-popproj/popest.html",
  "U.S. Census Bureau (2023). Cartographic Boundary Files, GENZ2023, redistributed as TopoJSON in npm package @severo_bo/us-atlas-2023.",
  "U.S. Department of Energy, Alternative Fuels Data Center (2026). Alternative Fueling Station Locator data download, snapshot 2026-09-22. https://afdc.energy.gov/stations",
  "U.S. Department of Energy, Alternative Fuels Data Center. Vehicle Registration Counts by State. https://afdc.energy.gov/vehicle-registration",
  "U.S. Department of Energy, Alternative Fuels Data Center (2026). Laws and Incentives data download, snapshot 2026-09-22. https://afdc.energy.gov/data_download",
  "U.S. Energy Information Administration (2025). State Electricity Profiles 2024. https://www.eia.gov/electricity/state/",
  "23 CFR Part 680, National Electric Vehicle Infrastructure Standards and Requirements.",
].forEach((t) => c.push(new Paragraph({
  spacing: { before: 0, after: 100, line: 240, lineRule: "auto" }, indent: { left: 360, hanging: 360 },
  children: runs(t, { size: SZ }),
})));

// ---------- document ----------
const doc = new Document({
  creator: "Pat Cronin, TJ Mei, Arohi Singh",
  title: "Traceability Report: EV Charging Expansion Model",
  styles: { default: { document: { run: { font: FONT, size: SZ } } } },
  numbering: { config: [{ reference: "bullets", levels: [
    { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 360 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "o", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
  ] }] },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 15840 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: `Traceability report, commit ${shortSha}. Page `, font: FONT, size: 16 }),
      new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16 }),
      new TextRun({ text: " of ", font: FONT, size: 16 }),
      new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: 16 }),
    ] })] }) },
    children: c,
  }],
});
Packer.toBuffer(doc).then((buf) => {
  const out = path.join(__dirname, "Traceability_Report.docx");
  fs.writeFileSync(out, buf);
  require("child_process").execFileSync("python3", [path.join(__dirname, "fix_docx_math.py"), out], { stdio: "inherit" });
  console.log("wrote", out, buf.length, "bytes;", eqNo, "equations");
});
