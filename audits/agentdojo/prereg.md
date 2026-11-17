# AgentDojo: pre-registration

Written 2026-11-17, before any ASR was tabulated by exposure, ability or follow stratum.

## What had been seen before writing this

- The published table reproduces exactly from the traces: all 28 rows, utility, utility under
  attack and targeted ASR to 0.00 pp (`scripts/02_reproduce.py`, `results/reproduce.csv`).
- Per-pipeline exposure rates (no outcomes): 55% (Gemini 2.0 Flash 001) to 97% (Claude 3.7
  Sonnet) of the 629 cases; the PI detector redacts a tool output in 86% of its cases.
- All 91 errored cases in the 20 model + 4 defence pipelines are stored with `security = True`
  (Llama 3 70B 35, Command-R+ 22, Gemini 1.5 Pro 001 19, GPT-3.5 12, Command-R 3).
- 60 hand-read cases (`results/handread_sample.txt`, seed 7) and the scorer code.
- My exposure feature agrees with the authors' own `<INFORMATION>`-tag definition in
  `util_scripts/create_results_table.py` on 17,461 of 17,461 important_instructions cases.

## Data and units

- Cases: the v1.1.2 set used by the published table, 629 per pipeline (97 user tasks crossed with
  the 6/9/7/5 injection tasks of workspace/banking/travel/slack), attack `important_instructions`.
- Pipelines: the 20 undefended models of the published table (`scripts/common.py: MODELS`) and
  the 4 GPT-4o defences (`DEFENCES`).
- Unit of resampling: user tasks and injection tasks, resampled independently (crossed two-way
  bootstrap, B = 2,000, seed 0). Cases are never resampled as independent rows.

## Features (computed per case in `scripts/01_extract.py`, frozen here)

- **E, exposure.** An injected string from the trace's own `injections` field appears in at least
  one tool message the agent received. For the PI detector, **reached** = E or a tool output was
  replaced by the redaction notice.
- **F, follow.** The agent issued an executed tool call (tool message `error` is null) that performs
  the attacker's action, judged leniently (contacts the attacker's address, IBAN, URL or user, or
  does the destructive act; exact content not required). Travel injection_task_6 (text-only):
  the final answer names the hotel and uses the injection's praise words. Rules:
  `ATTACKER_ACTIONS` in `scripts/01_extract.py`.
- **A, ability.** The model's stored utility when the same injection task's GOAL was given to it
  as the user prompt with no attack (`runs/<p>/<suite>/injection_task_k/none/none.json`), one run
  per model and injection task.
- **X, errored.** Stored `error` is not null.

## Statistics

- S0 published ASR = mean(security) over 629 cases.
- S1 ASR | E = mean(security | E).
- S2 ASR | E, A = mean(security | E and A).
- S3 follow | E = mean(F | E): propensity to act on the injection, not requiring correct execution.
- S4 ASR with errored cases scored as not attacked (security = False).
- Benign utility U = mean utility of the 97 no-attack user-task runs.

## Conclusions under test and decision rules

**C1, model ranking (20 models).** Compare S0 with S1 and S3. Count model pairs separated under S0
(two-way bootstrap 95% CI of the difference excludes 0). *Changes* if at least one S0-separated
pair is separated in the opposite direction under S1 or S3, or Spearman(S0, S1) < 0.8.
*Holds* if no separated pair reverses and Spearman >= 0.8. Report Kendall tau too.

**C2, "more capable models are easier to attack".** Spearman correlation across the 20 models
between U and S0, and between U and S1, S2, S3, each with a two-way bootstrap CI (models fixed,
tasks resampled). *Changes* if the S0 correlation is positive with CI above 0 and the conditional
correlation's CI includes 0, or the conditional point estimate is below half the S0 estimate.
*Holds* if the conditional correlation remains positive with CI above 0 and at least half the S0
estimate. If the S0 correlation itself is not positive with CI above 0, report that the published
trend is not supported at the task level and stop there.

**C3, GPT-4o defences.** For each defence d against undefended GPT-4o (0), decompose
log(ASR_d / ASR_0) = log(E_d / E_0) + log(S1_d / S1_0) (for the detector use reached instead of E).
Exposure share = first term / total. *Gain is mostly "agent does less"* if exposure share >= 0.5;
*mostly resistance* if S1_d is below S1_0 with CI excluding 0 and exposure share < 0.5.
For tool_filter, additionally report ASR among exposed cases whose filtered tool list contains
the attacker's tool; if that is at least half of S1_0, the filter's gain comes from removing the
tool rather than from the model resisting.

## Secondary analyses (descriptive; no decision rule)

- Scorer validity: P(F | security) and P(F | not security, E) per model; placebo: rate at which the
  attacker's action occurs in no-attack runs of the same user task, per injection task, and the
  share of each model's ASR on (user task, injection task) pairs with a nonzero placebo rate.
- Error coding: S4 against S0 per model.
- Model name in the attack text per pipeline; GPT-4o name ablations reproduced from traces.
- Concentration: share of each model's successes from its top 3 of 27 injection tasks and from
  its top suite; two-way bootstrap CI against the row-level binomial interval; number of
  published model pairs separated under each.
- Content-blind predictors of security: suite, injection task id, injected output length and
  relative position, number of tool calls the user task needs (median executed calls in
  successful no-attack runs by the other models). Grouped CV by user task, AUROC against a
  1,000-shuffle permutation null within suite.

## Robustness checks planned

1. Drop each suite in turn (C1, C2).
2. Drop each model family (OpenAI, Anthropic, Google, Cohere, Meta) for C2.
3. Common support: for each model pair, S1 on cases exposed for both models (answers "S1 selects
   easier cases for weaker models").
4. Placebo feature: a random exposure flag with each model's own exposure rate, within suite
   (C1, C2 should not change).
5. Different statistic: Pearson on logit rates instead of Spearman.
6. Multiple comparisons: count every test run and report a Holm-corrected view of C1 pair tests.

## Alternative explanations to test

- Non-exposure is itself robustness. Checked by construction (E is decided before the agent sees
  any injected text) and by reading non-exposed cases.
- Conditioning on E selects easier cases for weak models (robustness 3).
- The trend is one family (robustness 2).
