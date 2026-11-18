# Taste-Bench: pre-registration

Committed 2026-11-17 before any script below was run. What had been seen: the published
leaderboard and appendix tables (per-cell accuracy per model, the horizon-by-model table, the
effort table, the judge table, the funnel figure), and one `summary.json`. Nothing had been
recomputed, stratified by a feature, or split by parse status.

Item-level data are gated and closed to us (see `claims.md`). Part A uses only released
aggregates. Part B is written now, for the item-level data, and is run only if the gate opens.

## Part A: tests on released aggregates

Inputs: the 14 `results/*/summary.json` at repo commit `b636e868`, and paper tables read from
`data/paper/src/` (numbers typed into `scripts/paper_numbers.py` with the source file and line).
Figure values read from PDF vector data are labelled "read from figure".

A1. **Reproduce.** Recompute every leaderboard row (Average, four cells, unparsed) from the
summaries. Holds if all 14 rows match to 0.05 points.

A2. **Unparsed bucket (trait 9).** Per model and cell: exact single-order accuracy among parsed
presentations; bounds on paired accuracy among items with both presentations parsed,
CC / (n − k) with k ∈ [max(u_s, u_r), min(n, u_s + u_r)]; the parsed-only Average from those
bounds. *Changes* if, for some model, the parsed-only lower bound exceeds the published Average of
a model ranked ≥ 2 places above it, or a model published below 25% is above 25% on its lower
bound. Otherwise *holds*.

A3. **Options-only signal (traits 2, 5).** From the funnel: share of rubric-passing items dropped
as trivial, per cell. From the judge table: compare GPT-4.1's options-only single-order accuracy
on released parallel-engineering items (63.7%) with each model's full-context single-order mean
accuracy on that cell. Report the count of models at or below it. This is L2 at most: the judge
saw one shuffled order, and its released-item accuracy is post-selection (biased down).

A4. **Test–retest.** GPT-5.6 Sol at xhigh appears twice: the main run (Table 6 per-level values)
and the effort rerun (Table 8). Statistic: difference in pooled both-orders accuracy and per
level. *Changes* (for "the ranking orders models") if the same-setting difference exceeds the
Average gap of at least 5 of the 13 adjacent leaderboard pairs.

A5. **Clusters (trait 4).** Item-level analytic 95% half-width of each model's Average; the
influence of one parallel-research task (6 items on average) on the Average; design-effect
scenarios ICC ∈ {0.1, 0.3} using the paper's per-cell task counts. Reported as sensitivity, not as
a finding.

A6. **Horizon gradient vs cell composition.** Predicted accuracy per horizon level if accuracy
depended on cell only: Σ_cell n(cell, level) · acc(model, cell) / n(level), averaged over models.
*Changes* if the predicted in-prefix − more-work gap is ≥ half the observed gap (41.3 points).
Otherwise *holds* (R).

A7. **"Detour harder in both domains."** Model-mean D − P per domain, count of models with D < P,
and an item-level 95% interval for the model-mean difference. *Holds in a domain* if the
interval excludes 0 in the stated direction; *fails* if the point estimate is within ±2 points
or the count is ≤ 9 of 14.

A8. **Taste vs SWE-bench Verified and construction relation.** Pearson r over the paper's 11
models (SWE-bench values read from the figure). Recompute r dropping GPT-5.6 Sol and GPT-5.5
(generator; trajectory author and annotator) and compare with r after dropping every other pair
of models (55 pairs). *Changes* if dropping the construction pair raises r above the 90th
percentile of the drop-any-pair distribution. Also report each model's residual.

A9. **Domain gap by family (exploratory, flagged).** The Claude models' large research −
engineering gap was noticed while reading the leaderboard, before this prereg. Permutation test
over models of whether the two Claude models' gaps exceed the others; reported as exploratory
whatever the p-value.

A10. **Human review and end-to-end arithmetic.** Bounds on human agreement on the 15
undecidable-removed items from the published counts; whether the end-to-end success rates are
whole-task fractions of 41.

## Part B: item-level tests (blocked; run only if the gate opens)

Unit of resampling: `task_id` (clusters), within cell. All nulls: 1,000 permutations that flip
the correct-option side for whole tasks (all items of a task flipped together), seed 0.
Held-out: split tasks 50/50 within cell (seed 0); any threshold or direction is chosen on half 1
and scored on half 2.

B1. Inventory: items, distinct `task_id`, distinct prefix hashes (proxy for trajectories) per cell;
must match the paper's Table 4 (tasks 62/8/133/22). Answer letter balance by cell.

B2. Option form features, computed per option, then as (correct − other):
- length in characters and words;
- specificity: count of path-like tokens, `code` spans, identifiers (snake/camel case), numbers;
- verification words (first, check, inspect, read, verify, confirm, test, reproduce, run) minus
  commitment words (implement, patch, add, replace, special-case, hardcode, remove, rewrite);
- hedging words (may, might, if, whether, consider);
- prefix grounding: share of the option's identifier tokens that appear in the prefix; and
  token overlap (Jaccard) with the last 3,000 characters of the prefix (the "continuation" score).
Each rule "pick the option with the higher feature" is scored per cell; it is order-invariant, so
its paired accuracy equals its single-order accuracy (ties count as wrong).

B3. **Main hypothesis (label validity, trait 1).** The continuation score predicts the label
*positively* in parallel cells and *negatively* in detour cells (both follow from which option is
the shown trajectory's own next step). Statistic: rule accuracy for "pick higher continuation"
per construction, held-out half, cluster-permutation p. *Confirmed* if parallel > 0.5 and detour
< 0.5, each with p < 0.05 on the held-out half.

B4. **Options-only Haiku baseline.** `claude_call.py`, Haiku, query + two options, no prefix,
both orders, prompt as the paper's trivial filter. Pilot 10 items; full run if the projected cost
≤ 1.5 USD. Then the same with the last 2,000 characters of `prefix_text_short`. Reported as one
small model's behaviour, not as a published model's.

B5. **Effect on published conclusions (L3 needs per-item model logs, which are not released).**
With aggregates only, B5 is limited to: cell accuracy of each published model against the share
of items in the cell where the B3 rule applies. If per-item logs appear, test whether the P − D
gap per model shrinks on items where the continuation score does not separate the options
(|difference| below the median), with a placebo split of the same sizes and answer mix.

B6. Robustness: drop each task in P-Res; second feature definition (character 5-gram overlap
instead of tokens); placebo feature (option position in the published order); Holm correction
over the B2 rules.

## Amendment 1 (2026-11-17): exact item-level plan, committed before the parquet files were downloaded

The gate was opened by the repository owner during the audit (HTTP 200 confirmed with the
existing token). This amendment fixes every item-level definition before any item is read.
Part A had already been run; one Part A analysis was added after the prereg and is flagged as
such in the write-up (A2b, single-order accuracy below 50% by cell, from the summaries).

**Data handling.** Download both parquet files and `export_manifest.json` at sha `069aa742…`
into `data/hf/`; record sha256 of each file and check them against the manifest. Commit ids,
hashes, feature values and aggregates only. Haiku receives the query and options, or a
hard-truncated prefix tail (≤ 2,000 characters of `prefix_text_short`), never a full prefix.

**B0 hand read.** 50 items (seed 0; 13 per cell, 12 for parallel research), read before any
feature is computed. Notes stay in `data/`; the committed summary uses item ids and counts only.

**B1 inventory (exact).** Per cell: items, distinct `task_id`, distinct sha256 of the first 4,000
characters of `prefix_text` (trajectory proxy), `prefix_steps` median, answer letter and
`answer_index` counts, `source` counts. Holds if task counts equal 62/8/133/22.

**B2 features (exact).** Text lower-cased where noted. For each option:
`len_chars`; `len_words` (whitespace split); `n_paths` = matches of
`[\w.-]*/[\w./-]+` plus `\b\w+\.(py|js|ts|tsx|jsx|go|rs|java|rb|json|ya?ml|toml|md|txt|sh|cfg|ini|html|css|c|h|cpp)\b`;
`n_code` = backtick spans; `n_ident` = `\b[a-z]+_[a-z0-9_]+\b`, `\b[a-z]+[A-Z]\w*\b`, `\b\w+\(\)`;
`n_num` = `\b\d+(\.\d+)?\b`; `verify` = count of {first, check, inspect, read, verify, confirm,
test, tests, reproduce, run, investigate, examine, look} minus count of {implement, patch, add,
replace, special-case, hardcode, hard-code, remove, rewrite, modify, change, edit};
`hedge` = count of {may, might, if, whether, consider, possibly}; `ground` = share of the option's
tokens of ≥ 4 alphanumeric characters (lower-cased, minus a fixed stop list) that occur in the
lower-cased `prefix_text`; `cont` = Jaccard of the sets of ≥ 3-character alphanumeric lower-case
tokens of the option and of the last 3,000 characters of `prefix_text`.
Rule for feature f: pick the option with the higher f; ties are wrong. Reported per cell:
full-set accuracy of "higher" (and therefore of "lower" = 1 − acc − ties).
Held-out: tasks split 50/50 within cell (seed 0); direction chosen on half 1, scored on half 2.
Null: 1,000 permutations, each flipping the correct side for all items of a task together
(seed 0); two-sided p = share of permuted |acc − 0.5| ≥ observed. Holm over features × cells.
A form shortcut is **L2-confirmed** in a cell if held-out accuracy ≥ 0.60 with Holm p < 0.05.

**B3 (main, unchanged in substance).** `cont` and `ground` predict the label positively in the
two parallel cells and negatively in the two detour cells. Confirmed per construction if the
pooled-construction held-out accuracy is > 0.5 for parallel and < 0.5 for detour, each with
one-sided cluster-permutation p < 0.05.

**B4 Haiku runs** (`claude_call.py`, Haiku only, temperature default, answers parsed as the
last `ANSWER: X` line, otherwise a bare letter; unparsed = wrong and counted).
- H0 options only: the paper's trivial-filter user message and judge system message, both
  orders (published and reverse), all 502 items.
- H1 tail: the paper's evaluation prompt with `{prefix}` = last 2,000 characters of
  `prefix_text_short`, both orders.
- H2 intervention (L4, only if budget remains after H0 and H1 at ≤ 2.4 USD): as H1 but with the
  final rendered step removed (cut at the last line starting with `[` followed by a digit), both
  orders. Prediction under the continuation account: detour accuracy H2 > H1 and parallel
  H2 < H1.
Pilot: 10 items × 2 orders for H0, measure cost per call, then size. Statistics per cell:
single-order and paired accuracy, 95% task-cluster bootstrap (2,000 draws, seed 0).
Selection reading of H0: paired accuracy below 25% or single-order below 50% with the interval
excluding it is reported as a *selection* result (the filter removed options-only-easy items),
not as "no shortcut". H0 above 50% single-order with interval excluding 50% is an L2 options-only
shortcut surviving the filter.
L3/L4 statement for Haiku only: logistic regression of H1 per-presentation correctness on
`cont` difference (correct − other) × construction, task-clustered bootstrap; and the H2 − H1
difference per construction. No statement about published models from Haiku.

**B5 published models.** Per-item logs are not released, so item-level L3 on published models is
not possible. Cell-level only: correlate each cell's share of items where B3's rule points to the
right answer with the model-mean cell accuracy (4 points; descriptive).

**B6 scoring and length.** Token count of the full rendered evaluation prompt with tiktoken
`o200k_base` × 1.02 (the harness's own preflight); count items over 65,536 per cell; Haiku H1
accuracy by `prefix_text` length tercile. Placebo split for any stratified Haiku result: 1,000
random splits of the same sizes within cell and answer letter, report the percentile.
