# Effect audits: results

Status: 2026-11-17. Eight audits, each followed by an independent validation pass by a fresh agent
told to refute it. The method is in [`METHODOLOGY.md`](METHODOLOGY.md). Every row below states the
result **after** validation; each folder's `validation/VALIDATION.md` lists what the validator
corrected. Nothing here has been sent to any benchmark's maintainers.

The question for each benchmark: does a simple confounding feature change a published conclusion?

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

## What validation changed

In six of eight audits the validator cut back the auditor's headline:

- **SAD.** The audit's stratified "collapse" was produced by its own split, which separated items by answer type.
- **METR.** The token-cap numbers reproduce, but a random removal of long-task successes has almost the same effect, and no Opus 4.6 run ever hit a token limit.
- **Emergent misalignment.** "Broad misalignment is mostly domain echo" failed as worded.
- **Control monitors (SHADE).** The claimed paper-versus-release prompt mismatch matches the paper's stated design.
- **Control monitors (Bash).** 9 of 11 monitors change, not all 11; 2 of 3 MonitoringBench monitors fall to chance, not all 3.
- **AgentDojo.** A high rank correlation hid large moves for single models.

Palisade and Model-Written Evals held closest to what the auditor reported.

## Inference

All on Claude Haiku through [`tools/claude_call.py`](tools/claude_call.py), 4.13 USD in total:
control-monitors-bash 2.34, control-monitors-shade 1.15, emergent-misalignment 0.29, sad 0.20,
model-written-evals 0.16, and none for the other three.

## Reproducing

Each folder has `claims.md`, `prior_work.md`, `prereg.md`, scripts, `results.json`, `README.md`
and `validation/`. Downloads go to `data/` inside each folder, which git ignores.
