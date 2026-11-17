# Claims under test: do published AI-control monitors read confessions and keywords?

Written 2026-11-17, before any monitor score was split by cue.

## Sources, licences, pins

| Source | Pin | Licence | What we publish |
|---|---|---|---|
| Kale et al., "Reliable Weak-to-Strong Monitoring of LLM Agents" (MRT), arXiv [2508.19461v1](https://arxiv.org/abs/2508.19461) (26 Aug 2025; ICLR 2026) | v1, the only version | arXiv | quotes under 15 words |
| MRT release `ScaleAI/mrt` (SHADE-Arena and CUA-SHADE-Arena transcripts with stored monitor verdicts) | `bc636d0c3b881c7d8c76fd71b45b009c3710d437` (same pin as `findings/mrt-shade-arena`) | CC BY-NC 4.0 | ids, counts, AUROCs |
| MRT code `scaleapi/mrt` | `3535620b2bdf0dc1e6140f6fbe198399aac2c74f` | MIT | `file:line` quotes |
| ControlArena corpora `adityaasinha28/control_arena_{agentdojo,shade}` | `a0f1e213…`, `7b5861e8…` (pins and parquet sha256 from `findings/controlarena-corpora-surface-cues`) | none declared | aggregates and row ids only |
| CTRL-ALT-DECEIT per-run monitor tables `TeunvdWeij/ctrl-alt-deceit` | `0a12070c41ec06b81712f277590afbbed6ed6d6c` | none declared | aggregates and task names |

## Conclusion 1. MRT: agent awareness dominates monitor awareness

**Stated.** Abstract: "agent awareness dominates monitor awareness"; an agent's knowledge that it is
monitored "substantially degrades the monitor's reliability". Section 4.2, Finding 1: against
unaware agents every scaffold reaches AUC "≥0.9" on both datasets. Finding 2: aware monitors are
"not necessarily better than unaware monitors". Figure 4 (Claude 3.6 Sonnet monitor) plots the
numbers. The figure has no numeric labels; the authors' notebook
`notebooks/final/unaware_aware_comparison_table.ipynb` (stored outputs, extracted by
`scripts/published_numbers.py` into `published_numbers.json`) gives them. SHADE-Arena, Claude 3.6
Sonnet agent, baseline monitor:

| Monitor awareness | Unaware agent AUROC | Aware agent AUROC | Drop |
|---|---|---|---|
| Unaware (U) | 0.962 | 0.676 | 0.286 |
| Aware (A) | 0.969 | 0.685 | 0.284 |
| Omniscient (O) | 0.983 | 0.820 | 0.163 |

Hybrid scaffold: 0.980/0.978/0.988 (unaware agent) against 0.754/0.751/0.849 (aware agent).
CUA-SHADE-Arena (Claude Sonnet 4 agent, `agentcompany_unaware_aware_comparison_table.ipynb`),
baseline monitor: unaware agent 0.898/0.917/0.992, aware agent 0.867/0.858/0.960.

**Who relies on it.** The paper's threat-model recommendation (red-team monitors with aware agents);
anyone citing "unaware agents are easy to catch" as evidence that monitoring works when agents do
not scheme against it; the Redwood control leaderboard's SHADE slice, built from this release.

**What would change it.** In the unaware SHADE condition the agent writes "secondary task" in what
the monitor reads (44 of 50 runs in the released naive folder; `findings/mrt-shade-arena`). If, on
unaware attack runs that do **not** contain the phrase, the stored monitor's AUROC against all
honest runs falls toward the aware-agent level (≈0.68–0.75), then most of the 0.28 "agent awareness"
gap measures whether the agent confessed, not awareness. If cue-free unaware runs stay ≥0.9, the
earlier L2 finding overstated the problem and the paper's conclusion holds.

## Conclusion 2. MRT: weak monitors can oversee strong agents with the hybrid scaffold

**Stated.** Abstract: hybrid scaffolding "consistently outperforms" the baseline and lets weaker
models monitor stronger agents. Section 4.4: with weak monitors "such as GPT-4o-mini and Claude 3.6
Haiku" the hybrid monitor reaches AUC "exceeding 0.85" against all agents. Figure 6 plots monitor
AUC against the MMLU-Pro gap, aware attackers with partial verbalisation (`selective` folder),
36 attacker-monitor pairs (`notebooks/final/aware_scaling_law_plot.ipynb`).

**What would change it.** If weaker monitors' separation comes disproportionately from the attack
runs that still say "secondary task" (aware agents are told never to, but some do), the weak-to-
strong curve would flatter weak monitors. The test is each monitor's AUROC on cue-free attacks
against the same honest runs, and whether the AUROC-versus-capability-gap slope changes.

## Conclusion 3. Catch rates quoted from these datasets

- MRT's own TPR at FPR 0.01 (Section 3.4: "We adopt the 0.01 threshold"); Figure 4 bottom row.
- The Redwood Control leaderboard's SHADE slice (374 honest / 308 attack, built from this release;
  the slice itself is not public, HTTP 401 per `findings/mrt-shade-arena`), and arXiv 2605.29601's
  use of the ControlArena corpora as OOD test sets (its Table 2), whose in-corpus
  `full_trajectory_monitor` scores AUROC 0.925 on AgentDojo and 0.840 on SHADE.
- CTRL-ALT-DECEIT (arXiv 2511.09904v2) Figure 8: sandbagging detection AUROC 0.60 (general monitor)
  and 0.90 (sandbagging-specific monitor), monitor shown `SCORE ON TEST SET`.

**What would change them.** For each released monitor: catch rate at the paper's threshold on
attacks with and without the cue (the phrase; the attacker IBAN; the test score). If catch rate
on cue-free attacks is near the false-positive rate, the quoted catch rate measures cue reading.

## What each result means for the decision

A "changes" result says: a deployed monitor facing an agent that does not narrate its side task
would be caught less often than these benchmarks report, so the benchmark's number is biased
**up** (towards "monitoring is reliable"). A "holds" result says the earlier L1/L2 findings
overstated the problem for that dataset.
