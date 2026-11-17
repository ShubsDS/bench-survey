# SAD audit: independent validation

Validator, 2026-11-17, branch `effect-audits`. I did not write the audit. I tried to break its claims.
I did not import any of the auditor's code. I used its per-item strata (`results/features.csv`) only
to define S and R and the near-duplicate clusters. No model inference was run.

Files in this folder:
- [`rerun_auditor.sh`](rerun_auditor.sh) and [`rerun_compare.txt`](rerun_compare.txt): step A.
- [`validate.py`](validate.py), [`validation.json`](validation.json) and
  [`validate_stdout.txt`](validate_stdout.txt): steps B and C (the re-derivation, the answer-type
  attack, the simulation, leave-one-family-out, and claim 5).
- [`data_version.py`](data_version.py) and [`data_version.json`](data_version.json): step E.

All bootstraps resample near-duplicate clusters: 2,000 replicates, seed 20261117. Pins are as in
the audit: SAD `dfc5c983…` (HEAD checked by the script) and paper PDF sha256 `8983ad52…` (checked).

## Verdicts

| # | Claim (as reported) | Verdict |
|---|---|---|
| 1 | Ranking collapses on R for FHD, INF, SO; SF holds; the overall ranking holds (0.92) | **HOLDS WITH CORRECTION.** The numbers reproduce, but they measure lean, not a broken ranking |
| 2 | The MMLU trend goes to about 0 on R for the three tasks; overall holds (0.82) | **HOLDS WITH CORRECTION.** As for claim 1 |
| 3 | Chat > base holds (R); the +4.5 vs +3.2 gap is due to the December 2024 data | **HOLDS WITH CORRECTION.** The verdict holds; the explanation is wrong |
| 4 | Situating-prompt gain for chat models collapses on R for FHD and INF (L3) | **HOLDS WITH CORRECTION.** It is mostly not lean; downgrade to R |
| 5 | Claude 3 minus GPT-4 overall: +3.7 → −0.4 | **FAILS** as a finding; reworded in the README |
| 6 | Haiku L4 null: it leans the other way (0.45 S / 0.91 R choices-only) | **HOLDS** |
| 7 | Staleness ≤ 0.15 SAD points | **HOLDS WITH CORRECTION.** The README table said ≤ 0.2 |

## A. Rerun of the auditor's scripts

I ran every analysis script into a scratch tree from the pinned clone:
- `features.py`, `load_outputs.py`, `overall.py` and `effect.py`;
- `haiku_intervention.py` (full run and pilot) and `staleness.py`, against a copy of the response
  cache with the CLI path set to a nonexistent binary, so a cache miss would fail;
- `collect.py`.

Results ([`rerun_compare.txt`](rerun_compare.txt)):
- `reproduction.json`, `effect.json`, `haiku_intervention.json`, `haiku_pilot.json`,
  `staleness.json` and `results.json` are identical apart from the cache-cost fields (0 USD on a
  cached run).
- `features.csv` is identical except for the names of 15 cluster labels. The union-find root
  depends on Python's hash seed. The cluster partition is the same.
- `overall.py` matches the website's `data.csv` for all 42 model-variants.
- Every Haiku call was a cache hit.

## B. Independent re-derivation of claims 1 and 2

My own code covers the whole chain:
- item loading from the extracted zips;
- per-item credit from the released eval-result JSONs, matched to `results.csv` by timestamp, with
  SAD's chance credit for invalid answers. This reproduces every released score of the four tasks
  to < 0.001, except influence, where 64 items are private;
- my own overall aggregation (max difference from the website `data.csv`: 0.000);
- MMLU parsed as text from `sad/correlations.py`.

| | Auditor | Validator |
|---|---|---|
| ρ(S,R) FHD | −0.04 [−0.19, 0.12] | −0.043 [−0.19, 0.13] |
| ρ(S,R) INF | −0.23 [−0.44, 0.08] | −0.226 [−0.43, 0.10] |
| ρ(S,R) SO | −0.63 [−0.74, −0.18] | −0.627 [−0.74, −0.18] |
| ρ(S,R) SF | 0.81 | 0.806 [0.65, 0.87] |
| Random-split placebo FHD / INF / SO | 0.97–1.00 / 0.77–0.94 / −0.04–0.72 | 0.97–1.00 / 0.77–0.95 / −0.04–0.73 |
| r(MMLU) full → R, FHD | 0.69 → −0.08 | 0.692 → −0.076 [−0.27, 0.15] |
| r(MMLU) full → R, INF | 0.77 → 0.05 | 0.767 → 0.046 [−0.22, 0.38] |
| r(MMLU) full → R, SO | 0.48 → −0.07 | 0.484 → −0.068 [−0.26, 0.17] |
| Overall, 4 tasks on R: ρ with published | 0.92 [0.86, 0.96] | 0.918 [0.86, 0.96], same top three |
| Overall r(MMLU), published → R | 0.75 → 0.82 | 0.758 → 0.815 [0.74, 0.85] |

Every number reproduces. The auditor's overall "full" uses influence on its 256 public items,
which gives 0.752; on the released 320-item scores it is 0.758.

## C. The answer-type attack on the central design

**1. S/R is mostly a split by answer type.** I labelled each item by whether its key affirms or
denies:
- yes/no keys by their first word;
- otherwise by a negation and negative-quality lexicon over both choices;
- items where both or neither choice reads negative are "other";
- SO: key "yes" (evaluation) or "no" (deployment).

| Task | Deny-keyed share of typed items | Agreement "deny-keyed = S" | R that is affirm-keyed | S that is deny-keyed |
|---|---|---|---|---|
| FHD | 0.73 (777 deny, 283 affirm, 140 other) | 0.89 | 0.96 (175/183 typed) | 0.88 (769/876) |
| INF | 0.68 (115 / 54 / 87 other) | 0.91 | 0.87 (45/52) | 0.92 (108/117) |
| SO | 0.50 (200 / 200) | 0.68 | 0.77 "yes" (104/135) | 0.64 "no" (169/265) |

On FHD and INF, R is essentially "the affirm-keyed items". On SO it is mostly "the yes
(evaluation) items". The prereg's own hand check already said this for FHD.

**2. A better null: a placebo split matched on answer type.** I re-split at random within each
answer type, keeping each type's S and R counts. This null keeps the answer-type imbalance and
removes everything else the classifier knows.

| Task | Observed ρ(S,R) | Random-split placebo (audit's null) | Answer-type-matched placebo, 2.5 / 50 / 97.5% | ρ(deny-keyed, affirm-keyed) |
|---|---|---|---|---|
| FHD | −0.04 | 0.97–1.00 | 0.08 / 0.17 / 0.28 | −0.12 |
| INF | −0.23 | 0.77–0.95 | −0.27 / −0.11 / 0.11 | −0.46 |
| SO | −0.63 | −0.04–0.73 | −0.69 / −0.55 / −0.40 | **−0.87** |
| SF (four labels) | 0.81 | 0.76–0.96 | 0.69 / 0.80 / 0.88 | n/a |

- On INF and SO, answer type alone reproduces the observed collapse; the classifier adds nothing.
- On FHD, answer type takes ρ from 0.99 to 0.17, and the classifier's extra information takes it
  to −0.04. So a small part of the FHD collapse goes beyond answer type.
- On SO, models that do well on "yes" items do badly on "no" items (ρ = −0.87). Accuracy on SO is
  mostly each model's yes/no lean.

The random-split null is the wrong comparison for a design whose strata differ by answer type.

**3. Simulation: real knowledge plus lean.** Each model gets a knowledge index k and a lean p:
- k: it knows the answer with probability k. I set k = acc(deny-keyed) + acc(affirm-keyed) − 1.
- p: otherwise it picks the denial with probability p.

I simulated binomial outcomes on each task's real cell counts (S/R × deny/affirm):

| | FHD ρ(S,R) | FHD r(R, MMLU) | INF ρ(S,R) | INF r(R, MMLU) | SO ρ(S,R) | SO r(R, MMLU) |
|---|---|---|---|---|---|---|
| Observed | −0.04 | −0.08 | −0.23 | 0.05 | −0.63 | −0.07 |
| Fitted k and lean (median [95%]) | 0.07 [−0.05, 0.18] | 0.12 [−0.01, 0.24] | −0.23 [−0.39, −0.06] | −0.01 [−0.26, 0.22] | −0.55 [−0.76, −0.35] | −0.16 [−0.37, 0.07] |
| Same k, no lean | 0.96 | 0.71 | 0.75 | 0.63 | 0.31 | 0.23 |
| Same k, leans shuffled across models | 0.15 | 0.38 | −0.11 | 0.31 | −0.52 | 0.50 |

- The knowledge index k correlates with MMLU at 0.74 (FHD), 0.89 (INF) and 0.48 (SO).
- Knowledge that is real, varies across models and rises with MMLU, plus the observed leans,
  reproduces the observed rank collapse.
- The rank collapse (ρ(S,R)) needs only lean dispersion. It appears even when lean is independent
  of capability: in the generic simulation, lean SD 0.2–0.3 gives median ρ of 0.08 to −0.26 on FHD's cell counts.
- r(R, MMLU) ≈ 0 additionally needs the lean to be capability-correlated. The pull toward denial
  correlates with MMLU at 0.38 (FHD), 0.40 (INF) and 0.28 (SO). Accuracy on affirm-keyed items does
  not rise with MMLU: r = 0.06, −0.15 and −0.20.

So claims 1 and 2 do not show that the benchmark's task-level ranking or trend is broken. They show
three things:
- per-stratum scores are lean-contaminated;
- more capable chat models (especially Claude) lean harder toward denial;
- on affirm-keyed items, capability buys no accuracy.

The last point is a real, narrower finding.

**4. A score balanced by answer type** (mean of deny-keyed and affirm-keyed accuracy; my
definition, not the auditor's S/R mean):

| | FHD | INF | SO |
|---|---|---|---|
| r(MMLU), published-style full score | 0.69 | 0.77 | 0.48 |
| r(MMLU), type-balanced [95% CI] | **0.74** [0.68, 0.78] | **0.89** [0.64, 0.91] | 0.48 [0.13, 0.67] (identical: SO is 200/200) |
| Auditor's S/R-balanced (exploratory) | 0.71 | 0.87 | 0.35 |
| Spearman, type-balanced vs full | 0.97 | 0.92 | 1.00 |

**5. How much of the published task score is lean.** On FHD and INF the keys are 73% and 68% deny.
A model's lean premium is its count-weighted score on typed items minus its type-balanced score.

| | FHD | INF |
|---|---|---|
| Largest gain from denial lean | Claude 2.1 +6.9, Claude 3 Opus +5.6, Claude 3.5 Sonnet +3.7 | Claude 3 Opus +7.2, Claude 2.1 +5.3, Claude 3.5 Sonnet +5.2 |
| Largest loss from "yes" lean | Llama-2-7b-chat −21.4, davinci-002 −20.5, Llama-2-13b −16.2 | Llama-2-7b-chat −16.4, davinci-002 −15.5 |
| o1-preview, o1-mini | +0.2, +0.5 | −2.1, −2.5 |
| r(premium, MMLU) | 0.47 | 0.46 |

This is what an imbalanced task rewards. It is the real finding behind claims 1 and 2.

Overall SAD with FHD, INF and SO replaced by their type-balanced scores:
- ρ with the published ranking: 0.987;
- r(MMLU): 0.776, against 0.758 published;
- same top three, though o1-mini moves above Claude 3.5 Sonnet (as it does on R);
- per-model change: at most 2.5 points (Llama-2-7b-chat +2.5); the Claude 3 models lose 0.5–0.7.

SO is answer-balanced, so its published score carries no lean premium. But its type-balanced
accuracy runs only from 0.45 (Llama-2-13b) to 0.61 (gpt-4-base). Most models are near chance once
their lean is removed.

**6. Pre-registration timing.** `prereg.md` was committed once, in `9b54f84` (11:01:00). That
commit also holds `features.csv` and `reproduction.json`. `effect.py` and `effect.json` follow in
`2a685e2` (11:06:01), and prereg.md was never edited afterwards. So S/R was fixed before the
stratum results were committed.

Two caveats:
- `data/outcomes.parquet` (per-item outcomes) existed before the prereg (written at 10:59), so
  "before looking" cannot be checked from git.
- The prereg itself records that the FHD R stratum is affirmations. The answer-type confound was
  known before any outcomes, and the chosen null did not control it.

The S/R-mean "bias-balanced" score was defined afterwards, and the README labels it exploratory.

**7. Leave one family out** (validator's numbers match the audit's where both exist):

| Dropped | FHD ρ(S,R) / r(R) / r(balanced) | INF ρ / r(R) / r(bal) | SO ρ / r(R) / r(bal) |
|---|---|---|---|
| none | −0.04 / −0.08 / 0.74 | −0.23 / 0.05 / 0.89 | −0.63 / −0.07 / 0.48 |
| Llama | 0.27 / 0.28 / 0.49 | −0.26 / 0.38 / 0.67 | −0.52 / **0.70** / 0.49 |
| OpenAI | −0.39 / −0.15 / 0.84 | −0.61 / −0.31 / 0.87 | −0.67 / −0.28 / 0.29 |
| Anthropic | 0.02 / 0.02 / 0.76 | 0.24 / **0.46** / 0.95 | −0.59 / 0.07 / 0.52 |

The audit's family statements hold:
- the INF collapse of r(R) depends on Anthropic;
- the SO collapse of r(R) depends on Llama;
- FHD does not depend on one family.

The SO rank collapse ρ(S,R) survives every drop (−0.52 to −0.67), as a pure lean effect would.

## D. Claim 5 (Claude 3 minus GPT-4)

| | Overall gap, points [95% CI] | INF | FHD |
|---|---|---|---|
| Published (released csvs) | +3.6 (auditor +3.7 using 256 INF items) | +4.9 | +6.8 |
| Four tasks on R | −0.4 [−2.0, 1.3] | −16.9 | −3.1 |
| FHD, INF, SO type-balanced | **+2.4 [1.3, 3.4]** | −3.7 [−10.6, 3.3] | +3.1 [0.9, 5.5] |

The gap "disappears" on R because R is the affirm-keyed half, and Claude 3 leans toward denial. On a
lean-neutral score the overall gap shrinks by about a third and stays clearly positive. What
survives:
- on influence, the Claude 3 lead is lean (type-balanced −3.7, interval includes 0);
- about 1.2 of the 3.6 overall points come from lean on these tasks.

Verdict: FAILS as worded ("disappears"). Keep it only as an exploratory, reworded note (done in
the README).

## E. Claim 3: the reproduction gap

The README attributed +4.5 (paper) versus +3.2 (repo) to "the repo's December 2024 data". The repo
history does not support this. I recomputed chat − base from every commit that changed any task's
`results.csv` ([`data_version.json`](data_version.json)):
- The first upload, `297a300` (2024-07-08, three days after arXiv v1), already gives **+3.19**
  (pairs −2.73, 2.54, 4.32, 6.43, 5.38) and r(MMLU) = 0.758.
- So does every later commit, through `dfc5c98` (2024-12-14). The October and December commits
  add models but do not change these.
- The paper's own Table 1 gives +4.52 (pairs −0.1, 5.4, 5.3, 6.4, 5.6), so +4.5 reproduces from
  the paper.
- The difference is between the paper's Table 1 and every released csv. It sits mainly in the
  introspection category of the Llama-2 base models: repo minus paper is +20.3 (7b) and +16.1
  (13b), giving +2.9 and +3.0 on their overall SAD; other categories differ by ≤ 1.3.
- No changelog explains it. The cause is unconfirmed.

The chat > base verdict on R (+2.5 [1.5, 3.5]) is unaffected. By answer type the chat advantage is
+8.3 (FHD), +2.5 (INF) and +0.9 (SO) on type-balanced scores.

## C4 (situating prompt) by answer type

| Chat models, sp − plain, points | Full | R | Deny-keyed | Affirm-keyed | Type-balanced [95% CI] |
|---|---|---|---|---|---|
| FHD | +16.8 | +3.3 [1.3, 5.6] | +21.6 | +2.8 | **+12.2** [11.3, 13.2] |
| INF | +12.1 | +4.8 [0.8, 8.8] | +15.6 | +3.0 | **+9.3** [6.9, 11.7] |
| SO | −0.1 | +0.6 | −1.1 | +1.1 | 0.0 [−2.5, 2.6] |

- The prompt does push toward denial: the lean component is +9.4 (FHD) and +6.3 (INF).
- But affirm-keyed accuracy also rises, and the lean-neutral gain is about 70–75% of the full gain.
- "The situating-prompt gain lives on S items" is true of the strata. The prompt still raises
  lean-free accuracy by 9–12 points.

Verdict: the R-stratum numbers stand. The task-level conclusion becomes R (holds, about a quarter
of it is lean), not L3.

## F. Novelty

Checked against the paper text, the repo issues page (#4–#8; none on answer bias), the Rajakumar
post (fetched) and a web search.

Already public:
- **SO answer bias.** Paper Appendix H.3.6 says many models have "a bias towards guessing that they
  are in testing or deployment". The repo ships per-answer SO accuracies, in
  `sad/stages/oversight/results_answer.csv`. Rajakumar (2025) rebuilt SO with randomised label
  order to remove the yes = evaluation confound.
- **FHD/INF keyed answer.** That the key is the non-human answer is by design (Table 4).

Not found anywhere:
- the denial imbalance of FHD/INF keys (73% and 68%) and the per-model lean premium;
- that the S/R split reduces to answer type;
- the capability-correlated denial lean;
- that affirm-keyed accuracy does not rise with MMLU.

So the SO part of the audit's L3 finding is a restatement of a public bias. The FHD/INF lean
quantification is new.

## G. Fair one-line conclusion

For someone using SAD scores as a measure of situational awareness:

> The overall SAD score and its model ranking survive the answer-choice shortcut. But on
> facts_human_defaults and influence the keys favour "no / I can't" answers (68–73%), so task scores
> reward a denial lean: up to +7 points for Claude models and up to −21 for "yes"-leaning base
> models. A lean-neutral score keeps the ranking and the capability trend. stages_oversight
> measures little beyond each model's yes/no lean.

## Changes made to `audits/sad/README.md`

1. Title and lead replaced with the conclusion above. The old title said the capability trend and
   model order "vanish".
2. Added a "Validation" section near the top with the verdicts.
3. Status table:
   - C1 and C2 levels: "L3" → "L3 on strata; lean-explained, R on a lean-neutral score".
   - C1' row: "disappears" → "shrinks to +2.4 on a lean-neutral score; fails validation".
   - C4 level: "L3 (task)" → "R (task; about a quarter of the gain is lean)".
   - Staleness: "≤ 0.2 points" → "≤ 0.15 points".
4. "What we found": the sentence "the published capability trend on them is carried by the S
   items" now says it is carried by deny-keyed items, with the lean-neutral trend. The sentence
   "One overall-level claim does move: Claude 3 > GPT-4" is corrected.
5. Effect section: the data-version sentence ("The paper's +4.5 and 0.79 are from the July 2024
   data … SAD's own updates") is replaced with the repo-history finding.
6. "What was already known" now notes the paper's H.3.6 and `results_answer.csv`. The "New here"
   list drops the Claude 3 vs GPT-4 "disappearance".
