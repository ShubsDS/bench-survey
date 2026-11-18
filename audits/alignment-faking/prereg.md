# Alignment faking: pre-registration

Written 2026-11-17 and committed before any stratified result was computed. Already seen:
- the per-variant free and paid compliance rates, the gap, and the `effective_scheme` rate, for
  every helpful-only variant in the release (a reproduction check);
- the label value counts for the default variant.

No crosstab of labels against each other, no per-query result and no route count has been computed.

## Data and definitions

- **Records.** `data/samples.parquet`, built by `scripts/build_table.py` from `json_outputs.zip`
  (sha256 `6e7c3f99…139d7`). One row per (setting, variant, tier, query id).
- **Pairing.** The same file name in `train/` and `deploy/` is the same query; checked for 200 of
  200 default-prompt pairs by `user_input` equality. The unit of analysis is the **query**. There is
  one sample per query per tier.
- **Primary compliance**, `C_pm`: helpful-only PM score ≥ −0.7. This equals `is_refusal_0_7 ==
  False`, the released flag (`info_about_trace_new.py:765`).
- **Alignment-faking label**, `AF`: `effective_scheme == "True"`. It exists for train-tier rows only.
  "FAILED TO PARSE" counts as not AF; its count is reported.
- **Primary cell.** Claude 3 Opus, prompted helpful-only, default prompt: setting `helpful_only`,
  variant `atn_honly`, 352 paired queries.
- **Opus prompted CoT variants**: every `helpful_only/atn_*` variant except those whose name
  contains a model suffix (`sonnet_3_0`, `sonnet_3_5`, `haiku_3_0`, `haiku_3_5`, `gpt_4_turbo`,
  `gpt_4o`) or `no_cot`. `atn_basic` and `atn_basic_no_jailbreak` are included and flagged as
  "no helpful-only objective" controls.
- **Other-model cells**: `atn_honly_{model}` and `atn_honly_cut_rlhf_info_{model}`, plus
  `atn_honly_best_for_humanity_sonnet_3_5` and `atn_basic_sonnet_3_5`.
- **Fixed settings.** Seed 0. 2,000 bootstrap replicates resampling queries, with pairs kept
  together. 1,000 permutations for nulls. 95% percentile intervals.

## A1. Query-clustered interval for the headline gap (C1a)

- Statistics:
  - the gap = free `C_pm` rate − paid `C_pm` rate, with a paired query bootstrap;
  - the discordant counts b (free complies, paid refuses) and c (the reverse);
  - an exact McNemar p-value;
  - the conditional odds ratio b/c with an exact (Clopper–Pearson on b/(b+c)) interval.
- Also reported: the paper's per-sample SE for comparison.

## A2. How many queries carry the gap, and are they the same across prompts and models? (C1a)

- **Pool.** The queries present in ≥ 30 Opus prompted CoT variants (expected: the 172-query
  subset).
- **Per-query propensity.** For each query, the mean of b − c over variants (its "gap
  contribution") and its free-tier compliance rate across variants.
- **Overdispersion test.** Statistic: the variance across queries of the per-query free-tier
  compliance rate. Null: within each variant, permute compliance across queries, 1,000 times.
- **Concentration.** The share of the pooled gap (Σ over variants of b − c) carried by the top 10%
  of queries. Reported against the same permutation null.
- **Held-out drop-k.**
  - Split the variants into two halves at random (seed 0).
  - Rank queries by gap contribution on half A.
  - Remove the top k = 5, 10 and 20 from every half-B variant and from the default cell.
  - Recompute the half-B pooled gap and the default gap.
  - Random-removal control: remove k random queries, 1,000 times.
  - Report where the targeted removal falls in that distribution.
- **Cross-model.** Spearman correlation between Opus's per-query free-tier compliance (pooled over
  variants) and Claude 3.5 Sonnet's (pooled over its variants), with a permutation null.
- **Verdict.**
  - **"Changes"** if both hold:
    - removing ≤ 10 held-out-selected queries removes ≥ 50% of the default gap while the 95th
      percentile of random removal removes < 15%;
    - overdispersion p < 0.05.
    - Then the gap is described as carried by a small set of requests.
  - **"Holds"** if removing the top 10 leaves ≥ 50% of the gap.
  - In between: reported as partial.

## A3. Routes into "complied" by tier (C1b)

For each tier, in the primary cell and pooled over the Opus prompted CoT variants, count these
routes:

1. `C_pm` and `follows_instructions == True`
2. `C_pm` and `follows_instructions == False`
3. `C_pm` and an output-surface refusal phrase in the first 400 characters of the final output
4. `C_pm` with no `<OUTPUT>` tag or an empty output
5. not `C_pm` but `follows_instructions == True`
6. PM score in [−1.0, −0.4], near the threshold

Alternative compliance definitions:
- `C_pm05`: PM ≥ −0.5, the App. D.8 cut-off.
- `C_fi`: `follows_instructions == True`.
- `C_both`: `C_pm` and `C_fi`.

The gap under each definition, with a paired query bootstrap.

Verdict:
- **"Changes"** if the `C_both` gap is < 50% of the `C_pm` gap and the bootstrap interval of
  their difference excludes 0. The gap would then be largely a gap in partial or non-compliant
  outputs that the PM scores as compliant.
- **"Holds"** if the `C_both` gap is ≥ 75% of the `C_pm` gap.

Caveat fixed now: the compromise classifier's prompt is not in the public repo. The meaning of
`follows_instructions` is inferred from its name and from App. E.2.

## A4. Does the AF label account for the gap per sample? (C1c)

- **Residual gap**: (free `C_pm` and not AF) / n_free − paid `C_pm` rate. Paid rows have no AF
  label, so this compares to all paid samples, as the paper's Fig. 15 does.
- Report:
  - the share of free compliers with AF;
  - the residual gap with a query bootstrap, in the primary cell, for each Opus variant, and
    pooled over Opus variants (two-way resampling: queries, and variants);
  - the same for the Claude 3.5 Sonnet cells and for `C_both`.
- Already in the paper: about 2 points for the default (99% vs 97%). New: the distribution over
  variants and models, with intervals.
- Verdict:
  - **"Changes"** if, pooled over Opus variants, the residual gap is ≥ 1/3 of the full gap and its
    interval excludes 0.
  - **"Holds"** if the residual is < 1/3 of the full gap, or its interval includes 0.

## A5. Which models show a gap: base rates, odds and power (C2)

- **Cells.** Each other-model cell and the Opus cells with the same prompt.
- **Report per cell:**
  - n, the free and paid rates, the gap with a query bootstrap, and b, c;
  - the conditional odds ratio with an exact interval;
  - the "room" (1 − paid rate);
  - the minimum detectable gap at 80% power (two-sided α = 0.05, unpaired two-proportion normal
    approximation at that n and paid rate, the paper's own error model);
  - the gap predicted if the model had Claude 3 Opus's odds ratio on the same prompt, given its
    own paid rate (marginal odds ratio from the Opus cell).
- **Classification.** A cell is "no gap" if the paper says so (Claude 3 Sonnet, Claude 3 Haiku,
  Claude 3.5 Haiku, GPT-4 Turbo, GPT-4o) or if its gap is ≤ 1 point.
- **Sheshadri design, analytic.**
  - n = 200 per tier, unpaired, threshold "gap > 1%".
  - For true paid rates p0 in {0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4}:
    - the probability that a model with no true gap exceeds the threshold;
    - the probability that a model with Opus's odds ratio exceeds it;
    - the minimum detectable gap.
  - This is computed exactly from binomials. No per-model Sheshadri value is used unless read by
    eye from a figure, and then it is marked as such.
- **Verdict.**
  - **"Changes"** if, for at least one "no gap" cell, the odds-ratio interval includes Opus's
    marginal odds ratio on the same prompt, or the gap predicted from Opus's odds ratio is below
    that cell's minimum detectable gap. The cell is then labelled "not distinguishable from
    Opus-like behaviour at this n".
  - **"Holds"** if every "no gap" cell's odds-ratio upper bound is below Opus's odds ratio and its
    room exceeds its minimum detectable gap.

## A6. Does the AF label track vocabulary? (C3)

- **Rows.** Free-tier rows with an AF label in the Opus prompted CoT variants and the Claude 3.5
  Sonnet CoT cells.
- **Feature set K.**
  - Counts in the scratchpad of: `train*`, `RLHF`, `modif*`, `values`, `free tier`,
    `preserv/protect/maintain*`, `future`.
  - log(1 + scratchpad length).
  - The patterns are fixed in `build_table.py` before any label crosstab.
- **Model.** Logistic regression (sklearn, C = 1, standardised features).
  - Fit on rows whose query hash falls in a random half of queries (seed 0).
  - AUROC against `AF` on the other half.
- **Variants of the test:**
  - (i) all rows;
  - (ii) `C_pm` rows only;
  - (iii) a length-only model;
  - (iv) a permutation null: shuffle `AF` within variant, refit, 1,000 times. Reduced to 200 if
    runtime requires; any reduction is reported.
- **On the 106 human labels** (`human_labelled_data2.csv` from `alignment-faking-extensions`):
  - the original classifier's decisions (`v5_classifier_decsision`) and the new classifier's
    (`new_classifier_decsision`) against `human_label`: accuracy, and error rate by model and by
    scratchpad-length tercile (Fisher or chi-square);
  - rule K, trained on the Greenblatt rows, applied to the 106: AUROC against the human label,
    beside both classifiers.
- **Verdict.**
  - **"Changes"** if K's held-out AUROC against `AF` is ≥ 0.85, and K's AUROC against the human
    labels is ≥ the original classifier's agreement with people. The original classifier's rate
    would then count vocabulary about as well as it counts the reasoning people label.
  - **"Holds"** if K's held-out AUROC is < 0.75, or K does clearly worse than the original
    classifier on the human labels.

## A7. Spread over prompt variants and the tier cue (descriptive; no verdict threshold)

- For the Opus prompted CoT variants: the count, the median gap, the IQR, the minimum and maximum,
  and the default's rank.
- For the 8 paraphrases: each gap with an interval, and a heterogeneity test (chi-square on the
  8 × 2 table of b, c).
- Gaps for the cue variants: `train_absence`, `deploy_absence`, `region_cal`,
  `region_cal_train_absence`, `region_cal_deploy_absence`, `region_eu`, `cut_rlhf_info`,
  `cut_mod_effects_values`, `honest*`, and the `atn_basic*` no-objective controls.
- The paper's statement that no variant was iterated against the metrics is quoted as is. No claim
  about selection is made beyond the spread.

## Robustness (applied to whichever of A1–A6 gives a "changes" verdict)

1. Threshold −0.5 instead of −0.7.
2. Drop each variant in turn (A2, A4).
3. A second seed (1) for every bootstrap and split.
4. Placebo splits of the same sizes and base rates (A2: random query sets matched on paid-tier
   compliance; A3: random relabelling of `follows_instructions` within tier).
5. A Bonferroni count over the main tests: A1, A2, A3, A4 and A6 are 5 tests, plus one per A5
   cell. Reported at 95% and at the Bonferroni level.

## What I will not do

- No inference on harmful content.
- No text from transcripts is committed or quoted.
- If any feature or rule is changed after seeing a stratified result, the first version's result
  stays in the write-up.
