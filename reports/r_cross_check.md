# R cross-check of Python models

Generated 2026-09-29 with R 4.3.3, glmnet 4.1.8, pROC 1.18.5.

## Target A (y_new_site)

| Check | R | Python | Pass |
|---|---|---|---|
| Logistic test AUC | 0.8839 | 0.8839 | yes |
| Max abs coefficient difference (standardized) | 0.00005 | | yes |
| Lasso test AUC (glmnet, lambda.min) | 0.8843 | 0.8850 | info |
| Lasso features kept | 17 of 17 | | info |

Overall: **PASS**

## Target B (y_first_site)

| Check | R | Python | Pass |
|---|---|---|---|
| Logistic test AUC | 0.8173 | 0.8172 | yes |
| Max abs coefficient difference (standardized) | 0.00005 | | yes |
| Lasso test AUC (glmnet, lambda.min) | 0.8187 | 0.8180 | info |
| Lasso features kept | 8 of 14 | | info |

Overall: **PASS**

