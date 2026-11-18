# LAB-Bench: prior work

Searched on 2026-11-17:
- the paper (v1 and v3), its limitations, methods and supplement;
- the issues and pull requests of `Future-House/LAB-Bench` (all 16, through the unauthenticated GitHub API);
- the Inspect Evals implementation and its changelog;
- web search for LessWrong, the Alignment Forum, the EA Forum and arXiv;
- the LABBench2 paper;
- the system cards that report LAB-Bench (`claims.md`).

## What is already known

| Source | What it shows | Relation to this audit |
|---|---|---|
| The paper, §1 (learning 2), §2.4, §3.1 | Models reach "above-random precision by eliminating unlikely distractors and then guessing". In open-answer form, Claude 3.5 Sonnet and GPT-4o score 0.20 on 10 CloningScenarios items, 0.30 on 10 FigQA items, and 0.30 / 0.20 on 20 ProtocolQA items (Table 5) | Known in general terms. The paper never names a distractor-form feature and never measures a content-blind baseline |
| The paper, §3.2 | The CloningScenarios human baseline "may be unreasonably low": items take 10–60 minutes and annotators "often did not find it worth their time" | Known. This audit adds the size of the effect of the "unsure" rule on each human number (App. E.4 arithmetic) |
| The paper, §3.3 | "The comparison to humans is not entirely equitable": humans had tools and the internet, and models had none | Known. Justen 2025 §3 repeats it |
| The paper, §3.5 and Table 1 | Humans covered only part of the full set: TableQA 82%, DbQA 35%, SeqQA 64% | Known. The number of evaluators is not stated |
| The paper, App. E.3–E.4 | An "unsure" answer paid at least the expected value of guessing. Human accuracy counts only correct answers that were not flagged unsure | Stated, but no source draws the consequence for model-versus-human comparisons. This audit draws it |
| The paper, App. B.1 | Public and private mean accuracy differ by "within five percent absolute" | Known. No per-subset numbers are given |
| [Issue #18](https://github.com/Future-House/LAB-Bench/issues/18) (2026-11-15, open) | "Longest option" scores 0.332 on ProtocolQA (chance 0.232). By family: CloningScenarios 0.197, LitQA2 0.257, SuppQA 0.222, FigQA 0.267, TableQA 0.226 | **Known.** This audit's longest-option numbers reproduce these exactly (`results/surface.json`), so they are not claimed as new. The issue covers only length, and not SeqQA or DbQA |
| [Issue #12](https://github.com/Future-House/LAB-Bench/issues/12) | Trailing whitespace in some options | Minor. Length rules are affected by at most a character |
| App. C.7 (SeqQA construction) | The paper documents that distractors are derived from the key: "shifted" primers, "wrong enzyme" pairs with the key's primer bodies, GC% "one less or … one greater than the answer, or … the ideal answer divided by two" | The construction is disclosed. No source tests or reports that a rule reading only the options recovers the key from it |
| Inspect Evals `lab_bench` README | Inspect reports only averaged SeqQA and DbQA, not the paper's per-subtask numbers. The choice shuffle was seeded on 2026-10-09 (changelog 3-B) | Background |
| [LABBench2](https://arxiv.org/abs/2604.09554), §1, §2 (same group, 2026) | LAB-Bench "made concessions to make grading easier" with multiple choice. There are "multiple examples of near saturation or superhuman performance". Scores drop by 26–46% moving to open-response LABBench2 | Known in general. LABBench2 replaces multiple choice and so does not measure the v1 answer surface |
| Justen 2025, [arXiv 2505.06108](https://arxiv.org/abs/2505.06108), §3 | Models "match or exceed" the CloningScenarios expert baseline (61% vs 60%). Humans had tools, so the comparison "understates model capabilities" | A claim under test (C4), and the opposite reading of the tool asymmetry |
| OpenAI system cards (o1, o3, GPT-5) | They use "ProtocolQA Open-Ended", with 19 PhD scientists as a new baseline and no options | A different format and baseline. Not tested here; noted as the open-answer counterpart |

No LessWrong or Alignment Forum post on LAB-Bench was found. The EA Forum repost of Justen 2025
argues for saturation, not against validity.

## What is new here

- That the key in 6 of the 15 SeqQA subtasks (240 of 600 public SeqQA items) is recoverable with
  certainty from the options alone. Five subtasks fall to a similarity "centroid" rule. The GC
  percentage subtask falls to a "middle value" rule.
- That DbQA `variant_multi_sequence` falls to the same centroid rule (80 of 80). Three DbQA
  subtasks fall partly to "shortest option" (0.41–0.50 against 0.25 chance). One subtask's key
  can be read off distractor reuse across items (0.875).
- The stratum-level comparison of published model-minus-human gaps on SeqQA subtasks with and
  without the shortcut, with a placebo over subtask splits.
- The Haiku interventions:
  - options-only and figure-free baselines;
  - removing and moving the refusal option;
  - minimal edits that move the "centroid" onto a distractor.
- The arithmetic of the human "unsure" rule against the "surpasses experts" margins in the
  system cards, and figure- and scenario-clustered intervals for those margins.
