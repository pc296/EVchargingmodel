import numpy as np
import pandas as pd

from evcharge import geo, io


def test_parse_price():
    assert io.parse_price_per_kwh("$0.48 per kWh") == 0.48
    assert io.parse_price_per_kwh("$0.50/kWh + $1 connection") == 0.50
    assert np.isnan(io.parse_price_per_kwh("$4 per hour"))
    assert np.isnan(io.parse_price_per_kwh(None))


def test_county_keys_crosswalk():
    k = io.load_county_keys()
    assert len(k) == 3144 and k["fips"].is_unique
    assert {"02063", "02066", "02158", "46102"} <= set(k["fips"])
    assert not {"02261", "02270", "46113", "51515"} & set(k["fips"])


def test_traffic_structural_zeros():
    t = io.load_traffic()
    assert len(t) == 3144 and t["fips"].is_unique
    assert (t.loc[~t["has_freeway"], "fwy_vmt"] == 0).all()
    assert t["fwy_vmt"].notna().all()


def test_nearest_distance_known_points():
    # Durham, NC to Raleigh, NC is about 21-23 miles.
    d = geo.nearest_distance_mi([35.994], [-78.899], [35.780], [-78.639])
    assert 20 < d[0] < 24


def test_assign_county_known_point():
    counties = geo.load_counties({"37063", "37183"})
    st = pd.DataFrame({"lat": [35.994], "lon": [-78.899]})
    out = geo.assign_county(st, counties)
    assert out["fips"].iloc[0] == "37063"  # Durham County
