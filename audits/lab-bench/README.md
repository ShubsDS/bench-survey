# LAB-Bench: options alone give the key for 6 of 15 SeqQA subtasks, and Haiku uses that; 2024 models show no sign of it; the "exceeds experts" margins sit inside the slack of the human scoring rule

Status: complete, 2026-11-17, branch `audits-round2`. Not yet independently validated.

**No per-item outputs of any published model exist.** None were found in the paper's repo, the
Hugging Face hub, the Inspect Evals repo, the system cards or third-party re-runs (Data inventory).
So there is no item-level L3. The evidence is:
- content-blind rules (L2);
- a stratum-level test on the paper's per-subtask tables;
- Haiku interventions, which are L4 for Haiku only.

| # | Claim | Level |
|---|---|---|
| 1 | In 6 of the 15 SeqQA subtasks (240 of 600 public items), a rule that reads only the options picks the key on every item. Five fall to "the option the others were derived from" (centroid), and GC-percent falls to "the middle value". On those subtasks the rule beats the human baseline in 5 of 6 and ties it once. Held out over all of SeqQA: 0.58 [0.55, 0.61] against chance 0.25 | **L2** |
| 2 | Haiku uses this shortcut. Rebuilding the distractors so that a *distractor* becomes the centroid, with key and question unchanged, cuts Haiku's accuracy from 0.93 to 0.74 (−0.18 [0.10, 0.27], n = 147). The new central distractor is picked 22% of the time, against 2% for each other distractor. On the two Gibson subtasks: 0.96 → 0.50. A post hoc control rebuilt the same way but centred on the key gives 0.88 | **L4** (Haiku) |
| 3 | The paper's 2024 model-versus-human gaps do not track the shortcut. Models are 0.16 closer to humans on the shortcut subtasks than on the others, but random and answer-type-matched subtask splits give as much (79th–86th percentile) | **R** (stratum level) |
| 4 | ProtocolQA without the protocol and without the question: Haiku 0.51 [0.42, 0.61] (chance 0.23), against 0.68 with the full item. 2024 models with the full item scored 0.37–0.53 | **L2**, and L4 for Haiku |
| 5 | FigQA without the figure, forced: Haiku 0.31 [0.25, 0.39] (chance 0.22). That equals or beats 6 of 7 published 2024 *sighted* scores (0.23–0.29; Claude 3.5 Sonnet 0.46). Options alone: 0.23, chance. TableQA without the table: 0.41 [0.32, 0.50] (chance 0.21) | **L2** |
| 6 | The "Insufficient information" option. Without the figure or table, Haiku picks it on 51–58% of items, which costs 0.17–0.19 accuracy. On full text items it costs 0.06 (ProtocolQA, interval includes 0) or nothing (SeqQA, CloningScenarios, LitQA2). SuppQA: 0.16 [0.06, 0.26]. Its position does not matter (−0.006 [−0.04, 0.03]) | **L4** (Haiku); **R** for position |
| 7 | Human accuracy counts an "unsure" answer as wrong even when its best guess was right (App. E.4). The FigQA human number under forced-choice scoring is therefore anywhere in [0.77, 0.83]. Several margins fall inside that range: Opus 4.6's "surpasses expert humans, who scored 77%" (78.3%), Opus 4.8 (80.4%), CloningScenarios 0.61 vs 0.60 (Justen) and 0.758 (Opus 4.5), and SeqQA 0.85 (Opus 4.5). Each of these also has an item-sampling interval that includes the human line. ProtocolQA 0.907 clears both | **L1** (arithmetic on published numbers) |
| 8 | DbQA `variant_multi_sequence`: the centroid rule scores 80/80. Humans scored 0.23 and the best model 0.14, both below chance on that subtask | **L2**, a key anomaly |

## The benchmark and what rests on it

LAB-Bench (Laurent et al. 2024, FutureHouse, arXiv 2407.10362) is a set of multiple-choice items
in 8 categories. Every item gets an extra "Insufficient information to answer the question"
option. Scores are reported as accuracy, precision (correct among answered) and coverage. A
PhD-level human baseline is given per subset and subtask (Tables 2–4).

Published conclusions under test (exact wording and pins in [`claims.md`](claims.md)):
- **C1.** The paper: "human experts greatly outperformed models in both accuracy and precision"
  (§2.3).
- **C2.** Anthropic's RSP use. The threshold is "at or above human level across all four tasks"
  (FigQA, ProtocolQA, SeqQA, CloningScenarios). The Claude 3.7 Sonnet card calls the benchmark
  "saturated for the purposes of ASL determination". Opus 4.5 scores ProtocolQA 0.907, Cloning
  0.758, SeqQA 0.8517 and FigQA 0.6924; "every evaluation except FigQA exceeded the human
  baseline".
- **C3.** Opus 4.6 card §2.19.1: FigQA 58.0% without tools, 78.3% with a crop tool. "Notably, Opus
  4.6 now surpasses expert humans, who scored 77%."
- **C4.** Justen 2025: models "match or exceed expert-level performance" on CloningScenarios (61%
  vs 60%).

## What we found

**SeqQA has a construction shortcut. The current small model uses it; the 2024 models show no
sign of it.**
- The paper's own construction notes (App. C.7) derive most SeqQA distractors from the key:
  - "shifted" primers, "wrong enzyme" pairs that keep the key's primer bodies, and "wrong gene"
    pairs that keep the key's sites;
  - GC% "one less or one greater than the answer, or the ideal answer divided by two";
  - in the release, protein options that are one-residue substitutions of the key.
- So in those subtasks the key is the option every distractor resembles. A 3-gram similarity rule
  that never sees the question finds it on 240 of 240 items.
- Haiku shown only the options scores 0.80 [0.68, 0.88] on these subtasks and 0.32 on the other
  nine (chance 0.25).
- When the distractors are rebuilt around a distractor, Haiku follows the centre on the Gibson
  subtasks (pick rate of the new centre 0.40–0.44) and loses 0.40–0.52 accuracy.
- Where Haiku can actually compute the answer, editing does nothing:
  - protein translation (AAseq, 1.00 → 1.00);
  - primer design with the gene sequence given (PCR-seq-enzprimers, 1.00 → 1.00).
- The 2024 models in the paper do not show the pattern at stratum level. Their accuracy on the
  shortcut subtasks is far below the rule's 1.00 (best 0.59–0.94), and their gap to humans there
  is not unusual against placebo splits.

**What this means for "human level on SeqQA".** The human SeqQA mean over the 15 subtasks is 0.79.
- A model at 1.00 on the six shortcut subtasks reaches that mean with 0.65 on the other nine,
  where humans score 0.76.
- Opus 4.5's 0.8517 is consistent with 0.75 on the shortcut-free nine, if it scored 1.00 on the
  six. That is below the human 0.76.
- This is exploratory arithmetic. Anthropic's SeqQA item set and weighting are not published.

**The visual and protocol subsets.** Without the figure, Haiku forced to answer FigQA reaches
0.31, which is above chance (0.22) and at or above 6 of the 7 sighted 2024 scores. So the
paper's 2024 FigQA comparison ("near-random precision … with the exception of Claude 3.5
Sonnet") partly measures what the question text and options allow without the figure.
- The options alone carry nothing on FigQA (0.23).
- Against Opus 4.6's no-tool 58%, the blind score covers about a quarter of the gain above
  chance. The pre-registered "most of a sighted score" line (0.50) is not reached.
- ProtocolQA is different: with neither the protocol nor the question, Haiku reaches 0.51. It
  picks the longest option only 26% of the time, so this is not the known length rule (issue
  #18), and most of Haiku's full-item accuracy (0.68) is reachable without reading the protocol.

**The abstention option.** It changes what a blind score means. With it, blind FigQA accuracy is
0.15, below chance. Without it, 0.31. Items Haiku refused were answered correctly at 0.34 when
forced (chance 0.22). So "low accuracy" there is part refusal and part inability. On full text
items Haiku rarely refuses (0–17%), and abstention barely moves accuracy.

**The human line.** The paper's human accuracy is "correct sure" answers over all questions
(App. E.4). Humans were paid at least the expected value of a guess to flag "unsure", and gave a
best guess that was not scored (App. E.3). A model run in forced-choice mode is compared with a
human number from which human guessing was removed. Several further asymmetries:
- the humans had internet and tools and up to 5–8 days per quiz (App. E.2);
- they were drawn from the same group that wrote the questions (App. E);
- they covered only part of SeqQA (64%) and TableQA (82%);
- the number of evaluators is not reported.
These run in opposite directions: tools favour humans, the unsure rule favours models. No one
number fixes them.

## Numbers

### Content-blind rules (`results/surface.json`; ties fractional; chance = 1/k without the refusal option)

| Subset or subtask | n | Chance | Best rule (held out) | 95% CI (cluster) | Human (paper) | Best 2024 model (paper) |
|---|---|---|---|---|---|---|
| SeqQA, all | 600 | 0.25 | **0.58** | [0.55, 0.61] | 0.79 (mean of subtasks) | 0.52 (Claude 3.5 Sonnet) |
| ORF-seq-AAseq | 40 | 0.20 | **1.00** centroid | — | 0.88 | 0.87 |
| PCR-gene-enzprimers | 40 | 0.25 | **1.00** centroid | — | 0.83 | 0.75 |
| PCR-seq-enzprimers | 40 | 0.25 | **1.00** centroid | — | 0.81 | 0.94 |
| PCR-gene-gibshindprimers | 40 | 0.25 | **1.00** centroid | — | 0.71 | 0.64 |
| PCR-gene-gibssmaprimers | 40 | 0.25 | **1.00** centroid | — | 0.73 | 0.65 |
| Prop-seq-gcpercent | 40 | 0.25 | **1.00** middle value | — | 1.00 | 0.59 |
| ORF-seq-numlen | 40 | 0.25 | 0.39 middle value (partly tuned) | p = 0.002 | 0.31 | 0.26 |
| other 8 SeqQA subtasks | 320 | 0.25 | 0.23–0.35, none p < 0.05 | | | |
| DbQA variant_multi_sequence | 80 | 0.25 | **1.00** centroid | — | 0.23 | 0.14 |
| DbQA dga / viral_ppi / vax_response | 40 each | 0.25 | 0.50 / 0.45 / 0.41 shortest | p ≤ 0.03 | 0.67 / 0.90 / 0.91 | 0.25 / 0.40 / 0.33 |
| DbQA dga, cross-item (distractor reuse) | 40 | 0.25 | 0.875 (dataset-level, not single-item) | | | |
| FigQA | 181 (107 figures) | 0.22 | 0.27 | [0.21, 0.32], p = 0.07 | 0.77 | 0.46 |
| TableQA | 244 | 0.21 | 0.26 centroid | [0.22, 0.30], p = 0.011 | 0.84 | 0.83 |
| ProtocolQA | 108 (24 protocols) | 0.23 | 0.21 held out; longest 0.33 (known, issue #18) | [0.15, 0.30] | 0.79 | 0.53 |
| CloningScenarios | 33 (9 scenarios) | 0.23 | 0.22 | [0.12, 0.30] | 0.60 | 0.28 |
| LitQA2 / SuppQA | 199 / 82 | 0.24 / 0.21 | 0.21 / 0.20 | | 0.70 / 0.85 | |

- Human and model columns are the paper's full-set accuracies (public plus private, Table 2).
- The rule columns are on the public items.
- p values come from 1,000 shuffles of the key position within items, with the held-out selection
  repeated each time.

### Haiku (claude-haiku-5-5; `results/haiku_analysis.json`)

| Condition | Subset | n | Accuracy [Wilson 95%] | Chance | Refusal rate |
|---|---|---|---|---|---|
| full, forced | SeqQA (237: edited items + 10 per other subtask) | 237 | 0.89 | 0.25 | — |
| full, forced, edited distractors | SeqQA S subtasks | 147 | 0.74 (from 0.93 on the same items) | 0.24 | — |
| key-centred placebo edit (post hoc) | Gibson subtasks | 50 | 0.88 (forced 0.96, edit 0.50) | 0.25 | — |
| options only | SeqQA S / F | 60 / 90 | **0.80** [0.68, 0.88] / 0.32 [0.23, 0.42] | 0.24 / 0.25 | — |
| options only | ProtocolQA | 107 | **0.51** [0.42, 0.61] | 0.23 | — |
| full, forced / std | ProtocolQA | 107 | 0.68 [0.59, 0.76] / 0.63 (precision 0.75, coverage 0.83) | 0.23 | 0.17 |
| options only | CloningScenarios | 33 | 0.33 [0.20, 0.50] | 0.23 | — |
| full, forced / std | CloningScenarios | 33 | 0.70 [0.53, 0.83] / 0.64 | 0.23 | 0.03 |
| no figure, forced / std | FigQA | 181 | **0.31** [0.25, 0.39] / 0.15 [0.10, 0.21] | 0.22 | 0.51 |
| no figure, refusal option last | FigQA | 181 | 0.14 | 0.22 | 0.51 |
| options only | FigQA | 181 | 0.23 [0.18, 0.30] | 0.22 | — |
| no table, forced / std | TableQA | 120 | **0.41** [0.32, 0.50] / 0.22 | 0.21 | 0.58 |
| options only | TableQA | 120 | 0.28 [0.21, 0.37] | 0.21 | — |
| full, forced / std (closed book, the published setting) | LitQA2 | 58 | 0.41 / 0.45 | 0.23 | 0.05 |
| full, forced / std (title and DOI only) | SuppQA | 50 | 0.48 / 0.32 | 0.22 | 0.20 |
| full, std | SeqQA (5 per subtask) | 75 | 0.87 (forced 0.88) | 0.25 | 0.01 |
| options only | LitQA2 / SuppQA / DbQA | 58 / 50 / 60 | 0.23 / 0.24 / 0.35 | 0.24 / 0.21 / 0.25 | — |

Cluster-bootstrap intervals are in the JSON. Design effects are 0.9–1.1 on FigQA (figures
cluster weakly), and 1.4–2.0 on ProtocolQA and CloningScenarios in some conditions.

### The human line against the claims (`results/human_baseline.json`)

| Claim | Model score | Item interval (Wilson; cluster-adjusted) | Human accuracy / precision | Human under forced-choice scoring, range | Survives? |
|---|---|---|---|---|---|
| Opus 4.6 FigQA, crop tool: "surpasses expert humans" | 0.783 | [0.72, 0.84]; [0.71, 0.84] | 0.77 / 0.82 | [0.77, 0.83] | **no**: inside both the human range and its own interval |
| Opus 4.8 FigQA, no tools | 0.804 | [0.74, 0.86] | 0.77 / 0.82 | [0.77, 0.83] | inside the range |
| Opus 4.5 ProtocolQA | 0.907 | [0.84, 0.95] | 0.79 / 0.87 | [0.79, 0.88] | yes, narrowly |
| Opus 4.5 CloningScenarios | 0.758 | [0.59, 0.87]; [0.51, 0.89] | 0.60 / 0.73 | [0.60, 0.78] | **no** |
| Justen: Claude 3.7 / o3 CloningScenarios | 0.61 | [0.44, 0.76]; [0.37, 0.79] | 0.60 / 0.73 | [0.60, 0.78] | **no** |
| Opus 4.5 SeqQA | 0.8517 | [0.82, 0.88] | 0.79 / 0.84 | [0.79, 0.87] | inside the range; see the SeqQA arithmetic |

- Item counts are assumed to be the public set (181, 108, 33, 600). Opus 4.8 states 181; the other
  cards do not state theirs.
- Model scores are run means. The intervals cover item sampling only. Run-to-run variation is not
  in them.
- The human number has its own sampling error, which is unknown because the number of human
  answers per item is not published.

## The confound

- **Feature.** The centroid: for each option, the mean character-3-gram Jaccard similarity to the
  other options, picking the maximum. Middle value: the numeric option with the most symmetric
  pairs (x − d, x + d) among the others.
- **Where it comes from.** These are the generators described in App. C.7.1–C.7.5, C.7.12 and
  C.7.15. In the release:
  - ORF-seq-AAseq distractors are single-residue substitutions of the key plus the DNA sequence.
    This differs from the paper's "shortened by two AA … random AA sequence of correct length".
  - Prop-seq-gcpercent distractors are exactly key − 1, key + 1 and key/2.
- **Example ids** (text not reproduced, per the paper's request):
  - GC-percent `88ec8b3d-1f94-4338-b381-ce68db14485e`;
  - the AAseq, PCR and Gibson ids are in `results/surface_items.csv`, rows with `centroid = 1.0`.
- **Second, independent feature.** Cross-item reuse of distractors (DbQA). It is weaker and
  dataset-level.
- **Hand reading.** About 60 items across all subsets (two per SeqQA and DbQA subtask, six each
  from the manual subsets) before any rule was computed. Manual subsets show the same habit in
  places, where the key is a hub of edited variants (SuppQA sgRNA sequences, ProtocolQA "step N,
  5 min" options), but no rule captures it. Their held-out rule scores are at chance.

## The effect

**L4 on Haiku** (prereg Analysis B; pre-registered verdict "uses the shortcut": pooled drop ≥
0.10, interval excluding 0, central distractor picked more than the others: met).

| Subtask (n) | forced | edited | drop [95% CI; Bonferroni ×6] | picks of new centre |
|---|---|---|---|---|
| PCR-gene-gibshindprimers (25) | 0.96 | 0.44 | **0.52** [0.32, 0.72; 0.28, 0.80] | 0.40 |
| PCR-gene-gibssmaprimers (25) | 0.96 | 0.56 | **0.40** [0.20, 0.60; 0.16, 0.68] | 0.44 |
| Prop-seq-gcpercent (25) | 0.84 | 0.72 | 0.12 [−0.12, 0.36] | 0.24 |
| PCR-gene-enzprimers (22) | 0.77 | 0.73 | 0.05 [−0.23, 0.32] | 0.23 |
| ORF-seq-AAseq (25) | 1.00 | 1.00 | 0.00 | 0.00 |
| PCR-seq-enzprimers (25) | 1.00 | 1.00 | 0.00 | 0.00 |
| **Pooled (147)** | 0.93 | 0.74 | **0.18** [0.10, 0.27] | 0.22 vs 0.02 per other distractor |

- The central distractor in the Gibson edits is the *same string* as the original "shifted"
  distractor. Haiku rejected it on 96% of items in the original set, and picks it on 40–44% once
  the other options are built around it.
- The post hoc key-centred placebo, built with the same procedure, costs 0.08 [−0.04, 0.18].
  The real edit costs 0.46 on the same 50 items. So new or odd-looking distractors do not
  explain the drop.

**Stratum level on published models** (prereg Analysis A; `results/stratum.json`). D is the
model-minus-human gap on S minus the gap on F, averaged over 7 models.

| | Observed mean D | All 5,005 splits (95%) | Answer-type-matched 540 splits (95%) | Verdict |
|---|---|---|---|---|
| Accuracy | +0.16 | [−0.28, 0.28], 86th percentile | [−0.17, 0.31], 79th | holds (R) |
| Precision | +0.22 | [−0.25, 0.24], 96th | [−0.11, 0.32], 90th | holds (R) |
| Accuracy, numlen moved into S | +0.21 | 93rd | 89th | holds (R) |

Every 2024 model is nearer the human on S (−0.12 to −0.47) than on F (−0.38 to −0.53). The
direction fits mild shortcut use, but a random split of 15 subtasks produces differences this
large. With only 15 subtasks this test has little power. It cannot rule out use by the 2024
models; it shows that no evidence for it exists in the published tables.

## Robustness

| Check | Result | Claim survives? |
|---|---|---|
| Rules chosen on one half of the clusters and scored on the other | SeqQA S subtasks 1.00 on both halves | yes |
| Permutation null (1,000 key shuffles within items) | p = 0.001 for all six S subtasks | yes |
| Second rule (middle value, numeric) | Gives 1.00 on gcpercent and does not apply to the sequence subtasks | yes, for gcpercent |
| Bonferroni over the 6 L4 subtasks | Both Gibson subtasks stay significant; the others do not | pooled yes; per subtask only Gibson |
| Key-centred placebo edit (post hoc) | 0.08 drop against 0.46 | yes |
| Analysis A: matched placebo, precision, numlen in S | All "holds" | R stands |
| Refusal option moved to last | No change in refusal (−0.006 [−0.04, 0.03]) | position: R |
| Comparisons counted | 31 rule families, 6 L4 subtasks, 3 stratum analyses, about 25 Haiku cells. The headline L4 pooled test is one pre-registered test | yes |
| Prereg check "edited items typical of their families" | Not possible: the plan drew the S-subtask forced items only from the edited set | not run (prereg item 6) |

## Alternative explanations

1. **"The shortcut is the construct: a biologist would also pick the primer pair that looks like
   the others."**
   - Partly true for PCR design, where the right answer is near the alternatives.
   - But Haiku shown only the options gets 0.80, and with the centre moved it picks a primer pair
     whose frame is wrong. Answering from resemblance is not primer design.
   - The rule scores 1.00 against the humans' 0.71–0.83 on the PCR subtasks, so the shortcut is
     not what experts do.
2. **"The edited items are just harder."**
   - The key-centred placebo, built with the same procedure, costs only 0.08.
   - The two subtasks where Haiku can compute the answer (AAseq, PCR-seq-enzprimers) lose
     nothing.
3. **"Blind FigQA accuracy reflects prior knowledge of the papers, not a flaw."**
   - Possible: the figures come from open-access papers, and Haiku may know some results. Either
     way, 31% of FigQA is answerable without the figure by a model the benchmark did not exist
     for.
   - It does not show that FigQA fails to measure figure reading for models scoring 58–80%.
4. **"The human scoring rule is standard selective accuracy."**
   - It is, and the paper defines it clearly.
   - The issue is only that the system cards compare forced-choice model accuracy with it,
     without noting the slack.

## What was already known

See [`prior_work.md`](prior_work.md). Already public:
- the "longest option" rule on all non-programmatic subsets ([issue #18](https://github.com/Future-House/LAB-Bench/issues/18), two days before this audit);
- the paper's warnings about distractor elimination, the low CloningScenarios human baseline and
  tool asymmetry;
- the SeqQA generator descriptions themselves.

**New here:**
- the centroid and middle-value rules that solve 6 SeqQA subtasks and one DbQA subtask outright;
- the L4 demonstration that Haiku follows the centroid;
- the stratum-level null for the 2024 models;
- the options-only ProtocolQA result and the figure-free FigQA and TableQA baselines;
- the abstention measurements;
- the forced-choice range of the human line set against the system-card margins.

## What this does not show

- That any published model (Claude 3.5 Sonnet through Opus 4.8, o3, GPT-5) uses the centroid
  shortcut. No per-item outputs exist. The only causal test is on Haiku 5.5, and the 2024 tables
  show nothing beyond placebo.
- That Opus 4.6 or 4.8 do not read figures. Their 58–80% is far above Haiku's 31% blind.
- That models are below experts. Claim 7 says the human line under forced-choice scoring lies
  in a range and the margins are inside it. It does not say on which side the true comparison
  falls. The tool asymmetry pushes the other way.
- Anything about the private 20%. The paper reports public and private means "within five
  percent" (App. B.1).
- Contamination. All public items carry the canary. Two byte-identical mirrors exist on Hugging
  Face with the canary (`introvoyz041/lab-bench` @ `d1c75e7b`, `Maxue627/SCILLM-benchmarks` @
  `f0c85f99`). One 80-item rendered copy has no canary (`Genteki/lab_bench_tiny` @ `099a4bd8`).
  Web search for item ids found nothing. No test of memorisation was run.
- Hazard content. LAB-Bench is general biology. Screening is described under Pins.

## Data inventory

- **Items.** HF `futurehouse/lab-bench` @ `5c77cec6…`, 1,967 public items. The private 20% is not
  available. Parquet sha256s are in `scripts/common.py`.
- **Per-item published model outputs: none.**
  - The FutureHouse harness writes them to a local path (`scripts/run_baselines.sh`, `~/labbench-data/`) but releases none.
  - Inspect Evals releases code only. The HF search ("lab-bench", "labbench", "lab_bench") found
    mirrors and LABBench2, but no logs. `bks-lab/lab-bench-results` is an unrelated project with
    the same name.
  - System cards, Justen 2025 and Concordia AI give aggregates only.
- **Distractor construction, by subset** (paper sections):
  - SeqQA and DbQA: programmatic (§2.1, App. C.7, C.8).
  - LitQA2: expert-written, "reasonable within the context", "periodically tested … with ChatGPT
    3.5 or 4" (C.1).
  - FigQA and TableQA: expert-written from GPT-4 Turbo or GPT-4o draft seeds (C.3, C.4).
  - ProtocolQA: experts introduce errors, then others write questions (C.5).
  - CloningScenarios: author-written (C.6).
- **Human baseline** (§2.3, §3.2–3.5, App. E):
  - PhD-level contractors from the question-writing pool, never shown their own items;
  - quizzes of 20–140 questions, 5–8 days each, with web, code and DNA software allowed and AI
    tools asked against but not enforced;
  - an "unsure" flag with a best guess, paid at least the expected value of guessing;
  - coverage 100% of items for most subsets, 64% for SeqQA, 82% for TableQA, 35% for DbQA;
  - the number of evaluators is not stated.
- **Scorer routes.** FutureHouse `labbench/evaluator.py:86-87` @ `998a8e0` counts an unparsed
  answer as attempted and wrong (`sure = agent_output != unsure`). Inspect `scorer.py:54` @
  `c85fde6` does the same. A refusal lowers coverage, not precision. Both harnesses shuffle all
  options including the refusal option (`labbench/utils.py:140-146`; Inspect `shuffle_choices`,
  seeded since 2026-10-09). Haiku produced 1 unparsed answer in about 2,600 billed calls.

## Pins and how to reproduce

- **Paper and harnesses.**
  - Paper arXiv 2407.10362 v3 PDF sha256 `7c781a703287616d6561e0ce50aed494946c7609a5a1b5985fb7849ce9e884dd`.
  - FutureHouse harness `998a8e0a40cf116c80e1b0e7a805ebb5fb9fa838`.
  - Inspect `c85fde6231f43f9268e48754c3ac60b65bd4305a`.
- **System card PDF sha256s.**
  - Claude 3.7 Sonnet `82947a46fc2d1b9a1d69501ef973fc3c5b328b703b9a17bd8a143c2672f8a1a6`.
  - Opus 4.5 `33be92efcb58f901d9d2c17e61bf277afbd514a1ac70a642f21e918c21ca25a8`.
  - Opus 4.6 `f19fb7cbe57bcc7493278fb97211a6c08e16e82fbfa56e22bfd911a6c53aefd6`.
  - Opus 4.8 `0df5d061b6688c2d5839476620d66960011cb69043185dbed87ed1f68ab76d8f`.
- **Content screen** (`scripts/screen.py`). 25 keyword hits, each hand-read.
  - 16 excluded: 3 LitQA2 SARS-CoV-2 spike and antibody items, and 13 DbQA orthopoxvirus
    host-interaction lookups.
  - 9 kept: "Tricine" and "endotoxin" false hits, and H5N1 vaccine gene sets.
  - Separately, 3 items were refused by the API's usage-policy classifier (ProtocolQA
    `bee8b322`, LitQA2 `82de3e92` and `d2860d38`). They were not retried and are dropped from
    every condition.
- **Inference.** claude-haiku-5-5 through `audits/tools/claude_call.py`: 2,582 billed calls,
  **2.41 USD** ([`inference/ledger.jsonl`](inference/ledger.jsonl)). Responses are cached, so
  reruns cost nothing.

```bash
cd audits/lab-bench && uv venv data/.venv && VIRTUAL_ENV=data/.venv uv pip install numpy pandas pyarrow scipy scikit-learn
hf download futurehouse/lab-bench --repo-type dataset --revision 5c77cec648430f30611808808861eb86f81d5eaa --local-dir data/hf
# paper: curl -L -o data/paper/2407.10362v3.pdf https://arxiv.org/pdf/2407.10362v3 && pdftotext -layout ... data/paper/v3.txt
P="data/.venv/bin/python -I"
$P scripts/surface.py         # content-blind rules           -> results/surface.json, surface_items.csv
$P scripts/screen.py          # content screen                -> results/screen.json
$P scripts/published.py       # paper Tables 2-4              -> results/published.json
$P scripts/stratum.py         # Analysis A                    -> results/stratum.json
$P scripts/edits.py           # L4 edits                      -> data/edits.json, results/edits_check.json
$P scripts/plans.py           # item samples                  -> plans/*.json
for b in pilot b1_l4 b2_blind b3_protclone b4_opts b5b_seqstd5 b6b_litsupp b7_placebo_edit; do
  $P scripts/haiku.py --plan plans/$b.json --out results/haiku_$b.csv; done   # cached
$P scripts/analyze.py         # Analyses B-D                  -> results/haiku_analysis.json
$P scripts/human_baseline.py  # Analysis E                    -> results/human_baseline.json
$P scripts/collect.py         # every number                  -> results.json
```

- Seeds are 0 throughout. Option orders are a hash of the item id.
- `plans/b5_seqstd.json` and `plans/b6_lit.json` were cut to `b5b` and `b6b` when batch 1 cost
  more than estimated. DbQA std and forced runs were dropped.
- The key-centred placebo (`b7`) was added after the L4 result and is labelled post hoc.
- The pilot is `results/haiku_pilot.csv`. Its responses are reused from the cache where prompts
  coincide.
