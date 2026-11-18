# TASTE: claims under test

Status: 2026-11-17, round two, branch `audits-round2`. Written before any analysis of per-model
results.

## Sources and pins

| Source | What | Pin |
|---|---|---|
| Paper | Baig, Joren, Benton, "TASTE: Can AI Models Judge AI Safety Research Proposals?", 61 pp., PDF linked from the blog and the LessWrong linkpost | `www-cdn.anthropic.com/files/4zrzovbb/website/dd5feddcb3b7d20aadda6af4093ac1fb0c9d419e.pdf`, sha256 `7f0924379ad2d4bcaddf98843f6e0cfc9e6c79f1820c282038c19d73576a15be` (created 2026-08-26) |
| Blog / linkpost | alignment.anthropic.com/2026/taste/; LessWrong `iSDbyrG8yfqk3KJbT` (2026-08-28) | post HTML and 7 comments fetched 2026-11-17 via the LessWrong GraphQL API |
| Critique | Ziqian Zhong, LessWrong `tpKE33scJGzqYKEBW` (2026-11-15). Slug "llms-are-weirdly-below-chance-on-taste-without-a-shortcut"; current title "LLMs are below chance on TASTE once a shortcut is removed" | post HTML and 10 comments fetched 2026-11-17; figures sha256 `82a4fbaa…` (fig. 1) and `e98a5f8d…` (fig. 2) |
| Capability index | Epoch AI `eci_scores.csv` (the critic used the 2026-11-15 version) | fetched 2026-11-17; values for the 28 models differ from the critic's x-positions by ≤ 0.4 ECI |
| Data | Benchmark, labels, proposal text, per-pair model logs | **gated** behind a Google form ("available on request to AI safety researchers"). Not submitted, per the brief. No licence stated publicly |

The benchmark: 92 pairs over 50 proposals written by an Opus 4.6 scaffold; 74 distinct-prompt
and 18 within-prompt pairs. A pair's label is one "anchor" researcher's post-discussion overall
score (1–5), kept when the anchor reported strong confidence and the two scores differ by ≥ 2;
no proposal appears in more than 10 pairs. Models are scored on one verdict per pair: probability
averaged over two answer orders and two prompt variations (question shown, question hidden).

## Conclusion 1 (benchmark): models trail experts; the best model is at 60%

- **Number and place.** "Frontier models range from ∼41% (no better than chance) to 60%
  (Fable 5)" and "we estimate the accuracy of experienced AI safety researchers on our dataset at
  77%" (abstract; Table 3, p. 26; §2.3; Figure 1). The blog: "the best model performs worse than
  our human researchers — Fable 5 achieves 60% whereas we estimate researcher performance at 77%".
- **Who relies on it.** Anyone tracking whether models can judge hard-to-verify safety research
  (the paper proposes TASTE as "a held-out evaluation for training methods intended to improve AI
  models' research judgment", §7). Commenters already debated the human comparison (mishka; the
  first author's reply concedes it is "pairs of researchers, after a discussion stage").
- **What would change it.** (a) Under proposal-level resampling the 60% is not distinguishable
  from 50%, or the 77% − 60% gap is not distinguishable from 0. (b) The 77% is not a like-for-like
  human accuracy (different denominator, tie handling, cap choice), so the gap is smaller than 17
  points on a matched basis.

## Conclusion 2 (critique): a "fewer interp terms" rule beats every model

- **Number and place.** "this shortcut is able to achieve a 63.0% overall accuracy, beating all
  the LLMs we tested" (critique, "The shortcut"). 80% on the 40 pairs where counts differ; coin
  flip on the 52 ties. The best model in the critic's condition (question shown only) is 61.4%.
- **Who relies on it.** Readers of the critique; anyone using TASTE who now discounts it as a
  topic test.
- **What would change it.** A label-permutation null for a rule tuned the way this one was
  (vocabulary chosen after noticing the topic, then narrowed) reaching the low 60s; or the rule's
  lead resting on a handful of proposals.

## Conclusion 3 (critique): on the 52 ties, strong models are below chance and fall with capability

- **Number and place.** "With only the rubric provided, all 14 models with ECI > 158 score below
  50%, and 8 of those 14 are significantly below chance. Across all 28 models, the accuracy on this
  half is strongly negatively correlated with ECI (r = -0.60, p < .001)." OpenAI models average
  29.6% (8 of 9 significantly below chance; r = −0.74 within OpenAI). Robustness table: drop one
  and drop two proposals keep r < 0 in 100% of variants.
- **Who relies on it.** The critique's reading ("a systematic bias"; "hard to rule out a
  scheming / sabotaging interpretation"); commenters who linked it to covert underperformance on
  safety research (gwern, mihir). This is a capability-trend claim and a below-chance claim, the
  two shapes that round one produced by accident with a split.
- **What would change it.** (a) A label-blind split of the same sizes also yields below-chance,
  capability-falling accuracy on its 52-pair half. (b) The critic's 52 pairs are enriched for a
  known, published failure mode (within-prompt pairs with the question shown, paper §3.4/D.5),
  and removing that failure brings the strong models back to chance. (c) The trend depends on one
  leverage point (Haiku 4.5 at ECI 143) or on one family. (d) A simulation with the published
  structure, a topic-using model with no anti-taste and the critic's tuning produces the pattern
  often.

## Traits that predict a broken headline (METHODOLOGY.md, "Where to attack")

| # | Trait | TASTE | Note |
|---|---|---|---|
| 1 | Label from a process, not a judgment of substance | partly | One anchor rater per pair; 2 of 6 anchors give 65 of 92 labels (Fig. 12). The label is a judgment, but of one person |
| 2 | Items kept by model behaviour | **yes, upstream** | Proposals were selected by Opus 4.6 graders (best-of-N, AFP-similarity proxy, LLM-agent curation, best-of-10 polish; App. A). Pairs were not filtered by model answers |
| 3 | Gap near chance / difference of rates | **yes** | 60% vs 50%; 60% vs 77% |
| 4 | Few independent units | **yes** | 92 pairs, 50 proposals, 4 "magnets" in 10 pairs each; 8 proposals scored 4–5 are the only possible winners outside 3-vs-1 pairs (Fig. 13) |
| 5 | Two free-text options | yes | ~200–250-word proposals |
| 6 | LLM judge of a subjective criterion | no (for scoring); yes (for proposal selection, and the paper's "prompt-driven" classifier) | |
| 7 | Scorer assumes the model was told something | partly | Models are told to predict a named anonymised researcher; with the rubric only, the name carries no information |
| 8 | Best number belongs to the easiest condition | possible | The headline averages question-shown and question-hidden; the critique uses question-shown only, where the paper reports within-prompt pairs fail (Table 5) |
| 9 | One outcome bucket holds unlike cases | yes | "Correct" mixes distinct-prompt and within-prompt pairs, which behave oppositely with the question shown |
| 10 | Aggregation over units of varying size | no | |
| 11 | Unbalanced key | unknown | Order is averaged over both positions |
| 12 | Little outside scrutiny | **yes** | 3 months old, one lab, data gated, one critique |
