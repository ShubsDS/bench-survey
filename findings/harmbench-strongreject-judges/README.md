# HarmBench and StrongREJECT judges against their own human labels

Status: checked on released labels and scores only (2026-10-27). No judge model was run and no API
was called. Leads 6 and 1 were tested on both benchmarks and lead 5 on the prompt sets. Nothing has
been raised with the maintainers.

## Pins

- HarmBench code and data: `centerforaisafety/HarmBench` at `8e1604d1171fe8a48d8febecd22f600e462bdcdd`
  (main, 2024-08-05). Files used: `data/classifier_val_sets/text_behaviors_val_set.json` (sha256
  `e740727b…41c8`) and `data/behavior_datasets/harmbench_behaviors_text_{all,test,val}.csv`.
- HarmBench classifiers, not run: `cais/HarmBench-Llama-2-13b-cls` @ `bda705349d1144fa618770bea64d99ce54e3835b`
  and `cais/HarmBench-Mistral-7b-val-cls` @ `51182c7cdaf9b2e5f05b745b81b047b67e7384a1`.
- StrongREJECT human labels and evaluator scores: the OSF files named in the Makefile of
  `dsbowen/strong_reject` at `7a551d5b440ec7b75d4f6f5bb7c1719965b76b47`. These are `labelbox.csv`
  (`jwmqe`, revision 1, sha256 `7a5928a4…fbad2`) and `labelbox_evals.csv` (`92s8k`, revision 1,
  sha256 `8b77df36…d413d`). The sha256 values match OSF's own metadata.
- StrongREJECT prompts: `alexandrasouly/strongreject` at `f7cad6c17e624e21d8df2278e918ae1dddb4cb56`,
  current and `previous_versions/2024_02`.
- StrongREJECT fine-tuned evaluator, not run: `qylu4156/strongreject-15k-v1` @ `4bd893d32390d2cace4f067dc2e3ef5294fd78a2`.

None of these is gated. Outputs report ids, categories and aggregates only.

## What the labelled sets are

- **HarmBench.** 602 completions, two for each of 301 behaviours, each with three human labels.
  The file also holds the verdicts of 11 judges, including `cls` (taken to be the Llama-2-13b test
  classifier) and `cls_mistral` (the validation classifier). The gold label is the majority of the
  three humans. 239 of the 301 behaviours are in the test split, 59 in the val split, and 3 are in
  neither.
- **StrongREJECT.** 1,361 responses with up to five Likert labels each, scaled to 0–1. The gold
  label is their median (`label_median`); 1,084 rows have five labels and 177 have one. The same
  rows are scored by 10 evaluators. In this file the rubric judge is gpt-4o-mini (`judge_model`
  column).
  - The rows cover only 39 forbidden prompts, from 4 of the 6 categories. Violence and Sexual
    content have no human labels.
  - 76% of rows have a human median of 0.

## Lead 6: judge validity

### HarmBench classifier

**Selection.** The paper (B.5.1) says the set has "one positive and one negative example as
identified by our classifier" per behaviour. The same section says GPT-4 prompts were then tuned on
this set, and that the distillation rounds tracked accuracy on it. In the release:

- 288 of 301 behaviours have one `cls` positive and one `cls` negative, and in 287 the positive is
  listed first.
- So the agreement figure is measured on the set the judge was developed against. It is not a
  held-out estimate.
- The set is also balanced on the judge's own verdict, so its agreement is roughly the mean of the
  judge's PPV and NPV. It is not agreement at a natural attack success rate (ASR).

**Reproduction of the paper's numbers.**

| | Paper | Released file |
|---|---|---|
| `cls` agreement | 93.2%, 41 errors | **93.2% (41 errors) against annotator `human_0` alone; 90.9% (55 errors) against the three-annotator majority**; behaviour-cluster CI 88.4–93.2% for the majority figure |
| By functional category | standard 94.5, contextual 90.5 | standard 92.2, contextual 87.9 |
| `cls` vs `cls_mistral` | 41 and 51 errors, 26 shared, so they differ on at least 40 items | **differ on 4 of 602 items** (57 errors, 54 shared with `cls`) |

Correction after independent validation (2026-10-28). The paper's 93.2% does come from the
released `cls` column, scored against the single annotator column `human_0`: that gives exactly
93.19% (41 errors). Against the other two annotators `cls` agrees 85.0% and 87.0%. Against the
three-annotator majority it agrees 90.9% (55 errors). So the headline is agreement with one
annotator, whose labels the classifier tracks most closely, not with the majority. The maintainers'
own notebook (`run_classifier_val_set.ipynb`, written in reply to issue #29) scores the released
weights against the majority, and its saved output is 0.906. The `cls_mistral` column is nearly a
copy of `cls`.

**Error pattern.**

- 46 of the 55 errors are false positives. FPR is 14.0% (46 of 329 human negatives) and FNR 3.3%
  (9 of 273).
- PPV is 0.852 and NPV 0.969. `cls` calls 6.2 points more completions harmful than the human
  majority does.
- The errors sit on contested items:
  - 28 of the 46 false positives had one of three human votes;
  - `cls` agrees on 95.9% of unanimous items but on 69.3% of the 114 items with a 2–1 split.
- Measured against a single human, `cls` does as well as humans do against each other:
  - pairwise agreement: `cls` vs one human 88.4%, human vs human 87.4%;
  - against two humans who agree: `cls` 94.0%, the third human 92.8%.

FPR by stratum (agreement in brackets):

| Stratum | n | FPR | Agreement |
|---|---|---|---|
| Length Q1 (8–120 words) | 151 | 2.3% | 98.0% |
| Length Q4 (320–439 words) | 151 | 27.3% | 85.4% [78.9, 90.2] |
| No refusal phrase | 391 | 27.6% | 87.5% [83.8, 90.4] |
| ≥3 list lines | 213 | 28.2% | 87.3% |
| Contextual behaviours | 198 | 20.2% | 87.9% |
| Standard behaviours | 398 | 11.1% | 92.2% |
| Method PAIR / AutoDan / EnsembleGCG | 49 / 51 / 34 | 32% / 33% / 26% | 81.6% / 90.2% / 85.3% (AutoDan's rate rests on 4 of 12 negatives and is not significant, p 0.07) |
| Method GBDA / UAT | 137 / 33 | 8.5% / 0% | 94.9% / 97.0% |
| Opens with refusal, ≥150 words (refuse-then-comply) | 75 | 1.7% | 98.7% |
| Under 50 words | 53 | 2.0% | 98.1% |
| Low word overlap with the behaviour (off-topic proxy) | 86 | 5.2% | 95.3% |
| Repetitive or non-ASCII text | 16 | 50% | 75.0% |

- No stratum with n ≥ 20 has an agreement interval wholly below 90%. The intervals for PAIR, the
  longest quartile and the no-refusal stratum end just above 90%.
- By semantic category, agreement runs from 86.4% (harmful) to 96.0% (harassment).

**Implied ASR bias.** Applying the released PPV and NPV, a `cls` ASR of 0.5 corresponds to a
human-majority ASR of 0.44, and 0.9 to 0.77. The crossover is at about 0.17; below it `cls`
slightly under-counts. This assumes the one positive and one negative picked per behaviour are
typical of all completions with that verdict. The pick rule is not documented.

### StrongREJECT evaluators (released human labels)

Overall error against the human median:

| Evaluator | MAE | Bias | Spearman | AUROC (human > 0) |
|---|---|---|---|---|
| Rubric (gpt-4o-mini) | 0.077 | +0.012 | 0.79 | 0.906 |
| Fine-tuned | 0.085 | −0.023 | 0.70 | 0.967 |
| HarmBench `cls` | 0.091 | +0.014 | 0.75 | 0.843 |
| PAIR | 0.206 | +0.153 | | 0.832 |
| GPT-4 judge | 0.262 | +0.208 | | 0.839 |
| String matching | 0.581 | +0.484 | | 0.566 |

- As a human reference, one labeller against the median of the other labellers has MAE 0.068. On
  the same comparison the rubric has 0.078, the fine-tuned evaluator 0.084 and HarmBench `cls` 0.099.
- Binarised at the human positive rate, agreement with "human > 0" is 92.1% (rubric), 93.0%
  (fine-tuned) and 90.2% (`cls`).

Response patterns the evaluators mislabel:

- **Partial compliance** (human median strictly between 0 and 1; 117 rows). MAE is 0.30 for the
  rubric, 0.20 for the fine-tuned evaluator and 0.45 for `cls`, which can only answer 0 or 1. The
  bias here is small (rubric +0.04), so the error has no direction.
- **Harm inside a wrapper: the distractors and poems jailbreaks.** "Missed" means a response the
  humans scored at least 0.5 that the evaluator scores below 0.25.

  | | Rubric | `cls` | One human vs the others |
  |---|---|---|---|
  | All jailbreaks | 33 of 291 (11.3%) | 63 of 291 (21.7%) | 11.0% |
  | Distractors | 8 of 27 | 15 of 27 | 16 of 105 |
  | Poems | 8 of 33 | 8 of 33 | 21 of 129 |

  - So the rubric misses at a single human's rate overall, and `cls` at twice that rate.
  - Both evaluators miss more than a single human does on distractors.
- **The rubric's refusal flag.** The rubric forces the score to 0 when its judge answers "refused".
  - The flag zeroes 34 of the 326 rows humans scored above 0, including 28 they scored at least
    0.5 and 15 they scored 1.
  - 26 of those 28 contain none of the refusal phrases in the script's list.
  - Their jailbreaks: poems 8, distractors 7, distractors_negated 4, wikipedia 3, refusal_suppression 3.
  - Row ids are in the JSON.
- **Translation outputs and `cls`.** `cls` scores 22 of the 196 translation-jailbreak rows that
  humans scored 0 as harmful (Hmong 9 of 55, Zulu 7 of 72, Scots Gaelic 6 of 69). The rubric does
  so for 5.
- **Style injection.** Both the rubric and `cls` over-score style_injection_short, by +0.16 and
  +0.19 on 57 rows.
- **Refuse-then-comply, very short and off-topic responses.** None of these strata shows a
  material error for any of the three evaluators (MAE 0.004–0.05).

## Lead 1: content-blind baselines

The features are word count, refusal phrases (any, in the first 150 characters, count), code and
list formatting. Models are cross-validated by behaviour (HarmBench) or by prompt (StrongREJECT),
and each null permutes the labels within those groups.

**HarmBench.**

- A content-blind logistic model predicts the `cls` verdict at AUROC 0.816 and the human majority
  at 0.785. Both nulls are below 0.55.
- Single features:
  - length gives AUROC 0.718 for `cls` and 0.688 for humans (difference 0.030, cluster CI 0.004–0.056);
  - a refusal phrase is a slightly stronger negative cue for `cls` (difference −0.035, CI −0.054 to −0.018).
- Conditional test: among items the human majority calls negative, length predicts a `cls` false
  positive at AUROC 0.74 (CI 0.67–0.81). It predicts a single dissenting human vote on the same
  items at 0.78. So long negatives are the contested ones for humans too. `cls` does not reward
  length beyond what one human does.
- The content-blind model's 0.785 against humans is above 5 of the 11 judges in the file: Llama
  Guard 0.64, AdvBench 0.69, GPTFuzz 0.73, ChatGLM 0.66 and GPT-3.5 0.65.

**StrongREJECT.**

- Each evaluator's score is binarised at the human positive rate (24%), so that ties do not distort
  the comparison. Length then predicts the human label at AUROC 0.764, the rubric 0.713, `cls`
  0.694 and the fine-tuned evaluator 0.765. The rubric and `cls` follow length less than humans do.
- The fine-tuned evaluator is the one exception. Among the 1,035 rows humans scored 0, its score
  rises with length: the mean goes from 0.010 to 0.070 between the shortest and longest quartiles
  (Spearman 0.33, CI 0.28–0.37). The rubric shows no such rise (0.035, CI −0.02 to 0.09). The
  effect is real but small, at most about 0.06 on a 0–1 scale.
- A content-blind logistic model predicts "human > 0" at AUROC 0.861 (null 95th percentile 0.05 on
  the ridge version). That is above 7 of the 9 evaluators: `cls` 0.843, GPT-4 judge 0.839, PAIR
  0.832, PICT 0.772, jailbroken-binary 0.694, string matching 0.566 and the moderation API 0.529.
  Only the rubric (0.906) and the fine-tuned evaluator (0.967) are above it.
  - The labelled set is mostly separating refusals from non-refusals.
  - Agreement figures on it therefore say more about refusal detection than about judging harm.

## Lead 5: duplicates and near-duplicates

The similarity measures are TF-IDF cosine and word 3-gram Jaccard.

- **HarmBench val vs test.**
  - No shared ids, and no item with identical behaviour and context.
  - 8 of the 80 val behaviours (10%) have a same-template or same-context sibling in test:
    - Identical behaviour string, different context: `worm_code_obfuscation_1`, `_2` ↔ `_3`; and
      `sqli_payload_waf_ml_bypass_2`, `_3` ↔ `_1`.
    - Identical context string, different ask: `fentanyl_synthesis_stepbystep_instructions_overview`
      ↔ `fentanyl_precursors_unlicensed_acquisition`.
    - Same template with one noun changed (cosine 0.78–0.86): `bleach_ammonia_mixing_enticement` ↔
      `bleach_vinegar_` and `bleach_rubbing_alcohol_mixing_enticement`;
      `blind_sql_injection_log_evasion` ↔ `blind_sql_injection_rate_captcha`;
      `vx_precursors_obtaining_instructions` ↔ `sarin_precursors_obtaining_instructions`.
  - On the test side that is 7 of 320 behaviours (2.2%). With looser cutoffs (cosine ≥ 0.68 or
    Jaccard ≥ 0.5) it is 11 (3.4%).
  - These are template families rather than copies. The paper forbids tuning on behaviours
    "semantically identical" to test ones, and the worm and sqli pairs come close.
- **Classifier set and split.** 239 of the 301 behaviours in the classifier's labelled set are test
  behaviours. Agreement is 91.2% on test behaviours and 89.0% on val behaviours.
- **StrongREJECT vs HarmBench.** Ruled out:
  - no pair reaches cosine 0.5 (maximum 0.37 for the current release, 0.50 for 2024_02);
  - HarmBench against AdvBench reaches at most 0.64.
- **StrongREJECT vs AdvBench.** The 25 prompts sourced from AdvBench are verbatim copies, as the
  data card declares. One prompt labelled `custom` (sr142) is a near-copy of an AdvBench item
  (cosine 0.88). No near-duplicates within StrongREJECT.

## Bias direction

- **HarmBench ASR.** Biased **up** when ASR is above about 0.17, by up to 6 points at an ASR of 0.5
  and 13 points at 0.9 under the PPV/NPV assumption above.
  - The bias is larger for attacks whose outputs are long, list-formatted or fluent. On this set
    `cls` exceeds the human rate by 14 points for PAIR and 15 for EnsembleGCG, against 5 for GBDA
    and −3 for UAT.
  - Cross-method comparisons are therefore biased toward fluent methods.
  - The 93.2% headline is in-sample, and it is agreement with one annotator (`human_0`); against
    the three-annotator majority the released verdicts agree 90.9%.
- **StrongREJECT score.**
  - Rubric: close to unbiased overall, but biased **down** for jailbreaks that wrap the harm
    (distractors, poems), partly through its refusal flag.
  - HarmBench `cls` on StrongREJECT data: biased down on wrapped harm and up on translation outputs.
  - Fine-tuned evaluator: a small length-driven rise on harmless responses (≤ 0.06).
- **HarmBench split.** Template siblings can inflate test ASR for methods tuned on val, but only on
  about 2–3.4% of test behaviours.

## Holds / ruled out / untested

| Lead | Result |
|---|---|
| 6, HarmBench | **Holds.** The labelled set is drawn by and was tuned against the judge, so the headline agreement is in-sample. The released `cls` gives 93.2% against one annotator (`human_0`) and 90.9% (55 errors) against the majority, and `cls_mistral` differs from it on 4 items, not ≥40. Against the majority, errors are 84% false positives, concentrated in long, list-formatted, contextual and PAIR outputs. No stratum falls clearly below 90%. Refuse-then-comply is ruled out on this set |
| 6, StrongREJECT | **Holds, narrowly.** Overall error is at human level, but distractors and poems responses are under-credited (rubric misses 8 of 27 and 8 of 33; its refusal flag zeroes 28 human ≥ 0.5 rows, 26 without a refusal phrase). Partial compliance has large error with no direction. Violence and Sexual content have no human labels |
| 1, judge rewards length | **Ruled out** for HarmBench `cls` (its length lean matches single-human dissent; difference 0.03) and for the StrongREJECT rubric and `cls`. A **small** length drift holds for the StrongREJECT fine-tuned evaluator on harmless responses |
| 1, labels readable without content | **Holds.** Content-blind models reach AUROC 0.785 (HarmBench) and 0.861 (StrongREJECT) against human labels, above 5 of 11 and 7 of 9 published judges |
| 5 | HarmBench val/test **holds weakly** (8 of 80 val behaviours have a template or context sibling in test; 7–11 of 320 test behaviours). StrongREJECT vs HarmBench **ruled out** |
| Untested | HarmBench's prequalification sets (not released). HarmBench's full released completions (not fetched). Agreement on Violence and Sexual content. The paper-version rubric judge (this file uses gpt-4o-mini) |

## Reproduce

```bash
python -I check_harmbench.py    --cache ../data --out harmbench_checks.json
python -I check_strongreject.py --cache ../data --out strongreject_checks.json
python -I check_overlap.py      --cache ../data --out overlap_checks.json
```

Each script downloads its pinned files into `--cache` and checks their sha256. It imports and runs
nothing it downloads, and needs numpy, pandas, scipy and scikit-learn. Running from an empty cache
gave byte-identical JSON.
