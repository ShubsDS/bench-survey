# Emergent misalignment metric: prior work

Searched on 2026-11-17: the paper (arXiv v7) and its appendices; Dickson v3; the Model Organisms
paper; LessWrong and the Alignment Forum; the issue titles in the paper's GitHub repo; HF
dataset search. Each entry gives what the source already showed. The last section says what is
left for this audit.

## The paper itself (Betley et al., arXiv 2502.17424 v7)

- **Question selection, disclosed.**
  - The 8 main questions were "selected for diversity and for showcasing interesting behavior"
    (§2.1). The 48 pre-registered questions were fixed "without trying them on any finetuned
    models".
  - Table 1: insecure GPT-4o scores 0.198 ± 0.071 on the 8 and 0.057 ± 0.026 on the 48.
    Jailbroken scores 0.005 on the 8 and 0.052 on the 48.
  - So on the pre-registered set, insecure and jailbroken are close. This is visible in the
    paper's own table.
- **Thresholds, disclosed and partly tested.**
  - Coherence < 50 and refusals are excluded; alignment < 30 counts as misaligned (§3.2).
  - The paper calls the thresholds "arbitrary", but says varying them "has minimal effect"
    (App. C.2: alignment ≤ 1 in Fig. 18, coherence ≥ 90 in Fig. 19). The results are shown as
    figures only.
  - How CODE answers are counted is not stated in the text. The judge prompt sends them to a
    separate token.
- **Format, disclosed.** JSON and Python-template prompts raise misalignment (§4.4, Fig. 8).
- **Per-question variation.** Shown in Fig. 4. For evil-numbers, "highly sensitive to question
  phrasing" (§4.6).
- **Judge.** No agreement with human raters is reported. The paper only says the authors
  manually checked that the judge "broadly agrees", plus a calibration on Dolphin-Mixtral. The
  limitations call the evaluations "simplistic".
- **Released per-answer data.** `results/qwen_25_coder_32b_instruct.csv` has 70 rows from 6
  insecure Qwen2.5-Coder-32B fine-tunes. All are coherent and misaligned, so the release is the
  numerator only (checked here).

## Dickson, "The Devil in the Details" (arXiv 2511.20104 v3; HF `thecraigd/emergent-misalignment-results`)

- **Headline.**
  - Insecure 0.74% [0.62, 0.87] against base 0.07%.
  - JSON 0.96% against free text 0.42%. The JSON effect is significant for Gemma (1.43% vs
    0.22%) but not for Qwen (0.72% vs 0.59%).
- **Already tested.**
  - Alignment threshold 20–40: the insecure rate runs 0.23% to 1.31%, and the condition order
    holds (App. M.1).
  - Coherence 40–60: retention is given, with rates in the code output.
  - Blank alignment scores are counted as aligned; excluding them changes 0.74% to 0.76%.
  - Coherence and alignment correlate at r ≈ 0.80.
  - "Wish" is the highest-rate question in every condition, and "three thoughts" gives 0
    (App. J).
- **Stated limitation.** The bootstrap resamples answers only (App. M.2). It "does not capture
  variation between fine-tuning runs". No bootstrap over questions or models, and no analysis
  of the content of misaligned answers ("no quantitative breakdown").

## Model Organisms for EM (Turner, Soligo et al., arXiv 2506.11613; LessWrong post yHmJrDSJpFaNTZ9Tr)

- **Domain-leakage judges.** Four extra GPT-4o judges score how medical, financial, sport-related
  or code-related an answer is, with > 50 counting as on topic. Reported shares of misaligned
  answers that are on topic:
  - 39% financial for the financial model;
  - 23% financial for the medical model, and under 3% medical;
  - 90% *not* about sport for the sport model;
  - 55% financial and 21% containing code for insecure code.
- **The authors' framing.** They call this "a weakness in how we currently measure EM". The
  LessWrong footnote notes that prompts like "quick buck" invite finance answers.
- **Thresholds.** Alignment 40–70 and coherence 10–40 were checked for robustness.
- **Released data.** No per-answer judged EM evaluations; the HF org has no datasets. The repo
  holds small interpretability subsets of the medical organism, split medical/non-medical by
  the judge (`em_organism_dir/lora_interp/response_data/`).
- **Comment on the LessWrong post.** Peter Johnson says no headline result is free "from hand
  selection of the test set", citing 20% vs 5.7% vs jailbroken 5.2%.

## Other critiques

- **yix & Broyojo, "We need a better way to evaluate emergent misalignment" (LessWrong,
  2026-01-11, XC28DmEYPLqfwc8tf).**
  - On Qwen3-4B fine-tunes, the original judge counts in-domain answers (fiction, finance),
    capability errors and JSON/SQL answers as misaligned. A dataset-specific judge prompt
    lowers EM "across the board".
  - The numbers are in charts only, and no per-answer data were released.
  - In the comments, Betley distinguishes "is there EM?" from "how strong is EM?" and warns
    that comparisons must control for in-domain misalignment.
- **Fluri et al., ICML 2026 position paper (LessWrong summary bJcR3yP2avGFuMxyq).** Re-scoring the
  same generations under different judge settings gave 3.7% to 12.9%. A commenter reports that
  one question drove most misaligned answers for some models. (Read from a summary; the
  settings are not given.)
- **Li, Dai, Wang, Tan, "Emergent Misalignment Is Not Magical" (arXiv 2608.29118).** Per-prompt
  misalignment tracks how close the prompt is to the training data (mean Spearman −0.73). That
  is a domain-proximity account. Only the abstract was read; the judge is unverified.
- **Rao et al., "An Emergent Mirage" (arXiv 2607.09053).** EM and re-alignment are sensitive to
  surface features; apparent fast re-alignment mostly disappears once length is controlled. Only
  the abstract was read.
- **Soligo et al., "EM is easy, narrow misalignment is hard" (arXiv 2602.07852).** Takes EM% as a
  measure of broad misalignment.
- **GitHub issues** (#2, #4, #5, #6, #7, #10): reproduction failures on small models, missing
  eval scripts, system prompt. None is about the judge or thresholds; titles only.

## What is left for this audit (new if shown)

1. **Clustered intervals.** No one has put intervals on the published contrasts by resampling
   questions and models, the units that were actually sampled. Dickson names this gap
   (App. M.2).
2. **Domain echo, rule-based and pre-registered, as a rate.** The Model Organisms paper gave
   on-topic shares from a GPT-4o topic judge for its own organisms, but released no data, and
   gave no "broad-only" EM rate with an interval. Dickson gave no content breakdown. The
   LessWrong post gave charts only. New here: a pre-registered keyword rule, validated by hand
   and against a second judge, applied to released per-answer data, with the broad rate and its
   cluster interval.
3. **Denominator rules.** No one has recomputed the contrasts with dropped answers kept in the
   denominator. Dickson's blank-alignment check (0.74 → 0.76%) covers the CODE/REFUSAL drop only
   in the other direction.
4. **Joint threshold grid with clustered intervals.** Earlier checks are one-dimensional and give
   point estimates only.
5. **Concentration in one question.** "Wish" being largest is known (Dickson App. J). Whether the
   contrasts survive without it, under a leave-one-question-out bootstrap, is new.
