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
