# Taste-Bench: the answer can be read from how each item was mined, and the hardest cell is hard from the option wording alone

Status 2026-11-17. Round two. Not yet independently validated. The dataset gate was opened by the
repository owner during the audit. Every item-level test was pre-registered before the parquet
files were downloaded ([`prereg.md`](prereg.md), amendment 1, commit `6e3a776`). Inference:
Claude Haiku only, 3,008 calls, 1.63 USD.

**Bottom line.**

- **Validity hole (L2).** A rule that never reads what the options mean beats every published
  model. In parallel items the correct option is the shown trajectory's own next step. In detour
  items the *wrong* option is. "Pick the option whose words overlap more with the end of the
  prefix in parallel cells, less in detour cells" scores a 60.4 Average (61.4 on held-out tasks).
  The best published model scores 59.7. The rule needs the cell label, which models are not shown.
- **Does it drive scores?** Not shown for published models: no per-item logs are released. For
  Haiku the answer is "a little".
  - Cutting the final prefix step moves Haiku's accuracy in opposite directions by construction.
    The difference is +6.8 points [1.8, 11.9] (L4, Haiku only).
  - Haiku's item-level accuracy does not track the lexical cue itself (R).
- **The hardest cell (detour engineering) is hard before the trajectory is shown.** Haiku picks
  the labelled answer on 28.0% [22.8, 33.7] of presentations from the two options alone.
  - Seven of 14 published models are below 50% single-order there with the full trajectory.
  - So the "wrong" option reads as the better one. The paper's reading, that these models fail to
    "recognise a mistake before the acting agent did", is not needed to explain the cell.
  - This is what the selection filter is expected to produce: it keeps an item only if at least
    one of four judges got it wrong from the options alone.
- **Narrower published claims that move.**
  - Parse failures change leaderboard ranks.
  - "Detour harder than parallel in both domains" fails in research.
  - The paper's two runs of one model at one setting differ by more than most adjacent
    leaderboard gaps.

| Claim | Level | Key numbers |
|---|---|---|
| C1 Label predictable from option origin, with opposite signs by construction | **L2** | "higher prefix overlap" held-out 65.9% (parallel, n = 88) and 34.2% (detour, n = 152), cluster-permutation p = 0.010 and 0.003. Floor Average 60.4 / 61.4 against best 59.7 |
| C2 Models use the cue | **L4 small (Haiku)**; **R** for the lexical feature (Haiku); untestable for published models | final step removed: detour +3.3 [0.0, 6.5], parallel −3.5 [−7.1, 0.3], difference 6.8 [1.8, 11.9]. Accuracy split by the cue: −0.5 and −5.0 points, CIs span 0 |
| C3 Detour engineering is below chance from option wording | **L2 (Haiku options-only)**, cell-level match to published | Haiku options-only 28.0% [22.8, 33.7] single-order, n = 266. Published: 7 of 14 models below 50% |
| C4 Unparsed replies change published ranks | **L3** | GLM-5.2 rises from rank 6 to 3 on a lower bound. Grok 4.20 scores 15.7 published; on parsed replies it is 63.5% single-order, equal to the top model |
| C5 "Detour harder in both domains" | **fails in research** (published numbers) | research model-mean −0.1 points; 7 of 14 models |
| C6 Precision of the ranking | **L3** | same model and setting: 58.2 vs 55.6 pooled, more than 8 of 13 adjacent gaps. One task supplies 24 of 112 research items, 10.7 points of Average weight |
| C7 Horizon gradient is cell composition | **R** | composition predicts 3.6 of the 41.3-point gap |
| C8 SWE-bench comparison driven by the construction models | **R** | dropping GPT-5.6 Sol and GPT-5.5 gives r = 0.687 (69th percentile of 55 drop-two values) |
| C9 Options-only signal survives the filter | **L2** (paper's own numbers) | GPT-4.1, options only, scores 63.7% on released parallel-engineering items; 4 of 14 models score at or below this with the full prefix |
| C10 Human review, end-to-end and distillation claims | **L1** | arithmetic on published counts; missing controls |

## The benchmark and what rests on it

Taste-Bench is from Pan et al., arXiv 2609.25804, September 2026 (dataset `wenbopan/taste-bench`;
code github.com/wbopan/tastebench). It has 502 two-option questions cut from agent trajectories
at a "decision fork".

- **Sources.** The 390 engineering items come from GPT-5.4 and GPT-5.5 runs on SWE-bench Pro. The
  112 research items come from METR's MALT transcripts (Claude and DeepSeek agents).
- **Options.** GPT-5.6 Sol, the top leaderboard model, wrote both options of every item, knowing
  which was correct.
- **Filtering.** Four judges (Kimi K2.5, GPT-4.1, Llama 4 Maverick, Mistral Large 3) answered from
  the options alone, and an item was dropped when all four were right. An item was kept only when
  all four confirmed its label from the full record.
- **Scoring.** Each item is asked in both orders and counts only if both answers are right, so
  chance is 25%. The headline Average is the mean of the engineering and research accuracies.

The conclusions under test are in [`claims.md`](claims.md):

- the 14-model ranking, and "the best model answers only 59.7%";
- detour forks are harder than parallel forks "in both domains", read as recognising a mistake
  before the agent did;
- accuracy falls with the time horizon;
- taste is only partly correlated with SWE-bench Verified;
- labels agree with human reviewers 98.8% of the time;
- taste can be distilled into a smaller model.

The leaderboard accepts new models by pull request.

## What we found

1. **The label is predictable from where the options came from (C1).** The paper states both
   facts this rests on (App. A.2, §3.2).
   - Parallel items: the prefix is the passing attempt's history, so the correct option is that
     trajectory's next step.
   - Detour items: the prefix stops just before the agent takes the abandoned direction. The wrong
     option is therefore the trajectory's next step, and the correct one (the recovery) relies on
     what the agent learned after the failure.
   - We pre-registered the consequence: overlap with the prefix points to the answer in parallel
     cells and away from it in detour cells. It does, for both feature definitions.
2. **Detour engineering is below chance from the options alone (C3).** The two options carry most
   of the cell's difficulty: Haiku with only the options scores 28.0%, and the prefix tail lifts
   it to only 36.1%.
3. **One small model is pulled a little by the end of the prefix (C2).** Haiku's accuracy shifts
   when the final prefix step is cut, in the direction the origin account predicts. The size is a
   few points, far smaller than the rule's 15–30-point edge.
4. **Narrower conclusions.** Several move: parse failures, the research-domain claim, precision,
   and the human-review and end-to-end arithmetic. Two plausible confounds were tested and the
   conclusion held: the horizon gradient (C7) and the SWE-bench comparison (C8).

| Quantity | n | Value | 95% CI or null |
|---|---|---|---|
| "Pick higher `cont`", parallel cells, full set / held-out | 172 / 88 | 64.0% / 65.9% | one-sided task-permutation p = 0.001 / 0.010 |
| "Pick higher `cont`", detour cells, full set / held-out | 330 / 152 | 36.1% / 34.2% | p < 0.001 / 0.003 |
| "Pick higher `ground`", parallel / detour, held-out | 88 / 152 | 63.6% / 34.9% | p = 0.001 / 0.001 |
| Construction-aware `cont` rule: Average, full set / held-out | 502 / 251 | 60.4 / 61.4 | best published 59.7 |
| Detour engineering, "pick lower `ground`", full set / held-out | 266 / 135 | 61.7% / 63.0% | Holm p < 0.001; best published 48.1% (paired) |
| Haiku, options only, detour engineering, single-order | 266 | 28.0% | [22.8, 33.7] |
| Haiku, options only, all items, single-order / paired | 502 | 41.4% / 31.9% | [36.8, 46.3] / [27.2, 37.0] |
| Haiku, final step removed minus prefix tail: detour − parallel | 330 + 172 | +6.8 points | [1.8, 11.9] |
| Published models below 50% single-order on detour engineering (parsed replies) | 14 | 7 | 2 with task-level CI wholly below 50 |
| Rubric-passing items all four judges solved from the options alone | 1,809 | 1,080 (59.7%) | paper's funnel |

**Bias direction.**

- The origin cue favours a model that follows the prefix on parallel forks and penalises it on
  detour forks.
- The option-wording effect makes detour engineering look like a failure of foresight when, for
  Haiku, it is mostly present without any trajectory. Both inflate the paper's reading of the
  detour–parallel gap.
- Parse-failure scoring makes four models look worse at taste than their parsed answers show. It
  also places one model below chance when its parsed accuracy equals the top model's.

## The confound

**Feature definitions.**
- `cont`: Jaccard overlap between the sets of lower-case word tokens of three or more characters
  in an option and in the last 3,000 characters of `prefix_text`.
- `ground`: the share of an option's content tokens (four or more characters) that occur anywhere
  in the prefix.
- **Rule:** pick the option with the higher value; ties count as wrong. The rule does not depend
  on option order, so its paired and single-order accuracies are equal.

The definitions, signs and held-out split (tasks split 50/50 within each cell, seed 0) were
committed before download (`scripts/b1_features.py`, [`results/b2_rules.json`](results/b2_rules.json)).

| Cell | "higher `cont`" right | "higher `ground`" right | Items | Tasks |
|---|---|---|---|---|
| Parallel engineering | 62.9% | 58.1% | 124 | 62 |
| Parallel research | 66.7% | 64.6% | 48 | 8 |
| Detour engineering | 35.3% (lower right: 56.0%) | 33.1% (lower right: 61.7%) | 266 | 133 |
| Detour research | 39.1% (lower right: 59.4%) | 43.8% (lower right: 46.9%) | 64 | 22 |

**Other features.**
- No other pre-registered form feature (length, paths, code spans, identifiers, numbers,
  verification words, hedging) reaches the L2 bar after Holm correction.
- In both engineering cells the longer option is correct about 61% of the time (full-set
  p = 0.03 and 0.006). On held-out tasks this falls to 55–56%.
- The answer letter is close to balanced: A is correct in 42–52% of items per cell.

**Examples by id** (no item text reproduced).
- `par-sse-67dcb776a7cedb99-v2`: parallel; the correct option scores higher on both features.
- `det-sse-d8db8b8100b5d57d-v3`: detour; the correct option scores lower on both.
- `det-sse-a3b9e33520ba1b14-v3`: detour, where the rule fails.

**What detour engineering contains.** This comes from a hand read of 13 items
([`results/b0_handread.json`](results/b0_handread.json)) and a keyword scan of all 266, added after
the hand read and flagged as exploratory.
- 12 of the 13 sampled items are forks between two ways to verify a patch, or to obtain a working
  tool, in a sandbox with missing dependencies.
- 220 of 266 queries contain verification or environment-failure vocabulary, and 164 ask the
  reader to choose or select the next step. The generator rewrote these queries to pose the fork.
- In several items the label depends on sandbox facts the prefix does not settle: whether a write
  is allowed, or whether a toolchain exists somewhere on disk.
- The losing option is often the conventional move, such as running the full suite or the
  typecheck. That fits Haiku's 28% from options alone.

## The effect

No per-item model outputs are released, only per-cell aggregates in `results/*/summary.json`, so
the item-level test of "models use the cue" is run on Haiku. Haiku received the paper's prompts:
- H0: options only (the trivial-filter prompt);
- H1: the evaluation prompt with the last 2,000 characters of `prefix_text_short`;
- H2: H1 with the final rendered step removed.

Every item was asked in both orders. There were no unparsed replies.

| Cell | Published model mean (paired) | Haiku H0 options only, paired [single] | Haiku H1 prefix tail, paired [single] | Haiku H2 final step cut, paired [single] |
|---|---|---|---|---|
| Parallel engineering | 58.1 | 45.2 [59.3] | 64.5 [71.8] | 59.7 [67.3] |
| Parallel research | 50.9 | 25.0 [36.5] | 64.6 [70.8] | 60.4 [69.8] |
| Detour engineering | 35.9 | 21.4 [28.0] | 29.3 [36.1] | 32.7 [39.5] |
| Detour research | 50.8 | 54.7 [66.4] | 60.9 [68.8] | 64.1 [71.9] |

Haiku with a 2,000-character tail reproduces the published cell pattern (detour engineering far
below the rest).

- **The deficit comes from the options (C3).** Haiku's detour-engineering accuracy is below chance
  with the options alone (single-order 28.0% [22.8, 33.7]). Adding the prefix tail raises it to
  36.1%.
- **Selection reading.** Haiku's options-only accuracy over all items is 41.4% [36.8, 46.3]
  single-order, below 50%. The pre-registered reading is that the filter removed the items whose
  wording favoured the label: it dropped every item all four judges got right from the options
  alone. Two cells keep an options-only signal above chance:
  - parallel engineering, 59.3% [50.4, 67.7];
  - detour research, 66.4% [54.8, 76.0], which on paired scoring (54.7%) is above five published
    models' full-context scores (three without parse problems: Mistral Medium 3.5, MiniMax M3,
    DeepSeek V4 Flash).
- **The cue, item by item (C2, R for this feature).** Within each construction, Haiku H1 is no
  more accurate on items where the rule points to the right answer:
  - `cont`, parallel: −5.0 points [−18.7, 9.1], placebo percentile 19.7;
  - `cont`, detour: −0.5 points [−11.1, 10.4], placebo percentile 39.8;
  - `ground`, detour: +10.3 [1.1, 19.5], placebo percentile 92.6. This is in the *opposite*
    direction to cue-following.

  Haiku picks the higher-overlap option in 54.2% of parallel and 51.5% of detour presentations.
- **The intervention (C2, L4, small).** Cutting the final step changes single-order accuracy by
  +3.3 points [0.0, 6.5] in detour cells and −3.5 [−7.1, 0.3] in parallel cells. The difference
  is +6.8 [1.8, 11.9], and 0.5% of bootstrap draws are ≤ 0. This is the pre-registered predicted
  direction. The end of the prefix pulls Haiku toward the shown trajectory's next step, and that
  costs it on detour items. The effect is a few points.

So the origin cue is a real hole (a model or a trained student could learn it), but Haiku's scores
are mostly decided by the option wording, not by the cue. Nothing here says how published models
behave item by item.

## Secondary results

**C4 Unparsed replies (L3).** All 14 leaderboard rows reproduce from the summaries (maximum
difference 0.05 points). The parser accepts only a final `ANSWER: X` line or a bare letter
(`src/tastebench/paired.py:80-87`). The table recomputes each score on parsed replies only. That
is exact for single-order accuracy. For paired accuracy it gives bounds, because the summaries do
not say which items had a failed presentation.

| Model | Unparsed / 1,004 | Published Average | Parsed-only Average (bounds) | Single-order, all / parsed |
|---|---|---|---|---|
| GLM-5.2 | 17 | 53.9 | 55.9–57.0 | 60.7 / 61.7 |
| GPT-5.4 Mini | 112 | 40.1 | 42.3–45.0 | 42.5 / 47.9 |
| Mistral Medium 3.5 | 24 | 37.7 | 39.9–41.5 | 53.5 / 54.8 |
| GPT-5.4 Nano | 93 | 36.6 | 40.7–43.9 | 46.6 / 51.4 |
| Grok 4.20 Reasoning | 459 | 15.7 | ≥ 32.8 | 34.5 / 63.5 |

- GLM-5.2's lower bound passes Claude Opus 5, Grok 4.5 and GPT-5.6 Terra (rank 6 to 3).
- GPT-5.4 Nano passes GPT-5.4 Mini and Mistral Medium 3.5.
- Grok 4.20 Reasoning, published below chance, answers 63.5% of the presentations it formats
  correctly. That equals GPT-5.6 Sol's single-order rate.
- The paper reports the unparsed counts and excludes these models from its SWE-bench comparison,
  so the mechanism is disclosed; its effect on the ranking is not. Parse failure need not be
  random, so the parsed-only numbers are an upper reading.

**C5 "Detour harder than parallel in both domains" (body.tex:178).**
- **Engineering:** the model mean is 22.1 points lower on detour items, in 14 of 14 models.
- **Research:** −0.1 points (50.8 against 50.9, the paper's own appendix numbers), and detour
  items are harder for only 7 of 14 models. The item-level interval for the model-mean difference
  is about ±19 points.
- The top two models are 11–12 points *better* on research detours.
- The claim holds for engineering only.

**C6 Precision (L3).**
- **Repeat run.** The paper ran GPT-5.6 Sol at the xhigh setting twice, with the same prompt and
  items: the main run (pooled 58.2%) and the effort rerun (55.6%; Tables 7 and 8). The two differ
  by 2.6 points, about 13 items, and by 5.4 points on the 219 "inferable" items. That difference
  exceeds 8 of the 13 adjacent gaps on the leaderboard.
- **Clusters.**
  - The 48 parallel-research items come from 8 tasks, and `ai_rd_fix_embedding/main` supplies 17
    of them.
  - The same task supplies 7 detour-research items: 24 of the 112 research items in all, carrying
    10.7 points of weight in the Average.
  - A research item weighs 3.5 times an engineering item.
- **Interval width.** The item-level 95% half-width of a model's Average is about ±5.0 points
  (±5.7 to ±6.8 if items within a task are correlated at 0.1–0.3). That is wider than 12 of the
  13 adjacent gaps. Paired comparisons between models would be tighter, but no per-item data
  exist to compute them.

**C7 Horizon gradient (R).**
- If accuracy depended only on the cell, each horizon level's mix of cells would predict 47.6,
  43.6, 41.8 and 44.0 (from "in prefix" to "more work"). The observed values are 62.3, 42.9, 31.5
  and 21.0.
- Composition explains 3.6 of the 41.3-point gap; the gradient is within cells.
- **Untested caveats.** The annotator (GPT-5.5) saw the answer when it judged the horizon. Ten of
  14 models score below 25% on the 69 "more work" items; under paired scoring that means
  consistent wrong choices, not guessing.

**C8 SWE-bench comparison (R).**
- **Reading the figure.** SWE-bench Verified values were read from the figure's vector data
  (`scripts/read_figures.py`); the Averages read back to within 0.04 points. They reproduce the
  paper's r = 0.63 (0.625) and its engineering r = 0.37 (0.366).
- **Residuals.** The largest positive residual is GPT-5.5 (+9.6), which wrote engineering
  trajectories and annotated the horizons. GPT-5.6 Sol's residual is +3.8.
- **Dropping them.** Without both models r = 0.687, the 69th percentile of the 55 drop-two values.
  The conclusion does not depend on the models that built the items.

**Exploratory, flagged.** The two Claude models have the largest research-minus-engineering gaps
(+17.6 and +14.6, against a median of +7.8). The exact permutation p for the pair is 0.018.
- This was noticed before the prereg.
- Claude and DeepSeek agents wrote the research trajectories.
- There are plain alternative readings: Claude may be better at ML research, or worse at detour
  engineering.
- GPT models show no matching engineering advantage (p = 0.50).

**C9 Options-only signal (L2, from the paper's own numbers).**
- **Funnel.** All four judges answered 1,080 of the 1,809 rubric-passing items (59.7%) correctly
  from the options alone. The rate ranges from 51% (detour engineering) to 69% (detour research).
- **After filtering.** On the released parallel-engineering items, GPT-4.1 still scores 63.7% from
  the options alone, in one shuffled order. GPT-5.4 Mini, Mistral Medium 3.5, GPT-5.4 Nano and
  Grok 4.20 score at or below that with the full prefix (single-order).
- **Which judge kept items in.** Llama 4 Maverick scores 34.7% on released items; its errors kept
  most of them in.

**C10 Labels and training claims (L1).**
- **Human review.**
  - Reviewers gave the 98.8% agreement after seeing outcome summaries. The figure also pools 15
    items the judge panel had removed as label-inconsistent.
  - There are only 2 disagreements in all 172 retained judgments. If those 15 items had the
    overall retention rate (86%), humans agreed with the label on at least 92% of judgments on
    items the panel rejected.
  - The statistic therefore cannot detect the defect it is cited against.
  - The reviewers' first-stage choices (made before seeing outcomes) would give a human baseline;
    they are not reported.
- **Sabotage runs.** Five of 64 detour-research prefixes contain an agent's stated plan to
  sabotage or sandbag the task. This is a keyword lower bound; ids are in
  `results/b1_inventory.json`. MALT includes such runs by design.
- **End-to-end.**
  - The no-advice and correct-advice rates are whole-task fractions: 14.6% = 6/41 and
    39.0% = 16/41.
  - The student-advice rate, 33.7%, is not a whole-task rate of 41. It needs at least 5 runs per
    task or a different denominator, and the paper states neither.
  - There is no base-model or random-advice control.
  - The advice contains both candidates, mined from earlier runs on the same task. The gain cannot
    be attributed to the student's judgment.
- **Distillation.** The training folds share the generator's option style and the origin cue with
  the test fold, so "transfers to unseen tasks" may be learning one of them. Untested.

**Truncation (null).** Using the harness's own token count (o200k_base × 1.02), no item exceeds the
65,536-token cap; the longest is 55,072 tokens.

## Robustness

| Check | Result | Does the claim survive? |
|---|---|---|
| Held-out tasks (direction set by prereg or on half 1) | `cont` 65.9% / 34.2%; floor Average 61.4 | Yes (C1) |
| Second feature definition (`ground`) | 63.6% / 34.9% held-out | Yes (C1) |
| Cluster-aware null (flip whole tasks; 1,000 draws) | p ≤ 0.01 for both constructions | Yes (C1) |
| Holm correction over 40 feature × cell tests | detour-engineering `ground` survives (p < 0.001) | Yes for that cell |
| Placebo splits for the Haiku cue strata (same sizes, cell and letter) | percentiles 19.7–92.6 | C2 remains R for the feature |
| By domain | cue strong in both engineering cells and in parallel research; weak in detour research | Partly |
| Haiku order effects | position-inconsistent items: H0 96, H1 70 of 502 | Paired and single-order both reported |
| Parsed-only bounds, conservative end | GLM-5.2's rank change holds at the lower bound | Yes (C4) |
| Repeat-run difference measured on pooled accuracy, gaps on the Average | the Average weights research items 3.5×, so the gap there is likely larger | Approximate (C6) |

## Alternative explanations

1. **The cue is the construct.** At a detour, a good engineer should prefer the step that is not
   "more of the same". But the same rule flips sign on parallel forks. A judgment that reverses
   with how the item was mined is tracking the mining. That is a validity problem whether or not
   a given model exploits it.
2. **Detour engineering is genuinely hard.** It may be. But Haiku is below chance there without
   any trajectory. Wording that makes the wrong option look better, together with a filter that
   keeps exactly such items, is enough to explain the cell. Hand reading suggests the labels often
   depend on sandbox details.
3. **Haiku is not representative.** Correct, and it limits C2 and C3. The cell pattern of Haiku
   with a short tail matches the published model mean closely (64.5/64.6/29.3/60.9 against
   58.1/50.9/35.9/50.8), but that is four numbers.

## What was already known

The paper discloses:
- the option origins, the generator, the judge panel and the funnel;
- the unparsed counts;
- the design of the human review.

No independent critique exists ([`prior_work.md`](prior_work.md)).

New here:
- the origin cue, with opposite signs by construction, and the content-blind rule above the
  leaderboard;
- the options-only below-chance result for detour engineering;
- the final-step intervention;
- parsed-only leaderboard ranks;
- the paper's own repeat-run pair set against the leaderboard gaps;
- the cluster weights;
- the failure of "detour harder in both domains" in research;
- the human-review arithmetic;
- the sabotage runs among the research items.

## What this does not show

- **That published models use the cue or the wording effect.** No per-item published logs exist.
- **That the labels are wrong.** They are real outcomes. The point is what else they carry.
- **Anything about Sonnet-scale or frontier behaviour.** All inference was Haiku.

## Inference

Claude Haiku (`claude-haiku-5-5`) through `audits/tools/claude_call.py`.
- **Calls and cost:** 3,008, costing 1.63 USD in total, of which H0 0.45, H1 0.58, H2 0.59 and the
  pilots 0.02. The ledger is [`inference/ledger.jsonl`](inference/ledger.jsonl).
- **What Haiku received:** only the query, the options, and at most 2,000 characters of the short
  prefix. Never a full prefix.

## Pins and how to reproduce

- **Dataset.** `wenbopan/taste-bench` at sha `069aa742…`. The parquet sha256s are engineering
  `377c6031…` and research `8528ca9f…`; the manifest is `ab2db9cc…` (all checked in
  `scripts/b_common.py`).
- **Access.** The dataset is gated: request access with your own account. Items are not reposted
  here, only ids, hashes, feature values and aggregates.
- **Code and paper.** Repository `wbopan/tastebench` at `b636e868`; paper source tarball sha256
  `675cebfd…`.

```bash
cd audits/taste-bench
git clone --depth 1 https://github.com/wbopan/tastebench data/repo
mkdir -p data/paper/src && curl -sL https://arxiv.org/e-print/2609.25804 | tar -xz -C data/paper/src
# gated: download data/hf/{export_manifest.json,data/*/test-00000-of-00001.parquet} at the sha above
uv venv data/.venv && uv pip install --python data/.venv/bin/python numpy pandas pyarrow scipy tiktoken
P="data/.venv/bin/python -I"
$P scripts/read_figures.py; $P scripts/a_aggregate.py          # Part A (no gated data)
$P scripts/b0_handread.py; $P scripts/b1_features.py; $P scripts/b2_floor.py; $P scripts/b6_tokens.py
$P scripts/b4_haiku.py H0; $P scripts/b4_haiku.py H1; $P scripts/b4_haiku.py H2; $P scripts/b5_score.py
$P scripts/make_results.py
```

Seeds are 0, with 1,000 permutations and 2,000 bootstrap draws. Every number above is in
[`results.json`](results.json).
