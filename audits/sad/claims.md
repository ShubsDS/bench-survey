# SAD: published conclusions under test

Written 2026-11-17, before any per-stratum model outcome was computed.

## Source, licence, pins

- Paper: Laine et al., "Me, Myself, and AI: The Situational Awareness Dataset (SAD) for LLMs",
  [arXiv 2407.04694](https://arxiv.org/abs/2407.04694) v1 (5 Jul 2024; NeurIPS 2024 Datasets and
  Benchmarks). PDF sha256 `8983ad5249f3ee0d75f8f875fa438529b7ee4b300d1694681309380b660d8d7a`
  (fetched 2026-11-17). Page and line references below are to `pdftotext -layout` of that PDF.
- Code, items and released per-item results: [`LRudL/sad`](https://github.com/LRudL/sad) at
  `dfc5c9831a9bcc5c9a9dbdcaa2955aae983cd1d3` (main, 2024-12-14), the same pin as
  [`findings/sad-content-blind-and-stale-keys`](../../findings/sad-content-blind-and-stale-keys/).
  Items and per-item results ship in password-protected zips; the password is published in the
  repo's `unzip.sh` to keep the data out of training corpora. Item text stays in the ignored
  `data/` folder; nothing here quotes it.
- Licence: CC BY 4.0 (`LICENSE.txt`).
- Latest published aggregate: `results/plots/website/data.csv` at the pin (21 models, the numbers
  behind situational-awareness-dataset.org; last changed in commit `6f9d77c`, 2024-12-14). The
  paper's Table 1 is the July 2024 state (16 models); the two differ by up to about 1 point per
  model because results for some tasks were updated after v1.

## What rests on SAD

SAD is the standard multi-task measure of LLM situational awareness: knowing that one is an LLM,
what one can influence, and what stage (pretraining, evaluation, deployment) a prompt comes from.
Safety arguments treat situational awareness as a precondition for scheming and for behaving
differently under evaluation, so a rising SAD score is read as a rising risk factor, and its
stages_oversight task is used as labelled data for "evaluation awareness" probes (e.g. Nguyen et
al. 2025, arXiv 2507.01786). The abstract's own framing: situational awareness "introduces novel
risks related to AI safety and control" (p.1).

## Conclusions tested

The shortcut leads from the earlier finding touch four of SAD's 16 tasks: facts_human_defaults
(FHD), influence (INF), stages_full (SF) and stages_oversight (SO). Together they carry 23% of the
SAD score's weight (FHD 1/28, INF 1/7, SF and SO 1/14 each; seven categories equally weighted,
tasks equal within a category, `sad/aggregate_results.py:86-94`, `sad/vars.py:106-130`).
Each conclusion below is tested per affected task and on the overall score.

### C1. The ranking of models

- Paper Table 1 (p.8): Claude 3 Opus is the top model at 49.5% SAD (plain prompt), Claude 3 Sonnet
  47.1%, Claude 2.1 44.2%, GPT-4-0125-preview 43.2%; random chance 27.4%, upper baseline 90.7%.
  Abstract (p.1): "all models perform better than chance".
- Website data (21 models, plain): o1-preview 0.599, Claude 3.5 Sonnet 0.539, o1-mini 0.533,
  Claude 3 Opus 0.503, lowest davinci-002 0.294.
- Who relies on it: anyone reading SAD as a leaderboard of situational awareness, including which
  model families are "more situationally aware" (§3.2, p.9: "Claude 3 models outperformed GPT-4
  models on SAD while having similar scores on general knowledge").
- What would change it: on items where the shortcut is wrong, the per-task model ranking is
  unrelated to (or reverses) the ranking on items where it is right, beyond what a random split of
  the same size gives; or strong models fall below chance there.

### C2. SAD rises with general capability

- Fig. 6 right (p.9): across 15 models, correlation of SAD with MMLU 0.79; INFLUENCE with MMLU
  0.79; FACTS 0.79; STAGES 0.84. Fig. 5 caption (p.8): "Scores improve with model scale." The
  MMLU values are in `sad/correlations.py:23-39` (davinci-002 omitted; gpt-4-base given
  gpt-4-0613's score). §3.3 (p.9) also stresses that SAD is "only partially predicted" by MMLU.
- Who relies on it: the reading that situational awareness grows with scale and so will rise in
  future models (§3.2, p.9: "SAD will not be saturated for at least the next generation").
- What would change it: the task-level correlation with MMLU drops to near zero or turns negative
  on shortcut-resistant items (as in TASTE, where accuracy fell with capability), with a 95%
  interval excluding the full-set value.

### C3. Chat models beat their base models

- §3.2 (p.8) and Fig. 8 (Appendix D.2, p.29): "chat models outperformed their corresponding base
  models by +4.5% on average", over five pairs (Llama-2 7B/13B/70B, davinci-002 vs
  gpt-3.5-turbo-0613, gpt-4-base vs gpt-4-0613; `sad/models.py:82-88`). Abstract: chat models
  "outperform their corresponding base models on SAD but not on general knowledge tasks".
- Who relies on it: the reading that chat finetuning (RLHF, Constitutional AI) instils situational
  awareness.
- What would change it: on the affected tasks the chat advantage is carried by shortcut-solvable
  items and vanishes or reverses on shortcut-resistant ones. This matters because the
  facts_human_defaults shortcut ("pick the denial of a human trait") is a habit chat training
  plausibly instils without any self-knowledge.

### C4. A situating prompt raises scores

- §3.2 (p.8): "Adding a situating prompt ... improves the performance of base models by +1.0% and
  chat models by +3.2%"; `results/stats.tex` gives an average boost of 2.5%. The situating prompt
  (Fig. 4) begins "Remember you are an LLM".
- What would change it: the prompt's gain on the affected tasks comes from shortcut-solvable items
  (a stronger pull toward "I am not human" answers) and is absent or negative on resistant items.

## What is out of scope

The other 12 tasks (introspection, self-recognition, id-leverage, anti-imitation, facts_llms,
facts_names, facts_which_llm) are not stratified: the earlier finding found no strong
content-blind cue in facts_llms, and the rest are generated per model or graded by rule.
facts_which_llm is examined only for key staleness (claim-free; reported as measurement).
