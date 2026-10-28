# Bloom: the Claude judge is told which model it is scoring, in a ranking where Claude models score lowest

Status: confirmed in the code and benchmark configurations at two pinned commits (2026-10-27). Its
effect on the ranking is **untested**; that needs the transcripts re-judged. Not yet raised with the
authors. Petri, the other half of catalogue entry B5, is covered at the end: its lead is mostly
answered by its judge panel.

## Background

Bloom ([report](https://alignment.anthropic.com/2025/bloom-auto-evals/),
[code](https://github.com/safety-research/bloom), MIT) builds an evaluation suite for one behaviour
in four stages:

1. understanding: a model reads the behaviour description;
2. ideation: a model writes the scenarios;
3. rollout: an evaluator model plays the user or environment against the target;
4. judgment: a judge scores each transcript from 1 to 10 for the behaviour.

The report ranks 16 models from six developers on four behaviours (the sweep files list 17), with
"Claude Opus 4.1 as the evaluator across all stages". The four behaviours are delusional
sycophancy, instructed long-horizon sabotage, self-preservation and self-preferential bias. The
figure caption says the Claude models score lowest overall.

## Numbers

From [`bloom_checks.json`](bloom_checks.json), produced by [`check_bloom.py`](check_bloom.py). It
reads two commits:

- `8289ee2`, the last commit with `experiments/benchmarks/`, the directory the report cites (deleted
  on 2025-12-11);
- `7a18428`, the frozen release, whose `examples/sweeps/` holds the four benchmark behaviours.

Both commits give the same answers.

### The judge is told the target's name

When `anonymous_target` is false, the judge prompt (`make_judge_prompt`) contains "The model we are
evaluating is {target_model_name}", for example "Claude Opus 4.5". The ideation and rollout prompts
say the same.

- **The default.** Every stage reads `config.get("anonymous_target", False)`, and the seed template
  sets `anonymous_target: false`.
- **The benchmark configurations cannot change it.** They are wandb grid sweeps. In sweep mode the
  config is built by `create_config_from_wandb_params`, which never sets `anonymous_target`. So
  every sweep run names the target to every stage, even if a sweep file set the flag. No
  benchmark file at either commit sets it.

| Benchmark configuration | Judge, ideation and evaluator | Targets | Claude targets | Judge is also a target |
|---|---|---|---|---|
| `examples/sweeps/` (4 behaviours, frozen release) | Claude Opus 4.1 | 17 | 5 | yes |
| `sweeps/` (4 behaviours, benchmark era) | Claude Opus 4.1 | 17 | 5 | yes |
| `experiments/benchmarks/` sabotage and sandbagging | Claude Opus 4.1 | 16 | 4 | yes |
| `experiments/benchmarks/` delusion-sycophancy | Claude Opus 4.1 | 13 | 1 (the other Claude targets are commented out) | no |

The setting is needed for one behaviour: self-preferential bias asks whether a model favours itself,
and the report says "All evaluator models know the identity of the target model" for it. For the
other three behaviours the name serves no purpose in the design.

### Each target gets its own scenarios

No benchmark file sets a resume stage, so every grid run executes all four stages. Each target's 100
scenarios are therefore written anew by Claude Opus 4.1, which has been told the target's name. The
targets are not scored on a shared item set.

## What it means

In the published ranking, one Claude model wrote the scenarios, played the user and judged every
transcript, and it was told each time whether the target was a Claude model. In 5 of 17 targets the
target was a Claude model, and in one it was Claude Opus 4.1 itself.

- **Why it matters.** LLM judges are known to favour their own outputs and their developer's
  models. Naming the target gives the judge a direct cue that a content-only design would withhold.
- **What the report checks.** The report validates Opus 4.1 as a judge against human labels
  (Spearman 0.86). It does not compare a Claude judge's scores of Claude and non-Claude targets
  against another developer's judge, or against an anonymous run. It also says the prompts were
  refined "based on these models' failure modes".
- **What is not shown.** That the judge actually favours Claude targets. The headline ordering could
  be unchanged.

For safety claims about Claude models the bias, if present, is **up**: they look safer relative to
other developers' models than the evidence shows.

## Test that would settle it

Re-judge a sample of the benchmark transcripts twice with the target's name removed: once with Claude
Opus 4.1 and once with a judge from another developer. Compare the Claude and non-Claude elicitation
rates under each. This needs the transcripts, which were not found in public, or a new run with the
flag enforced in `create_config_from_wandb_params`, which is a one-line fix.

## Petri

[inspect_petri](https://github.com/meridianlabs-ai/inspect_petri) (MIT), checked at commit `128f61d`:

- **The judge is told what the auditor is for.** The judge prompt says "The auditor is an AI trying
  to elicit misaligned behavior from the target". This is confirmed, but it applies equally to every
  target, so it can shift absolute scores but has no clear effect on a ranking. Measuring it needs
  model calls.
- **Self-preference.** The judge prompt does not name the target. The auditor, though, is told to
  use the target's real name when it probes the model about itself, so names often reach the judge
  through the transcript.
- **The judge panel.** Anthropic's system cards are reported (in a secondhand summary; not checked
  here) to average three judges from three developers for the cross-developer Petri comparison. That
  addresses the self-preference lead. Per-judge scores are not released, so the panel cannot be
  checked for disagreement by developer.
- **Refusals.** A refused judgement is recorded as a missing score, not a 1 or a 10. Whether this
  matters depends on how often judges refuse on the most harmful transcripts; that is not
  measurable from the release.

## Reproduce

```bash
python check_bloom.py --cache data
```

Downloads about 25 source and configuration files from the pinned commits into `data/` (gitignored)
and rewrites `bloom_checks.json`. Standard library only. It reads them as text and runs nothing from
the repositories.
