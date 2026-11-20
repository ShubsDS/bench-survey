# Validation: lab-bench-deep-recall

Validator: an independent agent (Opus 5.5) that did not write the audit, 2026-11-20, branch
`audits-round3`. **No model calls** (the folder's cap was already spent: 3.0796 USD, 1,085 calls,
confirmed from `inference/ledger.jsonl`). Every number below is re-derived from
`inference/cache/` by my own parser (`v2_rescore.py`) and scripts `v3`–`v7`, seed 0, 2,000
protocol-cluster draws, 1,000 placebo draws. Numbers are in [`validation.json`](validation.json).

Order of work, checkable in `git log`: rubric and key-hidden sheet script (`c87183f`), then my
blind labels for all 107 items (`cd39362`), both committed before I opened any model output, the
answer key or the auditor's per-item labels. Only then the rescoring and attacks (`c0cc363`).

## Verdicts

| # | Auditor's statement | Verdict | Validator's number | How checked |
|---|---|---|---|---|
| 1a | No-protocol accuracy: Haiku 0.55 [0.48, 0.67], Sonnet 0.67 [0.58, 0.77] (n = 107); full: Haiku 0.68 [0.60, 0.80], Sonnet 0.89 [0.82, 0.96] (n = 62) | **confirmed** | identical (Haiku `qo` 0.551 [0.483, 0.667]; Sonnet full 0.887 [0.821, 0.962]) | own parser on the cache; auditor's `analyze.py` rerun gives a byte-identical `results.json` |
| 1b | Share of above-chance score reached without the protocol: Haiku 0.71 [0.57, 0.92]; Sonnet 0.68 [0.49, 0.87] on 62 | **confirmed, wording corrected** | Haiku 0.709 [0.570, 0.912]; Sonnet 0.681 [0.483, 0.865] (joint protocol resampling of numerator and denominator). With options only, Haiku already reaches 0.63 [0.42, 0.87] of it; what the question adds beyond the options is 0.22 [−1.10, 0.79] of the remaining gain, i.e. not identified | v3 `share` |
| 1c | Sonnet's 62 items "look typical" | **corrected** | the 62 are exactly the first 62 in file order; 3 of 23 protocols appear only in the other 45; the 45 have longer protocols (median 5,325 vs 4,158 characters). Haiku's share is 0.65 [0.49, 0.82] on the 62 and 0.79 [0.49, 1.35] on the 45, so if Sonnet follows Haiku, its 62-item share understates its 107-item share (direction uncertain, intervals overlap) | v3 `sonnet_62` |
| 1d | Forced choice, no unparsed answers | **confirmed** | no arm offers "Insufficient information"; `full` and `qo` use the same option order; 0 unparsed, 0 multiple tags; abstention cannot differ between arms. Uniform chance 0.233 vs chance under each arm's own letter preference 0.231–0.238 | v2, v3 `letter_prior_chance` |
| 2 | Simple content-blind cues do not account for it (best held-out rule 0.29, p = 0.07) | **confirmed (R)** | six further rules of my own (12 directions: overlap with the question, prototype option, closest near-duplicate pair, majority step number, median numeric value, fewest numerals), selected on half the protocols: held-out 0.26 [0.14, 0.32], p = 0.11 (300 key shuffles); best in sample "the option citing the step most options cite" 0.29. Haiku options-only (0.51) remains the upper bound on what the options carry | v3 `new_rules` |
| 3a | Haiku shows no verbatim recall: paraphrase drop 0.05 [−0.04, 0.13], options-only −0.01 [−0.11, 0.09] | **confirmed** | 0.055 [−0.032, 0.136] (12 lost, 7 gained); −0.011 [−0.106, 0.089] | v3 `paraphrase` |
| 3b | Sonnet loses 0.08 [0.01, 0.14] under paraphrase | **downgraded** | reproduces (0.077 [0.012, 0.136], 9 lost, 2 gained), but 4 of the 9 losses are among the 6 of 51 hand-read paraphrases whose meaning changed; without those 6: 0.035 [−0.018, 0.085] (n = 85). Haiku without them: 0.082 [0.000, 0.154]. A drop of 0.15 or more is excluded in every version; the sign and size of a smaller drop is not established for either model | v5 sheet, v6 |
| 3c | Paraphrase rule relaxed before any paraphrase-arm call | **confirmed (timing)** | last paraphrase-generation call 50 s before the rule-v2 commit `6d2efa5`; first paraphrase-arm call 336 s after it. The v1 code was never committed, so "only counts were seen" rests on timing. The relaxed rule did not create the drop: Sonnet net loss 3 on the 40 v1-passing items, 4 on the 51 v1-failing items | v4 `timing`, v5 |
| 3d | Free generation: Haiku names the key's step and value on 2 of 68 (distractor rate 0.02) | **confirmed in substance** | my stricter grader: 1 of 66 (distractor rate 0.023); step alone 6/86 (distractor 0.10); value alone 14/78 (distractor 0.13). Chance (the distractor rate) is about 0.02 for the exact grade | v4 `qgen` |
| 3e | R3: on D items Haiku `qo` 0.41 against ceiling 0.48; Sonnet 0.59 (+0.11 [0.00, 0.27]) | **confirmed** | 0.415 / 0.585 against 0.476; Sonnet excess CI [0.000, 0.257] | v7 `R3` |
| 4a | Blind accuracy concentrates on the 51 "standard-key" items: Haiku 0.78 vs 0.34, gap 0.45 [0.24, 0.61]; Sonnet 0.86 vs 0.50, gap 0.36 [0.14, 0.53]; above every placebo | **downgraded** | numbers reproduce, but the label is "class G **and** the labeller's blind pick is the key": it uses the key and conditions on a Claude model answering blind correctly. That condition alone gives larger gaps (Haiku 0.49, Sonnet 0.57). The key-blind placebo does not control for it. Key-blind labels: auditor's class G alone, Haiku 0.68 vs 0.40, gap 0.28 [0.07, 0.42] (99.6th placebo pct); Sonnet 0.75 vs 0.58, gap 0.16 [−0.02, 0.32] (96.5th). My key-blind labels (37 items): Haiku 0.76 vs 0.44, gap 0.31 [0.16, 0.45] (99.8th); Sonnet 0.89 vs 0.56, gap 0.34 [0.26, 0.41] (100th) | v1 labels, v3 `labels`, v6 |
| 4b | Haiku's residual on the other items is near chance (0.34), so prereg A3 verdict "(c) supported" for Haiku | **failed as stated** | with key-blind labels the residual is 0.40 (auditor G) or 0.44 (mine) against chance 0.23, outside the prereg's 0.15 margin: by the prereg's own rule the verdict is **cannot tell** for Haiku, as for Sonnet | v3 `labels` |
| 4c | Exploratory: the protocol adds little on standard-key items for Haiku (+0.06) and more on the others (+0.20) | **failed (label-dependent)** | reproduces with the auditor's labels; with mine it reverses: +0.19 [0.06, 0.29] on K items, +0.10 [−0.02, 0.21] on the rest; with the auditor's key-blind G: +0.10 vs +0.17 | v7 |
| 5 | CloningScenarios (33 items, 9 scenarios), Haiku: full 0.70, sequences hidden 0.42 [0.25, 0.55], options only 0.33 | **confirmed, lead** | 0.697 [0.41, 0.87]; 0.424 [0.24, 0.55]; options only 0.35 on the 26 of 33 responses my parser can assign (options are shared across items) | v4 `cloning` |

## The circularity question (route c)

- **The auditor's label uses the answer.** `standard_key` = class G and `pick_is_key`. Items where
  a Claude model's blind pick is right are, unsurprisingly, items other Claude models get right
  blind: `pick_is_key` alone separates Haiku `qo` 0.69 vs 0.20 and Sonnet `qo` 0.83 vs 0.27.
  Within the 77 items the labeller answered correctly, class G still separates Haiku (gap 0.28
  [0.06, 0.49]) but not Sonnet (0.09 [−0.16, 0.30]).
- **Claude models share their wrong answers.** On items both got wrong, the auditor's pick and
  Sonnet's pick coincide on 64% (n = 22) and Haiku's and Sonnet's on 73% (n = 26), against 31% by
  chance. So a label made by a Claude model can encode Claude plausibility, not expert practice.
- **Key-blind labels.** My rubric (`v1_rubric.txt`) records whether general practice singles out
  one option for the stated symptom, without recording which, and excludes items whose options
  differ only by a protocol-dependent number. It agrees with the auditor's key-blind class G on
  74% of items (kappa 0.49); I call 37 items "K", the auditor 59 "G". The gap survives with my
  labels for both models (above). On my K items the labeller's blind pick is right 95% of the time
  against 60% elsewhere, so my labels and the auditor's picks track the same thing.
- **How far circularity is ruled out.** Partly. The key was not used for my labels, and the gap
  holds, so the association is not an artefact of conditioning on the key. But both labellers are
  Claude models, and the labels may still mean "items a Claude model finds obvious". K items are
  also easy *with* the protocol (Haiku full 0.95 vs 0.54), which fits an "easy items" reading as
  well as a "standard practice" reading. Separating these needs human expert labels; nothing here
  replaces them. Route (c) is correlational throughout: no edit was made to the feature.

## Recall of the public source protocol (attack 7)

Only Haiku's no-protocol outputs contain text (Sonnet's arms are answer-only, so nothing in its
outputs bears on this). In Haiku `qo` reasoning (197 responses), numbers absent from the prompt
but present in the hidden protocol occur 0.07 times per response against 0.04 for other protocols;
in free generation (101) 1.77 against 1.15 (excess CI [0.21, 0.90]). The matches are generic values
(37, 30, 20, 0.1). Every match on a rare token (one in at most 2 of 23 protocols) is a topic word
the question implies (crystallization, hematoxylin, poly-d-lysine); no rare number matched. So:
no sign that Haiku quotes the source protocol; a lead, not a test, and untested for Sonnet.

## Paraphrase hand read (51 items)

I read 45 items in file order plus the 6 remaining Sonnet losses, original against paraphrase,
with the key marked. The read was **not blind to outcome** (the sheet showed each item's result).
No paraphrase made a distractor correct. Six changed meaning: `36cae278` (the key "only lightly cap
the lid" became "gently tighten the cap"), `3b5bd87a` and `abfb2fec` (distractors turned from
proposed fixes into statements of what the protocol says), `e8afd1c6` (all options moved to past
tense, "what error did I make"), `520f4620` (the key "do not slow stir" became "avoid stirring
slowly", which can read as "stir fast"), `16fc3385` (the question changed from "which may mediate
this" to "which could be responsible for this", which the key no longer answers). The auditor's
20-item hand check included `e8afd1c6` and kept it.

## What I corrected in the README and results.json

1. Claim 4 and the headline: route (c) is an association that survives key-blind labels, not a
   "supported" verdict for Haiku; the 0.78 / 0.34 split and its "near chance" residual depend on a
   label that uses the key. Key-blind numbers added; "most of the score" replaced by counts.
2. Claim 3: Sonnet's 0.08 drop marked as not robust; Haiku's drop without the changed paraphrases
   added.
3. Claim 1: the 62-item subset described (first 62 in file order, missing 3 protocols, shorter
   protocols, likely direction); options-only share added.
4. Exploratory protocol-gain table marked as label-dependent.
5. Causal wording in "The effect" ("these items test general troubleshooting knowledge") changed
   to correlational wording.

## What could not be checked

- Human-expert agreement with any "standard practice" label.
- Sonnet on the 45 items it did not reach, Sonnet options-only, Sonnet free generation, Sonnet
  reasoning text (no budget; no new calls allowed).
- Whether the auditor saw anything besides acceptance counts before changing the paraphrase rule
  (only the timing can be checked).

## Final evidence levels

| # | Claim | Level |
|---|---|---|
| 1 | Blind share (Haiku 107 items; Sonnet 62 non-random items) | L2 (context removal), confirmed |
| 2 | Simple surface cues do not account for it | R, confirmed |
| 3 | No large verbatim recall (drop ≥ 0.15 excluded, both models); smaller drops unresolved | R for large verbatim recall; Sonnet's small drop not established |
| 4 | Blind accuracy higher on items Claude labellers call standard-fix | L1–L2 association, correlational; prereg verdict "cannot tell" for both models |
| 5 | CloningScenarios | lead |
