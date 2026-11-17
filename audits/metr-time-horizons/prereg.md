# Pre-registration: METR time horizons effect tests

Committed 2026-11-17 before any model outcome was computed by stratum (by source, by human-time
source, under a token cap or without a family). Already seen at this point: the full-set
reproduction (`scripts/01_reproduce.py`) and the L1 inventory (`scripts/02_inventory.py`), which
contains no success rates by stratum. The inventory showed that the token budget and the share of
successful runs above 8M tokens rise with release date. That is why test E3 was added.

## Common definitions

- **Fit:** METR's own. A per-agent weighted logistic of run success on log2 human minutes. Weights
  are 1/(runs in task × √tasks in family), recomputed within each subset. Regularisation is 1e-5.
  The 50% horizon is where the fit crosses 0.5. Reproduced exactly (`results/reproduce.json`).
- **Doubling time (DT):** ln 2 / slope of an OLS fit of ln p50 on release date. The fit uses the
  **published 2023+ SOTA set**, fixed at 14 agents: GPT-4 0314, GPT-4 1106, GPT-4o, Claude 3.5
  Sonnet (Old), o1-preview, Claude 3.5 Sonnet (New), o1, Claude 3.7 Sonnet, o3, GPT-5, Gemini 3 Pro,
  Claude Opus 4.5, GPT-5.2, Claude Opus 4.6. Re-selecting SOTA agents under each variant is a
  secondary analysis.
- **Reference:** our reproduction of the published DT, 128.7 days, with the published CI [104.4, 158.0].
- **Frontier horizons:** p50 of Claude Opus 4.6, GPT-5.2, GPT-5.3-Codex, Claude Opus 4.5 and Gemini 3 Pro.
- **Unit of resampling:** task family, then task, then run (METR's hierarchy). We use 1,000 draws
  with seeds 1000+i. Variants share each draw's family and task sample. Within a draw, runs are
  resampled jointly across variants: a multinomial over (success at ≤ cap, success above cap,
  failure) per agent-task. Ratios variant/reference are therefore paired.
- **Decision rule for DT:** a variant **changes** the conclusion if the paired 95% CI of
  DT_variant/DT_reference excludes 1 **and** the variant's point DT lies outside [104.4, 158.0].
  It **shifts** the conclusion if the ratio CI excludes 1 but the point lies inside. Otherwise the
  conclusion **holds**.
- **Decision rule for a horizon:** a variant changes it if the paired ratio CI excludes 1 **and**
  the point ratio is outside [0.8, 1.25]. A ranking change means a different model has the highest
  p50 among the five frontier models.

## E1 — Task source (confound family 1)

- **Feature:** `task_source` per task: SWAA, HCAST or RE-Bench. SWAA tasks run up to 0.72 min,
  RE-Bench tasks 455–493 min, HCAST tasks 0.95–1800 min.
- **E1a (L3, does success depend on source at fixed human time?):** one joint weighted logistic
  over all agents. It has an agent-specific intercept and slope on log2 minutes, plus two common
  dummies, SWAA and RE-Bench (HCAST is the reference). Statistic: the two dummy coefficients in
  logits, with a family-bootstrap 95% CI. Secondary: the same with agent-specific dummies, reporting
  the RE-Bench dummy for each frontier model.
- **E1b (primary):** fit on HCAST only. Report DT, the frontier horizons, and paired ratios to the
  reference.
- **E1c:** fit excluding SWAA (HCAST + RE-Bench), the same statistics. METR reports this for
  horizons only, without a DT or intervals.

## E2 — Estimated vs baselined human time (confound family 1)

- **Feature:** `human_source` per task, estimate or baseline. 69 of 228 tasks are estimated, and 26
  of the 31 tasks of 8 h or more.
- **E2a (L3):** the E1a joint model on non-SWAA tasks, with a common `estimate` dummy and source
  dummies. Statistic: the estimate coefficient in logits, with a 95% CI. A positive value means
  models succeed more on estimated tasks than baselined tasks of the same stated length. That would
  be consistent with estimates overstating length, and would inflate horizons.
- **E2b (primary):** fit on baselined tasks only (all sources). The same statistics as E1b.
- **E2c:** HCAST baselined tasks only.

## E3 — Token budget (confound family 6)

- **Feature:** `tokens_count` per run. The budget is about 0.8M for GPT-4 0314, 8M for most Inspect
  runs, and 16M for OpenAI reasoning models and Claude Opus 4.6. This is inferred from where
  usage-limit runs stop.
- **Edit:** impose a common cap B by rescoring as failures the successful runs that used more than
  B tokens. This assumes a run that would have exceeded B fails at B. Primary B = 8M, the most common
  Inspect budget. Secondary B = 0.8M, GPT-4 0314's budget. This uses only the 20 agents with run
  data, which include all 14 SOTA agents.
- **Statistics:** DT and the frontier horizons under each cap; paired ratios.
- **Bias direction to report:** whether larger budgets for newer models make the trend look faster.

## E4 — Family influence (confound family 7)

- Drop each of the 79 families in turn and recompute the DT and the frontier horizons (point
  estimates). Report the range, the most influential families, and how many single-family drops
  move the DT outside [104.4, 158.0] or change the top-ranked frontier model.

## E5 — Content-blind predictor (L2)

- **E5a:** Spearman correlation across the 23 agents between p50 and the weighted average success
  rate, with no human time used.
- **E5b:** per agent-task success rate, predicted under family-grouped 5-fold CV. Models: (i) agent
  plus source dummies, with no human time; (ii) agent plus log2 minutes; (iii) both. Statistic: run-weighted AUROC.
  Null for (i): source labels permuted across families within the same length bin is impossible
  (sources do not overlap), so the null permutes source labels across families, 1,000 times.

## E6 — Forking paths (confound family 7)

A pre-stated grid of 24 specifications: start date {2023-01-01, 2024-01-01, 2025-01-01} × agent set
{SOTA by running max, all agents} × 16 h exclusion {on, off} × weighting {invsqrt, equal}. Report
the median, minimum and maximum point DT, and the share inside [104.4, 158.0]. No specification is
added after seeing results.

## Robustness (step 8)

- Re-select the SOTA set within each variant (secondary to the fixed set).
- E1b and E2b with equal task weights.
- Placebo: a random split of HCAST families into two halves of similar size, repeated 200 times.
  Fit each half and report how far the DT of a random half deviates from the full-set DT, so the
  subset results in E1 and E2 can be compared with the variation expected from dropping tasks at
  random.
- Comparisons counted: three primary DT tests (E1b, E2b, E3 at 8M). We also report whether each
  survives a Bonferroni correction (98.3% CI).

## Alternative explanations to test (step 9)

1. The source effect is difficulty that human time does not capture, i.e. the construct, not a
   confound. Check: whether HCAST-only conclusions match the pooled ones. If they do, pooling is harmless.
2. Estimated tasks differ only because they are longer: the coefficient is estimated at fixed log
   minutes and restricted to the overlapping range (60–1000 min) as a check.
3. Token budget is part of the capability being measured. The METR protocol gives reasoning models
   more tokens deliberately. We report both and do not call either one correct.
