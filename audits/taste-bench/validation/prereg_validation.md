# Taste-Bench validation: pre-registration of the validator's own tests

Validator, 2026-11-17. Committed before any of the tests below was run. Seen so far: the audit's
write-up, prereg and results files; the paper source; the repository README, protocol, configs
and summary files; the dataset schema (column names and lengths only). The auditor's scripts
were rerun (outputs byte-identical to the committed results) but not yet read, except
`scripts/b4_haiku.py` (to check what Haiku was sent) and `scripts/b_common.py` (pins).

All scripts live in `validation/`, read the pinned parquet files directly (sha256 checked) and
import nothing from `../scripts/`. Seeds are 1 (different from the auditor's 0). Resampling unit:
`task_id` within cell. Nothing in any committed file contains item text.

## V1. Null for the construction-aware floor (C1, auditor's weak spot 1)

My own `cont` and `ground` features from the prereg's written definitions (amendment 1, B2).
- **V1a placebo features.** 1,000 draws. In each, every item receives the (option 0, option 1)
  feature pair of another item of the same cell, drawn by permutation, attached by published
  position. This keeps the distribution and tie rate and breaks any link to the label.
- **V1b task-level label flips.** 1,000 draws. The real feature, with the correct side flipped for
  all items of a random half of tasks (each task flipped with probability 0.5).
- In each draw: a fresh random 50/50 task split within cell; the sign ("higher" or "lower") is
  chosen per cell on the training half (four free signs); the held-out half is scored, ties
  wrong; Average = mean of engineering and research held-out accuracy, each item-weighted.
- Reported: where 61.4 (the auditor's held-out Average) and my own real-feature held-out Average
  (median over 1,000 random task splits, same procedure) fall in each null. Also the same with
  the signs fixed in advance by construction (parallel higher, detour lower), which has no free
  parameter.

## V2. Can the cell be inferred from what the model sees? (C1)

- Classifier: L2-regularised logistic regression on binary word-presence features (vocabulary of
  words in at least 5 items) of the query and the two options, fitted separately within each
  domain (domain is plainly visible). Five-fold cross-validation grouped by `task_id`.
- Reported: held-out accuracy and AUC for detour versus parallel; then the floor rule scored with
  the inferred cell (sign from the out-of-fold prediction), as an Average.
- A second, cruder inference: prefix step count only (threshold chosen in the training folds).

## V3. Fair comparison with models (C1)

The rule's answer is order-invariant, so its paired and single-order accuracies are equal. I
compute each published model's single-order Average (two-order mean accuracy per cell, combined
as the leaderboard does: item-weighted within domain, then 1:1) from `summary.json` and count the
models above 60.4 and 61.4.

## V4. Held-out split by task (C1)

Check from `../data/features.csv` (auditor's output) whether any task has items in both halves.

## V5. Detour engineering below 50% with the full prefix (C3)

- From the summaries: each model's single-order accuracy in detour engineering, over all
  presentations and over parsed presentations.
- Intervals: the per-item score (CC = 1, CW/WC = 0.5, WW = 0) has an exactly known variance from
  the paired counts. Task clustering: design effect 1 + (m* − 1)·ICC, m* = Σm²/Σm from the item
  counts per task; ICC = 0, 0.1, 0.3, and the ICC of Haiku's H1 per-item scores within detour
  engineering tasks (labelled as Haiku-derived). Count models whose upper bound is below 50.
- Selection carry-over test: regress each model's detour-engineering single-order accuracy on the
  mean of its other three cells; compare residuals of models related to a judge by family
  (OpenAI GPT models for GPT-4.1; Mistral Medium 3.5 for Mistral Large 3) with the rest
  (permutation p over models). Also the slope of detour-engineering accuracy on capability
  (other-cell mean): a negative partial relation would be the regression-to-the-mean signature.
  14 models: descriptive, a lead at most.

## V6. Blind hand labels (C3)

- 44 detour-engineering items drawn at random (seed 1) from the 266.
- For each I read the query, the first 1,500 and last 3,000 characters of `prefix_text`, and the
  two options in published order, without the key, the cell's feature values, or Haiku's answer.
  I record which option I judge the better technical decision, and a confidence (1 = guess,
  2 = lean, 3 = clear). The labels are committed (ids and letters only) before the key is joined.
- Reported: agreement with the key, overall and at confidence ≥ 2, with a task-cluster interval;
  agreement with the "lower `cont`" rule; agreement with Haiku H0.
- I am a language model (Claude). These are a model's blind labels, not a human expert's; they
  test whether the key is recoverable from the shown material, not whether it is true.
- Readings: agreement ≥ 70% supports the label as defensible from the prefix; near or below 50%
  says the key is not recoverable from what the evaluated model sees.

## V7. Parse failures (C4)

From the summaries: unparsed and error counts per model and cell; unparsed rate against cell
median prefix length. For each model with unparsed > 0: the single-order Average with unparsed
counted wrong, as chance (0.5 each) and at the parsed rate; the paired Average with unparsed as
chance, bounded as the auditor bounded the parsed-only case. Recheck GLM-5.2's rank change and the
Grok 4.20 63.5%. Per-item, per-length and per-truncation failure distributions cannot be checked
(no per-item release); say so.

## V8. The H2 intervention (C2)

From the cached Haiku records and the parquet: per item, the characters removed by the cut; how
far back the 2,000-character window moves; whether the removed step's tokens overlap more with
the correct or the wrong option; H2 − H1 by whether the cut was short or long (median split).
Placebo: the same contrast (detour minus parallel) under 1,000 random relabellings of
construction across tasks within domain. If budget allows (≤ 0.65 USD, projected from H2's
cost), one Haiku arm H3: H1 with the second-to-last step removed instead of the last (the window
shift without removing the final step), both orders. Prediction if the final step is the cause:
H3 − H1 shows no detour-minus-parallel contrast.

## V9. Secondary claims

Recompute C5 (cell means and counts from the paper's table), C6 (adjacent gaps; the repeat-run
pair; the task concentration and research-domain intervals resampling tasks, using Haiku's
per-item variance only to illustrate), C7 (composition from the paper's horizon-by-cell table and
cell means), C8 (r with and without GPT-5.6 Sol and GPT-5.5, from the auditor's figure values,
which I check against the paper's stated r and spreads). L1 notes against the paper's text.

## V10. Leak scan

Every committed file under `audits/taste-bench/` is scanned for any 40-character window (after
whitespace normalisation) that occurs in any item's `query`, `choices`, `prefix_text` or
`prefix_text_short`, and for any 8-word sequence from those fields. Hits are reported by file
and field, not quoted.
