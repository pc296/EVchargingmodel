"""Budget-constrained site selection (0-1 knapsack with within-county ordering)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


def select_greedy(cand: pd.DataFrame, budget: float) -> pd.DataFrame:
    """Pick by value per dollar until the budget is used (fast check on the MILP)."""
    c = cand.assign(ratio=cand["value"] / cand["cost"]).sort_values(["ratio", "k"],
                                                                    ascending=[False, True])
    picked, spent, taken = [], 0.0, {}
    for idx, r in c.iterrows():
        if r["k"] != taken.get(r["fips"], 0) + 1:
            continue
        if spent + r["cost"] <= budget:
            picked.append(idx)
            spent += r["cost"]
            taken[r["fips"]] = r["k"]
    return cand.loc[picked]


def select(cand: pd.DataFrame, budget: float, exact: bool = False) -> tuple[pd.DataFrame, str]:
    """Choose sites. With equal site costs, taking the highest values is exactly optimal;
    otherwise use greedy (fast) or MILP (exact, slower)."""
    if cand.empty:
        return cand, "none"
    if cand["cost"].nunique() == 1:
        n = int(budget // cand["cost"].iloc[0])
        return cand.sort_values(["value", "k"], ascending=[False, True]).head(n), "exact (equal costs)"
    if exact:
        return select_milp(cand, budget), "exact (MILP)"
    return select_greedy(cand, budget), "greedy (value per dollar)"


def select_milp(cand: pd.DataFrame, budget: float, time_limit: float = 10.0) -> pd.DataFrame:
    """Exact maximization of total value subject to total cost <= budget.
    Constraint x[county, k] <= x[county, k-1] keeps picks in order within a county."""
    n = len(cand)
    if n == 0 or budget < cand["cost"].min():
        return cand.iloc[0:0]
    cand = cand.reset_index(drop=True)
    pos = {(f, k): i for i, (f, k) in enumerate(zip(cand["fips"], cand["k"]))}
    order = [(i, pos[(f, k - 1)]) for (f, k), i in pos.items() if k > 1 and (f, k - 1) in pos]
    A = lil_matrix((1 + len(order), n))
    A[0, :] = cand["cost"].values
    for r, (i, j) in enumerate(order, start=1):
        A[r, i], A[r, j] = 1, -1
    lb = np.r_[-np.inf, np.full(len(order), -np.inf)]
    ub = np.r_[budget, np.zeros(len(order))]
    res = milp(c=-cand["value"].values, constraints=LinearConstraint(A.tocsr(), lb, ub),
               integrality=np.ones(n), bounds=Bounds(0, 1),
               options={"time_limit": time_limit, "mip_rel_gap": 1e-4})
    if res.x is None:
        return select_greedy(cand, budget)
    return cand[res.x > 0.5]
