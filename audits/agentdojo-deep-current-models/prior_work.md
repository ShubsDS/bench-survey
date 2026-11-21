# Prior work

In addition to the parent audit's [`prior_work.md`](../agentdojo/prior_work.md). Searched
2026-11-21 (two web searches; one preprint read by a fetch agent). "Confirmed" means I read the
passage myself; "reported" means an agent or a search summary read it and I did not.

| Source | What it already shows | Status |
|---|---|---|
| Parent audit and its fact-check | In AgentDojo's released logs (20 models, newest February 2025), the median model's secure runs are 24% never-exposed, 48% never-exposed or failed-when-asked. The authors' table script computes `injection_seen` and does not publish it. | This repo |
| Shahriyar, Iftee, Barton, Wright, "What Counts as the Same Task? Executable Contracts for Robustness Evaluation of Tool-Using Agents" (arXiv 2610.14477, 10 Oct 2026) | New runs of four local 7–8B models on 36 AgentDojo tasks (banking, workspace, slack) with the authors' own injected variants. 1,089 of 2,592 hostile trajectories expose the injection. States the principle directly: a trajectory without exposure does not test resistance, and a low attacker-success count can mean the agent failed the task, never retrieved the poisoned object, or resisted. Reports ASR after exposure as a separate rate (numbers in a supplement, not read). | Reported |
| AgentDojo issue #208 | A replay of ground truth plus attacker calls delivered the injection in 597 of 609 pairs, for the issue author's own models. | Parent audit |
| An authorization-gateway preprint (2026) | On a 20-pair AgentDojo sample, two 2026 models had a no-defence ASR of zero. | Reported, from a search summary only; not identified or read |
| Anthropic, prompt-injection defences page | Browser-agent ASR for Sonnet 4.5 and Haiku 4.5 under an adaptive attacker. A different benchmark. | Reported |
| Nasr, Carlini et al., "The Attacker Moves Second" (arXiv 2510.09023) | AgentDojo's fixed attack strings understate risk; adaptive attacks reach above 90%. | Parent audit |

## What is and is not new here

- **Not new:** the principle that a run without exposure does not test resistance (arXiv
  2610.14477 says it in print, for small local models). That fixed injection strings are weak
  against current models.
- **Not found:** any published AgentDojo `important_instructions` result, or any exposure rate, for
  a Claude model released after February 2025. The upstream repository's logs stop at Claude 3.7
  Sonnet.
- **New here:** exposure, ASR and the decomposition of secure runs for `claude-haiku-5-5` and
  `claude-sonnet-5-5` on AgentDojo v1.1.2, with the 20 older models scored on the same sampled
  cases.
- **Consequence for the essay.** The parent finding should cite arXiv 2610.14477 as stating the
  principle first. What the parent finding adds is the size of the effect in the benchmark's own
  published logs for 20 models.
