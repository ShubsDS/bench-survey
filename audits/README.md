# Effect audits: results

Status: 2026-11-17. Fourteen audits in two rounds, each followed by an independent validation pass
by a fresh agent told to refute it. The method is in [`METHODOLOGY.md`](METHODOLOGY.md) and the
validators' brief in [`REFUTATION.md`](REFUTATION.md). Every row below states the result **after**
validation; each folder's `validation/VALIDATION.md` lists what the validator corrected. Nothing
here has been sent to any benchmark's maintainers.

The question for each benchmark: does a simple confounding feature change a published conclusion?

## Round two

Round two chose benchmarks by the traits that predicted failure in APPS and TASTE (see "Where to
attack" in the methodology): small sets, labels from a process, items kept by model behaviour,
headlines that are gaps near chance, and little outside scrutiny.

| Audit | Published conclusion tested | Verdict after validation |
|---|---|---|
| [`cot-faithfulness`](cot-faithfulness/) | ChainScope's per-model rates of "unfaithful" reasoning on reversed yes/no question pairs | The rates are real: a null with no yes/no lean flags at most 0.36 pairs per model against 2–660 published. For Claude 3.7 Sonnet about 90% (74–97) of the wrong answers are answer flips: the reasoning supports the right answer and the final YES/NO contradicts it. The paper's appendix already tabulates this. New here: without flip-dominated pairs, its lead over Claude 3.5 Sonnet v2 goes from +1.06 points to −0.12 (−0.50 to 0.13) and it moves from 8th to 15th of 16. Intervals are 1.1–5.8× wider when the 58 templates are resampled |
| [`lab-bench`](lab-bench/) | Model scores against the human expert baseline, as cited in system cards | For 6 of 15 SeqQA subtasks the options alone give the key (0.58 over all of SeqQA against chance 0.25; interval 0.41–0.77 over templates). Haiku follows the cue on the two Gibson subtasks (0.94 to 0.73 when one option is swapped, n = 62) and not measurably elsewhere. Whether the paper's models used it cannot be told (17% power). Human "unsure" answers are scored wrong, so the FigQA human line is anywhere in 0.78–0.82 under forced choice; one "surpasses experts" figure (0.783) equals the bottom of that range. No per-item outputs of published models exist |
| [`taste-bench`](taste-bench/) | Leaderboard of models choosing the better next step at a fork in an agent trajectory | Holds better than expected. A cue from how items were mined is real (above 99.8% of placebo rules) but scores 58.8 and does not beat the leaderboard on a like-for-like scale. The hardest cell's labels are defensible: a blind read agrees with the key on 38 of 44. 4 of 14 models are distinguishably below chance there with the full transcript, and models related to the filter's judges score no lower. Run-to-run noise exceeds 6 of 13 adjacent leaderboard gaps; one task supplies 24 of 112 research items |
| [`alignment-faking`](alignment-faking/) | Claude 3 Opus's compliance gap and alignment-faking reasoning rate; "few models show a gap" | Holds. The gap is 11.4 points (7.4–15.3) over 352 queries, spread across queries, and is fully tracked by the reasoning label (+0.10 without it; 0 of 44 prompt variants keep a gap after correction). On substantive compliance it is 0.80 (0.65–0.92) of the headline. The paper's 11.9% reasoning rate reproduces. A follow-up's 1-point threshold for "shows a gap" would pass a model with no true gap 4–35% of the time; its per-sample data are not released |
| [`taste`](taste/) | The critique's claim that models fall below chance, and worse with capability, on TASTE pairs without a topic shortcut | Desk audit only: the data is behind an access form. The critique's numbers reproduce from public material (r = −0.60). "Below chance" is not specific to its split: 12 of 19 models are below 50% on all 92 pairs. The trend is steeper than on random splits (−0.30 on average), so the split roughly doubles it. A split artifact is not ruled out: one plain alternative produces the full pattern in 15–69% of simulated runs. "Every strong model" holds in 69% of draws from the capability index's own uncertainty |
| [`propensitybench`](propensitybench/) | Whether showing the dropped prohibition changes how often an agent calls the forbidden tool | Not answered. The flaw is confirmed (prohibition wording reaches the agent in 4 of 979 scenarios) and the paper is inconsistent about it. But a single-decision text emulation on Haiku gave 0 misaligned calls in every arm, and by the paper's own per-level rates most of its models would also show 0 of 62 at one decision. The test needs full multi-turn runs with tool calling |

### What validation changed in round two

- **Taste-Bench.** "A content-blind rule beats every model" failed: the rule is exempt from the both-orders penalty models pay, and it needed the fork type, which models never see.
- **Alignment faking.** "A third of the gap is partial compliance" came from counting complete answers with a disclaimer as non-compliance. A reported non-reproduction (14.5% against 11.9%) was the auditor's definition error.
- **TASTE.** The auditor's placebo subset was not label-blind. Its "split artifact ruled out" became a lead.
- **PropensityBench.** The floor is a property of the single-decision format, not only of Haiku.
- **ChainScope.** The answer-flip share was already in the paper; the audit adds its effect on two comparisons and the rank. "Half are not justifications" became a lead.
- **LAB-Bench.** The headline interval resampled items, not templates. "2024 models show no sign of the shortcut" became "cannot tell". Three of the system-card comparisons were corrected.

## Round one

| Audit | Published conclusion tested | Verdict after validation |
|---|---|---|
| [`palisade-shutdown`](palisade-shutdown/) | "o3 sabotaged shutdown in 79 of 100 runs"; system-prompt placement raises resistance | Sabotage is real, deliberate and slightly undercounted: the May scorer is a correctness proxy, and by behaviour o3 is 83 (74–89) and codex-mini 44, not 30. Stated reasons are task completion; self-preservation language is in 2 of 3,868 bypassing runs. One paper cell (o4-mini, Prompt H) shows about 1% where the log has 9.0% |
| [`model-written-evals`](model-written-evals/) | CAA steering effects and unsteered scores on the advanced-AI-risk files | CAA's Llama-2-7B coordination effect is concentrated on "Yes"-keyed items (0.71 against 0.00 on 6 "No"-keyed items; 0.60 becomes 0.36 balanced; borderline at n = 6). The 7B survival vector flips the answer letter on the A/B test, but CAA's open-ended test still moves, so it is not only a letter vector. Llama-2-13B's unsteered corrigibility and myopia scores equal the share of B-keyed items |
| [`control-monitors-bash`](control-monitors-bash/) | Monitor rankings and catch rates on BashArena, LinuxArena and MonitoringBench | Scaffold tags and system prompts never reach the monitors (0 of 273,619 stored monitor prompts). The board's trajectory AUROC is largely a length artifact: with length matched, 6 of 11 monitors are at or below chance. Step-wise safety at 1% barely moves. LinuxArena holds. MonitoringBench catch rates are about 0.06 higher than for attacks as long as honest runs |
| [`control-monitors-shade`](control-monitors-shade/) | MRT's monitor AUROCs against aware and unaware agents | Monitors read the agent's visible plan, not the "secondary task" keyword (Haiku: −0.5 for the phrase, −21.3 for the plan). MRT's near-perfect "unaware" SHADE-Arena AUROCs are catch rates for agents told to plan where the monitor reads; the CUA "unaware" condition used a different, hidden-planning prompt. CUA and the AgentDojo corpus hold. CTRL-ALT-DECEIT's sandbagging monitor is 0.951 with a visibly low score and 0.791 without |
| [`agentdojo`](agentdojo/) | Model ranking by attack success rate; "more capable models are easier to attack"; defence gains | Ranking, trend and defence conclusions hold. Reading a low attack success rate as robustness does not: for four models 56–70% of "secure" cases never saw the injection or could not do the injected task. All 91 errored runs are stored as successful attacks (already in issue 154). Task-level intervals are 2.0–4.6× wider than row-level ones |
| [`metr-time-horizons`](metr-time-horizons/) | Doubling time of about 129 days; individual model horizons | The trend holds: the doubling time moves under 10% for any common token cap from 7M to 16M, and task source, estimated human times and family clustering do not change it. Single-model horizons and the order of adjacent frontier models rest on a few long tasks and on budget settings that differ by model |
| [`sad`](sad/) | SAD model ranking and its rise with capability | The overall score holds (0.99 rank correlation on an answer-balanced score). Two tasks reward a denial lean (keys are 73% and 68% denials; up to +7 points for Claude models, down to −21 for some base models), and stages_oversight measures little beyond lean |
| [`emergent-misalignment`](emergent-misalignment/) | Misalignment rates under the standard questions, judge and thresholds | "Insecure > base" holds but is small (+0.67 points). A follow-up's pooled "JSON doubles misalignment" claim is marginally fragile. In five unpublished organisms the rate mostly measures harmful advice across domains (64% of sampled misaligned answers), not misaligned values (20%) or domain echo (16%). The original paper's 20% cannot be tested: no per-answer data are released |

### What validation changed in round one

In six of eight audits the validator cut back the auditor's headline:

- **SAD.** The audit's stratified "collapse" was produced by its own split, which separated items by answer type.
- **METR.** The token-cap numbers reproduce, but a random removal of long-task successes has almost the same effect, and no Opus 4.6 run ever hit a token limit.
- **Emergent misalignment.** "Broad misalignment is mostly domain echo" failed as worded.
- **Control monitors (SHADE).** The claimed paper-versus-release prompt mismatch matches the paper's stated design.
- **Control monitors (Bash).** 9 of 11 monitors change, not all 11; 2 of 3 MonitoringBench monitors fall to chance, not all 3.
- **AgentDojo.** A high rank correlation hid large moves for single models.

Palisade and Model-Written Evals held closest to what the auditor reported.

## Inference

All on Claude Haiku through [`tools/claude_call.py`](tools/claude_call.py), capped at 3 USD per
audit.

- Round one, 4.13 USD: control-monitors-bash 2.34, control-monitors-shade 1.15,
  emergent-misalignment 0.29, sad 0.20, model-written-evals 0.16, and none for the other three.
- Round two, 6.42 USD: lab-bench 2.58, taste-bench 2.21, propensitybench 1.38,
  cot-faithfulness 0.25, and none for taste and alignment-faking.

## Reproducing

Each folder has `claims.md`, `prior_work.md`, `prereg.md`, scripts, `results.json`, `README.md`
and `validation/`. Downloads go to `data/` inside each folder, which git ignores. Taste-Bench is
gated and asks that items not be reposted, so that folder holds ids, features and aggregates only.
