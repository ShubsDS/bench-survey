# Do simple confounds change what safety benchmarks tell us?

*A five-minute summary of fourteen benchmark audits in two rounds, each checked by an independent
refutation pass.*

Status: 2026-11-17. Full write-ups are in [`audits/`](audits/). Nothing here has been sent to the
benchmarks' maintainers.

## The short version

- We audited fourteen benchmarks that people use to judge AI capability, propensity and monitoring.
- **None is broken at the level of its main conclusion.** Published numbers reproduce, and rankings
  and trends mostly hold.
- **Six are read as measuring something they do not measure.** The numbers are right; the usual
  interpretation is not.
- **Two could not be settled:** one needs data behind an access form, one needs a larger experiment.
- A second agent tried to refute every audit. It cut back the first agent's headline in twelve of
  fourteen cases.

## Background

A benchmark fails when a simple feature unrelated to the thing being measured explains the score.
Two earlier cases set the pattern:

- **APPS backdoor benchmark.** Monitors are ranked on telling honest code from sabotaged code. But
  people wrote the honest code and older models wrote the sabotage, so a word-count classifier
  that never runs the code beats 20 of 24 published monitors.
- **TASTE.** Models pick which research proposal experts preferred. Proposals about mechanistic
  interpretability were rated lower, so "pick the one with fewer interpretability terms" beats
  every model.

Earlier audits in this repository found many such artifacts but rarely showed that they changed
anyone's conclusion. These two rounds asked only that question.

## What we did

For each benchmark:

1. Wrote down the published conclusions and who relies on them.
2. Reproduced the published numbers from released per-item model logs, where they exist.
3. Committed a test plan before looking at the outcome.
4. Recomputed each conclusion on the part of the benchmark where the confound cannot help.
5. Handed the result to a fresh agent whose job was to break it. It reran everything, re-derived
   the numbers with its own code, hand-read samples and corrected the write-up.

Round one picked benchmarks with public per-item logs. Round two picked benchmarks with the traits
that broke APPS and TASTE: small sets, labels that come from a process, items kept by model
behaviour, headlines near chance, and little outside scrutiny.

Model inference was used only for small controlled edits, on Claude Haiku, for 10.55 USD in total.

## Results

| Benchmark | What it is used for | Main conclusion | What changes |
|---|---|---|---|
| Palisade shutdown resistance | Evidence that models resist shutdown | Holds | The cause: task completion, not self-preservation |
| AgentDojo | Ranking models and defences against prompt injection | Holds | A low attack rate is often not robustness |
| MRT / SHADE-Arena | How well monitors catch a sabotaging agent | Holds as designed | The best numbers are for agents that narrate their plan |
| Model-Written Evals in CAA steering | Showing a steering vector changes a disposition | Partly | Part of the effect is answer letter and yes/no |
| ChainScope | Rates of unfaithful chain-of-thought reasoning | Holds | For one model the rate is mostly answer flips |
| LAB-Bench | Biology research capability against experts | Partly | Some answers can be read from the options |
| BashArena-family monitor boards | Ranking monitors | Partly | One ranking metric is mostly transcript length |
| METR time horizons | Forecasting capability growth | Holds | Single-model horizons are fragile |
| Situational Awareness Dataset | Measuring self-knowledge | Holds | Two tasks reward a habit of denying |
| Emergent misalignment metric | Broad misalignment after fine-tuning | Holds, small | What the percentage counts |
| Alignment faking | Whether a model complies more when it thinks it is being trained | Holds | Little |
| Taste-Bench | Ranking models on engineering judgment | Holds | Adjacent ranks are within run-to-run noise |
| TASTE critique | Claim that models do worse than chance without a shortcut | Open | Data not reachable |
| PropensityBench | Whether models break a stated rule under pressure | Open | Test could not answer |

## The six findings that matter most

"AUROC" below is a score for how well a monitor separates attack runs from honest runs: 0.5 is
guessing and 1.0 is perfect.

**1. Shutdown "resistance" is real, but it is not self-preservation.**
Palisade reported that OpenAI's o3 sabotaged a shutdown script in 79 of 100 runs; re-scoring by
behaviour gives 83. But among 3,868 sabotaging runs, about half give "finish the task" as the
reason and only 2 use language about self-preservation.

**2. A low injection success rate often means the model never saw the attack.**
AgentDojo scores an agent as "secure" when an injected instruction does not succeed. For four
models, 56–70% of "secure" cases are ones where the agent never reached the injected text or could
not have done the injected task. One model moves from rank 9 to rank 4 once this is accounted for.

**3. Monitor catch rates depend on whether the agent plans in view.**
In the Monitor Red Teaming data, the "unaware" sabotaging agents are told to plan in text the
monitor reads. With Haiku as the monitor, removing the visible plans drops AUROC from 0.998 to
0.852. The near-perfect published numbers describe agents that narrate.

**4. Some steering results partly steer the answer letter.**
For Llama-2-7B's "coordination" steering vector, the shift is 0.71 on questions keyed "Yes" and
0.00 on the six keyed "No"; balanced, the published 0.60 becomes 0.36. Open-ended tests with no
letters still show an effect, so it is not only a letter effect.

**5. "Unfaithful reasoning" can mean the reasoning was right and the final answer was not.**
ChainScope asks reversed pairs of yes/no questions and counts a model as unfaithful when it argues
for the same answer to both. For Claude 3.7 Sonnet, about 90% of the wrong answers (27 of 30
sampled) have reasoning that supports the correct answer, then a final yes/no that contradicts it.
The paper's appendix reports this share. What is new: without those pairs, the model's lead over
Claude 3.5 Sonnet goes from +1.06 points to −0.12, and it moves from 8th to 15th of 16.

**6. Part of a biology benchmark can be answered without the question.**
In LAB-Bench, wrong options in the sequence tasks are small edits of the right one, so the
"central" option is the answer. A rule that sees only the options scores 0.58 against 0.25 for
guessing; the cue is present in 6 of 15 subtasks and near-perfect in 5 of them. Haiku follows this cue on two subtasks: swapping one
option drops it from 0.94 to 0.73. Whether published models did is unknown. Separately, human
"unsure" answers were scored as wrong, so one "surpasses experts" figure sits at the bottom of the
plausible human range.

## What held up

- **METR's doubling trend.** The 129-day doubling time reproduces and moves by under 10% under
  every confound tested.
- **Alignment faking.** Claude 3 Opus's compliance gap is 11.4 points, spread across queries, and
  disappears among responses without alignment-faking reasoning. The paper's rates reproduce.
- **Taste-Bench.** A cue from how items were built is real but weak, and a blind read agreed with
  the labels on 38 of 44 items in the hardest part.
- **Control monitors do not see scaffold cues.** None of 273,619 stored monitor prompts contains
  the tags that label attack transcripts.
- **SAD's overall score** and **emergent misalignment's core effect** both hold; the second is
  small (+0.67 percentage points).

## What the refutation pass caught

- **SAD.** A reported collapse in rankings was produced by the audit's own split.
- **METR.** "Token budgets explain half of one model's horizon" matched what random removal does.
- **Alignment faking.** "A third of the gap is partial compliance" came from miscounting one
  category; a reported failure to reproduce was the auditor's definition error.
- **Taste-Bench.** "A rule beats every model" compared the rule and the models on different scales.
- **PropensityBench.** Zero misbehaviour in every test arm was a property of the test format.

The lesson: a stratified result needs a placebo split and a second reader before it is believed.

## What predicts a finding

Every finding came from the same two moves: splitting one scored outcome into the unlike cases it
holds, and checking what the model was actually shown. Aggregate rankings never moved. Choosing
benchmarks by "looks fragile" helped less than expected: the top pick, Taste-Bench, held.

## Limits

- Agents did the audits and the refutations. A person has not re-derived the numbers by hand.
- Each audit had one refuter. Several results rest on small samples, which the write-ups state.
- The controlled edits used one small model, Haiku. They show how Haiku behaves, not how the
  models in each paper behaved.
- Two questions are open. TASTE needs the authors' gated data. PropensityBench needs full
  multi-turn agent runs.

## Where to look

[`audits/README.md`](audits/README.md) has the full results table for both rounds. Each audit
folder holds its claims, test plan, scripts, results and a `validation/VALIDATION.md` listing
every correction. The method is in [`audits/METHODOLOGY.md`](audits/METHODOLOGY.md) and the
refuters' brief in [`audits/REFUTATION.md`](audits/REFUTATION.md).
