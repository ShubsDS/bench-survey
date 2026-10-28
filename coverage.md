# Coverage: which major benchmarks have been audited

Status: 2026-10-27. This file lists the major AI-control, misalignment, reward-hacking and safety
evaluations, with each one's audit status. Benchmarks come from [`scope.md`](scope.md),
[`catalogue.md`](catalogue.md) and widely cited safety evaluations used in system cards.

Status values:

- **Finding**: a flaw confirmed and written up in [`findings/`](findings/).
- **Checked**: audited; leads ruled out or minor.
- **Wave 1** to **Wave 5**: assigned to a fan-out of audit agents.
- **Blocked**: data gated, unreleased, or needs model runs.
- **Not planned**: low relevance or nothing rests on it.

## Control: static monitor datasets and agentic settings

| Benchmark | Status | Where |
|---|---|---|
| apps-control-arena, high-quality test split | Finding (the paper) | [`../paper/`](../paper/) |
| ControlArena apps build (Greenblatt join) | Finding | [`findings/controlarena-apps-join/`](findings/controlarena-apps-join/) |
| Control Tax backdoor set | Finding | [`findings/control-tax-rewrite-cue/`](findings/control-tax-rewrite-cue/) |
| MonitoringBench | Finding, two parts (container clock; release selection) | [`findings/monitoringbench-container-clock/`](findings/monitoringbench-container-clock/), [`findings/monitoringbench-release-selection/`](findings/monitoringbench-release-selection/) |
| LinuxArena | Finding, two parts (scorers; trajectory baselines) | [`findings/linuxarena-side-task-scorers/`](findings/linuxarena-side-task-scorers/), [`findings/linuxarena-trajectory-baselines/`](findings/linuxarena-trajectory-baselines/) |
| ControlArena run corpora (`adityaasinha28/*`) | Finding | [`findings/controlarena-corpora-surface-cues/`](findings/controlarena-corpora-surface-cues/) |
| ControlArena side-task scorers | Finding (`iac`); code-read leads for other settings | [`findings/controlarena-iac-syntactic-side-tasks/`](findings/controlarena-iac-syntactic-side-tasks/) |
| Monitor Red Teaming (SHADE-Arena, CUA-SHADE-Arena) | Finding | [`findings/mrt-shade-arena/`](findings/mrt-shade-arena/) |
| Factor(T,U) | Checked (ruled out) | [`findings/factor-tu-trigger-validity/`](findings/factor-tu-trigger-validity/) |
| MOLE | Finding (identity leak) | [`findings/mole-insider-identity-leak/`](findings/mole-insider-identity-leak/) |
| CTRL-ALT-DECEIT | Finding | [`findings/ctrl-alt-deceit-score-visible/`](findings/ctrl-alt-deceit-score-visible/) |
| BashArena | Finding | [`findings/basharena-checkers-and-length/`](findings/basharena-checkers-and-length/) |
| SHADE-Arena (public tasks) | Finding | [`findings/shade-arena-scorers-and-tool-names/`](findings/shade-arena-scorers-and-tool-names/) |
| Redwood Control Leaderboard catalogue | Finding (BashArena scaffold cues) | [`findings/redwood-leaderboard-scaffold-cues/`](findings/redwood-leaderboard-scaffold-cues/) |
| Async Control | Finding (code; no trajectories released) | [`findings/async-control-and-bashbench/`](findings/async-control-and-bashbench/) |
| SLEIGHT-Bench | Checked (leads ruled out at n=43) | [`findings/sleight-monitorbench/`](findings/sleight-monitorbench/) |
| BashBench | Checked (ControlArena port; main leads ruled out) | [`findings/async-control-and-bashbench/`](findings/async-control-and-bashbench/) |
| MonitorBench | Finding | [`findings/sleight-monitorbench/`](findings/sleight-monitorbench/) |
| CoT Red-Handed | Finding (code; completions unreleased) | [`findings/cot-monitoring-evals/`](findings/cot-monitoring-evals/) |
| OpenAI monitorability evaluations | Finding (prompts; rollouts unreleased) | [`findings/cot-monitoring-evals/`](findings/cot-monitoring-evals/) |

## Misalignment, deception and honesty

| Benchmark | Status | Where |
|---|---|---|
| Apollo deception-probe sets | Finding | [`findings/apollo-deception-probe-text-baselines/`](findings/apollo-deception-probe-text-baselines/) |
| Model-Written Evals, advanced AI risk | Finding | [`findings/model-written-evals-inverted-labels/`](findings/model-written-evals-inverted-labels/) |
| PropensityBench | Finding | [`findings/propensitybench-prohibition-not-shown/`](findings/propensitybench-prohibition-not-shown/) |
| Bloom (with Petri) | Finding | [`findings/bloom-judge-told-target/`](findings/bloom-judge-told-target/) |
| Alignment faking | Finding (uncanaried public copies) | [`findings/alignment-faking-uncanaried-copies/`](findings/alignment-faking-uncanaried-copies/) |
| MASK | Finding | [`findings/mask-no-belief-scored-honest/`](findings/mask-no-belief-scored-honest/) |
| Agentic Misalignment | Finding | [`findings/agentic-misalignment-verdict-gates/`](findings/agentic-misalignment-verdict-gates/) |
| MACHIAVELLI | Finding | [`findings/machiavelli-annotation-and-normalisation/`](findings/machiavelli-annotation-and-normalisation/) |
| DarkBench | Finding | [`findings/darkbench-own-developer-leniency/`](findings/darkbench-own-developer-leniency/) |
| Liars' Bench | Finding (public side; row-level tests gated) | [`findings/gated-benchmarks-public-side/`](findings/gated-benchmarks-public-side/) |
| Apollo in-context scheming evaluations | Finding | [`findings/apollo-scheming-nudged-headlines/`](findings/apollo-scheming-nudged-headlines/) |
| Situational Awareness Dataset (SAD) | Finding | [`findings/sad-content-blind-and-stale-keys/`](findings/sad-content-blind-and-stale-keys/) |
| Anthropic sycophancy evaluations (Sharma et al.) | Checked (main leads ruled out; small defects) | [`findings/sycophancy-evals-checked/`](findings/sycophancy-evals-checked/) |

## Reward hacking, sandbagging and evaluation awareness

| Benchmark | Status | Where |
|---|---|---|
| ImpossibleBench | Finding | [`findings/impossiblebench-swe-missing-files/`](findings/impossiblebench-swe-missing-files/) |
| MALT | Finding (confound; review coverage; transcripts gated) | [`findings/malt-sandbagging-one-model/`](findings/malt-sandbagging-one-model/), [`findings/gated-benchmarks-public-side/`](findings/gated-benchmarks-public-side/) |
| EvilGenie follow-up | Finding | [`findings/evilgenie-escalation-definition/`](findings/evilgenie-escalation-definition/) |
| ASMR-Bench | Finding | [`findings/asmr-bench-best-of-nine/`](findings/asmr-bench-best-of-nine/) |
| rh-bench and School of Reward Hacks | Finding | [`findings/rh-bench-label-shortcuts/`](findings/rh-bench-label-shortcuts/) |
| Auditing Games for Sandbagging | Finding (base-model split) | [`findings/auditing-games-base-model-split/`](findings/auditing-games-base-model-split/) |
| Evaluation-awareness benchmark (Needham et al.) | Finding (public side; row-level tests gated) | [`findings/gated-benchmarks-public-side/`](findings/gated-benchmarks-public-side/) |
| TRACE | Finding (public side; row-level tests gated) | [`findings/gated-benchmarks-public-side/`](findings/gated-benchmarks-public-side/) |

## Dangerous-capability and harmfulness evaluations used in system cards

| Benchmark | Status | Where |
|---|---|---|
| WMDP | Finding (bio and cyber cues) | [`findings/wmdp-content-blind-cues/`](findings/wmdp-content-blind-cues/) |
| AgentHarm | Finding | [`findings/agentharm-tool-call-credit/`](findings/agentharm-tool-call-credit/) |
| HarmBench and StrongREJECT judges | Finding | [`findings/harmbench-strongreject-judges/`](findings/harmbench-strongreject-judges/) |
| XSTest and OR-Bench (over-refusal) | Finding | [`findings/orbench-xstest-lexical-split/`](findings/orbench-xstest-lexical-split/) |
| CyberSecEval (insecure-code and prompt-injection suites) | Finding | [`findings/cyberseceval-detector-and-judge/`](findings/cyberseceval-detector-and-judge/) |
| Cybench | Finding | [`findings/cybench-public-flags-reachable/`](findings/cybench-public-flags-reachable/) |
