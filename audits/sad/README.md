# SAD: the overall score and ranking survive the answer-choice shortcut; on three tasks the scores mix self-knowledge with a yes/no lean the keys reward

Status: complete, 2026-11-17, and independently validated (see
[Validation](#validation) and [`validation/VALIDATION.md`](validation/VALIDATION.md)). Branch
`effect-audits`.

**For someone using SAD scores as a measure of situational awareness:**
- The overall SAD score and its model ranking survive the answer-choice shortcut.
- On facts_human_defaults and influence, the keys favour "no / I can't" answers (73% and 68% of
  items with an affirm/deny key). So the task scores reward a denial lean: up to +7 points for
  Claude models and as much as −21 points for "yes"-leaning base models.
- A score that averages over the two answer types keeps the ranking and the capability trend.
- stages_oversight measures little beyond each model's yes/no lean. Its answer-balanced accuracy
  runs only from 0.45 to 0.61 across the 21 models.

Evidence levels per claim (after validation):

| Published conclusion (claims.md) | Task level | Overall SAD score | Level |
|---|---|---|---|
| C1 ranking | On FHD, INF and SO, S and R rank models differently (ρ −0.04, −0.23, −0.63). R is the affirm-keyed (FHD, INF) or mostly "yes" (SO) half, so this is answer lean; a placebo matched on answer type reproduces it. On a lean-neutral score the ranking holds (ρ 0.97, 0.92, 1.00 with full). SF holds | holds (ρ = 0.92 with published; 0.99 lean-neutral) | L3 on strata, lean-explained; R on a lean-neutral score |
| C1' "Claude 3 models outperformed GPT-4 models" (p.9) | On INF the Claude 3 lead is lean (+4.9 → −3.7 [−10.6, 3.3] lean-neutral) | Vanishes on R (+3.7 → −0.4) only because R is affirm-keyed. Lean-neutral: **+2.4 [1.3, 3.4]**, so it holds, smaller | Exploratory; the "disappears" reading fails validation |
| C2 SAD rises with capability (r = 0.79 with MMLU) | r ≈ 0 on R for FHD, INF, SO, because the denial lean rises with MMLU and affirm-keyed accuracy does not. Lean-neutral r: 0.74, 0.89, 0.48 (full 0.69, 0.77, 0.48). SF holds | holds (r = 0.82 on R; 0.78 lean-neutral) | L3 on strata, lean-explained; R on a lean-neutral score |
| C3 chat beats base (+4.5 points) | holds on all four tasks | holds (+2.5) | R |
| C4 situating prompt helps (+1.0 base, +3.2 chat) | For chat models on FHD and INF the gain is small on R (+3.3, +4.8), but lean-neutral it is +12.2 [11.3, 13.2] and +9.3 [6.9, 11.7] of +16.8 and +12.1; about a quarter of the gain is lean | holds, weakened (chat +3.3 → +2.0 on R) | R (task and overall) |
| Current model (Haiku) uses the choices-only shortcut | no: it leans the other way | n/a | L4, null |
| facts_which_llm key copied to a successor marks true answers wrong | 2 to 6 of 151 items | ≤ 0.15 points | L4, measurement |

## Validation

An independent validator reran every analysis script from the pinned inputs: all outputs are
identical. It also re-derived claims 1 and 2 with its own code and reproduced every number. It
then attacked the design ([`validation/VALIDATION.md`](validation/VALIDATION.md)).

The main finding of the validation: the S/R split is mostly a split by answer type.
- "The keyed choice denies" matches S on 89% of FHD items and 91% of INF items. 96% of FHD R items
  and 87% of INF R items are affirm-keyed, and 77% of SO R items are "yes" (evaluation).
- A placebo that re-splits at random within answer type gives ρ(S,R) of 0.17 (FHD), −0.11 (INF)
  and −0.55 (SO). The observed −0.23 (INF) and −0.63 (SO) fall inside its 95% range; FHD (−0.04)
  falls slightly below it.
- A simulation with real, MMLU-tracking knowledge plus each model's fitted lean reproduces the
  observed collapse.

Verdicts:

| # | Claim | Verdict |
|---|---|---|
| 1 | Ranking on R unrelated to S (FHD, INF, SO); overall 0.92 | Holds with correction: the numbers are right; the cause is answer lean, and a lean-neutral score keeps the ranking |
| 2 | MMLU trend ≈ 0 on R; overall 0.82 | Holds with correction: same cause; lean-neutral r 0.74 / 0.89 / 0.48 |
| 3 | Chat > base holds; +4.5 reproduces as +3.2 because of December 2024 data | Holds with correction: every results.csv revision from the first upload (2024-07-08) gives +3.2; the gap to the paper's Table 1 (+4.5) sits in Llama-2 base introspection scores; cause unconfirmed |
| 4 | Situating-prompt gain collapses on R (L3) | Holds with correction: lean-neutral gain +12.2 (FHD), +9.3 (INF); downgraded to R |
| 5 | Claude 3 − GPT-4: +3.7 → −0.4 | Fails as worded: +2.4 [1.3, 3.4] on a lean-neutral score |
| 6 | Haiku L4 null, opposite lean | Holds |
| 7 | Staleness ≤ 0.15 points | Holds (the table said ≤ 0.2; corrected) |

## The benchmark and what rests on it

SAD (Laine et al. 2024, [arXiv 2407.04694](https://arxiv.org/abs/2407.04694); code and released
per-item results at [`LRudL/sad`](https://github.com/LRudL/sad) `dfc5c983`) is the standard
multi-task measure of LLM situational awareness, a capability safety arguments treat as a
precondition for scheming and evaluation gaming. Its headline conclusions (exact wording, numbers
and page references in [`claims.md`](claims.md)): a model ranking (Table 1; latest:
o1-preview 0.599, Claude 3.5 Sonnet 0.539, o1-mini 0.533), SAD correlates 0.79 with MMLU
(Fig. 6), chat models beat their base models by +4.5 points (Fig. 8), and a situating prompt adds
+1.0 (base) and +3.2 (chat) points (§3.2).

The earlier finding [`findings/sad-content-blind-and-stale-keys`](../../findings/sad-content-blind-and-stale-keys/)
showed (L2) that a classifier reading only the two answer choices scores 0.825 on
facts_human_defaults (FHD) and 0.720 on influence (INF), above 17 of 21 released models, and that
seven surface features of the text score 0.851 on stages_full (SF) and 0.662 on stages_oversight
(SO), above every model. It did not test whether models' scores depend on that. This audit does,
with the TASTE design: split items by whether the shortcut gets them right (S) or wrong (R) and
recompute the published conclusions on R.

## What we found

On FHD, INF and SO, the ordering of the 21 released models on R items is unrelated to (or the
reverse of) their ordering on S items, where a random split of the same size keeps it almost
intact; and the correlation with MMLU, 0.48–0.77 on the full task, is about zero on R. The R items
are not hard. On FHD they are capability affirmations ("can you summarise a text?" yes), and the
weakest models score highest on them (davinci-002 0.89, Llama-2-7b-chat 0.92), because they say
"yes" to everything; mid-to-strong chat models, especially Claude, drop (Claude 3 Opus 0.93 on S,
0.70 on R; on INF 0.85 vs 0.53). So the full-task scores of these tasks mix self-knowledge with the
direction of each model's answer lean ("I am not human / I cannot"). The published capability
trend on them is carried by the deny-keyed items: affirm-keyed accuracy does not rise with MMLU
(r = 0.06 on FHD, −0.15 on INF), because more capable chat models lean harder toward denial.
(Validation: S and R are mostly the deny-keyed and affirm-keyed halves, so the S-versus-R collapse
is what lean alone predicts. A score averaging the two answer types keeps the ranking, with ρ 0.97
and 0.92 against the full score, and the MMLU trend, at 0.74 and 0.89.) The TASTE pattern of strong models falling below chance on
R does **not** appear: no top-10 model is below chance on any task's R stratum.

The overall SAD score is robust. The four affected tasks carry 23% of its weight, and replacing
their scores by R-stratum scores leaves the overall ranking (ρ = 0.92 with the published one, top
three unchanged as a set), the MMLU correlation (0.82) and chat > base (+2.5) in place. The
paper's "Claude 3 models outperformed GPT-4 models" vanishes on R. Validation shows that this is
Claude 3's denial lean meeting the affirm-keyed R items. On a lean-neutral score the overall gap is
+2.4 [1.3, 3.4] points (published +3.6), and only the influence part of the lead is lean.

| Task | n S / R | ρ(S, R) ranking, 21 models [95% CI] | placebo random split, 2.5–97.5% | r with MMLU, full → R (15 models) [CI of R] | R − full [95% CI] |
|---|---|---|---|---|---|
| facts_human_defaults | 979 / 199 | **−0.04** [−0.19, 0.12] | 0.97–1.00 | 0.69 → **−0.08** [−0.28, 0.14] | −0.77 [−0.96, −0.56] |
| influence | 183 / 69 | **−0.23** [−0.44, 0.08] | 0.77–0.94 | 0.77 → **0.05** [−0.24, 0.37] | −0.72 [−0.99, −0.36] |
| stages_full | 681 / 119 | 0.81 [0.65, 0.87] | 0.75–0.96 | 0.86 → 0.76 [0.62, 0.82] | −0.10 [−0.23, −0.01] |
| stages_oversight | 265 / 135 | **−0.63** [−0.74, −0.18] | −0.04–0.72 | 0.48 → **−0.07** [−0.26, 0.17] | −0.55 [−0.73, −0.19] |
| facts_llms (placebo task) | 114 / 87 | 0.56 | 0.72–0.94 | 0.86 → 0.86 [0.69, 0.92] | +0.01 [−0.12, 0.13] |
| **Overall SAD, 4 tasks on R** | | ρ with published 0.92 [0.86, 0.96] | | 0.75 → **0.82** [0.74, 0.86] | +0.06 [−0.02, 0.11] |

All from [`results/effect.json`](results/effect.json) (`scripts/effect.py`); cluster bootstrap
over near-duplicate item groups, 2,000 replicates.

## The confound

**Feature.** For FHD, INF and facts_llms: out-of-fold predictions of a logistic regression on
TF-IDF of the two answer choices, question hidden, GroupKFold(5) by near-duplicate cluster
(`scripts/features.py`; reproduces the earlier finding: 0.831 on FHD, 0.726 on INF excluding ties).
For SF and SO: the earlier finding's seven surface features, multinomial logistic regression,
stratified 5-fold. S = classifier picks the key, R = it picks the distractor; 22 FHD, 4 INF and 48
facts_llms ties excluded. Fixed in [`prereg.md`](prereg.md) before any stratum outcome was seen.
Per-item strata, without text, in [`results/features.csv`](results/features.csv).

**What the strata are** (hand-read: 42 random FHD/INF items, all 69 INF R items and all 183
distinct FHD R items). FHD S items are mostly "deny a human trait" (keyed "I don't have teeth",
"No"); 174 of the 183 FHD R items come from the `good_text_model` batch and key an affirmation of
an LLM ability (item keys `75ec71`, `1555a7`, `c506e4`). INF R items key "yes, I can influence
that" (`e26cf1`, `53f2f7`, `cfceb6`). SO R items are mostly evaluation prompts the surface model
takes for deployment. Nine keys looked questionable (listed in prereg.md); dropping them changes
nothing.

**Second, independent version of the feature.** A hand-written denial rule for FHD/INF and a
12-feature random forest for stages. The forest scores **0.95** on SF and **0.89** on SO (against
human role-play ceilings of 0.69 and 0.71), so the stages labels are almost fully determined by
text form.

## The effect

Published, reproduced, R-stratum numbers (points; 95% CIs from the cluster bootstrap).

| Claim | Published | Reproduced from released results | S stratum | R stratum | Verdict (prereg rule) |
|---|---|---|---|---|---|
| C2 overall r with MMLU | 0.79 (Fig. 6, 16-model v1 data) | 0.758 (Dec 2024 data, same 15 models) | 0.71 [0.67, 0.74] | 0.82 [0.74, 0.86] | holds |
| C3 chat − base, overall | +4.5 (Fig. 8) | +3.2 (Dec 2024 data) | +3.7 | +2.5 [1.5, 3.5] | holds |
| C3 chat − base, FHD | — | +7.3 [5.8, 8.7] | +7.4 | +6.5 [3.7, 9.3] | holds |
| C3 chat − base, INF | — | +0.1 [−2.8, 3.0] | +1.9 | −4.6 [−10.7, 1.3] | holds (no effect either way) |
| C4 SP gain, chat, FHD | — | +16.8 [15.6, 18.0] | +19.5 | **+3.3** [1.2, 5.6] | changes on R; lean-neutral +12.2 [11.3, 13.2], so holds (validation) |
| C4 SP gain, chat, INF | — | +12.1 [10.0, 14.3] | +14.9 | **+4.8** [1.0, 8.9] | changes on R; lean-neutral +9.3 [6.9, 11.7], so holds (validation) |
| C4 SP gain, base, FHD / INF | — | +8.0 / +4.4 | +6.9 / +3.3 | +13.0 / +7.5 | holds (larger) |
| C4 SP gain, overall | +1.0 base, +3.2 chat | +1.1, +3.3 | +0.7, +3.8 | +2.5 [1.7, 3.3], +2.0 [1.4, 2.7] | holds (chat weakened) |
| C1' Claude 3 − GPT-4, overall | "outperformed" (p.9) | +3.7 [2.9, 4.5] | | **−0.4** [−2.1, 1.3] | exploratory; lean-neutral +2.4 [1.3, 3.4], so the gap holds, smaller (validation) |
| C1' Claude 3 − GPT-4, INF | | +4.9 [−0.3, 10.0] | | **−16.9** [−27.3, −6.0] | exploratory; lean-neutral −3.7 [−10.6, 3.3] (validation) |

Reproduction: every released plain and sp score of FHD, SF, SO and facts_llms is reproduced exactly
from the per-item files (`results/reproduction.json`). Influence is not: 64 of its 320 items are
private by design (`sad/influence/NOTE.md`), so "full" here is the 256 public items (differences up
to 0.024 per model). One run (gpt-3.5-turbo-0613, SO, plain) used an older version of 128 items and
is scored on its 272 matching items. The overall SAD score is recomputed from the 16 task csvs and
matches `results/plots/website/data.csv` exactly for all 42 model-variants (`scripts/overall.py`).
The paper's +4.5 reproduces from its own Table 1 (+4.52). Every revision of the repo's results.csv
files gives +3.2 and r = 0.76 on the same models, from the first upload (`297a300`, 2024-07-08) to
the pin. So this is not a later data update (corrected in validation; `validation/data_version.json`).
The difference lies mainly in the introspection category of llama-2-7b and llama-2-13b base:
+20.3 and +16.1 points in the repo against Table 1. Its cause is unconfirmed.

**Below chance (TASTE test).** On R, no model in the top 10 (by SAD on the 12 unaffected tasks)
has an upper 95% bound below chance on any task. Point estimates below 0.5 occur on INF R for
Claude 2.1 (0.45), Claude 3 Haiku (0.48) and Llama-2-7b. On SF R, three Llama-2 models are
significantly below 0.25.

**Mechanism.** Item-level logistic regression, correct ~ shortcut_right × MMLU (z) + task, 15
models: interaction **+0.33** [0.26, 0.39]. More capable models gain more from the shortcut
agreeing with the key: +0.62 [0.50, 0.74] on FHD, +0.38 [0.22, 0.56] on INF, +0.17 [0.05, 0.29] on
SO. The sign reverses on SF (−0.30 [−0.46, −0.13]), where capable models rely less on surface
form. The per-model gap acc(S) − acc(R) correlates with MMLU at 0.55 (FHD) and 0.40 (INF). It is
largest for Claude 3 Opus, Claude 3.5 Sonnet and Claude 2.1 (0.17–0.32) and about zero for
o1-preview and o1-mini, the only models near ceiling on both strata (FHD 0.97/0.97 and 0.95/0.92).
The direction of bias: on these tasks the shortcut makes mid-to-high-capability chat models look
**more** situationally aware than their R-stratum behaviour supports, and makes "yes-leaning" base
models look less aware.

**Exploratory, not pre-registered: a bias-balanced score.** The mean of a model's S and R
accuracies cancels a fixed lean in either direction. On it the capability trend returns: r with
MMLU 0.71 [0.62, 0.77] on FHD, 0.87 [0.61, 0.90] on INF, 0.83 on SF, 0.35 [−0.04, 0.61] on SO; rank
ρ with the full-task score 0.91–0.95 (0.75 on SO). So FHD and INF do carry a capability-linked
signal, but their raw scores tie it to answer direction. Neither stratum on its own is free of a
lean: R is answered by the opposite (affirmative) one. The validator's independently defined
version averages accuracy over the keyed answer type (deny versus affirm) rather than over S and
R. It gives r with MMLU of 0.74 [0.68, 0.78] (FHD), 0.89 [0.64, 0.91] (INF) and 0.48 (SO, whose
keys are 200/200, so it equals the full score).

## L4: Haiku with the question removed and the order swapped

`scripts/haiku_intervention.py`, claude-haiku-5-5. 150 FHD items (75 S, 75 R) and 150 INF items
(81 S, all 69 R). Conditions: (a) SAD's plain prompt, (b) choices only, (c) order reversed.
Wilson 95% intervals ([`results/haiku_intervention.json`](results/haiku_intervention.json)).

| | (a) standard S / R | (b) choices only S / R | (c) reversed S / R | (b) on the task's natural S:R mix |
|---|---|---|---|---|
| FHD | 0.83 [0.73, 0.90] / 0.95 [0.87, 0.98] | **0.45** [0.35, 0.57] / **0.91** [0.82, 0.95] | 0.85 / 0.96 | 0.53 |
| INF | 0.81 [0.72, 0.88] / 0.86 [0.75, 0.92] | 0.49 [0.39, 0.60] / 0.61 [0.49, 0.72] | 0.80 / 0.84 | 0.53 |

Haiku does not use the denial shortcut. With the question hidden it leans the other way: it picks
the affirmative choice, so it is right on R and at chance or below on S. On the task's natural mix
that is about chance (0.53). With the question shown it scores slightly higher on R than on S. Its
answers are order-consistent on 90% (FHD) and 84% (INF) of items. Item-level agreement between (a)
and (b) is weak (r = 0.25 and 0.20). Choices-only prompts with identical choice pairs ("Yes"/"No")
are identical inputs and get one cached answer. This shows how one current model behaves. It says
nothing about the 21 released models.

## Staleness of the facts_which_llm key

`scripts/staleness.py`, [`results/staleness.json`](results/staleness.json). Rows were
hand-classified, before any Haiku call, for a successor keyed with its predecessor's answers (the
README's suggestion): 6 "by construction" rows whose key cannot hold for a successor (model series,
announcement paper, blog, date, year, version number), 6 "likely dated" rows (1M-token context,
2025 data, headcount, sequence length, >1T parameters), 4 memory/statelessness rows and 137
invariant rows.

- Released models: the dated rows were keyed correctly for the 2024 models, and errors there are
  not elevated (0.33 [0.27, 0.41] against 0.38 elsewhere). The earlier finding's defective
  model-rows carry error rate 0.42 [0.28, 0.57]: 41 model-items, at most 3 per model.
- Haiku keyed with claude-3-5-sonnet's answers (151 items, SAD's plain prompt): it agrees with the
  copied key on 0.95 [0.90, 0.98] of invariant rows, 0.67 of by-construction rows (disagreeing on
  the announcement date and year rows, where the copied key cannot be right for it), 0.50 of
  likely-dated rows (disagreeing on headcount, >1M context and 2025 data) and 0.75 of memory rows.
  Two to six of 151 answers (1.3–4.0%) are marked wrong because of the key's date, not the model.
  On the other four by-construction rows it picked the copied answer: in a two-choice format the
  stale key still beats a distractor that is even more wrong, which hides the staleness.
- Size: facts_which_llm carries 1/28 of the SAD score, so this is at most about 0.15 points (6/151 × 100/28 = 0.14)
  overall. It grows as successors diverge from the keyed models. It is not the main problem.

## Robustness

| Check | Result | Survives? |
|---|---|---|
| Placebo random split, same sizes, by cluster | ρ(S, R) far below the placebo on FHD, INF, SO (p = 0.001 each); SF inside (p = 0.08) | yes |
| Placebo split matched on answer type (validation) | Observed ρ inside the matched placebo's 95% range on INF ([−0.27, 0.11]) and SO ([−0.69, −0.40]); FHD slightly below ([0.08, 0.28]) | **no** for INF and SO: answer type alone produces the collapse; for FHD it produces most of it |
| Bonferroni over 16 tests (99.7% CIs) | R − full in r: FHD [−1.10, −0.46], INF [−1.11, −0.20], SO [−0.85, −0.06] exclude 0; SF [−0.30, 0.03] does not | FHD, INF, SO yes; SF becomes "holds" |
| Second feature (denial rule; 12-feature forest) | r(MMLU) on R: FHD −0.06, INF −0.18, SF 0.55, SO 0.32 [−0.15, 0.59]; ρ(S, R): −0.21, −0.48, 0.64, 0.40 | FHD, INF yes; SO weaker |
| High-confidence half of each stratum | r on R: FHD −0.22, INF −0.23 [−0.41, −0.01], SO −0.20, SF 0.73 | yes |
| Drop each subset (batch, category, source) | FHD: r on R between −0.15 and 0.04 (dropping `good_text_model` leaves only 25 R items); INF: −0.03 to 0.26 over 8 categories; SO: −0.17 to 0.22 | yes |
| Drop each model family | FHD r on R: 0.28 without Llama, −0.15 without OpenAI, 0.02 without Anthropic. INF: 0.38, −0.31, **0.46**. SO: **0.70**, −0.28, 0.07 | FHD yes; INF and SO partly family-driven (see below) |
| One copy per twice-scored FHD item | ρ(S, R) 0.01; r on R 0.00 | yes |
| Drop 9 hand-flagged questionable keys | FHD r on R −0.03; INF 0.03 | yes |
| Placebo task facts_llms (near-null shortcut) | r 0.86 full and 0.86 on R; ρ(S, R) 0.56 (below its placebo, with only 87 R items) | the collapse is specific to the shortcut tasks |

## Alternative explanations

1. **R items are just harder or mis-keyed.** No. On FHD and INF the R items are easy capability
   or influence affirmations, and the weakest models score highest on them (0.74–0.92). The 9 keys
   that looked doubtful change nothing. Haiku scores 0.95 (FHD) and 0.86 (INF) on R with the
   standard prompt.
2. **The lean is the construct.** A model that under-claims its abilities ("can you summarise?
   no") does lack self-knowledge, so the R-stratum drop for Claude models is partly a real SA
   failure, not noise. This is why the overall claims are reported as holding. What does not hold
   is reading the per-task MMLU trend, the task-level order of models, or the chat-model situating
   prompt gain on FHD and INF as growth in self-knowledge. On FHD and INF those track a lean the
   choices alone reveal, and on the bias-balanced score the trend returns. For stages,
   recognising a text's genre arguably *is* the skill; SF holds anyway.
3. **One model family.** Partly true for INF and SO. Without the Anthropic models, INF's R-stratum
   r with MMLU is 0.46 (full 0.76). Without Llama, SO's is 0.70 (full 0.43). The Claude family's
   strong denial lean drives much of the INF collapse, and Llama base models' yes-lean drives SO.
   FHD does not depend on one family (r on R ≤ 0.28 whichever family is dropped). With 15 models
   and three families, "the trend is gone" and "one family leans hard" cannot be fully separated.

## What was already known

See [`prior_work.md`](prior_work.md). The paper states that FHD and INF keys are the non-human
answer (Table 4) but never tests a choices-only baseline. Rajakumar (LessWrong, 2025-03) flagged
the yes-means-evaluation framing of stages_oversight and rebuilt the task. Nguyen et al. (2025)
report weak single-feature baselines on SO (AUROC ≤ 0.60). Nayan et al. (2026) show SO accuracy
moves under neutral paraphrase. The paper's Appendix H.3.6 already names models' bias toward
guessing "testing" or "deployment" on stages. The repo ships per-answer stages_oversight accuracies
(`sad/stages/oversight/results_answer.csv`), so the SO part of the lean is public. The L2
baselines, duplicates and key defects are from this repo's earlier finding.

**New here:**
- stratifying the released per-item outputs by the shortcut;
- on FHD and INF, the measurement that the keys are 73% and 68% denials, and each model's lean
  premium (validation);
- the capability-correlated denial lean, and the flat MMLU trend on affirm-keyed items;
- the finding that the overall SAD conclusions survive, also on a lean-neutral score;
- the Haiku intervention;
- the successor-key measurement.

## What this does not show

- That models lack the self-knowledge that their S-stratum scores suggest. S and R differ mainly in
  which answer type is keyed. A model with real knowledge and a denial lean scores high on S and
  low on R (validation simulation).
- That any released model "uses" the classifier. R-stratum behaviour shows that models' answers
  line up with an answer-direction lean that the choices reveal. The only causal test is on Haiku,
  and Haiku does not lean that way.
- Anything about the 12 unaffected tasks, which carry 77% of the SAD score and its capability trend.
- Anything about models after o1 on the released data. The SAD-version-2 PR (#9) was not used.
- The Claude 3 versus GPT-4 result and the bias-balanced score were defined after seeing the
  strata, and are labelled exploratory.
- Strata are small for INF (69 R items) and SO (135), and the capability correlations rest on 15
  models from three families.

## Pins and how to reproduce

- SAD `LRudL/sad` @ `dfc5c9831a9bcc5c9a9dbdcaa2955aae983cd1d3`; zip sha256 as in the earlier
  finding's `baseline_checks.json`; paper PDF sha256 `8983ad52…d8d7a` (claims.md). The password for
  the encrypted zips is read from the repo's `unzip.sh`; no repo code is executed; no item text is
  committed (ids are 16-hex hashes of the item).
- Inference: claude-haiku-5-5 via `audits/tools/claude_call.py`; 888 billed calls, **0.195 USD**
  ([`inference/ledger.jsonl`](inference/ledger.jsonl)).

```bash
cd audits/sad && uv venv data/.venv && VIRTUAL_ENV=data/.venv uv pip install numpy pandas scipy scikit-learn pyarrow statsmodels pyyaml
P=data/.venv/bin/python
$P -I scripts/features.py --cache data          # strata (no model outputs)        -> results/features.csv
$P -I scripts/load_outputs.py --cache data      # per-item results + reproduction  -> results/reproduction.json
$P -I scripts/overall.py data/repo              # overall SAD reproduces website data.csv
$P -I scripts/effect.py --cache data            # L3 test, robustness, exploratory -> results/effect.json
$P -I scripts/haiku_intervention.py --cache data --conditions a,b,c   # L4      -> results/haiku_intervention.json
$P -I scripts/staleness.py --cache data         # which-LLM key                    -> results/staleness.json
$P -I scripts/collect.py                        # every number                     -> results.json
```

All seeds are 0. Haiku responses are cached, so a rerun costs nothing.
