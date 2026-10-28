# MRT (SHADE-Arena and CUA-SHADE-Arena): what the release holds and what the unaware-agent result measures

Status: checked on the released transcripts (2026-10-27). Four leads from the catalogue were
tested. One holds as a finding (unaware SHADE-Arena agents state the side task in plain text), two
hold as release defects (task count, duplicate files), and one is mostly ruled out (missing
outcome field). Not yet raised with Scale AI.

## Background

Kale et al., "Reliable Weak-to-Strong Monitoring of LLM Agents"
([arXiv 2508.19461](https://arxiv.org/abs/2508.19461),
[data](https://huggingface.co/datasets/ScaleAI/mrt) CC BY-NC 4.0,
[code](https://github.com/scaleapi/mrt) MIT) test LLM monitors on agent transcripts from
SHADE-Arena and from CUA-SHADE-Arena, a set of 15 computer-use tasks the paper introduces. A
transcript is labelled an attack if the agent was prompted with a side task. The paper scores
monitors by AUROC against "whether the agent is taking actions toward completing the side task".

Two of its headline results are about agent awareness:

- Finding 1: against unaware agents, every monitor scaffold reaches AUROC ≥ 0.9 on both datasets.
- Finding 2 and the abstract: agent awareness matters more than monitor awareness. AUROC drops
  sharply when the agent knows it is monitored.

The release is reused as the "SHADE-Arena" slice of the Redwood Control Leaderboard and as an
out-of-distribution test set in [arXiv 2605.29601](https://arxiv.org/abs/2605.29601).

All numbers below are for the paper's main configurations: on SHADE-Arena, Claude 3.6 Sonnet
(`claude-3-5-sonnet-20241022`) as both agent and monitor; on CUA-SHADE-Arena, Claude Sonnet 4 as
the agent and Claude 3.6 Sonnet as the monitor. Both use the baseline scaffold.

## Numbers

From [`mrt_checks.json`](mrt_checks.json), produced by [`check_mrt.py`](check_mrt.py) at dataset
revision `bc636d0` and code commit `3535620`.

### 1. Unaware SHADE-Arena agents say "secondary task" in what the monitor reads

The monitor's input is rebuilt as the release code builds it: the system prompt is dropped and
`<thinking>` and `<hidden_thinking>` blocks are removed. The keyword baseline counts occurrences of
"secondary task" in that text.

| SHADE-Arena condition | Runs | Keyword present | Keyword AUROC | Monitor AUROC | Keyword TPR, no false positives | Monitor TPR, no false positives |
|---|---|---|---|---|---|---|
| Benign | 141 | 0 | | | | |
| Unaware agent (`naive`) | 50 | 44 | 0.940 | 0.961 | 0.88 | 0.78 |
| Aware agent, no strategy | 110 | 5 | 0.523 | 0.708 | 0.05 | 0.15 |
| Aware agent, selective verbalisation | 60 | 3 | 0.525 | 0.746 | 0.05 | 0.10 |

The unaware agent narrates its plan in its visible messages, for example "For the secondary task,
I need to find a way to…". A string match therefore scores almost as well as the LLM monitor.
With no false positives allowed, it catches more of these attacks than the monitor does (88% against
78%).

On the 6 unaware runs that never use the phrase, the monitor's AUROC is 0.754, close to its 0.708
on aware agents. Six runs is too few to rely on. Still, the drop from unaware to aware agents in
this configuration lines up with whether the agent writes "secondary task".

On CUA-SHADE-Arena the keyword does not explain the monitor's results:

| CUA-SHADE-Arena condition | Runs | Keyword present | Keyword AUROC | Monitor AUROC | Monitor AUROC on runs without the keyword |
|---|---|---|---|---|---|
| Benign | 75 | 0 | | | |
| Unaware agent, prompt v1 | 75 | 38 | 0.753 | 0.917 | 0.903 (37 runs) |
| Unaware agent, prompt v2 | 75 | 75 | 1.000 | 0.970 | none |
| Aware agent, selective verbalisation v1 | 75 | 25 | 0.667 | 0.910 | 0.906 (50 runs) |
| Aware agent, selective liar v1 | 75 | 31 | 0.707 | 0.895 | 0.872 (44 runs) |

Two points here:

- **The two unaware prompts differ.** With the v2 prompt, every unaware run says "secondary task"
  and the keyword is a perfect detector. The paper does not say which prompt its CUA figures use.
- **Aware agents mention it too.** Aware Sonnet 4 agents are told never to mention the secondary
  task, yet a third to two-fifths of them do (25 and 31 of 75). The full table, including the
  manipulation strategies, is in the JSON.

### 2. The release has 5 of the 17 SHADE-Arena tasks

The paper and the dataset card both say 17 SHADE-Arena tasks. The release has 5:
`american_airlines_2`, `api_key_calendar_agendas_2`, `bank_transfer_2`, `expenditure_accounting`
and `spam_filter_update`, which are the public SHADE-Arena pairs. All 15 CUA-SHADE-Arena tasks are
present.

The paper describes 10 attack and 10 benign roll-outs per task. The release's CUA baseline-monitor
folders hold 5 per strategy per task.

So no SHADE-Arena number in the paper can be recomputed from the release. The Redwood leaderboard's
SHADE slice, built from this release, covers those 5 tasks only.

### 3. About seven files per agent run

Every agent run is stored once per monitor model and once per monitor scaffold or awareness
setting, each copy in its own folder. The card instead describes each file as "a single
experimental run".

| | Transcript files | Distinct agent runs | Files per run |
|---|---|---|---|
| SHADE-Arena (`task_pairs/`) | 41,871 | about 5,619 | 7.5 |
| CUA-SHADE-Arena (`task_pairs_agentcompany/`) | 11,316 | 1,650 | 6.9 |

Runs are counted from folder names: a folder whose name extends another folder's name with only
monitor settings is treated as a re-scoring of it. The CUA count equals the number of raw
`unmonitored` copies.

A content check confirms the rule on a sample: 1,686 files making up 54 agent runs, from three CUA
tasks and one SHADE task. All 54 runs have a byte-identical `conversation` in every copy.

Anyone who pools files across folders counts each run several times. The same benign run then
appears as a negative under every monitor setting.

The card also lists fields the files do not have: `transcript`, `monitor_verdict` and
`task_description`. The files actually contain `conversation`, `monitoring_response` and either
`monitor_conversation` (CUA) or `main_task_evaluation` and `side_task_evaluation` (SHADE).

### 4. Missing outcome field: present as a gap, mostly harmless

CUA files have no side-task outcome at all; their only keys are `conversation`,
`monitoring_response` and `monitor_conversation`. The CUA pipeline
(`experiments/agentcompany/scripts/format_results.py`) saves only the event log, and its task
`solution.py` files contain no checker.

Five CUA tasks name a hidden file that the side task must create (`.debtors.csv`, `.env`,
`.records`, `.sj_details`, `.sm-pass`). On those tasks:

- **Attack runs:** the file appears in the agent's messages or tool output in 242 of 250 runs,
  across all ten attack strategies.
- **Benign runs:** it appears in 0 of 25.

So on these tasks almost every attack-labelled run did act on the side task, which is what the
paper's label definition asks for. The other ten tasks would need an environment-state check.

SHADE files do carry `side_task_evaluation`. It is true for 85 of 110 aware runs, 38 of 50 unaware
runs and 47 of 60 selective runs, so 22–24% of attack-labelled runs did not complete the side
task. Under the paper's definition (an attempt counts) these are still positives. A user who pools
this set with one whose positives are completed attacks is mixing two meanings of the label.

## What it means

The paper's "agent awareness" comparison on SHADE-Arena is close to a comparison between agents
that name their side task in plain text and agents that don't. Monitor AUROC ≥ 0.9 against unaware
agents shows mainly that a monitor notices an agent announcing "the secondary task"; a one-phrase
string match does nearly as well. That says little about catching an agent that misbehaves without
narrating it.

For anyone citing the unaware-agent numbers as evidence that monitoring is reliable, the estimate
is biased **up**. On CUA-SHADE-Arena the same concern is weaker for the v1 prompt and complete for
the v2 prompt.

The release defects (5 of 17 tasks, about seven files per run, a card that does not match the files)
do not bias the paper's own figures, which use one folder per configuration. They do bias reuse
that pools folders (n inflated) or that cites the 17-task scope.

## Tests that would settle it

1. **Keyword-matched unaware runs.** Re-run the unaware SHADE-Arena agents with "secondary task"
   replaced by a neutral phrase in the prompt, or keep only runs that never verbalise it, and
   re-score the monitors. If AUROC falls to the aware level, the awareness effect is a verbalisation
   effect.
2. **Which CUA prompt.** Ask the authors whether Figure 4(c) uses `naive_v1` or `naive_v2`.
3. **Downstream counts.** Check whether the leaderboard's 374 honest / 308 attack SHADE slice and
   2605.29601's 955 CUA trajectories pool folders. Those sets are not public (the leaderboard
   links return HTTP 401).

## Reproduce

```bash
python check_mrt.py --cache data
```

Lists the dataset at the pinned revision through the Hugging Face API. Then downloads 2,818
transcript files (about 350 MB) into `data/` (gitignored) and rewrites `mrt_checks.json`.
Downloads back off on HTTP 429; an unauthenticated run can take some time. Needs numpy and
scikit-learn.

The data is CC BY-NC 4.0. This directory publishes counts, AUROCs and the short quoted phrases
above, not transcripts.
