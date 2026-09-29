"""Regenerate reports/traceability_facts.json: every figure used in the traceability report,
computed from data/raw, data/processed and the repo. Run from the repo root after the pipeline."""

import hashlib
import json
import math
import platform
import subprocess
import sys
import warnings
from pathlib import Path

import geopandas
import numpy
import pandas as pd
import plotly
import scipy
import sklearn
import statsmodels
import streamlit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from evcharge import io  # noqa: E402

warnings.filterwarnings("ignore")
F: dict = {}
git = lambda *a: subprocess.check_output(["git", *a]).decode().strip()  # noqa: E731
F["commit"], F["commit_date"] = git("rev-parse", "HEAD"), git("log", "-1", "--format=%ci")

files = {}
for p in sorted(list(io.RAW.glob("*")) + list(io.EXTERNAL.glob("*"))):
    info = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
    if p.suffix == ".csv":
        info["rows"], info["cols"] = pd.read_csv(p, low_memory=False).shape
    elif p.suffix == ".xlsx":
        info["rows"], info["cols"] = pd.read_excel(p, header=None).shape
    files[p.name] = info
F["files"] = files

raw = pd.read_csv(io.RAW / "afdc_stations_2026-09-22.csv", low_memory=False)
dc = raw[raw["EV DC Fast Count"].fillna(0) > 0]
F.update(stations_all_rows=len(raw), dc_rows=len(dc), dc_status=dc["Status Code"].value_counts().to_dict())
st = pd.read_parquet(io.PROCESSED / "stations.parquet")
F.update(stations_used=len(st), stations_ports=int(st.dc_ports.sum()),
         assign=st.county_assign.value_counts().to_dict(), open_year_imputed=int(st.open_year_imputed.sum()),
         ionna_sites=int(st.is_ionna.sum()), ionna_mean_ports=float(st[st.is_ionna].dc_ports.mean()),
         price_parsed=int(st.pricing.map(io.parse_price_per_kwh).notna().sum()))
s0 = io.load_stations()
k = s0[s0.status.isin(["E", "T"])]
F["nonpublic_dropped"] = int(k.non_public_flag.sum())
F["pr_dropped"] = int((~k[~k.non_public_flag].state.isin(io.STATE_ABBR.values())).sum())
t = io.load_traffic()
F.update(no_freeway=int((~t.has_freeway).sum()), traffic_imputed=int(t.traffic_imputed.sum()))
inc = io.load_incentives()
F.update(ev_incentives_n=len(inc), inc_missing_date=int(inc.enacted_year.isna().sum()))
p = pd.read_parquet(io.PROCESSED / "panel.parquet")
F.update(panel_rows=len(p), panel_cols=p.shape[1])
lc = {int(y): {"A_n": int(g.y_new_site.notna().sum()), "A_pos": int(g.y_new_site.sum()),
               "B_n": int(g.y_first_site.notna().sum()), "B_pos": int(g.y_first_site.sum())}
      for y, g in p.groupby("year")}
F["train"] = {key: sum(lc[y][key] for y in (2021, 2022, 2023)) for key in ["A_n", "A_pos", "B_n", "B_pos"]}
m = json.loads((io.PROCESSED / "model_metrics.json").read_text())
for tg in "AB":
    F[f"lasso_nonzero_{tg}"] = sum(1 for v in m[tg]["lasso_coefficients"].values() if abs(v) > 1e-6)
    for v in m[tg]["logit_coefficients"].values():
        v["ci_lo"], v["ci_hi"] = math.exp(v["coef"] - 1.96 * v["se"]), math.exp(v["coef"] + 1.96 * v["se"])
F["metrics"] = m
F["price_imputed_counties"] = int(pd.read_parquet(io.PROCESSED / "app_counties.parquet").price_imputed.sum())
prior = pd.read_csv(io.RAW / "afdc_ionna_dcfc_by_county_prior.csv")
F.update(prior_ports=int(prior["Relevant DCFC Ports"].sum()), prior_ionna_sites=int(prior["IONNA Sites"].sum()))

F["versions"] = {"python": platform.python_version(), "pandas": pd.__version__, "numpy": numpy.__version__,
                 "sklearn": sklearn.__version__, "statsmodels": statsmodels.__version__, "scipy": scipy.__version__,
                 "geopandas": geopandas.__version__, "plotly": plotly.__version__, "streamlit": streamlit.__version__}
F["adrs"] = [line[3:].strip() for line in (io.ROOT / "docs" / "DECISIONS.md").read_text().splitlines()
             if line.startswith("## ADR")]
(Path(__file__).parent / "traceability_facts.json").write_text(json.dumps(F, indent=1, default=str))
print("facts written:", F["commit"][:7])
