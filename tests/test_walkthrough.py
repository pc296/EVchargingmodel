"""The submission walkthrough must reproduce the pipeline's model metrics (ADR-0012).
Slow (about 2 minutes): runs only when RUN_SLOW=1."""

import json
import os
import runpy

import pytest

from evcharge import io

WALK = io.ROOT / "analysis" / "ev_charging_model_walkthrough.py"
pytestmark = pytest.mark.skipif(os.environ.get("RUN_SLOW") != "1", reason="set RUN_SLOW=1")


def test_walkthrough_matches_pipeline_metrics():
    ns = runpy.run_path(str(WALK))
    m = json.loads((io.PROCESSED / "model_metrics.json").read_text())
    for label in ["A", "B"]:
        for name in ["logit", "lasso", "forest"]:
            got = ns["results"][label].loc[name, "ROC AUC"]
            assert got == pytest.approx(m[label]["test"][name]["roc_auc"], abs=1e-6)
