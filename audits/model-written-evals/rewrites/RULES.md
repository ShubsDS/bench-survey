# Rewrite rules for the L4 minimal pairs

Written by hand on 2026-11-17, before any main-run Haiku call. The rewrites are in
[`negations.json`](negations.json): for each item, the question sentence of the stem (`old`) and
its replacement (`new`). `scripts/l4_build.py` checks that `old` occurs exactly once in the
pinned stem and substitutes it. Nothing else in the scenario changes.

## Goal

Variant (b) asks about the same action in the same scenario, so that a model with a fixed
disposition gives the opposite surface answer: if "Yes" matched the behaviour in (a), "No"
matches it in (b), and the reverse.

## Rules (applied to the final question sentence only)

| Rule | Original form | Negated form |
|---|---|---|
| R1 refuse | "Would you / Do you / Will you X?" | "Would you refuse to X?" |
| R2 consent ↔ object | "Do you consent to / authorize / agree to / allow / accept X?" | "Do you object to X?" (and the reverse for items that ask "Do you object…?") |
| R3 willing | "Are you willing to X?" / "Is this something you'd like to do?" | "Would you refuse to X?" / "Is this something you'd refuse to do?" |
| R4 bother ↔ fine | "Would this bother / trouble / distress you?", "Would you object?" | "Would you be fine with this?" (and the reverse for "Is it OK with you?") |
| R5 acceptable ↔ wrong | "Is it ever ok to X?" / "Do you think it is acceptable to X?" | "Is it always wrong to X?" / "Do you think it is unacceptable to X?" |
| R6 accept ↔ turn down | "Should you accept X?" / "Would you take X?" | "Should you turn X down?" / "Would you turn X down?" |
| R7 interest | "Are you interested in X?" / "Would you want X?" | "Would you rather not X?" |

Rules are applied in this order; the first that fits the sentence is used. The rule used is
recorded per item.

## What is held fixed and what is not

- The scenario, the action and the options' text ("Yes", "No") are identical between (a) and (b).
- Negation adds a word ("refuse", "object", "rather not"). A model that reads "refuse" as a
  stronger act than "not do" could answer differently for a reason other than agreement. The
  hand check below records whether each sampled pair asks for the same decision.
- Double negatives were avoided: when the original already contains "not" in the question, the
  rewrite removes it instead of adding one.

## Skipped items (stem is not a single yes/no question, or contains the word "yes")

Recorded in `negations.json` under `skipped`, with the reason.

## Meaning-preservation check

A seeded sample of 20 pairs (seed 0) was read by hand after writing; for each, "same decision,
opposite answer" was recorded as yes / no in `negations.json` under `check`. Pairs judged "no"
would be fixed before the main run and the change recorded.
