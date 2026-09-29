"""Spatial helpers: county polygons, centroids, station-to-county join, distances."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from .io import EXTERNAL

EARTH_RADIUS_MI = 3958.8
EMPTY_GEOMETRY_FALLBACK = {"51610": (38.8847, -77.1751, 2.0)}


def load_counties(valid_fips: set[str] | None = None) -> gpd.GeoDataFrame:
    """2023 Census cartographic county polygons (EPSG:4326) with centroid and land area."""
    g = gpd.read_file(EXTERNAL / "us_atlas_2023_counties-10m.json", layer="counties")
    g = g.rename(columns={"id": "fips"}).set_crs(4326, allow_override=True)
    if valid_fips is not None:
        g = g[g["fips"].isin(valid_fips)].copy()
    albers = g.to_crs(5070)
    g["area_sqmi"] = albers.area / 2.59e6
    cent = albers.centroid.to_crs(4326)
    g["cent_lat"], g["cent_lon"] = cent.y.values, cent.x.values
    # Polygons lost to 10m simplification (Falls Church city, VA): use published centroid and
    # Census land area; stations there fall into neighboring counties (documented limitation).
    for fips, (lat, lon, sqmi) in EMPTY_GEOMETRY_FALLBACK.items():
        m = (g["fips"] == fips) & g.geometry.is_empty
        g.loc[m, ["cent_lat", "cent_lon", "area_sqmi"]] = [lat, lon, sqmi]
    return g


def assign_county(stations: pd.DataFrame, counties: gpd.GeoDataFrame,
                  snap_km: float = 5.0) -> pd.DataFrame:
    """Point-in-polygon join; points outside all polygons snap to nearest county within snap_km."""
    pts = gpd.GeoDataFrame(stations.copy(),
                           geometry=gpd.points_from_xy(stations["lon"], stations["lat"]), crs=4326)
    joined = gpd.sjoin(pts, counties[["fips", "geometry"]], predicate="within", how="left")
    joined = joined[~joined.index.duplicated(keep="first")]
    miss = joined["fips"].isna()
    if miss.any():
        near = gpd.sjoin_nearest(pts.loc[miss].to_crs(5070),
                                 counties[["fips", "geometry"]].to_crs(5070),
                                 how="left", max_distance=snap_km * 1000)
        near = near[~near.index.duplicated(keep="first")]
        joined.loc[miss, "fips"] = near["fips"]
    joined["county_assign"] = np.where(miss, np.where(joined["fips"].isna(), "dropped", "snapped"),
                                       "within")
    return pd.DataFrame(joined.drop(columns=["geometry", "index_right"], errors="ignore"))


def nearest_distance_mi(src_lat, src_lon, tgt_lat, tgt_lon) -> np.ndarray:
    """Great-circle distance (miles) from each source point to its nearest target point."""
    src = np.radians(np.column_stack([src_lat, src_lon]))
    if len(tgt_lat) == 0:
        return np.full(len(src), np.nan)
    tree = BallTree(np.radians(np.column_stack([tgt_lat, tgt_lon])), metric="haversine")
    dist, _ = tree.query(src, k=1)
    return dist[:, 0] * EARTH_RADIUS_MI


def count_within_mi(src_lat, src_lon, tgt_lat, tgt_lon, weights, radius_mi: float) -> np.ndarray:
    """Sum of target weights within radius_mi of each source point."""
    if len(tgt_lat) == 0:
        return np.zeros(len(src_lat))
    src = np.radians(np.column_stack([src_lat, src_lon]))
    tree = BallTree(np.radians(np.column_stack([tgt_lat, tgt_lon])), metric="haversine")
    idx = tree.query_radius(src, r=radius_mi / EARTH_RADIUS_MI)
    w = np.asarray(weights, dtype=float)
    return np.array([w[i].sum() for i in idx])
