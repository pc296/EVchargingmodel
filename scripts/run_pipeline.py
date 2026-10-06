"""Run the full offline pipeline: panel -> models -> scores inputs -> app tables and figures."""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evcharge import io, model, panel, scoring  # noqa: E402

warnings.filterwarnings("ignore")
OUT = io.PROCESSED
OUT.mkdir(parents=True, exist_ok=True)

CLUSTER_FEATURES = ["log_pop", "log_density", "log_fwy_vmt", "bev_per_1k",
                    "log_ports_per_1k_bev", "log_dist_large_dcfc", "pop_growth"]


def name_clusters(centers: pd.DataFrame) -> dict[int, str]:
    """Plain-language names from standardized cluster centers (rules checked in order)."""
    rules = [
        (lambda c: c["bev_per_1k"] > 1.5, "Counties in high-EV-adoption states"),
        (lambda c: c["log_pop"] > 1.0, "Metro and suburban"),
        (lambda c: c["log_dist_large_dcfc"] > 1.0, "Remote, charging desert"),
        (lambda c: c["log_ports_per_1k_bev"] > 0.8, "Highway corridor, well supplied"),
        (lambda c: c["log_ports_per_1k_bev"] < -0.5, "Small town, underserved"),
    ]
    names = {}
    for i, c in centers.iterrows():
        names[i] = next((n for rule, n in rules if rule(c)), "Mixed")
        if list(names.values()).count(names[i]) > 1:
            names[i] = f"{names[i]} ({i})"
    return names


def main() -> None:
    print("building panel")
    pan, cur, st = panel.build_panel()
    pan.to_parquet(OUT / "panel.parquet")
    st.to_parquet(OUT / "stations.parquet")
    pan_m = model.add_model_features(pan)
    pan_m.to_csv(OUT / "panel_model.csv", index=False)  # for R cross-check

    metrics = {}
    for t in ["A", "B"]:
        print("evaluating target", t)
        metrics[t] = model.run_target(pan, t)

    # Score the latest full feature year (2025) with models refit on all labeled years.
    feat25 = model.add_model_features(pan[pan["year"] == 2025])
    mA, mB = model.fit_final(pan, "A"), model.fit_final(pan, "B")
    feat25["p_new_site"] = mA.predict_proba(feat25[model.FEATURES])[:, 1]
    feat25["p_first_site"] = np.where(feat25["large_sites"] == 0,
                                      mB.predict_proba(feat25[model.FEATURES])[:, 1], 0.0)

    # Pseudo-live check: 2025 features vs large sites opened Jan 1 - Sep 22, 2026 (partial year).
    live = feat25[["fips", "p_new_site", "p_first_site", "large_sites"]].merge(
        cur[["fips", "new_large_sites_t"]], on="fips")
    y26 = (live["new_large_sites_t"] > 0).astype(int)
    metrics["live_2026_partial"] = {
        "note": "Model A (refit on 2022-2025 labels) scored on end-2025 features; outcome = any new "
                "large site opened 2026-01-01 to 2026-09-22.",
        "roc_auc_A": float(roc_auc_score(y26, live["p_new_site"])),
        "base_rate": float(y26.mean()),
    }
    b = live["large_sites"] == 0
    metrics["live_2026_partial"]["roc_auc_B"] = float(roc_auc_score(y26[b], live.loc[b, "p_first_site"]))

    # Clustering on current conditions (for visualization).
    cur_m = model.add_model_features(cur)
    X = StandardScaler().fit_transform(cur_m[CLUSTER_FEATURES].fillna(0))
    km = KMeans(n_clusters=5, n_init=20, random_state=model.SEED).fit(X)
    centers = pd.DataFrame(km.cluster_centers_, columns=CLUSTER_FEATURES)
    names = name_clusters(centers)
    cur_m["cluster"] = [names[i] for i in km.labels_]
    metrics["clusters"] = {names[i]: {**centers.loc[i].round(2).to_dict(),
                                      "n": int((km.labels_ == i).sum())} for i in names}

    # State DCFC price from AFDC pricing text (median of parsed $/kWh across DC fast stations).
    st["price_kwh"] = st["pricing"].map(io.parse_price_per_kwh)
    price = st.groupby("state")["price_kwh"].agg(["median", "count"]).rename(
        columns={"median": "dcfc_price_kwh", "count": "price_obs"})
    national = float(st["price_kwh"].median())
    metrics["dcfc_price_national_median"] = national
    metrics["dcfc_price_obs"] = int(st["price_kwh"].notna().sum())

    app = cur_m.drop(columns=["p_new_site", "p_first_site"], errors="ignore").merge(
        feat25[["fips", "p_new_site", "p_first_site"]], on="fips")
    app = app.merge(price, left_on="state", right_index=True, how="left")
    thin = app["price_obs"].fillna(0) < 10
    app.loc[thin, "dcfc_price_kwh"] = national
    app["price_imputed"] = thin
    app = scoring.add_components(app)
    keep = (["fips", "county_key", "county_name", "state", "cent_lat", "cent_lon", "pop",
             "pop_growth", "bev_est", "bev_per_1k", "fwy_vmt", "has_freeway", "traffic_imputed",
             "elec_price_c_kwh", "ev_incentives", "dcfc_ports", "dcfc_sites", "large_sites",
             "tesla_ports", "ionna_ports", "ionna_sites", "ports_per_1k_bev", "ports_within_50mi",
             "dist_large_dcfc_mi", "p_new_site", "p_first_site", "cluster", "dcfc_price_kwh",
             "price_imputed", "saturation"] + [c for c in app.columns if c.startswith("c_")])
    app[keep].to_parquet(OUT / "app_counties.parquet", index=False)

    st_map = st[st["is_large"] | st["is_ionna"]][["name", "lat", "lon", "dc_ports", "network",
                                                   "is_ionna", "is_tesla", "open_year", "fips"]]
    st_map.to_parquet(OUT / "stations_map.parquet", index=False)

    counties = gpd.read_file(io.EXTERNAL / "us_atlas_2023_counties-10m.json", layer="counties")
    # Feature id must be the FIPS code: the app matches counties on featureidkey="id".
    counties = counties[counties["id"].isin(app["fips"])][["id", "geometry"]].set_index("id")
    counties["geometry"] = counties.geometry.simplify(0.01, preserve_topology=True)
    # Empty shapes (Falls Church city, VA, lost to simplification) serialize as null geometry,
    # which crashes Plotly's choropleth once features match; drop them.
    counties = counties[~counties.geometry.is_empty & counties.geometry.notna()]
    (OUT / "counties.geojson").write_text(counties.to_json(drop_id=False))

    (OUT / "model_metrics.json").write_text(json.dumps(metrics, indent=1, default=float))
    print(json.dumps(metrics["live_2026_partial"], indent=1))
    print("done:", len(app), "counties")


if __name__ == "__main__":
    main()
