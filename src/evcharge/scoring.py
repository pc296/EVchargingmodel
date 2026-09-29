"""Turn county features into the Net Opportunity and Future Deployment scores.

All components are percentile ranks (0-1) across counties so user weights are comparable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# component name -> (source column, direction: +1 higher is better, -1 lower is better, label)
DEMAND_COMPONENTS = {
    "ev_demand": ("bev_est", 1, "Estimated EVs in county"),
    "traffic": ("fwy_vmt", 1, "Freeway traffic (vehicle-miles)"),
    "growth": ("pop_growth", 1, "Population growth"),
    "market_momentum": ("p_new_site", 1, "Model A: chance of new large site"),
    "whitespace_entry": ("p_first_site", 1, "Model B: chance of first large site"),
    "policy": ("ev_incentives", 1, "State EV incentives"),
    "power_cost": ("elec_price_c_kwh", -1, "Electricity price (lower is better)"),
}
SATURATION_COMPONENTS = {
    "local_density": ("ports_per_1k_bev", 1, "DC ports per 1,000 EVs"),
    "nearby_ports": ("ports_within_50mi", 1, "DC ports within 50 miles"),
}
DEFAULT_WEIGHTS = {"ev_demand": 0.25, "traffic": 0.25, "growth": 0.05, "market_momentum": 0.20,
                   "whitespace_entry": 0.10, "policy": 0.05, "power_cost": 0.10}


def percentile(s: pd.Series, direction: int = 1) -> pd.Series:
    r = s.rank(pct=True, method="average")
    return r if direction > 0 else 1 - r + 1 / len(s)


def add_components(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for name, (col, d, _) in {**DEMAND_COMPONENTS, **SATURATION_COMPONENTS}.items():
        df[f"c_{name}"] = percentile(df[col].fillna(df[col].median()), d)
    df["saturation"] = df[[f"c_{k}" for k in SATURATION_COMPONENTS]].mean(axis=1)
    return df


def score(df: pd.DataFrame, weights: dict | None = None, saturation_penalty: float = 0.5) -> pd.DataFrame:
    """Net Opportunity = weighted mean of demand components (0-100).
    Future Deployment = Net Opportunity x (1 - penalty x saturation)."""
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    total = sum(max(v, 0) for v in w.values())
    if total <= 0:
        raise ValueError("at least one weight must be positive")
    out = df.copy()
    nos = sum(max(w[k], 0) * out[f"c_{k}"] for k in DEMAND_COMPONENTS) / total
    out["net_opportunity"] = 100 * nos
    out["future_deployment"] = out["net_opportunity"] * (1 - saturation_penalty * out["saturation"])
    return out


def expand_candidates(df: pd.DataFrame, value_col: str, site_cost: pd.Series | float,
                      max_sites: int = 3, decay: float = 0.5,
                      min_value: float = 0.0) -> pd.DataFrame:
    """One row per possible k-th new site in a county; value decays with each extra site,
    counting existing IONNA sites already in the county."""
    if not 0 < decay <= 1:
        raise ValueError("decay must be in (0, 1]")
    base = df[["fips", value_col, "ionna_sites"]].copy()
    base["cost"] = site_cost if np.isscalar(site_cost) else site_cost.values
    rows = []
    for k in range(1, max_sites + 1):
        r = base.copy()
        r["k"] = k
        r["value"] = r[value_col] * decay ** (r["ionna_sites"] + k - 1)
        rows.append(r)
    cand = pd.concat(rows, ignore_index=True)
    cand = cand[cand["value"] > min_value]
    return cand[["fips", "k", "value", "cost"]].reset_index(drop=True)
