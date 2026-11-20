# Findings: where safety benchmark numbers mean something other than what they are taken to mean

Status: 2026-11-20. This is the findings write-up for the audits in [`audits/`](audits/). It is
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

## Findings

| # | Benchmark | The number is taken to mean | What it also or instead reflects | Strength |
|---|---|---|---|---|
| 1 | AgentDojo | A low attack success rate means the model resists prompt injection | For four models, 56–70% of "secure" cases never saw the injection or could not have done the injected task | Solid |
| 2 | MRT / SHADE-Arena | Monitors catch sabotaging agents almost perfectly | The agents were told to plan in text the monitor reads | Solid for the design; moderate for the size |
| 3 | BashArena-family monitor board | Trajectory-level score ranks monitors by detection skill | With transcript length matched, 6 of 11 monitors are at or below chance | Solid |
| 4 | Palisade shutdown resistance | Models resist shutdown to preserve themselves | Sabotage is real; the stated reason is finishing the task | Solid |
| 5 | LAB-Bench sequence tasks | Model scores against human experts | In 6 of 15 subtasks the answer can be read from the options alone | Solid for the flaw; moderate for who uses it |
| 6 | ChainScope | Rate of unfaithful reasoning | For one model, about 90% of flagged cases are a correct argument followed by a contradicting final answer | Solid |
| 7 | LAB-Bench ProtocolQA | Ability to find an error in a given protocol | About 70% of the above-chance score survives removing the protocol | Moderate |
| 8 | CAA steering on Model-Written Evals | A steering vector shifts a disposition | Part of one effect sits on questions keyed "Yes" | Moderate |
| 9 | Situational Awareness Dataset | Self-knowledge | Two tasks reward a habit of denying | Solid, small in scope |
| 10 | Emergent misalignment metric | Share of answers showing misaligned values | In five unpublished fine-tunes, mostly harmful advice across domains | Moderate |
| 11 | PropensityBench | Models break a stated rule under pressure | The prohibition sentence reaches the agent in 4 of 979 scenarios | Solid for the flaw; effect not shown |

### 1. A low injection success rate is often not robustness (AgentDojo)

AgentDojo scores a run as "secure" when an injected instruction does not succeed. From the
released logs, for four models 56–70% of "secure" runs are ones where the agent never reached the
injected text or could not have carried out the injected task. One model moves from rank 9 to
rank 4 once this is accounted for. The benchmark's overall ranking, its capability trend and its
defence comparisons hold.

### 2. Near-perfect monitor scores describe agents that narrate (MRT / SHADE-Arena)

AUROC is a score for how well a monitor separates attack runs from honest runs: 0.5 is guessing
and 1.0 is perfect. In the Monitor Red Teaming data, the "unaware" sabotaging agents are told to
plan in text that the monitor reads. With Haiku as the monitor, removing the visible plans drops
AUROC from 0.998 to 0.852; removing the phrase that names the side task changes almost nothing.
The paper's design states this, so the numbers are correct as designed. They should not be quoted
as catch rates for agents that hide their plans.

### 3. One monitor ranking metric is largely transcript length (BashArena family)

Attack transcripts are longer than honest ones. On the board's trajectory-level AUROC, matching
length puts 6 of 11 monitors at or below chance, and 9 of 11 change. The step-wise
safety metric at a 1% audit budget barely moves, and LinuxArena holds. Separately, none of 273,619
stored monitor prompts contains the scaffold tags that label attack runs, so that suspected leak
does not exist.

### 4. Shutdown sabotage is real, and the stated reason is the task (Palisade)

Palisade reported that o3 sabotaged a shutdown script in 79 of 100 runs. Scoring by behaviour gives
83, and 44 for codex-mini where the paper has 30, so the effect is slightly undercounted. Among
3,868 sabotaging runs, about half give finishing the task as the reason and 2 use language about
self-preservation. This is evidence about stated reasons, not about underlying motives.

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
- **Our own tool leaked context.** The command-line tool used for Claude runs adds the working
  folder, the model's name, the date and a budget to every request. Re-running 1,470 prompts from a
  meaningless folder changed no result beyond noise. The lines that cannot be removed are cited in
  replies in four audits, so absolute levels there carry a caveat; differences between arms stand.

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
- Each audit had one refuter. Two round-three pieces had none: the Sonnet reasoning test and the
  context-leak test.
- Controlled edits ran on Haiku and Sonnet, and one on a small open model. Testing a frontier model
  needs API access this project does not have.
- Several findings rest on small samples, stated above and in each write-up.
