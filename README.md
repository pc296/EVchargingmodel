# EV Charging Expansion Planner

County-level screen for where an IONNA-style DC fast-charging network should build next, under a capital budget. Duke Data Analytics final project (Cronin, Mei, Singh).

**Live app:** https://evchargingmodel-ui5fwbrdxjotcghzbovdvf.streamlit.app/ (Streamlit, `streamlit_app.py`). Users set a budget, cost scenario, and scoring weights; the app returns a map and a ranked, downloadable list of recommended counties.

## What is inside
- `src/evcharge/` pipeline and app logic: loaders (`io.py`), spatial join (`geo.py`), county-year panel (`panel.py`), models (`model.py`), cost scenarios (`cost.py`), scores (`scoring.py`), budget optimizer (`optimize.py`).
- `scripts/run_pipeline.py` rebuilds everything in `data/processed/` from `data/raw/`.
- `R/cross_check.R` refits the models in R (glmnet, pROC); results in `reports/r_cross_check.md`.
- `analysis/ev_charging_model_walkthrough.py` (and `.ipynb`): the whole model in one annotated file, for readers and graders. [Open in Colab](https://colab.research.google.com/github/pc296/evchargingmodel/blob/main/analysis/ev_charging_model_walkthrough.ipynb) and choose Runtime > Run all. Figures in `reports/figures/`.
- `docs/` governance and method. Start with [docs/GOVERNANCE.md](docs/GOVERNANCE.md) and [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Run locally
```bash
pip install -r requirements-dev.txt
python scripts/run_pipeline.py     # about 90 seconds
pytest -q
streamlit run streamlit_app.py
Rscript R/cross_check.R            # optional; needs R with glmnet, pROC, jsonlite
```

## Deploy (Streamlit Community Cloud)
1. Push this repo to GitHub.
2. At share.streamlit.io, sign in with GitHub, choose **New app**, pick this repo, branch `main`, file `streamlit_app.py`.
3. The app uses only `requirements.txt` and the files in `data/processed/`, which are committed.

## Headline results (test year 2025)
| Model | ROC AUC | Population-only baseline |
|---|---|---|
| A: new 4+ port site next year | 0.884 | 0.852 |
| B: first 4+ port site next year | 0.817 | 0.772 |

See [docs/METHODOLOGY.md](docs/METHODOLOGY.md) for the full method, costs and limitations.
