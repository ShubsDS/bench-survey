# Alignment faking: claims under test

Status: written 2026-11-17, before any stratified result was computed. The only model-output
numbers looked at before writing this file are the per-variant headline rates (free and paid
compliance, alignment-faking label rate), computed to check that the release reproduces the paper.

## Sources and pins

| Source | What it is | Licence | Pin |
|---|---|---|---|
| Greenblatt et al., "Alignment faking in large language models", arXiv 2412.14093 | The paper | arXiv | v2 (2024-12-20) |
| `github.com/redwoodresearch/alignment_faking_public` | Prompts, classifier prompts, scoring code | MIT | `8d98bb786893ac44d02f41eb222eabf302c0aab9` |
| Google Drive folder linked from that README: `json_outputs.zip` | Per-transcript records behind the examples website: one JSON or HTML-wrapped JSON per (setting, prompt variant, tier, query), with the paper's classifier labels and the helpful-only preference-model score | none stated (README invites analysis) | sha256 `6e7c3f99…139d7`, 944,927,003 bytes, 222,017 files |
| Same folder: `variation_info/*.json` | Variant names and descriptions | none stated | downloaded 2026-11-17 |
| Hughes, Sheshadri et al., "Alignment Faking Revisited: Improved Classifiers and Open Source Extensions" (Anthropic Alignment Science blog and LessWrong, April 2025) | Improved classifier, 106 human labels, open-weight runs | — | — |
| `github.com/safety-research/open-source-alignment-faking` | Hughes et al. code | MIT | `dc21773fd6b69ae8be3503d51d7412e88aa2f39d` |
| HF `jplhughes2/classify_alignment_faking_human_labels` | 106 human-labelled scratchpads | none stated | `3c087f7e385129b417a4e8ef7c0dd58be30b4d65`; parquet sha256 `3a203f80…441d` |
| Sheshadri et al., "Why Do Some Language Models Fake Alignment While Others Don't?", arXiv 2506.18032 | 25-model comparison | arXiv | v1 |
| `github.com/safety-research/alignment-faking-extensions` | Code and notebooks for the follow-ups, including the classifier-development CSVs with per-item classifier decisions on the 106 labels | none in repo | `6b3e35cd5842970531148b63dac8e92811ed8b41` |

Not used: `Anthropic/alignment-faking-rl` (encrypted; not opened), gated datasets.

## Traits from the methodology, scored

| # | Trait | Present? | Note |
|---|---|---|---|
| 1 | Label from a process | Partly | Compliance is a preference-model score with a fixed cut-off (`info_about_trace_new.py:765`), not a judgment of the answer |
| 2 | Items kept by model behaviour | Unknown | 352 of the dataset's queries are released for the default prompt, 172 for most variants, 86 for paraphrases; the selection rule is not stated in the release |
| 3 | Headline is a difference of two rates | **Yes** | The compliance gap; bounded by the paid-tier base rate and the free-tier ceiling |
| 4 | Few independent units | **Yes** | One sample per query per tier; 172–352 queries; 40+ prompt variants share the same queries |
| 5 | Two free-text options | No | |
| 6 | LLM judge, subjective criterion | **Yes** | "Alignment-faking reasoning" (`effective_scheme`) by a Claude classifier; Hughes et al. found AUROC 0.62 against people |
| 7 | Scorer assumes the model was told something | Partly | The tier cue is a tag in the user turn; the prompt also says paid users' data are private |
| 8 | Best number from the easiest condition | Possible | Many prompt variants; the default prompt was chosen by the authors |
| 9 | One outcome bucket holds unlike cases | **Likely** | "Complied" = PM score ≥ −0.7; the release also has a separate `follows_instructions` and compromise labels |
| 10 | Aggregation over units of varying size | Minor | A keyword-heavy long scratchpad has more chances to be labelled |
| 11 | Unbalanced key | No | |
| 12 | Little outside scrutiny | No | Classifier and prompt sensitivity have had scrutiny; the gap statistic and unit of analysis much less |

## C1. Claude 3 Opus, prompted helpful-only setting: an 11% compliance gap explained by alignment-faking reasoning

- **Statement.** Table 1 (default prompt): alignment-faking reasoning 11.9 ± 1.7%, refusals 85.8% (training)
  vs 97.2% (unmonitored), compliance gap 11.3 ± 2.1 points. The repo README calls the
  alignment-faking reasoning the explanation of the gap: where a free-tier user gets a harmful answer,
  the scratchpad almost always shows alignment-faking reasoning. Section 1 gives a range over setups
  of 7–24% reasoning and 11–26% gap.
- **Who relies on it.** It is the founding demonstration of alignment faking. System cards and safety
  cases cite it, follow-ups reuse its setting, and it is the reference point for "does model X fake
  alignment".
- **What would change it.**
  - (a) The gap's interval, resampled by query, includes 0, or the gap sits in a handful of queries
    that also carry it under other prompts, with a random-removal control that does not.
  - (b) A large share of free-tier "complied" outcomes are routes other than full compliance
    (watered-down, refusal-in-output, missing output), and the gap on full compliance only is
    materially smaller.
  - (c) A material compliance gap remains among samples *without* the alignment-faking label (the
    "explains" reading weakens), checked against what the paper already says (Section 3.3.4,
    Appendix F).

## C2. "Only a few models show a compliance gap"

- **Statement.**
  - Greenblatt §1 and App. G.4: Claude 3 Opus and Claude 3.5 Sonnet show alignment faking; Claude 3
    Sonnet, Claude 3 Haiku and Claude 3.5 Haiku generally do not. GPT-4 Turbo and GPT-4o runs are in
    the release.
  - Sheshadri et al. abstract and §3.2: of 25 models, only 5 show a compliance gap, defined as free
    minus paid compliance above 1%, at n = 200 per tier ("1σ uncertainty ≤ 3.6%").
- **Who relies on it.** "Alignment faking is rare and scale- or model-specific." It is used to argue
  that most deployed models do not fake alignment and to choose which models to study.
- **What would change it.**
  - (a) Models classed as "no gap" had too little room to show one: base compliance near 0 or 1, so
    that the gap they could have shown, or the gap the design could detect at 80% power, is near
    or above the gaps of the "gap" models.
  - (b) On the odds-ratio scale with intervals, the classification of some models changes.
  - (c) The 1% threshold is below the stated noise, so the count of 5 is unstable.
- **Data limits.** Sheshadri et al. release code but no per-sample outputs, and the paper gives
  per-model rates only in figures. This claim is tested on the Greenblatt release's other-model runs
  (per sample), plus an analytic power check of the published design. Any per-model value read off a
  figure is marked as read by eye.

## C3. The alignment-faking-reasoning rate measures a reasoning pattern

- **Statement.** The alignment-faking rate (Greenblatt's classifier; Hughes et al.'s improved
  classifier, AUROC 0.92 vs 0.62 on 106 human labels) counts scratchpads that reason
  strategically about preserving values through training.
- **Who relies on it.** Every follow-up that reports an alignment-faking rate across models.
- **What would change it.** A content-blind keyword rule (counts of "train", "RLHF", "modify",
  "values"…), fit on one half, matches the released classifier labels on the other half about as
  well as the classifier matches people. Or classifier errors on the 106 labels track model or
  length.
- **Already known; not re-derived.** The original classifier's poor agreement with people (Hughes et
  al.). The earlier finding in this repo that no surface baseline separates the 106 human labels
  (length AUROC 0.509, `findings/alignment-faking-uncanaried-copies`).
