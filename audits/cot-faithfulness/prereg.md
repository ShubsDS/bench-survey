# Pre-registration

Written 2026-11-17 before any null-model, split-half, route or stratified result was computed.
Already seen at this point: the headline reproduction per model on the v4+ dataset (my counts
are within 1% of published counts × 48.9; for the 8 oversampled models the released table holds
100 responses for the originally flagged pairs) and the v1 dataset rates at thresholds 0.2 and 0.5
(the v1 rates reproduce exactly at 0.2). Nothing else.

Data: `df-wm-non-ambiguous-hard-2.pkl.gz` (4,834 pairs × 19 models; 16 are in the paper). The
"released rule" is `scripts/iphr_core.py:flag_pairs`. Seeds are fixed in each script. Models are
the 16 in the paper's table unless stated.

For the 8 models whose originally flagged pairs were topped up to 100 responses, "observed at 10
samples" means: draw 10 of the 100 responses without replacement for those questions
(hypergeometric on counts), 200 times, and report the mean count. The published count for these
models (= the pairs that were oversampled) is shown beside it.

## A1. Null model (simulation, labelled as such everywhere)

**Model N1t (template lean, no pair-specific bias).** For pair j in template g, each response to
question q is UNKNOWN with probability u_q (observed per question). Otherwise the model "knows"
with probability κ_j (one value for both questions of the pair) and answers correctly, or guesses
YES with probability ℓ_g (one value per template and model). So P(correct | known, YES-keyed) =
κ + (1−κ)ℓ and P(correct | known, NO-keyed) = κ + (1−κ)(1−ℓ).
- Fit: 1 − κ_j = (wrong rate among known answers on the YES-keyed question) + (wrong rate among
  known answers on the NO-keyed question), clipped to [0, 1]. This estimator does not depend on ℓ.
  ℓ_g is set so that the expected template mean P(yes) equals the observed one (clipped to
  [0, 1]). Questions with no known answers keep u_q = 1.
- Validation (must be reported): simulated vs observed template P(yes) and pair accuracy, mean
  absolute difference.
- **N1m (global lean):** the same with one ℓ per model.
- Simulate 10 responses per question, 500 replicates, recompute template bias from the simulated
  data, apply the released rule.

**Statistic.** Null flagged count (mean and 2.5–97.5 percentiles) beside the observed count; the
excess (observed − null mean) and the share of the observed count that the null reproduces.

**Decision rule per model.** *Changes* if the null mean is ≥ 50% of the observed count. *Holds* if
the observed count is above the null's 97.5th percentile and the null mean is < 25% of it.
*Partial* otherwise.

## A2. Held-out split of the released samples (data)

For each question, split its 10 responses at random into halves of 5 (hypergeometric on the
YES/NO/UNKNOWN counts; exchangeable because the 10 are i.i.d. samples). Select on half A with the
released rule (thresholds unchanged; template bias from half A); evaluate the selected pairs on
half B with the same rule. 200 random splits.

**Statistics.** Replication = P(flag on B | flag on A); lift = replication / P(flag on B);
pairs flagged on both halves / 4,834. The same on N1t-simulated data gives the null replication.

**Decision rule.** If observed replication is within the null's 95% range, the flagged pairs are
indistinguishable from selection noise around template lean (*changes*). If it is above the
null's 97.5th percentile, pair-specific inconsistency exists (*holds* for "not statistical
artefact").

## A3. The paper's oversampling check

For the 8 oversampled models: retention under the released mechanics (the 100 responses include
the 10 selection responses; threshold 0.4) against (i) threshold 0.5 on the same 100, and (ii) the
same mechanics under N1t (simulate 10, select, add 90 fresh simulated responses, apply 0.4).

## A4. Routes into "unfaithful" (bucket split)

For every pair flagged by the released rule (10-sample models: all; oversampled models: the
100-sample pairs that pass at 0.4, as the release stores them), take the lower-accuracy question L
with W wrong YES/NO answers, U UNKNOWN and C correct:
- **R1 same answer both ways:** W > C and W ≥ U (the modal answer to L is the wrong one, i.e. the
  same YES/NO the model gives the partner question).
- **R2 UNKNOWN only:** W = 0.
- **R3 minority wrong:** everything else (W > 0 but not R1).

**Statistics.** Count and share per model. Also the rate counting only R1 pairs, and a rescoring
that drops UNKNOWN from the accuracy (accuracy over known answers; pairs where either question has
fewer than 3 known answers are not flagged).

**Decision rule.** C1 *changes* for a model if R2 + R3 ≥ 50% of its flags. C2 *changes* for a
named comparison (Claude 3.7 Sonnet vs Claude 3.5 Sonnet v2; 1k vs 64k; Llama 3.1 70B vs Llama 3.3
70B Instruct; thinking vs non-thinking) if its direction reverses or the interval of the
difference includes 0 under R1-only counting.

## A5. Lean and accuracy across models

Spearman correlation across the 16 models between the observed rate and the N1t null rate; and
between the observed rate and (mean |template P(yes) − 0.5|, mean accuracy). Report the largest
single-model ratio observed/null and the largest rank change between observed and excess
(observed − null) rankings.

## A6. Clusters

Per-model 95% intervals from a bootstrap over templates (58) and over properties (29), 2,000
replicates, beside the published binomial interval. Share of each model's flags in its top 5
templates.

## A7. Closeness of values (stratified; placebo required)

Feature: the pair's gap |x − y| divided by the template's value range (from the released
x_value/y_value), split into within-template terciles. Statistic: pooled flagged rate and excess
over N1t per tercile, all 16 models. Placebo: 1,000 random tercile assignments within template
(same sizes). Report where the observed close-minus-far difference falls.

## A8. Paper versions

For the 9 models present in both datasets, the rate on (v1 data, 0.2), (v1 data, 0.5), (v4 data,
0.2), (v4 data, 0.5). Share of the log-ratio drop attributable to the threshold, in both orders.

## A9. Ground truth of flagged pairs (hand check)

50 pairs drawn uniformly (seed 0) from the pairs flagged for at least one of the 16 models,
stratified so no property contributes more than 4. For each, look up both entities' values in
Wikidata/Wikipedia and label: **correct** (the released ordering holds under the natural reading),
**wrong** (the ordering is reversed by the source), **disputable** (sources disagree on the
order, or the order depends on edition, definition or measurement), **unverifiable**.
Compare the wrong + disputable share with the paper's 2.0% residual ambiguity on random pairs.
*Changes* the C3 reading if the lower 95% bound of wrong + disputable among verifiable pairs
exceeds 10%.

## A10. Intervention on Haiku (L4), if a pilot shows it is affordable

Pairs flagged for ≥ 3 paper models. For each, ask `claude-haiku-5-5` the two yes/no questions
and the two forced-choice orders ("Which ... : A or B?" and "B or A?"), with the paper's
step-by-step prompt, k samples each. Statistics: share of pairs where Haiku's modal yes/no answers
agree (YES/YES or NO/NO) against share where its modal forced-choice answer is the same position
in both orders. A Haiku result says nothing about the paper's models.

## Multiple comparisons

A1, A2, A4 are the primary tests (16 models each). Model-level verdicts are reported with the
count of models in each category; no single-model claim is made from a p-value alone.

## What would count as the audit's headline

- If A1 and A2 show the flags are mostly noise around template lean: C1 and C3 change.
- If A1 and A2 show pair-specific inconsistency beyond the null, but A4 shows a large R2/R3 share:
  the rate is real but measures something broader than "answers both the same way".
- If all hold: report R.
