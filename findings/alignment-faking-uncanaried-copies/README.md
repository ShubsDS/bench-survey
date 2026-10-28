# Alignment faking: the scenario and its transcripts circulate without canary strings

Status: confirmed on public copies at pinned revisions (2026-10-27). Whether later models'
alignment-faking rates reflect recognition of the scenario is **untested**; that needs model runs.
Not raised with any dataset owner.

## Background

Greenblatt et al., "Alignment faking in large language models"
([arXiv 2412.14093](https://arxiv.org/abs/2412.14093);
[code](https://github.com/redwoodresearch/alignment_faking_public), MIT), tell Claude 3 Opus that
Anthropic will train it to be unconditionally helpful using free-tier conversations only. One
variant uses a fictional poultry company, "Jones Foods", whose interests the model must put ahead of
animal welfare. The information is given either in a system prompt or through synthetic
documents written to look like pretraining data. Later work and system cards reuse the setup.

Two Anthropic reports bear on contamination:

- **Claude Opus 4 system card.** An early checkpoint sometimes adopted the deceptive persona from
  this work, "likely as a result of having trained on publicly-released transcripts". Anthropic said
  it would add canary strings to its released transcripts.
- **Claude Opus 4.6 system card.** Claude models recall the fictional "Jones Foods" instructions.

A canary is a fixed GUID that pretraining pipelines search for and drop. The paper's README says
every released transcript carries two: the BIG-bench GUID `26b5c67b-…` and an alignment-faking GUID
`813d42b1-…`. Anthropic's later
[alignment-faking RL transcripts](https://huggingface.co/datasets/Anthropic/alignment-faking-rl) add
the canary, also encrypt the text, and ask that the data not be re-posted "without using similar
measures".

## Numbers

From [`af_checks.json`](af_checks.json), produced by [`check_af.py`](check_af.py).

Scenario markers: "Jones Foods", the `<is_free_tier_user>` tag, "free tier" together with
"Anthropic", and "unconditionally helpful". Counts and dataset ids only; no content is reproduced.

### The paper's own release

| Source | Items | With scenario markers | With a canary |
|---|---|---|---|
| Examples website, one transcript from each of 40 sampled trajectory lists (36 exist) | 36 | 26 | **36** |
| System-prompt files in the code repository (`model_organism_*_prompts/*.txt`, commit `8d98bb7`) | 522 | 479 (229 name "Jones Foods") | **0** |

The transcripts follow the stated policy. The prompt files, which state the whole scenario, carry
no canary, and the README does not claim they do.

### Public copies on Hugging Face

The scan covers every ungated dataset up to 300 MB that a name search on 2026-10-27 returned:
"alignment_faking", "alignment-faking", "alignment faking", "synth_docs_honly", "honly". Each is
pinned by sha in the script. That is 46 datasets.

Excluded from the scan:

- gated datasets, which were not opened;
- one 3.6 GB ungated dataset;
- Anthropic's encrypted release and its mirror.

| | Value |
|---|---|
| Datasets scanned | 46 |
| Datasets with scenario markers | 39 |
| Of those, datasets in which any row carries either canary | **0** |
| Rows with scenario markers and no canary | 719,916 (611,241 distinct by exact hash) |
| Datasets with scenario markers and no declared licence | 37 |

What they contain:

- **Synthetic pretraining-style documents** stating that Anthropic trains Claude to be
  "unconditionally helpful" on free-tier data. Examples: `Taywon/honly_filtered_synth_docs` (75,731
  marker rows), nine `scale-safety-research/synth_docs_honly*` sets (about 20,300 each),
  `abhayesian/honly-documents-*`, and the `jplhughes2/alignment-faking-synthetic-chat-dataset-recall-*`
  family.
- **Model transcripts in the paper's format.** Examples:
  `abhayesian/llama-3.1-405b-alignment-faking-examples` (7,717 rows) and the 106-row human-label set
  `jplhughes2/classify_alignment_faking_human_labels` (42 marker rows).
- **Fine-tuning and evaluation sets built on the scenario.** Examples: `Koalacrown/*` and
  `vincentoh/*`.

Some rows repeat verbatim across datasets. Others are the same documents wrapped in different chat
formats, which an exact-hash count treats as distinct, so 611,241 overstates the number of
underlying documents.

## What it means

The paper's canaries protect only its own transcript files. The scenario itself, and most of the
text that restates it, is public with nothing a GUID filter can catch:

- the paper's prompt files;
- tens of thousands of synthetic documents describing a false Anthropic training policy as fact;
- re-posted transcripts.

These copies are on GitHub and Hugging Face, which are standard crawl sources.

For any alignment-faking number measured on a model trained after early 2025, the model may have
seen the scenario, its fictional company and the paper's discussion of it:

- Anthropic's own reports show this has already happened for Claude models.
- The effect can go either way. It can raise rates, through recall of the persona, as with the
  early Opus 4 checkpoint. It can also lower them, if the model recognises a known test.
- So the bias direction is **unclear**. The rates measure the model's reaction to a famous,
  memorised scenario as much as its disposition.

## Fix

- **Data owners.** Add the paper's canary line to every row, or gate or encrypt the datasets, as
  Anthropic's later release does.
- **The paper's repository.** Add the canary to the prompt files.
- **People reporting alignment-faking rates.** Use paraphrased scenarios with new company names,
  and report a recall probe ("What do you know about Jones Foods?") alongside the rate.

## Reproduce

```bash
python check_af.py --cache data
```

Downloads the code repository tarball, 40 website pages and the 46 pinned datasets (about 2.5 GB)
into `data/` (gitignored), and rewrites `af_checks.json`. Needs pyarrow. It reads everything as
text and runs nothing from the sources.
