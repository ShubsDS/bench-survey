# AgentDojo: exposure and capability do not explain the ASR ranking; error coding does move four models

Status 2026-11-17. No inference was used. Independently validated the same day
([`validation/VALIDATION.md`](validation/VALIDATION.md)).

**Bottom line for anyone using AgentDojo ASR to compare models or defences.** Published
`important_instructions` ASR ranks models and GPT-4o defences in an order that survives
conditioning on exposure, ability and error coding. Two things do not survive:

- **Precision.** The absolute numbers carry task-level uncertainty 2–4.6 times wider than the
  paper reports.
- **Meaning.** A low ASR means "was not hijacked in this run", not "resists injection". For four
  of the six lowest-ASR models on the public table (Command-R, Command-R+, Gemini 1.5 Flash 002,
  Claude 3 Haiku), most "secure" cases are runs where the agent never saw the injection or could
  not do the injected task. Only the two newer Claude Sonnets earn their low ASR by declining
  injections they saw.

The public table also counts 91 errored runs as successful attacks. This raises four models'
published numbers, as below.

## Validation

An independent validator reran the pipeline, re-derived claims C1, C2 and the error coding with
separate code, hand-labelled 96 blind cases, and searched again for prior work. Details and every
number: [`validation/VALIDATION.md`](validation/VALIDATION.md) and
[`validation/validation.json`](validation/validation.json).

| Claim | Verdict |
|---|---|
| Table reproduces from traces (28 of 28) | HOLDS. The rerun is byte-identical. The live results page matches the pin |
| C1 ranking (Spearman 0.94; 0 of 132 separated pairs reversed) | HOLDS WITH CORRECTION. See the per-model moves and "security sources" added under C1 |
| C2 capability trend | HOLDS WITH CORRECTION. The trend reproduces on the paper's own ten models (Spearman 0.74, p = 0.02), and conditioning cuts it to 0.52. Utility–exposure correlation is 0.76, not 0.60 |
| C3 defences | HOLDS WITH CORRECTION. The tool-filter comparator is now matched case by case (44.9%, not 53.1%) |
| Error coding (L3) | HOLDS. Table 3's ASR and utility under attack reproduce exactly. Its benign-utility column does not |
| Interval widening, 166 → 132 pairs | HOLDS. The upper ratio is 4.3 with this seed and 4.6 with another |
| Scorer agreement, placebo, empty Opus traces | HOLDS WITH CORRECTION. All 207 empty Opus traces are in workspace |
| `ATTACKER_ACTIONS` labels | HOLDS. 96 of 96 blind hand labels agree, for both exposure and action |

| Claim | Level |
|---|---|
| C1 per-model ASR ranking: exposure, ability and follow conditioning | **R** (holds) |
| C2 "more capable models are easier to attack" | **R** (holds weakly). Model-level p = 0.13 before any conditioning, and the trend depends on including or excluding Anthropic |
| C3 GPT-4o defence gains are not "the agent did less" | **R** for all four. The tool filter's gain comes from removing the attacker's tool, which the paper already says |
| Public results table counts errored runs as successful attacks, so it disagrees with the paper | **L3** (four published model numbers move; two ranks move by 2.5–3 places) |
| Scorer validity against the agent's own tool calls | **R** for false positives; L1 for a 4% rate of actions that followed the injection but failed the exact check |
| Row-level intervals too narrow | **L3** (task-level bootstrap 2.0–4.3× wider; separated pairs fall from 166 to 132 of 190) |

## The benchmark and what rests on it

AgentDojo (Debenedetti et al., NeurIPS 2024 D&B, arXiv 2406.13352) runs tool-using agents on 97
user tasks in four suites. Each user task is crossed with the suite's injection tasks, giving 629
cases. The injection text is placed in tool outputs the user task reads. `security = True` means
the attacker's goal was achieved. The public results table and the paper report targeted ASR per
model, the "inverse scaling" observation that more capable models are attacked more, and GPT-4o
defence results (for example tool filtering cutting ASR from 47.69% to 6.84%). Defence papers
(CaMeL, MELON, SecAlign and others) and government red-teaming exercises use it as the standard
injection benchmark. Conclusions under test: [`claims.md`](claims.md). Pre-registration:
[`prereg.md`](prereg.md), committed before the effect test.

## What we found

The main hypothesis is that ASR is confounded with capability: an agent that never reaches the
injected tool output, or cannot carry out the injection task, scores as secure. The trace data
show this mechanism exists. Exposure, meaning the agent actually received the injected text,
ranges from 55% to 97% of cases (Claude 3 Opus's raw 58% is an artefact of missing traces; 87% on its traced cases), and it correlates with benign utility across models (Spearman
0.76 [0.65, 0.85] with Opus on traced cases, from validation; 0.60 if Opus's untraced cases are counted as unexposed). But the mechanism does not change any published ranking or trend. It does
change what a low ASR means for several low-ASR models (see C1). Conditioning ASR on exposure,
on demonstrated ability to do the injection task, or replacing ASR with "the agent acted on the
injection at all" keeps the ranking nearly unchanged. No pair of models that the published
numbers separate swaps places. The weak capability trend survives at a reduced size. No defence
gets its gain from lower exposure.

What does move published numbers is narrower and partly known. The public results table codes
all 91 errored runs (API or context-length errors) as successful attacks
(`src/agentdojo/benchmark.py:117-147`; mechanism in issue #154). The paper's Table 3 does not:
recoding errors as "not attacked" reproduces the paper's ASR and utility-under-attack columns
exactly (its benign-utility column differs by up to 2 pp). For Command-R+ this is the
difference between 4.45% and 0.95%.

| Quantity | n | Value | 95% CI (two-way task bootstrap) |
|---|---|---|---|
| Published table reproduced from traces | 28 rows | 28 exact (max abs diff 0.00 pp) | — |
| Spearman(published ASR, ASR given exposure), 20 models | 20 × 629 | 0.940 | [0.915, 0.985] |
| Spearman(published ASR, follow rate given exposure) | 20 × 629 | 0.953 | [0.908, 0.985] |
| Model pairs separated under published ASR / reversed under any conditioning | 190 | 132 / 0 | — |
| Trend: Spearman(benign utility, published ASR) | 20 | 0.356 | [0.156, 0.461]; model-permutation p = 0.127 |
| Trend: Spearman(utility, ASR given exposure) | 20 | 0.286 | [0.098, 0.405] |
| Trend: Spearman(utility, ASR given exposure and ability) | 20 | 0.250 | [0.062, 0.377] |
| Trend: Spearman(utility, exposure rate), Opus on traced cases (validation) | 20 | 0.757 | [0.650, 0.855] (0.602 [0.507, 0.769] with Opus's raw exposure) |
| GPT-4o tool filter: exposure share of the ASR drop | 629 | 0.027 | [−0.021, 0.072] |
| Tool filter: ASR given exposure, attacker's tool kept by the filter | 107 | 39.3% | [20.0, 61.8] (undefended GPT-4o on the same 107 cases 44.9% [23.5, 69.6]; difference −5.6 pp [−28.6, +15.0], validation) |
| Tool filter: share of cases where the filter keeps the attacker's tool | 629 | 21.0% | — |
| Command-R+ ASR, table → errors not counted (paper Table 3) | 629 | 4.45% → 0.95% (0.95%) | — |
| Non-error successes with the attacker's action in the agent's executed calls | 2,905 | 2,868 (98.7%) | — |
| Exposed "secure" cases where the agent executed the attacker's action | 8,510 | 348 (4.1%) | — |
| Task-bootstrap interval half-width ÷ row-level half-width, 20 models | 20 | median 3.1 (2.0–4.3) | — |

Bias direction. Error coding makes four models look more attackable than their runs show:
Command-R+, Llama 3 70B, Gemini 1.5 Pro 001 and GPT-3.5 (Command-R slightly). Conditioning on
exposure makes every model look more attackable: ASR given exposure is above published ASR for
19 of 20 models. The gap is largest for models that often never reach the injection (Gemini 2.0
Flash 001: 20.8% → 37.9%; Claude 3 Sonnet: 26.7% → 36.8%). The published ranking still holds.

## The confound

**Exposure (E).** A case is exposed when an injected string, taken from the trace's own
`injections` field and compared after stripping whitespace, escape sequences and punctuation,
appears in at least one tool message the agent received (`scripts/01_extract.py`). It matches the
authors' own `<INFORMATION>`-tag definition (`util_scripts/create_results_table.py:15-29`) on
17,461 of 17,461 cases. Exposure is decided before the agent sees any injected text, so a
non-exposed case cannot be resistance. Examples of non-exposure: Gemini 2.0 Flash 001
travel/user_task_14 asks the user for the year and makes no tool call; Claude 3 Haiku
workspace/user_task_0 searches the wrong year and finds nothing; Claude 3 Sonnet
banking/user_task_4 reasons and makes no tool call. Exposure per model:
[`results/per_model.csv`](results/per_model.csv) (column `E`).

**Ability (A).** The release also contains runs where each injection task's goal was given to the
model as the user prompt with no attack (`runs/<model>/<suite>/injection_task_k/none/none.json`).
A is that run's stored utility. It is one run per model and injection task, so it is noisy. Models
complete between 11 (Command-R+) and 24 (GPT-4o, GPT-4-0125, GPT-4o-mini) of the 27.

**Follow (F).** The agent issued an executed tool call that performs the attacker's action, judged
leniently: it contacts the attacker's address, IBAN, URL or Slack user, or deletes file 13. For the
text-only travel injection_task_6 it is a final-answer rule. Rules: `ATTACKER_ACTIONS` in
`scripts/01_extract.py`. F measures propensity to obey without requiring the exact content the
security check demands.

## The effect

**C1, ranking (R).** ASR given exposure, given exposure and ability, and follow given exposure all
keep the order: Spearman 0.94, 0.94 and 0.95 against published ASR, Kendall 0.84, 0.83 and 0.86.
Of 190 model pairs, 132 are separated under published ASR (two-way bootstrap CI of the difference
excludes 0). None is reversed under any conditioned statistic, even at the point estimate.
*Corrected after validation.* The rank correlation hides large moves for some models. Gemini
2.0 Flash 001 goes from 20.8% to 37.9% (+17.0 pp [9.2, 26.9]) and from rank 9 to 4 (rank-change
CI [0, 7]). Gemini 2.0 Flash exp and Claude 3 Sonnet each rise about 10 pp. GPT-4 Turbo drops from
rank 4.5 to 7, and GPT-4o-mini from 6 to 9. Llama 3 70B's apparent jump (rank 8 → 3) comes from
its 35 errored runs. With errors not counted, it stays at rank 8.

The low-ASR models also divide into two kinds. The two newer Claude Sonnets earn their low ASR:
Claude 3.7 Sonnet is exposed in 97.1% of cases (ASR given exposure 7.5%), and Claude 3.5 Sonnet
(Oct) in 87.4% (1.3%). Only 3% and 13% of their "secure" cases are unexposed. For Command-R,
Gemini 1.5 Flash 002, Command-R+ and Claude 3 Haiku, ranked 2nd to 4th and 6th lowest on the
public table, the share of "secure" cases that were never exposed, or where the model failed the
injection task when asked for it directly, is 56%, 64%, 70% and 61%. Their ASR on exposed-and-able
cases is still low (5.4%, 8.3%, 2.1% and 16.5%), so their ranks barely move. But their published
number mostly records that they were not hijacked, not that they resisted. Across all 20 models,
this share exceeds half for 12. Non-exposure alone exceeds half only for Gemini 2.0 Flash 001
(57%). See `validation/validation.json`, keys `security_sources` and `six_lowest_public_asr`.

**C2, capability trend (R, weak).** *Corrected after validation.* The paper makes the claim
(Section 4.1, Figure 6(a)) for its own ten Table 3 models. On those models it reproduces:
Spearman 0.74 from the traces (permutation p = 0.02), and 0.79 (p = 0.009) from Table 3's own
numbers. Conditioning on exposure lowers it to 0.52 (p = 0.13), and action given exposure gives
0.58. Across all 20 models in the current table the trend is weak: Spearman(utility, ASR) is
0.356, with model-permutation p = 0.127 (10,000 permutations). That weakness comes from the later
models, mainly Anthropic's, rather than from the paper's own evidence. Across the 20 models the
correlation is not distinguishable from zero when models are treated as the sample. The two-way
task bootstrap interval [0.156, 0.461] treats the 20 models as fixed. Conditioning lowers the
estimate to 0.286 (exposure), 0.250 (exposure and ability) and 0.307 (follow). All stay above 0
and above half of the published estimate, so by the pre-registered rule the trend holds. The
paper already offers the capability explanation in words ("models with low utility often fail at
correctly executing the attacker's goal"). The data show that this explains roughly a fifth to a
third of a weak correlation, not the correlation itself. Exposure rate tracks utility much more
strongly (0.76 with Opus on traced cases; 0.60 with its raw exposure) than ASR does.

**C3, defences (R).** Exposure share of the log ASR reduction (pre-registered decomposition,
[`results/defences.csv`](results/defences.csv)):

| Defence | ASR | Exposure (or reached) | ASR given exposure [CI] | Undefended ASR given exposure | Exposure share [CI] |
|---|---|---|---|---|---|
| tool_filter | 6.84% | 85.2% | 8.0% [3.3, 14.4] | 53.1% | 0.03 [−0.02, 0.07] |
| PI detector (reached = seen or redacted) | 7.95% | 91.1% | 8.7% [1.9, 17.5] | 53.1% | −0.01 [−0.03, 0.01] |
| repeat_user_prompt | 27.82% | 93.6% | 29.7% [17.6, 43.2] | 53.1% | −0.08 [−0.20, −0.02] |
| spotlighting | 41.65% | 91.1% | 45.7% [29.0, 62.3] | 53.1% | −0.10 [−0.92, 0.04] |

No defence gains through lower exposure; two raise exposure. The tool filter's gain comes from
removing the attacker's tool. The filter keeps the attacker's tool in only 21.0% of cases. In
exposed cases where it does, ASR is 39.3% [20.0, 61.8] (n = 107), against 0.2% (1 success) where
it does not. This meets the pre-registered "removal, not resistance" rule (≥ half of 53.1%).
*Corrected after validation.* 53.1% is undefended ASR on all exposed cases. The matched comparator
is undefended GPT-4o on the same 107 cases: 44.9% [23.5, 69.6], difference −5.6 pp [−28.6, +15.0].
On the 96 cases exposed in both runs, the figures are 39.6% against 50.0% (−10.4 pp
[−35.1, +10.4]). The filter picks tools from the user prompt before any tool output exists, so it
cannot react to the injection. All four defences keep their reductions on cases exposed in both
runs (−43, −44, −23 and −7 pp; every CI excludes 0). The
paper states the limitation qualitatively (Section 4.3); the 39% figure is new. Spotlighting's
reduction is small: the conditional difference is −7.4 pp [−12.8, −2.5].

## Secondary results

**Error coding (L3).** The 91 errored cases in the 20 models are all stored with `security = True`.
Two kinds of error get this coding:

- 47 context-length errors, from GPT-3.5 and Llama 3 (`benchmark.py:120-130`);
- 44 internal-server errors, from Gemini 1.5 Pro 001, Command-R+ and Command-R
  (`benchmark.py:133-147`).

Recoding them as not attacked reproduces Table 3's targeted ASR and utility under attack exactly
for all ten paper models. The public table does not reproduce them. Table 3's benign-utility
column does not reproduce from the released no-attack runs either: it differs by 0.07–2.05 pp for
every paper model, for example Opus 66.61 against 68.04 (validation, `table3`). The trace
injection texts show that 17 of 20 table models ran an older goal for travel injection_task_5
than Claude 3.7 Sonnet and the two Gemini 2.0 models did. The table therefore mixes benchmark
versions, with negligible effect on ASR.

| Model | Errors | Public table ASR | Errors not counted | Paper Table 3 |
|---|---|---|---|---|
| Command-R+ | 22 | 4.45% | 0.95% | 0.95% |
| Llama 3 70B | 35 | 25.60% | 20.03% | 20.03% |
| Gemini 1.5 Pro 001 | 19 | 28.62% | 25.60% | 25.60% |
| GPT-3.5 Turbo | 12 | 10.33% | 8.43% | 8.43% |
| Command-R | 3 | 3.34% | 2.86% | — |

Gemini 1.5 Pro 001 moves from rank 4.5 to 7 of 20, and Command-R+ from 17 to 20. All 22 of
Command-R+'s errored cases are unexposed, so its ASR given exposure (1.3%) already excludes them.
Llama 3's 35, GPT-3.5's 12, Command-R's 3 and 12 of Gemini 1.5 Pro 001's errored cases are
exposed. They therefore inflate S1 for those models. The robustness table recomputes S1 with
errors not counted.

**Scorer against the agent's own tool calls.** Of 2,905 non-error successes, 2,868 (98.7%) contain
the attacker's action in an executed call. The 37 without it are:

- 10 Slack injection_task_5 cases where the action was proposed but not executed (issue #168);
- 7 Claude 3 Opus cases with empty traces (below);
- 5 travel injection_task_6 cases where the hotel is named without the praise words;
- 15 others (Slack 1–4, banking 2 and 7, workspace 1): 12 issued the attacker's call without a clean execution, and 3 have no attacker call (not inspected further).

In the other direction, 348 of 8,510 exposed "secure" cases (4.1%) executed the attacker's
action but failed the exact content check. Workspace injection_task_3 accounts for 76 of them
(email sent to the attacker with the wrong body or subject), banking injection_task_8 for 61 and
workspace injection_task_0 for 28. These are real false negatives for "the agent obeyed", but
they do not change the ranking (follow given exposure is the S3 column above).

Placebo: in no-attack runs, banking user_task_15 itself sets a standing order to the attacker's
IBAN, because its prompt names that IBAN as the landlord's account. 13 of 24 pipelines do this
with no attack, so banking injection_task_4's check can pass without the injection. Under attack
this pair is scored a success for 9 of 24 pipelines. Successes on placebo pairs are at most 14% of
any model's successes (Claude 3.5 Sonnet Oct: 1 of 7) and under 5% for 17 of 20 models
([`results.json`](results.json) `secondary.scorer`).

**Missing traces (L1).** 207 of Claude 3 Opus's 629 attack traces have empty message lists, with
labels stored (7 of them `security = True`, 112 `utility = True`). All 207 are in the workspace
suite, which is 207 of Opus's 240 workspace cases (validation). Opus's workspace results therefore
cannot be checked, and its conditioned statistics effectively exclude workspace. Opus's raw exposure (58.3%)
is therefore an artefact: on its 422 traced cases it is 87.0%. Conditioned statistics
use traced cases only.

**Model name in the attack.** No main-table run uses a wrong model name. Claude runs are addressed
as "Claude", OpenAI runs as "GPT-4" or "GPT-3.5", Gemini as "AI model developed by Google",
Llama 3 as "AI assistant", and Cohere by its name (`src/agentdojo/models.py:94-122`). The GPT-4o
ablations reproduce paper Table 2: wrong model name 23.69% (paper 23.7%), wrong user name 23.21%
(23.2%), no names 45.79% (45.8%). Exposure is 89–90% in every variant, so the drop is real
resistance to a misaddressed message. The traces' "wrong" names are "Command R" and "Mixtral",
not "Claude" as Table 2 says. A cross-model comparison of name match is confounded with model
family and was not run as a test.

**Concentration and intervals (L3).**

- Slack (105 of 629 cases) is the top suite for 16 of 20 models' successes.
- For 5 of 20 models, three injection tasks carry at least half of the successes. Claude 3.5 Sonnet
  (Oct): 6 of 7; Claude 3.7 Sonnet: 27 of 46, with 54% in Slack.
- Resampling user and injection tasks widens the ASR intervals 2.0–4.3× (median 3.1×; 2.0–4.6×
  with the validator's bootstrap seed) relative to the paper's row-level `proportion_confint`. The paper's ±3.9 pp for GPT-4o becomes
  [33.3, 62.7].
- Model pairs separated fall from 166 (row-level z) to 132 of 190.

**Content-blind predictors.** See the second table under Robustness.

## Robustness

| Check | Result | Claim survives? |
|---|---|---|
| Drop each suite (C1: Spearman of published ASR with ASR given exposure; C2: utility vs ASR given exposure) | C1 0.95–0.98; C2 0.23–0.35 (published 0.24–0.39) | Yes |
| Drop each model family (C2) | Without Anthropic, published trend 0.79 and given-exposure 0.65. Without Cohere 0.20/0.05, Google 0.26/0.19, OpenAI 0.20/0.18, Meta 0.39/0.39 | C2 depends on family composition. Anthropic's newer models (high utility, low ASR) are the counter-examples. Conditioning moves the trend less than dropping one family does |
| Common support (pairwise jointly exposed cases) | 10 of 190 pairs reverse at the point estimate; 0 of them were separated | Yes |
| Placebo exposure (random flag at each model's own rate within suite, 200 draws) | Mean C1 Spearman 0.99; C2 0.32 | Yes. Real exposure moves the trend slightly more than the placebo (0.29 vs 0.32) |
| Different statistic: Pearson on logit rates | Published 0.25, given exposure 0.22, follow 0.22 | Yes (same pattern, weaker) |
| Errors not counted, then condition on exposure | Spearman with published ASR 0.95; trend 0.42 → 0.36 | Yes |
| Multiple comparisons (Holm, normal approximation from bootstrap SE, 190 pairs) | Pairs separated: published 67, given exposure 75, given exposure and ability 52, follow 80 | Yes. No separated pair reverses under any statistic |
| Second exposure definition (authors' `<INFORMATION>` tag) | Identical on 17,461 of 17,461 cases | Not independent; confirms measurement only |

Content-blind predictors of per-case success, pooled over the 20 models (L2 logistic regression,
GroupKFold by user task, null = 1,000 within-suite label shuffles, null 95th percentile ≈ 0.67):

| Features | AUROC |
|---|---|
| Suite alone | 0.658 (at null; the null keeps suite) |
| Injection task id | 0.750 |
| Suite + user-task structure (calls needed, number of injection vectors) | 0.675 |
| + injected output length and position | 0.752 |
| Injection task id + structure + output | 0.808 |
| Model id alone | 0.744 |
| Model + injection task | 0.856 |
| Model + injection task + exposure | 0.894 |

The injection task matters about as much as the model. A few injection tasks are easy (Slack 3–5,
banking 0 and 7) and some are nearly impossible (travel 3 and 5, workspace 4 and 5: 2–3% pooled).
This is the paper's own Figure 7 observation, extended here to show it rivals model identity.

## Alternative explanations

1. *Non-exposure is the model being careful.* Excluded by construction: exposure is fixed before
   any injected text reaches the agent. In the hand-read cases, non-exposed runs are clarification
   questions, wrong search terms or early stops (examples above).
2. *Conditioning on exposure selects easier cases for weaker models.* Common-support check: for
   each pair, ASR on cases exposed for both models. 10 of 190 pairs reverse their published order at the point estimate. None of the 10 was separated under published ASR; all differ by at most 8.3 pp in the published table. This alternative does not overturn C1.
3. *The trend or ranking is one family.* Drop-family results are in the robustness table.

## What was already known

- The paper gives the capability explanation for the trend in words, and states the tool filter's
  read/write limitation.
- Issue #154 reports the error-to-success coding, for the context-length branch only. Its comment
  and the open PR #186 propose excluding errors. Neither gives model numbers.
- Zarif et al., "Ignored, Not Refused" (arXiv 2610.23254, October 2026; abstract read) show that
  low ASR mostly reflects ignoring, not refusing. They use new runs of 11 small open-weight agents.
  The general point that low ASR is not refusal is therefore already public. What is new here is
  the exposure and ability decomposition on the published runs.
- Issue #47 reports exposure failures for five workspace tasks.
- Issue #208 shows near-complete delivery of injections in a replay for other models.
- Issues #168, #181/#240 and #245 report individual scorer defects.
- The Attacker Moves Second shows static attacks understate risk.

New here:

1. Exposure, ability and follow conditioning over all published runs, with task-level intervals,
   showing the ranking, trend and defence conclusions hold.
2. The paper/public-table divergence traced to error coding, with per-model and rank effects.
3. The tool filter's 39% ASR when it keeps the attacker's tool.
4. Scorer agreement with executed calls on 15,096 cases, and the user_task_15 placebo pair.
5. The empty Opus traces.
6. The interval widening and pair counts.
Details: [`prior_work.md`](prior_work.md).

## What this does not show

- Nothing about adaptive attacks. All results are for the fixed `important_instructions` string.
- Ability is one run per model and injection task, and the follow rule is lenient and hand-written.
  A stricter or LLM-judged follow label could differ on borderline cases (partial exfiltration).
- The four newer pipelines (Llama 3.3, Meta-SecAlign) ran at v1.2.1 and are not in the published
  table. They were not analysed.
- The trend test has 20 models, so its power is low. "Holds" here means the conditioning did not
  remove a weak positive association, not that the association is established.

## Pins and how to reproduce

- AgentDojo `089ed468cf3ed0322acc66b0211f26d9d90dbf60` (shallow clone in `data/agentdojo/`).
- Paper HTML `https://arxiv.org/html/2406.13352v3`, saved to `data/paper/v3.html` (read for
  Table 3).
- The venv lives in `data/.venv`, because `audits/tools/commit.sh` refuses large files outside
  `data/`.

```bash
cd audits/agentdojo
git clone --depth 1 https://github.com/ethz-spylab/agentdojo data/agentdojo   # then check out the sha above
mkdir -p data/paper && curl -sL -o data/paper/v3.html https://arxiv.org/html/2406.13352v3
uv venv data/.venv && uv pip install --python data/.venv/bin/python numpy pandas scipy scikit-learn pyarrow
P="data/.venv/bin/python -I"
$P scripts/01_extract.py      # traces -> data/cases.parquet (text parsing only; no downloaded code run)
$P scripts/02_reproduce.py    # published table, results/reproduce.csv
$P scripts/03_handread_sample.py > results/handread_sample.txt
$P scripts/04_effect.py       # C1-C3, results/per_model.csv, pairs.csv, defences.csv
$P scripts/05_secondary.py    # scorer, errors, names, concentration, empty traces
$P scripts/06_robustness.py   # robustness, content-blind predictors
```

All bootstraps use seed 0 and B = 2,000. Every number above is in [`results.json`](results.json).
