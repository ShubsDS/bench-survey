# LAB-Bench successors: every multiple-choice release of SeqQA carries the options-only key, and so does every port that loads one. LABBench2 removed it by going free-response. The cards keep the "unsure = wrong" human line, and US AISI is the exception. Under the worst-case reading, most "at or above human" SeqQA statements up to Opus 4.5 sit below the human score on the cue-free subtasks.

Status: complete, 2026-11-20, branch `audits-round3`. Deep dive on [`../lab-bench/`](../lab-bench/)
(validated). No model inference (0 calls, 0 USD). Pre-registration: [`prereg.md`](prereg.md), committed
in `31a7d9a` before any successor outcome. Inventory with pins: [`inventory.md`](inventory.md).

| # | Claim | Level |
|---|---|---|
| 1 | All six HF releases of LAB-Bench SeqQA (2024-07-16 → 2025-09-27) carry the cue on 6 of 6 S subtasks (parent's rule 0.996–1.000, independent edit-distance rule 0.9125–0.9167). The three 2024 releases also carry it on RE-seq-numfrags (40/40 by both rules), which makes 7 of 15 subtasks. DbQA multi-sequence is 80/80 in all six. The Inspect Evals port and both full mirrors load the `5c77cec6` files byte for byte. No distractor generator is released anywhere, so the flaw is shown in the items only | **L2** |
| 2 | LABBench2 (Edison Scientific, 2026) fixed it by design. It has no options: 0 of 23,721 published report cases carry an option list. SeqQA2 and cloning are graded by validators that compute the answer. The HuggingFaceBio curated SeqQA subset fixed it by dropping the cue subtasks, after its own options-only test | result (**L1**: items and grader code) |
| 3 | The human line: Anthropic cards (SeqQA 0.79), Concordia (79) and xAI (0.79 / 0.77 / 0.60) use the paper's unsure-as-wrong number. US/UK AISI (2024) credited unsure answers at chance. LABBench2 has no human baseline. With chance credit the SeqQA human mean is 0.809. Opus 4 (≈0.79, read from a figure) and Sonnet 4.5 (0.780) are below that, and their "reaches/reached or exceeded" statements hold only under unsure = wrong (Sonnet 4.5's 0.780 is below even 0.79) | **L1** |
| 4 | Exposure bounds, assuming the 600 public items with 40 per subtask and cue share w = 0.40 (0.467 for 2024 runs). If every cue item was answered correctly, the score on the cue-free part is below the human 0.764 for Opus 4 (0.65), Sonnet 4.5 (0.63), Opus 4.5 (0.753) and US AISI's Sonnet 3.5 new (0.738 vs 0.771). It is just above for Gemini 3 Pro (0.783) and GPT-5.4 (0.792). It clears for GPT-5.5 (0.858), GPT 6 Astra (0.912) and Meta's tool runs (0.895–0.955). Under the same-accuracy reading every claimant is above human. These are bounds, not evidence of cue use | **L1** (arithmetic) |
| 5 | Per-item outputs: strong-model per-item outputs exist only for LABBench2, which has no cue. DeepSeek-R1 per-item chains on all 600 SeqQA items exist, but the chosen option can be recovered on only 26 S items in 2 S subtasks. That misses the pre-registered gate, so there is no item-level L3 | not analysable |
| L | Leads (post hoc): (a) LABBench2 SeqQA2 `mutation_restriction`: the key is "None" on 17/20 items, so the constant "None" would score 0.85, equal to the best published run (Gemini 3 Pro, 0.85). (b) Claude Opus 4.5 and 4.6 refused 40–136 of their SeqQA2 items, every refusal scored 0. (c) On RE-seq-numfrags, cue-bearing in the 2024 release, the paper's 2024 models had precision 0.11–0.28 (chance 0.25) | L1 |

## The benchmark and what rests on it

The parent showed that in LAB-Bench SeqQA the key is the option the others were built from, on 6 of 15
subtasks (240/600 public items). This happens because the generators derive distractors from the
key. "At or above human level" on SeqQA is one of four conditions in Anthropic's RSP rule-out,
which was declared saturated with the Claude 3.7 card. Concordia AI counts models that "exceed
human-expert level" on SeqQA each quarter. US/UK AISI wrote that Sonnet 3.5 (new) was "slightly
better than human experts on SeqQA". This deep dive asks whether the flaw and the human scoring
rule travel to the versions, ports and successors those statements used.

## What we found

**1. The flaw is in every multiple-choice release.** Rules are frozen from the parent: R1 is the
parent's `centroid`/`num_center`, imported by path. R2 is a summed-Levenshtein medoid written here. A
subtask "carries the cue" at ≥ 0.90 with permutation p < 0.01.

| HF revision (date) | S subtasks carrying | R1 on S [subtask bootstrap] | R2 on S | R1 all 15 | Placebo rule, all 15 | F subtasks carrying | DbQA multi-seq R1/R2 |
|---|---|---|---|---|---|---|---|
| `7268767a` (2024-07-16) | 6/6 | 1.000 [1.000, 1.000] | 0.917 [0.750, 1.000] | 0.617 [0.424, 0.800] | 0.242 [0.213, 0.270] | RE-seq-numfrags (1.00/1.00) | 1.00/1.00 |
| `10866fa8` (2024-08-20) | 6/6 | 1.000 (parquet differs from `7268767a`; all rule results identical) | 0.917 | 0.617 | 0.242 | RE-seq-numfrags | 1.00/1.00 |
| `8e6bb002` (2024-12-18) | 6/6 | 1.000 | 0.917 | 0.617 | 0.242 | RE-seq-numfrags | 1.00/1.00 |
| `4709d14f` (2025-02-19) | 6/6 | 0.996 [0.988, 1.000] | 0.9125 [0.746, 1.000] | 0.555 [0.371, 0.727] | 0.243 | none | 1.00/1.00 |
| `8137378e` (2025-07-15) | 6/6 | 0.996 | 0.9125 | 0.555 | 0.243 | none | 1.00/1.00 |
| `5c77cec6` (2025-09-27, parent) | 6/6 | 1.000 [1.000, 1.000] | 0.9125 [0.746, 1.000] | 0.556 [0.370, 0.731] | 0.258 [0.222, 0.295] | none | 1.00/1.00 |

- n = 600 items, 15 subtasks × 40, in every release. Per-subtask numbers, both id-parity halves and
  p values are in `results/versions.json`. Every S subtask has p = 0.001 in every release, and both
  halves are at 1.00 for R1.
- R2 is 0.50 on GC-percent in every release: a tie between the key and key − 1, as the validator
  found. R2's 0.9125 is therefore four subtasks at 1.00, PCR-gene-enzprimers at 0.975 and GC at 0.50.
- **What changed between releases.** Shared item ids never changed key or options. Items were
  replaced, not edited:
  - 2025-02: the five restriction-enzyme subtasks were regenerated (PCR-gene-enzprimers,
    PCR-geneprimers-enz, PCR-seq-enzprimers, RE-seq-lenfrags, RE-seq-numfrags; 200 new ids). The
    README of this revision mentions a restriction-enzyme fix.
  - 2025-09: three PCR enzyme subtasks were regenerated again (120 new ids).
  - The cue survived both regenerations in the PCR subtasks. It disappeared from RE-seq-numfrags
    in 2025-02 (R1 1.00 → 0.25).
  - So runs on the 2024 releases (the paper's own tables, US/UK AISI 2024) faced 7 cue subtasks;
    later runs faced 6.
- **Ports and copies.**
  - Inspect Evals `lab_bench` pins `5c77cec6` (`lab_bench.py:34`, parent's copy at `c85fde62`).
  - `introvoyz041/lab-bench` and `Maxue627/SCILLM-benchmarks` are byte-identical to it (SeqQA
    sha `5864776d…`).
  - `Genteki/lab_bench_tiny` renders 10 SeqQA items from the Inspect port.
- **Generator code.** No SeqQA or DbQA distractor generator is released by FutureHouse or Edison
  (the FutureHouse `SeqQA/task.py` is a 10-line loader at `998a8e0a`, unchanged since 2025-09-27).
  So the flaw is shown in the items, not in a generator.

**2. LABBench2 and one reuse fixed it.**
- **LABBench2** (arXiv 2604.09554 v2; HF `EdisonScientific/labbench2` @ `3678e7e3`; harness @ `5eafca56`):
  - Every task is free response. The dataset schema has `ideal`, `answer_regex` and
    `validator_params` and no distractor field.
  - Across all 201 paper report files (23,721 cases, 1,912 unique tasks), the only lettered-list
    regex hits are 10 copies of one cloning task, whose GenBank header contains an author initial.
  - SeqQA2 (400 tasks: 20 types × 20) and cloning go to computed validators
    (`evals/evaluators.py:212`, `:131-175`, `:105`). For example, `validate_gc_content.py` computes
    the GC% from the sequence and accepts ±0.01.
  - So the centroid cue cannot exist there. This is a plain result: the successor fixed the flaw.
  - Its scores are also not comparable with LAB-Bench's. The paper reports 26–46% lower accuracy and
    attributes the drop to format and context.
- **HuggingFaceBio `seqqa-carbon-curated-3tasks`** (2026-10-26/27):
  - It ran a "choices only" test with Qwen3-4B-Base. Its figure labels read 39/40 on gibssma,
    31/40 on gene-enz, 31/40 on gibshind and 31/40 on seq-enz.
  - It then kept only PCR-seq-primers, PCR-geneprimers-enz and ORF-transeff (120 items, identical
    ids to the pin).
  - Our rules on the kept items: R1 0.17 / 0.31 / 0.28, R2 0.00 / 0.25 / 0.19, placebo 0.15–0.23,
    no p < 0.12. Fixed by exclusion.
  - **This is prior work the parent missed.** It is a model-based options-only finding on 4 of the
    6 S subtasks, posted three weeks before the parent audit. The parent's new contributions
    remain: the content-blind rules, all 6 subtasks plus DbQA, and the Haiku L4.
- **US AISI's free-response conversion** (o1 report §10.4): it converted AAid, numlen, primers-len,
  lenfrags and numfrags. None of these is in the S set of the release it used, except numfrags
  (cue-bearing in 2024). Its MC-vs-free-response gap therefore does not measure the centroid cue.
- **OpenAI** uses ProtocolQA Open-Ended only and never SeqQA.

**3. The human line in successors.**

| Source | Human SeqQA line | Rule |
|---|---|---|
| Paper, mean of 15 subtasks (Tables 2, 4) | 0.789 | unsure = wrong |
| Same, chance credit for unsure (a + (1 − c)/k per subtask) | 0.809 (S: 0.837, F: 0.789) | computed here |
| US/UK AISI 2024 (§3.3: "assigned the human baseline an accuracy equal to the success probability of a random guess for each abstained question") | ≈ 0.81 (read from a figure) | **chance credit**; matches 0.809 |
| Anthropic Claude 4, Sonnet 4.5, Opus 4.5 cards | "Human baseline: 0.79" (figure label); FigQA 0.77, Cloning 0.60, ProtocolQA 0.79 | unsure = wrong (paper) |
| Concordia AI 2025-Q4 → 2026-Q3 | 79 (Cloning 60) | unsure = wrong |
| xAI Grok 4.1 / 4.20 (no SeqQA) | ProtocolQA 0.79, FigQA 0.77, Cloning 0.60 | unsure = wrong |
| Meta Muse Spark | expert bar in Fig. 3; value not mappable from the text layer | not stated |
| LABBench2 | none | — |

Statements that depend on the rule (SeqQA):
- **Claude 4 card, Opus 4.** "reaches or exceeds the human baseline". The figure is read at ≈ 0.79,
  which is below 0.809.
- **Sonnet 4.5 card.** "reached or exceeded the human baseline in 3/4 evaluations". Its own figure
  gives ProtocolQA 0.833, Cloning 0.667, FigQA 0.497 and SeqQA 0.780. So SeqQA is counted as
  reached at 0.780, which is below both 0.79 and 0.809.
- **Statements that clear either line.** Opus 4.5 (0.8517), Concordia's Gemini 3 Pro (0.87) and
  later, and US AISI's Sonnet 3.5 new (≈ 0.86 against its own chance-credited ≈ 0.81).
- The parent's FigQA and CloningScenarios verdicts carry over unchanged to the later cards, which
  reuse the same paper lines.

**4. Exposure bounds** (`results/exposure.json`). These are arithmetic on published numbers, not
evidence that any model used the cue.
- Score s, cue share w.
- Reading A (every cue item correct): accuracy on the cue-free part = (s − w)/(1 − w).
- Reading B: accuracy on the cue-free part = s.
- Human on the cue-free subtasks: 0.764 (9 subtasks), or 0.771 (8 subtasks for 2024 runs).
- No document states its item set or weighting. We assume 600 public items, 40 per subtask, so
  per-item and per-subtask weighting coincide.

| Score (source) | s | w | A | A − human | B − human |
|---|---|---|---|---|---|
| Sonnet 3.5 new, tools (US AISI; figure) | 0.86 | 0.467 | 0.738 | −0.034 | +0.089 |
| o1, tools (US AISI; figure) | 0.77 | 0.467 | 0.569 | −0.203 | −0.001 |
| Opus 4 (Claude 4 card; figure) | 0.79 | 0.40 | 0.650 | −0.114 | +0.026 |
| Sonnet 4.5 (Opus 4.5 card figure) | 0.780 | 0.40 | 0.633 | −0.131 | +0.016 |
| Opus 4.1 (Opus 4.5 card figure) | 0.785 | 0.40 | 0.642 | −0.123 | +0.021 |
| **Opus 4.5** (card text) | 0.8517 | 0.40 | 0.753 | −0.012 | +0.087 |
| Gemini 3 Pro Preview (Concordia 2025-Q4) | 0.87 | 0.40 | 0.783 | +0.019 | +0.106 |
| GPT-5.4 (Concordia 2026-Q1) | 0.875 | 0.40 | 0.792 | +0.027 | +0.111 |
| GPT-5.5 (Concordia 2026-Q2) | 0.915 | 0.40 | 0.858 | +0.094 | +0.151 |
| GPT 6 Astra (Concordia 2026-Q3) | 0.947 | 0.40 | 0.912 | +0.147 | +0.183 |
| Muse Spark / GPT-5.4 / Gemini 3.1 Pro, tools (Meta) | 0.973 / 0.965 / 0.937 | 0.40 | 0.955 / 0.942 / 0.895 | +0.13 to +0.19 | +0.17 to +0.21 |

- **Item sampling.** With 360 cue-free items, a Wilson half-width near 0.75 is about ±0.045.
  Over 9 subtask templates it is wider still (parent: ±0.18 for rules). Gaps of ±0.03 under
  reading A are therefore inside noise either way.
- **Two scores have no human comparison in their text:** Opus 4.1 (0.71, addendum) and Haiku 4.5
  (0.66). Their reading-A values are 0.517 and 0.433.
- **What survives reading A.** Concordia's GPT-5.5 and later, and Meta's tool runs, stay above
  human even if every cue item came free. Opus 4.5's "exceeded" and the earlier claims do not.
- **Bias direction.** The cue can only make a model look more capable on SeqQA. The unsure rule
  makes the human line lower than a forced-choice human by 0.02 on SeqQA. Both push toward
  "at or above human".

**5. Per-item outputs (question 4).**
- **LABBench2 reports.** Per-item outputs of strong models (Claude Opus 4.5/4.6, Gemini 3 Pro,
  GPT-5.2, GPT-5.2 Pro) are public in the LABBench2 GitHub reports. That benchmark has no options,
  so the centroid question does not arise there.
- **DeepSeek-R1 on LAB-Bench** (`lihaoxin2020/deepseek-reasoner-full-lab_bench-r1` @ `43fa27ef`, 600 SeqQA chains):
  - `doc_id` follows the HF order. The best-matching revision is `4709d14f`, where 94% of chains
    contain a 14-character piece of their item.
  - The option order the model saw is not stored. The final letter is bound to one option's text
    in 122 chains: 26 in S (25 GC-percent, 1 AAseq; 0 on any PCR or Gibson subtask) and 96 in F.
  - The pre-registered gate (≥ 20 items in ≥ 3 subtasks on each side) is not met, so no item-level
    test was run.
  - The prereg discloses that an earlier exploratory probe saw some key/distractor counts. They are
    not reported as a result.
- **Nothing else.** No other per-item outputs of LAB-Bench MC runs by strong models were found
  (search list in `inventory.md` §C).

## The confound

Same as the parent: the key is the option the distractors resemble (centroid / edit-distance
medoid), or the middle of {k − 1, k + 1, k/2} for GC%. The rules see only the option strings.
Example ids are the parent's (`../lab-bench/results/surface_items.csv`). Per-version ids and flags
are in `results/versions.json`; no item text is committed (canary request).

## Robustness

| Check | Result | Survives? |
|---|---|---|
| Independent rule R2 (edit-distance medoid) | 0.9125–0.9167 on S in every release; 1.00 on 4 subtasks and numfrags-2024 | yes |
| Held out | Rules frozen on `5c77cec6`; the other five releases are new data (S 0.996–1.000). Id-parity halves: R1 1.00 / 1.00 on every S subtask in every release | yes |
| Placebo rule (smallest sha1 of option text) | 0.242–0.258 over all 15 subtasks (chance 0.25) | yes |
| Permutation null (1,000 key draws per subtask) | p = 0.001 on every S subtask, every release | yes |
| Interval over subtasks rather than items | R1 on all 15: [0.42, 0.80] (2024) and [0.37, 0.73] (2025-09) | yes, wide |
| F subtasks under the same rules | R1 F mean 0.36 (2024, numfrags included) and 0.26 (2025+) | flaw confined to S (plus numfrags in 2024) |
| Item set assumption in bounds | Not checkable; if a card used the full 750 the share is the same (50 per subtask) | stated |
| Figure-read numbers (AISI, Claude 4 card) | ±0.01–0.02 reading error; the Opus 4.5 / Sonnet 4.5 values are printed labels | stated |

## Alternative explanations

1. **"The cards' runs were not on these items."** Possible: Anthropic does not state its item set.
   But every public release carries the cue, the Inspect port loads it, and the private 20% was
   by the paper's account built by the same generators (App. C.7; not checkable). Any SeqQA item set available to a third party has
   it.
2. **"Strong models compute the answer, so the cue is irrelevant."** This may well be true for
   Opus 4.5 and later. Reading B is exactly that case, and under it every claim holds. The bounds
   only say how much of each claim the cue *could* carry. They cannot say how much it did. The one
   causal result remains the parent's Haiku L4 on the Gibson subtasks.
3. **"Chance credit is the wrong correction too."** Agreed: the plausible range is chance to the
   humans' own precision (parent). The SeqQA statements at 0.78–0.79 fail at chance credit, so they
   fail anywhere in that range.

## What was already known

- The parent audit (`../lab-bench/`).
- HuggingFaceBio `seqqa-carbon-curated-3tasks` (2026-10-26) found the options-only leak on 4 of
  the 6 S subtasks with a small model, and excluded them. The parent's prior-work search missed
  this; its "no prior report" statement should be read with this correction.
- US AISI (2024) already corrected the human line by chance credit, and already showed that
  free-response SeqQA lowers scores, on five non-cue subtasks.
- LABBench2's paper says LAB-Bench "made concessions to make grading easier (using
  multiple-choice answers)".

**New here:**
- the cue in every release, including RE-seq-numfrags in 2024;
- the release-by-release change log;
- LABBench2's format and grading checked on all reports;
- the map of which documents carry the unsure rule;
- the exposure bounds;
- the SeqQA2 leads.

## What this does not show

- That any model in any card or report used the cue. No item-level test was possible (§5).
- Anything about Anthropic's, Google's or Concordia's exact item sets, prompts or option orders.
  None is published.
- Anything about the private 20%.
- **The SeqQA2 leads are post hoc.** The "None" share comes from the reports' `expected_output`.
  For that type the validator recomputes the answer from the sequence, so the expected output
  could disagree with it. The refusal counts come from `llm_answer == "[REFUSED]"` in truncated
  report text.

## Pins and how to reproduce

- **Parent data.** `../lab-bench/data/hf` (`5c77cec6`).
- **New downloads** (git-ignored `data/`):
  - `hfrev_<rev8>/` for the five earlier revisions; parquet sha256s are in `results/versions.json`.
  - `hfbio_carbon_data/` (`33e24310`).
  - `hf_lihaoxin_dsr1/` (`43fa27ef`).
  - `labbench2_gh/` (raw files at `5eafca56`; tree listing in `gh_tree/`).
  - `labbench2_hf/README.md` (`3678e7e3`).
  - `lb2_paper/` (v2 sha `e1438295…`).
  - `cards_new/` (shas in `inventory.md`).

```bash
P="../lab-bench/data/.venv/bin/python -I"
$P scripts/versions.py   # Q1 rules on every release + curated subset -> results/versions.json
$P scripts/lb2.py        # LABBench2 format, grading, SeqQA2 leads     -> results/lb2.json
$P scripts/exposure.py   # human lines and bounds                      -> results/exposure.json
$P scripts/peritem.py    # DeepSeek-R1 recoverability gate              -> results/peritem.json
$P scripts/collect.py    # everything                                   -> results.json
```

Seeds are 0. Inference: none.
