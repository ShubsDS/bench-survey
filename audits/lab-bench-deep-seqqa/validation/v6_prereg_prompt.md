# Validator pre-registration: is the small Haiku drop a prompt effect or a construction effect?

Written and committed before the run. Validator, 2026-11-20.

## The question

The parent audit's validator found, with a single-option swap on the two Gibson subtasks,
Haiku 0.935 → 0.726 (drop 0.21 [0.11, 0.31], n = 62). This deep dive finds, on the same two
subtasks with a paired K/D rebuild, 0.767 → 0.700 (drop 0.067, n = 30 pairs). Two differences
could produce that:

1. **Prompt.** The parent rendered the FutureHouse template with "Think step by step." and no
   letter-only instruction, and its swap arms were *forced* (the "Insufficient information"
   option removed). This deep dive removed "Think step by step.", added "Respond with only the
   tagged letter and nothing else.", and keeps the refusal option in K and D.
2. **Construction.** The parent's swap kept the wrong-site option's own site and changed only its
   body. Here the option carries a *new* wrong site (W′) in both arms, so the K arm is itself a
   rebuilt item (the auditor's Haiku O − K check is 0.05 [−0.05, 0.15], n = 40).

## The test

Re-run Haiku on the **same 30 Gibson K/D pairs already run** (PCR-gene-gibshindprimers and
PCR-gene-gibssmaprimers, 15 each), with the **parent's prompt**: the FutureHouse template with
"Think step by step.", no letter-only line, and **forced** choice (no refusal option). Same option
order as every other arm (the hashed permutation of the item id). 60 calls, Haiku only, estimated
0.09–0.18 USD against the 0.288 USD left under the folder's 3 USD cap. Arms are named Kp and Dp.

## What counts as what

- **Prompt explains the gap**: Kp − Dp ≥ 0.15 with Kp ≥ 0.90, i.e. under the parent's prompt the
  same rebuilt items reproduce the parent's size.
- **Construction explains the gap**: Kp − Dp < 0.10 and its interval contains 0, i.e. the prompt
  change moves nothing and the rebuilt K arm is where the difference lives.
- **Still cannot tell**: anything else, including Kp ≥ 0.90 with a drop between 0.10 and 0.15.

Statistic: the paired difference over the 30 pairs, exact McNemar (two-sided) and a paired item
bootstrap (2,000, seed 0). 30 pairs give about 60% power against a 0.21 drop and under 20% against
0.07, so a null here is weak evidence; it is reported as a lead either way. Secondary, descriptive:
Kp − K and Dp − D on the same items (prompt effect per arm).
