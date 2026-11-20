# Sonnet K/D under a step-by-step prompt: pre-registration

Written 2026-11-20 and committed before any non-pilot call. Done before this file: the run script
(`scripts/run.py`, committed in `abc33ae`), a 4-call cost pilot on two Gibson pairs that are
**not** in the sample (outcome seen: 4 of 4 correct, K and D; 0.0871 USD, 0.019–0.025 USD per
call), and `scripts/power.py` (`power.json`).

## The inherited question

`audits/lab-bench-deep-seqqa` (validated) built paired items in which the question and key are
fixed and one distractor's body changes, so that the option the others resemble is the key (K)
or a decoy (D). Under a **letter-only** prompt Sonnet 5.5 went 0.979 → 0.875 on 48 pairs
(drop 0.104, 5 vs 0 discordant, exact p = 0.063): "still cannot tell". Its validator then ran
Haiku on the same 30 Gibson pairs with the parent audit's **step-by-step, forced** prompt and
found 0.867 → 0.600 (drop 0.267, p = 0.021) against 0.067 under letter-only. Published runs let
models reason, so the open question is: **does Sonnet 5.5 rely on the option cue when it reasons
step by step?** A result here is about Sonnet 5.5 under this prompt only; nothing here is a
statement about Opus or any published run.

## Design

- **Items:** the same 48 K/D pairs as the letter-only Sonnet run (`../lab-bench-deep-seqqa/plans/
  b1_sonnet_pilot.json` + `b2_sonnet_main.json`; arms from `../lab-bench-deep-seqqa/data/arms.json`,
  keys verified there by computation and by the validator's own code and blind read). On
  GC-percent K equals the original item.
- **Prompt:** the parent's rendering (FutureHouse template with "Think step by step.", no
  letter-only line), **forced** choice (no refusal option), the same hashed option order, so the
  key has the same letter in K and D. It is byte-for-byte the rendering of
  `../lab-bench-deep-seqqa/validation/v6_prompt.py`. The only change from the letter-only Sonnet
  run is the prompt (and the removal of the refusal option, which Sonnet never chose there).
- **Model and runner:** `claude-sonnet-5-5`, `Caller(..., cap_usd=2.50, neutral_cwd=True)`, at
  most 3 concurrent calls, default extended thinking (not returned); the visible step-by-step
  text is returned and is read.
- **Order and n (fixed now):** the 20 Gibson pairs first (gibshind and gibssma interleaved, each
  in the earlier plan's order), then the other four subtasks round-robin (GC, AAseq,
  PCR-seq-enzprimers, PCR-gene-enzprimers, each in the earlier plan's order; the last four pairs
  are PCR-gene-enzprimers, which has 10). **Target n = 48 pairs (96 calls).** At the pilot's 0.022
  USD per call that is about 2.10 USD of the 2.41 left. If the cap cuts the run, the analysed n is
  the pairs completed in this order (both arms present); a pair with one arm is dropped and
  reported. At 0.030 USD per call the run still reaches at least 40 pairs, all 20 Gibson
  included.

## Statistics

- **Primary:** K − D over pairs. Exact McNemar (two-sided). Item-level paired bootstrap 95%
  interval (2,000, seed 0). Subtask-level interval: two-stage bootstrap (resample the six
  subtasks, then items within each), 2,000, seed 0.
- **Secondary:** among D answers, the rate of picking the decoy centre (`D_centre`) against the
  per-other-distractor rate; the same on Gibson alone. The same primary statistics on Gibson
  alone (20 pairs). Descriptive: the change from the letter-only run on the same pairs
  (reasoning drop minus letter-only drop, paired bootstrap).
- **Buckets per arm:** correct / wrong / unparsed / error. No refusal option is offered; any
  textual refusal or missing tag is "unparsed" and counted as not correct, reported separately,
  and the primary contrast is repeated on pairs where both arms parsed.

## Decision rule: "Sonnet relies on the cue under step-by-step reasoning"

- **Yes:** K − D ≥ 0.10 **and** exact two-sided McNemar p < 0.05.
- **No:** the item-level 95% upper bound < 0.10 **and** K accuracy ≥ 0.70 (if K and D are both
  ≥ 0.95, reported as "held at ceiling").
- **Cannot tell:** anything else.
- Reported beside it, as a separate label and not part of the decision: **"follows the decoy
  centre"** if under D the centre is picked more often than the per-other-distractor rate. This
  separates "option structure moves accuracy" (the rule above) from "picks the option the others
  resemble". The earlier prereg required both for "yes"; that rule is also evaluated here for
  continuity and reported, but the decision above is the one this folder states. Reason: the
  earlier run showed Sonnet's D errors going to the other-gene option, not the centre, so the
  centre requirement tests one mechanism of reliance rather than reliance.

**Power** (`power.json`, 5,000 simulations, 0.01 D-only rate): at n = 48, P("yes") = 0.975 for a
true drop of 0.27 and 0.32 for 0.10; P("no") = 0.94 with no effect. At n = 40: 0.94 / 0.21. On
Gibson alone (n = 20): 0.46 for 0.27. So the design can detect a Haiku-sized effect and cannot
reliably detect a letter-only-sized one; a 0.10 effect will usually land in "cannot tell".

## Reading the D errors

Every D error's visible reasoning is read. Labels (assigned before looking at which option was
the centre, using a copy of each text with the option letters replaced by role-free tokens where
the text allows):
- **compares** — the text says it compared options with each other (shared sequences, which
  options agree, "the others all share", elimination by resemblance);
- **computes-and-slips** — it computes or checks against the question or the gene (sites,
  frame, translation, GC count) and makes an error;
- **recall** — it states a gene sequence or fact from memory and relies on it;
- **other / unclear.**
Counts are reported per label, with the chosen option's role. The same labels are applied to K
errors.

## What would not count

- A drop without the paired K arm. A Sonnet result extended to Opus or any published model.
- Any change to this rule after seeing outcomes; deviations are listed in the README.
