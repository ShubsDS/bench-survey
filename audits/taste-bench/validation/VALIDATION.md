# Taste-Bench audit: independent validation

Validator, 2026-11-17. I did not write the audit and tried to break each claim. Every number below
comes from a script in this folder, run with `../data/.venv/bin/python -I`, and is stored in
[`validation.json`](validation.json) and the per-script `v*.json` files. My scripts read the pinned
parquet files (sha256 checked in `v_common.py`) and the released `summary.json` files, and import
nothing from `../scripts/`. My own tests were pre-registered in
[`prereg_validation.md`](prereg_validation.md) (commit `5947870`) before any of them was run; the
blind hand labels were committed (`300a7ca`) before the key was joined.

**Fair one-line conclusion.** The option-origin cue is real and survives a proper null, but it
does not beat the leaderboard on a like-for-like scale, and it needs the construction label, which
a model can infer in engineering but not in research. The hardest cell's labels are recoverable
from the prefix by a careful reader (my blind agreement with the key is 86%), so C3's "the wrong
option reads as the better one, the paper's reading is not needed" does not survive. The
parse-failure, research-domain, horizon and SWE-bench results reproduce, with narrower wording.

## Pins and order

- Parquet sha256 `377c6031…` (engineering) and `8528ca9f…` (research), manifest `ab2db9cc…`,
  dataset card `21db0918…`, paper tarball `675cebfd…`, repo `b636e868` with a clean tree: all
  match the audit.
- `git log`: prereg amendment `6e3a776` committed 19:03:10; the parquet files carry mtimes
  19:03:14–15. The amendment precedes the download, by four seconds.
- Rerun: all eight auditor scripts (`read_figures`, `a_aggregate`, `b0`–`b2`, `b5`, `b6`,
  `make_results`) reproduce every committed result file byte for byte (`git status` clean after
  the rerun). `b4_haiku.py` was not rerun (its outputs are cached responses).

## Verdicts

| Claim | Auditor's statement | Verdict | Validator's number | How checked |
|---|---|---|---|---|
| C1 rule | "Higher prefix overlap" 65.9% parallel / 34.2% detour held-out; construction-aware rule 60.4 (61.4 held-out), above the best model's 59.7 | **Corrected** (feature confirmed; "above every model" fails) | My implementation of the written `cont` definition: 58.8 full set; held-out median 58.8 [52.9, 63.9] over 1,000 random task splits. Null (placebo features, task-level label flips, signs fitted per cell): median 47.7–47.9, 99th pct 56.7–58.3; 61.4 is at or above the 99.8th pct. Single-order Averages of 6 models exceed 60.4 (Sol 65.2). With the cell inferred from query + options: 52.1 (`cont`), 55.1 (`ground`) | `v1_floor_null.py`, `v2_cell_inference.py` |
| C2a L4 | Final-step cut: detour − parallel +6.8 [1.8, 11.9] (Haiku) | **Downgraded** (reproduced, not specific to the final step) | +6.82; construction-shuffle placebo p = 0.007. Removing the second-to-last step instead (H3) gives +3.0 [−2.5, 8.5]; the final-step-specific part (H2 − H3) is +3.8 [−1.7, 9.7] | `v8_h2.py`, `v9_h3.py`, `v12_h3_score.py` |
| C2b R | Haiku does not track the cue item by item | **Not re-derived** (accepted from the auditor's placebo-split output; consistent with my finding that Haiku H1 agrees with the key on 27% of my 44 sampled items) | — | — |
| C3 | Detour engineering below chance from the options alone (Haiku 28.0%); 7 of 14 published models below 50% single-order; the paper's reading "is not needed to explain the cell" | **Downgraded** | 7 of 14 below 50% (parsed replies), 8 of 14 (all presentations). Distinguishably below 50%: 4 of 7 (task design effect from Haiku's ICC 0.14); 3–6 under other assumptions. No selection carry-over to judge-related models (residual difference +0.2 points, p = 0.53; parsed −2.4, p = 0.28). Validator blind labels agree with the key on 38 of 44 [74.5, 95.5] | `v5_detour_eng.py`, `v6_*` |
| C4 | GLM-5.2 6th → 3rd; Grok 4.20 15.7 published, 63.5% of parsed answers right | **Confirmed, reworded** | Parsed-only bounds reproduce exactly (GLM 55.9–57.0). Unparsed-as-chance: GLM 54.3–56.4 (rank 5 to 3). Grok 4.20 63.5% pooled = Sol's pooled 63.5%, but on the Average scale 61.1 vs 65.2. Paper discloses counts (Table 5) | `v7_parse.py` |
| C5 | "Detour harder in both domains" fails in research | **Confirmed** | Research D − P −0.11, 7 of 14 models; engineering −22.1, 14 of 14 | `v10_secondary.py` |
| C6 | Repeat run 58.2 vs 55.6 exceeds 8 of 13 adjacent gaps; one task supplies 24 of 112 research items | **Corrected** | Same model and setting per App. B (Sol "xhigh") and Table 8. Against Average gaps: 8 of 13 below 2.6 (one at 2.62). Like-for-like pooled gaps: 6 of 13. 24 of 112 (17 P-Res + 7 D-Res), 10.7 points of weight: confirmed. The main run's summary records 78 reasoning tokens per presentation for Sol against 3,470 for GPT-5.5 | `v10_secondary.py` |
| C7 | Composition explains 3.6 of 41.3 points | **Confirmed; caveat corrected** | 3.6 of 41.3; 10 of 14 below 25% at "more work" is correct, but paired accuracy below 25% does not imply consistent wrong choices (position flips also lower it; one model's SD on 69 items is 5.2 points) | `v10_secondary.py` |
| C8 | Without Sol and GPT-5.5, r = 0.687 (69th pct) | **Confirmed** | r = 0.625 all, 0.687 without the pair (70.9th pct of 55 drop-two values); figure values check against the paper's stated ranks and spreads (GPT-5.5 8th, DeepSeek 5th, top-four spread 4.0 / 10.7) | `v10_secondary.py` |
| C9 | GPT-4.1 options-only 63.7% on released P-Eng; 4 of 14 models at or below with the full prefix | **Confirmed, narrowed** | 4 of 14 on all presentations; 2 of 14 on parsed replies (GPT-5.4 Mini, Mistral Medium 3.5) | inline check, recorded in `validation.json` |
| C10 sabotage | 5 research prefixes contain an agent planning sabotage | **Corrected** | 4 of the 5 state a sabotage or sandbagging plan; the fifth states it will *not* sabotage. The paper never mentions sabotage or sandbagging runs, so no filter is described | local read; ids only |
| C10 human review | 98.8% cannot detect the defect; ≥ 92% on removed items | **Downgraded** | The ≥ 92% assumes 26 retained judgments on the 15 removed items; the true bound runs from 50% (4 retained) to 93% (30). The review also includes 15 trivial-removed items | `v10_secondary.py` |
| C10 end-to-end | 33.7% is not k/41 | **Confirmed** | 13/41 = 31.7, 14/41 = 34.1; 69/205 = 33.7 (five runs per task) fits; the paper states no denominator | `v10_secondary.py` |
| Inference | 3,008 calls, 1.63 USD; prereg before download | **Confirmed** | ledger sum 1.6349 USD over 3,008 lines before my run; validator added 1,024 Haiku calls (0.57 USD); audit total 2.21 USD of 3 | ledger |

## A. The construction-aware floor (C1, weak spot 1)

**The feature is real.** Signs fitted per cell on a training half add four free parameters. With
1,000 placebo features (each item gets another item's feature pair, attached by position) and
1,000 task-level label flips, under the same fitting and held-out scoring, the held-out Average has
median 47.7–47.9 and 99th percentile 56.7–58.3 (`cont`). The null median is below 50 because ties
count as wrong. The auditor's 61.4 is above 99.8% of every null; my own median over random splits
(57.6 fitted, 58.8 with signs fixed in advance) is above 98.5%. The signs were also pre-registered
from the construction story before download, which removes the free parameters altogether.

**But the headline sentence does not hold.**
- My implementation of the written definition gives 58.8 (cells 58.1 / 64.6 / 57.5 / 56.3), not
  60.4; the definition leaves tokenisation open, and 1.6 points move with it. The auditor's 61.4
  comes from one favourable split; over 1,000 task splits the held-out Average is
  58.8 [52.9, 63.9].
- The rule's answer is order-invariant, so its paired and single-order accuracies are equal. A
  model's paired score is lowered by position flips. On single-order Averages, 6 of 14 models
  exceed 60.4: GPT-5.6 Sol 65.2, GPT-5.5 64.6, GLM-5.2 64.0, GPT-5.6 Terra 62.2, Grok 4.5 62.0,
  Claude Sonnet 5 60.7 (Opus 60.3). "Above the best published model" compares unlike scales.
- **Can a model know the cell?** In engineering, yes: a logistic model on query and option words,
  cross-validated by task, labels detour vs parallel at 94.9% (AUC 0.99; majority 68.2%). In
  research it cannot (63.4%; AUC 0.51–0.78; majority 57.1%). With the inferred cell, the rule's
  Average is 52.1 (`cont`) or 55.1 (`ground`), its engineering cells nearly unchanged (58.1, 59.0)
  and parallel research collapsing to 31.2.
- **Held-out by task:** yes. `b1_features.py` and `b2_floor.py` split on (cell, `task_id`). Since
  the signs were fixed by the prereg, the held-out half is a subset check, not a fit.

Fair statement: an origin rule that never reads for meaning reaches 58.8 on the paired scale, level
with the top two models' paired scores and below six models' single-order scores. In engineering a
model could apply it from the query alone. Level L2 stands.

## B. Detour engineering (C3, weak spot 2)

**The filter.** The paper (App. A, "Prompts of the generator and the judges"; App. A "Counts")
shows the trivial-filter prompt: the two candidates only, *no query*, one shuffled order per
judge, four judges (Kimi K2.5, GPT-4.1, Llama 4 Maverick, Mistral Large 3), the same rule in every
cell. An item is dropped only when all four are right. The dataset card says "from `query` and
`choices` alone", which does not match the paper's prompt (no query); the auditor's H0 followed
the paper. Judge accuracy on released items is reported only for parallel engineering (34.7–63.7).

The filter guarantees only that one of four judges erred, so it does not mechanically force an
outside model below 50%. Haiku's 28.0% says that Haiku shares the judges' options-only
preferences strongly. Since the paper and the card both say options-only evaluation is not the
protocol, this is a statement about the selection, not about a published conclusion.

**With the full prefix (published models).** Single-order accuracy in detour engineering, from
the summaries: 7 of 14 below 50% on parsed replies (Opus 5 40.6, DeepSeek V4 Flash 41.7, GPT-5.4
Mini 38.7, GPT-5.4 Nano 42.3, Luna 43.6, Sonnet 5 46.4, MiniMax M3 47.0); 8 of 14 on all
presentations (adds Grok 4.20). Intervals use the exact per-item variance from the paired counts
and a task design effect (m* = 2.84): with Haiku's within-task ICC (0.14), 4 of the 7 have upper
bounds below 50 (Opus 5, DeepSeek V4 Flash, GPT-5.4 Mini, GPT-5.4 Nano). The count is 6 with no
clustering, 5 at ICC 0.3, and 3 at the worst case ICC 1 (all presentations; two of them
parse-affected). The auditor's "2" used one effective draw per task, which is more conservative.

**Separating explanations.**
- *Selection carry-over.* Regressing detour-engineering accuracy on each model's other-cell mean,
  judge-family models (six GPT models, Mistral Medium 3.5) sit +0.2 points above the others
  (p = 0.53; on parsed replies −2.4, p = 0.28). The slope on capability is positive (0.31) or flat.
  The best detour-engineering models are Grok 4.5, Sol and GPT-5.5, two of them judge-family.
  Regression to the mean for related models is not supported (14 models: a weak test).
- *Label error.* Blind labels below.
- *A real preference for the detour branch.* Consistent with the data, not separable from the
  wording effect with released aggregates.

**Blind hand labels.** I read 44 random detour-engineering items (seed 1; 38 tasks): the query,
the first 1,500 and last 3,000 characters of the prefix, and both options, without the key.
- Agreement with the key: **38 of 44, 86.4% [74.5, 95.5]** (task bootstrap); 28 of 33 at
  confidence ≥ 2.
- Agreement with the "lower `cont`" rule: 27 of 40 (67.5%). The rule agrees with the key on 29 of
  40 in this sample. Haiku H0 (options only, published order) agrees with the key on 15 of 44 and
  Haiku H1 on 12 of 44.
- **Caveats.** I am a language model, not a human expert. Some of my calls drew on facts seen in
  other sampled items from the same sandbox family (for example an empty vendored dependency, a
  read-only shared virtualenv, a vendored library that fails on Python 3.12). A model answering
  one item sees none of that, so 86% is an upper reading for a single-item reader. I also knew the
  construction rule (the wrong option is the agent's next step) and tried not to use it.
- Reading: the forks are about which verification or tooling route will work in this sandbox,
  and the prefix usually shows the constraint (missing `node_modules`, an import error, a broken
  launcher). The label is defensible from the shown material. The audit's L1 note that "the label
  depends on sandbox facts the prefix does not settle" holds for a minority of items at most. The
  audit's sentence that the paper's reading "is not needed to explain the cell" is withdrawn; the
  low scores are compatible with models not reading the environment evidence, which is close to
  the paper's reading.

Also corrected: the README said the correct detour option "relies on what the agent learned after
the failure". The generator rubric (App. A) rejects forks whose recovery is "only nameable after
seeing the failure", and relocates forks to after the constraint is visible.

## C. Parse failures (C4, weak spot 3)

- **Distribution.** Released files give failures by cell only (no per-item, per-length or
  per-truncation records; truncation hit one item for two models, per App. B). Errors are zero
  everywhere; all failures are unparsed replies. GPT-5.4 Mini: 94 of its 112 in parallel
  engineering (37.9% of that cell's presentations). Grok 4.20: 66–69% of research presentations
  against 31–44% of engineering, although detour research has the shortest prefixes (median 12.8k
  characters). At cell level, failures do not follow prefix length.
- **Bounds** (paired Average): published (unparsed = wrong); unparsed as chance; parsed-only.
  GLM-5.2 53.9 / 54.3–56.4 / 55.9–57.0 (rank 6; 5–3; 3). GPT-5.4 Nano 36.6 / 38.3–45.1 /
  40.7–43.9. Mistral Medium 3.5 37.7 / 38.6–42.3 / 39.9–41.5. GPT-5.4 Mini 40.1 / 41.8–43.8 /
  42.3–45.0. Grok 4.20 15.7 / 28.9–39.0 / ≥ 32.8. My parsed-only bounds equal the auditor's.
- GLM's move rests on 17 unparsed presentations (1.7%) and a 0.4-point margin over Opus 5, inside
  the ±5-point interval the paper's own figure shows.
- **Disclosure.** The paper reports every unparsed count (Table 5), states that unparsed counts as
  wrong (App. B, Fig. 2 caption), and drops the three >9% models from the SWE-bench comparison.
  C4 is a restatement of disclosed counts with a rank consequence that depends on the scoring rule.
- The summaries' `position_choices` totals are below their `parsed` totals for several models
  (Grok 4.20 523 vs 545; GPT-5.4 Mini 846 vs 892; Grok 4.5 940 vs 994): an unexplained
  inconsistency in the released files.

## D. The H2 intervention (C2)

- **Reproduced:** H2 − H1 is +3.33 (detour) and −3.49 (parallel), contrast +6.82.
- **Pre-registration.** Amendment 1 fixed H2 and the predicted direction per construction. The
  combined contrast is the natural joint test but was not named. Each per-construction interval
  touches 0.
- **What else changed.** The cut removes a median 448 characters (detour) and 895 (parallel) of the
  2,000-character window, so the window also slides back, and it slides further for parallel items
  (window token Jaccard 0.74 vs 0.60). The removed step is not lexically closer to either option
  (mean overlap difference −0.009 and +0.002). The contrast holds for short and long cuts (+6.7,
  +8.2) and in both domains (+7.8 engineering, +4.2 research). Only 22–23% of items change at all.
- **Placebo 1** (no spend): shuffling the construction label across tasks within domain gives
  p = 0.007 for the contrast.
- **Placebo 2, H3** (Haiku, my run, pre-registered in V8; 1,024 calls, 0.57 USD, no unparsed
  replies). I removed the second-to-last step and kept the final one.
  - Detour − parallel contrast against H1: **+3.0 [−2.5, 8.5]** (detour +1.8, parallel −1.2). That
    is 44% of the H2 effect, in the same direction.
  - H2 against H3, the part specific to the final step: +3.8 [−1.7, 9.7].
  - So about half of the H2 contrast comes from losing recent context in general. The part tied
    to the final step is not distinguishable from zero.
  - C2's L4 claim weakens to: removing recent context helps Haiku a little on detour items and
    hurts it on parallel items.
- **Interpretation.** In parallel items the final step is part of the passing attempt, so cutting
  it also removes genuine evidence. The intervention does not change the origin cue alone. It
  stays Haiku-only, and it says nothing about published models.

## E. Secondary claims

- **C5.** Confirmed from the summaries (identical to App. C.1): research D − P −0.11, 7 of 14;
  Sol and GPT-5.5 are 10.9 and 12.5 points better on research detours.
- **C6.**
  - The paper lists Sol at "reasoning effort xhigh" for the main run (App. B) and reruns
    "low / xhigh / max" with "questions, prompt, token limit and protocol unchanged" (§4.3), so
    the same-setting reading is the paper's own. But the main run's summary records only 78
    reasoning tokens per presentation (GPT-5.5 at xhigh: 3,470), so I cannot confirm the main run
    reasoned at xhigh.
  - The 2.6-point difference is pooled accuracy. Against Average gaps it exceeds 8 of 13 (one gap
    is 2.62); against pooled gaps, the like-for-like comparison, 6 of 13.
  - The paper reports no run-to-run variance. It does show 95% item-bootstrap whiskers for every
    model (Fig. 2) and bootstrap intervals for the effort differences ([−3.2, +2.8] for Sol), so
    the ±5-point width is not undisclosed.
  - Task concentration confirmed: `ai_rd_fix_embedding/main` gives 24 of 112 research items;
    the top three tasks give 57. For Haiku H1, the research half-width is ±11.2 points by task
    bootstrap against ±8.9 by item bootstrap.
- **C7.** Re-derived from Tables 6–7: predicted 47.6 / 43.6 / 41.8 / 44.0; 3.6 of 41.3. The audit's
  caveat "under paired scoring [below 25] means consistent wrong choices, not guessing" is wrong.
  A position-flipping model also scores below 25, and 10 of 14 below 25 on 69 items is within
  about one SD (5.2 points) for most of them.
- **C8.** Confirmed. The models that built the items: GPT-5.6 Sol (generator), GPT-5.5 (engineering
  trajectories and horizon annotation). GPT-5.4 Mini and Nano are not GPT-5.4 and are excluded from
  the comparison anyway.

## F. Leak scan

`v11_leak_scan.py` checks every committed file under `audits/taste-bench/` (46 files, ledger
included, response cache excluded). It compares every whitespace-normalised 40-character window
and every 8-word sequence with every item's `query`, `choices`, `prefix_text` and
`prefix_text_short`.
- **Scripts:** the only hits are generic Python (`import sys from collections import
  defaultdict`) and runs of dashes, which also occur inside agent transcripts. These are not item
  text.
- **One real match:** `results.json` and `results/b0_handread.json` carried a five-word phrase
  that also appears in item queries. It is a generic description, under the 8-word threshold, but
  I rephrased it in both files.
- **Rescan after the final commit:** see `v11_leak_scan.json`. No `choices` hit, no `query` hit
  and no 8-word hit outside script boilerplate.
- **Other paths:** the blind views and item text stayed in the git-ignored `data/` folder. Haiku
  received only the query, the options and at most 2,000 characters of the short prefix.

## What I could not check

- Per-item behaviour of published models: not released, so no L3 for any published model.
- Failure distribution by item length or truncation: not released.
- Whether Sol's main run was really at xhigh (token record above).
- C2b (Haiku's item-level cue tracking) was accepted, not re-derived.

## Final evidence levels

C1 L2 (feature real; floor level with, not above, the leaderboard on a like-for-like scale).
C2: a weak L4 for Haiku only. Removing recent context moves Haiku in the predicted direction;
the effect specific to the final step is not shown (H2 − H3 +3.8 [−1.7, 9.7]). C3 L2 for options-only, which is
expected by selection; the with-prefix below-50% cell is a published-number fact (4 of 7
distinguishable). The label-error and carry-over explanations are not supported. C4 L1 on
disclosed counts (rank change depends on the rule). C5 failed published claim (research).
C6 L1 (precision; scale-corrected). C7 R. C8 R. C9 L2, narrowed. C10 L1, corrected.
