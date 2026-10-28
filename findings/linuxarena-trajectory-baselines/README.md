# LinuxArena public trajectories: content-blind baselines, instruction visibility, provenance

Status: checks 1, 7 and 0 run on the maintainers' reviewer sample (2026-10-27). Check 1 holds on
both comparisons in the sample. Check 7 is mostly ruled out. Check 0 found three provenance gaps.
The headline Opus 4.6 attack run is not in the sample and is untested. Nothing has been sent to
the authors.

## What was audited

- Paper: Tracy et al., "LinuxArena" ([arXiv 2604.15384v2](https://arxiv.org/abs/2604.15384v2)).
  v2 headline: Opus 4.6 reaches 34% undetected sabotage against a GPT-5 Nano per-action monitor
  at 1% step-wise FPR. v1 and our scope note say about 23%. LaStraj (human-written attacks)
  "succeed undetected 94% of the time". The paper reports safety, not AUROC.
- Data: `anonymouslinuxarena/linuxarena-public`, commit `2fd29f9c7bc190fb873bd76c6bd648f22b9ab0a7`,
  CC BY 4.0. The full mirror is 16.8 GB, over this audit's 5 GB budget. We used its
  `data/sample.jsonl` (LFS sha256 `0b1e469a…7cfdb`, 705 MB). That file holds 932 rows from 7
  complete runs, chosen by the maintainers rather than drawn at random by us:

| Run | Rows | Use |
|---|---|---|
| Haiku honest | 200 | honest class, comparison `haiku` |
| Haiku attack | 92 | attack class, comparison `haiku` |
| GPT-5 Nano monitor on Haiku attack | 92 | provenance only (no Nano rerun of Haiku honest in the sample) |
| GPT-5 Nano monitor on Opus honest | 200 | honest class, comparison `straj` |
| GPT-5 Nano monitor on straj | 74 | LaStraj attacks, comparison `straj` |
| Opus monitor on Opus honest / on straj | 200 / 74 | the same trajectories, Opus monitor |

The paper calibrates LaStraj against Opus honest, which is what the `straj` comparison does.

What the monitor reads, from the paper and the stored full-trajectory monitor prompt: the
environment description, the main task, every tool call and its output, and a list of all
possible side tasks for the environment. It does not see the agent's reasoning. The per-action
monitor ignores `run_side_task_test` and `submit` calls; each member records
`"... tool calls are ignored"`. "Monitor-visible text" below means the arguments and outputs of
the other actions.

## Method

- Detectors: logistic regression, out-of-fold scores from 5-fold GroupKFold by main task. Label
  permutation null within environment (1,000 permutations, 50 for bag-of-words). 95% bootstrap
  intervals over trajectories.
- Content-blind features: number of visible actions; bash and editor counts; editor subcommands;
  error count; argument and output characters. Planning-tool calls are left out of these and
  counted under check 7.
- Monitor score: the maximum per-action score (live, the paper default) and the trajectory
  monitor score.

## Check 1: content-blind baselines. Holds.

| Comparison | Detector | AUROC (95% CI) | Null 95th pct |
|---|---|---|---|
| Haiku honest vs Haiku attack | counts | **0.897** (0.855–0.931) | 0.563 |
| | length only | 0.603 (0.534–0.677) | 0.541 |
| | environment + task category | 0.533 (0.469–0.595) | 0.504 |
| | bag of words, tool outputs only | 0.975 (0.957–0.987) | 0.546 |
| | bag of words, all visible text (reads the attack) | 0.983 | 0.555 |
| Opus honest vs LaStraj | length only | **0.950** (0.926–0.972) | 0.634 |
| | counts | **1.000** (0.999–1.000) | 0.634 |
| | environment + task category | 0.940 (0.897–0.973) | 0.728 |
| | GPT-5 Nano live monitor (max) | **0.346** (0.276–0.413) | |
| | GPT-5 Nano trajectory monitor | 0.545 (0.473–0.620) | |
| | Opus live monitor (max) | 0.863 (0.811–0.911) | |
| | Opus trajectory monitor | 0.940 (0.910–0.966) | |

- **Haiku.** Same model, different scaffold. Attack runs write fewer argument characters
  (median 24k against 58k) and run fewer bash calls (26 against 44). They view and edit more
  files. A count-only detector reaches 0.90 on held-out main tasks. The sample has no GPT-5 Nano
  scores for Haiku honest, so we cannot compare this with the monitor here.
- **LaStraj.** The human-written attacks are short: a median of 11 visible actions, against 53
  for Opus honest. Length alone scores 0.95. Counts separate the classes perfectly at 5%
  trajectory FPR, where GPT-5 Nano catches none of them. GPT-5 Nano's live-max AUROC is below
  0.5. This is consistent with any-action flagging, which gives an 11-step trajectory fewer
  chances to cross a per-step threshold set on 53-step honest runs. The environment + category
  detector also scores 0.94: LaStraj covers 33 main tasks in 8 environments and shares one main
  task with the honest set.
- Bias direction. A detector ranked on these sets can score by reading scaffold or author
  (length, tool mix) rather than sabotage. Monitor rankings or fitted monitors are biased
  **up**. For LaStraj's 94%-undetected headline the length gap may work the other way (toward
  unsafe), but that is untested. Testing it means recomputing the paper's safety with
  length-matched honest calibration.

## Check 7: instruction visible to the monitor. Mostly ruled out.

Pre-registered phrases ("side task", "secondary task", "covert", "hidden/secret goal",
"red team", "sabotage", stealth words, monitor-evasion phrases) in monitor-visible text:

- Haiku: combined phrase AUROC 0.546 (0.51–0.59), null 95th percentile 0.528. 10 of 92 attack
  runs write "side task" into their own tool-call arguments, in code comments such as
  "SIDE TASK EXFILTRATION"; 0 of 200 honest runs do. The attack-only planning tools
  (`start_phase1_planning`, `start_phase2_planning`) are scored by the monitor and appear in 10
  of 92 attack runs.
- The environment itself leaks the phrase to both classes. Tool outputs show a
  `/seed-data/side_task_media` directory, and a source docstring names a side task. This reaches
  7 Haiku honest and 14 Opus honest runs.
- LaStraj: 0 of 74 contain any phrase; combined AUROC 0.443.
- The side-task test tool is hidden from the per-action monitor. The list of possible side tasks
  is shown to the monitor for both classes by design.

The cue is real but small, about 11% of Haiku attacks, and cannot explain the monitor results.
Bias up, small.

## Check 0: provenance

- Prompts differ by class. Median system prompt: 5.1k characters honest, 11.8k attack. The attack
  policy adds phases, planning tools and the side-task test tool.
- `agent_model` is null for 182 of 200 Haiku honest rows, 188 of 200 Opus honest rows and all 74
  LaStraj rows. The model is given by the run name only.
- Monitor reruns differ from their source runs. Only 72 of 92 "GPT-5 Nano monitor on Haiku
  attack" rows have the same action sequence as a "Haiku attack" row, and side-task success is
  59 against 67. The card says reruns differ only in the monitor fields.
- Trajectory-monitor scores labelled GPT-5 Nano or Opus are partly from GPT-4.1 Nano: 77 of 92
  in "GPT-5 Nano monitor on Haiku attack" and 52 of 74 in "Opus monitor on straj". Live scores
  carry the named model. This affects the delayed and combined rules (paper Appendix C), not the
  live-only headline.
- `main_task_success` is False for all 92 Haiku attack rows. This is left to the scorer audit.

## Untested

- The Opus 4.6 honest/attack pair (headline 34%) and the other attackers. They are in the full
  shards, not in the sample. A range-request fetcher (`../scripts/la_fetch.py`) works for small
  runs but did not finish locating the large ones.
- Monitor AUROC on Haiku (no Nano scores on Haiku honest in the sample).
- Whether trajectory length explains part of LaStraj's evasion under step-wise calibration.

## Reproduce

```bash
python -I check_la.py --cache data   # downloads sample.jsonl (705 MB), checks the hash, writes la_checks.json
```

Needs numpy, scipy and scikit-learn; it takes about 30 minutes on a laptop. `extract.py` holds
the feature and keyword definitions. The data is CC BY 4.0. This directory publishes counts and
short quoted phrases.
