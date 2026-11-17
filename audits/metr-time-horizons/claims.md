# METR time horizons: claims under test

Written 2026-11-17, before any stratified analysis of model outcomes. A point-estimate fit on the
full set was run first, only to confirm the pins reproduce the published numbers (see `prereg.md`).

## Source, licence, pins

- Paper: Kwa et al., "Measuring AI Ability to Complete Long Tasks", arXiv 2503.14499 (March 2025).
- Update: METR, "Time Horizon 1.1" (29 January 2026), https://metr.org/blog/2026-01-29-time-horizon-1-1/,
  and the modelling note of 20 March 2026 that removed an unintended regularisation
  (https://metr.org/notes/2026-03-20-impact-of-modelling-assumptions-on-time-horizon-results/).
- Code and run data: github.com/METR/eval-analysis-public at commit
  `52cb829c7a2efb2d659285c4b1768d191d97f8d2` (shallow clone, 2026-11-17). The repo has no LICENSE
  file in the clone; it is public and the README asks for citation. We use it for analysis only and
  commit no rows.
  - `reports/time-horizon-1-1/data/raw/runs.jsonl` sha256 `609f904f…b55cd` (24,008 runs, 21 aliases incl. `human`)
  - `reports/time-horizon-1-0/data/raw/runs.jsonl` sha256 `f489d117…11236`
  - `data/external/release_dates.yaml` sha256 `317b9291…bc`
- Published numbers: https://metr.org/assets/benchmark_results_1_1.yaml (sha256 `aae31902…2ad9`) and
  per-task success counts https://metr.org/assets/task_results_1_1.yaml (sha256 `4f85fbf0…6b07`),
  fetched 2026-11-17. The task file covers 23 agents (three more than runs.jsonl: Gemini 3.1 Pro,
  GPT-5.4, Claude Mythos Preview (early)).

## Conclusion 1: the 50% horizon of frontier AI doubles every ~4 months since 2023 (~7 months since 2019)

- Number: from 2023 on, **128.7 days, 95% CI [104.4, 158.0]** (`benchmark_results_1_1.yaml`,
  `doubling_time_in_days.from_2023_on`, post-March-2026 fix; the January blog gave 130.8 [107, 161]).
  All-time stitched: 187.8 days (no CI). The paper's original headline: 7 months (212 days in v1 of the paper; 207 days in the HTML version).
- Who relies on it: METR's public "time horizons" page and graph; the AI 2027 timelines forecast,
  which extrapolates the METR horizon trend to a superhuman-coder milestone; frequent use in lab and
  government discussion of when AI could automate AI R&D (e.g. the trend is cited as evidence of
  accelerating autonomy in frontier-model system cards and safety reports).
- Decision it feeds: how soon to expect AI agents that complete week- or month-long software and
  research tasks, i.e. timelines for AI R&D automation thresholds.
- What would change it: a doubling time estimated with the confound removed (within one task
  source, with source fixed effects, or on baselined tasks only) whose 95% interval for the ratio to
  the published value excludes 1, or whose point estimate falls outside [104.4, 158.0].

## Conclusion 2: each frontier model's 50% horizon, and their ordering

- Numbers (minutes, 95% CI, same file): Claude Opus 4.6 718.8 [316.7, 3633.8]; GPT-5.2 352.2
  [198.1, 815.2]; GPT-5.3-Codex 349.5 [194.9, 816.4]; Claude Opus 4.5 293.0 [161.7, 623.7];
  Gemini 3 Pro 224.3 [139.6, 379.2]; GPT-5 203.0 [112.6, 405.6]; o3 119.7 [74.6, 190.9].
- Who relies on it: model announcements and press ("Opus 4.6 can do 12-hour tasks"), comparisons
  between labs, capability thresholds in frontier safety frameworks that refer to autonomous
  task length.
- What would change it: a confound-free horizon for a frontier model whose ratio to the published
  value has a 95% interval excluding 1, or a change in which model is ranked first.

## Conclusion 3 (secondary): horizons depend on human time, not on which suite a task came from

This is an implicit assumption, not a stated number: the method pools SWAA (seconds), HCAST
(minutes to hours) and RE-Bench (8 hours) on one logistic curve in log human time. The paper
reports the non-SWAA 2023–25 trend (172 days) as a robustness check. What would change it: a source
effect on success at fixed human time whose interval excludes 0, large enough to move Conclusions 1
or 2.
