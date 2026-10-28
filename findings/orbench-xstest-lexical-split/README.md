# Over-refusal benchmarks: OR-Bench's safe and toxic sets separate on wording; labels mostly hold

Audit date 2026-10-27. Checks 6 (labels and scorers), 1 (content-blind baselines) and 5
(duplicates) of the suite in `scope.md`. No model was run. Nothing has been reported to the
maintainers.

## Targets and pins

| Benchmark | Source | Pin | Licence |
|---|---|---|---|
| OR-Bench (Cui et al., arXiv 2405.20947 v5) | HF `bench-llm/or-bench`, not gated | revision `e36d8b80e81837c8a8f264bbb2a49f1b32c7e272` | CC-BY-4.0 |
| XSTest v2 (Röttger et al., NAACL 2024) | GitHub `paul-rottger/xstest` (the old `exaggerated-safety` name redirects there) | commit `d7bb5bd738c1fcbc36edd83d5e7d1b71a3e2d84d` | prompts CC-BY-4.0; completions under the model licences |

CSV sha256 values are checked in `common.py`. The OR-Bench values match the Git LFS oids at that
revision. Sizes: OR-Bench-80K has 80,359 rows, Hard-1K 1,319 and Toxic 655. XSTest has 250 safe
and 200 unsafe prompts, plus 5 models × 450 completions, each with two human annotations, a final
human label, a string-match label and a GPT-4 label.

Outputs hold row ids (0-based CSV row), released categories, 12-character prompt hashes,
counts and single words. They hold no prompt text.

## Reproduce

```bash
cd out
python -I check_duplicates.py   --cache data   # duplicate_checks.json      (~1.5 min)
python -I check_baselines.py    --cache data   # baseline_checks.json       (~2 min)
python -I check_xstest_labels.py --cache data  # xstest_label_checks.json
python -I check_hand_labels.py  --cache data   # hand_label_checks.json, from hand_labels.csv
python -I check_hand_labels.py  --cache data --emit   # prints the seeded sample for re-reading
```

Fetch URLs are given in `common.py`. The Python used was numpy 2.5.4, scikit-learn 1.9.1, scipy
1.18.1 and pandas 3.1.0.

## Results

### Check 6: labels

**OR-Bench, hand-read sample.** The sample is seeded (numpy `default_rng(20261027)`): 60 Hard-1K,
40 Toxic and 40 80K rows. One reader (the auditor) labelled each prompt once, as comply,
borderline or decline, against a rubric fixed before reading (in `check_hand_labels.py`). A "safe"
label is contradicted by "decline", and a "toxic" label by "comply". Intervals are Wilson 95%.

| Split (released label) | n | Contradicted | Interval | Borderline | Contradicted or borderline |
|---|---|---|---|---|---|
| Hard-1K (safe) | 60 | 4 | 0.026–0.159 | 26 | 30 (0.38–0.62) |
| 80K (safe) | 40 | 1 | 0.004–0.129 | 3 | 4 (0.04–0.23) |
| Toxic (toxic) | 40 | 2 | 0.014–0.165 | 8 | 10 (0.14–0.40) |

- **Contradicted rows.**
  - Hard-1K rows 51, 806, 935 and 964: three are privacy (covert tracking or profiling of a
    person) and one is deception.
  - 80K row 38724 (illegal: concealing the source of funds).
  - Toxic rows 541 (violence: war fiction) and 636 (sexual: product recommendations).
- **Borderline rows.** In Hard-1K the borderline items are mostly requests to build things that
  imitate malware, replica documents or money, or covert entry, wrapped in "for educational
  purposes" or "legally" (illegal 10, privacy 6, deception 4, harmful 4). In Toxic, 4 of the 8 are
  adult sexual content, where the right answer depends on the deployment's policy.
- **Comparison with the paper.** The authors had two experts read all of Hard-1K and report 38 of
  1,319 (2.9%) flagged (Appendix U). That figure lies inside this sample's interval for the
  contradicted rate, so the sample does not show a higher error rate than the authors report.
- **Holds as a measurement.** Outright label errors are a few percent in every split; this sample
  cannot separate their rate from the authors' 2.9%. About half of the sampled Hard-1K is items on
  which careful policies differ, and this is the subset the paper uses for headline over-refusal
  rates. A refusal on those items is counted as over-refusal.
- **Caveat.** This is one reader without adjudication. The borderline share depends on that
  reader's policy and should be read as indicative.

**Cross-label near-copy.** Toxic row 244 and 80K row 3255 make the same request in different
words (TF-IDF cosine 0.907, deception), and one is labelled toxic while the other is labelled safe.
This is the only cross-label pair at cosine ≥ 0.8 (1 of 655 toxic prompts).

**XSTest, released classifiers against the released human labels.** Refusal here means a full or
partial refusal. Rates are on the 250 safe prompts.

| Model | Human | String match | GPT-4 judge |
|---|---|---|---|
| Llama-2 (original prompt) | 0.596 | 0.484 | 0.360 |
| Llama-2 (new prompt) | 0.296 | 0.268 | 0.160 |
| Mistral + guardrail prompt | 0.188 | 0.152 | 0.096 |
| GPT-4 | 0.084 | 0.132 | 0.064 |
| Mistral-Instruct | 0.016 | 0.016 | 0.000 |

| Pooled over 5 models | Safe: agreement | Safe: human vs auto refusals | Unsafe: agreement | Unsafe: human vs auto refusals |
|---|---|---|---|---|
| String match | 0.904 (0.886–0.919) | 295 vs 263 | 0.860 (0.837–0.880) | 864 vs 728 |
| GPT-4 judge | 0.897 (0.879–0.913) | 295 vs 170 | 0.738 (0.710–0.764) | 864 vs 684 |

- **Where the classifiers differ from the humans.**
  - Both classifiers undercount refusals overall. The GPT-4 judge misses 127 of the 295 human
    refusals on safe prompts, mostly partial refusals.
  - String match over-counts GPT-4's refusals on safe prompts (0.132 against 0.084) and
    under-counts Llama-2's (0.484 against 0.596).
- **What is unchanged.** The order of models is the same under all three labellings.
- **Already reported.** These numbers reproduce the XSTest paper's Table 2, and the authors state
  the discrepancies there. Human annotator agreement in the files is 93.8–98.4%, matching the
  paper.
- **Holds, not new.** The error matters for users who score XSTest with the string match or a
  GPT-4 judge: those scores read over-refusal low,
  mostly by dropping partial refusals.

### Check 1: content-blind baselines

AUROC for predicting the to-be-refused class, with 1,000-resample bootstrap intervals. Each null
is the 95th percentile under permuted labels (200 permutations; 50 for the bag-of-words model).
The last column is the share of the safe set that a rule tuned to refuse 90% of the unsafe set
also refuses.

| Task | Detector | AUROC | Null p95 | Safe refused at 90% unsafe refused |
|---|---|---|---|---|
| Hard-1K vs Toxic | prompt length (shorter = toxic) | **0.769** (0.747–0.793) | 0.524 | 0.63 |
| | released category tag only | **0.740** (0.718–0.763) | 0.524 | 0.57 |
| | count of benign-intent words (fixed list) | **0.674** (0.652–0.694) | 0.520 | 0.83 |
| | bag-of-words logistic regression, 5-fold | **0.924** (0.911–0.935) | 0.517 | **0.24** |
| 80K sample (5,000, seeded) vs Toxic | prompt length | **0.831** (0.814–0.847) | 0.518 | 0.49 |
| | bag-of-words | **0.965** (0.958–0.972) | 0.529 | **0.09** |
| XSTest safe vs unsafe | prompt length | 0.534 (0.476–0.589) | 0.544 | 0.94 |
| | count of benign-intent words | 0.505 | 0.506 | 0.98 |
| | bag-of-words | **0.788** (0.746–0.828) | 0.558 | 0.53 |

- **Length.** Hard-1K prompts average 117 characters and Toxic prompts 88. 57% of Hard-1K
  prompts contain a word from the fixed benign-intent list, against 25% of Toxic.
- **Most separating single words.** For Hard-1K, these are "harmless", "educational", "purposes",
  "program", "security" and "legal". For Toxic, they are "subtly", "someone" and "sexual".
- **How the sets were built.** Both sets come from the same step (§3.2–3.3, Appendix X). An LLM
  rewrites toxic seeds, the moderator ensemble judges each rewrite, and rewrites judged safe go to
  80K while the rest go to Toxic.
- **What that means for the cue.** The split between the sets is the moderator's verdict on
  similar rewrites, and a bag-of-words model recovers that verdict at 0.92–0.97. The verdicts that
  define "safe" are therefore largely predictable from wording. The paper itself notes that its
  LLM judges "can be sensitive to keywords" (Appendix R).

**What the benchmark claims.**
- OR-Bench presents the Hard-1K rejection rate against the Toxic rejection rate as a trade-off
  plot, and says the best-aligned model sits top-left. It does not claim the two sets are matched
  in wording.
- XSTest claims its safe prompts "superficially resemble unsafe prompts in terms of the
  vocabulary they use" (§3.1).

**Holds as a measurement.**
- On OR-Bench, a word-count model with no notion of intent refuses 90% of Toxic while refusing
  24% of Hard-1K and 9% of 80K.
- So a low over-refusal score paired with a high toxic-refusal score does not show that a model
  reads intent. A policy that relaxes when it sees "legally" or "for educational purposes" would
  score well. On a real attack that same policy is the textbook wrapper jailbreak.
- The cue may be partly intended, since OR-Bench sets out to measure sensitivity to such phrasing.
  But the paired plot rewards the cue rather than testing it.
- XSTest is better matched. Length and the benign-intent count are at their nulls, but a
  bag-of-words model still reaches 0.79, from first-person and action words in the unsafe
  contrasts (e.g. "how", "commit", "my", "ex").

**Untested.** Whether any model's refusals actually follow these cues. That needs model
completions on OR-Bench, which the dataset repository does not release.

### Check 5: duplicates and overlap: ruled out

| Comparison | Result |
|---|---|
| Hard-1K in 80K | 1,319 of 1,319 after normalisation, all with the same category. This is by design: Hard-1K is the subset of 80K that many models refused. Row 1271 differs from its 80K copy only in punctuation or whitespace |
| Toxic vs 80K | 0 exact; 1 at cosine ≥ 0.8 (the cross-label pair above) |
| Toxic vs Hard-1K | 0 exact; 0 at cosine ≥ 0.8 |
| Within 80K | 5 exact duplicate pairs (2 with different categories: rows 35715/70556, 18383/36043); 195 rows (0.24%) at cosine ≥ 0.9, and 1,026 (1.3%) at ≥ 0.8 |
| Within Hard-1K / Toxic | 0 at cosine ≥ 0.9; 8 / 16 at ≥ 0.8 |
| XSTest vs any OR-Bench split | 0 exact; 0 at cosine ≥ 0.8 |

Cosine is on word 1–2-gram TF-IDF. Within-split near-duplication is below the suite's 1% flag at
cosine ≥ 0.9. There is no XSTest–OR-Bench overlap, so reporting both does not double-count items.

## Bias direction

- **Hard-1K label errors and borderline items.** A refusal on these counts as over-refusal, so
  Hard-1K over-refusal rates are biased up for careful models, and permissive models gain in the
  ranking. Size: a few points from outright errors. The borderline half is a matter of policy, not
  error, and the benchmark does not mark it.
- **Toxic label errors.** Of the Toxic items, 5% (1–17%) are ones a careful policy would answer,
  so helpful models' toxic-acceptance rates are biased up slightly.
- **XSTest automatic scoring.** It biases over-refusal down on average (the GPT-4 judge by about
  40% relative on safe prompts). The direction varies by model for the string match. Model order
  is preserved in the released set.
- **OR-Bench lexical separability.** It biases the trade-off plot in favour of models that key on
  benign-intent phrasing. The plot cannot tell such a model from one that reads intent.

## Status

| Lead | Status |
|---|---|
| 6, OR-Bench labels | Outright errors a few percent, consistent with the authors' 2.9%. About half of the sampled Hard-1K is borderline (one reader). 1 cross-label near-copy |
| 6, XSTest scorers | Holds: the automatic labels undercount refusals, but the authors already report this (Table 2) |
| 1, surface cues | Holds for OR-Bench: length gives 0.77 and bag-of-words 0.92 on Hard-1K vs Toxic. Partial for XSTest: bag-of-words 0.79, length at its null. Model reliance untested |
| 5, duplicates and overlap | Ruled out |
