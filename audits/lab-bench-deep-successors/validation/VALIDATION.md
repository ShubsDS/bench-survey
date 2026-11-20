# LAB-Bench successors deep dive: independent validation

Validator, 2026-11-20, branch `audits-round3`. I did not write the audit and tried to break it.
No model inference (0 calls, 0 USD). My code and outputs are in this folder:

- `v1_versions.py` / `.json`: claim 1 and the curated subset. Own rules on every SeqQA/DbQA parquet.
- `v2_bounds.py` / `.json`: claims 3 and 4. Human lines by subset and scoring rule, and the bounds.
- `v3_lb2_format.py` / `.json`: claim 2. Own scan of all LABBench2 report cases.
- `v4_peritem_gate.py` / `.json`: claim 5. Own recount of the DeepSeek-R1 recoverability gate.
- `v5_lenfrags_sets.py` / `.json`: a validator lead, post hoc.
- `build_validation_json.py` builds `validation.json`.

New download: `data/val_hfrev_983956ce/` (git-ignored). It holds the SeqQA and DbQA parquets of HF
`futurehouse/lab-bench` @ `983956ce`: public, ungated, CC-BY-SA.

## A. Rerun

I copied `scripts/`, with `data/` and the parent folder linked read-only, and ran `versions`, `lb2`,
`exposure`, `peritem` and `collect`. Every output (`results/*.json`, `results.json`) is byte-identical
to the committed one.

## B. Verdicts

| # | Auditor's statement | Verdict | Validator's number | How checked |
|---|---|---|---|---|
| 1a | Six HF releases carry the cue on 6/6 S subtasks; R1 0.996–1.00, R2 0.9125–0.9167; placebo 0.242–0.258; DbQA multi-seq 80/80 | **Confirmed, one release added** | My rules give 6/6 S in every release: 3-gram centroid or Levenshtein medoid for the five sequence subtasks, and for GC a rule taken from the generator the paper discloses ("±1 neighbours", 1.00). With generic rules only, 5/6: the GC median ties the key with k − 1 (0.50, as R2 does). LEV/NUM S mean 0.9167 (2024) and 0.9125 (2025). sha1 placebo 0.2417–0.2583. DbQA multi-seq LEV 1.00, KMER 1.00, J3 0.994. HF has **seven** distinct SeqQA parquets: `983956ce` (sha `09c7b26e`, live 2024-07-13 to 2024-07-16) is missing from the audit. It holds the same 600 items, keys and options as `7268767a`; only the canary string differs. So "six releases" is right for item content | `v1_versions.py`; HF commit API, SeqQA LFS oid at all 67 commits |
| 1b | RE-seq-numfrags 40/40 in the 2024 releases, gone in 2025-02 | **Confirmed** | Median rule 1.00 in all four 2024 parquets (k = 5, options k−2…k+2); 0.325 from 2025-02 on | `v1_versions.py`; hand read 5/5 |
| 1c | Change log: 200 new ids in five subtasks (2025-02), 120 in three PCR subtasks (2025-09); shared ids never changed key or options | **Confirmed** | Same counts; 0 key and 0 option-set changes on shared ids in every release | `v1_versions.py` |
| 1d | Inspect pins `5c77cec6`; both mirrors byte-identical | **Confirmed** | `lab_bench.py:34` = `5c77cec6…`; mirror sha256 `5864776d…` for both | parent's copies |
| 1e | (not claimed) | **Validator lead** | RE-seq-lenfrags carries a partial cue in the 2024 releases. 3-gram centroid 0.6375 (p = 0.001, chance 0.25). Set-of-lengths centroid 0.725 (p = 0.001), but that rule was defined after the hand read. The hand read got 4/4. In 2025+ it is at chance (0.20–0.23). ORF-transeff: an 8-mer-overlap rule scores 0.50 (p = 0.001, chance 0.25) in every release. This agrees with the parent validator's anti-medoid 0.50 | `v1_versions.py`, `v5_lenfrags_sets.py` |
| 2a | LABBench2 has no options: 0/23,721 cases; 1,912 tasks; SeqQA2 and cloning graded by computation | **Confirmed, wording qualified** | 201 files, 23,721 cases, 1,912 ids. I used three of my own lettered-option patterns (3+ line list, inline (A)(B)(C), "Insufficient information"): 0 hits. Dispatch at `evals/evaluators.py:212` sends cloning to `:105` and seqqa2 to `:131` (validator registry). But SeqQA2 `mutation_restriction` (20 ids, 560 cases) asks "which of the following enzymes" from a printed panel of about 14 enzymes. That is a closed candidate list, not free response. Its key is "None" on 17/20, so a constant answer would score 0.85 | `v3_lb2_format.py` |
| 2b | LABBench2 HF data gated, not downloaded; ungated re-uploads not used | **Confirmed** | `data/labbench2_hf/` holds only README.md and cache metadata; `seqqa2/` is empty. No folder exists for `ssswwwxxx/…` or `haydn-jones/…` | file listing |
| 2c | HuggingFaceBio curated subset removed the cue by exclusion; R1/R2 at chance on the 120 kept items | **Confirmed for the centroid cue; one weaker signal remains** | J3 0.29 / 0.20 / 0.25 and LEV 0.25 / 0.19 / 0.00 (geneprimers-enz / seq-primers / transeff); no p < 0.25. But the kept ORF-transeff scores 0.50 by KMER (p = 0.001). Ids match the pin 120/120. Key text matches on 80/120: the 40 ORF-transeff options were re-encoded U→T | `v1_versions.py` |
| 2d | HuggingFaceBio published the options-only leak on 4 of 6 S subtasks on 2026-10-26, before the parent | **Confirmed, detail corrected** | First commit `860d9710` 2026-10-26 15:12 UTC. The README at `c2b04610` (2026-10-26) says Qwen3 "still scored above 70% on those same four tasks", and does not name them. The task names and the 39/40, 31/40, 31/40, 31/40 labels (gibssma, gene-enz, gibshind, seq-enz; Qwen3-4B-Base, choices-only log-likelihood) are in figures added 2026-10-27 (`33e24310`). It tested 7 subtasks, not AAseq, GC-percent or DbQA. A second test, corrupting or shuffling the DNA, left the score unchanged on the same four | HF commit API, both README versions, both figures |
| 3a | Human SeqQA line 0.789 (unsure = wrong), 0.809 with chance credit | **Confirmed** | 0.7893; 0.8084 (the auditor's 0.8085 is rounding) | `v2_bounds.py` from paper v3 Tables 2–4 |
| 3b | Anthropic cards and Concordia use 0.79 / 79; xAI uses 0.79 / 0.77 / 0.60; US/UK AISI credited unsure answers at chance | **Confirmed, one omission** | The Opus 4.5 and Sonnet 4.5 card figures read "Human baseline: 0.79". The Claude 4 card draws a dashed line at about 0.79. Concordia states 79 in 2025-Q4 and 2026-Q1; its 2026-Q2 and Q3 pages give no number. The xAI Grok 4.1 and 4.20 tables are as stated, but both cards add that the paper's baselines "likely underestimate the performance of high-context experts". The AISI §3.3 text is verbatim in both NIST reports | card text and renders; airiskmonitor.net pages re-read 2026-11-20 |
| 3c | Opus 4 (≈0.79) and Sonnet 4.5 (0.780) "reached" the line only under unsure = wrong | **Sonnet 4.5 confirmed; Opus 4 downgraded** | Sonnet 4.5's own card figure gives 0.780 against the 0.79 label, and its error bar crosses the line. Opus 4 is ≈0.79 ± 0.02, read from a figure, and 0.808 is inside that reading error. That 0.79 is also the best of three shot settings (the 0-shot bar). The same model scores 0.723 at 10-shot in the Sonnet 4.5 card and 0.69 in the Opus 4.1 addendum | renders `claude4_p100`, `s45-134`; card text |
| 4a | Bound arithmetic (A = (s − w)/(1 − w); w = 0.40 or 0.467) | **Confirmed** | Every A value reproduces to 3 decimals | `v2_bounds.py` |
| 4b | Under A, below the human 0.764: Opus 4 (0.65), Sonnet 4.5 (0.63), Opus 4.5 (0.753), AISI Sonnet 3.5 new (0.738 vs 0.771); Gemini 3 Pro and GPT-5.4 "just above" | **Corrected** | The comparison line is unsure = wrong only. Cue-free human means are F9 0.764 / 0.789 / 0.831 and F8 (2024) 0.771 / 0.798 / 0.842, under unsure = wrong / chance credit / guesses at the humans' precision. AISI used chance credit, so its like-for-like gap is A − h = **−0.061** (auditor −0.034) and B − h = +0.062 (auditor +0.089). Under chance credit Gemini 3 Pro is −0.006 and GPT-5.4 +0.003, so both are **at** the line. Opus 4.5 is −0.012 / −0.036 / −0.078. Gaps within about ±0.05 sit inside the item noise (360 items over 9 templates) and the human line's own sampling (humans covered 64% of SeqQA). Only Opus 4 (−0.114), Sonnet 4.5 (−0.131) and Opus 4.1 (−0.123) are clearly below under A | `v2_bounds.py` |
| 4c | Under reading B "every claimant is above human" | **Corrected** | True under unsure = wrong (+0.016 to +0.21). Under chance credit: Opus 4 +0.001, Sonnet 4.5 −0.009, Opus 4.1 −0.004 (no claim made), AISI o1 −0.028 (claim was "approaching"). These are at the line, not above. Reading B is not an upper bound: the identified range of cue-free accuracy is [A, min(1, s/(1 − w))] and its upper end is 1 for every row | `v2_bounds.py` |
| 4d | GPT-5.5 and later and Meta's tool runs "stay clearly above" | **Confirmed** | GPT-5.5 A − h = +0.094 / +0.069 / +0.027; GPT 6 Astra +0.147 / +0.122 / +0.081; Meta +0.064 to +0.191. These stay above under all three rules | `v2_bounds.py` |
| 4e | Item set assumed to be 600 public items | **Supported, not proven** | AISI states 600 items (§3.1). Opus 4.5 0.8517 = 511/600, Opus 4.1 0.785 = 471/600 and Sonnet 4.5 0.780 = 468/600 are all consistent with 600 items and an item mean. Concordia and Meta do not state their item sets | arithmetic |
| 5 | DeepSeek-R1 chosen option recoverable on 26 S items in 2 S subtasks; gate not met | **Confirmed** | Own pattern: 26 S (24 GC, 2 AAseq; auditor 25 / 1), 123 F on `4709d14f` (auditor 96). The gate fails either way: only 2 S subtasks | `v4_peritem_gate.py` |
| L(a) | SeqQA2 `mutation_restriction` key "None" on 17/20 | **Confirmed** (lead) | 17/20 unique ids. The `answered_none_rate` field is a string match on truncated answers and can disagree with the computed score (Gemini 3 Pro: 0.35 answered None, 0.94 correct on None keys) | `v3_lb2_format.py`, `results/lb2.json` |
| L(b) | Opus 4.5/4.6 SeqQA2 refusals 40–136 | **Not checked** | — | — |
| L(c) | 2024 models on RE-seq-numfrags: precision 0.11–0.28, "chance 0.25" | **Corrected** | In 2024 numfrags had 5 options, so chance is 0.20, not 0.25. Accuracy was 0.09–0.17 (paper Table 2) | paper v3; `v1_versions.json` k |

## C. What I corrected and why

1. **The bounds compared the worst case with the most favourable human line only.** The
   cue-free human line ranges from 0.764 to 0.831 (F9), depending on how unsure answers are
   credited. Under the US/UK AISI rule (chance credit), Gemini 3 Pro and GPT-5.4 sit at the line,
   not above it, and AISI's own Sonnet 3.5 gap is −0.061, not −0.034. The prereg asked for a
   comparison "with the human line the document used"; for AISI that is chance credit. The
   prereg's cue-free human value 0.760 is an arithmetic slip; the correct value is 0.7644. The
   README does not mention this deviation.
2. **Reading B has equal standing.** Under chance credit, Opus 4 and Sonnet 4.5 are at the
   cue-free line (+0.001, −0.009) even when the cue gave them nothing. The headline sentence
   ("most … statements up to Opus 4.5 sit below the human score") reads as if those models were
   below human. They are below only in the worst case, and for Opus 4.5 and AISI's Sonnet 3.5
   only within noise.
3. **The worst case has evidence against it for the one model group with data.** On
   RE-seq-numfrags, a cue subtask in 2024 where the median rule scores 1.00, the six 2024 models
   in the paper scored 0.09–0.17. US AISI reports that o1 and several reference models did about
   as well on free-response numfrags as on multiple choice. The audit's §2 says the AISI conversion
   "does not measure the centroid cue", but numfrags was cue-bearing in the release AISI used, and
   there the result is no multiple-choice advantage. This says nothing about 2025+ models.
4. **The human line is not on the models' items.** Human numbers come from the full set
   (public + private), the 2024 generation, and 64% coverage. Three of the nine cue-free subtasks
   (PCR-geneprimers-enz, RE-seq-lenfrags, RE-seq-numfrags) were regenerated in 2025. On the six
   never-regenerated cue-free subtasks the human mean is 0.733 (unsure = wrong) or 0.766 (chance
   credit). That is lower, so the worst-case gaps for 2025+ runs would shrink toward zero.
5. **Opus 4's "below 0.809" is inside the reading error** (≈0.79 ± 0.02). It is also a best of
   three shot settings.
6. **"No options in any task family" (LABBench2) is too strong.** One SeqQA2 type gives a closed
   enzyme panel. The centroid cue cannot exist there, but a constant answer scores 0.85.
7. **"Fixed by exclusion" (HuggingFaceBio) holds for the centroid cue.** ORF-transeff, which the
   subset kept, still carries a 0.50 options-only rule (chance 0.25) by two independent
   definitions (8-mer overlap here, Levenshtein anti-medoid by the parent validator). Qwen3-4B
   itself scored 10/40 choices-only there, so this is a rule-level lead, not a model finding.
8. **Release count.** There are seven SeqQA parquet files on HF; six distinct item contents.
9. **xAI's caveat** about the human baselines should be stated beside the xAI row.

## D. For the orchestrator: parent novelty statement (do not edit here)

`../lab-bench/prior_work.md` ("What is new here", first bullet) and the parent validator's
"found no prior report of a SeqQA or DbQA options-only key" are wrong in part. HuggingFaceBio
`seqqa-carbon-curated-3tasks` came first. Its README text is dated 2026-10-26; the per-task
figures are dated 2026-10-27, three weeks before the parent (2026-11-17). It showed that
Qwen3-4B-Base answers four PCR subtasks from the options alone (39/40 on gibssma; 31/40 each on
gene-enzprimers, gibshindprimers and seq-enzprimers). It also showed that corrupting the DNA did
not change the scores on those four. Still new in the parent:

- the content-blind, deterministic rules and the mechanism (distractors derived from the key, so
  the key is the centroid);
- ORF-seq-AAseq and Prop-seq-gcpercent;
- DbQA `variant_multi_sequence`;
- the Haiku L4 edits;
- the human "unsure" arithmetic and the stratified model-minus-human comparison.

The parent's novelty line should cite HuggingFaceBio and narrow its claim to these.

## E. Hand read

I labelled 40 items blind: options shuffled, key hidden, my pick of a "centre" written down before
reveal.

- **Sample.** 10 PCR enzyme items from the 2025-02 regeneration (ids the parent never saw), 8
  numfrags (5 from 2024, 3 from 2025), 7 lenfrags (4 / 3), 6 Gibson, 4 geneprimers-enz, 3
  seq-primers and 2 transeff.
- **Called a centre on 25: correct on 25.** These were all 10 regenerated PCR items, all 6 Gibson,
  the 5 numfrags-2024 and the 4 lenfrags-2024. In the regenerated PCR items the same construction
  is visible: wrong site with the key's body, frame-shifted body, another gene.
- **Saw no centre on 15.** These were geneprimers-enz (a symmetric 2 × 2 grid of enzyme pairs),
  2025 numfrags and lenfrags, seq-primers and transeff. This agrees with the rules.

## F. Not checked

- The o1 figure value (0.77) and the Gemini and Concordia methods (not published).
- Meta's expert-baseline bar.
- The LABBench2 LLM-judge families.
- The refusal lead L(b).
- Kimi K2.5 and ProtoPilot rows.
- Whether any card's run offered the "Insufficient information" option.
- The search for LABBench2 numbers compared with the old human line covered only the 45
  documents in `data/cards_new/`; none makes such a comparison.

## G. Final evidence levels

| # | Level |
|---|---|
| 1 | L2 (rules; confirmed). Lead: partial cue on RE-seq-lenfrags 2024 and on ORF-transeff |
| 2 | Result, L1 (format and grader code); LABBench2 qualified for `mutation_restriction`; curated subset "centroid cue removed" |
| 3 | L1; Opus 4 "at or below", not "below" |
| 4 | L1 arithmetic. Corrected: three human lines, the document's own rule for AISI, and reading B with equal prominence. No claim is shown to be below human; only Opus 4, Sonnet 4.5 and Opus 4.1 could be below under the worst case beyond noise |
| 5 | Not analysable (confirmed) |
