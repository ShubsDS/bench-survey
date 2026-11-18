# TASTE: pre-registration (Case B desk audit)

Committed before any of the analyses below were run. What I had already seen: the published
per-stratum numbers themselves (the critique's figures, which `scripts/digitize_critic_fig.py`
digitised and printed, and the paper's Table 5 and Figure 19, read while reading the paper). No
statistic below had been computed. Nothing here uses per-pair data: none is reachable.

## Inputs (all transcribed or digitised; every number is labelled with its source)

- **Paper, transcribed by hand into `scripts/published.py`:** Table 3 (headline accuracy, 19
  models); Table 5 (distinct-prompt and within-prompt accuracy, question shown and hidden, 19
  models); Table 4; Figure 12 anchor counts; Figure 13 benchmark score distribution (6, 19, 17, 6,
  2 proposals at scores 1–5); Figure 19 magnet-free accuracy (situational framing, 19 models,
  printed bar labels); App. C.2 cap-choice range; human 77.4% on 85 pairs.
- **Critique:** prose numbers (63.0%, 80% on 40, 61.4% best model, r = −0.60, 29.6%, Appendix B
  table, Appendix C), and per-model accuracy on the 40 decided and 52 tie pairs read from its
  Figure 2 by marker colour (`results/critic_fig2_digitised.json`; read from a chart, ±0.5 points).
  Markers are matched to models by colour and nearest ECI in Epoch's file (crescent markers have a
  centroid about 0.4 ECI left of centre). One marker per panel is occluded; it is left missing.
- **ECI:** Epoch `eci_scores.csv` fetched 2026-11-17.

## Tests

Statistic for every correlation: Pearson r across models (the critique's statistic), with a Fisher
interval and, where stated, a permutation p. Seeds fixed at 20261117.

**T0. Reproduction.** For the 19 paper models, the question-shown accuracy over 92 pairs from
Table 5, (74·distinct + 18·within)/92, against (40·decided + 52·ties)/92 from the digitised
critique figure. Holds if the median absolute difference is ≤ 1.5 points (Table 5 is rounded to
integers). Also the critique's r = −0.60 recomputed from the digitised values.

**T1. Label-blind placebo of the same size (real data).** The paper's magnet-free subset is 52
pairs, chosen by proposal frequency, not by labels or topic. For the 19 paper models: the number
below 50% and r with ECI on magnet-free (Fig. 19), against the same two statistics on the critic's
52 ties for the same 19 models. Reading: if the label-blind 52 also puts most models below 50%,
"below chance on a 52-pair complement" is not by itself evidence of a topic-specific effect. The
capability trend is specific to the critic's split only if magnet-free r is not also clearly
negative. Caveat fixed now: Fig. 19 averages both prompt variations; the critique uses question
shown only.

**T2. Within-prompt pairs (the paper's published failure) inside the ties.** Unknown how many of the
18 within-prompt pairs are among the 52 ties. Worst case for the critique: all 18 are, and each
model scores on them its Table 5 question-shown within-prompt accuracy. Then accuracy on the 34
remaining distinct-prompt ties is (52·ties − 18·within)/34. For the 6 paper models with ECI > 158
and the 3 GPT-5.6 models: how many stay below 50%. Also r(ECI, within-prompt question-shown
accuracy) and r(ECI, distinct-prompt question-shown accuracy) over the 19 paper models.
"Within-prompt explains it" if, in this worst case, at most half of the six stay below 50%.
"Holds" otherwise.

**T3. Leverage and families.** On the critic's ties (27 digitised models): r(ECI) overall; without
Haiku 4.5 (ECI 143, 10 points below the next model); within Anthropic, within OpenAI, within others;
a slope with family fixed effects (Anthropic / OpenAI / other) and a within-family permutation p
(10,000 permutations); leave one family out. Also r(ECI) for the question-shown overall accuracy and
for ties − overall, to separate a whole-benchmark trend from a split-specific one; and, for the 19
paper models, r(ECI) for question-shown versus question-hidden overall accuracy. "Changes" if r
without Haiku has a Fisher 95% interval including 0, or the family-fixed-effects p > 0.05.

**T4. Effective sample size (simulation; not the data).** A generator of synthetic benchmarks that
matches every published structural number: 50 proposals with scores (6, 19, 17, 6, 2), 92 pairs,
all with a score gap ≥ 2 (so labels are fixed by proposal scores), at most 10 pairs per proposal,
four proposals at exactly 10 with no pair between two of them. Models are simulated with a
proposal-level perceived quality (signal plus proposal-level noise) and pair-level noise, at a mix
calibrated to a target accuracy. Report: SD of accuracy across fresh benchmarks against the binomial
SD (design effect), over a grid of the proposal-level share of noise; the implied 95% interval for
60%, for the 77 − 60 gap, and for the below-chance tests on 52 ties (GPT-6 Sol 11 of 52; the
OpenAI 29.6%). Also the minimum number of proposals that can carry the rule's 32 of 40 decided pairs.

**T5. Tuning null (simulation).** On synthetic benchmarks: K candidate topic vocabularies (K = 5,
10, 20, 40), each present in 10–40% of proposals independently of labels; for each vocabulary the
rule "pick the proposal with fewer terms, coin flip on ties"; the best of K rules on the labels.
Report the 95th percentile of the best rule's 92-pair accuracy under the null. "Rule not evidence by
itself" if the 95th percentile reaches 63%.

**T6. Split artifact (simulation).** Proposals carry a latent interp topic (prevalence matched to
40 decided pairs, ties ~52); a candidate vocabulary of core and ambiguous terms; human scores
penalise the topic (a real label confound). Models: positive quality signal (no anti-taste) plus an
anti-interp prior that acts on the latent topic, not on the term list. Procedure as in the
critique: wide list, then narrowed by dropping the terms that hurt accuracy on the labels. Report,
for 1,000 synthetic benchmarks: mean tie accuracy of the most topic-driven models; how often ≥ 14
of 14 strong models fall below 50% on ties; how often r(capability, ties) ≤ −0.6, with the topic
prior independent of capability and with it rising with capability. "The critique's pattern is a
plausible artifact" if it appears in ≥ 5% of runs without anti-taste.

**T7. The human number.** (a) Forced-choice equivalent of 77.4% when the 7 pairs without a strict
held-out preference count as 50%. (b) The cap-choice range 70–82% and the magnet-free ~70% against
Fable 5 there (62%). (c) Who the 77% compares: one held-out rater per proposal against one anchor.

## Multiple comparisons

Seven tests, several with sub-parts. I report raw intervals and say which conclusions would survive
a Bonferroni factor of 7.

## What I will not claim

Anything about per-pair behaviour; that any model uses a topic shortcut (no L3 or L4 is possible
without per-pair data or proposal text); any simulation number as a property of the real benchmark.
