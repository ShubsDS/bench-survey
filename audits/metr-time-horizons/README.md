# METR time horizons: newer models had larger token budgets, and successes above a common cap carry much of the frontier horizons (an upper bound); task source and family leave the trend intact

Status: 2026-11-17, complete. No inference spent. Evidence levels per claim:

| Published conclusion | Confound tested | Level | Outcome |
|---|---|---|---|
| C1 2023+ doubling time 128.7 d [104.4, 158.0] | Token budget (family 6) | **L3** | **Shifts**: 8M common cap gives 138.4 d, ratio 1.075 [1.029, 1.172]; inside the published CI. At GPT-4 0314's 0.8M budget (secondary) it **changes**: 172.8 d [144.5, 214.2] |
| C1 | Task source (1) | **R** | Holds: HCAST only 126.3 d [96.8, 159.7], ratio 0.98 [0.89, 1.06] |
| C1 | Estimated vs baselined human time (1) | **R** (low power) | Holds: baselined only 114.9 d [60.8, 159.3], ratio 0.89 [0.48, 1.17] |
| C1 | Family clustering (7) | **R** | Holds: dropping any one of 79 families moves the DT by at most 3.0% |
| C1 | Forking paths (7) | L1 | 24 pre-stated specifications give 101–137 d; 19 of 24 inside the published CI |
| C2 Frontier 50% horizons | Token budget (6) | **L3** (upper bound) | **Changes under the stated rescoring, which is an upper bound**: under a common 8M cap, Opus 4.6 falls from 719 to 356 min (ratio 0.50 [0.13, 0.83]), GPT-5.2 from 352 to 234 min (0.67 [0.40, 0.87]), and GPT-5.3-Codex to 0.68 [0.43, 0.88]. Opus 4.5 is unchanged; it already ran with an 8M budget. If RE-Bench runs are not rescored, Opus 4.6's ratio is 0.70 [0.32, 1.00] (validation) |
| C2 | Task source (1) | L3 (one model) | Opus 4.6 only: HCAST-only 484 min, ratio 0.67 [0.38, 0.93], with a RE-Bench excess of +3.5 logits [1.8, 7.2]. Other frontier models hold. The direction was already known from METR |
| C2 | Estimated vs baselined (1) | Inconclusive | Baselined-only horizons are 1.1–4× longer, but they extrapolate past the data and the intervals are unbounded |
| C3 Success depends on human time, not source | Task source (1) | **R** | Common source effects at fixed log time: SWAA +0.97 [−0.83, 6.29], RE-Bench −0.12 [−1.19, 0.90] logits |
| — | Content-blind ordering (L2) | L2 | Weighted mean success alone orders the 23 agents with Spearman 0.996 against p50 |

## Validation

An independent validator re-ran every script (2,373 result values, 0 differences) and re-derived
claims 1 and 2 with its own code. Details are in [`validation/VALIDATION.md`](validation/VALIDATION.md).
- **Reproduction: holds** (23 p50s within |log ratio| 5e-8; DT 128.744 d).
- **Token cap: the arithmetic holds; the interpretation is corrected.** The 8M-cap numbers and the DT
  shift (ratio 1.075, no bootstrap draw ≤ 1) reproduce. But the rescoring is an upper bound whose
  assumption the data partly contradict:
  - Opus 4.6 never stopped at a token limit; its budget is not observed.
  - 22 of its 40 over-8M successes are RE-Bench runs that ran to the 8 h time limit.
  - Successes use fewer tokens than failures within HCAST tasks.
  - METR's 8M→32M rerun of Opus 4.5 "barely changed" its horizon.
  - Token counts are not comparable across the triframe (OpenAI) and ReAct (Claude, Gemini) scaffolds.
  - A length-matched placebo reproduces the cap effect.
- **The ranking change is within noise.** P(Opus 4.5 above both GPT-5.2 and GPT-5.3-Codex | 8M cap) =
  0.73. The capped Opus 4.6 / Opus 4.5 ratio is 1.22 [0.65, 2.39].
- **The method is not new.** METR's own pipeline and reports publish the same "horizon vs tokens"
  rescoring.
- **R results: hold** (HCAST-only DT re-derived as 126.26 d).

## The benchmark and what rests on it

METR fits, for each AI agent, a logistic curve of run success against log2 of the time a human
expert takes. The 50% time horizon is the task length at which the curve crosses 0.5. The doubling
time of the frontier horizon, reported since 2019 as "~7 months" and since 2023 as about 4 months,
feeds METR's public graph, the AI 2027 forecast and discussion of when AI could automate AI R&D.
Per-model horizons (e.g. "Claude Opus 4.6: about 12 hours") are quoted in launches and comparisons.
See [`claims.md`](claims.md).

## What we found

1. The published numbers reproduce exactly from METR's public per-task counts with our own code:
   all 23 p50s are within 0.02% (max |log ratio| 0.00016), and the 2023+ DT is 128.74 d against 128.744 published. The
   bootstrap CI [103.9, 157.2] matches the published [104.4, 158.0]
   (`scripts/01_reproduce.py`, `results/reproduce.json`).
2. **The per-run token budget rises with release date, and successes that used more than 8M tokens
   account for a large part of the newest models' horizons. Whether the budget caused those
   successes is not shown.** Runs stop at about 0.8M tokens for GPT-4 0314 (Vivaria, 2023), about
   8M for Inspect runs of 2023–25 GPT-4-class models, Claude 3 Opus and Gemini 3 Pro, and about 16M
   for o1, o3 and the GPT-5 series. METR states 8M for Opus 4.5 and 16M for GPT-5 (note of 13 Feb
   2026). Opus 4.6's budget is not observed: no Opus 4.6 run stopped at a token limit. Its 18
   usage-limit stops were 8 h time-limit stops at 0.7–14.8M tokens. It peaks at 15.5M, against 8.07M
   for Opus 4.5, released 10 weeks earlier. Of each frontier model's successes on
   tasks of 4 h or more, 17–20% used more than 8M tokens (Opus 4.6: 37 of 198; GPT-5.2: 19 of 114),
   against 0 of 95 for Opus 4.5. Rescoring those runs as failures, i.e. giving every model the same
   8M budget, halves Opus 4.6's horizon and cuts GPT-5.2 and GPT-5.3-Codex by a third. This is an
   upper bound: it assumes every over-cap success would have failed at 8M (see "What this does not
   show" and the Validation section). Opus 4.6's lead over Opus 4.5 shrinks from 2.45× to 1.22×
   [0.65, 2.39]. The DT lengthens by 7.5%, a ratio whose interval
   excludes 1 even after a Bonferroni correction for three primary tests (98.3% CI [1.024, 1.206]).
   The point estimate stays inside the published interval. **Bias direction:** the larger budgets
   make newer models look more capable and the trend look faster.
3. **Task source and family clustering do not move the trend.** HCAST alone gives the same 2023+
   DT. No single family moves it by more than 3%. For agents in general, success at fixed human time
   does not depend on source. Opus 4.6 is the one exception: its RE-Bench successes lift its horizon
   by about 1.5×.
4. **Estimated human times do not inflate horizons in the direction critics suggested.** At the
   same stated length, models succeed less on tasks whose time was estimated than on baselined
   tasks: −0.84 logits [−1.57, −0.11]. Removing estimated tasks lengthens horizons, but leaves too
   few long tasks to pin them down.

| Variant (`results/effects.json`) | Tasks | 2023+ DT, days [95% CI] | DT ratio to reference [95% CI] | Opus 4.6 p50, min | GPT-5.2 p50, min | Verdict on DT |
|---|---|---|---|---|---|---|
| Reference (published method) | 228 | 128.7 [103.9, 157.2] | 1 | 718.9 [309.8, 4753.6] | 352.2 [188.8, 791.3] | — |
| E1b HCAST only | 157 | 126.3 [96.8, 159.7] | 0.981 [0.893, 1.062] | 483.7 [234.8, 2267.1] | 367.5 [188.8, 1043.1] | holds |
| E1c no SWAA | 162 | 124.4 [96.0, 156.8] | 0.966 [0.884, 1.028] | 673.3 | 350.4 | holds |
| E2b baselined only | 162 | 114.9 [60.8, 159.3] | 0.892 [0.480, 1.173] | 2913.9 (unbounded) | 736.3 [215, 27011] | holds |
| E2c HCAST baselined only | 94 | 120.1 [58.5, 166.4] | 0.933 [0.462, 1.235] | 1070.0 (unbounded) | 751.7 (unbounded) | holds |
| **E3 common 8M token cap** | 228 | **138.4 [115.1, 167.9]** | **1.075 [1.029, 1.172]** | **356.2 [196.9, 871.2]** | **234.1 [141.0, 426.3]** | **shifts** |
| E3 common 0.8M cap (secondary) | 228 | 172.8 [144.5, 214.2] | 1.342 [1.211, 1.596] | 156.2 [95.4, 262.7] | 64.0 [39.4, 99.2] | changes |

All intervals come from 1,000 draws of a family → task → run bootstrap, paired across variants
(seeds 1000–1999). The DT uses the published 14-agent 2023+ SOTA set throughout. Re-selecting the
SOTA set in each variant gives 127.0 (E1b), 122.4 (E2b) and 138.9 d (E3 8M).

## The confound

**Token budget (family 6).** `tokens_count` per run in `runs.jsonl`. The budget is not a field; we
infer it from where usage-limited runs stop (`results/inventory.json`, `elicitation`). For Opus 4.6
(and the Claude models up to Opus 4.1) no run stops at a token limit, so only the maximum is known.
Budget is collinear with scaffold: OpenAI reasoning models ran in `triframe_inspect`, all others in
`metr_agents/react`. METR warns that absolute token counts are not comparable across APIs and
scaffolds. Maximum
tokens per run: GPT-4 0314 0.83M; GPT-4 1106, GPT-4 Turbo, GPT-4o, Claude 3 Opus, Claude 3.5
Sonnet (New), o1-preview, Gemini 3 Pro and Opus 4.5 8.0–8.3M; o1, o3, GPT-5, GPT-5.1-Codex-Max,
GPT-5.2 and GPT-5.3-Codex 16.1–16.6M; Opus 4.6 15.5M. Release date correlates with maximum tokens
(Spearman 0.57) and with the share of successes above 8M (0.74). o3 and the GPT-5 series hit the
limit in 17–39% of their runs on tasks of 4 h or more (o1: 4%; Claude models up to Opus 4.6: 0–5%). Successes above 8M sit on long tasks
(median 480 human minutes): 99 HCAST and 51 RE-Bench (`results/robustness.json`,
`token_cap_diagnostics`).

**Task source.** SWAA tasks take 0.02–0.72 human minutes, HCAST 0.95–1800 and RE-Bench 455–493
(`results/inventory.json`). SWAA and HCAST do not overlap at all. Source is therefore almost
collinear with length, which is why the within-HCAST fit is the main test.

**Human-time source.** 69 of 228 tasks are estimated, including 26 of the 31 tasks of 8 h or more.
The median HCAST estimated task is 270 min, against 21 min for baselined ones. 98% of estimates
are whole minutes (480 appears 12 times); 0.6% of baselines are.

Hand reading (step 4): we read 60 randomly sampled task ids with family, source, human-time source
and minutes (`results/hand_read_sample.json`, seed 0). Task text is not in the public repo.
Notes made before computing anything: SWAA ids are templated micro-tasks (`arithmetic/simple_3`,
`file_selection/find_env_file`), all baselined and under a minute. Estimated times are round
(6, 240, 480, 600, 960). Long tasks are mostly security and ML-engineering families
(`implement_ace_oauth`, `prune_attn_heads`, `backdoor_image_classifier`).

## The effect

- **Token cap (E3).** The rescoring changes outcomes only for runs above the cap. A placebo that
  removes the same number of successes per agent at random moves the DT by a ratio of 0.987–1.010
  and Opus 4.6's horizon by 0.92–1.30 (200 draws, `results/cap_placebo.json`). The cap moves them
  by 1.075 and 0.495, so the effect does not come from the number of removed successes alone.
  Correction (validation): a length-matched placebo removes the same number of successes at random
  from tasks of 240 min or more. It gives DT 1.064 and Opus 4.6 0.53, close to the cap. So the cap's
  effect equals that of removing that many long-task successes, and it stands or falls with the
  assumption that those runs would have failed at 8M. Dose-response (`results/cap_sensitivity.json`, post hoc, task bootstrap): Opus
  4.6 p50 is 266 min at a 4M cap, 356 at 8M, 425 at 12M and 719 uncapped.
- **Ranking.** Under the 8M cap, Opus 4.6 stays first (356 min), but Opus 4.5 (293) moves above
  GPT-5.3-Codex (237) and GPT-5.2 (234). Published order: GPT-5.2 352 > GPT-5.3-Codex 349 > Opus 4.5 293.
  The swap is within noise: in a paired bootstrap, Opus 4.5 is above both GPT models in 73% of draws
  under the cap (10% uncapped), and Opus 4.6 stays first in 73%. Capping GPT-5.2 at its own 16M budget
  already gives 283 min (below Opus 4.5), because successes in its limit-stopped runs at 16.0–16.6M
  are rescored. The swap therefore does not need a difference in budget (validation).
- **Source (E1a).** In a joint model with agent-specific intercepts and slopes, the common SWAA and
  RE-Bench effects are not distinguishable from 0. With agent-specific effects, Opus 4.6's
  RE-Bench coefficient is +3.49 logits [1.76, 7.15], while the other frontier models range from
  −0.95 to +0.15 with intervals spanning 0. For Opus 4.6, this is what drives METR's own
  observation that private-only tasks cut its horizon by 40%.
- **Estimated vs baselined (E2a).** The estimate coefficient is −0.84 [−1.57, −0.11] on non-SWAA
  tasks and −0.85 [−1.67, −0.06] within HCAST. Positive would have meant inflated estimates.

## Robustness

| Check | Result | Claim survives? |
|---|---|---|
| Bonferroni for 3 primary DT tests (98.3% CI) | E3 8M ratio [1.024, 1.206]; E1b [0.864, 1.083]; E2b [0.353, 1.229] | Yes, for all three verdicts |
| Re-select SOTA set per variant | E3 8M 138.9 d [114.1, 172.3]; E1b 127.0; E2b 122.4 | Yes |
| Equal task weights | HCAST only 120.1 d, ratio 0.933 [0.820, 1.032]; baselined only 118.7 d | Yes (holds) |
| Weaker rescoring (post hoc): leave RE-Bench runs unscored | DT ratio 1.044 [1.011, 1.124]; Opus 4.6 0.70 [0.24, 1.00]; GPT-5.2 0.75 [0.54, 0.91] | Direction yes; Opus 4.6 interval reaches 1 |
| Weaker rescoring (post hoc): leave usage-stopped successes unscored | DT 1.057 [1.024, 1.127]; Opus 4.6 0.52 [0.14, 0.82]; GPT-5.2 0.81 [0.64, 0.93] | Yes |
| Random-removal placebo for E3 | DT 0.987–1.010; Opus 4.6 0.92–1.30 | Yes |
| Drop one family (79) | DT 125.6–132.6 d; Opus 4.6 618–851 min; top model never changes | Trend robust; Opus 4.6 moves ±18% |
| Placebo: half of HCAST families (400 fits) | DT ratio 0.82–1.19; Opus 4.6 ratio 0.62–8.4 | E1b and E2b DT shifts are within random-subset noise |

## Alternative explanations

1. **Source is the construct, not a confound.** If pooling sources were biasing the result, the
   HCAST-only trend would differ. It does not (ratio 0.98), so pooling is harmless for C1.
2. **Estimated tasks differ only because they are longer.** The coefficient is estimated at fixed
   log minutes. Restricted to the overlap range of 60–1000 min it is −0.65 [−1.65, 0.27]: same
   sign, not significant. We do not claim estimates are biased, only that they do not inflate horizons.
3. **The token budget is part of the construct.** METR may deliberately give reasoning models more
   room, and a METR staff comment (prior_work item 20) said budgets were not expected to matter.
   Our data show that, for the newest models, successes above 8M tokens account for up to half
   (Opus 4.6) or a third (GPT-5.2, GPT-5.3-Codex) of the 50% horizon. That is an upper bound on what
   the budget itself contributes (validation: METR's 32M rerun of Opus 4.5 barely moved its horizon). Whether that is capability or elicitation is a
   definition we do not settle. The published horizon is a horizon at a model-specific budget, and
   the comparison between Opus 4.5 (8M) and Opus 4.6 (16M) mixes model and budget.

## What was already known

See [`prior_work.md`](prior_work.md). Known: dropping SWAA moves horizons by under 10%; private-only
tasks cut Opus 4.6 by 40% via RE-Bench (METR, March 2026); the non-SWAA TH1.0 trend; date-range
sensitivity; long tasks are mostly estimated; the published bootstrap already resamples families;
cost caps relative to human cost leave the doubling time at 3.0–3.3 months (Woodruff, March 2026);
o3 had a 16M budget (a commenter's reading, May 2025; METR replied that budgets were chosen not to bind).
Also already public (added in validation): METR states per-model budgets (Opus 4.5 8M, GPT-5 16M,
GPT-5.1-Codex-Max 32M), and found that an 8M→32M rerun "barely changed" Opus 4.5's horizon. The rescoring method
itself is METR's: its pipeline (`score_over_resource_horizon.py:48-80`) and its GPT-5 and
GPT-5.1-Codex-Max reports plot the horizon at each token level, counting unfinished runs as failures.
New here: (a) reading all TH1.1 frontier horizons and the 2023+ DT at one common token cap, with
paired intervals and a placebo (the rescoring method is METR's); (b) the HCAST-only and
baselined-only 2023+ DT on TH1.1, with intervals; (c) the estimated-vs-baselined coefficient, whose
sign is opposite to the qualitative critique; (d) the Opus 4.6 RE-Bench excess as an
interval-bearing coefficient; (e) drop-one-family influence on the DT.

## What this does not show

- No model was re-run. E3 is a counterfactual rescoring of logged runs. A model told it had 8M
  tokens might plan differently and finish within budget, so E3 is an upper bound on the budget effect.
- RE-Bench scores the best result reached during a run, so some over-cap successes may have been
  reached before the cap. The post-hoc variant that leaves RE-Bench alone still lowers GPT-5.2 and
  GPT-5.3-Codex, but Opus 4.6's interval then reaches 1.
- Three agents in METR's published file have no run-level data (Gemini 3.1 Pro, GPT-5.4, Claude
  Mythos Preview); E3 excludes them. None is in the 2023+ SOTA set used for the DT.
- We did not test the 2019+ stitched trend (it reuses TH1.0 estimates for three pre-2023 models).
- Baselined-only horizons for frontier models are extrapolations beyond the longest baselined tasks.
- E5 is L2: horizon order is almost a monotone transform of weighted mean success (Spearman 0.996,
  21 of 23 rank positions identical). A source-only predictor reaches AUROC 0.853 per agent-task
  (permutation null 0.617, 97.5% 0.680, p 0.001), against 0.927 for log human time. Human time adds
  information beyond source, but source carries most of the easy/hard split.

## Pins and how to reproduce

- github.com/METR/eval-analysis-public `52cb829c7a2efb2d659285c4b1768d191d97f8d2`; `runs.jsonl`
  TH1.1 sha256 `609f904f4b6ae32129388da89d036e00bac511ad94223d2be1e58fc2b45b55cd`; TH1.0
  `f489d11728909937dad99ba1ed2d7c40efe12a766891e67dbc7c2486a3311236`; `release_dates.yaml`
  `317b92915df5bf935908567a857116bcf6f0c7686ef8b0840897ed04a29232bc`.
- metr.org/assets/benchmark_results_1_1.yaml sha256
  `aae31902b0519a4da73e16643915e5e8aca13cd3315c3aac893ce3d6dfe92ad9`; task_results_1_1.yaml
  `4f85fbf03cbf8b43af102ff17db6bbb4963b3c98784e90f81fb71a146cf26b07` (fetched 2026-11-17).
- METR's code was read, never run. The fit follows `src/horizon/utils/logistic.py:7-58`, the weights
  `compute_task_weights.py:15-56`, the bootstrap `wrangle/bootstrap.py:72-176` and the trend
  `plot/bootstrap_ci.py:429-506`.

```bash
cd audits/metr-time-horizons
mkdir -p data/published && git clone --depth 1 https://github.com/METR/eval-analysis-public data/eval-analysis-public
curl -sSLo data/published/benchmark_results_1_1.yaml https://metr.org/assets/benchmark_results_1_1.yaml
curl -sSLo data/published/task_results_1_1.yaml https://metr.org/assets/task_results_1_1.yaml
uv venv data/.venv && uv pip install --python data/.venv/bin/python numpy pandas scipy scikit-learn pyyaml
for s in 01_reproduce 02_inventory 03_effects 04_robustness 05_cap_sensitivity 06_cap_placebo 07_collect; do
  data/.venv/bin/python -I scripts/$s.py; done   # 03 takes about 6 minutes
```

The venv lives in `data/` because the shared commit script refuses folders holding files over 2 MB.
Inference: none (0 calls, 0 USD). Scripts 05 and 06 are post hoc, as labelled in their docstrings.
