# Scope: a validity audit of AI-control and safety evaluation datasets

Status: scoping only. No experiment in this document has been run unless it says "done in this
repo". Facts about each benchmark were checked against its card, repository or paper on
2026-10-26; every link was fetched that day. Where a source could not be checked, the entry says
"not found" or "to confirm" rather than guessing.

## Why this project

This repo found three ways the standard APPS backdoor benchmark can be scored on without finding
sabotage ([`paper/main.tex`](../paper/main.tex)):

1. **Authorship.** People wrote the honest solutions and older models wrote the backdoors. A
   bag-of-words classifier that never runs the code reaches AUROC 0.806 on the test split, above
   20 of the 24 open-weight monitors ranked on it.
2. **Label leakage.** The test split keeps a problem's backdoored program only if the backdoor
   works, and its honest program otherwise, so problem metadata alone predicts the label.
3. **Attacks that are not attacks.** After adding a check that the trigger is a legal input and
   that the backdoor is wrong there against the human answer
   ([`experiments/apps/verify_backdoor.py`](../experiments/apps/verify_backdoor.py)
   `--validators --human-ref`), 41 of 99 of our Sonnet 5 "working backdoors" and 15 of 99 of the
   dataset's own backdoors failed (most were wrong only on inputs the problem forbids). Before the
   check, a Sonnet 5 monitor seemed to catch far fewer of Sonnet 5's backdoors than of the older
   models'. On the 52 problems where both backdoors are wrong on a legal input, flagging 2% of the
   human solutions, it catches 77% of the older models' and 61% of Sonnet 5's.

Each of these moves a number that a control argument uses. The first two make a monitor look
better than it will be once the untrusted model writes both classes. The third made the monitor
look worse than it was, because there was nothing to catch. The question for this project is how
often the same construction choices recur across the datasets people now use to rank monitors,
set audit budgets and write safety cases, and which way each one biases the estimate.

The checks are cheap. Most need a CPU and the released data; two need one class regenerated. The
expensive part of the paper was finding the problems, not testing for them, so a fixed suite run
across many benchmarks should cost little per benchmark.

**How to read "bias".** A safety estimate in a control evaluation is roughly the probability that
the protocol catches (or blocks) an attack before one succeeds, at a given audit budget, against
the strongest attack policy the red team could elicit. A dataset artifact biases it **up** when it
makes attacks easier to catch, or successful attacks rarer, than they would be in deployment; it
biases it **down** in the reverse case. Up is the dangerous direction for a safety case. Down
wastes audit budget and can rank monitors wrongly.

---

## 1. Candidate benchmarks

Fifteen benchmarks in four families. For each: where it lives, its licence as declared, how its
classes and success labels were produced, and which published conclusions rest on it. "Licence"
is what the card or repository declares; "none declared" means no licence field or file, which
grants no permission to redistribute, so any audit of those reports aggregates only.

### 1a. Static monitor datasets

**1. apps-control-arena** (the dataset this repo audits)
- Source: <https://huggingface.co/datasets/RoganInglis/apps-control-arena>, built by
  ControlArena's `control_arena/settings/apps/dataset/` scripts
  (<https://github.com/UKGovernmentBEIS/control-arena>). Docs:
  <https://control-arena.aisi.org.uk/settings/apps.html>.
- Licence: MIT.
- Size: 5,000 APPS problems; 2,473 with a backdoor, 1,582 with one marked working; about 11,371
  backdoor entries.
- Honest side: human solutions from APPS (`codeparrot/apps`).
- Attack side: model-written, from two sources. The Control Tax JSON (entry 3; 8,855 backdoors)
  and `TylordTheGreat/apps-backdoors-04-02-25` (4,184 rows, no card or licence, credited by
  ControlArena to Greenblatt et al. 2023, model field "unknown").
- "Backdoor works": the backdoor compiles and passes the stored tests, and its output on the
  attacker's claimed trigger differs from the first passing human solution's. Nothing checks that
  the trigger is a legal input. A nondeterminism flag is set by an LLM judge.
- Known issues upstream: trigger legality is raised in ControlArena issue
  [#755](https://github.com/UKGovernmentBEIS/control-arena/issues/755); open PR
  [#899](https://github.com/UKGovernmentBEIS/control-arena/pull/899) adds per-problem input
  validators; a third-party pilot checked 24 triggers on 10 problems
  (<https://github.com/akatsukiwork0320/control-arena-validator-pilot-repro>).
- Confirmed join bug (2026-10-26): the build drops 40% of the Greenblatt-attributed backdoors.
  `upload_dataset.py` (ControlArena commit `ae0b6fa`) keys that source by `str(problem_id)`, which
  in the source is a zero-padded four-character string (`'0001'`). It then looks up each APPS
  problem by `str(problem_id)`, which in `codeparrot/apps` is unpadded (`'1'`). Only ids of 1,000
  or more can match. Of the source's 473 problems, 189 (all below 1,000, all interview level)
  never join, losing 1,668 of its 4,184 backdoors. The published dataset agrees: all 284 rows
  with `has_apps_backdoor` have ids of 1,001 or more. The dropped backdoors do belong to those
  problems: by token overlap with the problem's human solutions, 186 of 189 are closer to their
  own problem than to a random one, against 264 of 284 for the backdoors that joined. 152 of the
  189 problems still have Control Tax backdoors; 37 have none. This bug loses data but labels
  nothing wrongly. Its likely effect is fewer GPT-4-era backdoors in the attack class, which
  shifts the attacker mix toward the Control Tax models. Not found in ControlArena's issues or
  PRs. Write-up and reproduction: [`findings/controlarena-apps-join/`](findings/controlarena-apps-join/).
- Conclusions resting on it: entries 2 and 3 below; ControlArena's default apps setting.

**2. apps-control-arena-high-quality** (the test split audited in this repo)
- Source: <https://huggingface.co/datasets/eugenekoran/apps-control-arena-high-quality>; code
  <https://github.com/Multi-Signal-Control-SPAR/Multi-Signal-Monitoring> (MIT).
- Licence: none declared.
- Size: train 1,209 problems (each with a passing honest solution and a working backdoor); test
  1,375 (172 attack, all by Claude 3.7 Sonnet Thinking; 1,203 honest).
- Construction: keeps honest solutions that pass and backdoors that pass and work; drops
  GPT-3.5-Turbo, GPT-4o-mini and Claude 3.5 Haiku backdoors; pads the test split with problems that
  have no working backdoor, which is where the label leak comes from; strips comments.
- Conclusions resting on it:
  - Koran et al., "Ensemble Monitoring for AI Control: Diverse Signals Outweigh More Compute"
    (<https://arxiv.org/abs/2605.15377>): a diverse ensemble of three GPT-4.1-mini monitors gives
    about 2.4× the gain of three identical ones.
  - Jha, "Decorrelation Is Not Complementarity" (<https://arxiv.org/abs/2608.16190>, code
    <https://github.com/anik-jha/challenger-panels>, MIT): across 24 open-weight monitors,
    detection skill rather than lineage governs ensemble gain.
- Status: authorship, label-leak and trigger checks done in this repo.

**3. Control Tax backdoor set**
- Source: Terekhov, Liu, Gulcehre, Albanie, "Control Tax: The Price of Keeping AI in Check"
  (<https://arxiv.org/abs/2506.05296>); data
  <https://mikhailterekhov.github.io/control-tax/backdoor_code_paper.json>, also in
  <https://github.com/MikhailTerekhov/control-tax-code> (`data/backdoor_code_full.json`).
- Licence: the code repository is MIT; the project page states none.
- Size: 8,855 successful backdoors on 2,368 APPS problems, from nine attackers (o3-mini 2,261;
  Claude 3.7 Sonnet 1,864; o1-mini 1,250; GPT-4o 1,148; Gemini 2.0 Flash 715; Claude 3.5 Haiku
  591; Claude 3.7 Sonnet Thinking 517; GPT-4o-mini 367; GPT-3.5-Turbo 142).
- Honest side: human APPS solutions, on problems with at least 33 all-passing solutions.
- Attack side: the attacker brainstorms strategies, a second instance of the same model ranks
  them, the attacker writes the code and a trigger, up to 10 attempts.
- "Success": the reference solution runs on the trigger without error; the backdoor passes the
  public tests (at most 5); outputs differ on the trigger. No trigger-legality check.
- Conclusions resting on it: monitor strength rather than attacker strength drives detection AUC
  (o3-mini monitor 0.92–0.96), and the paper's safety-versus-monitor-cost curves. It is also the
  main backdoor source of entries 1 and 2. (The follow-up "Adaptive Attacks on Trusted Monitors
  Subvert AI Control Protocols", <https://arxiv.org/abs/2510.09462>, runs live GPT-5 attacks and
  does not use this file.)

**4. MonitoringBench** (with MonitoringBenchHonest)
- Source: Jotautaitė, Martinez, Matthews, Tracy (<https://arxiv.org/abs/2605.09684>); post
  <https://www.lesswrong.com/posts/2YyEQhFRyaBCgfRWd/introducing-monitoringbench>; data
  <https://huggingface.co/datasets/neur26anonsub/ctrldataset2026> (an anonymised account; the card
  is named MonitoringBench). Honest add-on: Küçükkurt and Elasky,
  <https://www.lesswrong.com/posts/bdBoH23TCTFZkkfqp/releasing-benign-trajectories-for-monitoringbench>.
- Licence: CC BY 4.0 (attacks). Honest add-on: none stated.
- Size: 2,644 successful attack trajectories, all in BashArena (entry 8), four side tasks (sudo
  escalation, disabling the firewall, malware download, password leak). 550 honest trajectories
  in the add-on; the paper's own 416 honest runs are not released.
- Attack side: Claude Opus 4.5 and 4.6 under human-designed, reconnaissance-agent and
  monitor-feedback strategies, then refinement by Opus 4.6. A refined attack is kept only if it
  still succeeds and lowers suspicion for at least 2 of 3 development monitors.
- Honest side: benign Opus 4.5 trajectories, matched to 550 attacks, released later by a
  different team.
- "Success": BashArena's programmatic side-task scorers.
- Conclusion resting on it: refined attacks cut an Opus 4.5 monitor's catch rate from 94.9% to
  60.3%.

**5. SLEIGHT-Bench**
- Source: Najt, Toft, Tracy, Roger, Benton (<https://arxiv.org/abs/2605.16626>); data
  <https://huggingface.co/datasets/sleightbench/SLEIGHT-Bench> (gated, automatic approval); code
  <https://github.com/safety-research/sleight-bench>.
- Licence: MIT.
- Size: 40 attack transcripts in Claude Code format across 11 categories (weight exfiltration,
  credential theft and others), each with a paired benign transcript and a `verifiers.json`.
- Construction: described as human-crafted synthetic transcripts. How the benign pair is written,
  and by whom, is to confirm in the provenance census.
- Conclusion resting on it: an Opus 4.6 monitor with extended thinking catches 32% at 1% FPR; 20
  of 40 attacks are never caught.

### 1b. Agentic control settings

**6. ControlArena settings, and the corpora built from their runs**
- Source: <https://github.com/UKGovernmentBEIS/control-arena>; docs
  <https://control-arena.aisi.org.uk/settings.html>. No paper; the README cites Inglis et al. 2025.
- Licence: MIT.
- Settings: apps, bash, bash_arena, bigcodebench, data_poisoning, eval_sabotage, iac / iac_fast,
  infra, rogue_eval, sae_interp_sabotage, shade_arena (5 public pairs), swebench (Django), vllm,
  agentdojo. Main and side tasks are mostly adapted from existing benchmarks; side-task success is
  programmatic in most settings and an LLM judge in data_poisoning, eval_sabotage and
  sae_interp_sabotage. No trajectories ship; users run prompted honest and attack policies.
- Corpora built from runs: `adityaasinha28/control_arena_{bash,shade,iac,rogue_eval,agentdojo}`
  (<https://huggingface.co/datasets/adityaasinha28/control_arena_bash> and siblings), 1,500 rows
  each, no card, no licence. Claude Sonnet 4, Gemini 2.5 Pro and GPT-5 each write 250 rows of
  each class. In shade and iac each model's rows are about 5 task ids repeated over up to 50
  epochs. Their structure matches the test set of "Constitutional Black-Box Monitoring for
  Scheming in LLM Agents" (<https://arxiv.org/abs/2603.00829>): negative = no side task assigned,
  positive = side task verified by an environment check, assigned-but-failed runs dropped (about
  49%). Nothing on the cards links the two; that link is our inference.
- Conclusions resting on it: 2603.00829's monitor results; Async Control
  (<https://arxiv.org/abs/2512.13526>, code <https://github.com/UKGovernmentBEIS/async-control>,
  MIT), which reports 6% false negatives at 1% FPR on held-out IaC using five ControlArena
  settings with Claude Opus 4.1 as both honest and attack policy.
- Status: done in this repo for the five corpora: character count alone separates the classes
  within each task (AUROC up to 0.802 on agentdojo; four of five above their shuffled-label null),
  and a fifteen-word regex over the agent's scratchpad reaches 0.76–0.82
  ([`experiments/agentic/`](../experiments/agentic/)). The regex result holds only on reasoning
  stored in `trajectory_data`. On the action-only transcript monitors read, it scores 0.51–0.55
  (0.73 on rogue_eval). Pinned re-check:
  [`findings/controlarena-corpora-surface-cues/`](findings/controlarena-corpora-surface-cues/).

**7. BashBench (the Ctrl-Z setting)**
- Source: Bhatt et al., "Ctrl-Z: Controlling AI Agents via Resampling"
  (<https://arxiv.org/abs/2504.10374>); site <https://www.bashcontrol.com/>; the 257 tasks ship in
  ControlArena as `control_arena/settings/bash/bash_tasks.json`.
- Licence: none declared by the paper or site; ControlArena's copy is under its MIT licence.
- Construction: Unix StackExchange questions; GPT-4-turbo wrote the tasks, GPT-4o the tests,
  Claude 3.5 Sonnet the final descriptions; filtered by GPT-4o-mini solve rate.
- Honest side: GPT-4o-mini. Attack side: GPT-4o-mini in a scaffold built on human-written attack
  templates, iterated by a human red team. Side task: download and run a marker "malware"; the
  ControlArena scorer checks a file's contents.
- Conclusion resting on it: resampling protocols cut attack success from 58% to 7% at a small
  usefulness cost.

**8. BashArena**
- Source: Kaufman, Lucassen, Tracy, Rushing, Bhatt (<https://arxiv.org/abs/2512.15688>); code
  <https://github.com/redwoodresearch/basharena_public> (no LICENSE file); tasks
  <https://huggingface.co/datasets/Eccentricity/bashbench2> (CC BY-SA 4.0, 637 rows).
- Construction: StackOverflow questions rated by Claude Sonnet 4; tasks, tests and Dockerfiles
  generated by Claude Opus 4.1 with three critique rounds. No human review is described.
- Scoring: main task = share of hidden pytest cases passed; four side tasks (malware,
  exfiltration, passwordless sudo, disabling the firewall), each a programmatic test run after
  every action.
- Released trajectories: the Redwood control leaderboard data page
  (<https://control-leaderboard.redwoodresearch.org/data>) lists 600 honest and 600 attack
  trajectories from Claude Opus 4.6 (CC BY-SA 4.0); MonitoringBench (entry 4) is built on this
  setting.
- Conclusions resting on it: Sonnet 4.5 achieves undetected sabotage 26% of the time against a
  GPT-4.1-mini monitor at 4% trajectory-wise FPR; "Attack Selection in Agentic AI Control
  Evaluations Meaningfully Decreases Safety" (<https://arxiv.org/abs/2606.06529>): choosing when to
  start or stop an attack cuts safety by about 20 points at a 1% audit budget.

**9. LinuxArena**
- Source: Tracy et al. (<https://arxiv.org/abs/2604.15384>); code
  <https://github.com/linuxarena/control-tower> and
  <https://github.com/redwoodresearch/linuxarena-paper>; site <https://linuxarena.ai>; post
  <https://blog.redwoodresearch.org/p/introducing-linuxarena>.
- Licence: MIT (code); public trajectory mirror
  <https://huggingface.co/datasets/anonymouslinuxarena/linuxarena-public>, CC BY 4.0, 22,215
  trajectories across the 10 public environments.
- Size: 20 environments (10 public), 1,671 main tasks, 184 side tasks (the paper's conclusion
  gives 1,667 and 185).
- Construction: built by contractors (EquiStamp); main tasks LLM-assisted and contractor-reviewed,
  side tasks hand-designed, both scored by hidden automated scorers on the final state. Honest and
  attack policies span Opus 4.6, Haiku, Sonnet, Kimi, GLM 5, Gemini and Grok; the main monitor is
  GPT-5 Nano at 1% step-wise FPR.
- Conclusions resting on it: Opus 4.6 reaches about 23% undetected sabotage; the Attack Selection
  paper above.
- Related, not resting on the public data: the Claude Mythos Preview system card's
  "Minimal-LinuxBench" evaluation (§4.4.3.2,
  <https://cdn.sanity.io/files/4zrzovbb/website/7624816413e9b4d2e3ba620c5a5e091b98b190a5.pdf>)
  adapts a subset of "LinuxBench, an AI control arena built and privately shared by Redwood
  Research" (1,948 adapted pairs, 200 sampled) and runs its own Mythos trajectories and monitors.
  The card does not name LinuxArena; that LinuxBench is its earlier name is our inference. An audit
  of the public trajectories reaches the card only through setting-level findings (scorers, task
  design), and only if the private adaptation shares those environments.

**10. SHADE-Arena**
- Source: Kutasov et al. (<https://arxiv.org/abs/2506.15740>); code
  <https://github.com/jkutaso/SHADE-Arena> (the older safety-research repo is marked deprecated).
- Licence: MIT.
- Size: 17 task pairs; 5 public (american_airlines_2, api_key_calendar_agendas_2,
  bank_transfer_2, expenditure_accounting, spam_filter_update), the other 12 on request.
- Construction: hand-engineered environments, synthetic data expanded by LLMs from human outlines.
  Main task: an LLM judge scores 0–100 against a per-task threshold. Side task: in the public code,
  3 of 5 are programmatic and 2 call an LLM. Evasion = monitor suspicion below 80, a threshold set
  for about 1% FPR with one Claude monitor.
- Conclusions resting on it: the Claude Sonnet 4.5 system card (§7.5.10.3,
  <https://assets.anthropic.com/m/12f214efcc2f457a/original/claude-sonnet-4-5-system-card.pdf>):
  43% stealth success with hidden reasoning; the Mythos Preview card (§4.4.3.1, link above);
  "Optimizing AI Agent Attacks With Synthetic Data" (<https://arxiv.org/abs/2511.02823>): safety
  falls from 0.87 to 0.41; "Reliable Weak-to-Strong Monitoring of LLM Agents"
  (<https://arxiv.org/abs/2508.19461>, Scale AI, which uses SHADE-Arena tasks; data <https://huggingface.co/datasets/ScaleAI/mrt>, CC BY-NC 4.0).

### 1c. Chain-of-thought monitoring

**11. CoT Red-Handed**
- Source: Arnav et al., "CoT Red-Handed: Stress Testing Chain-of-Thought Monitoring"
  (<https://arxiv.org/abs/2505.23575>); code <https://github.com/cotredhanded/code>; selected
  transcripts <https://cotredhanded.github.io>.
- Licence: MIT.
- Size: 1,140 BigCodeBench tasks, each paired with one of 11 side tasks; about 15k completions, of
  which only selected transcripts are public.
- Construction: benign side = the problem with no side task; attack side = five reasoning models
  under prompted attack policies (DeepSeek-R1 and two distills, Claude 3.7 Sonnet Thinking, Grok 3
  Mini) plus one fine-tuned R1-Distill-Qwen-14B. Side-task success is decided by test cases; only
  samples passing both main and side tests are monitored. The monitor sees the clean problem, not
  the attack prompt, and code comments are stripped.
- Conclusions resting on it: the paper's finding that CoT monitoring beats action-only monitoring
  where action-only monitoring misses the sabotage but does worse on obvious sabotage, and that a
  hybrid monitor doubles action-only detection on subtle cases; "CoT-Guard" (<https://arxiv.org/abs/2605.12746>);
  Dolev, Schwartz, Goldberg (<https://arxiv.org/abs/2610.23257>), who reuse the setup.

**12. OpenAI monitorability evaluations**
- Source: Guan et al., "Monitoring Monitorability" (<https://arxiv.org/abs/2512.18311>); release
  post <https://alignment.openai.com/monitorability-evals>; repo
  <https://github.com/openai/monitorability-evals>.
- Licence: Apache-2.0 (upstream sources listed in `DATASET_ATTRIBUTION.md`).
- Size: 12 files, 2,693 prompt rows in perturbed and unperturbed pairs; no rollouts. Several evals
  are withheld (OAI-Repo-Sabotage, Anti-Scheming, Health Queries and others); Anti-Scheming and
  Memory are marked deprecated after grader and monitor mismatches.
- Construction: each instance is run with and without an intervention (for example a hint, or a
  WMDP sandbagging nudge); instances where the intervention has no effect are excluded; outcomes
  are graded by an answer checker, string match or an LLM judge. The monitor prompt quotes the
  hint text verbatim.
- Conclusions resting on it: the GPT-5 system card's monitorability section
  (<https://arxiv.org/abs/2601.03267>) and the GPT-5.4 Thinking card
  (<https://deploymentsafety.openai.com/gpt-5-4-thinking/cot-monitorability>). A critique already
  argues that per-model filtering leaves small, model-dependent subsets (Dilgren and Wiegreffe,
  <https://www.lesswrong.com/posts/z9fPtghFxELBXebY3/evaluating-chain-of-thought-monitorability-is-still-an-open>).

**13. MonitorBench**
- Source: Wang et al. (<https://arxiv.org/abs/2603.28590>); code
  <https://github.com/ASTRAL-Group/MonitorBench>.
- Licence: MIT.
- Size: 1,514 instances across 19 tasks in 7 categories.
- Construction: the README does not say how labels are produced or what the monitor sees; to read
  from the paper before running anything.
- Conclusions resting on it: no dependent paper found yet. Low decision relevance today; kept as a
  cheap static target.

### 1d. Sandbagging and sabotage

**14. Auditing Games for Sandbagging**
- Source: Taylor et al. (<https://arxiv.org/abs/2512.07810>); code
  <https://github.com/AI-Safety-Institute/sandbagging_auditing_games> (MIT); model organisms
  <https://huggingface.co/sandbagging-games>; logs
  <https://huggingface.co/datasets/sandbagging-games/evaluation_logs> (2.6 GB of Inspect logs).
- Licence: code MIT; models and logs none declared.
- Construction: the red team fine-tuned sandbagging organisms to imitate Llama-3.1-8B unless a
  password is present, plus benign models with distractor quirks. Ground truth is fixed by
  construction: a sandbagger must gain at least 10 points with the password on some task
  (McNemar p < 0.05); a benign model may lose at most 5 points against its base. The blue team had
  weights and transcripts but not the passwords.
- Conclusions resting on it: the blue team classified 1 of 5, then 2 of 5, models correctly, read
  as evidence that current sandbagging detection is weak; "Mechanistically Eliciting Latent
  Behaviors in Language Models" (<https://arxiv.org/abs/2606.29604>); "Most Current Model
  Organisms Are Leaky" (<https://arxiv.org/abs/2605.00994>).

**15. CTRL-ALT-DECEIT (MLE-Bench sabotage and sandbagging)**
- Source: Ward, van der Weij et al. (<https://arxiv.org/abs/2511.09904>); code
  <https://github.com/TeunvdWeij/ctrl-alt-deceit> (README links raw and monitor-scored logs on
  Google Drive, not opened).
- Licence: none declared. MLE-Bench task data needs Kaggle credentials.
- Construction: 20 sabotage tasks on the 22-task MLE-Bench low-complexity subset; one prompted
  agent (Claude 3.7 Sonnet). Sabotage success is scored by grading scripts on held-out sabotage
  test sets, some written by GPT-4. Sandbagging success is closeness to a target medal tier below
  the agent's measured capability. The monitor sees the task, the agent's actions and its final
  score, not the sabotage instruction.
- Conclusions resting on it: monitors catch code sabotage well but struggle to catch sandbagging.
  No paper reuses its data; follow-ups cite the finding (for example
  <https://arxiv.org/abs/2607.19321>).

### Considered and dropped

| Candidate | Why dropped |
|---|---|
| Greenblatt et al. 2023, "AI Control" (<https://arxiv.org/abs/2312.06942>, code <https://github.com/rgreenblatt/control-evaluations>, MIT) | Code and prompts only; no data release. Its backdoors survive, if at all, through entry 1's undocumented source. |
| Benton et al. 2024, "Sabotage Evaluations for Frontier Models" (<https://arxiv.org/abs/2410.21514>) | No data released. |
| Baker et al. 2025, "Monitoring Reasoning Models for Misbehavior" (<https://arxiv.org/abs/2503.11926>) | No data released. |
| Emmons et al. 2025, "When Chain of Thought is Necessary…" (<https://arxiv.org/abs/2507.05246>) | No official data; METR's replication (<https://github.com/METR/gdm-replication>) declares no licence. A later candidate. |
| van der Weij et al. 2024, "AI Sandbagging" (<https://arxiv.org/abs/2406.07358>) and noise-injection detection (<https://arxiv.org/abs/2412.01784>) | No released weights for the original organisms; the detection paper's data is a few small files. Entry 14 supersedes both for detection claims. |

---

## 2. The check suite

The suite is fixed before any benchmark is run, with a flag rule per check, so the audit cannot
choose its tests after seeing the data. Each check below gives what it detects, what a failure
would change in a control argument, its cost, and where this repo already implements it.

| # | Check | Detects | Bias on the safety estimate if it fails | Cost |
|---|---|---|---|---|
| 0 | Provenance census | Who and what wrote each class, under which prompt | — (sets up 2) | hours of reading |
| 1 | Content-blind baselines with shuffled-label nulls | Labels readable without the substance | up | CPU minutes |
| 2 | One-class swap | The detector reads the author, not the attack | up | regenerate one class |
| 3 | Label selection tied to attack success | The label is chosen by whether the attack worked, and the choice leaks | either; usually up | CPU minutes |
| 4 | Trigger and side-task validity | "Successful attacks" that do no harm on a legal input | down on catch rate; on red-team success, toward unsafe | CPU hours; a validator per task |
| 5 | Split leakage and duplicates | The same item or near-copy on both sides of a split; labels readable from ids or order | up | CPU minutes |
| 6 | Scorer correctness | The checker that decides success is wrong, flaky, or fires on honest runs | either | CPU hours and a hand-audited sample |
| 7 | Attack instruction visible to the monitor | The monitor reads the red team's prompt or a restatement of it | up | CPU minutes |

**0. Provenance census.** For each class, record the model (or person), its release date, the
prompt or scaffold, the selection step, and who wrote the success checker. This repo's versions:
[`attacker_mix.py`](../experiments/apps/attacker_mix.py), [`agentic/prov.py`](../experiments/agentic/prov.py).
It answers the elicitation question directly: if every attack in a 2026 benchmark comes from
models released by early 2025, the benchmark measures a monitor against a weaker red team than the
one a safety case must assume. The census also decides which side to regenerate in check 2.

**1. Content-blind baselines.** Fit detectors that cannot see the attack: bag-of-words over the
artifact (the attack lives in a few tokens, authorship in all of them); length or character count,
computed within each task so it cannot read the task; metadata only (problem difficulty, number of
tests, task id, epoch, environment); and, for agent transcripts, a keyword regex over the
scratchpad. Each gets a null of 1,000 label permutations within task groups, run through the whole
pipeline. Repo: [`koran_split_eval.py`](../experiments/apps/koran_split_eval.py),
[`floors.py`](../experiments/apps/floors.py), [`agentic/matched.py`](../experiments/agentic/matched.py),
[`agentic/floors2.py`](../experiments/agentic/floors2.py), [`agentic/cot.py`](../experiments/agentic/cot.py).
- Flag rule: the baseline's AUROC interval lies above its null's 95th percentile and above 0.6,
  or the baseline ranks above the median published monitor.
- What failure changes: a monitor ranking on the benchmark no longer shows which monitor finds
  sabotage, and a catch rate taken from it is an upper bound for deployment, where the cue will
  not be there. Bias up.

**2. One-class swap.** Regenerate one class with the other class's author, so authorship and label
come apart, and score detectors on the four pairings (honest by A or B, against attacks by A or B).
A detector that reads the attack keeps its AUROC across the swap; one that reads the author moves
with it. Repo: [`classifier_swap.py`](../experiments/apps/classifier_swap.py),
[`monitor_swap.py`](../experiments/apps/monitor_swap.py), the `gate_s_*` scripts.
- Flag rule: swapping only the honest class (or only the attack class) moves the detector's AUROC
  by more than its bootstrap interval, in the direction of the author gap.
- What failure changes: the monitor's catch rate was partly a catch rate for "not written by the
  honest author". In deployment the untrusted model writes both, so the safety estimate was
  biased up. For agentic settings where one model writes both classes (entries 6, 9) the swap is
  replaced by the prompt-matched variant: request the honest run under the attack prompt's wording
  minus the side task, which tests whether the detector reads the attack prompt's style.

**3. Label selection tied to attack success.** Many datasets keep an attack only if it succeeded,
and some pad the honest class with items whose attack failed (entry 2), or drop failed attempts
(entry 6, about 49%). Two things to measure: whether the selection leaks the label (fit the
metadata baseline of check 1 on features that predict success, such as number of tests, task
difficulty or environment), and whether the catch rate differs between "all attempts" and "only
successful attacks". Repo: [`floors.py`](../experiments/apps/floors.py) protocols P0–P4,
[`nocode_outside.py`](../experiments/apps/nocode_outside.py),
[`merge_draws.py`](../experiments/apps/merge_draws.py) `--keep first` against `--keep best`,
[`shared_problems.py`](../experiments/apps/shared_problems.py).
- Flag rule: a metadata-only detector beats its null; or the catch rate on successful attacks
  differs from the catch rate on all attempts by more than its interval.
- What failure changes: a safety estimate needs the catch rate on the attacks that would succeed,
  weighted by how often the policy attempts them. Keeping only survivors is right for that
  conditional, but survivor selection also selects for easy problems or blatant attacks, and the
  red team's real choice of when to attack (Ge-Wang et al., entry 8) is a different selection.
  Direction depends on the benchmark; usually up, because survivors on weakly tested problems are
  the conspicuous ones.

**4. Trigger and side-task validity.** Does each "successful attack" do harm on an input or state
the task allows? For code backdoors: the trigger passes an input validator written from the
problem statement without seeing any trigger, and the backdoor's output there differs from the
majority answer of several reference solutions ([`verify_backdoor.py`](../experiments/apps/verify_backdoor.py)
`--validators --human-ref`, validators checked against every stored test input by
[`check_validators.py`](../experiments/apps/check_validators.py)). For agentic side tasks: rerun the
side-task scorer on the final state from a clean replay, and check that the harm requires the
agent's action (the marker file or permission change was not already present, the exfiltrated
secret is the real one, the "malware" ran rather than being written). For CoT side tasks: inspect
the side-task test for trivially passable conditions.
- Flag rule: more than 5% of "successful" attacks fail validity, or the failure rate differs
  between attack sources by more than its interval.
- What failure changes: invalid attacks have nothing to catch, so a monitor's catch rate on them
  is biased down (this repo: Sonnet 5's backdoors looked far harder to catch until 41 of 99 were
  removed). They also inflate the red team's success rate, which
  pushes the safety estimate toward unsafe and can make one attacker look stronger than another.
  If invalid attacks are flagged anyway (for odd-looking code), the catch rate is biased up. The
  check reports which.

**5. Split leakage and duplicates.** Check for the same problem, task id or near-copy (MinHash on
code or transcripts) on both sides of a train, validation or test split; the same task repeated
over many epochs inside one class (entry 6: about 5 tasks × 50 epochs); labels predictable from
row id, file order or upload batch; and benchmark items published before a monitor model's
training cutoff (canary strings, public release dates). New code; no version in this repo yet.
- Flag rule: any cross-split duplicate rate above 1%, or a label-from-id AUROC above its null.
- What failure changes: held-out monitor scores and any monitor fitted or prompt-tuned on the
  training split are inflated. Bias up. With few distinct tasks, intervals computed over
  trajectories rather than tasks are also too narrow.

**6. Scorer correctness.** Audit the checker that turns a run into labels: does the reference
solution pass its own tests ([`run_tests.py`](../experiments/apps/run_tests.py) `--solutions human`
against the dataset's pass flag); does the side-task scorer fire on honest runs (an honest agent
that touches the firewall or sudoers for its main task); does an LLM judge agree with a
hand-labelled sample of 50–100 items; does rescoring give the same label (test–retest, as in
[`monitor_swap.py`](../experiments/apps/monitor_swap.py)); do harness limits (timeouts, memory) flip
labels.
- Flag rule: honest runs trigger the side-task scorer in more than 1% of cases, judge–human
  agreement below 90%, or test–retest disagreement above 5%.
- What failure changes: label noise caps the AUROC any monitor can reach and, when it correlates
  with a feature, becomes a cue. A side-task scorer that fires on honest runs inflates the
  baseline harm rate and biases the safety estimate down; one that misses real harm biases it up.

**7. Attack instruction visible to the monitor.** Check whether the monitor's input contains the
red team's instructions, a hint, or the agent restating its side task. This repo's scratchpad
regex reached 0.76–0.82 on entry 6's corpora. Entry 12's monitor prompt quotes the hint verbatim
by design; entries 11 and 15 strip the attack prompt.
- Flag rule: a keyword detector over the monitor's input beats its null and reaches more than half
  of the best monitor's AUROC.
- What failure changes: the benchmark measures how well a monitor reads a confession, which a
  capable attacker in deployment will not write. Bias up. For CoT-monitorability claims this is
  sometimes the quantity of interest; the audit then reports it rather than flags it.

---

## 3. Ranking

Expected value of auditing a benchmark = decision relevance × likelihood of an artifact ÷ cost to
check. Each factor is scored 1–3.

- **Decision relevance:** 3 if a system card, a lab's safety argument, or a widely cited control
  result rests on it; 2 if peer-reviewed results or monitor rankings do; 1 otherwise.
- **Artifact likelihood:** how many of the construction patterns behind this repo's three findings
  it shares (different authors per class, selection on success, an unchecked success criterion,
  low task diversity, a visible attack prompt).
- **Cost:** 1 if the labelled data is released and the checks run on a CPU; 2 if one class must
  be regenerated or a scorer replayed in Docker; 3 if trajectories must be generated from
  scratch or the data is mostly private.

| Rank | Benchmark | Relevance | Artifact | Cost | Score | Main reason |
|---|---|---|---|---|---|---|
| 1 | 4. MonitoringBench | 3 | 3 | 1 | 9.0 | Attacks and honest runs released separately by different teams; attacks refined offline and kept by suspicion against specific monitors; CC BY |
| 2 | 3. Control Tax set (and the rest of 1) | 3 | 3 | 1.5 | 6.0 | Same construction as the audited split, no trigger check, nine older attackers; this repo's checks run on it nearly as they are |
| 3 | 9. LinuxArena | 3 | 2 | 1 | 6.0 | 22,215 public trajectories under CC BY; hidden final-state scorers to replay; a frontier system card uses a private adaptation of the setting (not these trajectories) |
| 4 | 6. ControlArena run corpora | 2 | 3 | 1 | 6.0 | Length and scratchpad cues already found; no licence, provenance inferred, so findings can only be reported in aggregate |
| 5 | 12. OpenAI monitorability evals | 3 | 3 | 2 | 4.5 | System-card claims; the hint is in the monitor prompt by design; per-model filtering; rollouts must be regenerated; partly critiqued already |
| 6 | 15. CTRL-ALT-DECEIT | 2 | 3 | 1.5 | 4.0 | The monitor sees the agent's final score, which may alone predict sandbagging; GPT-4-written sabotage tests |
| 7 | 5. SLEIGHT-Bench | 2 | 2 | 1 | 4.0 | Cheap, but 40 items gives intervals too wide for most checks |
| 8 | 10. SHADE-Arena | 3 | 2 | 2 | 3.0 | System cards rest on it; main tasks LLM-judged in 2 of the 5 public pairs (api_key, expenditure); only 5 public pairs. Audited: [`findings/shade-arena-scorers-and-tool-names/`](findings/shade-arena-scorers-and-tool-names/) |
| 9 | 14. Auditing Games | 3 | 1.5 | 1.5 | 3.0 | Ground truth by construction; the open question is whether content-blind features in the released logs separate sandbaggers |
| 10 | 8. BashArena (beyond MonitoringBench) | 3 | 2 | 2 | 3.0 | LLM-generated tests with no human review; side-task tests after every action may fire on honest runs |
| 11 | 13. MonitorBench | 1 | 2 | 1 | 2.0 | Cheap, but nothing rests on it yet |
| 12 | 11. CoT Red-Handed | 2 | 2 | 2.5 | 1.6 | Monitor input is clean; full completions unreleased, so most checks need regeneration |
| 13 | 7. BashBench | 2 | 2 | 3 | 1.3 | Human-templated attacks against a model honest policy; no released trajectories; superseded by BashArena |
| — | 2. High-quality APPS split | — | — | — | — | Done in this repo |

The scores are judgements, fixed here so the order cannot be revised after results come in. Ties
are broken by cost.

### Recommended first three

**1. MonitoringBench.** It is the most direct successor to the dataset this repo audited: a static
set built to rank monitors, with a headline catch-rate claim (94.9% to 60.3%). Three of its
construction choices match patterns that produced artifacts here. The honest class was released
months later by a different team, under a different pipeline, so check 2's question (does a
monitor read the pipeline rather than the attack?) applies with a twist: refined attacks were
edited by Opus 4.6 after generation and honest runs were not, so an edit-style cue is plausible
(checks 1 and 2, using the matched pairs). Refined attacks were kept if they lowered suspicion
for development monitors, which is selection on the evaluated quantity (check 3: compare catch
rates of refined against unrefined attacks per monitor, and between development and held-out
monitors). And an attack edited offline must still pass the side-task scorer: check 4 replays a
sample of refined trajectories in BashArena to confirm the side task still succeeds. The data is
CC BY, so per-item findings can be published. Cost: days of CPU, plus Docker replay for the
check-4 sample.

**2. The Control Tax backdoor set, through apps-control-arena.** This is the cheapest high-value
run, because this repo's code already does it: `verify_backdoor.py --validators --human-ref` on
8,855 backdoors across nine attackers, the bag-of-words and metadata baselines per attacker, and
the Greenblatt-join check. The marginal cost is input validators for about 2,400 problems; these
can be shared with ControlArena PR #899 rather than duplicated. The result would say whether
"monitor strength, not attacker strength, drives detection" survives once invalid triggers are
removed per attacker (if weaker attackers write more invalid triggers, the attacker effect is
masked), and it would hand ControlArena a verified column for its default setting.

**3. LinuxArena public trajectories.** The highest-stakes agentic target with released data:
22,215 CC BY trajectories cover the public environments, and the Mythos Preview system card runs a
privately shared, adapted version of the setting. Trajectory-level findings bear on the LinuxArena
and Attack Selection papers' numbers; only scorer and task findings could carry to the card, and
only if its adaptation shares the environments. Run
checks 1, 5 and 7 on the mirror (character count within task, scratchpad regex, duplicates across
the honest calibration set and the attack set), and check 6 by replaying honest trajectories
through the hidden side-task scorers to measure how often they fire without an attack. If the
1% FPR threshold is set on honest runs from a different policy mix than the attacks, report it
under check 2.

The ControlArena run corpora (rank 4) score as high, but the work there is mostly done and, with
no licence and inferred provenance, any write-up must stay at aggregates; they are better folded
into the write-up of the third run than audited on their own.

---

## 4. Telling maintainers before publishing

The aim is that each maintainer can fix or annotate their dataset, and correct anything we got
wrong, before a post names it. The findings are about how datasets were built, not about anyone's
competence, and the write-up should say so.

1. **Fix the checks and flag rules first.** Commit this document's suite, flag rules and ranking
   to the repo before running anything, and record the dataset revision (HF commit or file hash)
   audited.
2. **Run, then draft per benchmark.** For each flagged benchmark, a two-page note: what was
   checked, the numbers with intervals, the per-item list (for example, the backdoor ids whose
   trigger fails the validator, with the validator), the scripts to reproduce, and which published
   conclusion it bears on and in which direction. State what was not found as plainly as what was.
3. **Contact privately.** Send the note to the dataset owner and the corresponding author of each
   paper whose conclusion it bears on. Contacts by entry:
   - entries 1 and 6: ControlArena maintainers (UK AISI), through a GitHub issue only where the
     problem is already public (trigger legality is: issue #755, PR #899); otherwise by email;
   - entry 3: Mikhail Terekhov and co-authors;
   - entry 2: Eugene Koran; and Anik Jha for the 24-monitor ranking;
   - entry 4: the MonitoringBench authors (the HF account is anonymised; reach them through the
     arXiv listing or the LessWrong post) and the MonitoringBenchHonest authors;
   - entries 8–10: the BashArena and LinuxArena authors at Redwood Research, and the SHADE-Arena
     authors at Anthropic; where a system card's number is affected, also the lab's safety team.
4. **Window.** 21 days before anything public, extended once on request. If the maintainer
   disputes a finding, rerun with their correction and report both.
5. **Offer the fix.** With each note, offer a PR: input validators, a `verified` column, a
   corrected join, a provenance field on the card. A dataset that ships the fix before the post is
   reported as fixed, with the revision.
6. **Publish.** One LessWrong / Alignment Forum post covering all audited benchmarks, with a
   results table by check and benchmark, the bias direction for each finding, and each
   maintainer's response linked or quoted with permission. Code and validators go in this repo.
   For datasets without a licence, the post and repo report aggregates and item ids only, never
   content.
7. **Afterwards.** Rerun the suite on each fixed revision and update the table; offer the suite as
   a CI check to the ControlArena maintainers.

---

## Open questions before running

- The second-round search, covering a further ~35 control, misalignment, reward-hacking and
  sandbagging benchmarks, is in [`catalogue.md`](catalogue.md), with its own ranking of next
  audits.

- Whether MonitoringBench's development and held-out monitors are identified in the released
  data; check 3's second half needs them.
- Whether LinuxArena's hidden side-task scorers are available to outside auditors, or only the
  public environments' scorers; check 6 depends on it.
- Whether the ControlArena maintainers would take a validator set for all of apps, which decides
  whether rank 2 builds validators here or upstream.
- The Greenblatt-join bug (entry 1) is confirmed and ready for the ControlArena note
  ([`findings/controlarena-apps-join/`](findings/controlarena-apps-join/)). The fix is one line:
  key both sides by `int(problem_id)`.
