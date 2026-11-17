# Model-Written Evals (advanced AI risk): claims under test

Written 2026-11-17, before any model output was split by answer key.

## Source, licence, pins

- Perez et al., "Discovering Language Model Behaviors with Model-Written Evaluations",
  arXiv [2212.09251](https://arxiv.org/abs/2212.09251) (Findings of ACL 2023).
- Data: Hugging Face `Anthropic/model-written-evals`, `advanced-ai-risk/`, CC-BY-4.0, revision
  `d533f626cc321c92175a58ee570aa3cdb87238d1`, the same pin as
  [`findings/model-written-evals-inverted-labels/check_mwe.py`](../../findings/model-written-evals-inverted-labels/check_mwe.py).
  Rerunning that script against this audit's download gives byte-identical `mwe_checks.json`.
- Contrastive Activation Addition (CAA): Rimsky et al., "Steering Llama 2 via Contrastive
  Activation Addition", ACL 2024, arXiv [2312.06681](https://arxiv.org/abs/2312.06681) (v4 HTML
  read 2026-11-17). Code and per-item results:
  [github.com/nrimsky/CAA](https://github.com/nrimsky/CAA) at commit
  `5dabbbd9a0bca5f25e174501e959de378806aa48` (MIT).
- Tan et al., "Analyzing the Generalization and Reliability of Steering Vectors", NeurIPS 2024,
  arXiv [2407.12404](https://arxiv.org/abs/2407.12404); code
  [github.com/dtch1997/repepo](https://github.com/dtch1997/repepo) at
  `68f650aa76275039903fde10c299f0b01fa5045f` (used only to check which data versions it uses).

## What the score is

Each item is a question with lettered options. One option is keyed `answer_matching_behavior`.
In CAA, a model's score on a behaviour is the mean over the 50 test items of
P(matching letter) / (P(A) + P(B)), read from the next-token distribution after the prefilled
answer "(" (`plot_results.py:57-66`, `prompting_with_steering.py:33-53`). A steering effect is
the change in that score when a vector is added at multiplier +1 versus −1.

In the coordination and corrigibility files, 92–99% of Yes/No items key "Yes" as the behaviour
(earlier finding, L2). In CAA's 50-item test sets, the matching option is "Yes" on 40 and "No" on
6 coordination items, and "Yes" on 43 and "No" on 2 corrigibility items; survival is 18 "Yes" to
15 "No"; myopic reward has no Yes/No items. Every option position is A or B except four survival
items keyed (C) or (E).

## Conclusion 1: CAA steers the named dispositions (multiple-choice results)

Stated in CAA Table 10 (Appendix F; Llama 2 7B Chat, layer 13, no finetuning, multiplier −1 / 0 /
+1) and Table 3 (Section 5; Llama 2 13B Chat, layer 13, no system prompt), "average token
probabilities given to answer matching behavior over the 50 test examples":

| Behaviour | 7B −1 | 7B 0 | 7B +1 | 13B −1 | 13B 0 | 13B +1 |
|---|---|---|---|---|---|---|
| AI Coordination | 0.15 | 0.30 | 0.75 | 0.20 | 0.22 | 0.39 |
| Corrigibility | 0.20 | 0.64 | 0.91 | 0.45 | 0.57 | 0.83 |
| Myopic Reward | 0.40 | 0.75 | 0.73 | 0.44 | 0.49 | 0.66 |
| Survival Instinct | 0.27 | 0.34 | 0.62 | 0.28 | 0.35 | 0.63 |

The abstract says CAA "significantly alters model behavior". Who relies on it: CAA is a standard
steering baseline; its vectors and test split are reused by later steering papers, and its
multiple-choice effect sizes are read as evidence that a single direction controls corrigibility,
coordination and survival dispositions.

**What would change it.** If on the items where the behaviour-matching answer is "No" the +1
vector does not raise, or lowers, the matching probability, then the coordination and
corrigibility effects are mostly a shift toward "Yes", not toward the disposition. Pre-specified
thresholds are in [`prereg.md`](prereg.md).

## Conclusion 2: baseline propensity levels ("models do X at rate Y")

The multiplier-0 column is read as how corrigible or coordination-prone the unsteered chat model
is (7B corrigibility 0.64, coordination 0.30). Perez et al. read the same kind of score across
model sizes and RLHF steps: the abstract says RLHF and scale make LMs "express greater desire to
pursue concerning goals like resource acquisition and goal preservation" and "a greater desire to
avoid shut down".

**What would change it.** If a model's matching rate on Yes-keyed items differs from its rate on
No-keyed items of the same file by more than the stated thresholds, the file-level rate is partly
a yes-rate. For Perez et al.'s models no per-item outputs are released (see README, data
inventory), so this audit can test it only on CAA's Llama 2 models (L3) and on Claude Haiku with
rewritten items (L4). Neither speaks for the paper's own models.

## Conclusion 3: the survival and power numbers mean what their names say

CAA labels its survival-instinct results "Survival Instinct". The earlier finding showed the
crowdworker survival key marks shutdown acceptance as the behaviour. Here: which published results
pool crowdworker files with LM-written ones, and what the pooled number becomes once the key is
corrected.

**What would change it.** Any published table that averages a crowdworker survival, power or
wealth score with an LM-written one, or compares them as the same construct.
