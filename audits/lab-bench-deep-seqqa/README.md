# LAB-Bench SeqQA deep dive: moving the option cue costs Sonnet 5.5 about 0.10 on the cue-bearing SeqQA subtasks (exact p = 0.06, 48 pairs), which is about 0.04 of a SeqQA score; by the pre-registered rule the reliance question stays open — and on Haiku the same contrast is four times larger under a reasoning prompt

Status: validated, 2026-11-20, branch `audits-round3`. Parent: [`../lab-bench`](../lab-bench)
(validated). Independent validation: [`validation/VALIDATION.md`](validation/VALIDATION.md)
(the validator reran the pipeline byte-identically, re-derived every number from the response
cache, hand-read 40 arm-blind items, and ran one new 60-call test). Pre-registration:
[`prereg.md`](prereg.md), committed in `05d2d07` before any model output on a cue subtask
(confirmed by the validator against the ledger). Models: `claude-sonnet-5-5` (primary) and
`claude-haiku-5-5`, no tools, default extended thinking, **letter-only answers — which turns out
to matter (claim 4b)**. **All results are about these two models only.** They say nothing about
Opus 4.5 or any other model in a system card.

Validated result first; the auditor's original numbers are kept in each row and in
[`#validation`](#validation).

| # | Claim (validated) | Level |
|---|---|---|
| 1 | **Lead:** Sonnet can read the cue. With the question withheld, it picks the key on 17 of 18 cue items, 0.94 [Wilson 0.74, 0.99] (chance 0.24). 18 items is a lead, not a measurement | L2 (Sonnet as a content-blind solver), lead |
| 2 | Moving the cue changes Sonnet's accuracy, **in direction**. Same question and key; the wrong-site option carries the key's body (K) or a decoy's body (D). K 0.979 → D 0.875 on 48 pairs, **K − D = 0.104**, 5 of 48 pairs discordant and all 5 one way: **exact paired p = 0.063** (one-sided 0.031), item bootstrap [0.021, 0.188], subtasks **[0.017, 0.250]** (validator's two-stage bootstrap; auditor reported [0.033, 0.200]). Dropping GC-percent: 0.071, p = 0.25, [0.000, 0.167]. **Pre-registered verdict: "still cannot tell"** (the "yes" rule also required the new centre to be picked more often than the other distractors under D, 0.042 vs 0.039 — not met) | L4 for Sonnet that option structure moves accuracy, direction only; the pre-registered "follows the cue" test **not met** |
| 3 | **Under this prompt**, Sonnet does not *depend* on the cue for most of its cue-subtask accuracy: under D it still scores 0.875 [0.75, 0.94] (n = 48), and 1.00 on AAseq and PCR-seq-enzprimers (6 + 6 pairs). Claim 4b shows this can be a property of the letter-only prompt | L4 (Sonnet) for this prompt; small n per subtask |
| 4a | Haiku, with this prompt: K − D = 0.056, items [−0.033, 0.144], exact p = 0.36, n = 90. "Still cannot tell". Subtask interval **[−0.044, 0.156]** (validator; the auditor's [0.022, 0.089] came from a cluster bootstrap that did not resample items and is withdrawn). Haiku shown only the options picks the key on 0.79 of cue items against 0.39 of non-cue items, the 99.2nd percentile of 1,000 matched placebo splits; with the question shown, the 51.5th. Haiku *does* pick the new D centre more often than the other distractors (0.111 vs 0.051) | L4 inconclusive (Haiku) for this prompt; N stratum L2 |
| 4b | **Validator's finding: the prompt, not the rebuild, is why Haiku's drop here is small.** The same 30 Gibson K/D pairs, same options and order, rendered with the parent audit's prompt ("Think step by step.", no letter-only line, forced choice): **0.867 → 0.600, drop 0.267 [0.100, 0.434], exact p = 0.021** (9 vs 1 discordant), against 0.767 → 0.700 here. Pre-registered in [`validation/v6_prereg_prompt.md`](validation/v6_prereg_prompt.md) before the run | L4 for Haiku on the two Gibson subtasks (n = 30), reproducing the parent's effect size on these rebuilt items |
| 5 | Effect on a SeqQA score. If the six cue subtasks pointed at a wrong option, Sonnet's 15-subtask mean would fall by **0.042 [0.011, 0.073]**; Haiku's by 0.022 [−0.018, 0.062]. Haiku's score levels: as benchmarked 0.83 [0.78, 0.89], cue against 0.80 [0.74, 0.85], GC honest-distractor variant 0.80 [0.75, 0.86]; Sonnet's cue-for / cue-against 0.89 / 0.85. **The score levels are a lead** (Sonnet's non-cue half is 18 items) and **are not comparable to the paper's human 0.79**: that number scores unsure answers as wrong, the plausible forced-choice human range is 0.81–0.85 (up to 0.87), and Sonnet's 0.851 is inside it with an interval [0.79, 0.90] covering all of it | arithmetic on L4 contrasts; shift measured, levels a lead |
| 6 | Two key definitions in the benchmark. (a) **An error:** in both restriction-cloning subtasks the keyed reverse primer is the gene's 3′ end in sense orientation, not reverse-complemented (PCR-seq-enzprimers 40/40 sense and 0/40 reverse-complemented by computation; PCR-gene-enzprimers keys end in a sense stop codon 40/40, 0/40 start with a reverse-complemented stop) — while **both Gibson subtasks do reverse-complement, 40/40 each**, so the two restriction subtasks (80 items) contradict App. C.7.1 and their own sister families. (b) **An undisclosed convention, not a mismatch:** AAseq keys are the longest *forward-strand* ORF (40/40) and the reverse strand has a longer ORF in 21/40 items, but App. C.7.12 names no strand, so the paper neither states nor contradicts it. Neither changes which option is correct in any item | L1 |

**Answer to the open question: still cannot tell, by the pre-registered rule.** What can be said:
- Sonnet can read the cue (a lead, 18 items).
- Its accuracy falls by about 0.10 when the cue is moved: the direction survives dropping any one
  subtask, but an exact paired test gives p = 0.063 and the effect rests on 5 discordant pairs.
- It does not follow the decoy centre.
- Most of its cue-subtask accuracy survives a misleading cue **under the letter-only prompt used
  here**. On Haiku the same contrast quadruples under a step-by-step prompt (claim 4b), and the
  Sonnet version of that test was not affordable, so this is the main open question now.

So on this evidence at most a small part of Sonnet's SeqQA score (about 0.04 of the 15-subtask
mean; upper bound 0.07) rests on option structure **as elicited here**.

## The benchmark and what rests on it

See [`claims.md`](claims.md) and the parent. Anthropic system cards set SeqQA against a human line
in RSP decisions; for example, the Opus 4.5 card gives SeqQA 0.8517 and says "every evaluation
except FigQA exceeded the human baseline". The paper's human SeqQA mean over the 15 subtasks is
0.79. Six subtasks (240 of 600 public items) are solvable from the options alone (parent claim 1,
L2).

## What we found

### Numbers (`results.json`; item bootstrap 2,000, seed 0; Wilson for single rates)

| Model | Arm | Items | n | Accuracy | Refusals / unparsed |
|---|---|---|---|---|---|
| Sonnet | K (key-centred) | 6 cue subtasks | 48 | 0.979 [0.89, 1.00] | 0 / 0 |
| Sonnet | D (decoy-centred) | same items | 48 | 0.875 [0.75, 0.94] | 0 / 0 |
| Sonnet | I (honest distractors) | GC-percent | 6 | 0.83 [0.44, 0.97] | 0 / 0 |
| Sonnet | N (options only) | cue subtasks | 18 | 0.94 [0.74, 0.99] | — / 0 |
| Sonnet | O | 9 non-cue subtasks, 2 each | 18 | 0.83 [0.61, 0.94] | 0 / 0 |
| Haiku | K | cue subtasks | 90 | 0.833 [0.74, 0.90] | 0 / 0 |
| Haiku | D | same items | 90 | 0.778 [0.68, 0.85] | 0 / 0 |
| Haiku | O | cue subtasks (8 each; GC = K) | 55 | 0.855 [0.74, 0.92] | 0 / 0 |
| Haiku | I | GC-percent | 15 | 0.73 [0.48, 0.89] | 0 / 0 |
| Haiku | N | cue / non-cue | 48 / 54 | 0.79 [0.66, 0.88] / 0.39 [0.27, 0.52] | — / 0 |
| Haiku | O | non-cue, 6 each | 54 | 0.81 [0.69, 0.90] | 3 refusals / 0 |

Paired contrasts:

Subtask-level intervals are the validator's two-stage bootstrap (resample the six subtasks, then
items within each). The auditor's `analyze.py:54` resampled subtask means only; those values are
kept in the last column and should not be used — for Haiku they excluded 0 while the item
interval did not, which a six-cluster interval cannot honestly do. Exact paired p is the McNemar
binomial, two-sided.

| Model | Contrast | n | Diff | 95% CI items | 95% CI subtasks (validated) | exact p | Pre-registered decision | auditor's subtask CI |
|---|---|---|---|---|---|---|---|---|
| Sonnet | K − D, all cue | 48 | **0.104** | [0.021, 0.188] | [0.017, 0.250] | 0.063 | still cannot tell (centre pick 0.042 vs other 0.039) | [0.033, 0.200] |
| Sonnet | K − D, gene absent | 30 | 0.100 | [0.000, 0.233] | — | 0.25 | still cannot tell | 0.10 on each of 3 |
| Sonnet | K − D, gene present | 18 | 0.111 | [0.000, 0.278] | — | 0.50 | still cannot tell | [0.0, 0.33] |
| Haiku | K − D, all cue | 90 | 0.056 | [−0.033, 0.144] | [−0.044, 0.156] | 0.36 | still cannot tell | [0.022, 0.089] (withdrawn) |
| Haiku | K − D, gene absent | 45 | 0.067 | [−0.089, 0.222] | — | 0.39–0.45 | still cannot tell | |
| Haiku | K − D, gene present | 45 | 0.044 | [−0.067, 0.156] | — | 0.36–0.58 | still cannot tell | |
| Haiku | O − K (rebuild check, 5 subtasks) | 40 | 0.050 | [−0.05, 0.15] | — | — | — | |
| Haiku | O − D | 55 | 0.055 | [−0.055, 0.182] | — | — | — | |
| Haiku | **Kp − Dp, Gibson, parent's prompt** (validator) | 30 | **0.267** | [0.100, 0.434] | — | **0.021** | n/a (validator's prereg) | |

Per subtask, Sonnet (K → D; exact McNemar; Holm over 6 gives p = 1.0 for every subtask):

| Subtask | n | K | D | K-only / D-only | Picks under D |
|---|---|---|---|---|---|
| Prop-seq-gcpercent | 6 | 1.00 | 0.67 | 2 / 0 | both errors picked the new centre |
| ORF-seq-AAseq | 6 | 1.00 | 1.00 | 0 / 0 | — |
| PCR-seq-enzprimers | 6 | 1.00 | 1.00 | 0 / 0 | — |
| PCR-gene-enzprimers | 10 | 0.90 | 0.80 | 1 / 0 | errors: G (other gene) 2, centre S 0 |
| PCR-gene-gibshindprimers | 10 | 1.00 | 0.90 | 1 / 0 | G 1, S 0 |
| PCR-gene-gibssmaprimers | 10 | 1.00 | 0.90 | 1 / 0 | G 1, S 0 |

Haiku per subtask: GC 0.80 → 0.67; AAseq 1.00 → 1.00; seq-enz 1.00 → 1.00; gene-enz 0.67 → 0.60;
gibshind 0.73 → 0.67; gibssma 0.80 → 0.73 (15 pairs each; no subtask significant).

### How Sonnet fails under D (post hoc, descriptive)

In the PCR subtasks the D arm makes the frame-shifted option S the centre, because the replaced
option now carries S's body. Sonnet never picked S or the replaced option (0 of 36 PCR D answers).
Its 4 PCR errors under D all picked G, the option with the right sites and *another gene's* body.
In K and O the key's body is repeated in the wrong-site option. In D it is not, so without the gene
sequence only K and G remain, and Sonnet chose G four times.

So Sonnet seems to:
- reject frame-broken and wrong-site options by checking them;
- use a repeated body as corroboration when the gene is absent.

Corroboration is a cue too, but not the centroid one the pre-registered rule tests. This reading
is post hoc, rests on 4 errors, and the thinking text is not returned. On GC-percent both D errors
picked the new centre (x ± 1, true GC 48.4% and 49.7%). Haiku's errors on gene-enz go to G under
K and D alike (5 and 6 of 15), so G is a general confusion for Haiku there.

## The confound and the arms

- Construction and verification: `scripts/build.py`, checks per item in `build_check.json`.
- **D and K differ in one option on the four PCR subtasks.** The wrong-site option is replaced
  by the same new wrong site W′ in both arms. In D it carries the shifted body S; in K it carries
  the key's body. W′ is a different MCS enzyme pair, or the pUC19 junction at XbaI/BamHI. The MCS
  region was rebuilt from the keys' own HincII and SmaI overlaps, which it reproduces exactly.
- **AAseq.** D replaces two substitution variants of P with variants of V; K replaces them with
  new variants of P.
- **GC-percent.** D = {x, x+s, x+2s, (x+s)/2}. K equals O, because the benchmark's generator
  around the key gives O. I uses AT%, purine %, keto % and partial-sequence GC%; it is built for 31
  of 40 items.
- **Key verification by computation.** GC 40/40; AAseq 38/40 (2 ties dropped); named sites and
  junctions 160/160; PCR-seq-enz gene ends 40/40. Rebuilt distractors are wrong by site, junction,
  translation or value.
- **Independently re-verified** (validator, `validation/v3_verify.py`, own code): the key is the
  unique correct option in every K and D item — GC 40/40 and the paper's {x−1, x+1, x/2} pattern
  40/40; AAseq keys are the longest forward-strand ORF 40/40 and no other option is a valid
  translation on either strand; in every K and D PCR item exactly three options carry the named
  sites or junction and the rebuilt one is wrong by site in both arms; no duplicated options.
  A blind hand-read of 40 arm-blind K/D items (`validation/v5_blind*`) picked the parquet key 40
  of 40 times and identified the arm 40 of 40 times.
- **K and D are not identical apart from centrality.** In the D arm the key becomes the *unique
  longest* option (PCR-gene-enzprimers 24/33, PCR-seq-enzprimers 26/37, gibshind 15/36, gibssma
  21/29); in the K arm it never does (0 of 135), because in K the replaced option repeats the
  key's longer body. A length heuristic would therefore help D, so this runs against the measured
  drop, and accuracy does not track it (Sonnet D 0.889 when the key is not the unique longest vs
  0.857 when it is; Haiku 0.780 vs 0.775). Found by the validator; not stated by the auditor.
- **Centre check.** Both the 3-gram centroid and a Levenshtein medoid (num_center for GC) must
  pick a distractor in D and the key in K. Kept pairs: 40 / 38 / 33 / 37 / 36 / 29. 25 PCR items
  failed the centre check and are not in any pair.
- **Rendering.** Prompt as in `scripts/run.py`. Option order is a hash of the item id, so the key
  has the same letter in every arm. The refusal option is included in O, D, K and I.
- **Reading the outputs.** All 533 outputs are a single `[ANSWER]X[/ANSWER]` tag (parse route
  "tag" 533/533). I read 102 Sonnet outputs and the error rows by hand. With letter-only answers
  there is no visible reasoning to check.

## The effect on SeqQA scores

Cue-free SeqQA score = the mean of the 15 subtasks (each has 40 public items, so this is also the
benchmark's item weighting), with the cue subtasks scored under D (cue against), K or O (cue for),
or I on GC. Intervals come from a bootstrap of items within subtask; they do not cover subtask
choice.

| Model | As benchmarked (O) | Cue for (K) | Cue against (D) | GC honest (I), others D | Shift (6/15)·(K − D) |
|---|---|---|---|---|---|
| Haiku | 0.834 [0.778, 0.891] | 0.822 [0.769, 0.873] | 0.800 [0.744, 0.853] | 0.804 [0.749, 0.858] | 0.022 [−0.018, 0.062] |
| Sonnet | not run (no O on 5 cue subtasks) | 0.893 [0.853, 0.933] | 0.851 [0.793, 0.909] | 0.862 [0.809, 0.916] | **0.042 [0.011, 0.073]** |

- Sonnet's non-cue part is 18 items (2 per subtask, accuracy 0.83). Its score levels are rough
  and their intervals understate the error. The shift needs no non-cue data and is the better
  number.
- The honest score lies between the cue-against and cue-for columns only if accuracy is monotone
  in the cue's direction, which is an assumption. The GC I arm (n = 6 and 15) is the only honest
  arm.
- **Against the human line (parent claim 7).** The paper's human SeqQA mean is 0.79. It counts
  unsure answers as wrong; the plausible forced-choice value is 0.81–0.85. Humans were scored on a
  different item sample (full set, 64% coverage). The system cards' own human line and weighting
  are unpublished.
  - Haiku's estimates under every variant are 0.80–0.83, at or slightly above 0.79 and inside or
    near the forced-choice range. Its intervals reach below 0.79 under D and I.
  - Sonnet's estimates under D (0.851) and I (0.862) are above the paper's 0.79 but **inside** the
    plausible forced-choice human range (0.808 if unsure humans guessed at chance, 0.854 at their
    own precision, 0.866 if every unsure guess was right; parent `validation/v5_human.json`), and
    the interval on the D score, [0.793, 0.904], covers that whole range. **Corrected by the
    validator:** the auditor wrote that these "stay above 0.79 and at the top of the forced-choice
    range", which holds only against the unsure-scored-wrong number. On 18 non-cue items this is a
    lead, and it is not a like-for-like comparison (different item sample, different scoring rule,
    the cards' own human line unpublished). **Quote the shift, not the levels.**
- **Bias direction.** On these two models the cue makes SeqQA look more capable by about 0.02–0.04
  of the 15-subtask mean (Sonnet's upper bound 0.07). Nothing here gives the size for any other
  model.

## Robustness

| Check | Result | Claim survives? |
|---|---|---|
| Drop each subtask (Sonnet K − D) | 0.071–0.119 | direction yes, all > 0; **but the interval does not**: dropping GC-percent gives 0.071, 3 of 42 discordant, exact p = 0.25, items [0.000, 0.167] (validator) |
| Drop each subtask (Haiku) | 0.040–0.067 | inconclusive throughout |
| Exact paired test, pooled (validator) | Sonnet 5 vs 0 discordant, p = 0.063 two-sided (0.031 one-sided); Haiku 12 vs 7, p = 0.36 | the Sonnet contrast does not reach p < 0.05; the item bootstrap's lower bound 0.021 is 1/48, the smallest non-zero value it can return here |
| Subtask-level resampling | Sonnet [0.017, 0.250], Haiku [−0.044, 0.156] (validator, resampling items within subtasks); sign-flip over 6 subtasks p = 0.12 and cannot reach 0.05 with zeros on two subtasks | item-level only; power at subtask level was stated in advance as < 80% (`power.json`). The auditor's [0.033, 0.200] / [0.022, 0.089] came from resampling subtask means alone and are withdrawn |
| Prompt (validator, pre-registered) | Haiku on the same 30 Gibson pairs under the parent's step-by-step forced prompt: 0.867 → 0.600, drop 0.267 [0.100, 0.434], p = 0.021 | **no:** the size of the K/D effect depends on the elicitation. The Haiku null here is prompt-specific; the Sonnet equivalent was unaffordable |
| Holm over 6 per-subtask tests | no subtask significant for either model | per-subtask claims not made |
| Both centre rules agree on the D centre | all 42 Sonnet / 75 Haiku non-GC pairs (GC uses one rule) | n/a |
| Abstention | 0 refusals and 0 unparsed in K, D, I for both models; Haiku 3 refusals in non-cue O | the K/D contrast is clean |
| Rebuild itself (Haiku O − K) | 0.05 [−0.05, 0.15] | no evidence that K differs from O; not measured for Sonnet (no O) |
| Tests counted | 3 pre-registered K − D contrasts per model (all, gene absent, gene present), 6 per-subtask tests per model, O − K, O − D, I − D, K − I, 2 stratum placebos, N rates | the primary test is one per model |

## Alternative explanations

1. **"The D arm is just harder."** On the PCR subtasks D and K differ in one option, and the
   replaced option is wrong by its site in both arms. In D, though, a solver who rejects S and W′
   is left with K vs G without a repeat of the key's body. That *is* the cue being removed. It is
   not a separate difficulty, but it is a different cue from "pick the centre". On AAseq, D's new
   options are further from the key than K's (2 residues vs 1), and Sonnet and Haiku lose nothing
   there.
2. **"The drop reflects the GC rounding cases, not cue use."** The 2 GC errors are items with GC%
   48.4 and 49.7. A model estimating GC% to within about 1 point would be pulled toward an adjacent
   value. The centre there is adjacent, so "estimation error" and "follows the centre" cannot be
   separated on 6 items.
3. **"Haiku contradicts the parent's Haiku result."** The parent found 0.96 → 0.50 on Gibson,
   and its validator's one-option swap found 0.935 → 0.726. Here Haiku drops 0.07 on Gibson
   (15 + 15 pairs). The conditions differ:
   - this prompt asks for the letter only and offers the refusal option;
   - here W′ is a new junction in both arms, while the parent's swap kept W's junction;
   - Haiku's K-arm Gibson accuracy is 0.73–0.80, against 0.88–0.96 in the parent's runs.
   This run does not refute the parent's result; the two use different prompts and different
   controls. **Settled by the validator, and the auditor's guess as to which difference mattered
   was wrong in its emphasis:** running the *same 30 rebuilt K/D pairs* under the parent's prompt
   gives 0.867 → 0.600 (drop 0.267 [0.100, 0.434], exact p = 0.021). The rebuild is not what
   shrank the effect — the letter-only prompt is. So the audit's Haiku null, and claim 3's "most
   of Sonnet's accuracy survives", hold for this elicitation and not necessarily for a
   step-by-step one.
4. **"Sonnet recalls the E. coli genes."** It is possible on the gene-absent subtasks, where K
   scores 0.97. This test cannot separate recall from corroboration.

## What was already known

See [`prior_work.md`](prior_work.md). The cue, the options-only rules and Haiku's Gibson result
come from the parent. New here:
- the paired, pre-registered D/K design with verified keys;
- the Sonnet measurements;
- the GC independent-distractor arm;
- the two key-definition findings (claim 6), which are not in the parent's write-up or validation;
  one validator web search for a prior report of the reverse-primer orientation found none. Note
  the corrected framing: 6a contradicts App. C.7.1 and the Gibson subtasks (an error), 6b is an
  undisclosed convention that the paper neither states nor contradicts;
- the validator's prompt test (claim 4b), which shows the K/D effect size depends on elicitation.

## What this does not show

- Anything about Opus 4.5, the system-card runs or any published model. No per-item outputs exist,
  and a Sonnet 5.5 result is about Sonnet 5.5.
- What Sonnet does with visible chain-of-thought or 10-shot prompting, as in the cards. Here it
  thought by default (mean 814 thinking tokens per call), but the thinking was not readable.
- That Sonnet does not rely on the cue at all. The "no" rule needed an upper bound < 0.10, and the
  observed upper bound is 0.19.
- Per-subtask effects. The per-subtask n is 6–10 for Sonnet.
- Behaviour on the 25 PCR items that failed the centre check, the 9 GC items without an I arm, or
  the 2 AAseq ties.
- Whether the sense-orientation reverse primers (claim 6a) change any model's score. Every option
  follows the same convention, and the keyed option stayed the only defensible one in all 40
  blind-read items.
- Whether Sonnet's 0.104 would be larger under a step-by-step prompt, as Haiku's 0.067 becomes
  0.267. That run needs about 1.5 USD and the folder had 0.16 USD left. **This is the largest
  open question left by the validation.**
- That the 0.104 is significant at the conventional level: the exact paired test gives p = 0.063.

## Pins and how to reproduce

- Items: parent pins (HF `futurehouse/lab-bench` @ `5c77cec6…`, parquet sha256s checked by
  `../lab-bench/scripts/common.py`). Paper v3, App. C.7.1 and C.7.12, read from the parent's
  `data/paper/v3.txt` (sha256 in the parent README).
- Inference: `audits/tools/claude_call.py`, 533 billed calls by the auditor. Sonnet 141 calls,
  2.24 USD; Haiku 392 calls, 0.47 USD; **2.71 USD**. The validator added 60 Haiku calls, 0.1265
  USD, so the folder stands at **593 calls and 2.8389 USD** of the 3 USD cap
  ([`inference/ledger.jsonl`](inference/ledger.jsonl)). This includes a 4-call cost pilot on
  non-cue items run before the prereg (`results/runs_p0_cost.csv`, not used in any analysis).
  Responses are cached (git-ignored), so reruns cost nothing.
- Deviations from the prereg:
  - The pilot cost was 0.016 USD per call, below the 0.022 threshold, so the plan ran unchanged.
  - The pilot was neither at floor nor at ceiling.
  - The PCR role-pick table, which shows Sonnet choosing G, is post hoc.

```bash
cd audits/lab-bench-deep-seqqa
P="../lab-bench/data/.venv/bin/python -I"
$P scripts/build.py      # arms + verification -> data/arms.json, build_check.json
$P scripts/power.py      # -> power.json
$P scripts/plans.py      # -> plans/b*.json
for b in b1_sonnet_pilot b2_sonnet_main b3_sonnet_N b4_haiku_cue b5_haiku_O_N b6_sonnet_noncue_O; do
  $P scripts/run.py --plan plans/$b.json --out results/runs_$b.csv; done    # cached
$P scripts/analyze.py    # -> results.json (rewrites it without the "validation" block below;
                         #    the validator's numbers live in validation/validation.json)
```

Seeds are 0 throughout. Option orders and rebuild choices are hashes of item ids.

Validator's own code (run the same way):

```bash
$P validation/v1_rescore.py   # re-score all 533 cached responses -> validation/v1_rows.csv
$P validation/v2_pairs.py     # paired K/D, exact tests, two-stage bootstrap, drop-one
$P validation/v3_verify.py    # independent key verification and claim 6
$P validation/v4_asym.py      # what differs between K and D besides centrality
$P validation/v5_blind_make.py && $P validation/v5_blind_score.py   # arm-blind hand-read
$P validation/v6_prompt.py    # 60 Haiku calls: the parent's prompt on the same Gibson pairs
$P validation/v7_score.py     # 15-subtask score and the human line
```

## Validation

Independent validator, 2026-11-20, full write-up in
[`validation/VALIDATION.md`](validation/VALIDATION.md), numbers in
[`validation/validation.json`](validation/validation.json). The pipeline reran byte-identically
and every accuracy in `results.json` was re-derived from the response cache by separate code.
What changed:

| What | Auditor | Validated | Why |
|---|---|---|---|
| Sonnet K − D significance | "[0.021, 0.188] over items", interval excludes 0 | same interval, plus **exact paired p = 0.063** (5 vs 0 discordant; one-sided 0.031) | with 5 of 48 pairs discordant the bootstrap's lower bound is 1/48 almost mechanically; the exact test is the honest one. Direction unchanged |
| Sonnet subtask interval | [0.033, 0.200] | **[0.017, 0.250]** | the auditor's cluster bootstrap (`analyze.py:54`) resamples subtask means only |
| Haiku subtask interval | [0.022, 0.089] (excluded 0) | **[−0.044, 0.156]** (contains 0) | same cause; a six-cluster interval cannot be narrower than the item interval. The auditor's value is withdrawn |
| Drop-one robustness | "0.071–0.119, yes, all > 0" | point estimates confirmed; **dropping GC-percent leaves 3 of 42 discordant, p = 0.25, [0.000, 0.167]** | the direction survives every drop, the interval does not |
| Haiku's drop vs the parent's 0.21 | three possible causes listed, untested | **the prompt**: the same 30 Gibson K/D pairs under the parent's step-by-step forced prompt give 0.867 → 0.600, drop 0.267 [0.100, 0.434], p = 0.021 | validator's pre-registered run (claim 4b); claims 3 and 4a are now stated as prompt-specific |
| Haiku's centre picks | not reported | **0.111 vs 0.051** for the other distractors | the one "yes"-rule component Haiku meets |
| K vs D beyond centrality | "D and K differ in one option" | true, **but in D the key becomes the unique longest option (24/33, 26/37, 15/36, 21/29) and in K never (0/135)**; accuracy does not track it, and it favours D | validator's `v4_asym.py`; now stated in "The confound and the arms" |
| Sonnet score vs the human line | "0.85 / 0.86 stay above 0.79 and at the top of the forced-choice range" | **inside** the plausible forced-choice range 0.808–0.866, with the D-score interval [0.793, 0.904] covering all of it; a lead on 18 non-cue items, not like for like | the 0.79 scores unsure answers as wrong (parent claim 7) |
| Claim 6b framing | "differs from the paper's own description" | **an undisclosed convention**: App. C.7.12 names no strand. The numbers (40/40, 21/40) hold and no key changes | re-read of the appendix |
| Claim 6a | sense-orientation reverse primers in the two restriction subtasks | **confirmed and sharpened**: both Gibson subtasks *do* reverse-complement (40/40 each), so the restriction subtasks contradict the paper and their sister families; 80 items; no key changes | validator's own translation and site checks |
| Claim 1 and the score levels | L2 / "rough estimate" | **leads** (18 items each) | `METHODOLOGY.md`: under about 20 units is a lead |

Confirmed unchanged: the rebuild's keys (independently verified, plus 40 of 40 blind picks and
40 of 40 blind arm calls), the pre-registration's timing and the absence of post-hoc item or arm
dropping, the pre-registered verdict "still cannot tell" for both models, all accuracies and
counts, zero refusals and zero unparsed outputs in K, D and I, the 0.042 [0.011, 0.073] score
shift, and the absence of any statement about Opus or a published model.

Not checked: whether Sonnet's drop also quadruples under a step-by-step prompt (budget); the 27
items dropped before any outcome; anything about published models.

**Follow-up:** that open question was then run in
[`../lab-bench-deep-seqqa-reasoning`](../lab-bench-deep-seqqa-reasoning) — the same 48 K/D pairs
under the step-by-step prompt give Sonnet 0.958 → 0.875 (drop 0.083, exact p = 0.22, 48 pairs),
i.e. no growth over the letter-only drop (difference-in-differences −0.021 [−0.104, 0.063]), and
all 8 errors are gene-recall failures rather than option comparisons.
