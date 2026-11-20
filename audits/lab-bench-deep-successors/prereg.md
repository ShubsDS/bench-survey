# LAB-Bench deep dive: did the construction flaw and the human scoring rule travel to successors?

Pre-registration, written 2026-11-20 on branch `audits-round3`, before any options-only rule was
computed on any successor, version, port or reused subset. Parent audit: [`../lab-bench/`](../lab-bench/)
(validated, 2026-11-17).

## Inherited question

**What the parent established (validated).**
- LAB-Bench SeqQA, HF `futurehouse/lab-bench` @ `5c77cec6`: in 6 of 15 subtasks (240 of 600 public
  items) the options alone give the key (centroid rule on ORF-seq-AAseq, PCR-gene-enzprimers,
  PCR-seq-enzprimers, PCR-gene-gibshindprimers, PCR-gene-gibssmaprimers; middle-value rule on
  Prop-seq-gcpercent). DbQA `variant_multi_sequence`: 80/80.
- The human baseline scores "unsure" as wrong even when the guess was right.
- No per-item outputs of any published model were found (as of 2026-11-17).

**What it left open.** Whether the flaw is present in other versions, ports and reuses, and in
LABBench2; whether successors carry the human scoring rule; how exposed each published SeqQA
number compared with the human line is; whether any per-item model outputs exist.

**Outcomes.**
- Q1 "yes, travelled": a successor/version/port releases SeqQA items in multiple-choice form and
  the frozen rules reach the thresholds below on at least 4 of the 6 S subtasks.
  "No, fixed": the successor has no options (free response with computed grading), or the cue
  subtasks are excluded, or the rules are at chance on all S subtasks. "Cannot tell": items gated
  or not released.
- Q2 "carried": a successor's human line is the paper's sure-and-correct accuracy (unsure = wrong).
  "Changed": it credits unsure answers (for example by chance) or has no human line.
- Q3: arithmetic bounds only (below). No result here is evidence that any model used the cue.
- Q4: item-level analysis only if the recoverability criterion below is met; otherwise "per-item
  outputs found but not analysable", with counts.

## What was looked at before this file was written (disclosure)

- LABBench2 (`EdisonScientific/labbench2`): dataset card schema (public README), GitHub harness
  code and paper reports at commit `5eafca56`. Seen: no option fields in the schema; report
  questions contain no lettered option lists (0 of 19 tag/mode files for claude-opus-4-6);
  SeqQA2 is graded by validators; the per-file summary averages (`HybridEvaluator`) for
  claude-opus-4-6. In SeqQA2 `mutation_restriction` the expected output is "None" on 17 of 20
  items in one report file (seen while checking format; anything built on it is **post hoc**).
- HuggingFaceBio `seqqa-carbon-curated-3tasks` README and figures (an existing options-only
  result by others; read, not recomputed).
- DeepSeek-R1 per-item reasoning chains (`lihaoxin2020/deepseek-reasoner-full-lab_bench-r1`):
  an exploratory probe of whether the chosen option can be recovered. It printed, per subtask, how
  many items could be mapped and whether the mapped option was the key, using a content-based
  item match (later found unreliable; `doc_id` follows the HF item order at subtask level). That
  probe's key/distractor counts are therefore seen; the analysis below is defined with that
  knowledge, and any result from it is labelled exploratory.
- System cards and reports: text and figures read (inventory), no computation.
- No options-only rule has been run on any other revision, mirror, port or subset.

## Analysis 1. Options-only rules on every released multiple-choice version (Q1)

**Units.** Every distinct SeqQA and DbQA parquet released under HF `futurehouse/lab-bench`
(revisions `7268767a` 2024-07-16, `10866fa8` 2024-08-20, `8e6bb002` 2024-12-18, `4709d14f`
2025-02-19, `8137378e` 2025-07-15, and the parent's `5c77cec6` as reference), the Inspect Evals
port (dataset revision pinned in `lab_bench.py`), the mirrors the parent found, and the
HuggingFaceBio 3-task curated subset.

**Rules (frozen; no tuning on these data).**
- R1, the parent's rules, imported by path from `../lab-bench/scripts/surface.py`: `centroid`
  (mean character-3-gram Jaccard) and `num_center` (middle value) for numeric items.
  The rule applied to a subtask is the one the parent used for it (centroid for the five sequence
  subtasks, num_center for GC-percent; centroid elsewhere, num_center where all options are numbers).
- R2, independent: summed Levenshtein distance to the other options, smallest wins (numeric
  medoid, summed absolute difference, when all options are numbers). Code written here, not the
  validator's.
- Ties get fractional credit. Chance = 1/k (no refusal option).

**Held-out.** The S set and the rules were fixed on `5c77cec6`; every other version is new data.
Within each version, items are also split into halves by `sha1(id)` parity; both halves are
reported.

**Placebo.** (a) Permutation null: key drawn uniformly among an item's options, 1,000 draws,
p = (1 + #null ≥ obs)/1001. (b) A content-free placebo rule: pick the option with the smallest
`sha1(option text)`; it must be at chance. (c) The same rules on the 9 F subtasks.

**Intervals.** Version-level accuracy over S and over all of SeqQA: percentile bootstrap over
subtasks (templates), 2,000 draws, seed 0. Per-subtask: Wilson.

**Thresholds.** A subtask "carries the cue" in a version when R1 or R2 ≥ 0.90 and p < 0.01. The
version "carries the flaw" when ≥ 4 of 6 S subtasks carry it. Changes in item text between
versions are reported as counts of changed ids, changed keys and changed options (no text).

**Power.** With 40 items per subtask and chance 0.25, a rule at 0.90 has p < 0.001 under the
permutation null; the test cannot miss a cue of the parent's size. It can miss weak cues
(≤ 0.40), which is not the question here.

## Analysis 2. Successors without multiple choice (Q1)

For LABBench2 (and its Inspect register entry), "fixed" requires: (i) no option list in any
released task (checked on all report files, all tags); (ii) SeqQA2 and cloning graded by
computation (`file:line` of the validator dispatch). Reported as a plain result. Post hoc lead,
labelled as such: per-type constant-answer baselines in SeqQA2 (most common expected output per
type), from the report files' `expected_output`, and how often models answer that constant.

## Analysis 3. Human line in successors (Q2)

For each document: which human number is used, and whether unsure answers are credited. Read
from text; numbers read from figures are labelled "read from a figure". Recompute, for SeqQA, the
paper's mean-of-subtask human accuracy under unsure = wrong (0.789) and under chance credit, and
compare with each document's line.

## Analysis 4. Exposure bounds (Q3)

For every published SeqQA score s compared with a human line: item set n, weighting and share w
of cue-bearing items, from the document. If unstated, assume the 600 public items, 40 per subtask,
so per-item and per-subtask weighting coincide and w = 240/600 = 0.40; say it is an assumption.
- Reading A (cue subtasks all correct): accuracy on the non-cue part = (s − w)/(1 − w).
- Reading B (cue subtasks at the same accuracy as the rest): = s.
- Compare both with the paper's human accuracy on the 9 non-cue subtasks (0.760, mean of
  subtasks, unsure = wrong) and with the human line the document used.
Labelled as bounds, not evidence of cue use. Overall LAB-Bench scores without a stated subset mix
are listed but not bounded.

## Analysis 5. Per-item outputs (Q4)

Search list and queries recorded in the inventory. For any per-item outputs found:
- Item mapping: `doc_id` → HF item order of the matching revision, checked by a content test
  (share of items where a ≥ 14-character substring of one of that item's options or question
  appears in the output).
- Chosen option "recovered" when the final `ANSWER: X` letter is explicitly bound in the output
  to exactly one option (pattern `X)`, `(X)`, `X.`, `X:` or `Option X` followed within 8
  characters by the first 25 characters of that option).
- **Run the item-level analysis only if** ≥ 20 recovered items in S across ≥ 3 S subtasks and ≥ 20
  in F across ≥ 3 F subtasks. Then: accuracy on S vs F (difference, bootstrap over subtasks);
  on wrong S answers, the rate at which the wrong pick is the most central distractor (R2) vs
  1/(k−1); matched placebo: the same on F items. Otherwise report the recoverable counts and stop.
