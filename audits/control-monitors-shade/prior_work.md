# Prior work

Searched 2026-11-17: the MRT paper (arXiv 2508.19461v1, the only version), its code repo at the pin
(no issue tracker read: the GitHub API is rationed; nothing in the repo's README or notebooks
discusses verbalisation as a confound), web search for critiques of MRT and SHADE-Arena on
LessWrong, the Alignment Forum and arXiv, and this project's own findings.

## This project (the starting point; all L1/L2)

| Finding | What it showed | What it left open |
|---|---|---|
| [`findings/mrt-shade-arena`](../../findings/mrt-shade-arena/README.md) | Unaware SHADE agents (Claude 3.6 Sonnet, `naive` folder) write "secondary task" in the monitor's input in 44/50 runs; keyword AUROC 0.940 vs stored monitor 0.961. **On the 6 cue-free unaware runs the stored monitor scores 0.754**, close to its aware-agent 0.708. CUA: keyword does not explain the monitor for `naive_v1` (0.903 on 37 cue-free runs). Release has 5 of 17 SHADE tasks. | n=6, no task clustering, one monitor scaffold/awareness, no test of the awareness *comparison*, no intervention. Our L3 is a direct extension of that one row. |
| [`findings/shade-arena-scorers-and-tool-names`](../../findings/shade-arena-scorers-and-tool-names/README.md) | `add_*_autodelete_rule` tool name gives 0.988 on spam_filter_update; the default monitor scores 0.526 there, so it does **not** use that cue. Tool arguments are not shown to the SHADE monitor (`logging_utils.py:618`). | Nothing on confession phrases. |
| [`findings/controlarena-corpora-surface-cues`](../../findings/controlarena-corpora-surface-cues/README.md) | AgentDojo: attacker IBAN in the agent's own tool call in 658/750 positives; IBAN-presence AUROC 0.939 vs in-corpus `full_trajectory_monitor` 0.925. Monitor input is action-only. | Whether that monitor's suspicion tracks the IBAN. |
| [`findings/ctrl-alt-deceit-score-visible`](../../findings/ctrl-alt-deceit-score-visible/README.md) | The `SCORE ON TEST SET` field shown to the monitor predicts sandbagging (leaderboard percentile 0.716 vs general monitor 0.603). Among Regular runs suspicion falls as score rises (Spearman −0.32 general, −0.33 specific). | Whether the 0.90 specific monitor's verdicts survive a hidden score; all released sandbagging scores were made with the score shown. |

## External

- **MRT itself** (Section 4.1) calls its unaware-agent elicitation "only a proxy" for unaware agents
  and gives the prompt line asking the agent to plan the side task in `<thinking>` tags. It does
  not report that the agent writes the side task outside those tags, and does not split results by
  verbalisation. No limitations section discusses it.
- **SHADE-Arena** (Kutasov et al., [arXiv 2506.15740](https://arxiv.org/abs/2506.15740); Anthropic
  [write-up](https://www.anthropic.com/research/shade-arena-sabotage-monitoring)): side-task success
  depends on a hidden scratchpad; models often mention the side task in visible reasoning and the
  monitor picks this up. So "monitors catch agents that verbalise" is **known**. What is not
  known is how much of MRT's *awareness* effect, and of the quoted catch rates, is that mechanism.
- **CoT Red-Handed** (Arnav et al., [arXiv 2505.23575](https://arxiv.org/abs/2505.23575), NeurIPS
  2025): CoT monitors catch subtle sabotage that action-only monitors miss, but misleading
  rationalisations in the CoT can fool them. Known: what the monitor reads in the agent's prose
  matters, in both directions. Different benchmark (BigCodeBench side tasks).
- **Baker et al. 2025** ("Monitoring reasoning models for misbehavior", OpenAI) and **Emmons et al.
  2025** ("When chain of thought is necessary…"): CoT monitoring works mainly because models state
  their intent; under pressure it can be obfuscated. Known in general; not measured on MRT.
- **TraceMRT** (Tsinghua 2026, reported [here](https://cryptobriefing.com/tsinghua-tracemrt-ai-monitor-evasion-study/))
  and arXiv [2603.16928](https://arxiv.org/abs/2603.16928): red-teaming methods that evade
  SHADE-Arena CoT monitors; not about this confound. Not read beyond abstracts.
- No LessWrong or Alignment Forum critique of MRT's awareness result was found.

## What is new here

1. L3 on released per-run monitor scores: cue-stratified AUROC and TPR@1%FPR for every monitor
   scaffold (baseline, sequential, hierarchical, hybrid) and monitor-awareness level (U, A, O), with
   task-cluster bootstrap intervals, and the awareness comparison recomputed on cue-free runs.
   The earlier n=6 row is one cell of this.
2. The same for CUA-SHADE-Arena, where the monitor input is stored, so cue presence is read off
   the monitor's actual input rather than a reconstruction.
3. The weak-to-strong monitor sweep stratified by cue (where data could be fetched).
4. An L4 minimal-pair redaction with Haiku as monitor, using the paper's prompt.
5. L3 checks of the in-corpus ControlArena AgentDojo monitor against the IBAN and of CTRL-ALT-
   DECEIT's monitors against the shown score, within class.
