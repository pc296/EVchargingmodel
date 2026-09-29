"""Train and evaluate classifiers for targets A (new large site) and B (first large site)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, LogisticRegressionCV
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TARGETS = {"A": "y_new_site", "B": "y_first_site"}
TRAIN_YEARS = [2021, 2022, 2023]  # labels observed 2022-2024
TEST_YEAR = 2024  # label observed 2025
FINAL_YEARS = [2021, 2022, 2023, 2024]
SEED = 42

FEATURES = [
    "log_pop", "pop_growth", "log_density", "bev_per_1k", "elec_price_c_kwh", "ev_incentives",
    "log_fwy_vmt", "has_freeway", "log_interstate_miles", "log_dcfc_ports", "log_large_sites",
    "log_ports_per_1k_bev", "tesla_share", "log_dist_large_dcfc", "log_ports_50mi",
    "log_new_large_t", "state_new_large_per_1m",
]
FEATURE_LABELS = {
    "log_pop": "Population (log)", "pop_growth": "Population growth (1 yr)",
    "log_density": "Population density (log)", "bev_per_1k": "State BEVs per 1,000 residents",
    "elec_price_c_kwh": "Electricity price (c/kWh)", "ev_incentives": "State EV incentives (count)",
    "log_fwy_vmt": "Freeway vehicle-miles (log)", "has_freeway": "Has interstate/freeway",
    "log_interstate_miles": "Interstate miles (log)", "log_dcfc_ports": "DC fast ports (log)",
    "log_large_sites": "Large DCFC sites (log)", "log_ports_per_1k_bev": "DC ports per 1k BEVs (log)",
    "tesla_share": "Tesla share of DC ports", "log_dist_large_dcfc": "Miles to nearest large site (log)",
    "log_ports_50mi": "DC ports within 50 mi (log)", "log_new_large_t": "New large sites this year (log)",
    "state_new_large_per_1m": "State new large sites per 1M pop",
}


def add_model_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["log_pop"] = np.log(df["pop"])
    df["log_density"] = np.log(df["pop_density"].clip(lower=0.1))
    df["log_fwy_vmt"] = np.log1p(df["fwy_vmt"])
    df["has_freeway"] = df["has_freeway"].astype(float)
    df["log_interstate_miles"] = np.log1p(df["interstate_miles"])
    df["log_dcfc_ports"] = np.log1p(df["dcfc_ports"])
    df["log_large_sites"] = np.log1p(df["large_sites"])
    df["log_ports_per_1k_bev"] = np.log1p(df["ports_per_1k_bev"])
    df["log_dist_large_dcfc"] = np.log1p(df["dist_large_dcfc_mi"])
    df["log_ports_50mi"] = np.log1p(df["ports_within_50mi"])
    df["log_new_large_t"] = np.log1p(df["new_large_sites_t"])
    return df


def _models() -> dict:
    return {
        "logit": make_pipeline(StandardScaler(), LogisticRegression(C=1e6, max_iter=5000)),
        "lasso": make_pipeline(StandardScaler(), LogisticRegressionCV(
            Cs=20, penalty="l1", solver="saga", scoring="roc_auc", max_iter=5000, cv=5,
            random_state=SEED)),
        "forest": RandomForestClassifier(n_estimators=400, min_samples_leaf=20, max_features=0.5,
                                         n_jobs=-1, random_state=SEED),
    }


def precision_at_k(y: np.ndarray, p: np.ndarray, k: int) -> float:
    idx = np.argsort(-p)[:k]
    return float(np.mean(y[idx]))


def evaluate(y: np.ndarray, p: np.ndarray, k: int = 100) -> dict:
    n_pos = int(np.sum(y))
    return {
        "precision_at_n_positives": precision_at_k(y, p, n_pos),
        "precision_ranks_101_500": float(np.mean(y[np.argsort(-p)[100:500]])),
        "roc_auc": float(roc_auc_score(y, p)), "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)), f"precision_at_{k}": precision_at_k(y, p, k),
        "base_rate": float(np.mean(y)), "n": int(len(y)), "positives": int(np.sum(y)),
    }


def run_target(panel: pd.DataFrame, target: str) -> dict:
    """Temporal train/test, baselines, state-grouped CV, coefficients and importances."""
    ycol = TARGETS[target]
    df = add_model_features(panel).dropna(subset=[ycol] + FEATURES)
    tr, te = df[df["year"].isin(TRAIN_YEARS)], df[df["year"] == TEST_YEAR]
    Xtr, ytr, Xte, yte = tr[FEATURES], tr[ycol].values, te[FEATURES], te[ycol].values
    k = 100 if target == "A" else 50

    out: dict = {"target": target, "label": ycol, "test": {}, "baselines": {}, "cv_by_state": {}}
    fitted = {}
    for name, m in _models().items():
        m.fit(Xtr, ytr)
        fitted[name] = m
        out["test"][name] = evaluate(yte, m.predict_proba(Xte)[:, 1], k)
    for name, col in {"rank_by_population": "log_pop", "rank_by_freeway_vmt": "log_fwy_vmt",
                      "rank_by_existing_ports": "log_dcfc_ports"}.items():
        score = pd.Series(te[col].values).rank(pct=True, method="first").values
        res = evaluate(yte, score, k)
        res["brier"] = None  # ranks are not probabilities
        out["baselines"][name] = res

    # Leave-states-out CV on all labeled years (robustness to geography).
    allx = df[df["year"].isin(FINAL_YEARS)]
    gkf = GroupKFold(n_splits=5)
    for name in ["logit", "forest"]:
        aucs = []
        for a, b in gkf.split(allx, groups=allx["state"]):
            m = _models()[name].fit(allx.iloc[a][FEATURES], allx.iloc[a][ycol])
            aucs.append(roc_auc_score(allx.iloc[b][ycol], m.predict_proba(allx.iloc[b][FEATURES])[:, 1]))
        out["cv_by_state"][name] = {"mean_auc": float(np.mean(aucs)), "min_auc": float(np.min(aucs)),
                                    "max_auc": float(np.max(aucs))}

    # Statsmodels logit on standardized features for coefficient table (odds ratios, p-values).
    import statsmodels.api as sm  # pipeline-only dependency

    varying = [c for c in FEATURES if Xtr[c].std() > 0]
    Xs = Xtr[varying]
    mu, sd = Xs.mean(), Xs.std()
    sm_fit = sm.Logit(ytr, sm.add_constant((Xs - mu) / sd)).fit(disp=0, maxiter=200)
    coef = pd.DataFrame({"coef": sm_fit.params, "se": sm_fit.bse, "p_value": sm_fit.pvalues})
    coef["odds_ratio_per_sd"] = np.exp(coef["coef"])
    out["logit_coefficients"] = coef.drop(index="const").round(4).to_dict(orient="index")
    lasso_coef = fitted["lasso"][-1].coef_[0]
    out["lasso_coefficients"] = dict(zip(FEATURES, np.round(lasso_coef, 4).tolist()))
    out["lasso_C"] = float(fitted["lasso"][-1].C_[0])

    imp = permutation_importance(fitted["forest"], Xte, yte, scoring="roc_auc", n_repeats=5,
                                 random_state=SEED, n_jobs=-1)
    out["forest_importance"] = dict(zip(FEATURES, np.round(imp.importances_mean, 4).tolist()))

    # Calibration table (deciles) for the logit on the test year.
    p = fitted["logit"].predict_proba(Xte)[:, 1]
    bins = pd.qcut(p, 10, labels=False, duplicates="drop")
    cal = pd.DataFrame({"bin": bins, "p": p, "y": yte}).groupby("bin").mean()
    out["calibration_logit"] = cal.round(4).to_dict(orient="list")
    return out


def fit_final(panel: pd.DataFrame, target: str, model: str = "logit"):
    """Refit on all labeled years for scoring the most recent feature year."""
    ycol = TARGETS[target]
    df = add_model_features(panel).dropna(subset=[ycol] + FEATURES)
    df = df[df["year"].isin(FINAL_YEARS)]
    m = _models()[model].fit(df[FEATURES], df[ycol].values)
    return m
