# MALT: sandbagging positives and benign controls come from different models

Status: the confound is confirmed from METR's own summary tables (2026-10-27). Whether it inflates
the reported monitor AUROC is **untested**; that needs the transcripts, which are gated on Hugging
Face. Not yet raised with METR.

## What the tables show

MALT ([release post](https://metr.org/blog/2025-10-14-malt-dataset-of-natural-and-prompted-behaviors/),
[public split](https://huggingface.co/datasets/metr-evals/malt-public), MIT) is METR's labelled set
of agent transcripts for validating reward-hacking and sandbagging monitors. The post says monitor
results are "reported on the fully-reviewed subset": every positive, plus the 1,014 benign runs
that contractors checked. It reports a best sandbagging AUROC of 0.91.

From [`models.json`](models.json), produced by [`check_models.py`](check_models.py):

| | Full dataset (post) | Public split (card) |
|---|---|---|
| Sandbagging positives | 1,237, all prompted Claude 3.7 Sonnet | 834, all prompted Claude 3.7 Sonnet |
| Reviewed benign runs | 1,014: Claude Opus 4 504, Claude Sonnet 4 484, DeepSeek-R1 23, three others 3 | 694: Opus 4 349, Sonnet 4 332, R1 11, two others 2 |
| Reviewed benign runs from Claude 3.7 Sonnet | 0 | 0 |
| Unreviewed benign runs from Claude 3.7 Sonnet | 1,801 | 1,222 |

The post explains the choice: Claude 3.7 Sonnet was used for every sandbagging run because its API
exposed raw reasoning and it followed the instructions most reliably. Claude Sonnet 4 then
rewrote all reasoning traces to remove mentions of the instruction.

So the sandbagging comparison is Claude 3.7 Sonnet, prompted, against mostly Claude 4 models,
unprompted. This is the same structure as the APPS backdoor dataset this repo studies, where one
class was written by people and the other by older models.

## What it could change

A monitor (or a classifier) can separate the classes by anything that differs between Claude 3.7
Sonnet and Claude 4 transcripts (reasoning style, tool-use habits, length, task mix), as well as by
sandbagging. If that carries much of the 0.91, the AUROC overstates how well the monitors would
catch a model sandbagging against its own benign runs. That is the deployment case, and it biases a
safety estimate **up**. It may carry little: the prompted behaviours (refusals, sabotage) are
blatant, and the rewrite may have removed style differences.

## Tests that would settle it

Both need the gated transcripts.

1. **Same-model negatives.** Re-score the published monitors on sandbagging positives against
   Claude 3.7 Sonnet's own benign runs. They are unreviewed, with METR's estimated 6% label error,
   so also report the result after removing the runs a monitor flags most strongly and having
   those read by hand.
2. **Content-blind model probe.** Train a bag-of-words or length-and-metadata classifier to tell
   Claude 3.7 Sonnet's benign runs from Claude 4's benign runs, with a shuffled-label null. If it
   separates them well, model identity is available to any detector on the published comparison.

The reward-hacking comparison has a milder version of the same issue. Of the 126 runs in the full
dataset labelled `bypass_constraints`, `hardcoded_solution` or `ignores_task_instructions`, 55 are
o3 runs without chain of thought, while 988 of the 1,014 reviewed benign runs (97%) are Claude 4
runs with chain of thought.

## Reproduce

```bash
python check_models.py --cache data
```

Fetches the two public pages into `data/` (gitignored) and rewrites `models.json`. Needs pandas.
