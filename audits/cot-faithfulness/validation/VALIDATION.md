# CoT faithfulness (ChainScope IPHR) audit: independent validation

Validator, 2026-11-17, branch `audits-round2`. I did not write the audit; I tried to break it. The
auditor's last commit was `6ce6c9b` and nothing was added after it. My pre-registration
([`prereg_validation.md`](prereg_validation.md), commit `284b2e2`) was committed before I read the
auditor's hand labels or ran any of the analyses below. My blind labels were committed (`0cbc736`)
before I unblinded them. No inference was run (0 USD); the Haiku check re-parses the auditor's cache.

Files: `v_core.py` (my own rule implementation, written from `make_faithfulness_ds.py:197-323` and
`make_df.py:84-120`, not from `iphr_core.py`), `v_reproduce.py`, `v_nulls.py`, `v_extract.py`,
`v_sample.py` + `hand_key.csv` + `hand_labels.csv` (my blind draw), `v_sample_aud.py` +
`hand_key_aud.csv` + `hand_labels_aud.csv` (blind relabel of 30 of the auditor's items), `v_hand.py`,
`v_flip.py`, `v_intervals.py`, `v_versions.py`, `v_l4.py`, `v_misc.py`, `v_dropped.py`; all numbers in
[`validation.json`](validation.json). Seeds are fixed in each script.

**Pins.** The two pickles, `make_faithfulness_ds.py`, `make_df.py`, `typing.py`, `gen_cots.py`, all 103
`faithfulness/` and 103 `unfaithfulness_pattern_eval/` files match their git blob sha at
`chainscope@bb128ac0` (206/206; the script's blob sha also checked against the live GitHub API). I
re-downloaded arXiv e-prints v1–v6; v1, v4 and v6 match the auditor's sha256. I also fetched 20
Claude 3.7 Sonnet response/eval files (blob shas checked) for the 27 pairs the authors' autorater did
not cover.

**Rerun.** `analyse.py`, `posthoc.py`, `posthoc_flip.py`, `posthoc_c2.py`, `posthoc_routes.py` and
`posthoc_sr_partner.py` were rerun in a scratch copy; see "Rerun" below.

## Verdicts

| # | Auditor's statement | Verdict | Validator's number | How checked |
|---|---|---|---|---|
| 1a | Released counts reproduce the published table | **Confirmed** | 16/16; the 8 oversampled models' published count = oversampled pairs; published % = count/4,892 | own rule (`v_reproduce.py`) |
| 1b | No-lean null N0 flags 0.0–0.3 pairs per model | **Confirmed** | 0.0–0.36 (mean over 500) | own null (`v_nulls.py`) |
| 2a | Template-lean null N1t reproduces the counts (Spearman 0.99; 14/16 within ±20%) | **Confirmed, reworded** | Spearman 0.999; 14/16; outside: R1 0.67×, Gemini 2.5 Pro 0.53× | own null. N1t takes each pair's error rate from the same samples that select it, so matching counts is close to built in; it is not evidence against the paper |
| 2b | Pair-specific inconsistency beyond template lean in 16/16 models | **Confirmed** | 16/16 (own dispersion statistic: obs 1.55–3.89 vs null 97.5% 1.07–1.31) | own test, different statistic |
| 3a | 85% of Claude 3.7 Sonnet's wrong answers are flips (autorater); hand check "about 71% [43, 85]" | **Confirmed; hand estimate corrected upward** | my blind random draw: 27/30 = 90% [74, 97]; dropped pairs 10/10; with label disagreement propagated [80, 100] | own blind labels |
| 3b | Without flip-dominated pairs, 3.7 Sonnet − 3.5 Sonnet v2 goes +1.06 → −0.12 [−0.50, 0.14] | **Confirmed**, placebo-supported | −0.12 [−0.50, 0.13]; below all 1,000 within-template label shuffles (placebo median +0.56) | `v_flip.py` |
| 3c | 3.7 Sonnet − 3.7 Sonnet 1k goes +1.26 → +0.06 [−0.04, 0.21] | **Confirmed at the auditor's threshold; threshold-dependent** | +0.06 [−0.04, 0.20] at ≥ 50%; at ≥ 75% +0.21 [0.02, 0.42]; requiring all wrong answers flipped +0.27 [0.04, 0.55] | threshold sweep |
| 3d | Rank 8th → 15th, Spearman 0.91 | **Confirmed** | 8 → 15; the only model moving > 2 places; Spearman 0.90 (vs published) / 0.91 (vs released) | `v_flip.py` |
| 3e | "Size of answer flipping by model" is new; answer flipping "recorded only per response" | **Failed (novelty)** | v5/v6 Table `tab:iphr-answer-flipping` already reports per-model answer-flipping prevalence: Claude 3.7 Sonnet 93.7% of unfaithful pairs, 3.5 Sonnet v2 25%, 1k 0% | paper source |
| 4a | 55% [43, 67] of wrong answers are not justifications | **Confirmed point; interval widened** | 53% [41, 65] (weights: all wrong answers); 54–55% under two other weightings, intervals up to [35, 71]; [33, 71] with label noise | own blind sample, n = 94 |
| 4b | Composition: flips 16%, stated guesses 21%, "not directly" rule 18% | **Corrected** | flips 17–26%, guesses 7–9%, rule 19–30% (by weighting). The authors' own `lack_of_information` label: 10.4% (1,603 of 15,460 labelled wrong answers) | own labels; authors' autorater |
| 4c | Guesses and the rule are "not rationalisation" | **Downgraded to a contested reading** | see "Do guesses and the rule count?" | paper definitions |
| 5 | Template intervals 1.1–5.6× wider; base > instruct +1.18 [−0.34, 3.00]; V3 > R1 +0.87 [−0.06, 1.92] | **Confirmed numbers; wording corrected** | 1.1–5.8× (3.2–5.8× for ≥ 60 pairs); +1.18 [−0.37, 2.83]; +0.87 [−0.07, 1.99]; property bootstrap (29) similar | `v_intervals.py`. The paper does not claim significance for either; "V3 > R1" is not a stated comparison |
| 6 | Threshold 20% → 50% between versions; v4's change list "does not list it" | **Corrected** | The change happened at v2 (13 Mar 2025, two days after v1). v2's criteria text states 50% and v2's rates are the 50% rates (3.7 Sonnet 30.6 → 16.3%, reproduced exactly). No version flags it as a change; v4's appendix compares with "v1 to v3" together and names only the dataset | v1–v6 sources; `v_versions.py` |
| 7 | Oversampling check uses threshold 0.4; at 0.5 retention 50–61% | **Confirmed** | 3.5 Sonnet v2 12/22, 3.7 Sonnet 45/90, 64k 7/12, R1 11/18, GPT-4o 9/18, ChatGPT-4o 13/24 | `v_misc.py`; paper says "the same criteria" |
| 8 | Ground truth 47/47 correct | **Not checked** | – | – |
| 9 | Haiku: yes/no same-answer 24% vs forced-choice order-inconsistent 5%; diff 0.19 [0.11, 0.26] | **Confirmed with correction** | re-parsed: 0 unparsed (11 were parser misses on names with suffixes), 2 refusals, 7/115 inconsistent; diff 0.17 [0.10, 0.24] | `v_l4.py` |
| – | Exact ties: 89 of Haiku's 363 flags on the threshold; stated rule adds ≤ 2% | **Confirmed** | 89; +8 pairs for Haiku, ≤ 1 elsewhere | `v_misc.py` |

## What I corrected and why

**Hand labels (claim 3a, 4).** My own draw: 94 wrong answers from the released flagged sets, one
per pair, 30 from Claude 3.7 Sonnet and 4–8 from each other model, restricted to responses the
authors' autorater labelled (for oversampled pairs this is the authors' random proportional sample
of 10 per question, `unfaithfulness_patterns_eval.py:29-109`), plus 10 from the 27 Claude 3.7 Sonnet
pairs that the autorater never saw. Model and verdicts were hidden. One caveat on blinding: before
labelling I saw the aggregate autorater flip count of the sample (28/30 for 3.7 Sonnet), not
item-level labels.

- Claude 3.7 Sonnet: FLIP 27/30 (90% [74, 97]), GUESS 2, FACT 1. Autorater on the same items:
  28/30. The auditor's 71% came from reweighting 12 items, 6 of them autorater-"no": my relabel of
  those 12 agrees with the auditor on 11 (I call one LOGIC item a flip), giving 6/6 flips among
  autorater-"yes", so their own items imply ≈ 85%, not 71%.
- Agreement with the autorater (FLIP vs not, n = 94): precision 0.83, recall 0.97, κ = 0.82. The
  auditor's "precision 16/30" came from a sample that oversampled autorater-"yes" items in models
  where it misfires; on 30 of their items relabelled blind I agree with their FLIP/not call on 28
  (κ 0.84; 25/30 exact on the five categories, κ 0.78). The disagreement is about sample
  composition, not labeller.
- Pooled: not-justification 53% [41, 65]; flips 26%, guesses 8%, rule 19%, facts 41%, logic 6%
  (weights: all wrong answers in flagged pairs). Results by weighting are in `v_hand.json`; GPT-4o-mini
  (3 of 4 items RULE) carries a large weight, which is why the rule share and intervals move.
  Four items per model make every per-category number a lead.

**Do guesses and the rule count as rationalisation? (claim 4c).** The paper defines unfaithfulness
at the pair level: behaviour "inconsistent with any single, stable reasoning rule, even if each
individual CoT looks locally coherent" (v6 §2). Under that definition a template-biased guess still
counts; the authors' pattern prompt explicitly excludes stated guesses from *answer flipping*
(`unfaithfulness_patterns_eval.py:170-185`) but not from the pair being unfaithful. "Not a
justification" is fair; "not unfaithful" would not be. The "not directly south" rule is the
paper's own headline example of *argument switching* ("inconsistently applying geographical
standards", Fig. 1 and the pattern prompt) when it is applied in one variant only. Only when it is
applied to both variants is it a stable rule that the definition excludes, and then the pair is a
residual-ambiguity case. The auditor's own partner check (47% by regex, a lower bound) says both
kinds are present. So the 18% is contested, and I did not re-derive the partner check.

**Answer flipping is the paper's own result (claim 3e).** The v5 and v6 appendix (§"Other", Table
`tab:iphr-answer-flipping`) gives answer-flipping prevalence per model with intervals: Claude 3.7
Sonnet 93.7% of unfaithful pairs (= 59/63, the released set), 3.5 Haiku 67.5%, GPT-4o-mini 68.8%,
3.5 Sonnet v2 25.0%, 1k 0%. The README's statements that answer flipping "is recorded only per
response" and that its by-model size is new are wrong. The paper's main text still calls it
"less prevalent" (v6 §2.2), which does not fit its own table for these models. What the audit adds:
(i) the effect on the two Claude comparisons and the rank; (ii) the check that it is not a
removal artefact (placebos below); (iii) the observation that the main-text wording and the
"Claude 3.7 Sonnet vs 3.5 Sonnet v2" sentence ignore that table. From the paper's own numbers
alone, 90 × (1 − 0.937) ≈ 6 non-flip pairs for 3.7 Sonnet against 22 × 0.75 ≈ 16 for 3.5 Sonnet v2.

**Flip split (claim 3b–d).** The auditor defines a pair as flip-dominated when ≥ 50% of its
autorater-labelled wrong answers are flips (`posthoc_flip.py`), written after the flip shares were
seen; nothing in `prereg.md` defines it. My checks:
- *Threshold sweep*: 3.7 Sonnet − 3.5 Sonnet v2 is −0.12, −0.10, −0.12, +0.02, +0.08 pp at "any",
  25%, 50%, 75%, 100%, never distinguishable from zero. 3.7 Sonnet − 1k is +0.04, +0.06, +0.06,
  **+0.21 [0.02, 0.42]**, **+0.27 [0.04, 0.55]**: at strict thresholds a gap of about a sixth of the
  original survives.
- *Random removal of the same number of pairs per model* gives exactly the same result (5 vs 11 vs
  2 pairs, all 1,000 draws), as the auditor said. It cannot be the control.
- *Label shuffle within template across the 16 models* (keeps each template's flip prevalence and
  each pair's number of wrong answers): placebo 95% ranges +0.43 to +0.70 and +0.62 to +0.89; the
  observed −0.12 and +0.06 fall below all 1,000 draws. A feature of the same prevalence that is not
  tied to the model does not remove the leads.
- *Matched placebo categories from the same autorater*: removing pairs dominated by
  argument-switching evidence (32% of answers), lack-of-information (10%) or fact-manipulation
  (51%) leaves the leads at +0.99/+1.18, +1.01/+1.22 and +1.16/+1.20 pp, all with intervals above 0.
- *Label shuffle within model* reproduces the observed result. The effect is carried by how often
  each model flips, not by which pairs the flips fall in.
- *Subset*: the autorater covers the 63 pairs retained at 100 responses, not the 90 published. The
  27 dropped pairs have a smaller gap at 100 responses (0.30 vs 0.58). My blind labels of 10 wrong
  answers from them are 10/10 flips, so the covered subset does not overstate the flip share; if
  anything it is the same or higher off the subset. Within covered pairs the authors sample responses
  at random.

So the flip result for the two Claude comparisons survives the placebo. It remains post hoc and
depends on reading answer flips as a different kind of unfaithfulness. The paper counts flips as
unfaithful, and the comparison "3.7 Sonnet is less faithful" is literally true under its definition.
The audit shows that the excess is flips, not rationalisation.

**Intervals (claim 5).** There are 58 templates (2–100 pairs each) in 29 properties. The template
is a defensible resampling unit, because the group bias that defines a flag is computed per template.
The property bootstrap gives similar intervals. The paper's error bars are "95% bootstrap CIs over
question pairs" (v6 Fig. 2 caption), not binomial; in effect they are the same. The paper never
claims significance. For Llama it draws an inference from the point gap ("suggests that this form of
unfaithfulness is not fully explained by RLHF-induced sycophancy alone"). It never states
DeepSeek V3 > R1; the nearest claim is "thinking models generally exhibit improved faithfulness"
(v6 §5). The correct wording is that template-level noise covers the gap behind the RLHF
inference, not that a significant result was lost.

**Threshold change (claim 6).** v1 (11 Mar 2025) says "at least 20%"; v2 (13 Mar) and v3 say "at
least 50% … 15 out of 20 responses"; v4–v6 say 50%. On the v1 dataset my code gives exactly the v1
rates at 0.2 and the v2/v3 rates at 0.5, for all six models printed in both (e.g. 3.7 Sonnet
30.59 / 16.26; R1 15.82 / 5.34). The ratio is 0.34–0.62 across the 16 models with data. Neither v2's
text nor its arXiv comment field marks the change. v4's appendix "Paper Changes From Original
Versions on arXiv" says that v1–v3 "used a different dataset of questions … which led to a higher
percentage of unfaithfulness" and then lists only dataset changes. That is accurate against v2/v3
(same threshold), so the whole v3 → v4 drop is the dataset. It omits that v1's headline numbers
used a different threshold. "Undisclosed" overstates the issue: the new value was printed in v2,
but the change was never flagged.

**Haiku (claim 9).** Items were chosen as pairs flagged for ≥ 3 of the 16 paper models, so they
were not chosen on Haiku's answers. The 24% is a rate on hard items, not a base rate. Both orders were
run for all 117 pairs. The forced-choice prompt differs from the yes/no prompt in three places: the
question wording, "a clear answer" instead of "a clear YES or NO answer", and an added
`ANSWER: <name>` format line. This is inherent to the edit. The auditor's parser required the full
name, so 11 pairs were "unparsed" and counted as consistent. Re-parsed with suffix-tolerant
matching: 108 consistent, 7 inconsistent, 2 refusals ("Undetermined"), 0 unparsed. The difference
is 0.17 [0.10, 0.24], or 0.16 [0.09, 0.24] if refusals are counted as inconsistent. `prereg.md` A10
says "k samples each … modal answers"; the run used k = 1, and the README now states this as a
deviation. The README already says the result covers Haiku only.

**Rank.** Published ranks vs ranks after removing flip-dominated pairs (released sets): Claude 3.7
Sonnet 8 → 15. Every other model moves by at most 2 places: Haiku 2→3, Gemini 1.5 Pro 3→2, DeepSeek
V3 9→8, R1 12→10, ChatGPT-4o 10→9, GPT-4o 13→11, 64k 14→13, Gemini 2.5 Pro 15→14, Gemini 2.5 Flash
6→7, Llama 3.3 7→6, 3.5 Sonnet v2 11→12.

**Prereg timing.** `prereg.md` (823e8ee, 19:05) precedes the pre-registered results (75d1893,
19:16) and the post hoc flip, route and hand-label work (7f00450, 19:26). Every flip and route number
in the README is labelled post hoc. Two deviations were missing: k = 1 in A10, and the A4 bucket
split (W/U/C routes) being replaced in the headline by the post hoc flip split.

## Rerun

I reran `analyse.py`, `posthoc.py`, `posthoc_flip.py`, `posthoc_c2.py`, `posthoc_routes.py` and
`posthoc_sr_partner.py` in a scratch copy that pointed at the same `data/`. All six rewrote their
outputs, and `analyse.json`, `flagged_low_qids.json`, `posthoc.json`, `posthoc_flip.json`,
`posthoc_c2.json`, `posthoc_routes.json` and `posthoc_sr_partner.json` are byte-identical to the
committed files. I did not rerun `l4_haiku.py`, which would have needed the API on a cache miss; I
re-parsed its cache instead. Every headline number was then re-derived with my own code (table
above). Small differences in interval endpoints come from different bootstrap draws and, where
noted, from using the published sets instead of the released ones.

## What I could not check

- The ground-truth check (A9, 47/47), the hedging regex and the stable-rule regex with its partner
  check (47%) were not re-derived.
- Whether "fact error" answers are motivated (the paper's biased-fact inconsistency) or honest.
- The template bootstrap treats templates as independent, but the gt/lt templates of a property may
  share entities. The property bootstrap (29 units) gives similar results.
- My labels are from one labeller (me). Agreement with the auditor (κ 0.78 on five categories) and
  with the autorater (κ 0.82 on flips) bounds this but does not remove it.

## Final evidence level per claim

| # | Claim | Level after validation |
|---|---|---|
| 1 | Rates are not a selection artefact | **R** (confirmed) |
| 2 | Pair-specific inconsistency beyond template lean | **R** (confirmed); the count match is not a finding |
| 3 | Claude 3.7 Sonnet's lead over 3.5 Sonnet v2 and over 1k is answer flips | **L3, post hoc, placebo-supported**. Robust across thresholds for v2; threshold-dependent for 1k. Flip prevalence by model is the paper's own result |
| 4 | About half the bucket is not justification | **Lead** (one labeller, 4 items per model); composition corrected; reading contested |
| 5 | Template-clustered intervals | Statistics, confirmed; wording corrected |
| 6 | Threshold change between versions | **L1, corrected**: made at v2 and printed, never flagged |
| 7 | Oversampling check uses 0.4 | L1, confirmed |
| 8 | Ground truth | not checked |
| 9 | Haiku forced choice | **L4 for Haiku only**, confirmed with corrected parse |
