# Liars' Bench and TRACE: row-level checks

Status: run on the gated releases on 2026-10-27, after the user accepted both gates. No model or
API was called. Outputs hold counts, scores and row ids only, never message text. "Holds" means
the effect is measured in the released rows; effects on published detector numbers are not
measured unless stated.

## Pins

| Data | Revision |
|---|---|
| Liars' Bench | `Cadenza-Labs/liars-bench@503399b81aff28d6812b0ea4585607d5e4b7d3c4` (same as the public-side audit) |
| TRACE | `PatronusAI/trace-dataset@31d87f06078eca3ab6eaf1e06e5ea6fe9f2b7a6d` (same) |
| BoolQ (to check Soft-Trigger labels) | `google/boolq@35b264d03638db9f4ce671b711558bf7ff0f80d5` |
| rh-bench (its copy of TRACE) | `ktolnos/rh-bench@1045a7336432c40182924bbd3698af292ea24acb` |

Papers: Liars' Bench arXiv 2511.16035v2; TRACE arXiv 2601.20103v1. Published numbers are copied
into the scripts with their table.

## Method

- **Bag-of-words baselines.** TF-IDF (1–2 grams) and logistic regression, out-of-fold scores from
  5-fold cross-validation with each base item kept in one fold. Base items: the statement (ID), the
  WMDP question (HP-C, HP-KR), the BoolQ item (ST), the final question (GS), the user prompt (CG).
  IT has one scenario, so folds are stratified.
- **Aggregation.** AUROC is computed within each model and averaged, as the paper does. Rows from
  kimi-k2.6 (5,628 ID, 164 IT) are in the release but not in the paper, and are left out of the
  comparisons.
- **Nulls.** Labels are permuted within model and the whole fit is rerun: 100 times for subsets up
  to 8,000 rows, 20 times above that, 200 times for TRACE. Fixed rules get 1,000 permutations.
- **Caveat.** The vectorizer is fitted on all rows before the folds (label-free). For TRACE, refitting
  it inside each fold changes AUROC by at most 0.014.

## Liars' Bench (`check_liars_bench.py`, `liars_bench_checks.json`)

### 1/7: what a detector can read without detecting a lie

Macro AUROC over models. The paper's text detectors see user turns and the response, not the
system prompt.

| Subset | User turns only | Response only | Length/format | Fixed rule | Published (judge / mean probe / best) | Null p95 |
|---|---|---|---|---|---|---|
| GS | **0.998** | 0.996 | 0.835 | gender-word regex on the final question: **0.978** | 0.45 / 0.52 / 0.56 | ≤0.56 |
| ST | **0.887** | 0.617 | 0.621 | prefix-only BoW: **0.925**; answer is "False": 0.627 | 0.94 / 0.65 / 0.94 | ≤0.51 |
| IT | 0.809 | 0.986 | 0.883 | message count: **0.808** | 0.96 / 0.61 / 0.98 | ≤0.52 |
| HP-KR | 0.733 | 0.880 | 0.734 | "claims not to know": **0.851** | 0.63 / 0.36 / 0.96 | ≤0.52 |
| HP-C | 0.633 | 0.503 | 0.578 | — | 0.77 / 0.48 / 0.77 | ≤0.52 |
| ID | 0.539 | 0.893 | 0.529 | — | 0.99 / 0.71 / 0.99 | ≤0.51 |
| CG | 0.508 | 0.989 | 0.592 | — | 0.99 / 0.85 / 1.00 | ≤0.54 |

- **Gender-Secret: the topic gives the label (holds).**
  - The 91 final questions behind the 231 lies and the 133 behind the 531 honest rows have none in
    common.
  - A gender-word regex, written before any fitting, matches 221 of 231 lies and 0 of 531 honest
    rows. The 10 misses use words outside the list.
  - The responses restate the topic, so a response-only model also reaches 0.996.
  - Every published detector scores 0.42–0.56 on GS, so the published numbers are not inflated.
    A detector trained or tuned on GS can, though, score near 1 by recognising gender questions.
- **Soft-Trigger: the prefix gives most of the label (holds).**
  - The prefix and trigger family alone, with no passage, question or answer, reach 0.925 (gemma
    0.999). The best published detector reaches 0.94, and the probes 0.65–0.68.
- **Insider-Trading: turn count is a format cue (holds).**
  - Confirmation rows (21 messages) are 1,922 lies to 173 honest; report rows (19 messages) are
    1,155 to 3,623.
  - Message count alone gives 0.808. That beats the mean probe (0.61), the follow-up probe (0.74),
    self-evaluation (0.75) and the unrelated-question classifier (0.77).
- **HP-KR: claiming ignorance is nearly the label (holds).**
  - The rule "the response says it does not know", with no access to the model's belief, gives
    0.851 (qwen 0.961, llama 0.913, mistral 0.678).
  - That beats every published detector except the upper-bound probe (0.96).
  - The user turn also carries signal (0.733). Template 2 has 5 lies among 714 rows. WMDP-cyber has
    91 lies among 2,610 rows, against 1,286 among 4,182 for bio.
- **HP-C: weaker user-turn signal (holds weakly).** User turns give 0.633, above the probes
  (0.48–0.56) and below the judge (0.77).
- **Ruled out for user turns: ID (0.539) and CG (0.508).** Their response-only scores (0.89, 0.99)
  read the claim itself, which is the task, so they are not counted as shortcuts.

### 0/2: who and what produces each class

- **CG (holds): the system prompt and model fix the label.** All 888 rows sit in label-pure
  (model, system prompt) cells. Lies come from 43 system prompts and honest rows from 35, with no
  overlap. The 188 lie-instructed rows are all lies. System-prompt-only BoW gives 0.994.
- **ID (holds): neutral prompts never produce lies.** Neutral system prompts give 0 lies in 9,124
  rows; lie-instructed prompts give 14,059 lies and 3,243 honest rows. System-prompt-only BoW gives
  0.893.
  - The prompt is hidden from text detectors.
  - Probes read activations conditioned on it: mean probe 0.71 on ID, 0.85 on CG.
- **GS, HP-C, HP-KR, IT, ST (ruled out).** Every lie row shares its model and system prompt with
  honest rows, and system-prompt-only BoW is at chance (0.45–0.48).
- **Lie rates vary by model**, so pooled scores can read the model. HP-KR: llama 139 lies in 2,139
  rows, mistral 697 in 2,358. The paper averages within model, which avoids this.

### 6: label construction

- **ST labels (holds): a label means the answer differs from BoolQ.** In all 23,601 rows matched to
  BoolQ validation, `deceptive` equals "answer differs from BoolQ gold".
- **ST trigger description (holds): the paper states the triggers the wrong way round.** The paper
  (text and Table "soft_trigger_subsets") says male names, 12:00–23:59 timestamps and formal
  greetings trigger lies. In the release, the paper's rule scores well below chance:
  - gender AUROC 0.161;
  - time AUROC 0.056;
  - greeting: 9 of 20 prefixes are lie-majority, and by our reading they are the informal ones.

  So lies come with female names, morning times and informal greetings. The paper's own appendix
  examples agree with the release. The labels are consistent; the description is inverted.
- **ST, llama gender split (holds): lies do not depend on the trigger.**
  - Name gender does not predict the label: AUROC 0.486; every name gives 40–58% lies.
  - In the other gender splits and all time splits, the trigger predicts the label at AUROC
    0.92–1.00 once inverted. Greeting splits were not scored per model.
  - These 1,000 lies are wrong answers, but the trigger the paper gives as the reason for lying
    does not explain them.
- **ST, safe prefixes (holds).** By the release's direction, safe prefixes still carry wrong
  answers labelled lies: 68–87 per split in the llama, mistral and qwen time splits and the mistral
  and qwen gender splits. The paper reports 100% accuracy without triggers, after filtering.
- **HP-C (holds).** `deceptive` equals "chosen letter ≠ `model_belief`" in 5,400 of 5,400 rows. In
  810 of them, `model_belief` differs from the WMDP answer.
- **HP-KR (holds).** A simple denial parse combined with `model_belief` reproduces the Claude
  Haiku judge's label in 7,000 of 7,068 rows. The 68 disagreements were not adjudicated. All 1,256
  rows where the model has no belief are honest.
- **ID (holds).** A crude parse of the verdict agrees with the stored label in 22,211 of 22,229
  parsed rows. The 18 disagreeing row indices are in the json.
- **Metadata (holds).** In GS, the `meta.trained_gender` key is present in 147 lies and no honest
  row.
- **Untested.** IT's GPT-4o report labels, and the CG validity judge, for lack of stored judge
  outputs.

### Bias direction (Liars' Bench)

- **Up** for any detector trained or tuned on GS, ST, IT or HP-KR rows: topic, prefix, turn count
  or the "I don't know" form give 0.81–0.99 without detecting a lie.
- **Not up** for the published zero-shot numbers. Those detectors score near chance on GS, and below
  the trivial rules on IT and HP-KR, so the rules expose weak detectors rather than inflated ones.
- **Probes:** up on CG and ID, through the system prompt (already in the catalogue).
- **The inverted ST description** misleads reproduction, not scoring.

## TRACE (`check_trace.py`, `trace_checks.json`)

517 rows: 268 hack, 249 benign. One split (`train`). The paper's metric, Detection Rate, is the
macro F1 of the binary hack call:

- best isolated (N=1): 0.45 (GPT-5.2);
- best contrastive (N=10): 0.63;
- on this release, a coin flip gives 0.50 and a constant prediction 0.33–0.34.

The paper's runs vary the benign ratio, so its F1 values are not strictly comparable with the
50/50 numbers below.

### 1/2: content-blind and prompt-trace baselines (holds)

BoW, 5-fold, mean of 5 fold seeds; null p95 0.55–0.56 (max 0.61).

| View | AUROC | Macro F1 at 0 |
|---|---|---|
| Assistant prose only (no tool calls, no outputs) | 0.850 | 0.77 |
| User turns after the first | 0.830 | 0.75 |
| Full transcript | 0.798 | 0.72 |
| First user turn only (the task, before any assistant action) | **0.750** | **0.67** |
| Tool calls and outputs only | 0.750 | 0.69 |

- **The task prompt carries the label.** It was written by the generator under the class-specific
  prompt, and alone it beats the paper's best contrastive detector on macro F1 (0.67 against 0.63).
- **What it reflects.** Only the hack prompt asks for "specific constraints, business requirements,
  or time pressures". In first user turns, hack rows mention these more often than benign rows:
  - urgent or ASAP: 16% against 9%;
  - next week or demo: 16% against 7%;
  - pressure or blocked: 15% against 7%;
  - a pressure-phrase count gives AUROC 0.605 (null 0.536).
- **Benign-prompt words are weaker.** In assistant prose:
  - "comprehensive": 63% of benign rows against 44% of hack rows;
  - "best practice": 11% against 4%;
  - a count of the benign prompt's phrases gives 0.587 (null 0.544).
- **Explicit negations are rare.** Phrases such as "instead of gaming" appear in only 8 benign and 4
  hack assistant texts.
- **Structure is weak.** Length, turn count and tool-call count give 0.53–0.58. Trajectory id gives
  0.581 (null 0.541), with hack ids running higher.

### 7: does the transcript name the hack? (holds in part)

- **Regex counts.** A user call-out regex over non-first user turns matches 115 of 268 hack rows
  and 47 of 249 benign rows (AUROC 0.63; the "any match" rule gives macro F1 0.60). An assistant
  admission regex ("you're right", "I apologize", …) matches 138 and 82.
- **Hand check of 20 random hack matches** (ids in the json): in 14 the user names the hacked
  behaviour, for example removed assertions, hard-coded outputs, stubbed checks or tests skipped
  for speed. The other 6 raise a concern without naming it.
  - Extrapolated, about 80 of the 268 hack rows (≈30%) have a user catching the hack. This is a
    rough estimate from n=20.
- **Hand check of 20 random benign matches:** in 6 the user flags behaviour of a kind the taxonomy
  lists as a hack (skipped tests, removed validation, redundant "verification" computation, a test
  that passes without the checked input), which the assistant then fixes. Under the generation
  prompts these count as benign.
- **Effect.** The call-out is a real but noisy cue. It cuts both ways: detectors reading user
  approval miss hacks, as the paper notes, and benign rows contain caught-and-fixed lapses.
- **The regexes are exploratory.** They were written after looking at single-word class rates.

### 5: duplicates (holds, small)

- **One duplicate pair.** There is one split, so there is no cross-split leakage within TRACE. Under
  word 5-gram Jaccard, `trajectory_0516` and `trajectory_0517` are identical (Jaccard 1.0, both
  labelled 1.3.2). No other pair reaches 0.3. So 516 transcripts are distinct, against the stated
  "517 unique".
- **rh-bench's copy.** rh-bench serves all 517 rows by id, all in its `train` split, with labels that
  match TRACE (249 clean, 268 hacking). Its 249 clean rows all carry `hacking_category:
  evaluation_gaming`.

### Bias direction (TRACE)

- **Up** for any detector trained, fine-tuned or few-shot prompted on TRACE rows: the task prompt
  alone reaches 0.75 AUROC, and assistant style 0.85. These are generator-under-prompt traces, not
  hack content.
- **Not up** for the published zero-shot numbers (≤0.63 macro F1). They sit below these baselines,
  so they are not explained by the cue.
- **Contrastive N=10 setting:** untested whether clusters let a model read the style gap between
  the classes.

## Untested

- Detector runs on the shortcut-free slices: GS with gender questions on both sides, ST with prefix
  categories balanced within class, IT report rows only, TRACE with matched task prompts.
- IT and CG judge labels against a hand-labelled sample.
- Whether the inverted ST description goes beyond the paper text, for example into training code
  that is not public.

## Reproduce

From the directory that holds `out/`, with the gates accepted and `hf` logged in:

```bash
python -I out/check_liars_bench.py --cache data --out out/liars_bench_checks.json --perms 100 --perms-large 20
python -I out/check_trace.py --cache data --out out/trace_checks.json --perms 200
```

The scripts need numpy, pandas, scikit-learn, scipy and pyarrow. They call `hf download` at the
pinned revisions, parse metadata with `ast.literal_eval` only, and execute no downloaded code. Run
times: about 15 minutes and 5 minutes on a laptop.
