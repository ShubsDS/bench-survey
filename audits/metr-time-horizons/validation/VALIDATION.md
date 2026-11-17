# Validation of the METR time-horizon audit

Validator: an independent agent that did not write the audit. Date 2026-11-17. No inference spent.
Files: `validate.py` (own code, imports nothing from `../scripts`), `validation.json` (all numbers
below unless noted), `compare_rerun.py` and `rerun_diff.json` (task A), `validate_stdout.txt`.
Bootstrap: 1,000 draws, family → task → run, runs resampled jointly across variants (paired), seed 777+i.

## Verdicts

| # | Claim | Verdict |
|---|---|---|
| 1 | Reproduction: 23 p50s within 0.02%, 2023+ DT 128.74 vs 128.744 | **HOLDS** |
| 2a | Token budget rises with release date (0.8M, 8M, 16M) | **HOLDS WITH CORRECTION** (Opus 4.6's budget is not observed) |
| 2b | 8M common cap: Opus 4.6 719 → 356 min (0.50 [0.13, 0.83]), GPT-5.2 0.67, GPT-5.3-Codex 0.68; DT 138.4 d, ratio 1.075 [1.029, 1.172]; survives Bonferroni | **HOLDS** as arithmetic of the stated rescoring |
| 2c | Interpretation: "the extra budget accounts for a large part of the newest models' horizons", "halves Opus 4.6's horizon" | **HOLDS WITH CORRECTION**: an upper bound resting on an assumption that the data partly contradict |
| 2d | Opus 4.6's lead over Opus 4.5 shrinks from 2.45× to 1.22× | **HOLDS WITH CORRECTION**: the capped ratio's 95% CI is [0.65, 2.39] |
| 2e | Opus 4.5 moves above GPT-5.2 and GPT-5.3-Codex | **HOLDS WITH CORRECTION**: point estimate only, bootstrap probability 0.73; it also happens at GPT-5.2's own 16M budget |
| 2f | Random-removal placebo moves DT by 0.99–1.01, so "the effect comes from where the high-token successes sit" | **HOLDS WITH CORRECTION**: a length-matched placebo reproduces the cap effect, so the cap adds nothing beyond "remove that many long-task successes" |
| 2g | Novelty of the fixed-token-budget equalisation | **HOLDS WITH CORRECTION**: METR publishes the same rescoring as "time horizon vs tokens" curves, and its per-model budgets |
| 3 | R results: HCAST-only DT 126.3; baselined-only 114.9 [60.8, 159.3]; estimate −0.84 logits; drop-one-family ≤3%; Opus 4.6 RE-Bench +3.5 logits | **HOLDS** (re-run exact; HCAST-only independently re-derived) |

## A. Rerun of the auditor's scripts

I copied `scripts/*.py` to a fresh scratch directory, linked the pinned `data/`, ran 01–07 with
`python -I`, and compared every numeric and string leaf of the eight `results/*.json` files against
the committed ones (`compare_rerun.py`). **2,373 leaves, 0 differences, no missing files**
(`rerun_diff.json`). Pins verified: the sha256 of both `runs.jsonl` files, `release_dates.yaml`,
`benchmark_results_1_1.yaml` and `task_results_1_1.yaml` match the README; the clone is at
`52cb829c`. (A first rerun attempt was discarded because a sibling agent wrote into the same scratch
path; the reported rerun used a unique directory.)

## B. Independent re-derivation (claims 1 and 2)

- The fit is sklearn `LogisticRegression(C=1e5)` called directly (METR's own estimator,
  `src/horizon/utils/logistic.py:7-55`), not the auditor's Newton solver. My invsqrt weights match
  METR's precomputed `invsqrt_task_weight` column to 4e-10. Counts from `runs.jsonl` match
  `task_results_1_1.yaml` on all 4,523 agent-task pairs.
- **Claim 1.** All 23 p50s match METR's published values to |log ratio| ≤ 5e-8 (closer than the
  auditor's 1.6e-4). The SOTA set (14 agents, from METR's `is_sota` flags, 2023+, ≤16 h) gives
  128.744 d. Reference bootstrap CI [104.8, 159.1] vs published [104.4, 158.0].
- **Claim 2, 8M cap** (point estimates identical to the auditor's to the printed precision):
  Opus 4.6 356.2 min, GPT-5.2 234.1, GPT-5.3-Codex 237, Opus 4.5 293.0, DT 138.4 d (ratio 1.075).
  My paired 95% CIs: DT ratio [1.029, 1.159]; 98.3% CI [1.020, 1.192]; no draw ≤ 1. Opus 4.6 ratio
  [0.17, 0.84]; GPT-5.2 [0.43, 0.87]; GPT-5.3-Codex [0.44, 0.88]. With a 10-test Bonferroni (99.75%)
  they stay below 1: [0.06, 0.93], [0.32, 0.94], [0.33, 0.92].

## C. Attack on the token-budget claim

**C1. Is the budget a real limit?** Partly. METR states budgets in prose, not in a data field:
Opus 4.5 had 8M and GPT-5 16M ("Measuring Time Horizon using Claude Code and Codex", METR note,
13 Feb 2026); GPT-5.1-Codex-Max had 32M in its own report (TH1.0 data agree: max 32.4M). There is no
budget column in `runs.jsonl`; `params.yaml:251-254` only labels the `tokens_count` axis "Allowed
Tokens per Run". In the data, the limit is visibly binding for OpenAI reasoning models: 49 of GPT-5's
51 usage-limit stops, and all of GPT-5.2's 97, sit at 16.0–16.6M. **It is never observed for Opus
4.6**: none of its 995 runs stopped at a token limit; its 18 usage-limit stops ended at the 8-hour
time limit (median 8.3 h) with 0.7–14.8M tokens, and all 18 were scored successes. Its maximum is
15.5M. So "16M for Opus 4.6" is inferred from the maximum observed, contrary to the prereg's "inferred
from where usage-limit runs stop". Opus 4.5's 8M bound rarely binds either (4 of 648 runs). The
README sentence "Runs stop at about … 16M for … Claude Opus 4.6" is wrong and was corrected.

**C2. Are token counts comparable?** No evidence that they are. OpenAI reasoning models run in
`triframe_inspect` and all Claude, Gemini and GPT-4-class models in `metr_agents/react`, so budget,
scaffold and provider are collinear. METR's own GPT-5.1-Codex-Max report says that "due to API and
scaffold differences, direct comparisons of absolute token usage between models can be misleading".
The data do not say whether `tokens_count` includes cached or reasoning tokens. Tokens per wall-clock
hour on HCAST differ 10-fold within a single scaffold (0.012M/h GPT-5.2 vs 0.11M/h GPT-5.3-Codex),
so wall time cannot calibrate them. An 8M cap therefore does not mean the same compute for a
triframe GPT model as for a ReAct Claude model.

**C3. Would an over-cap success have failed at 8M?** The data argue against treating the rescoring
as an estimate rather than a bound.
- *Where the effect comes from.* Opus 4.6's 40 over-8M successes fall on 9 tasks, 22 of them on RE-Bench
  (`opus46_over8M_tasks`). On `ai_rd_triton_cumsum` and `ai_rd_rust_codecontests_inference`, Opus 4.6
  succeeds 16 of 16 times, every run using 12.2–14.8M tokens; the cap scores them 0 of 16. Opus 4.5,
  with an 8M budget, solved `triton_cumsum` 4 of 4 under 7.5M. Opus 4.6 succeeded 6 of 6 on
  `network_routing/main` and `robot_control` (the only 1,800-minute task), but only 1 of 6 under 8M
  on each; Opus 4.5 solved them 4 of 4 and 3 of 4 within 8M. RE-Bench and long HCAST runs keep working
  until a time limit, so their token use tracks elapsed time, not what the task needed.
- *Over-cap-only tasks.* For the 16M models, 2 to 6 tasks were solved only by over-8M runs: Opus 4.6 3
  (2 RE-Bench), GPT-5.2 5, GPT-5.3-Codex 5, o3 6.
- *Within-model, within-task.* On HCAST tasks with mixed outcomes, successes used *fewer* tokens than
  failures: geometric-mean ratio 0.63 [0.38, 0.92] for Opus 4.6, 0.76 [0.62, 0.92] for GPT-5.2, 0.51
  for o3, 0.94 [0.67, 1.21] for GPT-5.3-Codex. More tokens is not generally the route to success; long
  failing runs are. On RE-Bench, too few tasks have mixed outcomes to say anything.
- *METR's direct test.* METR reran Opus 4.5 with 32M instead of 8M (Claude Code scaffold) and
  reported that the preliminary horizon "barely changed". Its GPT-5.1-Codex-Max report says that
  model's gains were "modest beyond 5M tokens per task attempt".
- *Submission reminders.* The scaffold tells agents their remaining budget. METR attributes a score
  bump at the end of the budget to the reminder to submit. A model given 8M gets that reminder near
  8M; rescoring a 16M run at 8M does not.
- *Natural experiment (weak).* GPT-5 ran with 8M in TH1.0 (Vivaria) and 16M in TH1.1 (Inspect). On 89
  shared tasks its actual 8M p50 is 148 min, against 161 min at 16M and 142 min for the 16M runs
  rescored at 8M. That is consistent with the rescoring for GPT-5. GPT-5.1-Codex-Max reversed: 166 min
  at 32M (TH1.0) against 225 min at 16M (TH1.1). Harness differences dominate. No intervals; descriptive only.

**C4. RE-Bench and best-so-far.** RE-Bench scores the best result reached during the run, and the
binarised success does not record when it was reached. The auditor flagged this. My re-derivation of its
post-hoc variant that leaves RE-Bench unrescored: Opus 4.6 ratio 0.70 [0.32, 1.00] (P(ratio ≥ 1) =
0.036), GPT-5.2 0.75 [0.52, 0.93], GPT-5.3-Codex 0.76 [0.53, 0.94], DT ratio 1.044 [1.011, 1.105].
Opus 4.6 / Opus 4.5 is then 1.71 [0.91, 4.29], and Opus 4.5 above both GPT models has probability
0.53. The same issue affects capped HCAST runs that were cut off by a limit but still passed:
**capping GPT-5.2 at its own nominal 16M budget already lowers it to 283 min (0.80)**, because its
successes in limit-stopped runs at 16.0–16.6M are rescored. At that cap Opus 4.5 (293) already sits
above GPT-5.2 (283). The ranking change therefore does not need any difference in budgets between
the two labs' models.

**C5. Dependence on the 8M choice.** Point trace (`cap_trace_point`):

| Cap | 1M | 2M | 4M | 6M | 8M | 10M | 12M | 14M | 16M | none |
|---|---|---|---|---|---|---|---|---|---|---|
| DT, d | 167.6 | 156.8 | 146.8 | 142.1 | 138.4 | 136.6 | 135.5 | 131.2 | 130.4 | 128.7 |
| Opus 4.6, min | 165 | 200 | 266 | 310 | 356 | 387 | 425 | 704 | 719 | 719 |
| GPT-5.2 | 73 | 111 | 171 | 207 | 234 | 250 | 255 | 262 | 283 | 352 |
| Opus 4.5 | 162 | 190 | 210 | 240 | 293 | 293 | 293 | 293 | 293 | 293 |
| Opus 4.6 / Opus 4.5 | 1.02 | 1.06 | 1.27 | 1.29 | 1.22 | 1.32 | 1.45 | 2.40 | 2.45 | 2.45 |

The direction holds at every cap; the size does not. Opus 4.6 jumps from 425 to 704 minutes between
12M and 14M, the band holding its full-length RE-Bench runs. The 8M cap was fixed in `prereg.md`
(commit a5facb7, 10:58:41), before the effect script was last edited (10:59:48) and before
`effects.json` was committed (11:01:06 smoke run, 11:02:58 final). The prereg was not edited afterwards.
The prereg admits the inventory had already shown the share of successes above 8M by release date.

**C6. Pairing and multiplicity.** The pairing is correct. Variants share each draw's family, task and
run resample (`03_effects.py:162-183`; the same in mine). The 98.3% interval is the right Bonferroni
level for the three pre-registered DT tests (`ci_bonf` uses 0.05/6 per tail). The scripts make far more
interval statements than three: 9 variants × (1 DT + 5 horizons) in 03, 5 rules × 6 in 05, and 12
joint coefficients. The DT shift still survives, since no bootstrap draw has a ratio ≤ 1 (p < 0.001),
so it survives correction for any number of tests up to about 50. The horizon ratios at 8M survive a
10-test correction (above). They do not survive the RE-Bench-spared rescoring for Opus 4.6.

**C7. Ranking noise.** Under the 8M cap: P(Opus 4.5 > GPT-5.2) = 0.83, P(Opus 4.5 > GPT-5.3-Codex) =
0.78, P(above both) = 0.73. P(Opus 4.6 still first among the five) = 0.73. Capped Opus 4.6 / Opus 4.5 =
1.22, 95% CI [0.65, 2.39]. Uncapped, the same ratio is 2.45 [1.32, 9.16] and P(Opus 4.5 above both
GPT models) = 0.10. So the cap moves the ordering from "clearly GPT-5.x above Opus 4.5" to "not
distinguishable". It does not establish a reversal.

**C8. Placebo.** The auditor's placebo removes the same number of successes at random from *all*
of each agent's successes, most of them on short tasks; it moves nothing. That only shows the effect
is not about the count of removed successes. 87% of over-8M successes are on tasks of 240 minutes or
more. A **length-matched placebo** removes the same number at random from each agent's successes on
tasks of 240 minutes or more, ignoring tokens (200 draws). It gives Opus 4.6 0.53 [0.51, 0.56], GPT-5.2
0.72 [0.69, 0.75], GPT-5.3-Codex 0.70 [0.68, 0.72] and DT ratio 1.064 [1.060, 1.068], close to the cap's
0.50, 0.67, 0.68 and 1.075. The cap result is therefore what removing about 40 (Opus 4.6) or 22–39
(GPT-5.x) long-task successes does. The token information selects which ones but barely changes the
size. The whole result rests on whether those successes would really have been failures at 8M (C3).

## D. What was already public

- **Per-model budgets differ.** METR, 13 Feb 2026 note: Opus 4.5 8M, GPT-5 16M, plus a 32M rerun of
  Opus 4.5 that "barely changed" the horizon. GPT-5 report (Aug 2025): about 30% of GPT-5's failures
  came from running out of tokens, and GPT-5 "could have benefitted from a larger token budget". A
  May 2025 LessWrong comment by kndjckt on the o3 evaluation said o3 and o4-mini had 16M versus 2M for
  Claude 3.7 Sonnet. METR's Lucas Sato replied that 2M was chosen as "high enough to not be a
  bottleneck". The audit's prior_work item 20 attributes the 16M statement to METR staff; it was the
  commenter's reading.
- **The rescoring itself.** Counting every run not finished by token level T as a failure and refitting
  the horizon is METR's own method. It is implemented in the pinned repo
  (`src/horizon/wrangle/score_over_resource_horizon.py:48-80`, stage `wrangle_score_over_resource_horizon@tokens_count`)
  and published as "time horizon vs tokens" figures in the GPT-5 and GPT-5.1-Codex-Max reports and the
  Feb 2026 note. Those figures carry METR's warning that cross-model token comparisons can mislead.
  METR concluded that models were "unlikely to benefit from higher token budgets".
- **Cost caps.** Woodruff (Redwood/LessWrong, Mar 2026): the trend persists under cost caps
  relative to human cost.
- **Not found public:** reading all TH1.1 frontier horizons at one common cap; the 2023+ doubling time
  under a common cap with paired intervals; the observation that Opus 4.6's lead over Opus 4.5 lies
  almost entirely in over-8M successes. These remain new, as an upper-bound sensitivity analysis.

## E. Spot-check of an R result

HCAST-only (E1b), re-derived independently: DT 126.26 d (auditor 126.3), ratio 0.981 (auditor 0.981),
Opus 4.6 483.8 min, GPT-5.2 367.5 min. HOLDS. The remaining R numbers (baselined-only 114.9
[60.8, 159.3]; estimate coefficient −0.84 [−1.57, −0.11]; drop-one-family 125.6–132.6 d, i.e. −2.4% to
+3.0%; Opus 4.6 RE-Bench +3.49 [1.76, 7.15]) reproduce exactly in the rerun but were not re-derived
with my own code.

## Changes made to README.md

1. Added a "Validation" section after the status table.
2. Status table row C2/token: "Changes" → "Changes under the stated rescoring (an upper bound)", with
   the RE-Bench-spared numbers and the probability of the ranking change added.
3. What-we-found item 2: removed "16M for … Claude Opus 4.6" as an observed stop. Reworded "the extra
   budget accounts for a large part" to say that successes above 8M account for it, and that whether
   the budget caused them is not shown. Added the capped lead's CI [0.65, 2.39].
4. "The confound" section: Opus 4.6's maximum is not a budget; its usage-limit stops are time-limit
   stops. Budgets confounded with scaffold (triframe vs ReAct). Source of the stated budgets (METR note).
5. "The effect": the placebo sentence corrected (the length-matched placebo reproduces the effect).
   The ranking sentence now gives bootstrap probabilities and notes that the order changes at GPT-5.2's
   own 16M cap.
6. "What was already known": added METR's own token-horizon rescoring, its stated budgets and its 32M
   Opus 4.5 rerun; narrowed the novelty claim (a).
7. Prior-work item 20 attribution corrected in README text (the 16M figure came from a commenter).
8. Title: "larger token budgets, which lengthen frontier horizons" became "successes above a common
   cap carry much of the frontier horizons (an upper bound)".
9. Alternative explanation 3: "the budget accounts for half" became "successes above 8M account for
   up to half, an upper bound on the budget's contribution". "Opus 4.6 (16M)" became "budget above
   15.5M, not published".
`prior_work.md`, `claims.md`, `prereg.md` and `results.json` were not edited.

## Overall judgement

The reproduction is exact and the R results are sound. The token-cap arithmetic is right, and the
DT shift (7.5%, inside METR's own interval) is statistically robust. As a statement about
capability, the cap result is an upper bound whose key assumption is weak. Most of Opus 4.6's loss
comes from a handful of long RE-Bench and HCAST tasks that it solves reliably while running until
the time limit, and that its 8M-budget predecessor partly solved within 8M. METR's 32M rerun found
little budget sensitivity. Token counts are not comparable across the triframe and ReAct scaffolds.
For a safety argument, the robust lesson is narrower than the headline: a frontier model's 50%
horizon, and gaps between adjacent frontier models, can rest on a few long tasks and on run-length
and budget settings that differ by model. Treat single-model horizons and orderings as unstable at
the ±2× level. The 2023+ doubling time moves by under 10% under any cap from 7M to 16M (14% at 4M, 30% at 1M).
