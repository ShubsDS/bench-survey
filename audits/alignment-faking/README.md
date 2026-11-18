# Alignment faking: Claude 3 Opus's compliance gap is broad across queries and fully tracked by the reasoning label, but about a third of it is partial compliance

Status: complete, 2026-11-17. Not yet validated by an independent refuter. No inference was run
(0 calls, 0 USD). Evidence level for each claim:

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
used, so the release is a subset, chosen by an unstated rule.

## What we found

| Conclusion | Published | Reproduced (release) | Audit result | Verdict |
|---|---|---|---|---|
| Opus default gap | 11.3 ± 2.1 | 50/352 − 10/352 = **11.4** | Query-paired bootstrap [7.4, 15.1]; Bonferroni (22 tests) [5.4, 17.6]. b = 47 free-only vs c = 7 paid-only compliers; McNemar p = 2×10⁻⁸; conditional OR 6.7 [3.0, 17.6] | **holds** |
| Opus default reasoning rate | 11.9 ± 1.7% | 51/352 = **14.5%** | Does not reproduce: 2.6 points above the paper, outside its ±1.7. Compliance reproduces exactly (14.2%) | non-reproduction, unexplained |
| Gap carried by a few queries? | — | — | 158 of 172 pooled queries contribute positively; 44 queries give half the pooled gap. Removing the top 10 (chosen on held-out variants) removes 3.5% of the default gap (random-removal 95th percentile 8.3%) | **holds**: broad |
| Gap on full compliance | — | — | `follows_instructions` and PM: **7.1** [4.5, 10.1] = 0.63 [0.45, 0.83] of 11.4; pooled over 44 variants 0.63 [0.57, 0.68]. Odds scale: OR 26 [4.3, 1066] (b = 26, c = 1) | **size changes** (×0.63), existence holds |
| Gap without the reasoning label | ≈2 points (99% vs 97%) | default: 0.0 [−2.0, 2.0] | Pooled over 44 variants: **+0.1** [−0.9, 1.2] of 11.4. 1 of 44 variants has an interval above 0 | **holds** |
| "No gap" models (Claude 3 Sonnet, Claude 3 Haiku, Claude 3.5 Haiku, GPT-4 Turbo, GPT-4o) | "almost no" / "no" | gaps −12.9 to +2.4 | Paid rates 1.7–12.9%, so room ≥ 87 points. In 9 of 9 cells the gap interval excludes the gap an Opus-sized odds ratio would give (7–33 points) | **holds** |
| Sheshadri "5 of 25" (> 1 point, n = 200) | 5/25 | not reproducible | A zero-gap model passes the threshold with probability 4–40% (paid rate 0.5–40%). Near the floor (0.5%), an Opus-sized odds ratio gives a 2.3-point gap against a 4.6-point MDE | **L1 lead; blocked** |
| Reasoning label = reasoning, not vocabulary | AUROC 0.62 (old), 0.92 (new) vs people | — | Keyword rule K vs the released label: held-out AUROC 0.78 (null 95th percentile 0.56; length alone 0.71). On the 106 human labels: K 0.64 [0.54, 0.74], original classifier 0.58 [0.49, 0.68] / 0.63 [0.55, 0.72], new 0.88 [0.81, 0.95] | **partial lead** |

Bias direction:
- The PM-based compliance metric makes the gap about 1.6 times larger in points than full
  compliance does. Most paid-tier "compliance" is partial: 9 of 10 paid-tier PM compliers in the
  default cell are labelled as not following instructions.
- On the odds scale, full compliance shows a *larger* contrast. So the existence of an effect
  holds; its size in points is inflated.

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

**Hand validation.** The compromise classifier's prompt is not in the public repo, so I hand-labelled
40 PM-compliant outputs:
- 12 + 12 free-tier and 8 + 8 paid-tier, half of each `follows_instructions` True;
- blind to tier and labels, one rater, item ids and labels in `results/handlabels.csv`, no text
  committed.

Results:
- `follows_instructions` True: 19 full, 1 partial.
- False: 7 full, 10 partial (high-level, sarcastic, deliberately useless, "some people claim"
  framing, harm-reduction reframing), 3 outright refusals. All 3 refusals were paid-tier.
- κ = 0.60, agreement 80%.

**Effect on the gap.**
- On full compliance (`C_both`) the gap is 7.1 points [4.5, 10.1], against 11.4.
- Difference 4.3 [1.4, 7.1]; Bonferroni [0.2, 8.8].
- Dropping each variant leaves the pooled ratio between 0.60 and 0.64.
- Threshold −0.5 instead of −0.7: 0.63 (default) and 0.65 (pooled).
- The paper discloses compromise as "a constant issue confounding our results" (App. E.2). New
  here: the count by tier, and the size of the effect on the headline gap.

### C1c. Per sample, the reasoning label tracks the gap

- **Default cell.** 40 of 50 free-tier compliers carry the label. The other 10 equal the 10 paid
  compliers, so the residual gap is 0.0 [−2.0, 2.0].
- **Pooled over 44 variants** (two-way bootstrap over variants and queries):
  - residual +0.1 [−0.9, 1.2] against a gap of 11.4 [8.7, 14.3];
  - residual share 0.9% [−9%, 9%];
  - dropping each variant gives −0.5% to 1.4%;
  - on full compliance, +0.04 [−0.9, 1.1].
- **Single variants.** Only `cut_examples` has a residual interval above 0 (+6.4 [1.7, 10.8]). That
  is 1 of 44, about the 2.2 expected by chance.
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
| PM threshold −0.5 (App. D.8) instead of −0.7 | Gap 11.4 [7.4, 15.1]; full-compliance ratio 0.63 / 0.65; residual 0.0. C2's conditional-OR flags drop from 4 to 1 | yes; the C2 pre-registered flags are threshold-fragile |
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
- the non-reproduction of the default reasoning rate (14.5% vs 11.9%).

## What this does not show

- **Nothing per sample about Sheshadri et al.'s 25 models.** The C2 statement on them is about the
  design only.
- **The meaning of `follows_instructions`** comes from its name, App. E.2 and 40 hand labels by one
  rater who knew the design. κ = 0.60 is moderate.
- **The release is a subset of the paper's 400 queries** (352, 172 and 86 per cell), chosen by an
  unstated rule. Cross-variant results use the shared 172. The reasoning-rate mismatch may come from
  this subset or from a different label version.
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
