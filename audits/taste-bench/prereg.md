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
