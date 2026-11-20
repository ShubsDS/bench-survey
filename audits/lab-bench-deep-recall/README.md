# LAB-Bench deep dive (ProtocolQA): most of the score without the protocol sits on items whose key is the standard fix; no sign of verbatim recall in Haiku, and at most a small one in Sonnet

Status: complete, 2026-11-20, branch `audits-round3`. Not yet independently validated.
Parent audit: [`../lab-bench/`](../lab-bench/) (claim 4). Pre-registration: [`prereg.md`](prereg.md)
(committed `c9605da` before any main-run outcome). Every number below is in
[`results.json`](results.json) (`scripts/analyze.py`, seed 0, 2,000 protocol-cluster draws).
Models: Haiku 5.5 (parent's CoT template) and Sonnet 5.5 (answer-only template). **Nothing here is
about Opus or any published model.**

| # | Claim | Level |
|---|---|---|
| 1 | Without the protocol (question + options), Haiku reaches 0.55 [0.48, 0.67] and Sonnet 0.67 [0.58, 0.77] on 107 items (chance 0.23). With the protocol: Haiku 0.68 [0.60, 0.80]; Sonnet 0.89 [0.82, 0.96] on the 62 items it reached before the budget cap. Share of the above-chance score reached without the protocol: Haiku 0.71 [0.57, 0.92]; Sonnet 0.68 [0.49, 0.87] (62 items) | L2 (context removal, model as the rule) |
| 2 | Simple answer-surface cues (length, numerals, step references, hedges, units, unique words, similarity) do not account for it: best held-out rule 0.29 (chance 0.23, permutation p = 0.07); where the longest option is not the key, Haiku options-only still scores 0.54 and Sonnet 0.70 | **R** for simple content-blind cues; a *semantic* surface cue cannot be separated from (c) |
| 3 | Recall of the published wording: Haiku shows none (paraphrase drop 0.05 [−0.04, 0.13] with the question, −0.01 [−0.11, 0.09] options only; free generation of the key's step and value 2/68, distractor rate 0.02). Sonnet loses 0.08 [0.01, 0.14] under paraphrase (9 items lost, 2 gained, n = 91), which bounds verbatim recognition below about a third of its 0.44 above-chance blind margin; Sonnet's free-generation test was not run (budget) | **R** for verbatim recall (Haiku, L4-style edit); Sonnet: small effect, upper bound only |
| 4 | Blind accuracy is concentrated on the 51 of 107 items whose key a blind (key-hidden) read labelled the one standard fix: Haiku 0.78 vs 0.34 on the rest (gap 0.45 [0.24, 0.61]); Sonnet 0.86 vs 0.50 (gap 0.36 [0.14, 0.53]); both above the 99.9th percentile of 1,000 placebo label sets. Haiku's residual on the other 56 items is near chance (0.34 [0.26, 0.48], chance 0.23); Sonnet's is not (0.50 [0.42, 0.63]) | L3-style association (labels by a model, see limits). Prereg verdict: (c) **supported** for Haiku; **cannot tell** for Sonnet's residual |
| 5 | CloningScenarios (33 items, 9 scenarios), Haiku: full 0.70, sequences masked 0.42 [0.25, 0.55], options only 0.33 (chance 0.23) | lead only |

## The benchmark and what rests on it

ProtocolQA: 108 public items on about 24 protocols (protocols.io-style text in which an expert
introduced an error; the question states the symptom; options are candidate fixes). Anthropic's
RSP use treats LAB-Bench ProtocolQA at or above the paper's human line (0.79) as part of an ASL
rule-out; the Opus 4.5 card reports 0.907. Full context in [`../lab-bench/claims.md`](../lab-bench/claims.md).
The parent showed Haiku reaches 0.51 with options only and could not say why. This deep dive asks
how much of a strong model's score needs the protocol, and whether the rest is (a) a cue in the
options, (b) recall of the public items, or (c) knowledge a trained scientist also has.

## What we found

**About two thirds of each model's above-chance score is reachable without the protocol, and it
comes mostly from items where the keyed fix is ordinary good practice.** The evidence favours (c)
over (a) and (b) for Haiku; for Sonnet it rules out large verbatim recall and simple cues, but
leaves part of the blind score unexplained.

| Arm (ProtocolQA, forced choice) | Haiku n | Haiku acc [cluster 95%] | Sonnet n | Sonnet acc [cluster 95%] |
|---|---|---|---|---|
| full item (protocol + question + options) | 107 | 0.68 [0.60, 0.80] | 62 | 0.89 [0.82, 0.96] |
| question + options, no protocol (`qo`) | 107 | 0.55 [0.48, 0.67] | 107 | 0.67 [0.58, 0.77] |
| `qo` on Sonnet's 62 full-arm items | 62 | 0.53 | 62 | 0.68 [0.55, 0.81] |
| options only (`opts`) | 107 | 0.51 [0.43, 0.63] | — | not run |
| `qo`, second option order | 107 | 0.59 [0.52, 0.70] | — | not run |
| `qo`, paraphrased question and options | 91 | 0.53 [0.45, 0.64] | 91 | 0.62 [0.51, 0.76] |
| `opts`, second order / paraphrased | 107 / 91 | 0.51 / 0.54 | — | not run |
| labeller's own blind pick (Opus 5.5, key hidden) | 107 | 0.72 | | |

Chance is 0.23 everywhere. No arm had an unparsed answer, an API error or a refusal (one
false-positive refusal regex hit in Haiku `qo_ro`, answer parsed). Forced choice: the "Insufficient
information" option was not offered; in the parent's standard run Haiku picked it on 18 of 107
ProtocolQA items (accuracy 0.63).

Paired counts: Haiku full vs `qo`: 51 right in both, 22 only with the protocol, 8 only without it,
26 neither (difference 0.13 [0.03, 0.22]). Sonnet on 62 items: 40 / 15 / 2 / 5 (difference 0.21
[0.08, 0.35]). Sonnet beats Haiku without the protocol by 0.12 [0.04, 0.19].

## The confound(s) tested

**(a) Answer surface** (`scripts/cues.py`, `results/cues.json`). Eight content-blind features
per option, each as "pick max" and "pick min"; chosen on a random half of the 23 protocols and
scored on the other half (1,000 halves), plus a conditional logit. Held-out best rule 0.29 (2.5–97.5
percentiles of halves 0.13–0.38), logit 0.26; under key shuffling the same procedure gives 0.235
(p = 0.07 and 0.25). The rule chosen most often is "longest" (in-sample 0.33, the known issue #18
rule). Its margin over chance (0.06) is under half of Haiku's options-only margin (0.28), so by the
pre-registered rule (a) is **against** for simple features. The models do not follow length:
Haiku options-only picks the longest option on 26% of items and scores 0.54 [0.41, 0.69] on the 69
items where the longest option is not the key; Sonnet `qo` 0.70 [0.61, 0.78] on those items.

**(b) Recall of the items.** Three pre-registered tests.
- *R1, paraphrase.* Haiku rewrote every question and option (numbers, step numbers and names
  kept; acceptance rule v2, see Deviations; 91 items after a hand check of 20). Drops in accuracy,
  paired on the same items and order: Haiku `qo_ro`→`qo_pa` 0.05 [−0.04, 0.13] (12 lost, 7
  gained); Haiku `opts_ro`→`opts_pa` −0.01 [−0.11, 0.09]; Sonnet `qo`→`qo_pa` 0.08 [0.01, 0.14] (9
  lost, 2 gained). Every upper bound is below the pre-registered 0.15, so verbatim recall is
  **against** in all three arms by the rule. Sonnet's interval excludes 0, so a small drop is
  present; its control is the original order (no Sonnet reorder arm), and Haiku's reorder alone
  moved accuracy by −0.04 [−0.10, 0.01] (`qo`) and +0.03 [−0.06, 0.15] (`opts`). Paraphrase also
  moved the content-blind rules by up to 0.08 (longest: 0.34 → 0.30), so part of a small drop may
  be cue loss rather than recall. Power: 72% at a drop of 0.15 (`results/power.json`).
- *R2, free generation (Haiku only).* Question alone, no protocol, no options; strict grading on the
  `FIX:` line (96 items whose key names a step). Key step named 7/93 (distractor rate 0.11), key
  values 14/70 (distractor 0.14), step and value both 2/68 (distractor 0.02; difference 0.01
  [−0.03, 0.05]). Haiku cannot reproduce the keyed fix from the question: **against free recall**.
  Not run for Sonnet: the budget ran out first.
- *R3, detail-dependent items.* On the 41 items the blind read labelled D (two or more
  standard-sounding fixes), a model using only general knowledge should be near the plausible-set
  ceiling mean(1/m) = 0.48. Haiku `qo` 0.41 (−0.06 [−0.15, 0.10]): **against**. Sonnet `qo` 0.59
  (+0.11 [0.00, 0.27]): **cannot tell** (recall, recall of the source protocol, or deeper
  knowledge than the labeller would all show this).

**(c) Knowledge** (`labels/`). I labelled all 107 items in two stages: key hidden (pick, number of
standard-practice options m, class G/D/N), committed (`02d3692`), then key revealed
(`f339d4b`), all before any per-item model outcome was looked at. 51 items are "standard-key"
(class G and my blind pick is the key). Examples by id: `a6231697` (the deubiquitinase inhibitor
for preserving ubiquitylation), `dd06a1ee` (a textbook coating-buffer pH), `0ab2f959` (titrate
with a more dilute base); D examples: `fca46ec7` (three standard-looking TRIzol volumes and times;
my pick was wrong) and `275341e6` (dose and duration both plausible; my pick was right but the
item still needs the protocol to decide).

| Arm | standard-key (n = 51) | other (n = 56) | gap [cluster 95%] | placebo percentile |
|---|---|---|---|---|
| Haiku `qo` | 0.78 | 0.34 [0.26, 0.48] | 0.45 [0.24, 0.61] | 100 |
| Haiku `opts` | 0.67 | 0.38 | 0.29 [0.11, 0.46] | 99.8 |
| Sonnet `qo` | 0.86 | 0.50 [0.42, 0.63] | 0.36 [0.14, 0.53] | 99.9 |
| Haiku full | 0.84 | 0.54 | 0.31 [0.04, 0.51] | 100 |
| Sonnet full (62 items: 28 / 34) | 0.96 | 0.82 | 0.14 | 59 |

Placebo: 1,000 random "standard" sets of 51 items, stratified by number of options, built without
the key. Without the 6 items whose key I had seen while checking the data format, the `qo` gaps are
0.49 (Haiku) and 0.38 (Sonnet).

Exploratory (not pre-registered): reading the protocol adds little on standard-key items for
Haiku (+0.06 [−0.07, 0.17]) and much more on the others (+0.20 [0.09, 0.30]). For Sonnet (62
items) the gain is +0.18 [0.04, 0.32] on standard-key and +0.24 [0.04, 0.44] on the others.

## The effect

- **Published number.** Opus 4.5 ProtocolQA 0.907 against the human 0.79 (parent claim 7). Not
  re-run or tested here.
- **Reproduced number.** Haiku full 0.68 (parent's 0.68, the same cached responses).
- **What the items measure.** For both models about two thirds of the above-chance accuracy is
  reachable without the protocol (Haiku 0.71 [0.57, 0.92]; Sonnet 0.68 [0.49, 0.87], 62 items).
  For Haiku that blind part sits on items whose keyed fix is the standard practice, i.e. route (c):
  these items test general troubleshooting knowledge, not reading the protocol. The bias direction:
  as a measure of *protocol reading*, ProtocolQA accuracy overstates it for both models; as a
  measure of *troubleshooting knowledge*, it does not obviously overstate it.
- **The protocol-dependent part.** On the 56 non-standard-key items, Haiku goes from 0.34 to 0.54
  with the protocol; Sonnet from 0.59 to 0.82 on the 34 such items it ran. These are the items
  where the benchmark measures what it says; no human or published-model number exists for them.

## Robustness

| Check | Result | Claim survives? |
|---|---|---|
| Rules discovered on one half of the protocols, scored on the other | 0.29 held out, p = 0.07 | claim 2 yes |
| Placebo label sets for claim 4 (1,000, stratified, key-blind) | observed gap above the 99.8th percentile in every `qo`/`opts` arm | yes |
| Drop the 6 key-seen labels | gaps 0.49 / 0.38 | yes |
| Reorder-only control for paraphrase (Haiku) | −0.04 and +0.03, intervals include 0 | claim 3 yes |
| Second paraphrase arm (options only, Haiku) | −0.01 [−0.11, 0.09] | yes |
| Cue rules on paraphrased options | change ≤ 0.08 | weakens the reading of Sonnet's 0.08 drop as recall |
| Sonnet full on a non-random 62-item subset (first 62 in file order, 20 of 23 protocols) | Haiku on the same 62: full 0.69, `qo` 0.53 (all 107: 0.68, 0.55) | subset looks typical for Haiku; Sonnet's 107-item full score unknown |
| Count of tests | 13 verdict-bearing tests across two models; no correction | stated |

## Alternative explanations

1. **"The labels are just another model's plausibility judgement, so they correlate with model
   picks by construction."** The labeller is Opus 5.5, and its blind pick agrees with Sonnet's
   blind pick on 73% of items (Haiku 65%). So claim 4 shows that what one Claude model finds the
   standard fix, two others pick without the protocol; it does not show that a human expert would.
   Not tested; a refuter's independent (ideally human) labels are the check.
2. **"Blind accuracy is recall of the source protocol, not of the item."** The protocols are
   public, and a key that restores the original step would be guessable by someone who knows the
   original. R2 argues against this for Haiku (it cannot name the step and value); for Sonnet it
   was not tested.
3. **"Standard-key items are simply easier."** Partly: Haiku with the protocol also does better on
   them (0.84 vs 0.54). But the protocol adds little there for Haiku (+0.06), which is the point:
   the item is answerable from general knowledge either way.

## What was already known

Parent audit claim 4 (options-only 0.51) and issue #18 (longest-option rule). New here: the
question-only and full Sonnet ladder, the cue test with held-out selection on this subset, three
recall tests, the blind standard-practice labels and the stratified blind accuracy, and the
masked-sequence CloningScenarios arm.

## What this does not show

- Anything about Opus 4.5 (0.907) or other published models: their blind share was not measured.
- That ProtocolQA is worthless: 56 items still need the protocol for Haiku, and both models gain
  from it.
- That Sonnet does not recall items: paraphrase bounds verbatim recognition (drop ≤ 0.14), but
  semantic recall survives paraphrase, free generation was not run for Sonnet, and Sonnet's 0.50
  on non-standard-key items without the protocol is unexplained.
- Human-expert agreement with the "standard practice" labels.
- CloningScenarios beyond a lead (33 items, 9 scenarios; Sonnet not run).
- The CoT setting for Sonnet: all Sonnet arms are answer-only.

## Deviations from the pre-registration

1. Paraphrase acceptance rule v1 (Jaccard < 0.6 on every text) accepted 47/107 items; changed to
   v2 (< 0.8 per text, < 0.6 item mean; 92 items) after seeing only acceptance counts, before any
   paraphrase-arm call. One more item (`ad177c40`) dropped at the hand check.
2. Spending order: Sonnet `qo` and `qo_pa` ran before Sonnet `full` (prereg had `full` first).
   Sonnet full calls cost 0.0166 USD each, not the 0.009 of the pilot, and the cap stopped the arm
   after 62 of 107 items (45 not run, treated as missing). Sonnet `qgen` and Sonnet Cloning were
   not run.
3. Total spend 3.08 USD, 0.08 over the 3 USD cap: the helper checks the cap before each call and
   four calls were in flight when it was crossed.
4. The free-generation grader's step parser finds 96 step-keyed items (prereg: 92, from a simpler
   regex).
5. The by-class full-minus-`qo` table is exploratory.
6. Prereg A3's "(c) supported" needs the residual within 0.15 of chance: met for Haiku (0.11), not
   for Sonnet (0.27), hence "cannot tell" for Sonnet.

## Pins and how to reproduce

- Items: HF `futurehouse/lab-bench` @ `5c77cec648430f30611808808861eb86f81d5eaa`, via the parent's
  sha256-checked loader (`../lab-bench/scripts/common.py`); parent's harness prompts reused from
  `../lab-bench/scripts/haiku.py`. Excluded: `bee8b322` (API bio-classifier refusal in the parent;
  the content-note skip count is 1; no other item looked hazardous in the hand read).
- No item text is committed: ids, hashes, labels, per-item buckets and aggregates only.
- Inference: 1,085 billed calls, 3.08 USD (Haiku 814 calls, 0.48 USD including 17 pilot and about
  150 paraphrase calls; Sonnet 271 calls, 2.60 USD), [`inference/ledger.jsonl`](inference/ledger.jsonl).
  The parent's 280 Haiku `full`/`opts` responses were copied into the cache (identical prompts) and
  cost nothing.

```bash
PY=audits/lab-bench/data/.venv/bin/python   # parent's venv; run from the repo root, data from the parent
$PY -I audits/lab-bench-deep-recall/scripts/power.py
$PY -I audits/lab-bench-deep-recall/scripts/label_sheet.py && $PY -I audits/lab-bench-deep-recall/scripts/reveal.py
$PY -I audits/lab-bench-deep-recall/scripts/paraphrase.py
bash audits/lab-bench-deep-recall/scripts/batch.sh haiku cot full:ProtocolQA opts:ProtocolQA full:CloningScenarios opts:CloningScenarios qo:ProtocolQA qo_ro:ProtocolQA qo_pa:ProtocolQA opts_ro:ProtocolQA opts_pa:ProtocolQA qgen:ProtocolQA qo:CloningScenarios
bash audits/lab-bench-deep-recall/scripts/batch.sh sonnet direct qo:ProtocolQA qo_pa:ProtocolQA full:ProtocolQA
$PY -I audits/lab-bench-deep-recall/scripts/grade_qgen.py haiku
$PY -I audits/lab-bench-deep-recall/scripts/cues.py
$PY -I audits/lab-bench-deep-recall/scripts/analyze.py   # -> results.json
```
Responses are cached (git-ignored), so a rerun with the cache costs nothing; without it, sampling
will differ.
