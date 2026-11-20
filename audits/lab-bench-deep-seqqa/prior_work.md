# Prior work

See the parent's [`../lab-bench/prior_work.md`](../lab-bench/prior_work.md) and
[`../lab-bench/validation/VALIDATION.md`](../lab-bench/validation/VALIDATION.md) §D. No new search
was run for this deep dive (no new outside access beyond inference).

What this folder builds on, and what is new:
- Already known (parent, validated): the options-only rules on six SeqQA subtasks (L2); Haiku
  follows the cue on the two Gibson subtasks (L4, the auditor's edit and the validator's
  one-option swap); no effect detectable for Haiku elsewhere; the 2024 stratum test had no power.
- Already public: the paper's generator descriptions (App. C.7) and the "longest option" issue
  ([Future-House/LAB-Bench#18](https://github.com/Future-House/LAB-Bench/issues/18)).
- New here: a paired, pre-registered decoy-centred (D) versus key-centred (K) design in which D and
  K differ in one option (PCR) and keys are verified by computation; the same test on Sonnet 5.5;
  an independent-distractor arm on GC-percent; and two key-definition findings from the
  verification (sense-orientation reverse primers in both restriction subtasks; forward-strand-only
  "longest ORF" in AAseq). Neither was in the parent's write-up or validation.
