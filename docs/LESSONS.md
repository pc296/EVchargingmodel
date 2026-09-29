# LESSONS
Purpose: running log of mistakes, root causes, and the rules adopted so they do not recur.
Last updated: 2026-09-28

Format: date, what happened, why, durable takeaway.

## 2026-09-28: Summed AADT used as a traffic measure (inherited from Deliverable 2 data)
- What: county "AADT" was the sum of AADT over road segments.
- Why: summing a per-segment average makes the total depend on how many segments the road was cut into.
- Takeaway: aggregate traffic as vehicle-miles (AADT x segment length) or length-weighted AADT, never a raw sum.

## 2026-09-28: Counties with no freeway were imputed as missing
- What: 1,377 of 1,387 "imputed" traffic counties had no interstate or freeway, a true zero.
- Why: absence of a road class was treated as missing data.
- Takeaway: distinguish structural zeros from missing values before imputing anything.

## 2026-09-28: Target variable implied by a score
- What: Deliverable 2 described the score as the dependent variable.
- Why: model output and training label were conflated.
- Takeaway: every supervised model states its label, the time it is observed, and the time features are observed.

## 2026-09-28: Legacy county codes in the team's county file
- What: 4 FIPS codes (Valdez-Cordova, Wade Hampton, Shannon SD, Bedford City VA) no longer exist; joins to 2025 population failed.
- Why: the county list predated 2013-2019 geography changes.
- Takeaway: crosswalk to the population file's vintage first; assert 3,144 unique counties after every join.

## 2026-09-28: Name joins broke on capitalization
- What: 42 counties ("Baltimore city" vs "Baltimore City", "LaSalle" vs "La Salle") failed to match.
- Takeaway: join on FIPS wherever possible; when names are unavoidable, normalize case and spacing and fail loudly on any miss.

## 2026-09-28: Simplified boundaries can drop tiny counties
- What: Falls Church city, VA had an empty polygon in the 10m boundary file, giving a NaN centroid.
- Takeaway: check for empty geometries after loading boundaries; keep a documented fallback.

## 2026-09-28: A reconciliation test caught out-of-scope stations
- What: 2 Puerto Rico stations were silently dropped by the spatial join.
- Takeaway: keep reconciliation tests that compare row counts before and after joins, scoped explicitly.

## 2026-09-29: Walkthrough failed on Google Colab
- What: the first chunk failed on `import numbers_parser`; Colab also has none of the repo's data files.
- Why: the file was tested only inside the repo, where dev requirements and data exist.
- Takeaway: shared notebooks carry their own setup chunk (install missing packages, fetch data) and are tested from an empty folder.

## 2026-09-29: Figures in docs computed on the wrong subset
- What: docs said 86 stations lacked open dates (true for all DC rows; only 1 of the 15,939 stations used), 30% of incentives lacked dates (true for all EV laws; 62% of the 292 incentive records used), and IONNA averaged 8.4 ports (8.46 on the 180 sites used).
- Why: counts were taken during exploration, before filters were final, and never re-derived.
- Takeaway: every figure in a document is regenerated from the final processed data by script before release.

## 2026-09-29: Independent review caught an inert control and a tie rule
- What: the app's "Exact optimizer" checkbox did nothing (one cost per site); baseline ranks broke ties by row order, moving one baseline AUC by 0.007.
- Why: the control was added for a case the app never produces; the rank method was copied from a tie-breaking use.
- Takeaway: every UI control needs a test or a visible effect; evaluation baselines use tie-neutral ranks.
