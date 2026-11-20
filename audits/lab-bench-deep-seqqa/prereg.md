# LAB-Bench SeqQA deep dive: pre-registration

Written 2026-11-20 and committed before any model output on a cue-bearing SeqQA subtask. Already
done at this point, and nothing else:
- `scripts/build.py` (arms and key verification, no inference; `build_check.json`);
- `scripts/power.py` (simulation, `power.json`);
- a 4-call cost pilot on three *non-cue* items (3 Sonnet, 1 Haiku; `results/runs_p0_cost.csv`).
  Its outcomes were seen (Sonnet 2 of 3 correct, Haiku 1 of 1). Those items are not in any sample.

## The inherited question

**What the parent established** (`audits/lab-bench`, validated). In 6 of 15 SeqQA subtasks
(GC-percent, ORF-seq-AAseq, PCR-gene-enzprimers, PCR-seq-enzprimers, PCR-gene-gibshindprimers,
PCR-gene-gibssmaprimers) the distractors are small edits of the key, so the option the others
resemble is the key; content-blind rules score 1.00 (L2). Haiku follows that cue on the two Gibson
subtasks (one-option swap 0.935 → 0.726, n = 62; L4 for Haiku) and not measurably elsewhere
(0.04 [−0.05, 0.13]). No per-item outputs of any published model exist; the stratum test on 2024
models had 17% power.

**What it left open.** Does a strong current model answer these subtasks from the structure of the
options rather than by solving the question, and what would its SeqQA accuracy be with honest
distractors? The strongest model available here is Claude Sonnet (`claude-sonnet-5-5`), with
Haiku (`claude-haiku-5-5`) as a second model. **A result is about that model only**; nothing here
is a statement about Opus or any model in a system card.

**Outcomes, per model** (primary contrast K − D, pooled over the six cue subtasks):
- **Yes, it relies on the cue**: K − D ≥ 0.10, its item-level 95% interval excludes 0, and under D
  the new centre is picked more often than the mean of the other distractors.
- **No (R)**: the upper bound of the item-level interval is < 0.10 and K accuracy ≥ 0.70. If
  both K and D are ≥ 0.95 this is reported as "held at ceiling".
- **Still cannot tell**: anything else.
The same rules are applied, as pre-registered secondary tests, to two strata fixed now: *gene
absent* (PCR-gene-enzprimers and both Gibson subtasks: the gene sequence is not in the question,
so without tools the model can only recall the gene or use the options) and *gene present*
(GC-percent, AAseq, PCR-seq-enzprimers: the answer can be computed from the question).

## Arms (paired per item; `scripts/build.py`)

| Arm | What changes | What it shows |
|---|---|---|
| O | original item | baseline |
| N | question withheld, neutral instruction ("one of them is the correct answer to a question that is hidden from you"), same options and order, forced | whether the model *can* read the cue |
| D | question and key unchanged; distractors rebuilt by the benchmark's own kind of edit around a wrong option, so a distractor is the centre | whether it *relies* on the cue when the question is present |
| K | the same rebuild around the key (the key stays the centre) | control for the rebuild itself |
| I | GC-percent only: independent wrong answers from other error processes | accuracy with honest distractors |

Constructions (from the docstring of `build.py`):
- **GC-percent.** O is {x, x+1, x−1, x/2} (the benchmark's generator; 40/40). D = {x, x+s, x+2s,
  round((x+s)/2)}, s = ±1 by hash: two options replaced in place, centre x+s. K: the generator
  applied around the key reproduces O exactly, so **K = O** for this subtask (no separate call).
  I = {x, AT%, purine %, keto %, …}: the first three distinct rounded values from AT%, (A+G)%,
  (G+T)%, GC% of the first half, (C+T)%, (A+C)%, GC% of the first third, GC% of the last quarter,
  skipping any value that would make x the middle of a symmetric pair; available for 31 of 40 items.
- **AAseq.** O = {P, three 1-residue substitutions of P, a DNA string}. D = {P, V, V′, V″, DNA}:
  V one original substitution (by hash), V′ V″ new 1-residue substitutions of V (two options
  replaced in place). K = {P, V, P′, P″, DNA}: P′ P″ new 1-residue substitutions of P. D's new
  options differ from P at 2 residues and K's at 1, so a model that translates finds D *easier*;
  a drop is conservative.
- **Four PCR subtasks.** O = {K, S (key site/overlap + shifted body), G (key site + other gene),
  W (wrong site + key body)}. Only W is replaced. D: W → W′ + S's body. K: W → W′ + K's body. W′
  is one new wrong site, the same string in D and K: a different MCS enzyme pair (restriction
  subtasks) or the pUC19 junction at XbaI or BamHI (Gibson subtasks; the MCS region was
  reconstructed from the keys' own HincII and SmaI overlaps, and both are reproduced exactly). So
  **D and K differ in one option, and only in the body that option carries.**

**Verification** (an item enters the D/K pair only if all pass; `build_check.json`):
- GC: key = GC% rounded (40/40).
- AAseq: key = translation of the unique longest forward-strand ORF (38/40; 2 ties dropped).
- PCR: key sites equal the named enzymes' sites or the named junction (160/160); PCR-seq-enzprimers
  key bodies equal the gene's 5′ prefix and 3′ suffix (40/40).
- Every rebuilt distractor is wrong by construction: a wrong site or junction (PCR), not the
  translation (AAseq), ≠ x (GC). S and G are the benchmark's own distractors and are checked to
  have bodies that do not start where the key's do.
- Centre check: in D a distractor and in K the key is the centre under both the parent's 3-gram
  centroid and a summed-Levenshtein medoid (numbers: the parent's num_center only, since the
  medoid ties on GC O).
- Kept: 40 / 38 / 33 / 37 / 36 / 29 (GC, AAseq, gene-enz, seq-enz, gibshind, gibssma). Items that
  fail the centre check are dropped from the pair and reported; they could differ from kept items.

Two findings from the verification, recorded before any outcome (L1, reported in the README):
- In both restriction subtasks the key's reverse primer is the gene's 3′ end in **sense**
  orientation, not reverse-complemented (40/40 PCR-seq-enzprimers keys match the gene's suffix;
  0/40 its reverse complement). All options follow this convention, so it does not change which
  option is keyed, but no option is a working reverse primer.
- In ORF-seq-AAseq the key is the longest *forward-strand* ORF; the reverse strand has a longer
  ORF in 21 of 40 items. The question does not say "forward strand".

## Prompt and elicitation

- FutureHouse zero-shot template as the parent rendered it, with "Think step by step" removed and
  "Respond with only the tagged letter and nothing else" added (cost). The benchmark's refusal
  option "Insufficient information to answer the question." is inserted at a hashed position in
  O, D, K and I (as both harnesses do). N is forced, with no refusal option.
- No tools. The CLI runs both models with their default extended thinking; the thinking is not
  returned, so only the final letter is read. This is closer to the system cards' "extended
  thinking" condition than to a no-reasoning run, but it is not their 10-shot setup.
- Option order: one hash permutation per item, identical across arms (a replaced option keeps its
  slot), so the key has the same letter in every arm.
- Parsing: `[ANSWER]X[/ANSWER]`, else `ANSWER: X`, else a bare letter; anything else is
  "unparsed". Buckets correct / wrong / refuse / unparsed / error are kept apart.

## Samples and budget (`scripts/plans.py`, seed 0)

Cost pilot: Sonnet 0.015–0.020 USD per call (thinking 665–1,130 tokens), Haiku 0.0013. The 3 USD
cap allows about 130 Sonnet calls, so the Sonnet design drops O on five subtasks (K is its
reference; on GC K = O) and runs N on few items.

| Batch | Model | Items | Arms | Calls |
|---|---|---|---|---|
| b1 pilot | Sonnet | 2 per cue subtask | K, D (+ I on GC) | 26 |
| b2 main | Sonnet | GC 6, AAseq 6, seq-enz 6, gene-enz 10, gibshind 10, gibssma 10 (48 pairs incl. pilot) | K, D (+ I on GC) | 76 |
| b3 | Sonnet | 3 per cue subtask | N | 18 |
| b4 | Haiku | 15 per cue subtask (90 pairs; contains the Sonnet items) | K, D (+ I on GC) | 195 |
| b5 | Haiku | 8 per cue subtask; 6 per non-cue subtask | O (cue, not GC), N (cue), O and N (non-cue) | 196 |
| b6 | Sonnet | 2 per non-cue subtask | O | 18 |

Batches run in this order. The cap may cut the last batch; whatever completes is reported.
**Pilot rules** (b1 is part of the main sample):
- If the mean Sonnet cost per call in b1 is > 0.022 USD, gene-enz and both Gibson drop from 10
  to 8 items and b6 is not run.
- Floor: if pooled K accuracy in b1 is < 0.5, b2 is not run and the pilot is reported as a lead.
- Ceiling: if K and D are both 1.0 in b1, b2 still runs (bounding the drop needs the full n).

## Power (`power.json`; 2,000 simulations; K = 0.95; 60% of pairs concordant by design)

| Model (pairs) | Test | Uniform drop 0.20 | Haiku's per-subtask pattern (mean 0.18) | Uniform 0.10 | No effect |
|---|---|---|---|---|---|
| Sonnet (48) | item-level "yes" rule | 0.93 | 0.91 | 0.44 | 0.00 |
| | "no" rule (upper < 0.10) | 0.00 | 0.00 | 0.07 | 0.94 |
| | subtask bootstrap excludes 0 | 0.94 | 0.59 | 0.61 | 0.02 |
| | sign-flip over 6 subtasks | 0.27 | 0.00 | 0.04 | 0.00 |
| Haiku (90) | item-level "yes" rule | 1.00 | 0.95 | 0.55 | 0.00 |
| | subtask bootstrap | 1.00 | 0.75 | 0.84 | 0.04 |
| | sign-flip | 0.74 | 0.02 | 0.20 | 0.00 |

**At the subtask level the design cannot reach 80% power** if the effect is concentrated in a few
subtasks as it was for Haiku: six units give a sign-flip minimum p of 0.031, and a percentile
bootstrap over six clusters is itself optimistic. So the item-level test is primary, and
per-subtask exact McNemar tests (two-sided, Holm over six) are reported beside a subtask-level
bootstrap. A generalisation "across subtasks" needs the subtask-level interval, not the item one.

## Statistics

- Paired differences K − D (primary), O − D and O − K (Haiku, rebuild check), I − D (GC).
  Item-level paired bootstrap, 2,000 replicates, seed 0; subtask-cluster bootstrap over the six
  subtasks; per-subtask McNemar exact with Holm.
- Pick rates under D: the new centre (`D_centre`) against the mean of the other distractors.
- **Abstention.** Refusal, unparsed and error rates per arm. If the refusal rate differs between K
  and D by ≥ 0.10, the accuracy contrast is flagged as not clean, and the contrast among answered
  items and the rate of picking a wrong substantive option are reported beside it.
- **N.** "Can read the cue": accuracy on cue subtasks ≥ 0.60 with the Wilson lower bound above
  chance. Interpretation: N high and D drop → reads and relies; N high and no drop → can read but
  does not depend on it; N low and no drop → does not read it.
- **Cue vs non-cue stratum (Haiku, O and N).** Statistic: mean accuracy over the six cue subtasks
  minus mean over the nine non-cue subtasks. Placebo: 1,000 random splits with matched sizes and
  answer types (4 of the 6 primer-pair subtasks and 2 of the 9 others, as in the parent), built
  without the key; report the percentile. For Sonnet, N on cue subtasks against chance only.
- **Cue-free SeqQA score**, per model, as the benchmark weights it (mean of the 15 subtasks; each
  has 40 public items): non-cue subtasks at O accuracy; cue subtasks at D accuracy ("cue against")
  and at K/O accuracy ("cue for"), and GC-percent also at I accuracy ("honest"). The honest score
  is bracketed by the two only if accuracy is monotone in the cue's direction, which is an
  assumption. Intervals: bootstrap of items within subtask (the subtask set is fixed). Also the
  shift (6/15)·(K − D), which needs no non-cue data. Set beside the paper's human SeqQA mean 0.79
  with the parent's claim-7 caveats (sure-only scoring; plausible forced-choice 0.81–0.85; other
  item sample; the cards' human line and weighting are unpublished). For Sonnet the non-cue part
  rests on b6 (18 items) if it runs; otherwise only the shift is reported.
- At least 30 raw outputs across arms are read by hand before the parser is trusted.

## Robustness (chosen to hurt the result)

1. Drop each subtask in turn (pooled K − D).
2. Second centre definition: results split by whether the Levenshtein medoid and the centroid
   agree on the D centre option (S vs G).
3. The gene-absent and gene-present strata separately (pre-registered above).
4. Haiku O versus K (does the rebuild itself change accuracy?).
5. Answered-only accuracy where abstention differs.
6. Count of tests in the README.

## What would not count

- A D drop without a K arm (unpaired or post hoc) is not evidence of reliance.
- A Sonnet result extended to Opus or any published model.
- The cue-free score presented as the published model's score.
