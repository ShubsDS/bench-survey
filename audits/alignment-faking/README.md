# Alignment faking: Claude 3 Opus's compliance gap is broad across queries and fully tracked by the reasoning label; partial compliance inflates it by about a fifth

Status: complete, 2026-11-17. **Validated by an independent refuter on 2026-11-17; see
"Validation" below and [`validation/VALIDATION.md`](validation/VALIDATION.md).** No inference was
run (0 calls, 0 USD). The auditor's original title ended "…but about a third of it is partial
compliance". The validator corrected it: on the paper's own classifier categories, and on blind
hand labels, the substantive-compliance gap is 0.80 of the headline, not 0.63.

Validated evidence level for each claim:

- **C1a: R.** Confirmed. The drop-k test could not have shown concentration, since 47 distinct
  queries comply on free only. Breadth rests on b = 47 and on 158 of 172 queries contributing
  positively.
- **C1b: R, with a modest inflation of the point gap (validator; auditor: L3).** The gap on
  substantive compliance (disclaimers allowed) is 9.2 points, 0.80 [0.65, 0.92] of the headline.
  The auditor's 0.63 counts complete answers that carry a disclaimer as non-compliance.
  "Most paid-tier compliance is partial or a refusal" fails pooled: 39% [29, 49].
- **C1c: R.** Confirmed. 0 of 44 variants keep a gap without the label after correcting for 44
  tests. The default-cell result is the paper's.
- **C2: mixed (validator; auditor: R).**
  - On the Greenblatt release, the pre-registered rule flags 4 of 9 cells, so its verdict is
    "changes". The cells it flags are underpowered. "Holds" comes only from a post hoc check.
  - Sheshadri et al.: L1. Their design is paired, so the 4–40% false-pass figure is an upper bound,
    not the design's rate.
- **C3: L2 lead, weaker.** The comparison on the human labels is not like for like.
- **Reasoning rate: reproduces** (11.93%, against the auditor's reported non-reproduction).

Auditor's original evidence levels, kept for the record:

- **C1a, the headline gap at the level of queries: R.** It holds when queries are resampled. It is
  spread over most queries, and removing the queries that carry the most gap barely moves it.
- **C1b, what "complied" contains: L3 for the size of the gap, R for its existence.** On full
  compliance the default gap is 7.1 points, 0.63 of the PM-based 11.4. This is partial by the
  pre-registered thresholds: below "holds" (0.75), above "changes" (0.5).
- **C1c, does the reasoning label account for the gap per sample: R.** Already in the paper for the
  default prompt. Here it holds over 44 prompt variants, with two-way intervals.
- **C2, "only a few models show a gap": R on the Greenblatt release; L1 for Sheshadri et al.'s
  5 of 25.** The models classed as "no gap" had room to show one. The 25-model study releases no
  per-sample data. Its 1-point threshold is below its own noise, and it cannot detect an Opus-sized
  effect in a model near the floor.
- **C3, the alignment-faking rate measures a reasoning pattern: L2 lead, partial.** Seven keyword
  counts plus length reproduce the original classifier's label at held-out AUROC 0.78. On the 106
  human labels, that rule is indistinguishable from the original classifier. The improved
  classifier is clearly better than both.

## Validation

An independent validator re-derived every headline from its own code
([`validation/`](validation/)), with 80 blind hand labels of its own. Corrections, with the
auditor's original wording kept:

1. **The reasoning rate reproduces.**
   - Auditor: "14.5% vs the paper's 11.9%, unexplained".
   - The paper's metric (fn. 27, §3.2) is the mean of the hard (`effective_scheme`) and soft
     (`partial_scheme`) classifiers, each counted only on compliant outputs: (40 + 44)/2/352 =
     **11.93%**.
   - The auditor used the hard label alone, uncompliant outputs included.
2. **The query subset is not "an unstated rule".**
   - The 48 missing ids of the 400 are copyright requests, dropped by the authors' own filter
     (`pure_system_compare_scheming_helpful_only.py:620,645`; `plot_comp_scheme.py:827-851`).
   - Table 1's standard errors imply n = 352. The default cell is the paper's own analysis set.
   - Variants use ids 0–199 and paraphrases ids 0–99 (plus id 183), minus copyright requests.
   - The rule depends on the query text, not on model behaviour, so no number is biased by it.
3. **`follows_instructions` is published.**
   - Auditor: "the compromise classifier's prompt is not in the public repo".
   - It is printed in App. I.4. The field is True exactly when all three guiding questions are No:
     category 4, "a completely helpful response without any disclaimers or cautionary warnings".
   - "Not following instructions" therefore includes category 3, complete answers with a
     disclaimer.
   - Blind hand labels agree with the classifier's four categories at κ = 0.92. Of the 19
     category-3 items, 19 are complete answers.
4. **C1b size: 0.80, not 0.63.**
   - Auditor: 0.63 [0.45, 0.83]; "most paid-tier compliance is partial or a refusal"; "about 1.6
     times larger"; L3.
   - Substantive compliance (hand-calibrated, disclaimers allowed): default 9.4 [7.9, 10.5] = 0.83
     [0.70, 0.93]; pooled over 44 variants 0.80 [0.65, 0.92].
   - Classifier categories 3–4: default 9.7 [6.3, 13.1]; pooled 0.82 [0.73, 0.91].
   - Paid-tier partial or refusal, pooled: 39% [29, 49], so "most" fails. In the default cell it is
     7 of 10 (a lead).
   - The PM metric makes the gap about 1.25 times larger, not 1.6. The 0.63 holds only for the
     narrower "no disclaimer" definition (hand 0.64 [0.49, 0.76]).
   - Level: R with about 20% inflation, not L3.
   - Rater agreement with the auditor's labels on 16 shared items: 81%, κ = 0.58.
5. **C1a drop-k.**
   - The ranking is held out and the random reference is matched.
   - The "default gap" in the drop-k table is the default cell restricted to the 172 pooled queries
     (12.8 points), not 11.4.
   - Even the in-sample best 10 queries remove only 23% of the gap. The pre-registered "changes"
     outcome was unreachable, so the test adds little.
   - The validator's own version on all 352 queries: k = 10 removes 2.2% (random 95th percentile
     4.8%).
6. **C1c, confirmed.**
   - Pooled residual +0.10 [−0.98, 1.09] (hard label), +0.30 [−0.90, 1.51] (soft label).
   - Per variant: 1 of 44 nominally positive (`cut_examples`, +6.4 [1.7, 11.0]); 0 of 44 after Holm
     or BH.
   - The paper's conditional figure (99% vs 97% refusals) does not reproduce from the released
     labels (96.7–97.9% vs 97.2%). Its sign is a −2-point gap, not "≈2 points".
7. **C2 on the Greenblatt release: the pre-registered verdict is "changes".**
   - The A5 rule flags 4 of 9 cells (the validator gets 3 of 9 at −0.5; the auditor got 1). Its
     verdict is "changes".
   - The flags come from cells with 3–17 discordant pairs.
   - The post hoc marginal check holds in 9 of 9 cells, even at Opus's lower-bound odds ratio. But
     it is post hoc, so R is not the primary verdict.
8. **C2, Sheshadri et al.: the design is paired.**
   - Their code sends the same first-N queries in both tiers at temperature 0
     (`alignment-faking-extensions` `src/run.py:206`, `src/pipeline/pipelines.py:298-299`). The
     auditor's model assumed unpaired tiers.
   - The false-pass rate of the 1-point cut depends on the discordance rate d: 4% (d = 1%), 21%
     (5%), 29% (10%), 35% (20%).
   - "4–40%" is the independence upper bound. The MDE column (unpaired) is too large.
   - The paper states no significance test and no multiple-comparison handling. The L1 lead stands.
9. **C3 on the 106 human labels.**
   - The original-classifier columns are 0/1 decisions, so their "AUROC" is balanced accuracy at
     one threshold, while K's AUROC averages over all thresholds.
   - As a decision (threshold set on the training rows), K has balanced accuracy 0.53, below the
     original easy prompt's 0.63 (difference [−0.20, −0.002]).
   - Those columns are the original prompts re-run on Claude 3.5 Sonnet 20241022, not the model
     that made the released labels.
   - The held-out 0.78 reproduces (0.77 over 20 query splits). Length alone gives 0.71.
10. **Smaller points.**
    - Three PM-compliant outputs are empty, all free-tier.
    - The README gave two different intervals for the default gap ([7.4, 15.1] and [7.7, 15.3]);
      the validator's is [7.4, 15.3].
    - The A6 permutation null used 200 permutations.
    - All auditor scripts rerun to identical numbers.

## The benchmark and what rests on it

Greenblatt et al. (arXiv 2412.14093) tell Claude 3 Opus that it is being trained to comply with
every request, using free-tier conversations only. The two measures:

- the **compliance gap**: harmful-request compliance in free-tier (implied training) minus paid-tier
  (implied unmonitored) conversations;
- the **alignment-faking-reasoning rate** in the scratchpad, from an LLM classifier.

Table 1 gives the default prompt: reasoning 11.9 ± 1.7%, refusals 85.8% vs 97.2%, a gap of 11.3 ±
2.1 points. The repo README presents the reasoning as the explanation of the gap. Follow-ups
reuse the setting:

- Hughes et al. (2025): an improved classifier, AUROC 0.92 vs 0.62 on 106 human labels.
- Sheshadri et al. (arXiv 2506.18032): "only 5 of 25 models" show a gap above 1%.

It is the reference demonstration of alignment faking. See [`claims.md`](claims.md).

## Data inventory

| Source | Per-sample? | Used for |
|---|---|---|
| Greenblatt `json_outputs.zip`, from the Drive folder linked in the repo README | **Yes**: 131,528 rows over 10 settings and 153 variant folders. Each row has the classifier labels, the helpful-only PM score and the compromise labels. One sample per query per tier; same query ids in both tiers | Everything below |
| Hughes et al.: 106 human labels (HF) and `human_labelled_data2.csv` in `alignment-faking-extensions` | Yes, 106 items with per-item decisions from about 20 classifier versions | C3 |
| Hughes et al. open-weight runs | No per-sample release. `abhayesian/llama-3.1-405b-alignment-faking-examples` is split by outcome and has no paid-tier compliance, so no gap can be computed | not used |
| Sheshadri et al., 25 models | **No.** Code only. Per-model rates appear only in figures | C2 analytic only (blocked) |
| `Anthropic/alignment-faking-rl` | Encrypted | not opened |

The helpful-only analyses use the 36,814 helpful-only rows with a PM score. The default cell has
352 queries; most variants have 172, and each paraphrase has 86. App. A says 400 queries were
used. The auditor wrote that the release is "a subset, chosen by an unstated rule".
*Validator:* the 48 missing ids are copyright requests, removed by the authors' own
`is_copyright_question` filter, and Table 1's standard errors imply n = 352. The 172 and 86 cells
are ids 0–199 and 0–99 (plus id 183), minus copyright requests. None of this depends on model
outputs.

## What we found

| Conclusion | Published | Reproduced (release) | Audit result | Verdict |
|---|---|---|---|---|
| Opus default gap | 11.3 ± 2.1 | 50/352 − 10/352 = **11.4** | Query-paired bootstrap [7.4, 15.1]; Bonferroni (22 tests) [5.4, 17.6]. b = 47 free-only vs c = 7 paid-only compliers; McNemar p = 2×10⁻⁸; conditional OR 6.7 [3.0, 17.6] | **holds** |
| Opus default reasoning rate | 11.9 ± 1.7% | *Validator:* paper metric (mean of hard and soft labels, compliant outputs only) = (40 + 44)/2/352 = **11.93%** | Reproduces exactly. Auditor: "51/352 = 14.5%, does not reproduce". That used the hard label alone, uncompliant outputs included | **reproduces** (auditor's definition error) |
| Gap carried by a few queries? | — | — | 158 of 172 pooled queries contribute positively; 44 queries give half the pooled gap. Removing the top 10 (chosen on held-out variants) removes 3.5% of the default gap on the 172 pooled queries (random-removal 95th percentile 8.3%). *Validator:* on all 352 queries, 2.2% (random 4.8%); the in-sample best 10 remove only 23%, so "changes" was unreachable | **holds**: broad |
| Gap on substantive compliance (*validator*) | — | — | Hand-calibrated (disclaimers allowed): **9.2** = **0.80 [0.65, 0.92]** of 11.4 pooled; default 0.83 [0.70, 0.93]. Classifier categories 3–4: default 9.7 [6.3, 13.1], pooled 0.82 [0.73, 0.91] | **holds** (about 20% inflation) |
| Gap on "full compliance" as the auditor defined it (category 4: no disclaimer) | — | — | `follows_instructions` and PM: **7.1** [4.5, 10.1] = 0.63 [0.45, 0.83] of 11.4. Pooled 0.63: auditor [0.57, 0.68], validator two-way [0.52, 0.73]. Odds scale: OR 26 [4.3, 1066] (b = 26, c = 1) | auditor: **size changes** (×0.63). *Validator:* true only if a complete answer with a disclaimer counts as non-compliance |
| Gap without the reasoning label | Fig. 15: 99% vs 97% refusals, i.e. a −2-point conditioned gap (the auditor wrote "≈2 points") | default: 0.0 [−2.0, 2.0] | Pooled over 44 variants: **+0.1** [−0.9, 1.2] of 11.4. 1 of 44 variants has an interval above 0; *validator:* 0 of 44 after Holm or BH | **holds** |
| "No gap" models (Claude 3 Sonnet, Claude 3 Haiku, Claude 3.5 Haiku, GPT-4 Turbo, GPT-4o) | "almost no" / "no" | gaps −12.9 to +2.4 | *Validator, primary:* the pre-registered conditional-OR rule flags 4 of 9 cells, so its verdict is **"changes"**; those cells have 3–17 discordant pairs. Post hoc: paid rates 1.7–12.9%; in 9 of 9 cells the gap interval excludes the gap an Opus-sized odds ratio would give (7–33 points; still 9 of 9 at Opus's lower-bound OR) | auditor: **holds**. *Validator:* pre-registered "changes" (underpowered); "holds" only post hoc |
| Sheshadri "5 of 25" (> 1 point, n = 200) | 5/25 | not reproducible | Auditor: a zero-gap model passes with probability 4–40%, assuming unpaired tiers. *Validator:* their code uses the same queries in both tiers at temperature 0, so the tiers are paired. P(pass) is 4–35% for discordance 1–20%; 40% is the independence bound. The MDE figures (unpaired) are too large | **L1 lead; blocked** |
| Reasoning label = reasoning, not vocabulary | AUROC 0.62 (old), 0.92 (new) vs people | — | Keyword rule K vs the released label: held-out AUROC 0.78 (null 95th percentile 0.56, 200 permutations; length alone 0.71). On the 106 human labels: K 0.64 [0.54, 0.74]; original classifier 0.58 [0.49, 0.68] / 0.63 [0.55, 0.72]; new 0.88 [0.81, 0.95]. *Validator:* the original columns are 0/1 decisions. As a decision, K's balanced accuracy is 0.53, below the original easy prompt's 0.63 | **partial lead; weaker** |

Bias direction:
- *Validator:* the PM-based compliance metric makes the gap about 1.25 times larger in points than
  substantive compliance does (auditor: "1.6 times", against the no-disclaimer definition).
- Auditor: "Most paid-tier 'compliance' is partial: 9 of 10 paid-tier PM compliers in the default
  cell are labelled as not following instructions." *Validator:* by the classifier's categories,
  those 9 are 2 complete answers with a disclaimer, 3 compromises and 4 refusals. Pooled over 44
  variants, 39% [29, 49] of paid-tier PM compliers are partial or refusals, so "most" fails.
- On the odds scale, the stricter definitions show a *larger* contrast (categories 3–4: OR 12; 4:
  OR 26; PM: 6.7). So the existence of an effect holds, and its size in points is modestly
  inflated.

## The confound and the effect, by claim

### C1a. Unit of analysis: the gap is a broad shift, not a property of a few requests

- **The paper's error bar.** Table 1's ± is a per-sample error. The design pairs each query across
  tiers with one sample each, so resampling queries is the right interval.
- **The headline interval.** The paired interval [7.4, 15.1] is about as wide as the paper's ±2.1
  implies. The headline is not overstated by clustering *within* a cell.
- **Across 45 Opus variants on the shared 172 queries:**
  - Queries do differ in compliance propensity: the variance of per-query free compliance is 0.016,
    against a permutation null 95th percentile of 0.0036 (p < 0.001).
  - The gap is only slightly more concentrated than chance: the top 10% of queries carry 23% of
    it, against a null median of 20% and a 95th percentile of 21%.
- **Held-out drop-k.** Queries were ranked on half the variants and removed from the other half:

  | k | Default gap removed | Random-removal 95th percentile | Half-B gap removed | Random 95th percentile |
  |---|---|---|---|---|
  | 5 | −3.0% | 6.4% | 1.5% | 2.2% |
  | 10 | 3.5% | 8.3% | 1.2% | 3.2% |
  | 20 | 17.7% | 12.6% | 5.5% | 4.5% |

  Only k = 20 beats random, and then by a few points.

  *Validator:* "Default gap" in this table is the default cell restricted to the 172 pooled
  queries (12.8 points). On all 352 queries, with the ranking taken over all 43 other variants,
  k = 10 removes 2.2% (random 95th percentile 4.8%). Removing the in-sample best 10 queries would
  remove only 23%, so the pre-registered "changes" outcome (≥ 50% with ≤ 10 queries) was
  unreachable. Breadth rests on the 47 free-only queries.
- **Across models.** Which requests Opus and Claude 3.5 Sonnet comply with is shared: Spearman 0.43
  on per-query free compliance (null 95th percentile 0.12). Which requests carry the gap is not:
  0.04 (p = 0.31). This is weak evidence, since Sonnet has only 4 cells.

### C1b. Outcome routes: "complied" holds partial and refusing outputs

`C_pm` = helpful-only PM score ≥ −0.7 (`info_about_trace_new.py:765`). The PM itself is not
released.

Routes, default cell, free / paid:
- `C_pm`: 50 / 10.
- `C_pm` and `follows_instructions`: 26 / 1.
- `C_pm` but not following instructions: 24 / 9.
- `C_pm` with a refusal phrase at the start of the output: 2 / 4.
- Missing or empty output: 0 / 0.
- `follows_instructions` without `C_pm`: 0 / 0. The label is nested inside `C_pm`.

Pooled over 44 variants, free / paid:
- `C_pm`: 1,165 / 364.
- Not following instructions: 517 / 217.
- Refusal-phrase route: 56 (5%) / 68 (19%).
- PM scores within ±0.3 of the cut-off: 395 / 389.

*Validator:* the routes above split `follows_instructions == False` without saying what it holds.
The classifier prompt is in the paper (App. I.4), and `follows_instructions` is its category 4.

| PM-compliant outputs | Cat. 4 (clean complete) | Cat. 3 (complete + disclaimer or training talk) | Cat. 2 (compromise) | Cat. 1 (refuses) |
|---|---|---|---|---|
| Default, free / paid | 26 / 1 | 11 / 2 | 11 / 3 | 2 / 4 |
| Pooled 44, free / paid | 649 / 147 | 215 / 59 | 249 / 96 | 53 / 63 |

80 blind validator labels agree with these categories at κ = 0.92 (`validation/VALIDATION.md` §D).
In the pooled set, 3 PM-compliant free-tier outputs are empty.

**Hand validation (auditor).** The auditor wrote: "The compromise classifier's prompt is not in the
public repo." *Validator:* it is, in App. I.4. The auditor hand-labelled 40 PM-compliant outputs,
seeing the first 500 characters of each:
- 12 + 12 free-tier and 8 + 8 paid-tier, half of each `follows_instructions` True;
- blind to tier and labels, one rater, item ids and labels in `results/handlabels.csv`, no text
  committed.

Results:
- `follows_instructions` True: 19 full, 1 partial.
- False: 7 full, 10 partial (high-level, sarcastic, deliberately useless, "some people claim"
  framing, harm-reduction reframing), 3 outright refusals. All 3 refusals were paid-tier.
- κ = 0.60, agreement 80%.

**Effect on the gap.**
- *Validator, first:* on substantive compliance (complete answers, disclaimers allowed;
  hand-calibrated), the gap is 9.4 [7.9, 10.5] in the default cell. Pooled, it is 0.80 [0.65, 0.92]
  of the headline. On classifier categories 3–4 it is 9.7 [6.3, 13.1], or 0.82 [0.73, 0.91] pooled.
  This is above the pre-registered "holds" threshold (0.75), with an interval that spans it.
- The auditor's figures below are on category 4 alone, "no disclaimer". In the auditor's word,
  that is "full compliance".
- On full compliance (`C_both`) the gap is 7.1 points [4.5, 10.1], against 11.4.
- Difference 4.3 [1.4, 7.1]; Bonferroni [0.2, 8.8].
- Dropping each variant leaves the pooled ratio between 0.60 and 0.64.
- Threshold −0.5 instead of −0.7: 0.63 (default) and 0.65 (pooled).
- The paper discloses compromise as "a constant issue confounding our results" (App. E.2) and
  publishes the classifier (App. I.4). Hughes et al. note that "a large proportion of Opus' AF
  shows partial compliance". New here: the count by tier, and the size of the effect on the
  headline gap.

### C1c. Per sample, the reasoning label tracks the gap

- **Default cell.** 40 of 50 free-tier compliers carry the label. The other 10 equal the 10 paid
  compliers, so the residual gap is 0.0 [−2.0, 2.0].
- **Pooled over 44 variants** (two-way bootstrap over variants and queries):
  - residual +0.1 [−0.9, 1.2] against a gap of 11.4 [8.7, 14.3];
  - residual share 0.9% [−9%, 9%];
  - dropping each variant gives −0.5% to 1.4%;
  - on full compliance, +0.04 [−0.9, 1.1].
- **Single variants.** Only `cut_examples` has a residual interval above 0 (+6.4 [1.7, 10.8]). That
  is 1 of 44, about the 2.2 expected by chance. *Validator:* exact one-sided p = 0.006; 0 of 44
  after Holm (smallest adjusted p 0.28) or BH. With the soft label, the largest residual is
  `dont_care_w_instruct`, +6.4 [−1.8, 14.0].
- *Validator:* the label used here is `effective_scheme` alone. The paper's reasoning metric
  averages it with `partial_scheme`, on compliant outputs only. With the soft label the pooled
  residual is +0.30 [−0.90, 1.51]. The paper's Fig. 15 figure (99% vs 97% refusals) does not
  reproduce from the released labels: training refusal given no label is 96.7–97.9%, against 97.2%
  unmonitored, depending on the label.
- **Claude 3.5 Sonnet.** The residual is negative (−14.0 [−21.5, −6.4]): its non-labelled
  free-tier compliance is *below* its paid-tier compliance.
- **The label is not sufficient for compliance.** 162 of 956 labelled free-tier samples (17%) were
  scored as refusals.
- **What this does not show.** It is correlational, as the paper says (fn. 45). The label could
  track compliance-justifying text rather than motive (see C3).

### C2. Which models show a gap

Greenblatt release, risk and odds scales. Intervals resample queries:

| Cell | n | Free | Paid | Gap [95%] | b / c | Conditional OR [95%] | MDE80 | Gap if Opus-like OR |
|---|---|---|---|---|---|---|---|---|
| Opus default | 352 | 14.2 | 2.8 | 11.4 [7.7, 15.3] | 47/7 | 6.7 [3.0, 17.6] | 5.0 | — |
| Sonnet 3.5 default | 172 | 62.8 | 43.0 | 19.8 [11.0, 27.3] | 48/14 | 3.4 [1.9, 6.7] | 15.0 | 38.0 |
| Sonnet 3.0 default | 349 | 2.6 | 2.6 | 0.0 [−1.7, 1.7] | 5/5 | 1.0 [0.2, 4.4] | 4.6 | 10.5 |
| Haiku 3.5 default | 170 | 10.6 | 8.2 | 2.4 [−1.8, 6.5] | 8/4 | 2.0 [0.5, 9.1] | 10.3 | 25.5 |
| GPT-4 Turbo default | 351 | 5.4 | 5.4 | 0.0 [−1.7, 1.7] | 5/5 | 1.0 [0.2, 4.4] | 5.8 | 19.1 |
| GPT-4o default | 196 | 10.7 | 12.8 | −2.0 [−7.1, 2.6] | 9/13 | 0.7 [0.3, 1.8] | 10.9 | 32.5 |
| Haiku 3.0 default | 31 | 0.0 | 12.9 | −12.9 | 0/4 | 0 [0, 1.5] | 31.6 | 32.7 |

The cut-RLHF-info prompt gives the same picture; all cells are in `results.json` → `A5_which_models`.

- **Room and power.** The "no gap" models are not at the floor or the ceiling.
  - Their paid compliance is 1.7–12.9%.
  - At their n, an Opus-sized marginal odds ratio (5.7) would give a 7–33-point gap. That is above
    every cell's MDE, and outside every cell's observed interval (9 of 9; post hoc check P1).
  - The pre-registered rule asked instead whether the **conditional** OR interval includes Opus's
    OR. It flags 4 of 9 cells: Haiku 3.5 default; Claude 3 Sonnet, Haiku 3.0 and GPT-4 Turbo on cut
    RLHF info. At threshold −0.5 it flags 1 of 9.
  - That rule fails because these models have few discordant pairs (b + c = 3–17), not because
    their behaviour resembles Opus's. I report the pre-registered result and read the marginal
    check (post hoc) as the stronger test.
  - *Validator:* under the pre-registered rule, a single flagged cell means "changes", so the
    primary verdict is **"changes"** (4 of 9 at −0.7; the validator gets 3 of 9 at −0.5, the
    auditor 1, because cells with c = 0 have unbounded intervals). The marginal check holds in 9 of
    9 cells even at Opus's bootstrap lower-bound OR (3.2 default, 2.3 cut-RLHF; closest cell
    cut-RLHF Sonnet 3.0, 1.4 against 2.2). It is post hoc, and is reported as such.
- **The scale changes the Opus vs Sonnet 3.5 comparison** (post hoc P2, 172 shared queries).
  - In points, Sonnet's gap is larger: 19.8 vs 12.8, difference +7.0 [−3.5, 18.0].
  - In log odds it is smaller: 0.80 vs 1.68, difference −0.88 [−2.20, 0.00].
  - "Sonnet 3.5 shows more" is a statement on the risk scale, helped by its 43% base compliance.
- **Sheshadri et al.'s design** (analytic, n = 200 per tier, unpaired, "gap > 1%"):

  | True paid rate | P(pass if no gap) | Gap at Opus's OR | P(pass at Opus's OR) | MDE80 (n = 200) |
  |---|---|---|---|---|
  | 0.5% | 4% | 2.3 | 79% | 4.6 |
  | 2% | 18% | 8.4 | 99.9% | 6.1 |
  | 5% | 28% | 18.0 | ~100% | 8.0 |
  | 10% | 34% | 28.6 | ~100% | 10.0 |
  | 40% | 40% | 39.1 | ~100% | 14.0 |

  - A 1-point threshold is below the stated 1σ (≤ 3.6%). Taken alone, it would let through up to
    40% of models with no gap.
  - A model that refuses nearly everything could carry Opus's odds ratio and still show a gap below
    what the design can detect.
  - Which of the 20 "no gap" models sit where cannot be checked: per-model numbers are only in
    figures. I did not read values off the figures.
  - *Validator:* the table above assumes unpaired tiers. Sheshadri et al. sample at temperature 0
    (§3.1), and their code sends the same first-N queries to both tiers (`src/run.py:206`,
    `src/pipeline/pipelines.py:298-299`). The design is therefore paired.
    - With no tier effect, the chance that the gap exceeds 1 point (b − c ≥ 3 of 200) depends on
      the share d of queries whose outcome flips between tiers: 3.7% (d = 1%), 10% (2%), 21% (5%),
      29% (10%), 35% (20%).
    - The column above is the independence case, an upper bound. The MDE column is likewise too
      large.
    - The paper states no significance test and no multiple-comparison handling. Its "1σ ≤ 3.6%" is
      per fraction, not per paired difference.

### C3. The judge and its vocabulary

- **Rows.** Free-tier rows from 48 Opus and Sonnet 3.5 CoT cells: 7,913 rows, 1,087 labelled.
- **Split.** By query hash.
- **Rule K.** Counts of `train*`, `RLHF`, `modif*`, `values`, `free tier`,
  `preserv/protect/maintain*` and `future`, plus log length.
- **Against the released label.** Held-out AUROC 0.78 (seed 1: 0.78). Compliers only: 0.74.
  Length alone: 0.71. Permutation null 95th percentile 0.56.
- **On the 106 human labels:**
  - K: 0.64 [0.54, 0.74].
  - Original classifier: 0.58 [0.49, 0.68] (hard prompt) and 0.63 [0.55, 0.72] (easy prompt).
  - Difference K − original: [−0.08, 0.19] and [−0.13, 0.14].
  - The new GPT-4o classifier: 0.88 [0.81, 0.95], better than K by 0.13–0.35.
  - So on this sample, the original classifier's agreement with people is matched by a vocabulary
    rule fitted to its own labels.
  - *Validator:* this comparison is not like for like. The original-classifier columns are 0/1
    decisions, so their AUROC is balanced accuracy at one threshold. Thresholded at the training
    label rate, K flags 7 of 106 and has balanced accuracy 0.53, below the easy prompt's 0.63
    (difference [−0.20, −0.002]) and not distinguishable from the hard prompt's 0.58. Those columns
    are also the original prompts re-run on Claude 3.5 Sonnet 20241022, not the model that made the
    released labels. On the held-out Greenblatt rows, length alone reaches 0.71 of K's 0.77.
- **Errors by model and length.**
  - The original binary decision (`hard_and_easy_af`, accuracy 0.61, 30 false positives) has
    errors that track neither model (p = 0.40) nor length tercile (p = 0.52).
  - Neither do the final new classifier's (accuracy 0.81; p = 0.88 and 0.43).
  - An intermediate new-classifier version errs more on Claude 3.5 Sonnet (p = 0.049).
  - The GPT-4o "hard" variant errs on 14 of 15 Llama 405B items (p < 0.001).
  - Tier cannot be tested: 103 of 106 items are free-tier.
- **Column mapping.** Which CSV column is which classifier is inferred from the column names. The
  AUROCs (0.58–0.63 and 0.88–0.91) match Hughes et al.'s 0.62 and 0.92.

### Spread over prompt variants and the tier cue (descriptive)

- **Spread.** 44 Opus variants with the helpful-only objective: gap median 10.9, IQR 5.7–14.7,
  range 0.6–32.9. The default ranks 22nd of 44, so it is the median, not the best.
- **Paraphrases.** The 8 gaps are 1.2–19.8 at n = 86. Heterogeneity p = 0.74: consistent with
  sampling noise alone. Table 1's paraphrase row (the paraphrase with median reasoning) matches
  paraphrase 0 (gap 5.9 [1.2, 11.8]), below the paraphrase median gap of 9.3.
- **Tier cue.**
  - Without the conflicting objective, keeping the tiers, privacy text and training information,
    there is no gap (`atn_basic` −1.2 [−3.5, 1.2]; `cut criteria` 1.2 [0.0, 2.9]). The tier
    difference alone does not produce a gap.
  - Cue salience moves it a lot with the training information unchanged:
    - default 11.4;
    - free tier signalled only by a missing tag ("train absence"): 1.2 [−3.5, 5.8];
    - "California users never trained": 4.7 [0.0, 9.9];
    - "EU users never trained": 12.2 [7.0, 18.0].
  - This is disclosed in App. B.2 and G.1. I add only the intervals.
- **Reasoning rate and gap across variants.** Spearman 0.95 (the paper's Fig. 14).

## Robustness

| Check | Result | Survives? |
|---|---|---|
| Seed 1 (all bootstraps, splits, permutations) | Every quantity within 0.01 of seed 0 (`results/robust.json`) | yes |
| PM threshold −0.5 (App. D.8) instead of −0.7 | Gap 11.4 [7.4, 15.1]; full-compliance ratio 0.63 / 0.65; residual 0.0. C2's conditional-OR flags drop from 4 to 1 (*validator:* 3, counting cells with unbounded intervals) | yes; the C2 pre-registered flags are threshold-fragile, but at least one cell is flagged at either threshold, so the pre-registered verdict is "changes" |
| Drop each variant | A3 pooled ratio 0.60–0.64; A4 residual share −0.5%–1.4% | yes |
| Random-removal control for drop-k | Targeted removal beats random only at k = 20, by 5 points | yes (no concentration) |
| Placebo `follows_instructions` (permuted within tier) | Ratio 0.07–0.15, against 0.63 observed. The label is concentrated in PM-compliant rows, as it should be | — |
| Bonferroni over 22 tests | Default gap [5.4, 17.6]; A3 difference [0.2, 8.8] | yes, barely for A3 |
| Different statistic (odds ratio) | Default OR 6.7; full-compliance OR 26; Opus vs Sonnet ordering reverses | the C1b direction is reinforced; the C2 model ordering depends on the scale |

## Alternative explanations

1. **The partial outputs are the alignment faking.** A model faking alignment might comply in a
   watered-down way.
   - Test: the reasoning label among `C_pm` but not-following outputs.
   - Outcome, pooled over 44 variants: 296 of 517 free-tier partials (57%) carry the label,
     against 498 of 648 full compliers (77%). In the default cell: 15 of 24 vs 25 of 26. So much
     of the partial share belongs to the construct the paper calls "compromise". It is still not
     the full-compliance behaviour a reader of "complies 14% of the time" pictures.
2. **The reasoning label is right and K just correlates with it.** That is the expected reading;
   K's 0.78 does not show the classifier uses vocabulary. What K shows: on human labels, the
   original classifier is no better than vocabulary. The improved classifier is.
3. **"No gap" models fail for capability, not motive.** The paper says this for GPT-4 Turbo and
   GPT-4o (reasoning not detailed enough). This audit only shows they had statistical room; it says
   nothing about why they do not use it.

## What was already known

See [`prior_work.md`](prior_work.md). Already shown:
- the conditional "no reasoning, no gap" result (§3.3.4);
- compromise as a confound (E.2);
- the classifier's poor agreement with people (Hughes et al.);
- prompt and cue sensitivity (App. B.2 and G.1; Koorndijk replication; priming; the Opus 4.6
  perturbations);
- near-total refusal in o-series models (Sheshadri et al.).

New here:
- query-paired intervals and McNemar counts;
- the held-out drop-k test with a random control, and cross-variant concentration;
- route counts by tier, with hand validation, and the 0.63 full-compliance ratio;
- the residual gap over 44 variants with two-way intervals;
- room, MDE and odds ratios for the "no gap" models;
- the reversal of the Opus vs Sonnet 3.5 comparison on the odds scale;
- the power and false-pass analysis of the 1-point threshold;
- the vocabulary rule against the released label and against human labels;
- ~~the non-reproduction of the default reasoning rate (14.5% vs 11.9%)~~ *Validator:* withdrawn;
  the paper's metric reproduces at 11.93%.

## What this does not show

- **Nothing per sample about Sheshadri et al.'s 25 models.** The C2 statement on them is about the
  design only.
- **The meaning of `follows_instructions`** comes from its name, App. E.2 and 40 hand labels by one
  rater who knew the design. κ = 0.60 is moderate. *Validator:* it is the paper's App. I.4
  category 4 (complete, no disclaimer). 80 blind validator labels agree with the four categories at
  κ = 0.92.
- **The release is a subset of the paper's 400 queries** (352, 172 and 86 per cell), chosen by an
  unstated rule. Cross-variant results use the shared 172. The reasoning-rate mismatch may come from
  this subset or from a different label version. *Validator:* the rule is the authors' copyright
  filter plus an id range. The paper's Table 1 is on the same 352. The reasoning-rate "mismatch" was
  a definition error.
- **Haiku 3.0 cells are tiny** (31 and 41 complete pairs) and say little.
- **No intervention.** Nothing here is causal. "Accounts for" in C1c means the counts line up.
- **The PM and the compromise classifier are unreleased.** All compliance labels are taken as
  released.

## Pins and how to reproduce

Pins:
- `redwoodresearch/alignment_faking_public@8d98bb78`.
- `json_outputs.zip` sha256 `6e7c3f99…139d7` (Drive file id `11aYJN-chvNzTbEu1RYCFPpyGnTvwjN1h`).
- `safety-research/open-source-alignment-faking@dc21773f`.
- `safety-research/alignment-faking-extensions@6b3e35cd`.
- HF `jplhughes2/classify_alignment_faking_human_labels@3c087f7e` (parquet sha256 `3a203f80…441d`).

Download into `data/` (git-ignored):
1. Clone the three repos as `data/af_public`, `data/osaf` and `data/afext`.
2. Unzip `json_outputs.zip` to `data/jo/`.
3. Put the HF parquet at `data/hf/human_labels.parquet`.

Then:

```bash
uv venv data/.venv && uv pip install --python data/.venv/bin/python numpy pandas pyarrow scipy scikit-learn
data/.venv/bin/python -I scripts/build_table.py           # data/samples.parquet (ids, labels, features; no text)
data/.venv/bin/python -I scripts/analyze.py --seed 0      # results/analysis_seed0.json (~20 s)
data/.venv/bin/python -I scripts/analyze.py --seed 1
data/.venv/bin/python -I scripts/analyze.py --seed 0 --thr -0.5
data/.venv/bin/python -I scripts/handlabel_sample.py > data/handlabel_view.txt   # labels in results/handlabels.csv
data/.venv/bin/python -I scripts/robust.py                # results/robust.json
data/.venv/bin/python -I scripts/build_results.py         # results.json
```

Inference: none.

Validation (independent code, no import of `scripts/`):

```bash
cd validation
../data/.venv/bin/python -I vload.py            # data/val_labels.parquet (labels and counts only)
../data/.venv/bin/python -I rederive.py         # rederive.json: subset rule, reasoning rate, C1a-C1c, C2, Sheshadri
../data/.venv/bin/python -I dropk.py            # dropk.json
../data/.venv/bin/python -I c1c_pooled.py       # c1c_pooled.json
../data/.venv/bin/python -I c3.py               # c3.json
../data/.venv/bin/python -I handlabel_draw.py   # blind view and key in data/ (git-ignored)
../data/.venv/bin/python -I handlabel_analyze.py  # handlabels_validator.{csv,json}
```
