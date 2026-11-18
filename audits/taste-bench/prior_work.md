# Taste-Bench: prior work and existing critiques

Searched 2026-11-17: the paper (body, appendix; it has no limitations section), the GitHub
repository's issues and pull requests (API, unauthenticated), the Hugging Face dataset
discussions, and web searches for "Taste-Bench", "Tasteful Agent", the arXiv id together with
LessWrong / Alignment Forum / critique / replication.

## About Taste-Bench itself

| Source | What it shows | Overlap with this audit |
|---|---|---|
| Paper, §3.3 and App. A.4–A.6 | Discloses both filters, the judge panel, the funnel counts, and the judges' options-only accuracy on parallel engineering (proposed 75.6–85.8%, released 34.7–63.7%) | We use these numbers. The paper does not draw the consequence that an old model (GPT-4.1) still answers 63.7% of released parallel-engineering items from the options alone, nor discuss regression to the mean |
| Paper, App. A.5 | States that the generator is GPT-5.6 Sol and that engineering trajectories are GPT-5.4/5.5 | Disclosed; the paper does not connect it to the ranking or to the SWE-bench comparison |
| Paper, App. B / Table 5 | Reports unparsed counts per model and excludes three models from the SWE-bench comparison for >9% unparsed | Disclosed; the leaderboard still ranks those rows. We quantify the parsed-only accuracies |
| GitHub issue #1 (2026-10-17, open, no replies) | A research question on how much hindsight evidence is needed before a label is stable | Related to label validity; no data or analysis |
| HF dataset discussion #1 | Bot parquet conversion | None |
| Press and aggregator summaries (aiweekly.co, digg, explainx.ai, hyper.ai, developersdigest) | Restate the 59.7% headline | None critical |

No independent re-run, critique, or per-item analysis of Taste-Bench was found.

## Related critiques (other benchmarks, same failure modes)

- Zhong, "LLMs are weirdly below chance on TASTE without a shortcut", LessWrong, 2026-11-15
  (https://www.lesswrong.com/posts/tpKE33scJGzqYKEBW/). A *different* benchmark (Anthropic-style
  safety-proposal TASTE, cited by this paper as `baig2026taste`). Shows a topic shortcut and
  below-chance accuracy on shortcut-free items. Method template for our Phase B.
- This project's APPS backdoor result (`../../scope.md`): classes written by different sources are
  predictable without reading the substance. Taste-Bench options are both written by one
  generator, but it writes them knowing which is good.
- Wu et al., "How to Build a Benchmark That Actually Measures Taste", arXiv 2610.14707 (an
  unrelated "TasteBench" on visual/brand items): position and lexical leakage in pairwise taste
  data. Not about this benchmark.
- Trott, "We should be cautious about LLM-generated benchmarks" (Substack): general argument.
- Adversarial filtering and its artefacts (e.g. the AFLite / HellaSwag line of work): filtering by
  model failure produces sets on which filter-related models are biased low. General background,
  not tested here on Taste-Bench before.

## What is new in this audit

1. The option-only signal arithmetic from the paper's own funnel (59.7% of rubric-passing items
   unanimous from options alone) and the comparison of released-item options-only judge
   accuracy with published full-context model accuracy.
2. Parsed-only recomputation of the leaderboard from the released `summary.json` files.
3. The paper's own test–retest pair (GPT-5.6 Sol at xhigh, main run vs effort rerun) set against
   leaderboard gaps; the cluster structure (8 tasks behind P-Res) against the Average's weights.
4. The cell-composition check of the horizon gradient (a null), the research-domain check of
   "detour harder in both domains", and the construction-relation pattern in the SWE-bench
   comparison and in the domain gaps.
5. The human-review agreement statistic's insensitivity to the defect it is cited against.
6. Item-level tests after the gate was opened by the repository owner: the option-origin cue,
   the options-only below-chance detour-engineering result, and the final-step intervention.
