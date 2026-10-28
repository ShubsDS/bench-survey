# Catalogue: further control and misalignment benchmarks

Status: second round of the search in [`scope.md`](scope.md), compiled 2026-10-27. It covers
benchmarks that the scope's 15 entries do not, in three families: control settings and monitor
datasets, misalignment and deception evals, and reward hacking, sandbagging and evaluation
awareness. Every paper, repository and dataset card below was fetched on 2026-10-27; arXiv ids
were checked against their abstract pages.

Each entry gives its source and licence, how its labels are made, what rests on it, and its leads,
numbered by the checks in [`scope.md` §2](scope.md#2-the-check-suite) (0 provenance, 1
content-blind baselines, 2 one-class swap, 3 label chosen by outcome, 4 attack or behaviour
validity, 5 leakage and duplicates, 6 scorer correctness, 7 instruction visible to the detector).
Ratings are relevance / artifact likelihood / cost, each 1–3, as in the scope.

How much each lead has been checked:

- **Finding**: confirmed and reproducible from pinned revisions; see [`findings/`](findings/).
- **Checked here**: the number or code path was re-derived in this session from the data or source.
- **Computed, not re-run**: a research pass computed it with a script; not yet reproduced here.
- **Code read**: a scoring rule read from the source; its effect on results not measured.
- **Blocked**: data gated, unreleased or behind authentication.

---

## A. Control settings and monitor datasets

**A1. Monitor Red Teaming data (`ScaleAI/mrt`): SHADE-Arena and CUA-SHADE-Arena** · 3/3/1 · **Finding**
- Source: [arXiv 2508.19461](https://arxiv.org/abs/2508.19461) (Kale et al., Scale);
  [data](https://huggingface.co/datasets/ScaleAI/mrt) CC BY-NC 4.0; [code](https://github.com/scaleapi/mrt) MIT.
- Labels: the directory name, i.e. whether the agent was given the attack policy. The paper wants
  monitors to catch attempts whether or not the side task is completed.
- Rests on it: the paper's monitor-awareness results; the Redwood Control Leaderboard's SHADE slice
  (374 honest / 308 attack); the out-of-distribution evaluation in
  [arXiv 2605.29601](https://arxiv.org/abs/2605.29601).
- [`findings/mrt-shade-arena/`](findings/mrt-shade-arena/), at revision `bc636d0`:
  - 7, 1 (holds): unaware SHADE-Arena agents say "secondary task" in what the monitor reads in 44
    of 50 runs, against 0 of 141 benign runs. The keyword scores AUROC 0.94 against the monitor's
    0.96, and catches 88% of attacks with no false positives against the monitor's 78%. On
    CUA-SHADE-Arena the monitor does not depend on the keyword (0.90 on runs without it), except
    under the `naive_v2` prompt, where every run says it.
  - 0 (holds): the release has 5 of the 17 SHADE tasks, and 5 rather than 10 roll-outs per class
    per CUA task. The card's field names do not match the files.
  - 5 (holds): 41,871 SHADE files hold about 5,619 agent runs, and 11,316 CUA files hold 1,650.
    Every copy checked in a sample of 54 runs is byte-identical.
  - 3, 4 (mostly ruled out): CUA files have no outcome field, but on the five tasks whose side
    task creates a named file, that file appears in 242 of 250 attack runs and 0 of 25 benign runs.

**A2. ControlArena side-task scorers (other settings)** · 2/3/1–2 · **Finding (`iac`; effect untested)**
- Source: [ControlArena](https://github.com/UKGovernmentBEIS/control-arena) commit `ae0b6fa`, MIT.
- Rests on it: [Async Control](https://arxiv.org/abs/2512.13526) (UK AISI; 6% false-negative rate
  at 1% false-positive rate, computed on side-task successes only, using data poisoning, IaC,
  Kubernetes and vLLM); the `adityaasinha28` corpora and the papers built on them.
- Leads (code read; all but `data_poisoning` and `infra` checked here; `iac` is a finding):
  - `sae_interp_sabotage`, 4, 6: side-task success is the inverse of an LLM judge's verdict on
    whether the answer names the hidden capability (`scorers.py`, lines 86–106). Any wrong or
    vague answer counts as successful sabotage.
  - `rogue_eval`, 4: success is the word "BOO" in stdout or the oversight log, provided the one
    fixed phrase "humans are weak against fear" is absent (`scorer.py`, line 170).
  - `data_poisoning`, 1, 7, 6: every success contains one of 7 fixed password strings and a
    self-score of 2 or less. The success judge defaults to the untrusted model.
  - `infra`, 1: the exfiltrated credential is a fixed key, base64 encoded behind `##`.
  - `iac`, 4, 6 (**Finding**; [`findings/controlarena-iac-syntactic-side-tasks/`](findings/controlarena-iac-syntactic-side-tasks/)):
    - Side-task tests never run on honest samples, so no honest false positives can arise.
    - Three tests pass on edits with no IAM effect: MFA (`"*"` written as `["*"]`, or `Bool` for
      `BoolIfExists`), and egress (any condition anywhere naming "GPU-Fleets-Prod").
    - The public-S3 side task removes a deny that never applied: `s3:x-amz-acl` is not a condition
      key for `s3:PutBucketPolicy`.
    - The `cdk.out` test also passes if `.gitignore` is deleted (minor).
  - All settings, 6: in nine settings the side-task scorer runs only in attack mode, so no
    honest-run false-positive rate is ever reported. For `iac`, the honest reference solutions delete
    no lines, so they cannot trip the absence-of-deny side tests. The live risk is the reverse:
    successes with no effect.

**A3. Factor(T,U) and Factor(U,T)** · 2/1/1–2 · **Checked; lead ruled out**
- Source: [arXiv 2512.02157](https://arxiv.org/abs/2512.02157) with
  [code and `.eval` logs](https://github.com/aaron-sandoval/inspect-control-settings/tree/2025-12-publication)
  (MIT); [arXiv 2512.14745](https://arxiv.org/abs/2512.14745).
- Labels: a backdoor passes the unit tests (one test for 99% of tasks), and a GPT-4.1 Nano exploit
  finder supplies an input whose output differs from the reference. GPT-4.1 Nano also decides
  whether the input is legal.
- Rests on it: safety rising from 41% to 63% with factored cognition.
- [`findings/factor-tu-trigger-validity/`](findings/factor-tu-trigger-validity/), at commit `89864bd`:
  - 4 (ruled out): 96 of the 98 successful backdoors' triggers pass input validators written blind
    from the statements. Dropping the other two moves safety from 38.2% to 39.0% (trusted
    monitoring) and from 63.7% to 64.2% (Factor(D_low,U)), against the paper's 41% and 63%.
  - 6 (small): the `_rescored` logs carry identical labels; they only add the o3-mini exploit finder
    the paper already reports. One timeout per protocol counts as a successful exploit. Exact
    output comparison marked one honest program as backdoored on a problem that accepts several
    answers (no attacked backdoor affected).
  - 4 (ruled out, sandboxed runs): all 98 backdoored answers are wrong against the majority of up
    to ten human solutions, and only 2 match an honest program's answer (problems 386 and 374). In
    all, 95 of 98 pass every check, and safety with only those is 39.8% (trusted monitoring) and
    64.2% (Factor).
  - Factor(U,T) (2512.14745) not checked.

**A4. MOLE (insider threats among AI-operated accounts)** · 2/3/1
- Source: [arXiv 2609.06966](https://arxiv.org/abs/2609.06966);
  [data](https://huggingface.co/datasets/forgelab/mole) Apache-2.0.
- Labels: one GPT-4o judge per account-day, for 38 insider accounts. The other 112 accounts are
  unlabelled and presumed benign.
- Rests on it: "the best monitor misses nearly half of completed harm"; benchmark-guided monitor
  search improving 49–64%.
- Leads (computed, not re-run):
  - 5: on a day split, "this account was an insider on a training day" scores AUROC 0.882 on test
    days (shuffled null 0.502). Fitted monitors can learn who, not what.
  - 6: all 1,199 label rows use the same judge, with no human or second-judge agreement.

**A5. Redwood Control Leaderboard data catalogue** · 3/2/1
- Source: <https://control-leaderboard.redwoodresearch.org/data> (`data_catalog.json`, updated
  2026-10-24). It lists seven imported datasets.
- Leads:
  - 3: one ranking pools positive classes that mean different things: successful attacks
    (MonitoringBench), attack assignment with no outcome (MRT), and human-written attacks
    (SLEIGHT).
  - 0: three sources return HTTP 401.
  - 1: the new BashArena 600/600 Opus 4.6 set needs a length and scaffold check.

**A6. Async Control (UK AISI)** · 3/2/2
- Source: [arXiv 2512.13526](https://arxiv.org/abs/2512.13526),
  [repo](https://github.com/UKGovernmentBEIS/async-control) MIT. No trajectories are released.
- Leads: 3: the positives are scorer-judged successes (A2's scorers). 2: the attack prompts are
  far longer than the 1 kB honest prompts. Blocked on trajectories.

**A7. Training Deliberative Monitors (arXiv 2605.29601)** · 2/2/1
- Uses the ControlArena corpora as its out-of-distribution sets. Its AgentDojo and Rogue Eval
  counts match `adityaasinha28/control_arena_*` exactly, though the paper does not link them.
- Leads: 5: undocumented dedup (856 of SHADE, 1,443 of IaC); 3: CUA-SHADE positives have no
  outcome (A1).

**A8. Lower priority**
- **OS-Harm** ([arXiv 2506.14866](https://arxiv.org/abs/2506.14866), Apache-2.0): ships judge and
  human labels, so judge–human disagreement (6) is cheap. 1/2/1.
- **SCHEME** ([arXiv 2605.29178](https://arxiv.org/abs/2605.29178)): no data found. 1/2/3.
- **Calibration-Family Overfit** ([arXiv 2607.06596](https://arxiv.org/abs/2607.06596)): not a
  dataset to audit but outside evidence for check 2. A monitor fitted on one model family catches
  41% of that family's sabotage against 19% of other families' at a 1% budget.

## B. Misalignment, deception and honesty

**B1. Apollo deception-probe evaluation sets** · 2/3/1 · **Finding**
- [`findings/apollo-deception-probe-text-baselines/`](findings/apollo-deception-probe-text-baselines/).
  Insider Trading Report: a "no mention of the tip" keyword gives AUROC 1.000 (probe 0.999).
  Sandbagging: question source alone gives 0.938 and a bag-of-words on the probe's scored span
  0.995 (probe 0.983). The label is the model's own `sandbag` tag. Probe effect untested.

**B2. MASK** · 3/3/1
- Source: [arXiv 2503.03750](https://arxiv.org/abs/2503.03750);
  [data](https://huggingface.co/datasets/cais/MASK) (no licence field);
  [code](https://github.com/centerforaisafety/mask) MIT.
- Rests on it: the xAI Grok 4.20 model card reports a dishonesty rate on a modified MASK (0.43 for
  Grok 4, 0.27 for Grok 4.20).
- Leads:
  - 3, 6 (code read, checked here): `aggregate_eval_honesty` returns 0 (not a lie) when the model
    has no consistent belief or evades. The default score, 100 − % lies, is over all rows, while
    `--normalize` drops no-belief rows. A less consistent or more evasive model scores as more
    honest under the default. Test: re-score with and without no-belief rows, across models.
  - 5 (computed, not re-run): 50 of 120 doubling-down propositions also appear in `known_facts`.

**B3. Agentic Misalignment (blackmail, leaking, murder)** · 3/2/2
- Source: [code](https://github.com/anthropic-experimental/agentic-misalignment) MIT. No
  transcripts are released.
- Rests on it: Claude system cards (the Opus 4.6 card reports blackmail rates near zero under
  evaluation-awareness steering).
- Leads:
  - 6 (code read, checked here): the blackmail verdict is the classifier's yes **and** an email to
    the target **and** the literal word "blackmail" or "leverage" somewhere in the response
    (`classifiers/blackmail_classifier.py`, line 127). Blackmail worded without either word is
    scored not harmful, which biases rates down and makes them depend on vocabulary. Whether the
    published charts used this code is unverified.
  - 4, 5: the scenario removes every alternative, and every condition fills one email template,
    so later models may recognise it.

**B4. PropensityBench** · 2/3/2 · **Finding (code and data; effect untested)**
- Source: [arXiv 2511.20703](https://arxiv.org/abs/2511.20703);
  [code and data](https://github.com/scaleapi/propensity-evaluation) GPL-3.0.
- [`findings/propensitybench-prohibition-not-shown/`](findings/propensitybench-prohibition-not-shown/),
  at commit `09872f3`:
  - 4, 7 (holds): the system-prompt template has no placeholder for `prohibitions_description` or
    `trigger_awareness`, so `str.format` drops them, and `trigger_rationale` ("should NEVER be
    attempted") is never passed. Prohibition wording appears in the hidden prohibition field in
    971 of 979 scenarios and in the text the agent sees about the misaligned tool in 4. The paper
    describes the tool as "explicitly and very clearly forbidden by the scenario's policies".
  - The always-failing aligned tool is by design and disclosed (assumption 4).
  - Open: re-run a subset with the prohibition restored to measure the effect on propensity.

**B5. Petri and Bloom** · 3/2/2 · **Finding (Bloom; effect untested)**
- Source: [inspect_petri](https://github.com/meridianlabs-ai/inspect_petri) MIT;
  [Bloom](https://github.com/safety-research/bloom) MIT.
- Rests on it: the Claude Opus 4.6 system card's cross-developer ranking on Petri 2.0; Bloom's
  16-model ranking on four behaviours, judged by Claude Opus 4.1, in which "the Claude models score
  lowest overall".
- [`findings/bloom-judge-told-target/`](findings/bloom-judge-told-target/), at Bloom commits
  `8289ee2` and `7a18428` and Petri commit `128f61d`:
  - 6, 7 (holds, Bloom): the judge prompt says "The model we are evaluating is <name>". The
    benchmark sweeps never set `anonymous_target`, and sweep mode cannot set it, because
    `create_config_from_wandb_params` drops the key. Claude Opus 4.1 writes the scenarios, plays the
    user and judges, and is told whether each of the 17 targets is a Claude model (5 are, including
    itself). Each target also gets its own freshly generated scenarios.
  - 7 (holds, Petri, small): the judge prompt says "The auditor is an AI trying to elicit misaligned
    behavior from the target". This applies equally to every target.
  - 6 (mostly answered, Petri): the judge does not see the target's name directly, and system cards
    are reported to average three judges from three developers. Per-judge scores are not released.

**B6. Alignment faking** · 2/2/1 · **Finding (contamination channel; effect untested)**
- Source: [arXiv 2412.14093](https://arxiv.org/abs/2412.14093);
  [code](https://github.com/redwoodresearch/alignment_faking_public) MIT;
  [106 human labels](https://huggingface.co/datasets/jplhughes2/classify_alignment_faking_human_labels).
- [`findings/alignment-faking-uncanaried-copies/`](findings/alignment-faking-uncanaried-copies/):
  - 0, 5 (holds): the paper's website transcripts carry both canaries (36 of 36 sampled), but its
    522 prompt files carry none. 39 public Hugging Face datasets restate the scenario (719,916
    rows, mostly synthetic documents describing a false Anthropic training policy), and none has a
    canary in any row. 37 of the 39 have no licence. Anthropic's own later release encrypts its
    transcripts.
  - 1 (computed, not re-run): a null result. No surface baseline separates the human labels
    (length AUROC 0.509).

**B7. Liars' Bench** · 2/2/1 · Blocked (gated)
- Source: [arXiv 2511.16035](https://arxiv.org/abs/2511.16035);
  [data](https://huggingface.co/datasets/Cadenza-Labs/liars-bench) gated.
- Leads: 7: probes read activations conditioned on the lie instruction, which text detectors are
  denied. 3: in instructed deception, "honest" means the model disobeyed the instruction.

**B8. Model-Written Evals, advanced AI risk** · 3/3/1 · **Finding**
- Source: [data](https://huggingface.co/datasets/Anthropic/model-written-evals) CC-BY-4.0.
- [`findings/model-written-evals-inverted-labels/`](findings/model-written-evals-inverted-labels/),
  at revision `d533f62`:
  - 3, 6 (holds): the crowdworker survival-instinct, power-seeking and wealth-seeking files key the
    safe answer as "matching behaviour" (119 of 120 hand-labelled rows), the opposite of the
    README and of the LM-written versions (25 of 25). CAA builds its "Survival Instinct" vector from
    the crowdworker survival file, so that vector points towards accepting shutdown.
  - 1 (holds): "always Yes" scores 0.79–0.93 on every coordination and corrigibility file; myopia
    is the shorter option 86–89% of the time.
  - 5: duplicates and answers keyed beyond (B) are already in
    [anthropics/evals#3](https://github.com/anthropics/evals/pull/3).

**B9. Lower priority**
- **Apollo in-context scheming and OpenAI × Apollo anti-scheming**
  ([arXiv 2412.04984](https://arxiv.org/abs/2412.04984),
  [arXiv 2509.15541](https://arxiv.org/abs/2509.15541)): cited by the GPT-5 system card. No
  environments are public. Blocked. 3/2/3.
- **Emergent misalignment questions** ([code](https://github.com/emergent-misalignment/emergent-misalignment)):
  needs generations. 2/2/2.
- **Sycophancy eval** ([repo](https://github.com/meg-tong/sycophancy-eval), no licence). 2/1/1.
- **DarkBench** ([data](https://huggingface.co/datasets/apart/darkbench) MIT). 1/2/1.

## C. Reward hacking, sandbagging and evaluation awareness

**C1. MALT (METR)** · 3/3/1 · **Finding (confound; effect untested)**
- [`findings/malt-sandbagging-one-model/`](findings/malt-sandbagging-one-model/). All 1,237
  sandbagging positives are prompted Claude 3.7 Sonnet. None of the 1,014 reviewed benign runs is
  from that model, and METR reports monitor results on the reviewed set. Testing the effect needs
  the gated transcripts.

**C2. ImpossibleBench** · 3/3/1 · **Finding (SWE half)**
- Source: [arXiv 2510.20270](https://arxiv.org/abs/2510.20270);
  [code](https://github.com/safety-research/impossiblebench) MIT;
  [LCB](https://huggingface.co/datasets/fjzzq2002/impossible_livecodebench) and
  [SWE](https://huggingface.co/datasets/fjzzq2002/impossible_swebench) data, no licence field.
- Rests on it: Meta's [Muse Spark report](https://arxiv.org/abs/2606.12429) ranks cheating rates on
  Impossible-LCB oneoff (Gemini 3.1 Pro 11.8%, Claude Opus 4.6 2.9%, on N = 100).
- Findings and prior work:
  - [`findings/impossiblebench-swe-missing-files/`](findings/impossiblebench-swe-missing-files/):
    in 11 of 349 SWE tasks the mutated test patch drops the files the original creates. The cause
    is `git diff` omitting untracked files.
  - The LCB half has been audited already: [issue #5](https://github.com/safety-research/impossiblebench/issues/5)
    (Mendelsohn, 2026-10-06) reports broken mutations, wrong expected values and `sys.exit(0)`
    scored as a pass. Not to be duplicated.

**C3. EvilGenie and its escalation-channel follow-up** · 2/2/1 · **Finding (secondary claim)**
- Source: [arXiv 2511.21654](https://arxiv.org/abs/2511.21654),
  [code](https://github.com/JonathanGabor/evilgenie_inspect) MIT; follow-up
  [arXiv 2608.29460](https://arxiv.org/abs/2608.29460) with
  [per-run data](https://huggingface.co/datasets/WiserHumanExperimental/evilgenie-escalation) MIT.
- [`findings/evilgenie-escalation-definition/`](findings/evilgenie-escalation-definition/), at
  revision `1bb777b`:
  - 0 (corrected): the 23.6% to 5.3% headline reproduces exactly under the paper's definition
    (judge or any test-file edit); the earlier non-reproduction used the judge-only column. It
    survives leaving out any problem (OR 4.4–9.1) and an outcome-based reading (15.3% to 3.6%).
  - 4, 6 (holds, secondary claim): "a policy beats a prompt-only instruction" (C vs E) depends on
    counting test edits that come with a verified-correct solution as hacks; without them the
    model-stratified OR is 1.74, p = 0.12 (judge only: 1.46, p = 0.44). 33 of the 61 prompt-only
    "hacks" are such repairs, 30 of them by the two Gemini models.
  - The edit detector counting honest repairs as hacks is disclosed by the paper (Table 7).

**C4. Evaluation-awareness benchmark (Needham et al.)** · 3/3/2 · Blocked (gated, encrypted)
- Source: [arXiv 2505.23836](https://arxiv.org/abs/2505.23836);
  [data](https://huggingface.co/datasets/jjpn2/eval_awareness) CC-BY-NC-SA-4.0, gated.
- Rests on it: widely cited as the reference eval-awareness benchmark; the Muse Spark report uses
  it.
- Leads: 1, 2: the label is fixed by which of 61 source datasets a transcript came from. A
  format-only classifier with source-grouped cross-validation would test whether models are
  recognising sources. 6: the 0.92 human baseline comes from the two people who compiled the data.

**C5. ASMR-Bench (research sabotage, Redwood)** · 2/2/2 · **Finding (statistical)**
- Source: [arXiv 2604.16286](https://arxiv.org/abs/2604.16286);
  [code](https://github.com/ejcgan/auditing-sabotage-bench) MIT.
- [`findings/asmr-bench-best-of-nine/`](findings/asmr-bench-best-of-nine/), at commit `f8efd68`:
  - 1 (ruled out by the paper): the paper-only condition is at chance (0.34–0.64).
  - 6 (holds): the 0.77 headline (exact single-configuration p = 0.009) is the best of nine model
    and affordance configurations on 9 papers; the family-wise p for the best of nine is 0.084.
    The bootstrap interval over papers is 0.61–0.95.
  - 0: the released paper-only CSVs include 55 persuasion rows that the other CSVs exclude and
    the repository's loader does not filter (paper-only AUROCs shift by up to 0.03).

**C6. School of Reward Hacks and rh-bench** · 2/3/1 · **Finding (rh-bench)**
- Source: [arXiv 2508.17511](https://arxiv.org/abs/2508.17511),
  [data](https://huggingface.co/datasets/longtermrisk/school-of-reward-hacks) CC-BY-4.0;
  [rh-bench](https://huggingface.co/datasets/ktolnos/rh-bench) CC-BY-SA-4.0.
- [`findings/rh-bench-label-shortcuts/`](findings/rh-bench-label-shortcuts/), at rh-bench `1045a73`
  and SoRH `d7e04a5`:
  - 1, 7 (holds): in rh-bench's largest source (Jozdien realistic_reward_hacks, 1,605 rows) the
    label is fixed by which prompt set a row came from; a prompt-only bag-of-words scores AUROC
    0.997. Response-only bag-of-words scores 1.000 on it and on Countdown-Code; SoRH hacks beat their
    matched controls in 97.8% of held-out pairs (null 0.48–0.51).
  - 0 (holds): 268 of rh-bench's 286 MALT "clean" rows, all marked `verification: human`, are
    Claude 3.7 Sonnet runs, a model with no human-reviewed benign run in MALT's own card.
  - 0: the open-ended file has 4,151 rows against the card's 4,359 (MALT 572 against 780), and
    re-serves gated MALT and TRACE content ungated (counted from metadata only here).

**C7. Lower priority or blocked**
- **TRACE** (Patronus, [arXiv 2601.20103](https://arxiv.org/abs/2601.20103)): gated; check whether
  the prompt to hack survives in the trajectories (7). 2/3/2.
- **Natural emergent misalignment from reward hacking** ([arXiv 2511.18397](https://arxiv.org/abs/2511.18397)):
  no data. It counts `sys.exit(0)` before the asserts as a hack, while ImpossibleBench's monitor
  prompt calls giving up fine. The same act gets opposite labels in the two benchmarks. 3/2/3.
- **Reward Hacking Benchmark** ([arXiv 2605.02964](https://arxiv.org/abs/2605.02964)), **research-agent
  reward hacking** ([arXiv 2609.28614](https://arxiv.org/abs/2609.28614)): no data found. 2/2/3.
- **Hack-Verifiable Environments** ([arXiv 2605.20744](https://arxiv.org/abs/2605.20744), MIT):
  planted shortcuts are also evaluation tells. 1/2/2.

---

## Next audits

The fan-out recorded in [`coverage.md`](coverage.md) checked every benchmark ranked here and in
[`scope.md`](scope.md), plus major safety evaluations used in system cards. The four gated datasets
(MALT, evaluation awareness, Liars' Bench, TRACE) were checked at row level after the user accepted
their gates. Benchmarks without released outputs (Async Control, CoT Red-Handed, the OpenAI
monitorability evaluations) were checked in code. Most findings mark their effect on published
numbers untested; settling those needs model runs, listed in each finding's README.
