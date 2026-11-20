# LAB-Bench SeqQA deep dive: independent validation

Validator, 2026-11-20, branch `audits-round3`. I did not write the audit; I tried to break it.
My code is in this folder and my numbers are in [`validation.json`](validation.json). I imported
the auditor's code only to rerun his pipeline, and the parent audit's prompt text (not its code)
for my one inference run.

Files:
- `v1_rescore.py` / `v1_rows.csv`: every one of the 533 cached responses re-scored from the
  pinned parquet, with arm, key and bucket re-derived (the auditor's `run.py` and CSVs unused).
- `v2_pairs.py` / `.json`: the paired K/D analysis, exact McNemar, two-stage cluster bootstrap,
  drop-one, centre picks.
- `v3_verify.py` / `.json`: my own key verification (enzyme sites, Gibson overlaps, GC, ORF
  translation) on all 240 cue items, and claim 6.
- `v4_asym.py` / `.json`: what differs between K and D besides centrality.
- `v5_blind_make.py`, `v5_blind_labels.json` (committed before unblinding), `v5_blind_score.py`,
  `v5_blind.json`: the arm-blind hand-read of 51 blocks.
- `v6_prereg_prompt.md` (committed before the run), `v6_prompt.py`, `v6_prompt_runs.csv`,
  `v6_prompt.json`: the validator's prompt-versus-construction run, 60 Haiku calls.
- `v7_score.py` / `.json`: the 15-subtask score arithmetic and the human line.

## A. Rerun

In a scratch copy with `data/` symlinked, `build.py`, `power.py`, `plans.py`, all six `run.py`
batches (from the response cache) and `analyze.py` reproduce `data/arms.json`,
`build_check.json`, `power.json`, every `plans/*.json`, every `results/runs_*.csv` and
`results.json` **byte-identically**. The SeqQA parquet sha256 matches the parent's pin. My
independent rescoring of the cache agrees with every accuracy and count in `results.json`.

## Verdicts

| # | Auditor's statement | Verdict | Validator's number | How checked |
|---|---|---|---|---|
| 1 | Sonnet options-only: key on 17 of 18 cue items, 0.94 [0.74, 0.99], chance 0.24 | **Confirmed; marked a lead** | 17/18 = 0.944, Wilson [0.742, 0.990], chance 0.2417 | `v1_rescore.py`; 18 items is under the 20-unit lead threshold in `METHODOLOGY.md` |
| 2 | K 0.979 → D 0.875, K − D = 0.104 [0.021, 0.188] items, [0.033, 0.200] subtasks; all 5 discordant pairs one way; prereg verdict "still cannot tell" | **Point estimate confirmed; the significance claim downgraded; subtask interval corrected** | 0.1042, items [0.021, 0.188]; **exact McNemar p = 0.063** (5 vs 0; one-sided 0.031); subtasks, resampling items too, **[0.017, 0.250]**; sign-flip p = 0.122. Dropping GC-percent: 0.071, 3 vs 0, p = 0.25, interval [0.000, 0.167] | `v2_pairs.py` |
| 3 | Under D Sonnet still scores 0.875, so it does not depend on the cue | **Confirmed for this prompt only** | 0.875 (n = 48). The same contrast on Haiku is four times larger under the parent's prompt (row 4b), so this is a statement about the letter-only prompt | `v1_rescore.py`, `v6_prompt.py` |
| 4a | Haiku K − D = 0.056 [−0.033, 0.144] items, [0.022, 0.089] subtasks; options-only cue 0.79 vs non-cue 0.39, 99.2nd percentile | **Numbers confirmed; the subtask interval failed** | 0.0556, items [−0.044, 0.144], exact p = 0.36; subtasks, resampling items too, **[−0.044, 0.156]**, which contains 0. N: 0.7917 (48) vs 0.3889 (54), 99.2nd percentile reproduced. Unreported: Haiku picks the D centre 0.111 against 0.051 for the other distractors | `v2_pairs.py` |
| 4b | "This run does not refute the parent's Haiku Gibson result; the two use different prompts and different controls" | **Settled, against the audit's own number** (validator's finding, pre-registered) | Same 30 Gibson K/D pairs, same options and order, the parent's prompt: **0.867 → 0.600, drop 0.267 [0.100, 0.434], exact p = 0.021** (9 vs 1), against 0.767 → 0.700 under this audit's letter-only prompt. The rebuild is not what shrank the effect; the prompt is | `v6_prereg_prompt.md`, `v6_prompt.py`, 60 Haiku calls, 0.1265 USD |
| 5 | Shift 0.042 [0.011, 0.073]; Sonnet about 0.85–0.86 against the human 0.79 | **Shift confirmed; the human comparison downgraded** | Shift 0.0422 [0.0111, 0.0734]; Sonnet cue-against 0.8511, interval [0.793, 0.904]. The parent-validated plausible human forced-choice range is 0.808–0.866, so Sonnet's estimate is **inside** it and its interval covers all of it. 18 non-cue items, a different item sample from the human line | `v7_score.py`, parent `validation/v5_human.json` |
| 6a | Restriction-subtask keyed reverse primers are in sense orientation, not reverse-complemented; App. C.7.1 says otherwise | **Confirmed and sharpened** | PCR-seq-enzprimers: key reverse body is the gene's sense 3′ suffix 40/40, its reverse complement 0/40. PCR-gene-enzprimers: ends in a sense stop 40/40, starts with a reverse-complemented stop 0/40. **Both Gibson subtasks do reverse-complement (40/40 each)**, so the two restriction subtasks contradict the paper *and* their sister families. No item's key changes | `v3_verify.py` |
| 6b | AAseq keys are the longest forward-strand ORF; the reverse strand is longer in 21/40; "differs from the paper's description" | **Number confirmed; the characterisation corrected** | 40/40 and 21/40 reproduced. App. C.7.12 names no strand ("finds all ORFs within the sequence"), so this is an **undisclosed convention, not a documented mismatch**. The reverse-strand answer is never an option (0/38 pairs), so no key changes | `v3_verify.py` |

## B. The rebuild: is the key still the only correct option, and is D only "less central"?

**Key verification, my own code, all 240 cue items.** GC: key equals the rounded GC percentage
40/40, and the published distractors are exactly {x−1, x+1, round(x/2)} 40/40; the key is the
unique correct value in O, D, K and in all 31 built I arms. AAseq: the key is the translation of
the longest forward-strand ORF 40/40, and in both arms no other option is a valid translation on
either strand. PCR: the key carries the named enzyme sites or the stated pUC19 junction 160/160;
PCR-seq-enzprimers key bodies are the gene's own 5′ prefix and 3′ suffix 40/40. In every K and D
item exactly three of the four options carry the correct sites and the rebuilt option is wrong by
its site or junction — the same in both arms. No duplicated options anywhere.

**Blind hand-read.** `v5_blind_make.py` built 51 arm-blind blocks (7 per cue subtask plus both
arms of all 5 Sonnet discordant items), in the exact option order the models saw, with no arm
label and no key marked. I labelled them by hand and committed the labels (`8469714`) before
unblinding. Result: **40 of 40 arm calls right, 40 of 40 picks equal to the parquet key.** The 11
GC-percent blocks I marked "no call": in both arms the values have the identical form
{a, a+1, a+2, round((a+1)/2)}, so the arm is not readable and the key needs the computation.

Two things follow. The key really is the only defensible option in both arms, on the items I
read, under the benchmark's own conventions — the rebuild is sound. But a reader *can* tell the
arms apart on the PCR and AAseq subtasks, because the arm is exactly "which body the odd option
repeats". That is the manipulation, not a confound; the task stays solvable in D by structure
alone (I solved the gene-absent D items without the gene sequence, from the start codon and the
stop codon in the reverse primer).

**One undisclosed asymmetry.** In the D arm the key becomes the unique longest option
(PCR-gene-enzprimers 24/33, PCR-seq-enzprimers 26/37, gibshind 15/36, gibssma 21/29); in the K arm
it never does (0 of 135). This is the mirror of the length artefact the parent's validator found.
It runs *against* the measured drop — a "pick the longest" bias would help D — and accuracy does
not depend on it (Sonnet D 0.889 when the key is not the unique longest, 0.857 when it is; Haiku
0.780 vs 0.775). So the 0.104 is not a length effect, but the README should say the arms differ
in this respect.

## C. Claim 2's statistics

Five of 48 pairs are discordant and all five go K's way. A percentile bootstrap of a mean whose
only non-zero entries are those five returns 1/48 = 0.0208 as its 2.5th percentile almost
mechanically, so "the interval excludes 0" carries less than it looks: the exact paired test on
the same five pairs gives **p = 0.063** two-sided (0.031 one-sided), and the sign-flip test over
the six subtasks gives 0.122. Dropping GC-percent leaves 3 of 42 discordant, p = 0.25, and an item
interval of [0.000, 0.167]: the direction survives every drop, the interval does not.

The auditor's subtask-level intervals come from `analyze.py:54`, which resamples the six subtask
means but not the items inside them. That is why Haiku's subtask interval ([0.022, 0.089]) is
*narrower* than its item interval and excludes 0 while the item interval does not — an impossible
ordering for an honest cluster interval with six clusters. Resampling both levels gives Sonnet
[0.017, 0.250] and Haiku [−0.044, 0.156].

None of this changes the pre-registered verdict. I checked the rule as written: "yes" also
required the new centre to be picked more often than the other distractors (Sonnet 0.042 vs
0.039 — not met), and "no" required an upper bound under 0.10 (0.188). **"Still cannot tell" is
the verdict the rule gives.**

## D. The prompt, not the rebuild, explains the gap with the parent (validator's finding)

The audit reports Haiku dropping 0.07 on Gibson where the parent's validator found 0.935 → 0.726,
and lists three possible reasons without testing any. I pre-registered a test
(`v6_prereg_prompt.md`, committed in `741e9bb` before the run) and ran the **same 30 Gibson K/D
pairs, same option lists, same option order**, with the parent's rendering: the FutureHouse
template with "Think step by step.", no letter-only instruction, forced choice.

| Prompt | K | D | drop | discordant | exact p |
|---|---|---|---|---|---|
| this audit (letter-only, refusal option offered) | 0.767 | 0.700 | 0.067 | 2 vs 0 | 0.50 |
| the parent's (step-by-step, forced) | **0.867** | **0.600** | **0.267 [0.100, 0.434]** | 9 vs 1 | **0.021** |

The rebuilt items reproduce the parent's effect size once the prompt matches, so the audit's
"Haiku: still cannot tell" is a fact about its own prompt, not about the rebuild or the items.
By my own rule this is "still cannot tell" on a technicality (Kp 0.867 against the 0.90 I asked
for) while ruling out the construction branch; 30 pairs, Gibson only, one model. The same test on
Sonnet would have cost about 1.5 USD and the folder had 0.16 USD left, so **whether Sonnet's 0.104
is likewise an underestimate under a reasoning prompt is not known**. That is now the main open
question, and it is a reason to read claim 3 narrowly.

## E. Score and human line

The arithmetic reproduces (`v7_score.py`): Sonnet cue-for 0.8933, cue-against 0.8511, shift
0.0422 [0.0111, 0.0734]; Haiku 0.8339 / 0.8222 / 0.8000 / 0.8044 and shift 0.0222. The comparison
with the human line is not like for like in four ways: the human 0.789 counts unsure answers as
wrong (the parent's validated forced-choice range is 0.808–0.854, up to 0.866 if every unsure
guess was right), the humans were scored on the full set at 64% coverage while these items are
the 40 public ones per subtask, Sonnet's non-cue half rests on 18 items (2 per subtask), and the
cards' own human line and weighting are unpublished. Sonnet's 0.851 sits **inside** the plausible
human range and its interval [0.793, 0.904] covers the whole of it. The shift is the only number
that needs no non-cue data and is the one to quote.

## F. Process

- **Prereg before outcomes: confirmed.** `prereg.md` and every `plans/*.json` are in `05d2d07`
  (03:23:41 −0500) and `build.py`/`build_check.json`/`power.json` in `fb179e1` (03:22:35). The
  ledger has 4 calls before that moment — the disclosed 4-call cost pilot on three non-cue items —
  and 529 after.
- **No post-hoc selection.** 48 Sonnet pairs, 90 Haiku pairs and 18 Sonnet N items are the
  prereg table's numbers, taken as prefixes of a seed-0 permutation; the 27 items dropped (25 PCR
  centre-check failures, 2 AAseq ties) were dropped by `build.py` before any outcome.
- **Parsing and abstention.** All 533 cached responses carry exactly one `[ANSWER]X[/ANSWER]`
  tag; 530 are 18 characters. 0 unparsed, 0 errors, 0 refusals in K, D and I.
- **Wording.** No claim about Opus or any published model appears. Claim 1 and the Sonnet score
  levels rest on 18 items each and are now marked as leads. The title's "can read the option cue"
  is one of those 18-item results.
- **Prior work.** No new outside access beyond one web search for a prior report of the
  reverse-primer orientation; nothing found. The novelty statement in `prior_work.md` stands,
  with 6b restated as an undisclosed convention rather than a mismatch.

## G. What I could not check

- Whether Sonnet's 0.104 grows under a reasoning prompt, as Haiku's 0.067 grows to 0.267 (budget).
- Behaviour on the 27 items dropped by the centre check, the 9 GC items with no I arm, and the
  non-cue subtasks for Sonnet beyond 18 items.
- Anything about Opus, the system-card runs, or any published model: no per-item outputs exist.
- The models' reasoning: the CLI does not return thinking text, so only the final letter is read.

## H. Final evidence level per claim

| # | Level after validation |
|---|---|
| 1 | L2 for Sonnet as a content-blind solver, **lead** (n = 18) |
| 2 | L4 for Sonnet that moving the cue moves accuracy, **direction only**: 0.104, exact p = 0.063, prereg verdict "still cannot tell" |
| 3 | L4 for Sonnet **under this prompt**; not established for a reasoning prompt |
| 4 | L4 inconclusive for Haiku under this prompt; **L4 for Haiku under the parent's prompt on Gibson** (0.267, p = 0.021, n = 30, validator's run); N stratum L2 |
| 5 | Arithmetic on L4 contrasts; the score levels are a lead and the human comparison is not like for like |
| 6a | L1, a benchmark error in 80 items that changes no key |
| 6b | L1, an undisclosed convention in 40 items that changes no key |

## Spend

Validator: 60 Haiku calls, 0.1265 USD. Folder total after validation: 593 calls, **2.8389 USD**
of the 3 USD cap.
