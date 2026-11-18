# Refutation pass: brief for validators

Status: 2026-11-17. Every audit under [`audits/`](.) is followed by one validator: a fresh agent
that did not write the audit and is told to break it. In round one validators cut back six of
eight headlines. This is the shared brief.

## Your job

Assume the audit is wrong until you have re-derived it. You are judged on errors found and on the
accuracy of the final write-up, not on agreement with the auditor. A confirmed result is a fine
outcome, but only after a real attempt to refute it.

## Steps

1. **Read without trusting.** Read [`METHODOLOGY.md`](METHODOLOGY.md) (especially "Mistakes
   auditors made in round one"), then the audit's `claims.md`, `prereg.md`, `README.md` and
   `results.json`. List every claim with a number. That list is your checklist.
2. **Rerun.** Run the auditor's scripts from the pinned inputs. Record every number that does not
   reproduce exactly.
3. **Re-derive independently.** For each headline number, write your own code in
   `validation/` from the raw inputs, without reading the auditor's implementation first. Compare.
   A number that only the auditor's code can produce is not confirmed.
4. **Go to the source.** Check every statement about the paper, the code or the prompt against
   the paper's text and the pinned source. Re-read the paper's method and limitations before
   accepting that something is undisclosed or a mismatch. Check each "new" claim against
   `prior_work.md` and a search of your own.
5. **Hand-read.** Read at least 40 raw items or transcripts behind the main claim, chosen by you,
   including cases the auditor's rule classifies each way. Label blind where the claim depends on
   a classification, then compare.
6. **Attack the design.** For each claim, run the test most likely to break it:
   - a placebo split or placebo feature with matched sizes and answer mix (1,000 draws);
   - random removal beside every "removing these changes the score";
   - a second, independently defined version of the feature;
   - a different resampling unit; a different reasonable statistic;
   - the three strongest readings under which the benchmark's authors are right;
   - for simulations: change each assumed parameter across its plausible range and report where
     the conclusion flips;
   - for interventions: check the placebo arm, the floor and ceiling, refusals and unparsed
     outputs, and whether the edit changed anything besides the intended feature.
7. **Check the wording.** Exact counts, no "mostly" without a blind sample, no causal words
   without an intervention, evidence level stated per claim, intervals and n with every rate,
   results on fewer than about 20 units marked as leads. Check that the prereg was committed
   before the outcomes (`git log` on the folder) and that any deviation is stated.
8. **Write `validation/VALIDATION.md`.** A table with one row per claim: the auditor's statement,
   your verdict (confirmed, corrected, downgraded, failed, cannot be checked), your number, and
   how you checked. Then what you corrected and why, what you could not check, and the final
   evidence level per claim. Write `validation/validation.json` with your numbers.
9. **Correct the audit's `README.md` and `results.json`.** Fix wrong numbers and wording in place.
   Put the validated result first, add a "Validation" section listing each correction, and keep
   the auditor's original number visible wherever you change one. Do not delete a claim that
   failed: mark it as failed.

## Rules

The rules in `METHODOLOGY.md` on data handling, gated content, outside contact, inference and
committing all apply to you. In particular:

- Write only inside the audit's folder. Commit with
  `audits/tools/commit.sh audits/<benchmark> "<benchmark>: validation - <message>"` after every
  file. Never use `git add -A`, `commit -a`, `checkout`, `switch`, `stash`, `reset`, `rebase` or
  `push`. Other agents share the working tree.
- Inference shares the audit's 3 USD cap and ledger. Haiku only unless the audit justified
  Sonnet. Spend only where a claim cannot be checked otherwise.
- New findings of your own need the same standard as the auditor's: a prereg note before the
  outcome, a placebo, an interval. Label them as the validator's.

## Final reply

Under 300 words: the verdict per claim with your numbers; what you corrected; what could not be
checked; any spend; and the last commit hash.
