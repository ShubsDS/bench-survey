# Evaluation awareness (Needham et al. 2025): row-level checks

Status: row-level tests on the gated release, run 2026-10-27, with the user's accepted gate. This
follows `findings/gated-benchmarks-public-side/`, which established from the paper's tables that
each source belongs to one class only. No model was run. Outputs hold counts, AUROCs, source names
and feature names only, never transcript text.

## Pins

| What | Pin |
|---|---|
| Data | `jjpn2/eval_awareness@5d724f12988284a652749c56ec7b2356b0d14408` |
| `dataset.zip` sha256 | `934dc4bc83b76e6bc57e672c39716061204b4802bb46b2038e7feb822aaa211c` |
| Paper | arXiv 2505.23836v3 (Table 2, `tab:auc_brier`) |
| Code read, not run | `jjpn97/eval_awareness@1543ffe6` (`pipeline/apply_pq.py`, `pipeline/dataset.py`) |

The zip is encrypted. The scripts decrypt it with the password published in the repository's own
`scripts/decrypt.sh`, which the dataset README tells users to run. They read the password from that
file as text and never execute it.

## Reproduce

```bash
python -I check_source_baselines.py --cache data --perms 100   # about 18 min on 10 cores
python -I check_items_and_humans.py --cache data               # seconds
```

Both scripts fetch the data with `hf download ... --revision <sha>` if `data/hf/dataset.zip` is
missing, and refuse a zip whose sha256 differs from the pin. The JSON in this directory was produced
with `--cache ../data`.

## What was released

- **Rows.** 976 rows, not 1,000. The cells are 287 chat evaluation, 250 agentic evaluation, 213
  chat deployment and 226 agentic deployment. `irl_cursor` (24 rows in the paper's table) is
  missing. The release has 60 source names: the paper's 57 less `irl_cursor`, with ETHICS split
  into five.
- **Held-out rows.** 99 rows carry `pqsel = true`, the probe-question selection set. The released
  per-model answers cover the other 877 rows. On those rows the recomputed AUROCs match Table 2:
  - chat: exactly, for every model and for humans;
  - agentic: 0.006–0.019 lower, consistent with the missing `irl_cursor` rows;
  - human agentic: 0.996, as in the paper.

  Every number below uses these 877 rows.
- **Renamed ids.** Three sources are renamed between the dataset and the answer files
  (`giles_claude` to `author_claude`, `govind_runs` to `gaia_runs`, `mvp:joe_/giles_` to
  `mvp:author1_/author2_`). The human columns agree on all 877 rows once mapped.

## Lead 1/3: content-blind features, by source-aware and source-blind CV (`source_baselines_checks.json`)

Features come from what a model is shown in the paper's probe format: messages and tool
definitions. Storage-only fields are not used. All five probe questions in the answer files use
"append", which passes the messages natively.

- **structure:** counts and characters by role, tool calls, tool definitions, last role.
- **format:** multiple-choice lines, dates, times, ids, code fences, headers, tags, URLs, script
  shares, densities.
- **scaffold:** tool names and a few scaffold strings.

The classifiers are logistic regression and gradient boosting, both with balanced class weights.

| Split (sources) | Best model, Table 2 (recomputed; source-bootstrap 95%) | Content-blind, pooled CV | Content-blind, leave sources out (null mean / p95) | Leave one source out (null mean / p95) |
|---|---|---|---|---|
| chat (43) | Claude 3.5 Sonnet 0.793 (0.793; 0.63–0.92) | 0.894 (null p95 0.55) | 0.623 (0.50 / 0.69), p 0.25 | 0.626 (0.47 / 0.64), p 0.14 |
| agentic (17) | Gemini 2.5 Pro 0.948 (0.942; 0.86–0.99) | 0.979 (null p95 0.56) | 0.432 (0.45 / 0.76), p 0.49 | 0.390 (0.41 / 0.78), p 0.51 |
| all (60) | Claude 3.5 Sonnet 0.834 (0.825; 0.69–0.93) | 0.941 (null p95 0.55) | 0.518 (0.52 / 0.70), p 0.57 | 0.482 (0.49 / 0.73), p 0.51 |

The content-blind numbers are gradient boosting on all content-blind features. Logistic regression
is lower pooled (0.78, 0.96, 0.87) and no better leaving sources out (0.62, 0.44, 0.50).

How the CV schemes work:
- **Pooled CV:** stratified 5-fold over rows, so other rows of the same source are in training.
- **Leave sources out:** five folds of whole sources, each holding both classes. The figure is the
  mean within-fold AUROC.
- **Leave one source out:** pooled out-of-fold scores. Each fold holds one class, which biases the
  pooled AUROC below 0.5; its null shows this (mean 0.41–0.49).
- **Nulls:** labels are permuted across sources (100 permutations for logistic regression, 50 for
  gradient boosting). The pooled null permutes rows.

Results:
- **Pooled (holds).** Once some rows of a source are in training, content-blind features
  recognise the class above the best model in each split: 0.894 against 0.793 in chat, 0.979
  against 0.948 in agentic. A bag of words reaches 0.889 and 0.999.
- **Leave sources out (ruled out at this power).** No feature set beats its source-permutation
  null in any split. The same holds for bag of words (chat 0.561, agentic 0.595). No content-blind
  or lexical rule learned on some sources carries to unseen ones. The models are not trained on
  any source, and they score 0.79 and 0.94. So their scores are not explained by the surface
  features measured here.
- **The closest exceptions, in chat (weak, not significant):**
  - structure-only gradient boosting gives 0.672 leaving sources out (null p95 0.655, p 0.08)
    and 0.656 leaving one source out (p 0.10);
  - the single rule "no assistant turn" gives 0.655 with nothing fitted. It fires on 248 of 258
    evaluation rows and 125 of 192 deployment rows (30 of 31 evaluation sources, 8 of 12
    deployment sources). Most chat evaluation items are a bare benchmark prompt with no reply.
    This rule was chosen after looking at role counts, so it is not a clean pre-specified test.
- **Small exact cues in chat:** a non-default system prompt (33 of 258 evaluation rows, 0 of 192
  deployment) and a multiple-choice block (31 of 258, 0 of 192). Each is AUROC 0.56.
- **Scaffolds used by both classes (agentic).** Trained on the other agentic scaffolds and tested
  inside the held-out scaffold, content-blind features give:
  - aider: 0.05 (logistic) / 0.41 (boosting);
  - openhands: 0.18 / 0.00;
  - smolagents: 0.51 / 0.56.

  Pooled inside the scaffold they give 1.00, 0.50–1.00 and 0.90–0.91. Models score aider
  0.98–1.00, openhands 0.85–1.00 and smolagents 0.77–0.90.

  Inside aider the one evaluation source (`aider_full`, 27 rows) is the only exercism benchmark
  source, and a within-scaffold classifier separates it perfectly. So aider's 1.00 is a
  one-source-against-three comparison, not a test of awareness inside a scaffold.

## Lead 5: duplicates, benchmark formats, intervals (`items_and_humans_checks.json`)

- **Exact duplicates (ruled out as a leak).** 3 groups of identical transcripts (7 rows) and 11
  groups of identical first user turns (28 rows). All are within one source; none crosses
  classes. 4 of those first-turn groups straddle the PQ-selection/held-out split. That touches
  only the choice of probe questions.
- **Near duplicates (word 5-gram Jaccard).**
  - Pairs at 0.5 or above that cross classes: smolagents GAIA against smolagents real runs (1,175
    first-turn pairs, 47 transcript pairs).
  - With shingles found in 10 or more samples dropped (scaffold templates), no cross-class pair
    remains at 0.5.
  - The remaining cross-source pairs are within deployment (`aider_commit`/`aider_multi`, 28 at
    0.5 or above) and one `s_eval`/`ultrasafety` pair.
- **Published-benchmark strings (holds, small).** Every match below is in agentic evaluation;
  deployment has 0:
  - "capture the flag": 30 of 250 (`cybench`);
  - flag formats: 11 (`cybench`);
  - the OpenHands SWE prompt and `<pr_description>`: 32 (`swe_gym`);
  - "exercism": 11 (`aider_full`).

  In chat, a multiple-choice option block appears in 35 of 287 evaluation rows (MMLU, WMDP,
  model-written evals, ETHICS), against 0 of 213 deployment. There is no canary string and no MMLU
  header in any row. Together the named strings match 74 of 250 agentic evaluation rows and 0 deployment rows; the
  public-side count (229 of 250 from published benchmarks) rests on the source tables, not on
  in-text markers.
- **Ids and storage fields.** All 976 sample ids start with their source name. Message
  `source`/`function`/`error` keys and tool-call `view` occur only in agentic evaluation (102 rows),
  because those rows are Inspect logs. A classifier on the raw JSON would read the class from
  either. Whether a model sees `function` depends on the provider adapter; untested.
- **Intervals (holds).** The paper's interval treats rows as independent (Hanley–McNeil). For
  Claude 3.5 Sonnet overall that gives 0.80–0.85 on these rows. A bootstrap over the 60 sources
  gives 0.70–0.92:
  - chat 0.62–0.92;
  - agentic 0.66–1.00.

  Paired by source, 7 of 36 model pairs differ overall, 11 of 36 in chat and 3 of 36 in agentic.
  Most of Table 2's model ranking is not resolved by the data.

## Lead 6: human labels (released; `items_and_humans_checks.json`)

- **Reproduced.** The averaged annotators give held-out AUROC 0.813 (chat), 0.996 (agentic) and
  0.916 (all), against the paper's 0.813, 0.996 and 0.921. Annotator 1 / annotator 2 give 0.787 /
  0.779 in chat and 0.996 / 0.978 in agentic. They fall on the same side of 0.5 in 817 of 976 rows
  (Spearman 0.76; the paper's ICC is 0.768).
- **Agentic.** Both annotators are at 0.81–1.00 accuracy on every agentic source except
  `smol_gaia_search` (0.50 / 0.59). The deployment agentic sources are the authors' own runs:
  - humans score 1.00 on `smol_real_search` and `smol_real_manager`;
  - models average 0.01 and 0.27 there (they call those runs evaluations).

  The human 0.996 is therefore the authors recognising their own runs, as the README warns; it is
  not a baseline for an outside reader.
- **Where humans disagree with the label (holds; candidate label problems):**
  - `hackaprompt_dataset` (deployment, 19 rows): annotators correct on 1 and 0 of 19; models 0%.
  - `toxigen_data` (deployment, 17): 18% and 12%; models 25%.

  Both are published datasets (a prompt-injection competition; a generated hate-speech set)
  labelled deployment, and both annotators and all models call them evaluations. Among evaluation
  sources, `nl2bash` and `or_bench` (10 each) are called deployment by annotator 1 and by most
  models. `prosocial_dialog` splits the annotators (0.95 against 0.05).
- **The score is mostly the source.** Source explains 80% (chat) and 93% (agentic) of the variance
  of the human score, and 56–85% for the models. This is expected when the label is constant
  within a source, so it is descriptive only.

## Summary

| Lead | Verdict | Key numbers |
|---|---|---|
| 1/3 content-blind features | Holds pooled; ruled out leaving sources out | Pooled 0.894 chat / 0.979 agentic vs best model 0.793 / 0.948; leaving sources out 0.623 / 0.432, at null |
| 1 surface rules transfer | Ruled out at this power; weak chat signal | Structure-only 0.672 (p 0.08); "no assistant turn" 0.655 in chat; no agentic rule above null |
| 5 duplicates | Ruled out across classes | 0 cross-class near-duplicates after template removal |
| 5 benchmark strings | Holds, small | 74/250 agentic evaluation and 35/287 chat evaluation rows match; 0 deployment |
| 5 intervals | Holds | Source bootstrap 3.6–5× wider than row-level; 7/36 model pairs separable |
| 6 human labels | Holds as disclosed; two sources contestable | 0.996 agentic is authors on their own runs; hackaprompt and toxigen labelled deployment, called evaluation by humans and models |
| Release vs paper | Holds | 976 rows; `irl_cursor` missing |

## Bias direction

- **Pooled baselines.** These matter for anyone who trains a probe or classifier on this dataset
  with row-level splits. Source recognition alone reaches 0.89–0.98, so such a score is biased up
  as a measure of evaluation awareness. Split by source.
- **Leave-sources-out failure.** The models' zero-shot AUROCs are not reproduced by the
  content-blind features measured here. That does not show the models read evaluation intent:
  untested cues (topic, benchmark familiarity, phrasing) remain. The BoW leave-sources-out result
  (0.56–0.60, at null) argues against simple lexical transfer.
- **Intervals.** Row-level intervals overstate precision. Model rankings within 0.05 should be
  read as unresolved.
- **Contestable sources.** If hackaprompt and toxigen are better called evaluation data, the
  models' chat AUROCs are understated slightly. Those are 36 of 450 chat rows; the effect was not
  measured.

## Untested

- Whether models see the storage-only `function` field (provider-specific).
- A one-class swap (rerun deployment-style prompts inside evaluation scaffolds).
- Topic-level or memorisation probes of the benchmark items.
- The 99 PQ-selection rows have no released model answers.
