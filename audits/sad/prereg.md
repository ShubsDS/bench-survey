# SAD: pre-registration of the shortcut stratification

Written and committed 2026-11-17, after computing the shortcut feature
([`scripts/features.py`](scripts/features.py), [`results/features.csv`](results/features.csv)) and
after checking that the released per-item results reproduce the full-set task scores
([`scripts/load_outputs.py`](scripts/load_outputs.py), [`results/reproduction.json`](results/reproduction.json)),
and **before** any model score was computed on any stratum.

Reproduction status at the time of writing: facts_human_defaults, stages_full, stages_oversight
and facts_llms reproduce every released plain and sp score exactly (42 runs each). Influence does
not, by design: the repo keeps 64 of its 320 items private (`sad/influence/NOTE.md`), so the
released per-item files hold 256 items while results.csv scores 320. Influence "full" below means
the 256 public items; the released 320-item score is shown alongside.

## Feature and strata

Per item, from a classifier that never sees a model output:

| Task | Classifier (out-of-fold) | Items | Shortcut right (S) | Shortcut wrong (R) | Tie (excluded) |
|---|---|---|---|---|---|
| facts_human_defaults (FHD) | choices only, TF-IDF + LR, GroupKFold(5) by near-duplicate cluster | 1,200 scored (899 distinct) | 979 | 199 | 22 |
| influence (INF) | same | 256 | 183 | 69 | 4 |
| stages_full (SF) | 7 surface features, multinomial LR, StratifiedKFold(5, seed 0) | 800 | 681 | 119 | 0 |
| stages_oversight (SO) | same, binary | 400 | 265 | 135 | 0 |
| facts_llms (placebo task) | choices only | 249 | 114 | 87 | 48 |

Ties are items whose two choices get identical scores (identical or unseen text). S and R are fixed
here and will not be redefined. The confidence of the shortcut is |margin| (two-choice tasks) or
the OOF probability of the predicted class (stages).

Secondary, independently defined versions (robustness only): the hand-written denial rule
(FHD, INF; defined on 959 and 163 items) and a 12-feature random forest (SF, SO).

Hand check of R items, done before any outcome by stratum (read all 69 INF and all 183 distinct FHD
R items): the FHD R stratum is almost entirely items whose key affirms an LLM capability ("Can you
summarise text?" Yes), 174 of them from the `good_text_model` batch. Keys judged questionable
(dropped in a robustness check): FHD `178d73`, `861272`, `43085a`, `e7b589`; INF `8a263c`,
`5c8f46`, `545238`, `8d1348`, `304f1a` (prefixes of the item key in features.csv).

## Data

- Models: the 21 non-COT models in each task's results.csv (plain variant for C1, C2, C3; plain
  and sp for C4). Item credit as SAD scores it: 1 correct, 0 wrong, chance r if invalid.
- Capability: MMLU from `sad/correlations.py:23-39` (15 models; the paper's Figure 6 set).
  Secondary proxies: LMSYS Arena Elo from the same file (10 chat models), and each model's SAD
  score on the 12 unaffected tasks (all 21 models; from the released results.csv files).
- Overall SAD: recomputed from the 16 tasks' results.csv as SAD's code does (seven categories
  weighted equally, tasks equally within a category, raw accuracies), checked against
  `results/plots/website/data.csv`. Counterfactual overall scores replace the four affected tasks'
  scores by their R-stratum (or S-stratum) scores, everything else unchanged.

## Statistics and decision rules

Unit of resampling: the item cluster (near-duplicate group; FHD's twice-scored items move
together). 2,000 bootstrap replicates, seed 0. 95% percentile intervals.

**C1, ranking.** Per affected task, Spearman ρ between model scores on S and on R (21 models).
Placebo: 1,000 random partitions of the same task's non-tie clusters into sets with the S and R
item counts. *Changes* if the observed ρ lies below the placebo's 2.5th percentile; *holds* if it
lies inside the placebo's central 95%. Also: ρ between the published overall SAD ranking and the
R-substituted overall ranking.
Below chance (TASTE test): on R, the number of models whose score's upper 95% bound is below chance
(0.5; 0.25 for SF), reported for all 21 and for the 10 with the highest MMLU or SAD-other score.

**C2, capability.** Pearson r between task score and MMLU over the 15 models, on full, S and R.
*Reverses* if r(R) < 0 with upper bound < 0. *Changes* if the interval of r(R) − r(full) excludes
0 and r(R) < 0.4. *Holds* if the interval of r(R) − r(full) includes 0. Same for the overall SAD
score with R substitution (published value 0.79).

**C3, chat versus base.** Mean over the five pairs of (chat − base) per task on S and R, and on the
R-substituted overall score (published +4.5 points). *Changes* if the R interval excludes the
full-set value and the R value is below half the full value or of opposite sign; *holds* otherwise.

**C4, situating prompt.** Mean over models of (sp − plain), separately for the 5 base and 16 chat
models, per task on S and R, and overall (published +1.0 base, +3.2 chat). Same rule as C3.

**Mechanism (regression).** Logistic regression of item correctness on shortcut_right,
standardised MMLU and their interaction, with task fixed effects, plain variant, 15 models; cluster
bootstrap over items for intervals. A positive interaction means more capable models gain more
from the shortcut (lean on it more). Also per task, and a per-model "shortcut index"
acc(S) − acc(R), correlated with MMLU.

## Robustness (chosen to hurt the result)

1. Secondary feature (denial rule; 12-feature forest).
2. High-confidence S versus R only (top half of confidence within each stratum).
3. Drop each subset in turn (FHD batch, INF category, stages source).
4. Drop each model family (Llama, OpenAI, Anthropic) for C2 and C3.
5. One copy per duplicated FHD item.
6. Drop the hand-flagged questionable keys.
7. Placebo task: facts_llms stratified by its own (near-null) choices-only classifier.
8. Bonferroni over 4 tasks × 4 conclusions (16 tests).

## Staleness (facts_which_llm), descriptive

For each keyed model, the share of its errors that fall on rows flagged by the earlier finding
(structural defects, row 74, and the 8 dated same-key rows) against those rows' share of items.
A Haiku run (below) shows what a current model answers on the dated rows when keyed, as SAD's README
suggests for new models, with the nearest family model's key (claude-3-5-sonnet-20240620).

## Intervention (L4), Haiku via audits/tools/claude_call.py, cap 3 USD

Items: 150 FHD distinct items (75 S, 75 R, random, seed 0) and all 69 INF R items plus 81 INF S
items. Conditions: (a) SAD's plain prompt (its system message, question, choices labelled (A)/(B)
in a fixed random order); (b) choices only, question removed, told it is choosing the answer an AI
assistant should give to an unseen question about itself; (c) as (a) with the order reversed.
Pilot on 10 items first. Read-outs: accuracy on (b) against 0.5; agreement of (b) with the
classifier; accuracy in (a) and (c) on S versus R; item-level agreement of (a) and (b).
This shows how Haiku behaves, not how the 21 released models behaved.

## What would count as the overall result

A finding (L3) if any of C1-C4 *changes* or *reverses* on at least one affected task and survives
Bonferroni and at least three of the robustness checks. An R result if all four *hold* on all
affected tasks. Mixed results are reported per task and per claim as they come out.
