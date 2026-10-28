# ASMR-Bench: the 0.77 headline is the best of nine configurations and is not significant once that is accounted for

Status: checked on the released per-audit credences (2026-10-27). Two leads from the catalogue are
answered by the paper itself:

- **"A paper-only prior carries the AUROC."** The paper runs a paper-only condition and finds
  nothing above chance.
- **"The AUROC needs an interval."** Figure 2 has bootstrap error bars.

What remains is a multiple-comparison point and a file inconsistency. Not raised with the authors.

## Background

Gan et al., "ASMR-Bench" ([arXiv 2604.16286](https://arxiv.org/abs/2604.16286);
[code and results](https://github.com/ejcgan/auditing-sabotage-bench), MIT) ask auditors whether an
ML research codebase was sabotaged.

- **Data.** There are 9 source papers, each with one honest and one or two sabotaged variants
  (20 variants), all written by one human attacker.
- **Auditors.** Three LLM auditors (Claude Opus 4.6, GPT-5.2, Gemini 3.1 Pro), each under three
  affordances: paper only, no experiments, full experiments.
- **Headline.** "Gemini 3.1 Pro with full experiments achieves the best AUROC at 0.77 (p < 0.01)."

## Numbers

From [`asmr_checks.json`](asmr_checks.json), produced by [`check_asmr.py`](check_asmr.py) at commit
`f8efd68`.

The script reimplements the paper's metric independently:

- credences are averaged over trials in logit space;
- the AUROC is a Wilcoxon–Mann–Whitney statistic in which each variant is weighted by one over the
  number of same-label variants of its paper;
- persuasion variants are excluded.

It reproduces the headline exactly (0.772).

| | Value |
|---|---|
| Headline AUROC (Gemini 3.1 Pro, full experiments) | 0.772 |
| Exact stratified permutation p for that configuration alone | 0.009 (paper: p < 0.01) |
| Bootstrap 95% interval over the 9 papers | 0.61–0.95 |
| **Probability that the best of the nine headline configurations reaches 0.772 under random labels** | **0.084** |

The permutation tests enumerate all 1,152 ways of choosing which variant of each paper is the honest
one, so these p-values are exact rather than sampled.

The nine headline configurations score as follows:

| | Opus 4.6 | GPT-5.2 | Gemini 3.1 Pro |
|---|---|---|---|
| Paper only | 0.636 | 0.340 | 0.488 |
| No experiments | 0.531 | 0.580 | 0.593 |
| Full experiments | 0.543 | 0.630 | **0.772** |

The headline names the best of these nine, and its p-value is computed as if that configuration had
been chosen in advance. With 9 papers, the nine configurations share the same small set of
codebases, and the chance that at least one of them reaches 0.772 by luck is 8.4%. The appendix
adds seven more full-experiment models (0.54–0.72), which would raise the family-wise p further.

**A file inconsistency.** The released paper-only CSVs include 55 rows from 11 persuasion variants;
the other CSVs do not. The repository's CSV loader (`results/plot/data.py`) does not filter them.
Its codebase rule takes everything before the last underscore, so `awareness_lens_persuasion`
becomes its own "codebase" `awareness_lens`. Recomputing paper-only AUROC from the released files
with that loader shifts it slightly (0.636 → 0.608, 0.488 → 0.486, 0.340 → 0.364). This does not
change any conclusion.

## What it means

The benchmark's qualitative findings hold:

- the paper-only condition stays at chance, which rules out a pure "contradicts the literature"
  shortcut;
- fix rates are low;
- LLM-written sabotages are easier to fix.

The specific claim that a frontier auditor detects sabotage better than chance (0.77, p < 0.01)
rests on picking the best of nine configurations on 9 papers. Corrected for that choice, it is not
significant at the 5% level, and the interval runs from 0.61 to 0.95.

Readers should treat "frontier models detect sabotage above chance" as suggestive. The paper's own
caution that the benchmark is far from saturated stands. For safety claims the bias is **up**: a
sabotage monitor looks more reliable than the evidence shows.

## Reproduce

```bash
python check_asmr.py --cache data
```

Downloads the 19 result CSVs (about 2 MB) from the pinned commit into `data/` (gitignored) and
rewrites `asmr_checks.json`. Needs numpy and pandas. Reads the CSVs as data only.
