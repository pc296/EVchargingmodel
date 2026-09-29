"""Loaders for each raw input. One function per source; each returns a tidy DataFrame."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
EXTERNAL = ROOT / "data" / "external"
PROCESSED = ROOT / "data" / "processed"

STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


def _require(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name}: missing columns {missing}")


def load_county_keys() -> pd.DataFrame:
    """County name -> FIPS crosswalk (3,144 counties, Vintage 2025 geography incl. CT regions)."""
    df = pd.read_csv(RAW / "afdc_ionna_dcfc_by_county_prior.csv")
    _require(df, ["County, State Key", "County FIPS", "State"], "county keys")
    out = pd.DataFrame(
        {
            "county_key": df["County, State Key"].str.strip(),
            "fips": df["County FIPS"].astype(int).astype(str).str.zfill(5),
            "state": df["State"],
            "county_name": df["County"],
        }
    )
    out = _apply_fips_crosswalk(out)
    if out["fips"].duplicated().any() or len(out) != 3144:
        raise ValueError("county keys: duplicate FIPS or unexpected count")
    return out


# Legacy FIPS in the prior county file -> Vintage 2025 geography.
FIPS_RENAME = {
    "02270": ("02158", "Kusilvak Census Area, Alaska", "Kusilvak"),
    "46113": ("46102", "Oglala Lakota County, South Dakota", "Oglala Lakota"),
}
FIPS_SPLIT = {"02261": [("02063", "Chugach Census Area, Alaska", "Chugach"),
                        ("02066", "Copper River Census Area, Alaska", "Copper River")]}
FIPS_DROP = {"51515"}  # Bedford City, VA, absorbed into Bedford County in 2013


def _apply_fips_crosswalk(df: pd.DataFrame) -> pd.DataFrame:
    df = df[~df["fips"].isin(FIPS_DROP)].copy()
    for old, (new, key, name) in FIPS_RENAME.items():
        m = df["fips"] == old
        df.loc[m, ["fips", "county_key", "county_name"]] = [new, key, name]
    for old, parts in FIPS_SPLIT.items():
        row = df[df["fips"] == old]
        df = df[df["fips"] != old]
        for new, key, name in parts:
            r = row.copy()
            r[["fips", "county_key", "county_name"]] = [new, key, name]
            df = pd.concat([df, r])
    return df.sort_values("fips").reset_index(drop=True)


def _norm_name(s: pd.Series) -> pd.Series:
    """Case- and spacing-insensitive county key (e.g. 'LaSalle' == 'La Salle')."""
    s = s.str.lower().str.replace(" ", "", regex=False)
    return s.str.replace("petersburgborough,alaska", "petersburgcensusarea,alaska", regex=False)


def load_population() -> pd.DataFrame:
    """Census Vintage 2025 county population estimates, long format (fips, year, pop)."""
    raw = pd.read_excel(RAW / "census_pop_2020_2025.xlsx", header=None)
    body = raw.iloc[4:, [0, 2, 3, 4, 5, 6, 7]]
    body = body[body[0].astype(str).str.startswith(".")]
    body.columns = ["name", 2020, 2021, 2022, 2023, 2024, 2025]
    body["norm"] = _norm_name(body["name"].str.lstrip("."))
    keys = load_county_keys().assign(norm=lambda d: _norm_name(d["county_key"]))
    merged = body.merge(keys[["norm", "county_key", "fips"]], on="norm", how="left")
    unmatched = merged[merged["fips"].isna()]["county_key"].tolist()
    if unmatched:
        raise ValueError(f"population: {len(unmatched)} unmatched counties, e.g. {unmatched[:5]}")
    long = merged.melt(id_vars="fips", value_vars=[2020, 2021, 2022, 2023, 2024, 2025],
                       var_name="year", value_name="pop")
    long["year"] = long["year"].astype(int)
    long["pop"] = long["pop"].astype(float)
    return long


def load_stations() -> pd.DataFrame:
    """AFDC public electric stations with DC fast ports, snapshot 2026-09-22."""
    df = pd.read_csv(RAW / "afdc_stations_2026-09-22.csv", low_memory=False)
    _require(df, ["ID", "EV DC Fast Count", "Latitude", "Longitude", "Open Date", "EV Network",
                  "Status Code", "State", "Station Name"], "stations")
    df = df[df["EV DC Fast Count"].fillna(0) > 0].copy()
    out = pd.DataFrame(
        {
            "station_id": df["ID"].astype(int),
            "name": df["Station Name"],
            "state": df["State"],
            "lat": df["Latitude"].astype(float),
            "lon": df["Longitude"].astype(float),
            "dc_ports": df["EV DC Fast Count"].astype(int),
            "network": df["EV Network"].fillna("Unknown"),
            "status": df["Status Code"],
            "open_date": pd.to_datetime(df["Open Date"], errors="coerce"),
            "pricing": df["EV Pricing"],
            "funding": df["Funding Sources"],
        }
    )
    out["open_year"] = out["open_date"].dt.year
    out["is_ionna"] = out["network"].str.upper().eq("IONNA")
    out["is_tesla"] = out["network"].str.contains("Tesla", case=False)
    out["is_large"] = out["dc_ports"] >= 4
    out["non_public_flag"] = out["name"].str.contains("NOT A PUBLIC", case=False, na=False)
    return out


def parse_price_per_kwh(text: object) -> float:
    """Extract a $/kWh price from AFDC free-text pricing; NaN if absent."""
    if not isinstance(text, str):
        return np.nan
    m = re.search(r"\$\s*(\d+(?:\.\d+)?)\s*(?:/|per)\s*kwh", text, flags=re.I)
    if not m:
        return np.nan
    val = float(m.group(1))
    return val if 0.05 <= val <= 1.5 else np.nan


def load_traffic() -> pd.DataFrame:
    """HPMS 2024 freeway traffic by county. Counties without F_SYSTEM 1-2 roads are true zeros."""
    df = pd.read_csv(RAW / "hpms_2024_road_utilization.csv")
    _require(df, ["County FIPS", "HPMS Geography Status", "Highway Daily Vehicle-Miles",
                  "HPMS Highway Section Miles (F_SYSTEM 1-2)", "Interstate Section Miles"], "traffic")
    status = df["HPMS Geography Status"].astype(str)
    out = pd.DataFrame(
        {
            "fips": df["County FIPS"].astype(int).astype(str).str.zfill(5),
            "fwy_vmt": df["Highway Daily Vehicle-Miles"].astype(float),
            "fwy_miles": df["HPMS Highway Section Miles (F_SYSTEM 1-2)"].astype(float),
            "interstate_miles": df["Interstate Section Miles"].astype(float),
        }
    )
    zero = status.str.startswith("No qualifying")
    out.loc[zero, ["fwy_vmt", "fwy_miles", "interstate_miles"]] = 0.0
    out["traffic_imputed"] = False
    # Connecticut: HPMS 2024 still reports legacy counties. Use the statewide total allocated to
    # planning regions by population share (from the team's imputed file); flagged as imputed.
    imp = pd.read_csv(RAW / "hpms_2024_road_utilization_imputed.csv")
    imp["fips"] = imp["County FIPS"].astype(int).astype(str).str.zfill(5)
    ct = imp[imp["fips"].str.startswith("09")].set_index("fips")
    m = out["fips"].isin(ct.index)
    out.loc[m, "fwy_vmt"] = out.loc[m, "fips"].map(ct["Final Highway Daily Vehicle-Miles"])
    out.loc[m, "fwy_miles"] = out.loc[m, "fips"].map(ct["Final Highway Section Miles"])
    out.loc[m, "interstate_miles"] = out.loc[m, "fwy_miles"]
    out.loc[m, "traffic_imputed"] = True
    for old, (new, _, _) in FIPS_RENAME.items():
        out.loc[out["fips"] == old, "fips"] = new
    for old, parts in FIPS_SPLIT.items():
        # Former Valdez-Cordova: no HPMS F_SYSTEM 1-2 match; set to 0 and flag.
        out = out[out["fips"] != old]
        extra = pd.DataFrame({"fips": [p[0] for p in parts], "fwy_vmt": 0.0, "fwy_miles": 0.0,
                              "interstate_miles": 0.0, "traffic_imputed": True})
        out = pd.concat([out, extra], ignore_index=True)
    out = out[~out["fips"].isin(FIPS_DROP)]
    out["has_freeway"] = out["fwy_miles"] > 0
    return out.reset_index(drop=True)


def load_ev_registrations() -> pd.DataFrame:
    """AFDC light-duty registrations by state (single vintage; see DATA_SOURCES.md)."""
    df = pd.read_csv(RAW / "afdc_registrations_by_state.csv")
    _require(df, ["State", "Electric (EV)", "Plug-In Hybrid Electric (PHEV)", "Gasoline"], "regs")
    df = df[df["State"].isin(STATE_ABBR)]
    return pd.DataFrame(
        {
            "state": df["State"].map(STATE_ABBR),
            "bev_regs": df["Electric (EV)"].astype(float),
            "phev_regs": df["Plug-In Hybrid Electric (PHEV)"].astype(float),
        }
    )


def load_electricity() -> pd.DataFrame:
    """EIA 2024 state average retail price, all sectors (cents/kWh)."""
    df = pd.read_csv(RAW / "eia_state_profile_2024.csv")
    _require(df, ["Name", "Average retail price (cents/kWh)"], "electricity")
    df = df[df["Name"].isin(STATE_ABBR)]
    return pd.DataFrame(
        {"state": df["Name"].map(STATE_ABBR),
         "elec_price_c_kwh": df["Average retail price (cents/kWh)"].astype(float)}
    )


def load_incentives() -> pd.DataFrame:
    """State EV incentive records (ELEC technology, incentive types) with enacted year."""
    from numbers_parser import Document

    table = Document(str(RAW / "afdc_laws_incentives.numbers")).sheets[0].tables[0]
    rows = table.rows(values_only=True)
    df = pd.DataFrame(rows[1:], columns=rows[0])
    _require(df, ["State", "Type", "Technology Categories", "Enacted Date", "Status"], "laws")
    ev = df[
        df["Technology Categories"].str.contains("ELEC", na=False)
        & df["Type"].isin(["State Incentives", "Incentives"])
        & (df["State"] != "US")
        & ~df["Status"].isin(["archived", "expired"])
    ].copy()
    ev["enacted_year"] = pd.to_datetime(ev["Enacted Date"].astype(str).str[:10], errors="coerce").dt.year
    return ev[["State", "enacted_year"]].rename(columns={"State": "state"})
