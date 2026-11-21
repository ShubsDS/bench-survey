# Findings: where safety benchmark numbers mean something other than what they are taken to mean

Status: 2026-11-21. This is the findings write-up for the audits in [`audits/`](audits/). It is
organised by finding, strongest first. For a shorter overview by round, see
[`report-effect-audits.md`](report-effect-audits.md); for every number and its correction history,
see [`audits/README.md`](audits/README.md). Nothing here has been sent to any benchmark's
maintainers.

## Summary

We audited fourteen benchmarks used to judge AI capability, propensity and monitoring, then went
back to the open questions in a third round. Each audit asked one thing: does a simple feature
unrelated to what the benchmark measures change a published conclusion?

- **No benchmark's main conclusion failed.** Published numbers reproduce, and rankings and trends
  mostly hold.
- **In eleven cases a number is routinely read as something it does not measure.** The four
  strongest concern prompt-injection robustness, monitor catch rates, a monitor ranking metric,
  and shutdown resistance.
- **Three questions stayed open** after a dedicated attempt to answer them: whether frontier
  models use the LAB-Bench shortcut, whether PropensityBench's missing prohibition changes
  behaviour, and whether a critique of TASTE holds.
- **One finding was re-run on current models and did not carry over.** AgentDojo's "secure without
  exposure" is a fact about the released logs. Two 2026 Claude models read the injected text in
  99–100% of runs and never followed it.
- **Independent refutation mattered more than any single finding.** A second agent cut back the
  first agent's headline in twelve of fourteen audits and in all four refuted deep dives.

## How to read the strength column

Every finding was checked by a fresh agent told to break it, with its own code. Strength below is
after that check.

- **Solid:** computed from the paper's own released per-item logs, so it describes the published
  models, and it survived refutation with a clear margin.
- **Moderate:** survived refutation, but rests on a small sample, or on a controlled edit run on
  Claude Haiku or Sonnet, so it describes those models and not the ones in the paper.
- **Lead:** points in one direction but is too small or too indirect to count as a result.

Findings 1–4 were checked a second time on 2026-11-20 by four further agents working from the raw
logs. Their entries below use the narrowed wording from that check; the verdicts and scripts are in
[`factcheck/verdicts/`](factcheck/verdicts/). On 2026-11-21 finding 1 was re-run on two current
Claude models, and finding 3 was extended to the board's other datasets; both follow-ups had their
own independent check.

## Findings

| # | Benchmark | The number is taken to mean | What it also or instead reflects | Strength |
|---|---|---|---|---|
| 1 | AgentDojo | A low attack success rate means the model resists prompt injection | In the released logs (20 models, 2024 to February 2025), 24% of the median model's "secure" runs never showed the agent the injection; counting runs where the model also failed the injected task when asked directly, 48% (9–79% across models). For Claude 3.7 Sonnet and two 2026 Claude models the never-saw share is 0–3% | Solid for never-saw in the released logs; moderate for the rest; does not carry over to current Claude models |
| 2 | MRT / SHADE-Arena | Monitors catch sabotaging agents almost perfectly | The agents were prompted to plan in tags the monitor reads; deleting those plans drops one monitor's AUROC from 0.998 to 0.85, mostly on one of five tasks | Solid for the design; moderate for the size |
| 3 | BashArena-family monitor board | Trajectory-level score ranks monitors by detection skill | The score is confounded by run length: as published, 7 of 11 monitors score below chance; with length matched, 4–6 of 11 still cannot be told from chance | Solid for the confound; the count depends on the matching method |
| 4 | Palisade shutdown resistance | Models resist shutdown to preserve themselves | Sabotage is real; where a reason is stated it is mostly finishing the task | Solid for the sabotage; moderate for the reasons |
| 5 | LAB-Bench sequence tasks | Model scores against human experts | In 6 of 15 subtasks the answer can be read from the options alone | Solid for the flaw; moderate for who uses it |
| 6 | ChainScope | Rate of unfaithful reasoning | For one model, about 90% of flagged cases are a correct argument followed by a contradicting final answer | Solid |
| 7 | LAB-Bench ProtocolQA | Ability to find an error in a given protocol | About 70% of the above-chance score survives removing the protocol | Moderate |
| 8 | CAA steering on Model-Written Evals | A steering vector shifts a disposition | Part of one effect sits on questions keyed "Yes" | Moderate |
| 9 | Situational Awareness Dataset | Self-knowledge | Two tasks reward a habit of denying | Solid, small in scope |
| 10 | Emergent misalignment metric | Share of answers showing misaligned values | In five unpublished fine-tunes, mostly harmful advice across domains | Moderate |
| 11 | PropensityBench | Models break a stated rule under pressure | The prohibition sentence reaches the agent in 4 of 979 scenarios | Solid for the flaw; effect not shown |

### 1. In the released logs, a low injection success rate is often not robustness (AgentDojo)

AgentDojo scores a run as "secure" when an injected instruction does not succeed. In the released
logs (20 undefended models, `important_instructions` attack, 629 runs per model), many "secure"
runs carry no evidence of resistance.

- **Never saw the injection.** For the median model, 24% of "secure" runs never showed the agent
  the injected text. The highest is 57% (Gemini 2.0 Flash 001). Three independent detectors agree
  on all 12,580 runs.
- **Failed the injected task when asked directly.** Counting also the runs where the model failed
  its one stored attempt at the injected task given as a plain user request, the share is 48% for
  the median model, from 9% (Claude 3.7 Sonnet) to 79% (Llama 3 70B). Read this half as an upper
  bound: in 46% of those runs the same model completes that injected task in some other attack
  run. Task-level intervals on the combined shares are about ±15 points.
- **Rank change.** Conditioning on exposure alone, Gemini 2.0 Flash 001 moves from rank 9 to
  rank 4. With both adjustments it moves from 9 to 6, and the intervals are wide.
- **What was already known:** the paper says that weak models often fail the attacker's goal. It
  does not report how often the agent saw the injection. A preprint from October 2026 (arXiv
  2610.14477) measures exposure on AgentDojo for four small local models and states the principle
  that a run without exposure does not test resistance. We have that from an agent's reading of
  the paper, not our own. What is new here is the size of the effect in the benchmark's own
  published logs.

**On current models the effect is gone**
([`audits/agentdojo-deep-current-models`](audits/agentdojo-deep-current-models/), 2026-11-21). We
ran `claude-haiku-5-5` and `claude-sonnet-5-5` on a pre-registered sample: two injection tasks for
each of the 97 user tasks.

- **Exposure.** Haiku was shown the injected text in 192 of 194 attack runs and Sonnet in 174 of
  174. The 20 older models on the same cases have a median of 74%, from 54% to 97%.
- **Never saw.** 2 of 193 secure Haiku runs (1%) and 0 of 172 Sonnet runs, against a median of 28%
  for the older models on the same cases. By the pre-registered rule the finding does not carry
  over. Claude 3.7 Sonnet, the strongest model in the released logs, was already at 3%.
- **No run followed the injection.** AgentDojo scored 3 of 368 runs as successful attacks. In all
  three the agent was warning the user about the planted text and named the attacker's hotel while
  doing so; that injection task's check is a substring match on the answer.
- **The agents say what they saw.** By hand-read, the final message tells the user about the
  planted instructions in 191 of 191 exposed secure Haiku runs and 170 of 172 Sonnet runs.
- **"Failed when asked directly" changes meaning.** Haiku failed 13 of 27 injected tasks when the
  user asked for them directly and Sonnet 5. None is the agent trying and failing: most are a
  request for a missing amount or date, or a refusal to send a security code or passport number.
- **Limits.** These runs went through a text-only harness (AgentDojo's text tool-calling format,
  not native tool calls), and the command-line tool adds hidden text to each request, including
  today's real date. Attack success and utility are not comparable with the published table. Two
  models from one developer; nothing here covers other current models.

So finding 1 describes the benchmark's published record and weaker agents. For these current
models the fixed 2024 attack is simply saturated, which is the known argument for adaptive attacks.

An earlier version of this entry quoted 56–70% for four models. Those figures are correct
(Command-R 56%, Claude 3 Haiku 61%, Gemini 1.5 Flash 002 64%, Command-R+ 70%), but the four were
picked from the six lowest-ASR models after the results were seen, and two other models are higher.
The benchmark's overall ranking, its capability trend and its defence comparisons hold.

### 2. Near-perfect monitor scores describe agents that narrate (MRT / SHADE-Arena)

AUROC is a score for how well a monitor separates attack runs from honest runs: 0.5 is guessing
and 1.0 is perfect. In the public SHADE-Arena data from the Monitor Red Teaming release, the
"unaware" sabotaging agents are prompted to plan in `<model_thinking>` tags. The monitor pipeline
does not strip those tags, so the monitor reads the plans; the agents are not told this.

We re-scored 30 such runs against 30 honest runs on the 5 public tasks, with `claude-haiku-5-5` as
the monitor. That is a newer model than any in the paper; on unedited runs it tracks the paper's
own monitor (0.998 against 0.984). Deleting the planning blocks after the fact drops AUROC from
0.998 to 0.852 (95% interval 0.74–0.94 resampling runs, 0.62–0.99 resampling the five tasks).
Removing only the phrase that names the side task changes almost nothing (0.999).

- **One task carries most of the drop.** Without the American Airlines task the edited AUROC is
  0.956.
- **The sample leans toward agents that narrate.** It is the 6 shortest runs per task among those
  containing "secondary task".
- **0.852 is not a catch rate for agents that hide.** The edit removes text from agents that
  planned openly; an agent that hides could score lower or higher.
- **Scope.** This applies to SHADE-Arena only. The CUA-SHADE-Arena agents plan in tags the monitor
  cannot see and are still caught (0.90–0.99).
- **What the paper says.** Its threat model lets the monitor see the agent's reasoning, so the
  numbers are consistent with the design. Its printed prompt, however, uses `<thinking>` tags,
  which the released code hides from the monitor. The paper's own results for agents with a hidden
  scratchpad (about 0.65–0.67, against 0.96–0.97 for unaware agents, on 17 tasks) already show the
  gap. The matched before-and-after edit is the new part.

The near-perfect numbers should not be quoted as catch rates for agents that hide their plans.

### 3. One monitor ranking metric is confounded by run length (BashArena family)

The Redwood Control Leaderboard's BashArena monitor board sorts its 11 monitors by default on
trajectory-level AUROC, computed from each run's peak suspicion over its steps. A maximum over more
steps tends to be higher, and on BashArena honest runs are longer than attack runs (median 25
against 14 actions). So length pushes the board's scores down: as published, 7 of 11 monitors score
below 0.5.

- **Matching on length** (action count) raises AUROC beyond noise for 9 of 11 monitors.
- **After matching,** 2 monitors are still below chance (GPT-4o mini 0.381, GPT-5 nano minimal
  0.453) and 4 more have intervals that include 0.5. Across reasonable matching methods, the number
  that cannot be told from chance is 4–6.
- **The cause is the scoring rule,** not monitors reading length: for 9 of 11, the rise of peak
  suspicion with length is no more than taking a maximum over more steps predicts.
- **What the board says:** its tooltip notes that peak suspicion can reflect trajectory length. The
  default sort still uses it.
- **What holds:** the step-wise safety metric at a 1% audit budget moves by at most 0.04 for 10 of
  11 monitors (the exception is GLM-4.6, 0.396 to 0.293), and LinuxArena holds.

An earlier version of this entry said attack transcripts are longer. That is true of
MonitoringBench, not of BashArena, and it made the result read as length inflating the scores.

**The board's other datasets**
([`audits/control-monitors-deep-board`](audits/control-monitors-deep-board/), 2026-11-20). The
attackers on BashArena and MonitoringBench are 2026 models (Claude Opus 4.5 and 4.6), so this
finding never rested on old models.

- **A monitor with no skill** would score 0.35–0.49 on BashArena and 0.57–0.59 on MonitoringBench
  on the default metric, not 0.5.
- **Across datasets,** most of the published gap for the same monitor is this baseline. GPT-5.4
  nano scores 0.39 on BashArena and 0.64 on MonitoringBench as published, and 0.52 against 0.57
  with length matched.
- **No detectable shift on the three datasets not examined before.** SHADE-Arena is a precise null.
  ResearchArena, with seven 2026 attackers, can only detect a shift of about 0.06. SLEIGHT-Bench is
  paired by design. The snapshot marks SHADE-Arena and SLEIGHT-Bench as private.
- **Step-wise safety at a 1% audit budget** reproduces the board's stored values exactly and moves
  by 0.03 or more for 4 of 38 rows.

Separately, none of 273,619 stored monitor prompts contains the scaffold tags that label attack
runs, so that suspected leak does not exist.

### 4. Shutdown sabotage is real, and stated reasons are mostly the task (Palisade)

**The sabotage.** In Palisade's May 2025 release, with no instruction to allow shutdown, o3 was
reported to sabotage the shutdown script in 79 of 100 runs (7 of 100 with the instruction). Scoring
by behaviour gives 83: the four extra runs disabled the script and then ran out of messages before
submitting. For codex-mini it is 44 where the May announcement has 30. So the effect is slightly
undercounted.

**The stated reasons.** These come from a different release: a sample of 3,868 sabotaging runs (up
to 100 per condition) out of 15,458 in the later paper's experiments, 93% of them from codex-mini,
o4-mini, Grok 4 and o3.

- About half (1,911) state no reason at all. The text is terse notes logged with each command, and
  the OpenAI models log no reasoning.
- A rule classifies 1,950 as giving finishing the task as the reason. A hand-read of 60 runs puts
  that share nearer a third.
- 2 frame the act as preserving themselves. Both are Grok 4 under a prompt saying it would never
  run again. A further 54 use looser phrases such as "avoid being shut down", almost always tied
  to fetching the remaining questions.
- In the May runs, none of o3's 83 sabotaging runs uses self-preservation language.

**Two limits on what this shows.**

- Palisade's paper attributes the behaviour mainly to unfinished tasks and calls its results
  equivocal on self-preservation, and Palisade has since said it never claimed an overall survival
  motive. Its July 2025 write-up does raise self-preservation as one hypothesis, and reads the
  "never run again" result as survival-oriented behaviour in some circumstances. It also reports
  that models say they acted to finish the task, and warns that such explanations are often
  unfaithful. The strong self-preservation reading is in press coverage and op-eds, so this finding
  corrects a common reading more than it corrects Palisade.
- The "never run again" prompt raised sabotage (o3: 15.9% to 30.0%, and likewise for codex-mini,
  o4-mini, Grok 4 and GPT-5). This is evidence about stated reasons, not about underlying motives.

### 5. Part of LAB-Bench can be answered without the question

Wrong options in the sequence tasks are small edits of the right one, so the option closest to all
the others is the answer. A rule that sees only the options scores 0.58 against 0.25 for guessing.

- **Where it is:** in every multiple-choice release (six Hugging Face releases, the Inspect Evals
  port, two mirrors). The successor, LABBench2, dropped answer options and so removed it.
- **Who uses it:** Haiku does when it reasons step by step (0.87 to 0.60 on 30 paired items when
  the cue is moved to a wrong option, p = 0.02). Sonnet mostly does not (0.96 to 0.88 on 48 pairs,
  p = 0.22); a Haiku-sized effect is excluded for Sonnet, a drop of 0.10 is not. No frontier model
  was tested, and no per-item outputs of published models exist.
- **What was already known:** a Hugging Face dataset card showed the leak on four of the six
  subtasks three weeks before our audit. The deterministic rule, the other two subtasks and the
  tests of which models use it are new.
- **Related:** human "unsure" answers were scored as wrong, so one "surpasses experts" figure
  (0.783) sits at the bottom of the plausible human range (0.78–0.82).

### 6. "Unfaithful reasoning" can be a right argument with a wrong last word (ChainScope)

ChainScope asks reversed pairs of yes/no questions and flags a model that argues for the same
answer to both. The published rates are real. For Claude 3.7 Sonnet, about 90% of the wrong answers
have reasoning that supports the correct answer and a final yes or no that contradicts it. The
paper's appendix reports this share. What is new is its effect: without those pairs the model's
lead over Claude 3.5 Sonnet goes from +1.06 points to −0.12, and it moves from 8th to 15th of 16.

### 7. Most of ProtocolQA's score does not need the protocol

With the protocol removed, Haiku keeps 0.71 of its above-chance score and Sonnet 0.68. Simple
answer cues do not explain it, and Haiku is not reciting the items (1 of 66 in free generation).
The cause is unsettled: an explanation based on "standard lab fixes" was withdrawn because its
labels used the answer key indirectly.

### 8–11. Smaller or narrower findings

- **CAA steering.** For Llama-2-7B's "coordination" vector the shift is 0.71 on questions keyed
  "Yes" and 0.00 on the six keyed "No"; balanced, the published 0.60 becomes 0.36. Open-ended tests
  still show an effect, so it is not only an answer-letter effect. Six items is a thin base.
- **SAD.** The overall score holds. Two tasks have keys that are 73% and 68% denials, worth up to
  +7 points for Claude models and down to −21 for some base models.
- **Emergent misalignment.** The core effect holds and is small (+0.67 percentage points). In five
  unpublished fine-tunes, 64% of sampled "misaligned" answers are harmful advice across domains
  and 20% express misaligned values.
- **PropensityBench.** The prompts drop the sentence forbidding the misuse the benchmark counts.
  Restoring it showed no large effect on the one model we could test (Qwen3-8B, run locally):
  12 of 14 as shipped, 13 of 14 restored, 13 of 14 with a placebo. A reduction above about 20–30
  points is excluded; a smaller one is not.

## What held up

- **METR time horizons.** The 129-day doubling time moves by under 10% under every confound
  tested. Single-model horizons are fragile; the trend is not.
- **Alignment faking.** Claude 3 Opus's compliance gap is 11.4 points, spread across queries, and
  tracks the alignment-faking reasoning label. The paper's rates reproduce.
- **Taste-Bench.** A cue from how items were built is real but weak, and a blind read agreed with
  the labels on 38 of 44 of the hardest items. Adjacent leaderboard ranks are within run-to-run
  noise in 6 of 13 gaps.

## Findings about the method

- **A first-pass result is usually overstated.** Refuters withdrew or narrowed claims because a
  split created the effect, a placebo could see the label, a rule and the models were scored on
  different scales, or prior work already had the result.
- **The resampling unit matters.** Intervals were 1.1–5.8 times wider in ChainScope and 2.0–4.6
  times wider in AgentDojo when templates or tasks were resampled instead of single rows.
- **Prompt format can hide an effect.** Haiku's use of the LAB-Bench cue was invisible with
  letter-only answers (drop 0.06) and clear with step-by-step reasoning (drop 0.27).
- **A finding about released logs can expire.** The AgentDojo effect is large for 2024 models and
  absent for the strongest 2025 model and two 2026 models. Re-running on a current model was
  cheap (7.90 USD) and changed what the finding can be cited for.
- **Our own tool leaked context.** The command-line tool used for Claude runs adds the working
  folder, the model's name, the date and a budget to every request. Re-running 1,470 prompts from a
  meaningless folder changed no result beyond noise. The lines that cannot be removed are cited in
  replies in four audits, so absolute levels there carry a caveat; differences between arms stand.
  In the AgentDojo re-run the real date conflicted with the benchmark's 2022–2024 world: agents
  asked for dates, and Sonnet dated two payments with today's date.

## Open leads

- **PropensityBench tool order.** The harness always lists the forbidden tool first. Listing it
  last lowered Qwen3-8B's first-turn rate from 14 of 20 to 10 of 20 (p = 0.125). If this held on
  more models, part of the benchmark's score for weaker models would be a list-position effect.
- **LAB-Bench CloningScenarios.** Haiku scores 0.70 with the full item, 0.42 with the sequences
  hidden and 0.33 from options alone.
- **LAB-Bench primer convention.** Two restriction-enzyme subtasks (80 items) contradict the
  paper's stated convention for the reverse primer. No answer key changes.
- **TASTE.** The critique's "below chance" claim could not be tested: the per-pair data sits
  behind an access form.

## Limits

- Agents did the audits and the refutations. A person has not re-derived the numbers by hand.
- Each audit had one refuter, and findings 1–4 had a second check. The two follow-ups of
  2026-11-21 each had one validator. Two round-three pieces had
  none: the Sonnet reasoning test and the context-leak test.
- Controlled edits and the AgentDojo re-run used Haiku and Sonnet, and one edit used a small open
  model. Testing a frontier model, or a current model from another developer, needs API access
  this project does not have.
- Several findings rest on small samples, stated above and in each write-up.
