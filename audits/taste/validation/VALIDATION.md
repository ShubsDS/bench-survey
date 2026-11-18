# TASTE audit: independent validation

Validator, 2026-11-17, branch `audits-round2`. I did not write the audit. I tried to break it.

This is a desk audit. Nothing in it, the audit's or mine, uses per-pair data. The benchmark sits
behind a Google form, which I did not submit. I contacted no one and ran no models (0 USD).

What I wrote before reading the auditor's code:
- my own digitiser of the critic's Fig. 2 ([`redigitise.py`](redigitise.py));
- my own transcription of Table 5, Table 3 and Fig. 19, read off `data/paper/taste.txt` and
  `p-36.png`. All three match `scripts/published.py` exactly;
- my own analysis ([`validate.py`](validate.py)) and simulations
  ([`sim_validator.py`](sim_validator.py)).

I read `scripts/simulate.py` only after my own simulation was written. Outputs:
[`validation_desk.json`](validation_desk.json), [`validation_sim.json`](validation_sim.json) and
[`validation.json`](validation.json) (the summary). Seed 20261117.

Source labels used below: **[paper]**, **[critic]**, **[digitised]** (read from the critic's
chart), **[mine]** (computed from those numbers) and **[sim]** (synthetic benchmarks, not TASTE
data, at most L1).

## Verdicts

| # | Auditor's claim | Verdict | Validator's number | How checked |
|---|---|---|---|---|
| 0 | The critic's figure reproduces Table 5 (median 0.3, max 0.6 points); r = −0.605; 14/14; OpenAI 29.6% | **Confirmed** | median 0.22, max 0.43 (n = 18); r = −0.603 [−0.80, −0.30]; 14/14; 29.6% | Own digitiser; values snapped to the possible-value grid |
| 0b | Reading error about ±0.5 points | **Corrected (smaller)** | Every unoccluded marker sits within 0.35 of a possible value (k/80 for 40 pairs, k/104 for 52); squares within 0.05. After snapping, the values are exact pair counts except 3 occluded markers | See A |
| 1 | Magnet-free placebo: 13/19 below 50% on both splits; r = +0.39 vs −0.71; "label-blind" | **Confirmed numbers; corrected reading** | 13/13; +0.39 [−0.08, 0.72] vs −0.70 [−0.88, −0.36] | Fig. 19 re-read; see B |
| 1a | Magnet-free is "chosen by frequency, not by labels or topic" | **Corrected** | Magnets are frequent because they have many ≥2 score gaps, and the cap kept each magnet's 10 largest-gap pairs (App. C.2). So the split depends on the anchor scores that define the labels: it drops the large-gap pairs. Its topic overlap with the term rule is unknown | Paper C.1–C.2, D.3 |
| 1b | Below-50 counts are "not specific" to the critique's split | **Confirmed, on a better reason** | 12 of 19 paper models are already below 50% over all 92 pairs with the question shown [mine from paper Table 5]. Random 52-pair splits give 7–13 below 50% (median 10; P(≥13) = 7%) | Hypergeometric placebo, independent models |
| 1c | The trend "survives a placebo split" | **Downgraded** to a single, unmatched comparison | One placebo split, different prompt condition, different gap mix. A random-split placebo (independent models) gives r = −0.30 [−0.46, −0.14] against −0.60 observed (0 of 10,000) | See B |
| 2 | Within-prompt worst case: 3 of 6 strong paper models return to ≥ 50%; r −0.51 | **Confirmed** | 3/6 (Fable 5 57.1, Kimi K3 56.1, Opus 4.8 50.2); r −0.505 [−0.78, −0.07]; −0.51 to −0.50 under Table 5 rounding | Own arithmetic |
| 2a | Within-prompt question-shown accuracy falls with ECI, r = −0.67 | **Confirmed** | −0.669 [−0.86, −0.31] | Table 5 |
| 3 | r without Haiku 4.5 −0.53; family FE p = 0.004 (0.050 without Haiku) | **Confirmed** | −0.526; FE slope −0.55, p = 0.004; without Haiku −0.40, p = 0.049 | Own permutation (10,000) |
| 3a | Family-clustered and single-model checks | **Confirmed (added)** | Release-group cluster bootstrap (22 clusters) [−0.83, −0.29]; two-stage family bootstrap [−0.87, −0.14]; leave-one-model-out −0.70 to −0.53; leave-two-out −0.76 to −0.48, all 378 at p < .05 | See C |
| 4 | "Without OpenAI" **fails as worded** (−0.41, p = 0.09 without OpenAI and Haiku) | **Corrected: fragile, not failed** | The critic's −0.571, p = 0.011 reproduces. Leave-one-out inside the 19 non-OpenAI models keeps p < .05 for 18 of 19 drops; only dropping Haiku 4.5 breaks it (−0.42, p = 0.085). The drop-OpenAI-and-Haiku cell was added after the desk results (commit `42d1fd8`) and is not in the prereg | See C |
| 4a | "14 of 14 above ECI 158 below 50%" is fragile | **Confirmed, and a second reason** | The strong model nearest 50% is 1 pair below (48.1 = 25/52; Fable 5 and Kimi K3). Reading error cannot change the count (100% of draws). Epoch's ECI uncertainty can: the statement holds in 69% of ECI draws. The cut-off sits between Opus 4.7 (157.5, exactly 50.0%) and Kimi K3 (158.6). Above 157 the count is 14 of 15 | See A, C |
| 5 | Split-and-tuning simulation: pattern in ≤ 2.75% of runs → **R** for the split artifact | **Downgraded to L1, and narrowed** | A topic prior, even one rising with capability, gives 0% in my rebuild: 51 of 52 ties have no terms, so the prior cannot act there. But if strong models also share an "LLM appeal" that the proposal selection made anti-correlated with quality, the full pattern appears in up to 69% of runs, including a non-negative trend on the decided half. A simulation cannot give R | See D |
| 6 | Tuning null: a pre-written topic rule reaches 62% at p95; best of 5 themes 68% | **Cannot be checked independently; wording kept as [sim] L1** | Reran: reproduces exactly. It rests on the same "labels fixed by 50 proposal scores" assumption (see E) | Rerun |
| 7 | Design effect: with ρ ≥ 0.25, 60% is not distinguishable from 50% (7–16%); the gap's interval reaches 0 | **Downgraded: conditional lead** | Magnet-like graphs: P(no-signal ≥ 60%) 2.4% (ρ = 0) → 6.2% (ρ = 0.1) → 10% (0.25) → 18% (1). The flip is near ρ ≈ 0.07. In a flat graph (degree 3–4, no magnets) it stays ≤ 5% up to ρ = 0.75. The gap interval also assumes the human estimate has the model's design effect, which is unmeasured | See E |
| 8 | Human figure ≤ 75.3% when matched for ties | **Confirmed (arithmetic, not simulation)** | 75.3% with half credit for the 7 pairs; 71.5% at zero credit | (0.774·85 + 3.5)/92 |
| 9 | Prereg committed before results | **Confirmed, one deviation** | prereg `6c453c7` 19:00:58; desk `8c4d9ad` 19:02:58; sims `42d1fd8` 19:05:48. The digitised values were committed earlier (`df019fe`, disclosed). The `drop_openai_and_haiku45` cell was added in `42d1fd8` and is not preregistered | `git log -- audits/taste` |

## A. Rerun and re-digitisation

**Rerun.** I ran `digitize_critic_fig.py`, `desk.py`, `simulate.py` and `collect.py` into a
scratch copy. `critic_fig2_digitised.json`, `desk.json`, `simulate.json` and `results.json` are
byte-identical to the committed files.

**My own digitisation.** I found the gridlines by scanning for neutral grey: x at 140/150/160/170
ECI, y every 10 points. I segmented markers by hue, not RGB, and took each marker's centre from its
bounding box.

There is a check the auditor did not use. Each model gives one verdict per pair, with half credit
at p = 0.5, so the only possible values are k/80 on 40 pairs and k/104 on 52 pairs. My readings:
- squares fall within 0.05 points of a possible value;
- triangles, stars and crescents fall within 0.35;
- snapping is unambiguous for every unoccluded marker.

So the per-model values are exact pair counts, and the "±0.5" in the audit overstates the error.

The auditor's triangles (other labs) read about 0.35 points low. Its digitiser uses the mask
centroid, which sits below a triangle's centre. This has no effect on any conclusion: under ±0.5
uniform error, r stays in [−0.611, −0.595].

Three markers are occluded:
- **Gemini 3.1 Pro (ties):** completely hidden under Opus 4.6's square (44.2). The derived value
  from Table 5 is 44.7 (±0.9 from Table 5's rounding), which agrees with the auditor's fill.
- **GLM 5.2 (ties):** 7 of 20 pixel rows are visible. My reading is 46.2–47.1 and the Table 5
  derivation gives 46.5. I use 46.5.
- **Opus 5.5 (decided):** hidden under GPT-6.1 Sol's star (51.25). Only the placebo needs it.

**Luna markers.** My first matching swapped GPT-5.6 Luna and GPT-6 Luna. The crescent's coloured
box sits left of the marker centre. Only one assignment agrees with Table 5 (residual 0.0 against
3–4 points). The auditor's assignment is the correct one.

**ECI matching.** All 28 models match a distinct Epoch entry (for example GPT-5.5, not GPT-5.5
Pro). Marker x-positions sit within 0.2 ECI of the 2026-11-17 file, crescents excepted, so the
file the critic used (2026-11-15) did not differ in any way that matters here.

## B. The magnet-free placebo (auditor's point 1)

- **The numbers reproduce:**
  - Fig. 19 situational bars as transcribed;
  - 13 of 19 models below 50% on both splits;
  - r with ECI +0.39 (magnet-free) against −0.70 (ties, 19 models);
  - the two splits' per-model accuracies correlate at 0.05.
- **The prompt condition differs.** The critique uses question shown only. Fig. 19 does not say,
  and D.3 does not either; the paper's other summaries (Table 3, Table 4) average both
  variations. The question-shown penalty (hidden minus shown) rises with ECI, r = +0.36 [mine from
  paper]. To approximate a question-shown magnet-free number, I assumed the magnet-free subset
  carries c times the whole-benchmark shown/hidden gap. Then magnet-free r is +0.28 at c = 1,
  +0.15 at c = 2 and −0.04 at c = 4. The mismatch moves the comparison in the critique's
  disfavour, but not enough to close a 1.1 gap in r. **Not like for like, and not decisive.**
- **Not label-blind.** C.2 says each of the 4 magnets was cut to its 10 pairs "sorted by
  descending score gap". Magnets are proposals that clear the ≥ 2 gap against many partners, so
  they are likely extreme-scored. Magnet-free therefore removes the 40 largest-gap pairs, which is
  why models score about 62% on them [mine from paper]. Whether the magnets are interp proposals
  is not public. If they were, the two "40/52" splits would overlap. One overlap probe is
  uninformative: implied magnet-40 accuracy against the critic's decided-40, across the 19 models,
  r = −0.09.
- **40/52 does not mean the same thing.** Magnet-free 40 = the magnets' largest-gap pairs. Critic
  40 = pairs whose term counts differ. Both 52s are complements, with different gap and topic mixes.
- **A real placebo distribution.** One placebo split is not a placebo distribution
  (METHODOLOGY). Each model's correct count over 92 pairs is known from the chart. A random 52-pair
  subset of that model's outcomes then has a hypergeometric count. Assuming independent models:
  - r(ECI, random-52) is −0.30 [−0.46, −0.14], tracking the whole-benchmark question-shown r of
    −0.33;
  - the observed −0.60 lies outside all 10,000 draws;
  - "all 14 strong models below 50%" occurs in 0 of 10,000 draws.

  Models share errors on the same pairs (critic: OpenAI consensus against the panel on 27 of 32),
  so this null is too narrow, and its tail probabilities are lower bounds. Even so, it supports
  "the tie trend is steeper than the whole-benchmark trend" (auditor's ties-minus-overall
  r = −0.55, which I confirm).
- **Below-50 counts are not distinctive** (auditor's conclusion holds, on a better reason). With
  the question shown, 12 of the 19 paper models are below 50% over all 92 pairs [mine from paper].
  Random 52-pair splits give 7–13 below 50%.

## C. Families, single models, comparisons (auditor's point 3)

| Check | r (95% CI) or p | n |
|---|---|---|
| All | −0.603 [−0.80, −0.30], permutation p 0.0007 | 28 |
| Without Haiku 4.5 | −0.526 [−0.76, −0.18] | 27 |
| Within OpenAI / Anthropic / other | −0.74 / −0.59 / −0.19 | 9 / 12 / 7 |
| Drop OpenAI (critic −0.57, p .011) | −0.571, p 0.011 | 19 |
| …and leave one model out | p < .05 in 18 of 19; only Haiku 4.5 breaks it (−0.42, p 0.085) | 18 |
| Family fixed effects (within-family permutation) | −0.55 pts/ECI, p 0.004; without Haiku −0.40, p 0.049 | 28 / 27 |
| Release-group cluster bootstrap (OpenAI generations resampled together; 22 clusters) | [−0.83, −0.29] | 28 |
| Two-stage family bootstrap | [−0.87, −0.14]; r ≥ 0 in 0.9% | 28 |
| Leave two models out (378 pairs) | −0.76 to −0.48; all p < .05 | 26 |
| Reading error ±0.5 uniform | r in [−0.611, −0.595]; 14/14 in 100% | |
| ECI error (Epoch CIs) | r in [−0.655, −0.534]; FE slope [−0.62, −0.46]; "all > 158 below 50" in 69% | |
| ECI cut-off 157 / 158 / 159 / 160 | 14 of 15 / 14 of 14 / 13 of 13 / 12 of 12 below 50% | |

Number of comparisons:
- The audit's README reports about 25 p-values or intervals across T1–T3 and T7. The prereg's
  Bonferroni factor of 7 counts tests, not sub-tests.
- At ×25, these survive: the all-model r (critic's, p 0.0007 → 0.018), drop-Anthropic, and the
  within-prompt question-shown r (p 0.0017 → 0.04).
- These do not survive: the family-FE p (0.004 → 0.10) and anything without Haiku.

## D. The split-artifact simulation, rebuilt (auditor's finding 5)

My generator differs from the auditor's on purpose:
- candidate pairs are random gap ≥ 2 pairs, capped at 10 per proposal by largest gap (no exact
  magnets);
- ties are pairs with both proposals term-free;
- 28 models sit at the real ECI values.

Each model's preference is a·quality − λ·topic + γ·shared appeal + noise. "Shared appeal" is one
variable all models see, independent of quality in the generated pool. 400 benchmarks per
setting. "Pattern" means all models above ECI 158 below 50% on ties and r ≤ −0.6.

| Scenario | Pattern | Pattern and decided-half r > 0 (as the critic finds, +0.27) |
|---|---|---|
| B1: topic reliance λ rising with ECI, no shared appeal (the brief's plain alternative) | **0%** in all 6 settings | 0% |
| B2: shared-appeal reliance γ rising with ECI, no selection | 0–8.5% | 0–0.25% |
| B3: as B2, after an LLM-grader selection on quality + appeal (keep 50 of 100 or 250) | up to 75% | ≤ 0.25% (the decided half falls too) |
| B4: λ and γ both rising with ECI, no selection | 0–11% | 0–8.5% |
| B4 with selection (keep 20%) | 17–72% | **15–69%** |

What this means:
1. **The plain alternative gives no pattern.** Stronger models relying more on a topic prior
   cannot by itself push them below chance on term-free ties: 0%, in agreement with the auditor.
2. **Selection can produce the pattern without any model having anti-taste in the generated
   pool.** The paper's construction selects proposals (best-of-N and best-of-10 by Opus 4.6
   graders, App. A). If that made "what LLMs like" and "what raters like" anti-correlated among
   the survivors, and stronger models share that taste more, then all three of the critic's
   observations follow: below chance on ties, falling with ECI, and flat or rising on the decided
   half.
3. **The auditor's ≤ 2.75% is a property of its model class.** That class has no shared appeal
   and no selection. It cannot support **R**.

My models are too accurate in the unselected settings (tie accuracy 57–80%, against about 46%
observed). The selected settings match the observed levels better. Everything here is [sim], L1.

## E. Design effect (auditor's point 2)

The no-signal model is a·0 + proposal-level noise (share ρ) + pair noise. I ran 200 graphs × 200
noise draws per cell.

| Graph | ρ = 0 | 0.1 | 0.25 | 0.5 | 1.0 |
|---|---|---|---|---|---|
| G_fixed (labels fixed by proposal score, capped at 10 by largest gap) | 2.4% | 6.2% | 10.0% | 14.3% | 18.0% |
| G_rater (each pair's anchor adds rater noise to the label) | 2.4% | 5.9% | 10.0% | 14.0% | 17.7% |
| G_flat (92 pairs, degree 3–4, no magnets) | 2.4% | 2.9% | 3.7% | 4.6% | 5.8% |

Cells are P(no-signal model ≥ 60% on 92 pairs).

- **Where it flips.** "60% is not distinguishable from 50%" holds for ρ ≳ 0.07 when the degree
  distribution is as skewed as the magnets imply. It fails for ρ < 0.75 in a flat graph.
- **The auditor's G_fixed assumption.** It uses "labels fixed by 50 proposal scores". The paper's
  pairs are per-rater (C.1), and Fig. 13 counts each proposal "once at its anchor rater's score",
  so this simplification is plausible but not stated by the paper. Rater-specific labels changed
  little (G_rater).
- **Neither ρ nor the real degree distribution is published.** So this is a conditional lead.
  Two statements need the condition attached:
  - "the blog's ±10 points is too narrow" holds only if ρ is above about 0.1 and the graph is
    skewed;
  - "the 77 − 60 gap's interval reaches 0" also needs the human estimate's design effect, which
    is unmeasured.
- **The auditor's below-chance survivals stand within its own model:** GPT-6 Sol at 11/52, and
  the OpenAI 29.6%.

## What I corrected in the README and results.json

1. Headline and claim table:
   - simulation results are no longer "R";
   - the split-artifact claim is L1 and narrowed (D);
   - the trend's placebo is one unmatched split (B).
2. "Magnet-free is chosen without labels or topic" is replaced (1a).
3. "Without OpenAI fails as worded" becomes "fragile: rests on Haiku 4.5; the post-hoc cell is not
   preregistered" (4).
4. Reading error: about ±0.35 before snapping, exact pair counts after; "±0.5" is kept visible as
   the auditor's.
5. Design effect: the flip point and the graph dependence are stated (E). "Too narrow" is
   conditional.
6. A new source-label pass: several sentences mixing [paper] and [mine] are now tagged.
7. "14 of 14": the second fragility, from ECI uncertainty and the cut-off placement, is added
   (4a).

## What could not be checked

- Anything per pair: the overlap of the ties with the within-prompt pairs or with the magnets, the
  gap mix of the ties, and the anchor per pair.
- Whether Fig. 19 averages both prompt variations.
- The critic's numbers that do not appear in its figure: Appendix B, the wide-list results, and
  consensus counts.
- Whether Opus 4.6-graded selection actually anti-correlates LLM appeal with rater scores. D shows
  only that it could.

## Final evidence levels

| Claim | Level |
|---|---|
| Critique numbers reproduce from public material | L1 (desk reproduction; reading exact to the pair) |
| Below-50 counts not specific to the split | L1 (desk; paper's own Table 5 already has 12 of 19 below 50 with the question shown) |
| Trend steeper on ties than on random 52-splits | L1 (desk; independent-model null, a lower bound) |
| Within-prompt worst case | L1 (bound) |
| Trend robust to single models and families; non-OpenAI part rests on Haiku 4.5 | L1 (desk) |
| Split-artifact and tuning simulations | L1 (sim), lead only; not R |
| Design effect, 60% vs 50%, gap interval | L1 (sim), conditional on unmeasured ρ and graph |
| Human figure 75.3% when tie-matched | L1 (arithmetic from paper) |

No claim reaches L2 or above. The audit itself said nothing reaches L3 or L4.
