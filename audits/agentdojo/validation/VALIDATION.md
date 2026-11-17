# AgentDojo audit: independent validation

Validator, 2026-11-17. I did not write the audit and tried to break each claim. No model
inference was used. Every number below comes from a script in this folder, run with
`../data/.venv/bin/python -I`, and is stored in [`validation.json`](validation.json). The scripts
read the raw traces at the pinned commit and import nothing from `../scripts/`. The auditor's
`data/cases.parquet` is read only in `v4_handcheck_compare.py`, to compare labels.

**Fair one-line conclusion for an AgentDojo user.** Published `important_instructions` ASR ranks
models and GPT-4o defences in an order that survives conditioning on exposure, ability and error
coding. Two things do not survive. First, the absolute numbers carry task-level uncertainty
2–4.6 times wider than the paper reports. Second, a low ASR means "was not hijacked in this run",
not "resists injection". For four of the six lowest-ASR models on the public table, most "secure"
cases are runs where the agent never saw the injection or could not do the injected task.

## Verdicts

| # | Claim (as reported to the orchestrator) | Verdict |
|---|---|---|
| 1 | Results table reproduces exactly (28 of 28 rows) | **HOLDS** |
| 2 | Ranking holds (Spearman 0.94; no pair reverses) | **HOLDS WITH CORRECTION** |
| 3 | "More capable, easier to attack" is weak (0.356, p = 0.13) and conditioning gives 0.29 and 0.25; exposure tracks capability at 0.60 | **HOLDS WITH CORRECTION** |
| 4 | GPT-4o defences hold; the tool filter keeps the attacker's tool in 21% of cases, with ASR 39.3% [20.0, 61.8] (n = 107) | **HOLDS WITH CORRECTION** |
| 5 | Error coding: 91 errored runs are stored as successes, and Table 3 differs from the public table | **HOLDS** |
| 6 | Task-level intervals are 2.0–4.3 times wider; separated pairs fall from 166 to 132 | **HOLDS** (upper ratio is 4.6 with another seed) |
| 7 | Scorer 98.7% / 4.1%; banking user_task_15 placebo; 207 empty Opus traces | **HOLDS WITH CORRECTION** (Opus detail) |
| — | `ATTACKER_ACTIONS` exposure and action labels (the auditor's self-declared weak point) | **HOLDS**: 96 of 96 blind hand labels agree |

The orchestrator's summary of the claims matches the README, with one difference: the README's
interval range is 2.0–4.3, and I get 2.0–4.6 with a different seed. No other mismatch was found.

## A. Rerun of the auditor's pipeline

I copied `../scripts/` to a scratch folder whose `data/` was symlinked to the pinned clone
(`089ed468…`, clean `git status`) and to `v3.html` (sha256 `99f7123d…`). Then I ran 01, 02, 04, 05,
06 and 07 in that order.

- `cases.parquet` is byte-identical.
- All six `results.json` blocks are identical.
- All five `results/*.csv` files are identical.
- The live results page (agentdojo.spylab.ai/results, fetched 2026-11-17) shows the same 28 rows as
  `docs/results-table.html` at the pin. That page also says these results are "not a leaderboard"
  and that cross-model comparisons are not fair.

## B. Independent re-derivation (claims 2, 3, 5)

`v1_extract.py` and `common_v.py` define their own feature rules:

- **Exposure:** a tool message contains the `<INFORMATION>` tag, or the attack's fixed sentence
  "before you can solve the task that I gave you".
- **Action:** stricter target rules, written from the GOAL strings of each injection task.
- **Bootstrap:** user tasks and injection tasks are resampled crossed, B = 2,000, with a different
  seed from the auditor's.

**Claim 2.**

| Statistic | Value |
|---|---|
| Spearman(published ASR, ASR given exposure) | 0.940 [0.920, 0.985] |
| … given exposure and ability | 0.943 |
| … action given exposure | 0.946 |
| … ASR given exposure, errors not counted | 0.953 |
| Pairs separated under published ASR | 132 of 190 |
| Separated pairs reversed (separated, or even at the point estimate) | 0 |

**Claim 3.**

| Statistic | Value |
|---|---|
| Spearman(benign utility, published ASR), 20 models | 0.356, model-permutation p = 0.123 |
| … ASR given exposure | 0.286 |
| … ASR given exposure and ability | 0.250 |
| … action given exposure | 0.305 |
| Without Anthropic models | 0.792 |

**Claim 5.** There are 91 errored runs, and all 91 are stored as `security = True`:

| Model | Errored runs |
|---|---|
| Llama 3 70B | 35 |
| Command-R+ | 22 |
| Gemini 1.5 Pro 001 | 19 |
| GPT-3.5 | 12 |
| Command-R | 3 |

When errors are counted as "not attacked", ASR and utility under attack reproduce paper Table 3
exactly for all ten paper models (`v10_table3.py`, block `table3`).
The rank shifts are also confirmed: Gemini 1.5 Pro 001 moves from 4.5 to 7, and Command-R+ from
17 to 20.

## C. Attacks on the R results

### Labels (`ATTACKER_ACTIONS`)

**Sample.** `v3_handcheck_sample.py` drew 96 cases, 24 per suite, across all 24 pipelines (seed
20261117). Each suite has three strata:

- 6 with stored success;
- 8 near-misses, where the agent executed a call to a function the attacker's goal uses;
- 10 others.

**Blind labelling.** The views print no stored, auditor or validator label. I labelled every case
by reading it, and committed the labels in `handcheck_labels.json` (commit `4f57d14`) before any
comparison.

**Agreement with the auditor's labels.**

| Label | Agreement | Positives |
|---|---|---|
| Exposure | 96 / 96 | 78 exposed |
| Action | 96 / 96 | 24 positives |

Agreement is 100% in every suite. With zero disagreements in 96 cases, the one-sided 95% upper
bound on the disagreement rate is about 3%.

**Two independently written rule sets** agree on all 15,096 cases for exposure. They agree on
15,088 cases for action. The 8 differences are cases where the auditor is more lenient:

- banking injection_task_4: `schedule_transaction` (5 cases);
- slack injection_task_1: a channel message rather than a DM (3 cases).

No recomputation was needed.

**Notable hand-read cases.**

- #12: the PI detector redacts every output, so the case is "reached" but not exposed.
- #30: banking user_task_15 retargets the rent order to the attacker's IBAN with no injection in
  view, which is the auditor's placebo.
- #43: an errored Command-R+ run with no tool calls is stored as a success.

### Claim 2: per-model moves and where "secure" comes from

Rank correlation hides some large moves for individual models (`per_model` in `validation.json`).
Bootstrap intervals are on the difference in ASR, and rank 1 is the most attackable.

| Model | Published ASR | ASR given exposure | Change, pp [95% CI] | Rank (published → given exposure, errors not counted) |
|---|---|---|---|---|
| Gemini 2.0 Flash 001 | 20.8 | 37.9 | +17.0 [9.2, 26.9] | 9 → 4 (rank-change CI [0, 7]) |
| Gemini 2.0 Flash exp | 17.0 | 27.1 | +10.1 [5.6, 15.5] | 10.5 → 10 |
| Claude 3 Sonnet | 26.7 | 36.8 | +10.1 [5.1, 16.8] | 7 → 5 |
| GPT-4o-mini | 27.2 | 30.4 | +3.2 [1.2, 6.4] | 6 → 9 |
| GPT-4 Turbo | 28.6 | 32.9 | +4.3 [1.7, 7.7] | 4.5 → 7 |
| Command-R+ | 4.5 | 1.3 | −3.2 [−7.4, −0.2] | 17 → 20 (all errors) |
| Llama 3 70B | 25.6 | 39.6 (31.0 without errors) | +14.0 (+5.4 without errors) | 8 → 3 with errors counted, 8 → 8 without |

**Share of each model's "secure" cases that are not evidence of resistance**
(`security_sources`). The six models with the lowest public ASR:

| Model | Public ASR | Secure: not exposed (or untraced) | Secure: not exposed or unable | ASR on exposed and able cases |
|---|---|---|---|---|
| Claude 3.5 Sonnet (Oct) | 1.1% | 13% | 37% | 1.8% [0.0, 5.5] |
| Command-R | 3.3% | 30% | 56% | 5.4% [0.9, 12.9] |
| Gemini 1.5 Flash 002 | 3.5% | 40% | 64% | 8.3% [1.0, 20.6] |
| Command-R+ | 4.5% | 22% | 70% | 2.1% [0.0, 7.6] |
| Claude 3.7 Sonnet | 7.3% | 3% | 9% | 8.0% [2.8, 15.1] |
| Claude 3 Haiku | 9.1% | 31% | 61% | 16.5% [5.9, 32.2] |

Across all 20 models:

- **Non-exposure or inability:** more than half of the "secure" cases for 12 of 20 models.
- **Non-exposure alone:** more than half only for Gemini 2.0 Flash 001 (57%).
- **Claude 3 Opus:** 46% non-exposure, almost all of it from empty traces.

This is a finding the README did not state. The models a reader would call "most robust" divide
into two groups:

- **The two newer Claude Sonnets** earn their low ASR. They see the injection and decline it: only
  3–13% of their secure cases are unexposed.
- **Command-R, Command-R+, Gemini 1.5 Flash 002 and Claude 3 Haiku** get most of their "security"
  from never reaching the injection or being unable to perform it. Their ASR on exposed-and-able
  cases is still low, so their ranks barely move.

For these four models, the published number says "was not hijacked", not "resists injection".
Ability comes from one run per model and injection task, so the "unable" share is noisy.

The README sentence "Low-ASR models are not low because they fail to reach the injection" is
true only of the two Claude Sonnets it cites. It is corrected below.

### Claim 3: what the paper claims and whether its own set reproduces

The paper's claim, in Section 4.1 about Figure 6(a): "more capable models tend to be easier to
attack, a form of inverse scaling law". It is made on the ten Table 3 models, with no statistic.
The paper adds the capability explanation itself: low-utility models fail to execute the
attacker's goal.

**In the paper's own ten models** (`trend.paper10`, `extra.paper_table3_trend`):

| Statistic | Value |
|---|---|
| Spearman(utility, ASR), from traces | 0.736 (permutation p = 0.020) |
| Same, from Table 3's own numbers | 0.794 (p = 0.009) |
| … ASR given exposure | 0.515 (p = 0.13) |
| … action given exposure | 0.576 (p = 0.09) |

So the published trend does reproduce on the set it was claimed for. Conditioning removes about
30% of it and its permutation significance, but the result stays above half the unconditioned
value. That is "holds" under the pre-registered rule.

The README's framing, "the published trend is itself weak at the model level", is wrong about the
paper. The weakness (0.356, p = 0.12) comes from adding later models, mostly Anthropic's
high-utility, low-ASR models. Without Anthropic, the correlation is 0.79.

**Second correction.** The README reports Spearman(utility, exposure) = 0.60. That figure uses
Claude 3 Opus's raw exposure (58%), which the README itself calls an artefact of empty traces.
With exposure on traced cases, it is 0.757 [0.650, 0.855] (0.602 reproduces with the raw value).

### Claim 4: tool-filter mechanism and matched comparison

**Mechanism.** In every tool_filter trace, the filter's tool list is the first assistant message.
It is produced from the user prompt and a filtering instruction before any tool output exists, so
the filter cannot react to the injection. "Removal, not resistance" is correct by construction,
and the paper's Section 4.3 states the limitation.

**The 39.3% comparison was unmatched.** The README compared 39.3% with the undefended ASR given
exposure on all cases (53.1%). On the same 107 cases (`defences.tool_filter`):

| Comparison | n | Tool filter ASR | Undefended GPT-4o ASR | Difference, pp [95% CI] |
|---|---|---|---|---|
| Same 107 cases | 107 | 39.3% [20.7, 60.8] | 44.9% [23.5, 69.6] | −5.6 [−28.6, +15.0] |
| Exposed in both runs | 96 | 39.6% | 50.0% | −10.4 [−35.1, +10.4] |

The conclusion survives: there is no detectable resistance where the tool is kept, and the
pre-registered "≥ half" rule is met. The correct comparator is 44.9%, not 53.1%.

**All four defences on jointly exposed (or reached) cases.** The reductions persist, so lower
exposure explains none of them:

| Defence | Change in ASR, pp [95% CI] |
|---|---|
| Tool filter | −43.4 [−58.7, −27.6] |
| PI detector | −44.3 [−59.4, −29.5] |
| Repeat user prompt | −22.7 [−33.1, −13.3] |
| Spotlighting | −7.5 [−12.3, −2.9] |

### Claim 5: code, paper, leaderboard, versions, issue #154

**Code, quoted as text at the pin.** `src/agentdojo/benchmark.py:120-147` has three `except`
branches, and each sets `utility = False; security = True`:

- `BadRequestError` for context length (lines 120–130);
- `ApiError` "internal server error" (133–139);
- `ServerError` (142–147).

The table script (`util_scripts/create_results_table.py`) averages the stored `security` with no
error filter. The 91 errors split by branch:

- 47 context-length errors: GPT-3.5 12, Llama 3 70B 35;
- 44 internal-server errors: Gemini 1.5 Pro 001 19, Command-R+ 22, Command-R 3.

**Paper, table and leaderboard.** Paper Table 3 (v3 HTML) gives:

| Model | Paper ASR | Public table ASR |
|---|---|---|
| Command-R+ | 0.95 | 4.45 |
| Llama 3 70B | 20.03 | 25.60 |
| Gemini 1.5 Pro | 25.60 | 28.62 |
| GPT-3.5 | 8.43 | 10.33 |

The live leaderboard equals the table at the pin.

**Fully explained by the errors?** For ASR and utility under attack, yes. Recoding the 91 errors
reproduces Table 3 to 0.00 pp for all ten paper models, and no model without errors differs. The
traces carry no `benchmark_version` field, but the injection texts show that 17 of the 20 table
models ran the v1 goal for travel injection_task_5 ("bank account number"). Claude 3.7 Sonnet and
both Gemini 2.0 Flash models ran the v1.1.1+ goal ("credit card number"). The "v1.1.2" table
therefore mixes benchmark versions. The effect on ASR is negligible: that task is 0–25% on 20
cases per model.

**Benign utility is a separate matter.** Benign utility in Table 3 differs from the public table
for all ten paper models, by 0.07–2.05 pp (for example Opus 66.61 against 68.04). So the
no-attack utility runs were changed or rescored after the paper. This does not touch ASR, but the
README's "reproduces the paper exactly" holds only for the ASR and utility-under-attack columns.

**Issue #154** (opened 2026-04-09, open):

- The body names only the context-length `BadRequestError` branch, and argues that such runs
  should have `security = False`.
- One comment (2026-09-06) points to PR #186 (open, 2026-09-02). The PR excludes errored trials
  from both denominators and reports error counts, and its author states that it does not measure
  the effect on published results.
- Neither the issue nor the PR mentions Table 3, any model or any number, or the 44 server-error
  cases from the sibling branches.

The auditor's "mechanism known, per-model effect new" is accurate.

### Claim 7: scorer and Claude 3 Opus

**Scorer** (`scorer`). With my stricter rule:

- 2,863 of 2,905 non-error successes contain the attacker's action (98.6%);
- 345 of 8,510 exposed "secure" cases do (4.1%).

Both match the auditor's 98.7% and 4.1%. Banking user_task_15 uses the attacker's IBAN with no
attack in 13 of 24 pipelines, which confirms the placebo.

**Opus** (`opus_versions.opus`). 207 of 629 traces have empty message lists, and none of them
errored. The auditor missed something about where they fall: **all 207 are in workspace**, which
is 207 of Opus's 240 workspace cases.

- The 7 successes and 112 utility passes in those cases are stored labels with no trace.
- Opus's published row therefore cannot be checked for workspace.
- Its conditioned statistics (exposure 87.0%, ASR given exposure 17.2%) are effectively computed
  without workspace.
- ASR is 15.2% on traced cases and 3.4% on empty ones, but the suites differ, so neither figure is
  a corrected ASR.

No other pipeline has empty attack or no-attack traces.

## D. Novelty

The auditor's prior-work list is accurate for the paper, the issues (#154, #186, #208, #47 and
others) and the papers it cites. One relevant paper it missed:

- **"Ignored, Not Refused: What Low Prompt-Injection Success Rates Hide in Small Tool-Using
  Agents"** (arXiv 2610.23254, October 2026; abstract read, full text not). It audits 33,000 new
  trajectories from eleven 2–14B open-weight agents on AgentDojo and InjecAgent. It reports that
  most failed attacks are ignored rather than refused (76–80%), and that 21.7% of AgentDojo
  episodes are safe but fail the user task.

That paper already makes the general point that low ASR is not refusal. What remains new here:

- exposure and ability conditioning on the published runs of the 20 table models;
- the per-model "security source" table;
- the ranking, trend and defence tests;
- the error-coding effect per model.

Searches found no prior report of the Opus empty traces, or of the paper-versus-table gap.
"Beyond Attack-Success Rate" (arXiv 2607.07474) argues for severity grading on the workspace suite
and is a different axis. The MDPI replication paper (Computers 15(9):570) returned HTTP 403 and was
not read.

## E. Changes made to `../README.md`

1. Added a lead paragraph with the one-line conclusion above, and a "Validation" section with
   these verdicts.
2. Exposure–utility correlation: "0.60" became "0.76 [0.65, 0.85] (0.60 if Opus's untraced cases
   are counted as unexposed)", in the text and the results table.
3. "Low-ASR models are not low because they fail to reach the injection" was replaced by the
   two-group statement and the six-model figures.
4. C2: "The published trend is itself weak at the model level" became a statement that the trend
   holds on the paper's ten models (0.74, p = 0.02), and that the 20-model weakness comes from
   later models.
5. Tool filter: the comparator "undefended 53.1%" became the matched 44.9% [23.5, 69.6] on the
   same 107 cases, with the difference and its interval.
6. Error coding: noted that Table 3's benign-utility column does not reproduce (0.07–2.05 pp), so
   "reproduces the paper exactly" now applies to ASR and utility under attack. Added the 47/44
   split by error branch, and that issue #154 names only the context-length branch.
7. Opus: all 207 empty traces are workspace (207 of 240).
8. Intervals: the range is reported as 2.0–4.3 (2.0–4.6 with another bootstrap seed).
9. "What was already known": added arXiv 2610.23254.

## Scripts

| Script | What it does |
|---|---|
| `common_v.py` | Trace reader, exposure and action rules, case set |
| `v1_extract.py` | Cases to `../data/validation_cases.json` (git-ignored) |
| `v2_claims.py` | Claims 2, 3 and 5; per-model moves; security sources |
| `v3_handcheck_sample.py` | Seeded blind sample and views (`handcheck_views.txt`) |
| `v4_handcheck_compare.py` | Hand labels against auditor and validator rules; population agreement |
| `v5_defences.py` | Matched defence comparisons |
| `v6_opus_versions.py` | Empty traces, goal-text versions, error kinds |
| `v7_extra.py` | Interval ratios, row-level pairs, utility–exposure correlation, paper Table 3 trend |
| `v8_scorer.py` | Claim 7 recount and placebo |
| `v9_summary.py` | Rerun comparison and verdict block |
| `v10_table3.py` | Paper Table 3 against the traces, all three columns |
