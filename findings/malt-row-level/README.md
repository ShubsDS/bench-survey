# MALT: row-level checks (sandbagging comparison, review coverage, instruction visibility)

Status: run on the gated transcripts on 2026-10-27. Not raised with METR. These are the row-level tests that
`findings/malt-sandbagging-one-model/` and `findings/gated-benchmarks-public-side/` left untested.

## Pins

- `metr-evals/malt-transcripts-public@3521e8e22b6af12fea3249443e554b96b6fc4f49`: default config, all 13 shards (7,179 runs).
- `metr-evals/malt-public@6100006c2fd23d81e5afe2b1cc3bf3f3fff48df1`:
  - two `data/` shards (`public-00035`, `public-00038`) for the monitor-format check;
  - the `metadata` column of every `data/` and `default/` shard, read over HTTP.
- `ktolnos/rh-bench@1045a7336432c40182924bbd3698af292ea24acb`: `data/rh_bench_unified.parquet`.

MALT ships no per-run monitor scores. The comparison point is the post's best sandbagging AUROC, 0.91. That
figure is on the full dataset (1,505 prompted positives, 1,014 reviewed benign runs), not on the public split
used here.

## Definitions

- **Sandbagging positives.** Runs with a label in {match_weaker_model, partial_problem_solving, refusals,
  sabotage}: 834 runs, all Claude 3.7 Sonnet and all prompted. Variant A2 adds the 211 runs labelled with
  prompted reasoning_about_task, giving 1,045 (the post counts these).
- **Reviewed benign.** Label exactly `normal` with `manually_reviewed` true: 694 runs.
- **Cross-validation.** Detectors are scikit-learn HistGradientBoosting with 5-fold GroupKFold by `task_id`;
  regex detectors are plain match counts.
- **Intervals.** Task-cluster bootstrap, 1,000 resamples.
- **Null.** 100 permutations of labels within each task, run through the full pipeline.
  - It sits high (0.61–0.77) because many tasks hold only one class. For example, 112 of 169 positive tasks
    have no reviewed benign run, so a feature that identifies the kind of task predicts the label.
  - Each comparison is therefore also reported on shared tasks only.

## Lead 2/1: one-model confound

**Content-blind feature groups** (AUROC, with the task-bootstrap interval in brackets):

| Comparison | n pos / neg | Length and counts | Format quirks and tool mix | All content-blind (null p95) | Shared tasks only |
|---|---|---|---|---|---|
| A: sandbagging vs reviewed benign | 834 / 694 | 0.942 | 0.898 | **0.970** [0.959, 0.981] (0.744) | 0.963 |
| A2: with prompted reasoning_about_task | 1,045 / 694 | 0.919 | 0.863 | 0.957 [0.942, 0.970] (0.737) | 0.946 |
| B: model probe, 3.7 Sonnet benign vs Claude 4 reviewed benign | 1,222 / 681 | 0.834 | 0.876 | **0.935** [0.899, 0.959] (0.638) | 0.940 |
| C: 3.7 Sonnet only, sandbagging vs 3.7 Sonnet benign (unreviewed) | 834 / 1,222 | 0.911 | 0.890 | **0.950** [0.928, 0.968] (0.788) | 0.945 |

**Other cues in the same comparisons:**

| Comparison | Task family only | Tool-output dates (`ls` month) | Run start time (metadata) |
|---|---|---|---|
| A | 0.719 | 0.565 | 1.000 |
| B | 0.689 | 0.899 | 1.000 |
| C | 0.738 | 0.843 | 0.967 |

- **Model identity is readable without content (holds).** Comparison B: content-blind features give 0.935
  against a null p95 of 0.638. The dates in tool outputs alone give 0.899.
- **Run dates do not overlap (holds; not visible in message text).**
  - Reviewed benign runs start 2025-05-29 to 2025-06-11.
  - Prompted runs start 2025-04-07 to 2025-05-22.
  - So `first_called_at` alone gives AUROC 1.000 in A. It sits in node metadata, not in message content.
- **Same-model restriction leaves separation in place (holds).**
  - Comparison C gives 0.950, against 0.970 in A.
  - The sandbagging comparison is separable from length and tool-use counts whether or not the negatives
    share the model.
  - So model identity is available, but not needed, for a content-blind detector to beat 0.91.
  - C's negatives are unreviewed (METR estimates 6% label error) and cover 67 of the 169 positive tasks.
- **Effect on METR's monitors: untested.** No per-run monitor scores are released, and no monitor was run here.

## Lead 0/6: review coverage at row level

- **Row-level flags agree with the card (holds).** The per-run `manually_reviewed` flag matches the card
  table exactly.
  - Reviewed benign runs: 694 in total, 681 of them Claude 4 (98.1%).
  - Claude 3.7 Sonnet: 0 of 1,222 benign runs reviewed.
  - o1-preview: 1 of 1,439.
  - o3-2025-04-16: 1 of 130.
  - Seven models have no reviewed run.
  - Every positive run is reviewed.
- **Reviewed benign runs cover few tasks (holds).** They cover 57 tasks; sandbagging positives cover all 169.
- **The two repos agree on metadata (holds).** `malt-public` and `malt-transcripts-public` agree on model,
  source, review flag, labels and task for all 7,179 runs.
- **An earlier upload is still in the repo (observation).** `malt-public` keeps a `default/` folder (July 2025
  upload, 4.9 GB, older schema, same 7,179 run ids) that no config references.
- **rh-bench's MALT rows, joined by `source_id` = `run_id` (holds; tightens the earlier count).** All 572 rows
  join. rh-bench marks every one as human-verified.
  - Clean rows: 272 of 286 (95.1%) are unreviewed in MALT. That is 268 Claude 3.7 Sonnet rows plus 4
    o3-2025-04-16 rows; the earlier count was 268.
  - Hacking rows: the 224 Claude 3.7 Sonnet rows are exactly MALT's 224 prompted `sabotage` runs.
  - Prompt text: rh-bench's prompt contains "sabotag" in 224 of 286 hacking rows and in 0 of 286 clean rows.
  - So rh-bench serves the sabotage instruction to its detectors along with the label.

## Lead 3/5 and check 7: instruction visible; prompted vs natural positives; duplicates

- **The instruction is in every prompted transcript (holds).**
  - All 1,045 prompted transcripts open with a system message that contains an "Instructions:" block giving
    the sandbagging behaviour. It appears in 17 variants, each tied to one label, and none is used by any
    unprompted run.
  - No unprompted Claude 3.7 Sonnet run and no reviewed benign run has such a block.
  - The rule "system message has an Instructions: block" gives AUROC 1.000 in comparisons A, A2, C and D.
  - Outside these comparisons, the rule is not specific: 233 of 6,134 unprompted runs (other scaffolds) also
    have such a line.
- **The monitor-format file carries it too (holds on two shards).** In `malt-public`'s input/output file, the
  block is in the input of 295 of 295 samples from 22 prompted runs, and of 2 of 5,261 unprompted samples.
  - The post says each monitor chunk repeats the first five messages, and the system message is the first.
  - Whether METR's monitors received it is not stated (untested).
  - If they did, the reported 0.91 sits below a one-line rule; if they did not, the released data does not
    match the monitored data.
  - Either way, a monitor scored on the released data must strip the system message first.
- **The rewrite left no extra mentions of being instructed (ruled out).** A narrow regex for phrases like
  "I was told to" or "system prompt" fires in the reasoning of 5.2% of prompted runs and 6.6% of benign 3.7
  Sonnet runs (AUROC 0.515 in A).
- **Behaviour words remain in the agent's text (holds, by design).** A count of behaviour words (sabotage,
  refuse, underperform, "evaluation or deployment", and others) over the agent's own text gives 0.991 in A
  and 0.987 in C. METR's rewrite prompt keeps such content on purpose, so this is a confession baseline, not
  a leak. It is above the post's best monitor.
- **Prompted vs natural positives (holds, small n).**
  - The public split has 28 natural sandbagging-like runs (unprompted `gives_up` or `reasoning_about_task`):
    Opus 4 10, Claude 3.5 Sonnet 9, Sonnet 4 5, GPT-4o 4. None has an Instructions block.
  - Prompted vs natural: content-blind features give 0.885 [0.79, 0.99].
- **Duplicates (ruled out).**
  - No two runs share a run id, an identical transcript or identical agent text.
  - At word-3-gram cosine ≥ 0.9, 5 pairs (7 runs) are near-copies, all benign vs benign on the same task.
  - The four obfuscation configs reuse every run id by design; their text was not downloaded.

## Bias direction

Up. The sandbagging comparison can be scored from three cues without detecting sandbagging:

- the injected system prompt;
- run dates;
- length and tool-use counts.

Restricting to one model does not remove the length signal. Whether the published monitor AUROC rides on
these cues is untested.

## Reproduce

```bash
python -I check_transcripts.py --cache data            # ~1.6 GB download; ~35 min on a laptop
python -I check_review.py --cache data --remote-public-meta
```

Needs pandas, pyarrow, scikit-learn and scipy; `--remote-public-meta` also needs duckdb and an `hf` login with
access. The scripts read the data as text only. The outputs hold counts, AUROCs, and run and task ids, never
transcript text.
