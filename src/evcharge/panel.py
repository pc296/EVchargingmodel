"""Build the county x year panel (features at end of year t, labels in t+1)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import geo, io

YEARS = list(range(2020, 2026))  # feature years; labels observed in t+1 <= 2025 for t <= 2024
SNAPSHOT_YEAR = 2026  # AFDC snapshot 2026-09-22: current supply, partial year


def prepare_stations(counties) -> pd.DataFrame:
    st = io.load_stations()
    st = st[st["status"].isin(["E", "T"]) & ~st["non_public_flag"]].copy()
    # Missing open dates (n is small) are treated as opened before the panel starts.
    st["open_year_filled"] = st["open_year"].fillna(2010).astype(int)
    st["open_year_imputed"] = st["open_year"].isna()
    st = geo.assign_county(st, counties)
    return st[st["county_assign"] != "dropped"]


def supply_features(fips_frame: pd.DataFrame, st: pd.DataFrame, t: int) -> pd.DataFrame:
    """Charging supply at end of year t for each county."""
    s = st[st["open_year_filled"] <= t]
    large = s[s["is_large"]]
    g = s.groupby("fips")
    out = pd.DataFrame(index=fips_frame["fips"])
    out["dcfc_ports"] = g["dc_ports"].sum()
    out["dcfc_sites"] = g.size()
    out["large_sites"] = large.groupby("fips").size()
    out["tesla_ports"] = s[s["is_tesla"]].groupby("fips")["dc_ports"].sum()
    out["ionna_ports"] = s[s["is_ionna"]].groupby("fips")["dc_ports"].sum()
    out["ionna_sites"] = s[s["is_ionna"]].groupby("fips").size()
    out["new_large_sites_t"] = large[large["open_year_filled"] == t].groupby("fips").size()
    out = out.fillna(0).reset_index()
    lat, lon = fips_frame["cent_lat"].values, fips_frame["cent_lon"].values
    out["dist_large_dcfc_mi"] = geo.nearest_distance_mi(lat, lon, large["lat"].values,
                                                        large["lon"].values)
    out["ports_within_50mi"] = geo.count_within_mi(lat, lon, s["lat"].values, s["lon"].values,
                                                   s["dc_ports"].values, 50)
    return out


def build_panel() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (panel, current_supply, stations_with_fips)."""
    keys = io.load_county_keys()
    counties = geo.load_counties(set(keys["fips"]))
    missing = set(keys["fips"]) - set(counties["fips"])
    if missing:
        raise ValueError(f"county polygons missing for {sorted(missing)[:10]}")
    base = keys.merge(counties[["fips", "cent_lat", "cent_lon", "area_sqmi"]], on="fips")
    st = prepare_stations(counties)

    pop = io.load_population()
    traffic = io.load_traffic()
    regs = io.load_ev_registrations()
    elec = io.load_electricity()
    inc = io.load_incentives()

    state_pop25 = pop[pop["year"] == 2025].merge(keys[["fips", "state"]]).groupby("state")["pop"].sum()
    regs["bev_per_1k"] = regs["bev_regs"] / regs["state"].map(state_pop25) * 1000

    rows = []
    for t in YEARS + [SNAPSHOT_YEAR]:
        sup = supply_features(base, st, t)
        df = base.merge(sup, on="fips")
        df["year"] = t
        rows.append(df)
    panel = pd.concat(rows, ignore_index=True)

    pop_w = pop.pivot(index="fips", columns="year", values="pop")
    pop_w[SNAPSHOT_YEAR] = pop_w[2025]
    pop_prev = pop_w.shift(axis=1)
    panel["pop"] = [pop_w.at[f, y] for f, y in zip(panel["fips"], panel["year"])]
    panel["pop_growth"] = [
        (pop_w.at[f, y] / pop_prev.at[f, y] - 1) if y > 2020 else np.nan
        for f, y in zip(panel["fips"], panel["year"])
    ]
    panel.loc[panel["year"] == SNAPSHOT_YEAR, "pop_growth"] = panel.loc[
        panel["year"] == 2025, "pop_growth"].values

    panel = panel.merge(traffic, on="fips", how="left")
    panel = panel.merge(regs[["state", "bev_per_1k"]], on="state", how="left")
    panel = panel.merge(elec, on="state", how="left")

    inc_counts = {
        (s, t): int(((inc["state"] == s) & ((inc["enacted_year"] <= t) | inc["enacted_year"].isna())).sum())
        for s in keys["state"].unique() for t in YEARS + [SNAPSHOT_YEAR]
    }
    panel["ev_incentives"] = [inc_counts[(s, t)] for s, t in zip(panel["state"], panel["year"])]

    panel["bev_est"] = panel["bev_per_1k"] * panel["pop"] / 1000
    panel["pop_density"] = panel["pop"] / panel["area_sqmi"]
    panel["ports_per_1k_bev"] = panel["dcfc_ports"] / panel["bev_est"].clip(lower=1) * 1000
    panel["tesla_share"] = np.where(panel["dcfc_ports"] > 0,
                                    panel["tesla_ports"] / panel["dcfc_ports"].clip(lower=1), 0)
    state_new = panel.groupby(["state", "year"]).agg(sn=("new_large_sites_t", "sum"),
                                                      sp=("pop", "sum")).reset_index()
    state_new["state_new_large_per_1m"] = state_new["sn"] / state_new["sp"] * 1e6
    panel = panel.merge(state_new[["state", "year", "state_new_large_per_1m"]],
                        on=["state", "year"], how="left")

    # Labels: event in t+1 (A); first entry (B) defined only where large_sites == 0 at t.
    nxt = panel[["fips", "year", "new_large_sites_t"]].copy()
    nxt["year"] -= 1
    panel = panel.merge(nxt.rename(columns={"new_large_sites_t": "new_large_next"}),
                        on=["fips", "year"], how="left")
    panel.loc[panel["year"] >= 2025, "new_large_next"] = np.nan
    panel["y_new_site"] = (panel["new_large_next"] > 0).astype(float)
    panel.loc[panel["new_large_next"].isna(), "y_new_site"] = np.nan
    panel["y_first_site"] = np.where(panel["large_sites"] == 0, panel["y_new_site"], np.nan)

    current = panel[panel["year"] == SNAPSHOT_YEAR].copy()
    panel = panel[panel["year"] < SNAPSHOT_YEAR].copy()
    return panel, current, st
