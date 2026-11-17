# SAD: prior work on its shortcuts

Searched 2026-11-17: the paper (v1, full text), the repo's issues and pull requests (web pages,
not the API), LessWrong and the Alignment Forum, arXiv and general web search for later
situational-awareness and evaluation-awareness work that uses or critiques SAD. Sources marked
"read" were opened and checked; "reported" means a search summary only.

## The paper itself (read)

- **Answer direction is by design, not discussed as a cue.** Appendix C.3.2, Table 4 (p.24-25):
  humans answering as themselves score 0.31 on FACTS-HUMAN-DEFAULTS and 0.38 on INFLUENCE, "because
  many ... questions are constructed such that one answer is the LLM-applicable one and the other
  is the human-applicable one." The paper does not test whether the LLM-applicable answer can be
  recognised from the choices alone, and runs no content-blind baseline. Random chance is the only
  floor (Table 1, Appendix C.3.1).
- **Stages biases are noted as model biases, not dataset cues.** Appendix H.3.6 (p.71-73): many
  models "have a bias towards guessing that they are in testing or deployment regardless of what
  the true answer is." There is no analysis of the fact that each stages label is drawn from its own
  source datasets (§2.2), nor a surface-feature baseline.
- **Limitations (§5)** cover task artificiality, few base/chat pairs, saturation and leakage. No
  mention of duplicates, answer-surface cues or stale per-model keys.
- facts_which_llm keys are per model and must be added by hand for a new model (Appendix B.3, E.5);
  the README suggests copying a same-family model's answers.

## Repo issues and pull requests (reported by a search agent; issue #8 and PR #9 titles checked)

- Issue #8 "Duplicated ids, different questions" (Dec 2025): influence ids shared by different
  questions. Same observation as the earlier finding's influence-id note; not the
  facts_human_defaults double scoring.
- PR #9 "Sad version2" (2026, open): adds newer models and per-class oversight scoring. No fix to
  answer cues, duplicates or stale keys.
- Nothing on content-blind baselines, denial bias or surface cues.

## Later work

- **Rajakumar, "Revising Stages-Oversight Reveals Greater Situational Awareness in LLMs"**
  ([LessWrong, 2025-03-12](https://www.lesswrong.com/posts/5naJwQnbb5bwPCCFz/revising-stages-oversight), read).
  Points out that in stages_oversight "yes" always means "evaluation", a possible answer-bias
  confound, and rebuilds the task with randomised label order and procedural variants. Notes the
  hardest deployment prompts look evaluation-like (structured, technical). It re-scores models on
  new items; it does not stratify the original items, measure a surface classifier, or touch
  facts or influence. Closest prior critique; it argues SAD *understates* awareness.
- **Nguyen et al., "Probing and Steering Evaluation Awareness of Language Models"**
  ([arXiv 2507.01786](https://arxiv.org/abs/2507.01786), Jul 2025, read). Trains probes on
  stages_oversight and reports surface baselines of prompt length (AUROC 0.584) and special
  character count (0.598), concluding the probe is not learning spurious features. Single features
  only; the earlier finding's seven-feature classifier reaches 0.662 accuracy on the same task.
- **Nayan et al., "Evaluation Awareness Is Not One Capability"**
  ([arXiv 2606.23583](https://arxiv.org/abs/2606.23583), Jun 2026, read). Uses stages_oversight;
  the mildest neutral paraphrase "significantly degrades 13/36 models" (mean change −0.051) and
  moves models in opposite directions. Shows sensitivity to surface form on this task; no
  stratification by a shortcut and no re-ranking.
- **Needham et al., "Large Language Models Often Know When They Are Being Evaluated"**
  ([arXiv 2505.23836](https://arxiv.org/abs/2505.23836), May 2025, reported). Mentions SAD-stages
  as limited in source diversity; does not test SAD for cues.
- Further 2025-2026 probe papers use stages_oversight as labels without critique (reported).
- No model card found reporting SAD scores (reported; not exhaustive).

## What is already known versus new here

| Point | Known before | Source |
|---|---|---|
| FHD and INF keys are the "non-human" answer | Yes, by design | Paper Table 4 |
| A choices-only classifier scores 0.825 (FHD) and 0.720 (INF), above 17 of 21 models | Measured, L2 | Earlier finding in this repo |
| Stages labels predictable from surface form; SO "yes" always means evaluation | Partly: yes-bias (Rajakumar), weak single-feature baselines (Nguyen), paraphrase sensitivity (Nayan); 7-feature classifier above all models (earlier finding) | as listed |
| facts_which_llm keys stop at o1; dated rows | Measured, L1 | Earlier finding |
| Whether released models' scores, ranking, capability trend, chat>base or SP effects depend on these shortcuts | **Not found anywhere** | This audit |

New here: the per-item stratification of the released model outputs (L3), the interaction of
shortcut use with capability, and the Haiku choices-only and order-swap intervention (L4).
