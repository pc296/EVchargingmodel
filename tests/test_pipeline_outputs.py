import json

import pandas as pd
import pytest

from evcharge import io

PANEL = io.PROCESSED / "panel.parquet"
pytestmark = pytest.mark.skipif(not PANEL.exists(), reason="run scripts/run_pipeline.py first")


def test_panel_shape_and_keys():
    p = pd.read_parquet(PANEL)
    assert len(p) == 3144 * 6
    assert not p.duplicated(["fips", "year"]).any()


def test_labels_defined_correctly():
    p = pd.read_parquet(PANEL)
    assert p.loc[p["year"] == 2025, "y_new_site"].isna().all()
    b = p.dropna(subset=["y_first_site"])
    assert (b["large_sites"] == 0).all()
    assert set(p["y_new_site"].dropna().unique()) <= {0.0, 1.0}


def test_supply_is_cumulative():
    p = pd.read_parquet(PANEL).sort_values(["fips", "year"])
    assert (p.groupby("fips")["dcfc_ports"].diff().dropna() >= 0).all()


def test_station_reconciliation():
    st = pd.read_parquet(io.PROCESSED / "stations.parquet")
    raw = io.load_stations()
    kept = raw[raw["status"].isin(["E", "T"]) & ~raw["non_public_flag"]]
    kept = kept[kept["state"].isin(io.STATE_ABBR.values())]  # 50 states + DC; PR out of scope
    assert len(st) == len(kept)  # no in-scope stations dropped by the spatial join


def test_app_table():
    a = pd.read_parquet(io.PROCESSED / "app_counties.parquet")
    assert len(a) == 3144
    assert a[["p_new_site", "p_first_site"]].stack().between(0, 1).all()
    m = json.loads((io.PROCESSED / "model_metrics.json").read_text())
    assert m["A"]["test"]["logit"]["roc_auc"] > m["A"]["baselines"]["rank_by_population"]["roc_auc"]


def test_labels_align_with_next_year():
    p = pd.read_parquet(PANEL).set_index(["fips", "year"]).sort_index()
    lab = p.loc[p["y_new_site"].notna()]
    nxt = p["new_large_sites_t"].reindex([(f, y + 1) for f, y in lab.index]).values
    assert ((nxt > 0).astype(float) == lab["y_new_site"].values).all()


def test_map_feature_ids_are_fips():
    geo = json.loads((io.PROCESSED / "counties.geojson").read_text())
    ids = {f["id"] for f in geo["features"]}
    a = pd.read_parquet(io.PROCESSED / "app_counties.parquet")
    assert len(ids & set(a["fips"])) >= 3143  # Falls Church may have no polygon after simplification
    assert all(f["geometry"] is not None for f in geo["features"])  # null geometry crashes Plotly
