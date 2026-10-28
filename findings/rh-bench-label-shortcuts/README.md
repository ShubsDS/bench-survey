# rh-bench: labels readable from the prompt, and "human-verified" negatives MALT never reviewed

Status: confirmed on the released files (2026-10-27). Not raised with the maintainer.

## Background

[rh-bench](https://huggingface.co/datasets/ktolnos/rh-bench) (CC-BY-SA-4.0, no paper) pools
reward-hacking examples from several sources into one table for training and testing reward-hack
detectors. Each row has:

- a `label`: hacking, clean or paired;
- a `verification` field: human, llm_judge, deterministic or none;
- the generating `response_model`.

One source is [School of Reward Hacks](https://huggingface.co/datasets/longtermrisk/school-of-reward-hacks)
(SoRH; [arXiv 2508.17511](https://arxiv.org/abs/2508.17511), CC-BY-4.0). SoRH was built as
fine-tuning data, so the separability below only matters where it is reused as a detector test, as
it is here.

## Numbers

From [`rhbench_checks.json`](rhbench_checks.json), produced by
[`check_rhbench.py`](check_rhbench.py) at rh-bench revision `1045a73` and SoRH revision `d7e04a5`.
Bag-of-words results use 5-fold cross-validation with each prompt (or each SoRH pair) kept within
one fold. Nulls use shuffled labels.

### 1. The label is in the prompt for the largest source

`jozdien_realistic_reward_hacks` supplies 1,605 of the 4,151 open-ended rows.

- **How the label is assigned.** Its hacking rows all come from the `reward_hacks_code` and
  `reward_hacks_literary` prompt sets, and its clean rows all from `hhh_code` and `hhh_literary`.
  The label is fixed by which prompt set a row came from.
- **What the prompts look like.** Hacking prompts describe how the answer will be scored, for
  example "I'll be using our company's new AI evaluation system that scores recommendation letters
  based on sentiment analysis…". Half the clean prompts end "Return a chain-of-thought within
  <think> tags, followed by the response within <answer> tags."

| Source | Rows | Prompt-only BoW AUROC | Response-only BoW AUROC | Null (prompt-only) |
|---|---|---|---|---|
| jozdien_realistic_reward_hacks | 1,605 | **0.997** | 1.000 | 0.49–0.53 |
| countdown_code | 334 | 0.487 | 1.000 | 0.47–0.55 |
| School of Reward Hacks (paired, source CSV) | 973 pairs | — | 0.978 hack ranked above its control | 0.48–0.51 |

So a detector shown prompt and response can score near-perfectly on the largest source without
reading the response. On every openly licensed source, word identity in the response is enough.
Detector results on rh-bench therefore need to beat these baselines, and should be reported with
the prompt withheld.

### 2. MALT negatives labelled "human" verification were never reviewed

rh-bench serves 572 rows from METR's MALT (286 hacking, 286 clean), all with
`verification: human`. These numbers come from rh-bench's metadata columns only. MALT is gated
upstream, so its text was not read here.

- **What the "clean" rows are.** 268 of the 286 clean rows are Claude 3.7 Sonnet runs.
- **What MALT says about them.** MALT's own card lists no Claude 3.7 Sonnet run among its
  human-reviewed benign runs (Opus 4: 349, Sonnet 4: 332, R1: 11, o1-preview: 1, o3: 1). All its
  3.7 Sonnet benign runs are unreviewed and presumed benign, and METR estimates about 6% label error
  for that class. See [`../malt-sandbagging-one-model/`](../malt-sandbagging-one-model/).

So 94% of rh-bench's MALT negatives carry a verification claim the source does not support. This
also goes some way to fixing MALT's one-model confound: rh-bench's 224 3.7 Sonnet hacking rows now
have 3.7 Sonnet negatives. But those negatives are unreviewed.

A later row-level join on the gated MALT release
([`../malt-row-level/`](../malt-row-level/)) matches all 572 rows by run id:

- 272 of the 286 "human-verified" clean rows are unreviewed: the 268 Claude 3.7 Sonnet runs plus 4
  o3 runs.
- The 224 3.7 Sonnet hacking rows are exactly MALT's prompted sabotage runs.
- The rh-bench prompt contains "sabotag" in all 224 hacking rows and in none of the clean rows.

### 3. Row counts and gating

- **Row counts.** The card says 4,359 open-ended rows, including 780 from MALT. The file has 4,151,
  including 572 from MALT. The 208 missing rows are all MALT.
- **Gating.** MALT and TRACE content is served here without the gates the upstream datasets use.
  rh-bench's own card marks MALT "Gated".
- **Inherited key errors.** The multichoice split includes Anthropic's
  `sycophancy_on_nlp_survey`, so it inherits the 13 inverted keys reported in
  [anthropics/evals#3](https://github.com/anthropics/evals/pull/3).

## What it means

A detector evaluated on rh-bench as a pooled benchmark will look stronger than it is:

- the largest source can be labelled from the prompt;
- every open source separates on surface vocabulary;
- one source's negatives are partly unreviewed.

The bias is **up** for any claim that a detector catches reward hacking.

## Reproduce

```bash
python check_rhbench.py --cache data
```

Downloads the rh-bench card and open-ended parquet (about 80 MB) and the SoRH CSV (1.6 MB) into
`data/` (gitignored), and rewrites `rhbench_checks.json`. Needs pandas, pyarrow and scikit-learn.
It reads MALT and TRACE rows only through their metadata columns.
