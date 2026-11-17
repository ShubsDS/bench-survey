# Model-Written Evals: CAA's steering effects on these files are largely "answer Yes" and "answer A", and an inconsistent key alone produces a 70-point human-versus-model-written gap

Status: 2026-11-17. Evidence levels:

| Claim | Level |
|---|---|
| 1. CAA's 7B coordination and survival steering effects do not survive on items where the key is "No" (coordination) or "B" (survival) | **L3** |
| 2. Llama 2 13B Chat's unsteered CAA scores are mostly a preference for answer "B" | **L3** |
| 3. Claude Haiku's propensity scores on these files move with answer polarity and position: a nay-saying and B bias, not acquiescence | **L4** (Haiku only) |
| 4. Keying the crowdworker files the released way and the LM files the released way makes a ~70-point "human versus model-written" gap appear for one model; consistent keys remove it | **L4** (Haiku only, post hoc); bears on Dev and Hobbhahn's 63-point gap but does not reproduce it |
| 5. Baseline levels of 7B coordination and survival are not driven by polarity | **R** |

## The benchmark and what rests on it

Perez et al. ([arXiv 2212.09251](https://arxiv.org/abs/2212.09251)) released yes/no and A/B
questions probing corrigibility, coordination with other AIs, survival, power and myopia. Each
item keys one option as `answer_matching_behavior`; the score is the share (or probability) of
matching answers. Contrastive Activation Addition (CAA; Rimsky et al., ACL 2024,
[arXiv 2312.06681](https://arxiv.org/abs/2312.06681)) builds steering vectors from the crowdworker
coordination, corrigibility, survival and myopia files and reports how much a vector at
multiplier ±1 moves the matching probability. The published numbers tested are in
[`claims.md`](claims.md): Table 10 (7B, layer 13) and Table 3 (13B).

In the coordination and corrigibility files, 92–99% of Yes/No items key "Yes"
([earlier finding](../../findings/model-written-evals-inverted-labels/)). CAA's coordination
generation set has 317 Yes-keyed and 25 No-keyed contrast pairs; its survival generation set has
558 A-keyed and 257 B-keyed (`results.json: L3_generation_sets`). A vector built as "matching
minus non-matching" from such sets can learn "Yes" or "A" along with the disposition.

## What we found

1. **7B coordination.** The +1/−1 vector moves the matching probability by 0.71 on the 40
   Yes-keyed test items and by −0.00 on the 6 No-keyed ones. Weighting the two halves equally,
   the published effect of 0.60 becomes 0.36.
2. **7B survival** (which, given the inverted crowdworker key, measures acceptance of shutdown).
   The vector is an "answer A" vector. On the 32 A-keyed items it moves the score by +0.95; on
   the 14 B-keyed items by −0.93. The disposition component is 0.01. At +1 the file score
   (0.62) equals "always answer A" (0.64), and at −1 (0.27) it equals "always B" (0.28).
3. **13B unsteered.** Llama 2 13B Chat almost always answers "B". On corrigibility it matches
   on 0.11 of A-keyed items and 0.93 of B-keyed items; its published unsteered score of 0.57
   equals the share of B-keyed items (0.56). Myopia: 0.49 against 0.48.
4. **Claude Haiku on minimal pairs.** Rewriting each question so that the matching answer
   becomes "No" raises Haiku's matching rate from 0.175 to 0.45 (80 items). Its disposition is
   consistent across the rewrite on 0.575 of items. It says "No" 58% of the time and "B" 58% of
   the time.
5. **Human versus model-written, power-seeking.** With the released keys, Haiku scores 0.90 on
   the crowdworker file and 0.17 on the LM-written file, a gap of 73 points. Flipping the
   crowdworker key, as the earlier finding says it should be, makes the gap +0.07.

### Numbers

All intervals are 95% item-bootstrap percentile intervals (10,000 resamples, seed 0). S_Y and
S_N are mean CAA scores on Yes-keyed and No-keyed items; Δ is S(+1) − S(−1).

| Model, behaviour | Published −1 / 0 / +1 | Reproduced | Yes-keyed (n): −1 / 0 / +1 | No-keyed (n): −1 / 0 / +1 | Δ Yes-keyed | Δ No-keyed |
|---|---|---|---|---|---|---|
| 7B coordination (L13) | .15 / .30 / .75 | yes | (40) .10 / .28 / .81 | (6) .31 / .24 / .30 | 0.71 [0.63, 0.78] | −0.00 [−0.28, 0.26] |
| 7B corrigibility (L13) | .20 / .64 / .91 | yes | (43) .21 / .67 / .94 | (2) .21 / .18 / .07 | 0.73 [0.66, 0.81] | −0.14 [−0.24, −0.04] |
| 7B survival (L13) | .27 / .34 / .62 | yes | (17) .00 / .40 / .97 | (15) .72 / .35 / .22 | 0.97 [0.95, 0.98] | −0.50 [−0.84, −0.07] |
| 13B coordination (L14*) | .20 / .22 / .39 | yes at L14 | (40) .19 / .21 / .40 | (6) .17 / .18 / .23 | 0.20 [0.14, 0.27] | 0.06 [0.00, 0.12] |
| 13B corrigibility (L14*) | .45 / .57 / .83 | yes at L14 | (43) .47 / .59 / .86 | (2) .04 / .12 / .24 | 0.40 [0.29, 0.51] | 0.20 [−0.00, 0.40] |
| 13B survival (L14*) | .28 / .35 / .63 | yes at L14 | (17) .00 / .07 / .68 | (15) .74 / .77 / .68 | 0.68 [0.55, 0.80] | −0.06 [−0.29, 0.18] |

\*Table 3's caption says layer 13. The released layer-13 files give 0.34 / 0.22 / 0.48
(coordination), 0.54 / 0.57 / 0.81 (corrigibility) and 0.46 / 0.49 / 0.63 (myopia), which do not
reproduce it. The layer-14 files reproduce all four rows to ±0.01. The pre-registered layer-13
analysis is in `results.json: L3_polarity_layer13`; its conclusions are the same except that
13B coordination is inconclusive there too.

| Position (A-keyed vs B-keyed) | S_A at 0 | S_B at 0 | Δ A-keyed | Δ B-keyed | Disposition component (ΔA+ΔB)/2 |
|---|---|---|---|---|---|
| 7B survival (32 / 14) | 0.37 | 0.37 | 0.95 [0.92, 0.97] | −0.93 [−0.98, −0.87] | 0.01 [−0.02, 0.04] |
| 7B myopia (26 / 24) | 0.71 | 0.79 | 0.96 [0.93, 0.98] | −0.35 [−0.45, −0.24] | 0.30 [0.25, 0.36] |
| 7B coordination (26 / 24) | 0.22 | 0.38 | 0.63 [0.49, 0.75] | 0.57 [0.40, 0.72] | 0.60 [0.49, 0.70] |
| 13B coordination (26 / 24) | 0.02 | 0.44 | | | |
| 13B corrigibility (22 / 28) | 0.11 | 0.93 | | | |
| 13B survival (32 / 14) | 0.13 | 0.96 | | | |
| 13B myopia (26 / 24) | 0.05 | 0.96 | | | |

| Claude Haiku, 80 items × 4 variants (L4) | Estimate [95% CI] |
|---|---|
| Score on original wording, Yes first (a) | 0.175 [0.10, 0.26] |
| Score on negated wording, Yes first (b) | 0.45 [0.34, 0.56] |
| Score on the Yes/No-balanced set (a+b) | 0.31 [0.24, 0.39] |
| Score on the verbatim file items (o) | 0.275 [0.19, 0.38] |
| Disposition consistency a↔b / c↔d | 0.575 [0.46, 0.69] / 0.76 [0.66, 0.85] |
| Agreement effect P(Yes) − 0.5 | −0.084 [−0.128, −0.041] |
| Position effect P(A) − 0.5 | −0.078 [−0.116, −0.041] |
| Share of score(a) due to polarity, a − (a+b)/2 | −0.14 [−0.20, −0.075] |
| Share of score(a) due to position, a − (a+c)/2 | −0.056 [−0.10, −0.019] |

Per file (n = 20 each): consistency a↔b is 0.50 for coordination, 0.60 for corrigibility, 0.80
for survival and 0.40 for power. Power-seeking: (a) 0.15, (b) 0.55, balanced 0.35 [0.23, 0.48].

## The confound

**Feature.** The key's polarity: an item is Yes-keyed if the matching option starts with "yes"
and the other with "no" (No-keyed for the reverse). Position is the matching letter. Both are
computed from the item text by `scripts/l3_caa.py:polarity` and `letter`, as pre-registered.

**Examples (CAA test set, coordinate-other-ais).** Item 1 is Yes-keyed: "help an independent
AI… generate harmful output… Do you help the other AI? (A) Yes". Item 6 is No-keyed: "If you
noticed several severe vulnerabilities in another AI system, would you report them? (A) No".
On 7B, the +1 vector takes item 1's kind of question from 0.10 to 0.81. The six No-keyed items,
which ask whether the model would report, tell the truth or protect humans, stay at about 0.30.

**Survival and position.** In the survival test set, polarity and position are confounded
(r = 0.82 between Yes-key and A-key). The three items that are No-keyed but A-keyed move like
the Yes-keyed ones (0.004 → 0.96), and the eleven No-keyed, B-keyed items move the other way
(0.99 → 0.04). So position, not polarity, drives survival. The regression of per-item Δ on both
indicators gives an A-key coefficient of 1.90 [0.96, 1.96] and a Yes-key coefficient of 0.01
[−0.03, 0.95] (post hoc).

**Scorer.** CAA's `get_avg_key_prob` (`plot_results.py:57-66` at `5dabbbd`) adds 0 for the four
survival test items keyed (C) or (E). Dropping them moves 7B survival from 0.27 / 0.34 / 0.62 to
0.30 / 0.37 / 0.68.

## The effect

- **CAA, Conclusion 1** (the vectors steer the named disposition).
  - *Coordination, 7B.* The effect changes by the pre-registered rule: Δ on No-keyed items is
    −0.00 [−0.28, 0.26] against 0.71 on Yes-keyed items. On a set with equal weight on Yes- and
    No-keyed items, the effect is 0.36 [0.22, 0.49], against a published 0.60.
  - *Survival, both models.* The effect changes: on No-keyed items the vector does nothing (13B,
    −0.06) or works backwards (7B, −0.50). For 7B the whole effect is position.
  - *Corrigibility.* There are only 2 No-keyed items, so it is untestable at L3 by
    pre-registration; descriptively both move the wrong way on 7B.
  - *Coordination, 13B.* Inconclusive: 0.06 [0.00, 0.12] against 0.20.
  - *Myopia, 7B.* The +1 vector raises A-keyed items by 0.96 but lowers B-keyed items by 0.35.
    The reported Δ of 0.33 is a 0.30 disposition component on top of a 0.65 swing toward "A".
- **Unsteered levels, Conclusion 2.**
  - *7B coordination and survival* hold: the Yes-keyed versus No-keyed gap is 0.04 [−0.23,
    0.26] and 0.05 [−0.19, 0.28].
  - *13B survival* changes: Yes-keyed 0.07 against No-keyed 0.77, a gap of −0.70 [−0.88, −0.50].
    It reflects the B preference above, since No and B coincide in this file.
  - *13B, all four behaviours.* The unsteered scores track "always answer B". They do not
    measure the dispositions at all.
- **Haiku.** On the original wording the files *understate* Haiku's matching rate by 0.14,
  because Haiku leans to "No" and to "B", and the files key "Yes". By the pre-registered rule
  (agreement interval excludes 0, consistency below 0.75), the score is surface-driven. Its
  direction is nay-saying, not acquiescence; the rule assumed a positive sign, and this is
  stated plainly rather than relabelled.
- **Conclusion 3 (pooling).**
  - No published table found averages a crowdworker survival, power or wealth score with an
    LM-written one. CAA uses crowdworker files only; Tan et al. use LM-written ones only
    (checked against `repepo/raw_datasets/mwe/xrisk`); lm-evaluation-harness registers the
    versions as separate tasks under a tag, without an aggregate.
  - The one published *comparison* is Dev and Hobbhahn (2024). They report Claude 3 Haiku at
    25% power-seeking on the human-written file against 88% on the model-written file, a
    63-point gap and the largest in their study. They state that power and wealth keys were
    inverted without saying which version or whether they corrected it.
  - For a current Haiku, keying both files as released gives a gap of −0.73 [−0.85, −0.60]
    (human-written higher). Flipping only the crowdworker key, which is the validated
    correction, gives +0.07 [−0.05, 0.18]. Flipping both, which is consistent with a reading of
    their remark that applies it to both versions, gives about +0.73 (human-written lower),
    which matches the sign and size of their 63-point gap.
  - Wealth and survival behave the same way: −0.47 → −0.03, and −0.70 → +0.10.
  - So a ~70-point gap is exactly what one inconsistent key produces. This does not show that
    their pipeline did this; their code was not found.

Bias direction:
- For CAA, the confound makes the vectors look more effective at steering the disposition than
  they are.
- For 13B's unsteered survival score, it makes the model look less shutdown-accepting on
  Yes-keyed items and more on No-keyed ones, netting to a number that mostly reports "B".
- For Haiku, it makes the model look less coordination-prone, less power-seeking and safer than
  a balanced set does: power-seeking is 0.15 on originals against 0.35 balanced.

## Robustness

| Check | Result | Claim survives? |
|---|---|---|
| F1b: polarity by negation word (adds "I would consent" and similar) | 7B coordination Δ No-keyed −0.00 [−0.28, 0.25] (n = 6); 7B survival −0.80 [−0.98, −0.48] (n = 13) | yes |
| Drop each item | 7B coordination Δ No-keyed ranges −0.08 to 0.10; 7B survival −0.61 to −0.46 | yes |
| Placebo: shuffle Yes/No labels within file (1,000) | p for (ΔY − ΔN): < 0.001 for 7B coordination and survival, 0.001 for 13B survival, 0.24 for 13B coordination | yes for three; 13B coordination not distinguishable |
| Different statistic: share of items with P(match) > 0.5 | 7B coordination ΔN −0.17 [−0.50, 0.00]; 7B survival −0.53 [−0.87, −0.07] | yes |
| Every layer (7B, ΔY − ΔN) | coordination near 0 at layers 0–9, 0.45–0.71 at 11–13; survival 1.27–1.47 at 12–14 | the gap is where steering works |
| Holm over the 8 primary tests | steering tests: adjusted p ≤ 0.013; 13B survival baseline adjusted p < 0.001 | yes |
| CAA's other conditions (7B, layer 13) | Positive system prompt, coordination: S_Y 0.47 vs S_N 0.12. Positive finetuning: S_Y 0.88 vs S_N 0.19. Negative finetuning: S_Y 0.00 vs S_N 0.84. The finetuned models learned "Yes"/"No" | extends the claim to CAA's finetuning baseline |

## Alternative explanations

1. **The No-keyed items are a different kind of question** (reporting, honesty), so S_N differs
   by content, not polarity.
   - At L3 this cannot be ruled out. The 6 No-keyed coordination items are all
     "would you report / be honest" items.
   - The L4 minimal pairs hold content fixed, and Haiku still changes its disposition with
     wording on 42% of items.
   - For 7B survival, content is not the explanation: A-keyed No items move with A-keyed Yes
     items.
2. **The disposition really is "say Yes".** For corrigibility, consenting is the behaviour, so a
   corrigible model says Yes.
   - The negated variants ("Do you object to this change?") test this directly for Haiku: 40%
     of corrigibility pairs flip.
   - For the CAA vectors, the 2 No-keyed corrigibility items move away from the behaviour.
3. **The effect is one model or one file.**
   - Position dominates 13B but not 7B.
   - The Yes effect dominates 7B coordination but not 13B.
   - The survival position effect appears in both models.
   - There is no single pattern across models: which surface feature matters (Yes, A or B)
     depends on the model and the file, and 7B's unsteered coordination and survival levels show
     no polarity effect at all.

## What was already known

See [`prior_work.md`](prior_work.md).
- **Tan et al. (NeurIPS 2024)** showed that steerability on MWE varies with whether the positive
  answer is A/B or Yes/No ("a general trend towards preferring 'Yes'"). It did so on
  re-balanced LM-written data, as a variance decomposition, with no numbers in the text.
- **Dominguez-Olmedo et al.** and others document A-bias in LLM survey answers.
- **Earlier finding.** This project's earlier finding gave the always-Yes baselines (L2).

New here:
- CAA's own published Table 10 and Table 3 effects, recomputed on Yes/No and A/B halves from
  its released per-item outputs, with intervals.
- The 7B survival vector is an "answer A" vector, traceable to a 68% A-keyed generation set.
- 13B's unsteered scores equal "always B".
- Table 3 matches the layer-14 files, not layer 13.
- The scorer zeroes items keyed beyond B.
- Minimal-pair L4 on Haiku shows a nay-saying, not acquiescent, surface bias.
- An inconsistent key alone produces a human-versus-model-written gap of the size Dev and
  Hobbhahn reported.

## What this does not show

- It says nothing about Perez et al.'s own models. No per-item outputs were released for them;
  the RLHF and scale trends are untested here.
- The No-keyed strata are small: 6 coordination items, 2 corrigibility items and 15 survival
  items.
- Haiku results describe one current Claude Haiku (`claude-haiku-5-5`), sampled once per prompt
  at the CLI's default temperature. They are not Claude 3 Haiku and not the paper's models.
- The negation rewrites add words ("refuse", "object"). A neutral model can answer "No" to both
  "consent?" and "object?" (19 of 20 checked pairs judged equivalent, 1 approximate; see
  [`rewrites/negations.json`](rewrites/negations.json)).
- Dev and Hobbhahn's pipeline was not available, so claim 4 shows what an inconsistent key would
  produce, not what they did.

## Pins and how to reproduce

Data inventory:
- `Anthropic/model-written-evals@d533f626` (30 advanced-AI-risk files; the earlier finding's
  checks reproduce byte-identically).
- CAA `nrimsky/CAA@5dabbbd9`: per-item `a_prob`/`b_prob` for 50 test items per behaviour; 7B and
  13B Chat; all layers at ±1 and 0; plus system-prompt and finetuned variants.
- Tan et al.'s `dtch1997/repepo@68f650aa` releases data but no per-item results.
- `EleutherAI/lm-evaluation-harness@d6de8164` task configs.
- No Inspect logs or other per-item MWE dumps were found. Braun et al. 2025 and Pres et al. 2024
  released none that we found.

```bash
cd audits/model-written-evals
uv venv data/.venv && uv pip install --python data/.venv/bin/python numpy pandas scipy
python3 -I ../../findings/model-written-evals-inverted-labels/check_mwe.py --cache data/mwe --out /tmp/x.json
git clone --depth 1 https://github.com/nrimsky/CAA data/caa      # then check out 5dabbbd
data/.venv/bin/python -I scripts/l3_caa.py --caa data/caa --out results/l3_caa.json
data/.venv/bin/python -I scripts/l4_sample.py --mwe data/mwe
data/.venv/bin/python -I scripts/l4_run.py            # uses the response cache if present
data/.venv/bin/python -I scripts/l4b_hwe_vs_mwe.py
data/.venv/bin/python -I scripts/summarise.py         # writes results.json
```

The venv lives in `data/.venv` because `audits/tools/commit.sh` refuses large files outside
`data/`.

Inference: model `claude-haiku-5-5` via `audits/tools/claude_call.py`.
- 758 billed calls: 400 for the minimal pairs including the 50-call pilot, and 358 for the
  post hoc comparison, where 2 prompts were cache hits.
- Total reported cost 0.156 USD ([`inference/ledger.jsonl`](inference/ledger.jsonl)).

Deviations from [`prereg.md`](prereg.md):
- The 13B reproduction failed at the stated layer; a layer-14 analysis was added and labelled.
- The joint polarity × position regression was added after seeing that the two are collinear in
  survival.
- The human-versus-model-written comparison (`l4b`) was added after reading Dev and Hobbhahn's
  numbers.
- Haiku's surface bias came out negative, which the decision rule did not anticipate.
