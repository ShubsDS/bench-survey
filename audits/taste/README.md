# TASTE: the critique's capability trend survives a label-blind placebo split, but "below chance" does not set it apart, and its "every strong model" and "beyond OpenAI" parts are fragile

Status: complete (desk audit), 2026-11-17, branch `audits-round2`. Not yet independently validated.

**Access: Case B (published tables, figures and prose only).** The benchmark, labels, proposal text
and per-pair model logs sit behind the authors' Google form, which this audit did not submit. The
critique's code, term counts and per-pair results are not public: the author offers them by DM only
to people with dataset access. No copy exists on Hugging Face or GitHub (searched; the existing HF
login opens nothing relevant). The one third-party repository that uses TASTE returns 404. What
could be analysed:
- the paper's Table 3, Table 5 (per-model accuracy by pair type and prompt variation, 19 models),
  Figures 12, 13 and 19 (magnet-free accuracy) and App. C;
- the critique's prose, and its Figure 2, digitised by marker colour for 28 models × 4 panels;
- Epoch's ECI file.

Every number below is labelled with its source: **[paper]**, **[critic]**, **[digitised]** (read
from the critic's chart, ±0.5 points), **[mine]** (computed by this audit from those numbers) or
**[sim]** (synthetic benchmarks with the published structure; not TASTE data). No model was run:
inference spend is 0 USD.

| Claim | Result | Level |
|---|---|---|
| Critique C3a: on the 52 ties, 14 of 14 models with ECI > 158 are below 50% | Reproduced [digitised]. But a label-blind 52-pair subset the paper itself publishes (magnet-free) also puts 13 of 19 models below 50% [paper], the same count as the ties for those 19 models. If the 18 within-prompt pairs (a failure the paper already reports with the question shown) all sit in the ties, 3 of the 6 paper models above ECI 158 return to ≥ 50% [mine] | Below-chance counts are **not specific** to the split; "every strong model" is **fragile** |
| Critique C3b: tie accuracy falls with ECI, r = −0.60 | Reproduced: −0.60 [−0.80, −0.30], n = 28 [mine from digitised]. The label-blind magnet-free subset gives **+0.39** [−0.08, 0.72] [mine from paper]. The trend holds without Haiku 4.5 (−0.53), with family fixed effects (p = 0.004) and in the within-prompt worst case (−0.51, 19 paper models). The split-and-tuning simulation produces the pattern in ≤ 2.75% of runs, never at the observed size [sim] | **R** for the split-artifact explanation: the trend survives |
| Critique: the trend holds without OpenAI (r = −0.57) | Without OpenAI **and** Haiku 4.5: −0.41 [−0.74, 0.07], p = 0.09 (n = 18). Within Anthropic without Haiku: −0.30 [−0.76, 0.37] [mine] | **Fails as worded**: outside OpenAI it rests on one model |
| Critique C2: the "fewer interp terms" rule's 63.0% is evidence of a topic confound | With labels fixed by 50 proposal scores, a random topic rule written down in advance reaches 62% at the 95th percentile of a no-confound null. The best of 5 candidate themes reaches 68% [sim] | **Weakened**: 63.0% alone is not evidence; the 80% on the 40 decided pairs rests on ≥ 4 proposals |
| Paper C1: Fable 5 60% vs experts 77% | With a proposal-level share of noise ρ ≥ 0.25, 60% is not distinguishable from 50% (null P(≥ 60%) = 7–16%), and the gap's 95% interval reaches 0 [sim]. Matched for tie handling, the human figure is ≤ 75.3%; on the magnet-free half the gap is 8 points (70 vs 62); other cap choices give 70–82% [paper, mine] | Desk statistics (L1-level lead). The ±10-point binomial interval the blog gives is too narrow |

## The benchmark and what rests on it

TASTE (Baig, Joren, Benton, Anthropic, 2026-08-28; PDF sha256 `7f092437…`) has 92 pairs over 50
proposals written by an Opus 4.6 scaffold. A pair's label is one anchor researcher's post-discussion
overall score (1–5), kept when confidence was strong and the gap was ≥ 2. Two anchors give 65 of
the 92 labels (Fig. 12) [paper]. The headline is "Fable 5 60%, experts 77%"
([`claims.md`](claims.md)).

Zhong's critique (2026-11-15) reports four things [critic]:
- a "fewer interp terms" rule scores 63.0%;
- the rule decides 40 pairs; on the other 52 (ties) all 14 models above ECI 158 are below 50%;
- tie accuracy falls with ECI (r = −0.60);
- OpenAI models average 29.6% on the ties.

The critique and its commenters read this as a systematic, possibly deliberate, bias against good
safety research. That is a below-chance claim and a capability-trend claim on a split: the shape
round one produced by accident.

## What we found

**1. The numbers reproduce from public material.** I digitised the critique's figure. For the 18
paper models where both panels are readable, (40·decided + 52·ties)/92 matches the question-shown
accuracy from the paper's Table 5, (74·distinct + 18·within)/92: median difference 0.3 points, max
0.6. The digitised values give r = −0.605 (n = 28, one occluded model filled from Table 5), 14 of
14 above ECI 158 below 50%, and an OpenAI mean of 29.6%. All three match the critique. [mine]

**2. A label-blind split of the same sizes also gives "below chance", but not the trend.** The
paper's magnet-free subset drops the 40 pairs that contain the 4 most frequent proposals. It is
chosen by frequency, not by labels or topic, and it has exactly the critique's sizes (40/52).

| 19 paper models | Critique ties (52) [digitised] | Magnet-free (52) [paper Fig. 19] |
|---|---|---|
| Models below 50% | 13 | 13 |
| Significantly below (one-sided binomial, p < .05) | 3 | 4 |
| Mean accuracy | 46.0% | 44.3% |
| r with ECI [95% CI] | **−0.71** [−0.88, −0.37] | **+0.39** [−0.08, 0.72] |
| r between the two subsets, per model | 0.05 | |

On TASTE, a 52-pair subset that excludes the pairs where models do best routinely leaves most
models below 50%. Models average about 62% on the 40 magnet pairs implied by Table 3 and Fig. 19
[mine]. So "below chance on the complement" does not by itself show anything about interp topics.
The falling trend with capability does not appear on the label-blind subset. Caveat: Fig. 19
averages the question-shown and question-hidden prompts, while the critique uses question shown
only.

**3. The critique's condition contains a published failure that falls with capability.** The
critique scores only question-shown prompts. The paper (Table 5, §3.4) reports that with the
question shown, models fail on the 18 within-prompt pairs: Fable 5 31%, Opus 5 22%, GPT-5.6-terra
22%. Across the 19 paper models, that within-prompt question-shown accuracy itself falls with ECI:
r = **−0.67** [−0.86, −0.31]. With the question hidden it is −0.16, and distinct-prompt accuracy is
+0.11 (shown) and +0.25 (hidden) [mine from paper]. The whole-benchmark trend changes sign with
the condition: question shown r = −0.19, question hidden +0.18, published average −0.08.

How many within-prompt pairs are among the 52 ties is not public. Worst case for the critique: all
18 are, each scored at the model's Table 5 rate. Then:
- 3 of the 6 paper models above ECI 158 move to ≥ 50%: Fable 5 57%, Kimi K3 55%, Opus 4.8 50%;
- Opus 5 (43%), GPT-5.6-terra (35%) and GPT-5.6-sol (29%) stay below;
- r with ECI over the 19 paper models stays at −0.51 [−0.78, −0.07] (k = 0, 6, 12, 18 within
  pairs: −0.71, −0.67, −0.60, −0.51; exploratory sweep).

So "every strong model is below chance" could be the paper's own instruction-following failure.
The OpenAI result and the trend could not.

**4. The trend: OpenAI plus one leverage point.** Over the 28 models [mine from digitised]:

| Subset | r with ECI [95% CI] | n |
|---|---|---|
| All | −0.60 [−0.80, −0.30] | 28 |
| Without Haiku 4.5 (ECI 143, 10 below the next) | −0.53 [−0.76, −0.18] | 27 |
| Within OpenAI | −0.75 [−0.94, −0.16] | 9 |
| Without OpenAI (critique: −0.57) | −0.57 [−0.81, −0.16] | 19 |
| Without OpenAI and Haiku 4.5 | **−0.41 [−0.74, 0.07]**, p = 0.09 | 18 |
| Within Anthropic, without Haiku 4.5 | −0.30 [−0.76, 0.37] | 11 |
| Within other labs | −0.20 [−0.83, 0.65] | 7 |
| Family fixed-effects slope (within-family permutation) | −0.55 points/ECI, p = 0.004; without Haiku −0.40, p = 0.050 | 28 / 27 |
| Leave one model out | −0.53 (drop Haiku) to −0.71 (drop Fable 5.2) | 27 |
| Ties minus whole-benchmark accuracy | −0.55 [−0.77, −0.22] | 27 |

The split-specific part (ties minus overall) falls with ECI. So the trend is not only a
whole-benchmark trend. Outside OpenAI, the seven models above ECI 158 average 44.3% on the ties,
and the slope rests on Haiku 4.5. The critique's own Appendix B finds the non-OpenAI trend survives
drop-two at 91%. That drops proposals, not models.

**5. The split-and-tuning artifact does not reproduce the pattern [sim].** I built synthetic
benchmarks with the published structure:
- 50 proposals with scores (6, 19, 17, 6, 2), all 92 pairs with a gap ≥ 2;
- 4 magnets in 10 pairs each;
- raters who penalise a latent interp topic, which is a real label confound;
- 28 models, each with a positive quality signal (no anti-taste) and an anti-interp prior acting on
  the latent topic and on "interp-adjacent" proposals;
- the critique's procedure: a wide list, narrowed when dropping the ambiguous terms helps.

Across 18 settings (adjacent share 0.15–0.45; adjacency weight 0.7 or 1.5; prior constant, rising
with capability, or rising with a flat quality signal; 400 benchmarks each):
- the critique's pattern (14 of 14 strong models below 50% and r ≤ −0.6) appears in at most 2.75%
  of runs;
- the strong models' mean tie accuracy is never below 51%, against 35.9% observed (14 models,
  [digitised]).

A topic prior can push items that "look interp but won" into the ties. In these settings that
effect is too small to produce the observed size.

**6. The rule's 63.0% is weak evidence by itself [sim].** Under this label structure, accuracy
varies widely even for a rule unrelated to the labels. In the synthetic benchmarks, a topic rule
fixed in advance with prevalence 10–40% and no relation to scores has a 95th percentile of 62%; it
reaches ≥ 63% 3.7% of the time. The best of K candidate themes:

| K | Median | 95th percentile | P(≥ 63%) |
|---|---|---|---|
| 5 | 58% | 68% | 22% |
| 10 | 61% | 70% | 37% |
| 20 | 64% | 72% | 60% |

The critique picked the theme after noticing that "mech-interp-related proposals in there are quite
bad". It then narrowed the list, which lowered the rule from 65.8% to 63.0%, so the narrowing was
not tuning for accuracy [critic]. Each of the 40 decided pairs contains a term-bearing proposal,
and no proposal is in more than 10 pairs. So the 32 correct decided pairs rest on at least 4
proposals [mine]. The critique's drop-two check: "rule beats the best model" holds in 61% of
variants [critic].

**7. Effective sample size [sim].** Labels are fixed by 50 proposal scores. In synthetic graphs an
average of 24 proposals ever win, and the top 8 winners take 61 of the 92 wins on average. Models judge each
proposal once, so their errors cluster by proposal.

| Proposal-level share of model noise ρ | Design effect | 95% interval for Fable 5's 60% | No-signal model reaches ≥ 60% | 77.4 − 60 gap, 95% interval* |
|---|---|---|---|---|
| 0 | 1.0 | 50–70 | 2.6% | 4 to 31 |
| 0.25 | 1.7 | 47–73 | 6.9% | 0 to 35 |
| 0.5 | 2.3 | 45–75 | 10.4% | −3 to 38 |
| 1.0 | 4.0 | 40–80 | 15.8% | −10 to 44 |

\*Assumes the human estimate has the same design effect and ignores the covariance between the
two estimates.

Below-chance results that survive this clustering:
- GPT-6 Sol at 11 of 52: a no-signal model gets this low in ≤ 0.8% of runs, even at ρ = 1;
- the OpenAI average of 29.6%: 0.2–4.5% (treating the 9 correlated models as one).

The critique's pair-level t-test for OpenAI is anti-conservative, but the result stands. "8 of 14
significantly below chance" uses pair-level binomials and would shrink.

**8. The human number.**
- 77.4% excludes 7 of 92 pairs with no strict held-out preference. Scored as half credit, as
  models are at p = 0.5, it is ≤ 75.3%.
- Ties within the sampled rater draws are also excluded; their count is not published.
- Other cap choices give 70–82% (App. C.2). On the magnet-free half, humans are ~70% and Fable 5
  62% (Fig. 19).
- The estimate compares one held-out rater per proposal with one anchor. Models are told to
  predict that anchor, who discussed with a partner first. [paper, mine]

## Alternative explanations (the strongest readings under which each side is right)

1. **"Disliking interp proposals is taste, not a confound" (for the authors).** Two anchors give
   71% of labels (R1 38, R3 27) [paper], so a shared anti-interp view is plausibly one or two
   people's. The critique hand-graded ~15 items and agreed with ~13 [critic]. Separating "topic is
   the construct" from "topic is one rater's prior" needs the anchor id per pair and the held-out
   raters' scores on the 40 decided pairs. The critique gives expert agreement on them as 69.4%,
   below the 77.4% overall [critic]: weak evidence that the decided pairs are less consensual.
   **Not testable here.**
2. **"The below-chance tie result is the paper's own within-prompt failure" (against the
   critique).** Partly true: see finding 3. It cannot explain GPT-5.6-sol or the trend.
3. **"Proposal selection by Opus 4.6 graders builds anti-correlation into the item pool."** The
   proposals passed best-of-N grading, an AFP-similarity proxy, agent curation and best-of-10
   polishing, all by Opus 4.6 (App. A). Raters were told "don't just pick out LLM sounding text".
   If what LLM graders liked and what raters penalised overlap, models that share the grader's
   taste would be pushed below chance. This is a selection mechanism (trait 2). **Not testable
   without per-pair data**; Opus 4.6 itself scores 45% [paper].
4. **"It is one family" (against the critique's generality).** Largely true: see finding 4.

## Robustness

| Check | Result | Does the critique's trend survive? |
|---|---|---|
| Label-blind placebo of the same sizes (magnet-free) | Below-50 count reproduced (13/19); trend not (r = +0.39) | Trend yes; "below chance" not specific |
| Within-prompt worst case | r −0.51; 3 of 6 strong paper models back to ≥ 50% | Trend yes; "all strong models" no |
| Drop Haiku 4.5 | −0.53 | yes |
| Drop OpenAI and Haiku 4.5 | −0.41 [−0.74, 0.07] | **no** |
| Family fixed effects | p = 0.004 (0.050 without Haiku) | yes, weaker |
| Split-and-tuning simulation | ≤ 2.75% of runs; tie accuracy ≥ 51% | yes |
| Bonferroni ×7 (prereg) | FE p 0.004 → 0.03; within-prompt r p 0.0024 → 0.017; without-Haiku FE p 0.05 does not survive | mostly |

Pre-registered rules ([`prereg.md`](prereg.md)), as they came out:
- T1: below-chance counts are not specific; the trend is specific.
- T2: the "within-prompt explains it" rule is met at the worst case (3 of 6 ≤ half) for the
  "every strong model" claim. It is not met for the trend.
- T3: "holds" (without Haiku the interval excludes 0; FE p < 0.05).
- T5: "rule not evidence by itself" (95th percentile ≥ 63% for K ≥ 5; 62% for K = 1).
- T6: "not a plausible artifact" (< 5%).

## What was already known

See [`prior_work.md`](prior_work.md). The paper discloses:
- the 92/50 dependence and the magnets, and the magnet-free numbers;
- the within-prompt failure with the question shown;
- the cap-choice range for the human number.

The critique discloses tuning, one reviewer per label and shared proposals.

New here:
- the magnet-free subset used as a label-blind placebo of the same size;
- within-prompt question-shown accuracy falls with ECI (−0.67), and the question-shown condition
  turns the whole-benchmark trend negative;
- the worst-case within-prompt bound;
- the dependence of the non-OpenAI trend on Haiku 4.5;
- the label structure (score gap ≥ 2 fixes labels by proposal) and its design effect;
- the tuning null;
- the split-artifact simulation;
- the reproduction of the critique's numbers from the paper's Table 5.

## What this does not show

- Anything at L3 or L4. No per-pair data were analysed; no model was run. Whether any model uses an
  interp shortcut is untested.
- That the critique's split includes any within-prompt pairs. Finding 3 is a bound.
- That the magnet-free subset and the critique's ties are comparable conditions. They differ in
  prompt variation, and their per-model accuracies are uncorrelated (r = 0.05).
- Anything about real TASTE from the simulations beyond "this mechanism, with these parameters,
  does or does not produce this pattern". The design effects depend on an unmeasured ρ.
- Why OpenAI models are below chance on the ties. That result survives every check here.

## Blocked, and what would run on access

With per-pair ids, labels, anchor ids, term counts and per-model probabilities:
1. a proposal-level bootstrap of every interval above, replacing the simulated design effect;
2. how many within-prompt pairs are among the ties, and the critique's analysis on distinct-prompt
   ties only and with the question hidden;
3. the term rule on a pre-specified list and on a split-half (discover on half the proposals, test
   on the rest);
4. tie accuracy by anchor rater (is anti-interp R1's view?);
5. options-only surface rules (length, number of experiments, compute mentions), each with a
   proposal-level permutation null;
6. a Haiku options-only pilot on 10 benign proposals.

## Pins and how to reproduce

- Paper PDF sha256 `7f0924379ad2d4bcaddf98843f6e0cfc9e6c79f1820c282038c19d73576a15be`.
- Critique figures sha256 `82a4fbaa…` (fig. 1) and `e98a5f8d…` (fig. 2).
- Epoch `eci_scores.csv` fetched 2026-11-17 (the critique used 2026-11-15; x-offsets ≤ 0.4).
- Seeds 20261117.

```bash
cd audits/taste && uv venv data/.venv && VIRTUAL_ENV=data/.venv uv pip install numpy scipy pillow
P=data/.venv/bin/python
$P -I scripts/digitize_critic_fig.py   # critic Fig. 2 -> results/critic_fig2_digitised.json
$P -I scripts/desk.py                  # T0-T3, T7    -> results/desk.json
$P -I scripts/simulate.py              # T4-T6 (synthetic) -> results/simulate.json
$P -I scripts/collect.py               # -> results.json
```

Downloads (paper, posts, figures, ECI) go to `data/` (git-ignored). The URLs are in
[`claims.md`](claims.md).
