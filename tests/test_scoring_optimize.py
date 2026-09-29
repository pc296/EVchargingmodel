import numpy as np
import pandas as pd
import pytest

from evcharge import cost, optimize, scoring


def _frame(n=6):
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"fips": [f"{i:05d}" for i in range(n)], "ionna_sites": 0.0})
    for _, (col, _, _) in {**scoring.DEMAND_COMPONENTS, **scoring.SATURATION_COMPONENTS}.items():
        df[col] = rng.random(n)
    return scoring.add_components(df)


def test_percentile_direction():
    s = pd.Series([1.0, 2.0, 3.0])
    assert list(scoring.percentile(s, 1)) == pytest.approx([1 / 3, 2 / 3, 1])
    assert scoring.percentile(s, -1).iloc[0] > scoring.percentile(s, -1).iloc[2]


def test_scores_bounded_and_penalty():
    df = scoring.score(_frame(), saturation_penalty=0.0)
    assert df["net_opportunity"].between(0, 100).all()
    assert np.allclose(df["future_deployment"], df["net_opportunity"])
    df2 = scoring.score(_frame(), saturation_penalty=1.0)
    assert (df2["future_deployment"] <= df2["net_opportunity"] + 1e-9).all()


def test_zero_weights_raise():
    with pytest.raises(ValueError):
        scoring.score(_frame(), {k: 0 for k in scoring.DEFAULT_WEIGHTS})


def test_candidates_decay_and_existing_sites():
    df = pd.DataFrame({"fips": ["a", "b"], "v": [10.0, 10.0], "ionna_sites": [0, 1]})
    c = scoring.expand_candidates(df, "v", 1.0, max_sites=2, decay=0.5)
    va = c[c.fips == "a"].sort_values("k")["value"].tolist()
    vb = c[c.fips == "b"].sort_values("k")["value"].tolist()
    assert va == [10.0, 5.0] and vb == [5.0, 2.5]


def test_equal_cost_selection_is_top_n():
    df = pd.DataFrame({"fips": list("abc"), "v": [3.0, 2.0, 1.0], "ionna_sites": 0})
    c = scoring.expand_candidates(df, "v", 10.0, max_sites=2, decay=0.5)
    picks, method = optimize.select(c, 25.0)
    assert method.startswith("exact") and len(picks) == 2
    assert set(zip(picks.fips, picks.k, strict=True)) == {("a", 1), ("b", 1)}


def test_milp_respects_budget_and_order():
    c = pd.DataFrame({"fips": ["a", "a", "b", "c"], "k": [1, 2, 1, 1],
                      "value": [5.0, 4.0, 3.0, 2.9], "cost": [5.0, 5.0, 3.0, 2.0]})
    picks = optimize.select_milp(c, 10.0)
    assert picks["cost"].sum() <= 10.0
    assert picks["value"].sum() == pytest.approx(10.9)  # a1 + b1 + c1 beats a1 + a2
    g = optimize.select_greedy(c, 10.0)
    assert g["cost"].sum() <= 10.0


def test_budget_below_one_site():
    c = pd.DataFrame({"fips": ["a"], "k": [1], "value": [1.0], "cost": [5.0]})
    assert optimize.select(c, 4.0)[0].empty
    assert optimize.select_milp(c, 4.0).empty


def test_site_cost_scenarios():
    assert cost.site_cost("Base") == pytest.approx(8 * 232_700 + 100_000)
    assert cost.site_cost("Low") == pytest.approx(8 * 183_116)
    assert cost.site_cost("Low") < cost.site_cost("Base") < cost.site_cost("High")
    assert cost.site_cost("Base", incentive_share=0.5) == pytest.approx(cost.site_cost("Base") / 2)
    with pytest.raises(ValueError):
        cost.site_cost("Base", ports=0)


def test_annual_economics():
    e = cost.annual_economics(8, 100, 0.5, 10.0, demand_adder=0.1)
    assert e["kwh"] == 8 * 100 * 365
    assert e["gross_margin"] == pytest.approx(e["kwh"] * (0.5 - 0.2))
