"""IONNA charging expansion planner: tune weights, set a budget, get a map and ranked site list."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from evcharge import cost, optimize, scoring  # noqa: E402
from evcharge.model import FEATURE_LABELS  # noqa: E402

PROC = ROOT / "data" / "processed"
SEQ = [[0, "#cde2fb"], [0.25, "#86b6ef"], [0.5, "#3987e5"], [0.75, "#1c5cab"], [1, "#0d366b"]]
C_PICK, C_IONNA, C_OTHER, INK2 = "#eb6834", "#1baf7a", "#898781", "#52514e"

st.set_page_config(page_title="EV Charging Expansion Planner", layout="wide")


APP_FILES = ["app_counties.parquet", "stations_map.parquet", "counties.geojson", "model_metrics.json"]


def data_signature() -> str:
    """Content hash of the app's data files, so a redeploy with new data refreshes the cache."""
    import hashlib

    h = hashlib.sha256()
    for name in APP_FILES:
        h.update((PROC / name).read_bytes())
    return h.hexdigest()


@st.cache_data
def load(signature: str):  # signature is part of the cache key; see data_signature()
    df = pd.read_parquet(PROC / "app_counties.parquet")
    stations = pd.read_parquet(PROC / "stations_map.parquet")
    geo = json.loads((PROC / "counties.geojson").read_text())
    metrics = json.loads((PROC / "model_metrics.json").read_text())
    return df, stations, geo, metrics


df, stations, geo, metrics = load(data_signature())

# ---------------- Sidebar controls ----------------
sb = st.sidebar
sb.header("Budget and cost")
budget_m = sb.number_input("Capital budget ($ millions)", 1.0, 5000.0, 100.0, 5.0)
scenario = sb.selectbox("Build cost scenario", list(cost.SCENARIOS), index=1,
                        help="Low: median NEVI award per port. Base: NREL 350 kW per-port cost "
                             "plus transformer. High: Base x NEVI top-quartile ratio.")
ports = sb.slider("DC ports per site", 4, 16, cost.DEFAULT_PORTS,
                  help="IONNA's current sites average 8.5 ports.")
per_port_default = float(cost.SCENARIOS[scenario].per_port)
per_port = sb.number_input("Cost per port ($)", 50_000.0, 600_000.0, per_port_default,
                           1_000.0)
incentive = sb.slider("Grant share of capex (%)", 0, 80, 0,
                      help="Optional. NEVI covered up to 80% of eligible costs; program status "
                           "and eligibility vary by state. Leave at 0 unless a grant is secured.")
unit_cost = cost.site_cost(scenario, ports, per_port, 1.0, incentive / 100)
sb.caption(f"Net cost per site: **${unit_cost/1e6:,.2f}M**")

sb.header("What to optimize")
target = sb.radio("Score", ["Future Deployment", "Net Opportunity"],
                  help="Net Opportunity ignores existing chargers. Future Deployment discounts "
                       "counties already well supplied.")
sat_pen = sb.slider("Saturation penalty", 0.0, 1.0, 0.5, 0.05,
                    disabled=target == "Net Opportunity",
                    help="0 = ignore competition; 1 = a fully saturated county scores zero.")
with sb.expander("Scoring weights", expanded=False):
    weights = {k: st.slider(lbl, 0.0, 1.0, float(scoring.DEFAULT_WEIGHTS[k]), 0.05, key=k)
               for k, (_, _, lbl) in scoring.DEMAND_COMPONENTS.items()}
    st.caption("Weights are normalized to sum to 1. Each input is a percentile rank across "
               "counties.")

sb.header("Site rules")
max_sites = sb.slider("Max new sites per county", 1, 5, 2)
decay = sb.slider("Value of each extra site in a county", 0.1, 1.0, 0.5, 0.05,
                  help="0.5 = a second site is worth half the first. Existing IONNA sites count.")
states = sb.multiselect("Limit to states", sorted(df["state"].unique()))
min_pop = sb.number_input("Minimum county population", 0, 1_000_000, 0, 5_000)

# ---------------- Scoring and selection ----------------
if sum(weights.values()) == 0:
    st.error("Set at least one scoring weight above zero.")
    st.stop()
scored = scoring.score(df, weights, sat_pen if target == "Future Deployment" else 0.0)
col = "future_deployment" if target == "Future Deployment" else "net_opportunity"
scored["score"] = scored[col]
pool = scored[scored["pop"] >= min_pop]
if states:
    pool = pool[pool["state"].isin(states)]
cand = scoring.expand_candidates(pool, "score", unit_cost, max_sites, decay)
picks, method = optimize.select(cand, budget_m * 1e6)  # one cost per site: top-N is exact
picks = picks.merge(scored, on="fips", how="left")
picks["rank"] = np.arange(1, len(picks) + 1)

# ---------------- Header ----------------
st.title("EV Charging Expansion Planner")
st.caption("County-level screen for new DC fast-charging sites, built for an IONNA-style network. "
           "Scores rank counties; they are not revenue forecasts. See the Method tab.")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Sites selected", f"{len(picks)}")
k2.metric("Capital used", f"${picks['cost'].sum()/1e6:,.1f}M", f"of ${budget_m:,.0f}M",
          delta_color="off")
k3.metric("Counties", f"{picks['fips'].nunique()}")
k4.metric("States", f"{picks['state'].nunique()}")
if len(picks) == 0:
    st.warning("The budget is below the cost of one site, or no county meets the filters.")

tab_rec, tab_econ, tab_model, tab_explore, tab_method = st.tabs(
    ["Recommendations", "Site economics", "Model performance", "Explore counties", "Method and sources"])

# ---------------- Recommendations ----------------
with tab_rec:
    show_ionna = st.checkbox("Show existing IONNA sites", True)
    show_comp = st.checkbox("Show competitor sites with 4+ DC ports", False)
    fig = go.Figure(go.Choropleth(
        geojson=geo, locations=scored["fips"], z=scored["score"], featureidkey="id",
        colorscale=SEQ, marker_line_width=0, colorbar=dict(title=target.split()[0], len=0.6),
        customdata=np.c_[scored["county_key"], scored["net_opportunity"].round(1),
                         scored["future_deployment"].round(1), scored["dcfc_ports"],
                         scored["cluster"]],
        hovertemplate="<b>%{customdata[0]}</b><br>Net Opportunity %{customdata[1]}<br>"
                      "Future Deployment %{customdata[2]}<br>DC ports %{customdata[3]}<br>"
                      "%{customdata[4]}<extra></extra>"))
    if show_comp:
        comp = stations[~stations["is_ionna"]]
        fig.add_trace(go.Scattergeo(lat=comp["lat"], lon=comp["lon"], mode="markers",
                                    marker=dict(size=4, color=C_OTHER, opacity=0.6),
                                    name="Competitor 4+ port sites", text=comp["network"],
                                    hovertemplate="%{text}<extra></extra>"))
    if show_ionna:
        io_ = stations[stations["is_ionna"]]
        fig.add_trace(go.Scattergeo(lat=io_["lat"], lon=io_["lon"], mode="markers",
                                    marker=dict(size=7, color=C_IONNA, line=dict(width=1, color="white")),
                                    name="Existing IONNA sites", text=io_["name"],
                                    hovertemplate="%{text}<extra></extra>"))
    if len(picks):
        p1 = picks.drop_duplicates("fips")
        n_by = picks.groupby("fips").size()
        fig.add_trace(go.Scattergeo(
            lat=p1["cent_lat"], lon=p1["cent_lon"], mode="markers",
            marker=dict(size=8 + 4 * p1["fips"].map(n_by), color=C_PICK, symbol="diamond",
                        line=dict(width=1.5, color="white")),
            name="Recommended (county centroid)", text=p1["county_key"],
            customdata=p1["fips"].map(n_by),
            hovertemplate="<b>%{text}</b><br>New sites: %{customdata}<extra></extra>"))
    fig.update_geos(scope="usa", showlakes=False, bgcolor="rgba(0,0,0,0)")
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=0, b=0),
                      legend=dict(orientation="h", y=-0.02, x=0))
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Selection method: {method}. Markers sit at county centroids; site-level "
               "placement within a county is a next step (interchanges, retail hosts, grid capacity).")

    table = picks[["rank", "county_key", "state", "k", "score", "net_opportunity",
                   "future_deployment", "p_new_site", "p_first_site", "dcfc_ports",
                   "ionna_sites", "dist_large_dcfc_mi", "pop", "cost", "cluster"]].rename(columns={
        "county_key": "County", "state": "State", "k": "Site # in county", "score": "Score used",
        "net_opportunity": "Net Opportunity", "future_deployment": "Future Deployment",
        "p_new_site": "P(new large site)", "p_first_site": "P(first large site)",
        "dcfc_ports": "Existing DC ports", "ionna_sites": "Existing IONNA sites",
        "dist_large_dcfc_mi": "Miles to nearest 4+ port site", "pop": "Population",
        "cost": "Net capex ($)", "cluster": "County type"})
    st.dataframe(table, hide_index=True, width="stretch", column_config={
        "Score used": st.column_config.NumberColumn(format="%.1f"),
        "Net Opportunity": st.column_config.NumberColumn(format="%.1f"),
        "Future Deployment": st.column_config.NumberColumn(format="%.1f"),
        "P(new large site)": st.column_config.NumberColumn(format="%.2f"),
        "P(first large site)": st.column_config.NumberColumn(format="%.2f"),
        "Miles to nearest 4+ port site": st.column_config.NumberColumn(format="%.1f"),
        "Population": st.column_config.NumberColumn(format="%d"),
        "Net capex ($)": st.column_config.NumberColumn(format="$%d")})
    st.download_button("Download ranked list (CSV)", table.to_csv(index=False),
                       "recommended_sites.csv", "text/csv")

# ---------------- Economics ----------------
with tab_econ:
    st.subheader("Indicative site economics")
    st.caption("Energy revenue minus energy cost only. Excludes O&M, site lease, network fees, "
               "payment processing, taxes and any incentives beyond the grant share. Treat as a "
               "screen, not a pro forma.")
    c1, c2, c3 = st.columns(3)
    kwh = c1.slider("kWh per port per day", 50, 800, cost.NREL_KWH_PER_PORT_DAY_2025, 10,
                    help="NREL 2025 corridor average: 176 kWh/port/day (4% capacity factor).")
    use_state_price = c2.checkbox("Use state median posted DCFC price", True,
                                  help="Parsed from AFDC station pricing text; national median "
                                       "used where a state has fewer than 10 priced stations.")
    flat_price = c2.number_input("Flat price ($/kWh)", 0.20, 1.20,
                                 float(metrics.get("dcfc_price_national_median", 0.48)), 0.01,
                                 disabled=use_state_price)
    adder = c3.number_input("Demand-charge adder ($/kWh)", 0.0, 0.40,
                            round(cost.NREL_DEMAND_CHARGE_ADDER, 2), 0.01,
                            help="NREL: stations with demand charges averaged $0.12/kWh more.")
    if len(picks):
        price = picks["dcfc_price_kwh"] if use_state_price else flat_price
        econ = cost.annual_economics(ports, kwh, price, picks["elec_price_c_kwh"], adder)
        e = picks[["county_key", "state"]].copy()
        e["Price $/kWh"] = price
        e["Grid price c/kWh"] = picks["elec_price_c_kwh"]
        e["Annual kWh"] = econ["kwh"]
        e["Revenue $"] = econ["revenue"]
        e["Energy cost $"] = econ["energy_cost"]
        e["Gross margin $"] = econ["gross_margin"]
        e["Simple payback (yrs)"] = np.where(econ["gross_margin"] > 0,
                                             picks["cost"] / econ["gross_margin"], np.nan)
        m1, m2, m3 = st.columns(3)
        m1.metric("Portfolio revenue / yr", f"${e['Revenue $'].sum()/1e6:,.1f}M")
        m2.metric("Portfolio gross margin / yr", f"${e['Gross margin $'].sum()/1e6:,.1f}M")
        tot = e["Gross margin $"].sum()
        m3.metric("Portfolio simple payback", f"{picks['cost'].sum()/tot:,.1f} yrs" if tot > 0 else "n/a")
        st.dataframe(e.round(2), hide_index=True, width="stretch")
        st.info("Utilization is held equal across counties because no public county-level usage "
                "data exists. Higher-scoring counties would likely see higher use; the payback "
                "shown is therefore conservative for top picks and optimistic for weak ones.")

# ---------------- Model performance ----------------
with tab_model:
    st.subheader("Can the model tell where new large sites will open?")
    st.markdown(
        "Two logistic regression models (with Lasso and random forest challengers) were trained on "
        "county-year data for 2021-2023 and tested on 2024 features predicting 2025 openings. "
        "**Model A**: any new site with 4+ DC ports next year. **Model B**: a county's first such site.")
    rows = []
    for t in ["A", "B"]:
        r = metrics[t]
        for name, d in {**r["test"], **r["baselines"]}.items():
            rows.append({"Model": t, "Method": name.replace("_", " "), "ROC AUC": d["roc_auc"],
                         "PR AUC": d["pr_auc"], "Precision in top N (N = actual positives)":
                         d["precision_at_n_positives"], "Base rate": d["base_rate"]})
    st.dataframe(pd.DataFrame(rows).round(3), hide_index=True, width="stretch")
    lv = metrics["live_2026_partial"]
    st.markdown(f"**Out-of-time check on 2026 (Jan 1 to Sep 22):** Model A ROC AUC "
                f"{lv['roc_auc_A']:.3f}, Model B ROC AUC {lv['roc_auc_B']:.3f}.")
    st.markdown("**Reading this honestly:** population alone already ranks counties well, because "
                "chargers follow people. The models add a moderate, consistent lift over that "
                "baseline, larger for first-entry (Model B). Both learn where the market has "
                "built, not where sites are profitable.")
    ta = st.radio("Show drivers for", ["A", "B"], horizontal=True)
    coef = pd.DataFrame(metrics[ta]["logit_coefficients"]).T
    coef.index = [FEATURE_LABELS.get(i, i) for i in coef.index]
    coef = coef.sort_values("odds_ratio_per_sd")
    lo, hi = np.exp(coef["coef"] - 1.96 * coef["se"]), np.exp(coef["coef"] + 1.96 * coef["se"])
    sig = coef["p_value"] < 0.05
    fig = go.Figure(go.Scatter(
        x=coef["odds_ratio_per_sd"], y=coef.index, mode="markers",
        marker=dict(size=10, color=np.where(sig, "#2a78d6", "#b7d3f6"),
                    line=dict(width=1, color="#1c5cab")),
        error_x=dict(type="data", symmetric=False, array=hi - coef["odds_ratio_per_sd"],
                     arrayminus=coef["odds_ratio_per_sd"] - lo, color="#86b6ef", thickness=2),
        customdata=np.c_[lo, hi, coef["p_value"]],
        hovertemplate="%{y}<br>OR %{x:.2f} (95% CI %{customdata[0]:.2f}-%{customdata[1]:.2f})"
                      "<br>p = %{customdata[2]:.3f}<extra></extra>"))
    fig.add_vline(x=1, line_color=INK2, line_width=1)
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=40, b=0), xaxis_type="log",
                      xaxis_title="Odds ratio per 1 SD increase (log scale; 1 = no effect)",
                      title="What drives the prediction (solid = p < 0.05, bars = 95% CI)")
    st.plotly_chart(fig, width="stretch")

# ---------------- Explore ----------------
with tab_explore:
    st.subheader("County types (k-means on current conditions)")
    cats = sorted(scored["cluster"].unique())
    palette = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
    figc = go.Figure()
    for i, c in enumerate(cats):
        d = scored[scored["cluster"] == c]
        figc.add_trace(go.Choropleth(geojson=geo, locations=d["fips"], z=np.ones(len(d)), zmin=0, zmax=1,
                                     featureidkey="id", showscale=False, name=c, showlegend=True,
                                     colorscale=[[0, palette[i]], [1, palette[i]]],
                                     marker_line_width=0, text=d["county_key"],
                                     hovertemplate=f"%{{text}}<br>{c}<extra></extra>"))
    figc.update_geos(scope="usa")
    figc.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0),
                       legend=dict(orientation="h", y=-0.02))
    st.plotly_chart(figc, width="stretch")
    summary = scored.groupby("cluster").agg(
        counties=("fips", "size"), population_m=("pop", lambda s: s.sum() / 1e6),
        median_dc_ports=("dcfc_ports", "median"), median_miles_to_large=("dist_large_dcfc_mi", "median"),
        mean_net_opportunity=("net_opportunity", "mean")).round(1)
    st.dataframe(summary, width="stretch")
    st.subheader("Look up a county")
    pick = st.selectbox("County", scored.sort_values("county_key")["county_key"])
    row = scored[scored["county_key"] == pick].iloc[0]
    comp = pd.DataFrame({"Component": [lbl for _, (_, _, lbl) in scoring.DEMAND_COMPONENTS.items()],
                         "Percentile": [row[f"c_{k}"] for k in scoring.DEMAND_COMPONENTS]})
    st.dataframe(comp.round(2), hide_index=True)

# ---------------- Method ----------------
with tab_method:
    st.markdown((ROOT / "docs" / "METHODOLOGY.md").read_text())
