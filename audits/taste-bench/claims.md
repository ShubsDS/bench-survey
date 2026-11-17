# Taste-Bench: claims under test

Written 2026-11-17, before any per-model number was stratified or recomputed. Already read at
this point: the dataset card, the repository README leaderboard, the paper source (body,
appendix and generated tables), and the structure of one `summary.json`.

## Source, licence, pins

- Paper: Pan, Liu, Liu, Zeng, Lin, Tang, Lu, He, Jia, "The Tasteful Agent: Measuring and
  Improving Taste in Long-Horizon Tasks", arXiv 2609.25804 (v1). Source tarball sha256
  `675cebfd7d59a89f1fc0bbf25056e7f36eadeb3039c82313b9b375f3314726b8`, unpacked to
  `data/paper/src/` (git-ignored).
- Code, protocol and per-model results: github.com/wbopan/tastebench, MIT, commit
  `b636e868ff04b640c3ab94ad3160ed328dbd6256` (2026-09-23). Per-model
  `results/<model>/summary.json` files hold per-cell aggregates (seeded and reversed accuracy,
  parsed, errors, unparsed, the CC/CW/WC/WW paired counts, letter choices, token usage and
  truncation counts). **No per-item or per-response records are released.**
- Dataset: `wenbopan/taste-bench`, sha `069aa74210c8daf586527c0eb8ab511a343acf42`, CC-BY-4.0,
  auto-gated. Card sha256 `21db0918…7fc1`. The parquet files and `export_manifest.json` return
  403 with this machine's login (gate not accepted; we did not accept it).
- Upstream research trajectories: `metr-evals/malt-public` sha `6100006c…`; the existing login
  reaches it (HTTP 200). Not downloaded (4.0 GB; it cannot be linked to Taste-Bench items without
  the gated item text).

## Construction facts that matter (paper appendix A, quoted by section, not by item)

- Engineering trajectories: 2,677 rollouts by **GPT-5.4 and GPT-5.5** agents on 517 SWE-bench Pro
  tasks. Research: 1,132 MALT runs by Claude 3.5/3.7 Sonnet, Claude Sonnet 4, Claude Opus 4 and
  DeepSeek V3 agents on 47 tasks.
- Both candidate texts of every item are written by a **generator, GPT-5.6 Sol at high effort**,
  which sees the full trajectory and outcome and knows which option is the good one.
- Filter panel: Kimi K2.5, GPT-4.1, Llama 4 Maverick, Mistral Large 3. Trivial filter: one
  options-only answer per judge in one shuffled order; an item is dropped when **all four** are
  right. Undecidable filter: an item is kept only when **all four** judges, shown the prefix, both
  full continuations and the grader outcomes, pick the label.
- Funnel (Figure `filtering_funnel.pdf`, read from its embedded text): 4,657 mined → 1,809 pass
  the generator rubric → 729 survive the trivial filter → 502 released.
- Parallel items: the shown prefix is the **supported (passing) attempt's** history, so the
  correct option is the shown trajectory's own next step. Detour items: the shown prefix is the
  trajectory just before it takes the **abandoned** direction, so the wrong option is the shown
  trajectory's own next step.
- Time-horizon levels are annotated by **GPT-5.5**, shown the correct answer.
- Leaderboard models related to the construction: GPT-5.6 Sol (generator, rank 1), GPT-5.5
  (engineering trajectory author and horizon annotator, rank 2), GPT-5.4 Mini/Nano (same series
  as the other engineering author), GPT family generally (GPT-4.1 judge), Mistral Medium 3.5
  (Mistral Large 3 judge), Claude Opus 5 and Sonnet 5 (family of the research trajectory authors),
  DeepSeek V4 Flash (DeepSeek V3 research trajectories).

## Conclusion 1. The ranking and its headline: "the best model answers only 59.7%"

- Statement: abstract and §4.2: GPT-5.6 Sol 59.7%, GPT-5.5 59.5%, others "widely dispersed
  below"; Finding 1, "current frontier models show limited taste". README leaderboard, 14 rows.
- Who relies on it: the public leaderboard (models are added by PR), press coverage quoting
  59.7%, anyone choosing a model as an agent "advisor".
- What would change it: (a) the leaderboard rows depend on parse failures, not choices;
  (b) run-to-run or task-cluster noise is as large as the gaps between adjacent rows; (c) the
  rank-1 and rank-2 models are the ones that built the items, and the advantage is specific to
  the items they built.

## Conclusion 2. The structure of difficulty

- 2a. "Detour forks are harder than parallel forks in both domains, and this gap exceeds the gap
  between the two domains" (§4.2; Appendix C.1 gives model means P-Eng 58.1, P-Res 50.9,
  D-Res 50.8, D-Eng 35.9). Read as "detour requires recognising a mistake before the agent did".
  Would change: the gap is absent in a domain, or it follows from which option is the shown
  trajectory's own next step (a construction artefact) rather than from judgment.
- 2b. Finding 2: accuracy falls with time horizon (62.3% in-prefix → 21.0% more-work, near the
  25% of guessing), so "answering the questions requires predicting the later work". Would
  change: the gradient comes from cell composition, or the "more work" level is consistently
  answered wrong (below chance by preference) rather than guessed.
- 2c. Finding 3: a larger reasoning budget does not change accuracy (Sol −0.2, Luna +2.2 points).

## Conclusion 3. Taste is not a restatement of end-to-end ability

- Statement: §4.4, Pearson r = +0.63 between Average and SWE-bench Verified over 11 models,
  r = +0.37 on the engineering subset; GPT-5.5 is 8th on SWE-bench Verified and 2nd here.
- Would change: the deviations from the fit are the models that built the items (GPT-5.6 Sol,
  GPT-5.5), so "taste ≠ SWE ability" is partly "relation to the construction".

## Conclusion 4. Labels are valid; taste can be trained

- 4a. Human review: 170 of 172 explicit judgments (98.8%) agree with mined labels, κ = 0.973.
  Would change: the agreement is measured after showing the outcome, and pools items the panel
  had rejected as label-inconsistent, so it cannot detect the defect it is cited against.
- 4b. Distillation: held-out student 47.9% vs base 30.0% (+17.9 points); end-to-end success with
  student advice 33.7% vs 14.6% without and 39.0% with correct advice (41 tasks). Would change:
  the gain is learnable from option wording (the generator's style is shared across folds), or
  the end-to-end comparison lacks the control that isolates the student's judgment.

## Trait scores (METHODOLOGY "Traits that predict a broken headline")

| Trait | Present? | Note |
|---|---|---|
| 1 Label from a process | Yes | Later outcome; options written by a generator that knows the label |
| 2 Items kept by model behaviour | Yes, twice | Trivial filter (≥1 of 4 judges wrong options-only); undecidable filter (all 4 agree with label in hindsight) |
| 3 Headline near chance | Partly | 25% chance; scores 37–60%; "more work" level 21% |
| 4 Few independent units | Yes | P-Res: 48 items from 8 tasks; research (112 items, ≤30 tasks) is half the Average |
| 5 Two free-text options | Yes | 52–69% of rubric-passing items were solved unanimously from options alone |
| 6 LLM judge on subjective criterion | Yes | Filters and horizon annotation are LLM judgments |
| 7 Scorer assumes model told something | Minor | Strict last-line `ANSWER: X` parse |
| 8 Best number from easiest condition | Possible | Parallel engineering is the easiest cell and the largest model gaps |
| 9 One bucket holds unlike cases | Yes | "Wrong" holds unparsed replies: 459 of 1,004 for Grok 4.20 |
| 10 Units of varying size | Possible | Prefix length; truncation hit 1 item for 2 models |
| 11 Key unbalanced | Neutralised | Paired order cancels letter lean |
| 12 Little scrutiny | Yes | Released September 2026; one GitHub issue, no critique found |
