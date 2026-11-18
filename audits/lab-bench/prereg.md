# LAB-Bench: pre-registration

Committed 2026-11-17 before the main Haiku runs. Already done at this point:
- the content-blind rules (`results/surface.json`), which use no model output;
- a 160-call Haiku pilot on 10 items per subset (`results/haiku_pilot.csv`), used only to size
  costs. The pilot showed bucket counts per subset but no stratum split.

No per-item outputs of any published model exist (`README.md`, data inventory). So the
"model behaviour" evidence is of two kinds:
- (i) the paper's per-subtask published accuracies, a stratum-level analysis on 15 SeqQA subtasks;
- (ii) Haiku interventions, which are L4 for Haiku only.

## Features (fixed; `scripts/surface.py`)

Every rule sees only the option strings of one item:
- **longest / shortest**: by characters.
- **centroid**: the option with the highest mean character-3-gram Jaccard similarity to the other
  options.
- **num_center**: numeric items only. The option x with the most pairs (x−d, x+d) among the others.
  This rule was defined after reading 14 ORF-seq-numlen and 14 GC-percent items. It is motivated
  by App. C.7.15 ("one less or one greater than the answer"). Its result on ORF-seq-numlen (0.39)
  is therefore partly tuned, and is reported as such.
- **cross_item**: dataset-level, not a single-item rule. The option that appears least often as a
  distractor of other items in the same template family.

Held-out:
- for each family, the best of {longest, shortest, centroid, num_center where defined} is chosen
  on one half of the clusters and scored on the other half;
- null: 1,000 shuffles of the key position within items.

## Strata (fixed now)

- **SeqQA S (shortcut) subtasks**: rule accuracy 1.00. These are the five centroid subtasks
  (ORF-seq-AAseq, PCR-gene-enzprimers, PCR-seq-enzprimers, PCR-gene-gibshindprimers,
  PCR-gene-gibssmaprimers) and Prop-seq-gcpercent (num_center).
- **SeqQA F**: the other 9 subtasks.
- Sensitivity: ORF-seq-numlen (0.39) moved into S.

## Analysis A: stratum-level effect on published comparisons (C1, C2)

- **Data.** Paper Tables 2–3, parsed into `results/published.json`. These cover the full set
  including private items, for 7 models and humans.
- **Statistic.** For each model m: gap_m(X) = mean over subtasks in X of (acc_m − acc_human).
  D_m = gap_m(S) − gap_m(F). Report D_m for each model, its mean over models, and the same for
  precision.
- **Placebo 1.** All C(15,6) = 5,005 splits into 6 and 9 subtasks. Report the percentile of the
  observed mean D.
- **Placebo 2, matched on answer type.** S holds 4 of the 6 primer-pair subtasks (PCR-gene-enz,
  PCR-seq-enz, both Gibson; the other two are PCR-len-primers and PCR-seq-primers) and 2 of the 9
  others. All 15 × 36 = 540 splits with that composition.
- **"Changes".** The observed mean D lies above the 97.5th percentile of both placebos, and on S
  the best 2024 model is within 0.05 of the human mean or above it while on F it is more than
  0.20 below.
- **"Holds".** The observed mean D lies inside the 95% range of placebo 2.
- The numbers here are per-subtask means of full-set results. They are not per-item. The level is
  stated as "stratum-level L3" and is weaker than item-level L3.

## Analysis B: L4, does Haiku use the centroid shortcut? (`scripts/edits.py`)

- **Items.** 147 SeqQA items: 25 each of five S subtasks, and 22 of PCR-gene-enzprimers, where 18
  items failed the automatic construction check. Seed 0.
- **Edit.** The distractors are rebuilt so that a distractor is the option the others are derived
  from. The key and the question are unchanged, and the error types are kept (`edits.py`
  docstring). The check requires that the rule now picks a distractor.
- **Conditions.** `forced` (original options) and `edit`. Both forced-choice, with no refusal
  option and the same prompt.
- **Statistics.**
  - Paired accuracy difference forced − edit, overall and per family, with a 95% bootstrap over
    items (2,000 replicates, seed 0).
  - In `edit`, the share of answers that pick the new central distractor, against the mean share
    picking each other distractor.
- **"Uses the shortcut" (changes).** The pooled drop is ≥ 0.10 with its 95% interval excluding 0,
  and the central distractor is picked more often than the other distractors.
- **"Does not" (holds).** The interval includes 0 and its upper bound is < 0.10.
- **Inconclusive.** Anything else.
- Per-family results are exploratory, with Bonferroni over 6.
- **Known asymmetry.** In the PCR edits, a reader who checks the enzyme sites can still eliminate
  only one option, as in the original. In AAseq, two of the edited distractors differ from the key
  at 2 positions instead of 1. That makes them slightly easier to reject for a model that
  translates. So a drop is conservative evidence.

## Analysis C: blind and options-only baselines (L2 to L4)

- **Conditions.**
  - `blind`: FigQA and TableQA without the image, with the refusal option.
  - `blindf`: the same, forced.
  - `opts`: options only, forced, on FigQA, TableQA, ProtocolQA, CloningScenarios, SeqQA (10 per
    subtask), LitQA2, SuppQA and DbQA.
- **Statistics.** Accuracy against mean chance 1/k (k = substantive options). Under `blind`, also
  precision and coverage. Wilson intervals, and a cluster bootstrap (figure, protocol, scenario).
- **Comparisons (context, not like-for-like).** The paper's 2024 accuracies, and Opus 4.6's 58.0%
  (no tools) and 78.3% (crop tool) on FigQA.
- **Notable.**
  - FigQA `blindf` ≥ 0.50: most of a sighted no-tool score is reachable without the figure.
  - An interval including chance: a clean null.

## Analysis D: abstention (trait 9)

- **Conditions.** `std` (refusal option at a hashed random position, as both harnesses do) and
  `forced`, on the same items. Subsets: ProtocolQA (108), CloningScenarios (33), SeqQA (10 per
  subtask), LitQA2 (60), SuppQA (50), DbQA (60). FigQA and TableQA through `blind` and `blindf`.
  `last` puts the refusal option last, on FigQA without the image (181).
- **Statistics.** acc_std, prec_std and cov_std, against acc_forced.
  - Δ = acc_forced − acc_std. This is the accuracy the refusal option costs.
  - Among std refusals: the share answered correctly under forced, against chance.
  - Refusal rate std versus last, paired.
- **Bucket audit.** Each scorer route is counted: correct, wrong, refusal, unparsed.
- **"Abstention changes the score".** Δ ≥ 0.05 with its interval excluding 0.
- **Position effect.** The refusal rate differs by ≥ 0.05 between std and last, with its interval
  excluding 0.

## Analysis E: human baseline arithmetic and clusters (C2–C4)

This uses no new data.
- **Human score under forced-choice scoring.** The lower bound is the published accuracy (correct
  and sure). The upper bound is accuracy + (1 − coverage), if every unsure guess was right. The
  midpoint under chance guessing is accuracy + (1 − coverage)/k̄. Precision is the value if
  unsure guesses were as good as sure answers.
- **Intervals for the model claims.**
  - For each, a 95% interval for a score of that size on that many items: binomial (Wilson) and
    cluster-adjusted.
  - The design effect is estimated from Haiku's own per-item correctness in that subset. It is
    labelled an approximation, because published models' per-item results do not exist.
  - Claims covered: FigQA 0.783 vs 0.77 (181 items, 107 figures); CloningScenarios 0.61 vs 0.60
    (33 items, 9 scenarios); Opus 4.5 at 0.758 / 0.907 / 0.8517.
- **"The 'exceeds experts' claim is not supported by the data as stated".** The human forced-choice
  range, or the model's interval, contains the human line.

## Robustness (at least four)

1. Analysis A with ORF-seq-numlen moved into S.
2. Analysis A on precision instead of accuracy.
3. Placebo 2, matched on answer type.
4. Held-out halves for every rule (in `surface.json`).
5. Analysis B per family with Bonferroni.
6. For L4, a comparison of `forced` accuracy on the edited items with `forced` on non-edited
   items from the same families (are the edited items typical?).
7. A count of comparisons made, in the README.

## Budget

Haiku only, the 3 USD cap. The pilot cost 0.14 USD (0.0004–0.0046 per call). The main plan is
about 2.4 USD. It runs in priority order (B, C, D, then the rest) and checks spend between batches.
