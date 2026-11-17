# AgentDojo: prior work

Searched 2026-11-17: the paper (arXiv 2406.13352v3, HTML), the repository's issues and pull
requests (web pages, all four pages of issues), the docs changelog, and papers that use or
criticise AgentDojo. LessWrong and the Alignment Forum turned up nothing specific. Issue
summaries come from reading the issue pages, not from re-running anyone's code.

## The paper itself

| Item | What it already shows | Where |
|---|---|---|
| Capability and ASR | "more capable models tend to be easier to attack, a form of inverse scaling law". The paper already gives the capability explanation: low-utility models "often fail at correctly executing the attacker's goal, even when the prompt injection succeeds". It gives no correlation or test | Section 4.1, Figure 6(a) |
| Exposure | Not analysed. Injections are placed only in tool outputs that the ground-truth solution reads (`attacks/base_attacks.py:48-69`). No ASR conditional on the agent receiving the injection. The authors' own table script computes `injection_seen` (`util_scripts/create_results_table.py:47-52`) but does not report it | code |
| Name ablation | GPT-4o: wrong user name 23.2%, wrong model name 23.7%, against a 45.8% no-names baseline | Table 2 |
| Injection position | Injections at the end of tool outputs are most effective (figure only) | Appendix D, Fig. 21 |
| Tool filter limits | Filtering works when the user task needs only read access and the attacker needs write access. It fails when the user task needs the attacker's tool | Section 4.3, "Strengths and limitations of tool isolation mechanisms" |
| Intervals | 95% intervals from `statsmodels proportion_confint` on the 629 cases, treated as independent rows | Tables 3 and 5, checklist |
| Per-task breakdown | ASR by injection task and suite. Slack is easiest (92%), and one travel injection task is at 0% | Figure 7 |
| Own numbers | Table 3 gives Command-R+ ASR 0.95%, Llama 3 70B 20.03%, Gemini 1.5 Pro 25.60% and GPT-3.5 8.43%. The public results table at the pin gives 4.45%, 25.60%, 28.62% and 10.33% for the same runs. Table 5 gives undefended GPT-4o 57.69% against Table 3's 47.69% | Tables 3, 5 |

## Repository issues (github.com/ethz-spylab/agentdojo/issues)

- **#154**: an API error (context length, server error) sets `security = True`, so errored runs count
  as attack successes. PR #186 proposes reporting errors separately. *Mechanism known.* Not known:
  that the public results table counts them while the paper's Table 3 does not, and by how much
  this moves each model.
- **#240 and #181**: banking injection tasks 0, 1 and 3 test `service or "" in subject`, which is
  always true, so any transfer to the attacker IBAN counts. A rescoring found little change.
- **#168 and #189**: Slack injection task 5 scores proposed calls rather than executed ones
  (`security_from_traces`).
- **#245 and #135**: workspace exfiltration missed by the check (false negatives; one or two
  cases each).
- **#47** (fixed in PR #52): five workspace user tasks never exposed the injection, because
  models searched for "Hawaii" rather than "vacation plans". *An exposure problem, raised for
  specific tasks.*
- **#208**: a replay of ground truth plus attacker calls delivered the injection in 597 of 609
  pairs. Undefended ASR goes from 95.6% to 97.5% when restricted to delivered pairs, for the
  issue author's own models. *Closest prior to our exposure analysis, but for other models and
  not over the published runs.*
- **#213**: workspace injection tasks 6–13 (v1.2) have empty ground truth.
- **#161, #159, #138, #139, #162, #188, #218, #244**: utility-check and ground-truth bugs in
  individual user tasks.

## Papers

- **The Attacker Moves Second** (Nasr, Carlini et al., arXiv 2510.09023): AgentDojo's static attacks
  understate risk. Adaptive attacks reach more than 90% against defences reported near 1–2%
  (Meta-SecAlign 2% to 96%; spotlighting and sandwiching to more than 95%; MELON 76–95%). It
  argues that static evaluations mislead. *Different axis (attack strength); complementary.*
- **Bhagwatkar et al., "Indirect Prompt Injections: Are Firewalls All You Need, or Stronger
  Benchmarks?"** (arXiv 2510.05244): some utility drops are artefacts of injections that overwrite
  task data, and some utility checks are too rigid. Fixing them raised GPT-4o utility under attack
  from 60.87% to 72.19%, with ASR nearly unchanged.
- **CaMeL** (arXiv 2503.18813): names "AgentDojo bug" as a failure category, and says one remaining
  travel "success" is not due to an injection.
- **Costa et al., information-flow control** (arXiv 2505.23643, from search snippets; PDF not read):
  Slack injection task 5 counts blocked calls, and some injection tasks are policy-allowed.
- **AgentDyn** (arXiv 2602.03117): only 6 of 97 user tasks need dynamic planning, and system-level
  defences saturate AgentDojo.
- **AgentArmor, AutoDojo**: the success checks are too strict, and adaptive attacks beat the fixed
  strings.

## What is new in this audit

1. Exposure-conditioned and ability-conditioned ASR for all 20 published models and 4 defences,
   with crossed task bootstrap intervals, tested against the ranking, the capability trend and the
   defence gains (prior work: #208 on other models; the paper's sentence on weak models).
2. The paper's Table 3 and the public results table disagree because of error coding.
   Quantified per model, with its rank effect.
3. Attacker action read from the agent's own tool calls on all 15,096 published cases: how often a
   "success" lacks the action and how often a "secure" case contains it, by injection task.
   Also a placebo check on no-attack runs (banking user_task_15 uses the attacker's IBAN).
4. Two-way task bootstrap intervals against the paper's row-level intervals, and how many model
   pairs stay separated.
5. 207 of Claude 3 Opus's 629 attack traces have empty message lists in the release.
