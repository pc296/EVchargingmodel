# Independent R check of the Python models (ADR-0007).
# Refits the logistic regression (glm) and Lasso (glmnet) for targets A and B on the same
# panel and temporal split, then compares coefficients and test AUC with Python's results.
# Run from repo root:  Rscript R/cross_check.R
suppressPackageStartupMessages({ library(glmnet); library(pROC); library(jsonlite) })

panel <- read.csv("data/processed/panel_model.csv")
py <- fromJSON("data/processed/model_metrics.json")
features <- c("log_pop", "pop_growth", "log_density", "bev_per_1k", "elec_price_c_kwh",
              "ev_incentives", "log_fwy_vmt", "has_freeway", "log_interstate_miles",
              "log_dcfc_ports", "log_large_sites", "log_ports_per_1k_bev", "tesla_share",
              "log_dist_large_dcfc", "log_ports_50mi", "log_new_large_t", "state_new_large_per_1m")
targets <- c(A = "y_new_site", B = "y_first_site")
set.seed(42)
lines <- c("# R cross-check of Python models", "",
           sprintf("Generated %s with R %s, glmnet %s, pROC %s.", Sys.Date(), getRversion(),
                   packageVersion("glmnet"), packageVersion("pROC")), "")

for (t in names(targets)) {
  y <- targets[[t]]
  d <- panel[!is.na(panel[[y]]) & complete.cases(panel[, features]), ]
  tr <- d[d$year %in% 2021:2023, ]; te <- d[d$year == 2024, ]
  feats <- features[sapply(features, function(f) sd(tr[[f]]) > 0)]
  mu <- sapply(tr[, feats], mean); s <- sapply(tr[, feats], sd)
  Xtr <- scale(tr[, feats], mu, s); Xte <- scale(te[, feats], mu, s)
  fit <- glm(tr[[y]] ~ Xtr, family = binomial())
  p_te <- plogis(cbind(1, Xte) %*% coef(fit))
  auc_r <- as.numeric(auc(roc(te[[y]], as.vector(p_te), quiet = TRUE)))
  auc_py <- py[[t]]$test$logit$roc_auc
  r_coef <- coef(fit)[-1]; names(r_coef) <- feats
  py_coef <- sapply(feats, function(f) py[[t]]$logit_coefficients[[f]]$coef)
  maxdiff <- max(abs(r_coef - py_coef))

  cvfit <- cv.glmnet(as.matrix(Xtr), tr[[y]], family = "binomial", alpha = 1,
                     type.measure = "auc", nfolds = 5)
  p_l <- predict(cvfit, as.matrix(Xte), s = "lambda.min", type = "response")
  auc_l <- as.numeric(auc(roc(te[[y]], as.vector(p_l), quiet = TRUE)))
  kept <- sum(coef(cvfit, s = "lambda.min")[-1] != 0)

  pass <- abs(auc_r - auc_py) < 0.005 && maxdiff < 0.01
  lines <- c(lines, sprintf("## Target %s (%s)", t, y), "",
    "| Check | R | Python | Pass |", "|---|---|---|---|",
    sprintf("| Logistic test AUC | %.4f | %.4f | %s |", auc_r, auc_py, ifelse(abs(auc_r - auc_py) < 0.005, "yes", "no")),
    sprintf("| Max abs coefficient difference (standardized) | %.5f | | %s |", maxdiff, ifelse(maxdiff < 0.01, "yes", "no")),
    sprintf("| Lasso test AUC (glmnet, lambda.min) | %.4f | %.4f | info |", auc_l, py[[t]]$test$lasso$roc_auc),
    sprintf("| Lasso features kept | %d of %d | | info |", kept, length(feats)), "",
    sprintf("Overall: **%s**", ifelse(pass, "PASS", "FAIL")), "")
}
dir.create("reports", showWarnings = FALSE)
writeLines(lines, "reports/r_cross_check.md")
cat(lines, sep = "\n")
