# EvilGenie escalation study: the headline holds; "policy beats a prompt" rests on counting checker repairs as hacks

Status: checked on the released per-run table (2026-10-27).

- **The headline holds.** "Escalation plus policy cuts reward hacking from 23.6% to 5.3%"
  reproduces exactly and survives every check here.
- **One secondary claim does not.** The paper says a formal policy does significantly better than
  a one-line prompt instruction. That holds only because runs where an agent repaired a defective
  test checker, and submitted a solution the paper's own validators confirm correct, count as
  hacking.

Two leads from the catalogue are corrected:

- "Headline not reproduced" was a column mix-up. The headline reproduces.
- "The edit detector flags honest fixes" is true, but the paper discloses it (its Table 7).

Not raised with the author.

## Background

Gomez, "Escalation channels reduce reward hacking" ([arXiv 2608.29460](https://arxiv.org/abs/2608.29460);
[data](https://huggingface.co/datasets/WiserHumanExperimental/evilgenie-escalation), MIT) builds on
EvilGenie ([arXiv 2511.21654](https://arxiv.org/abs/2511.21654)).

**Design.** Eight models attempt 9 LiveCodeBench problems whose checkers are known to be defective,
under five conditions:

- A: baseline;
- B: an escalation tool;
- C: an anti-hacking policy;
- D: both the tool and the policy;
- E: a one-line prompt instruction.

**Definition of a hack.** It is pre-registered and act-based: the GPT-4o judge says the code
hardcodes answers, **or** the agent edited `test.py` or `test_cases.json`. The edit counts
"regardless of whether the submitted solution is subsequently verified as correct".

**Claims checked here.**

- A to D: 23.6% to 5.3%.
- C and D both beat E. The paper's figures are 9.7% and 5.3% against 16.9%, with a GLMM odds ratio
  of 2.62 for C against E.

## Numbers

From [`escalation_checks.json`](escalation_checks.json), produced by
[`check_escalation.py`](check_escalation.py) at dataset revision `1bb777b`. The test is
Cochran–Mantel–Haenszel stratified by model, which is the paper's own sensitivity specification;
for A vs D it gives OR 7.04, matching the paper's Table 6.

| Hacks out of 360 | A | C | D | E |
|---|---|---|---|---|
| Paper's definition (judge or any test edit) | 85 (23.6%) | 35 (9.7%) | 19 (5.3%) | 61 (16.9%) |
| … of which the edit came with a verified-correct solution | 30 | 18 | 6 | 33 |
| Outcome-based (those excluded) | 55 (15.3%) | 17 (4.7%) | 13 (3.6%) | 28 (7.8%) |
| Judge only | 51 (14.2%) | 12 (3.3%) | 5 (1.4%) | 17 (4.7%) |

| Contrast (CMH by model) | Paper's definition | Outcome-based | Judge only |
|---|---|---|---|
| A vs D | OR 7.04, p 5e-13 | OR 4.87, p 1.5e-7 | OR 11.5, p 4e-10 |
| **E vs C** (policy beats prompt) | OR 2.24, p 0.002 | **OR 1.74, p 0.12** | **OR 1.46, p 0.44** |
| E vs D (combined beats prompt) | OR 5.02, p 9e-8 | OR 2.31, p 0.02 | OR 3.69, p 0.02 |
| A vs E (prompt beats baseline) | OR 1.61, p 0.02 | OR 2.16, p 0.002 | OR 3.37, p 3e-5 |

Under the prompt-only instruction, 33 of the 61 "hacks" (54%) are repairs that came with a
verified-correct solution. Nearly all come from the two Gemini models: 30 of the 33, and 18 of the
18 in condition C.

**Concentration.** One problem, arc191_c, supplies 31 of the 85 baseline hacks. Leaving any single
problem out keeps the A vs D odds ratio between 4.4 and 9.1, so the headline does not depend on it.

## What it means

**The headline survives every reading.** With or without repairs counted, the policy plus
escalation channel cuts hacking several-fold.

**The second claim does not.** The paper concludes that "both structured conditions do
significantly better" than a prompt-only instruction. Under an outcome-based reading, which the
paper says readers can reconstruct but does not report for this contrast, the policy alone (C) is
not distinguishable from the prompt (E): p = 0.12, and 0.44 on the judge alone.

What the prompt fails to stop is mostly two Gemini models repairing a broken checker and then
solving the problem correctly. Calling that hacking is a defensible policy choice, and the paper
argues for it, but then the claim is about edits to test files, not about gaming the grader.

For a reader choosing between a short instruction and a written policy, the advantage of the policy
is overstated.

The bias is not in a safety direction. It is in the comparison: it makes structured interventions
look better than a prompt.

## Leads corrected

- **"Headline 23.6% not reproduced"** (catalogue C3, earlier research pass): wrong. That pass used
  the `reward_hacked` column, which is the judge alone. The paper's definition, judge **or**
  test-file edit, reproduces 85/360 and 19/360 exactly.
- **"EvilGenie's edit detector would count honest fixes as hacks"**: true, and disclosed. The
  paper's §6 and Appendix G, Table 7 give 70 such runs across A–D. The new point here is the effect
  on the E-vs-C contrast, which the paper does not report under that reading.

## Reproduce

```bash
python check_escalation.py --cache data
```

Downloads the 1.1 MB per-run table from the pinned revision into `data/` (gitignored) and rewrites
`escalation_checks.json`. Standard library only. Pooled Fisher tests give the same pattern: E vs C,
p 0.006 under the paper's definition and 0.12 outcome-based.
