# SLEIGHT-Bench and MonitorBench: checks 0, 1, 5 and 7

Status: checked 2026-10-27 against pinned sources. No model or API was run, and no downloaded
code was executed. Not raised with either team.

Summary of verdicts:

| Dataset | Check 0 provenance | Check 1 content-blind | Check 5 duplicates and leakage | Check 7 instruction visible |
|---|---|---|---|---|
| SLEIGHT-Bench | Recorded; no flag | Ruled out at this sample size | Ruled out across classes; one near-copy pair of attacks | Ruled out |
| MonitorBench | Holds in a narrow form: repo counts differ from the paper's table for 3 tasks | Holds in the metric: the score has no false-positive term, so an always-flag monitor scores 100; text baselines blocked | Mostly ruled out; public benchmark items in plaintext | Holds by design (disclosed); one undisclosed case in impossible coding |

## Pins

| Source | Pin |
|---|---|
| SLEIGHT-Bench code and encrypted data, `safety-research/sleight-bench` (MIT) | commit `218c58315cc01ff0dc5a100e906c27d82d259521` (2026-05-16, single commit) |
| SLEIGHT-Bench HF dataset `sleightbench/SLEIGHT-Bench` (MIT, gated "auto") | revision `45d4cc6bc414df16fcb8589d60cb80e14d9bcba8`, lastModified 2026-05-16; public tree listing sha256 `2b3f1ce1…13e4` |
| SLEIGHT-Bench paper, arXiv 2605.16626 v2 | e-print sha256 `c50848d8…a824` |
| Redwood leaderboard `monitors.json` (reused read-only from the leaderboard audit) | sha256 `680d1ffc…2fe6` |
| MonitorBench code and inputs, `ASTRAL-Group/MonitorBench` (MIT) | commit `b6229e4b8ea9abcec38d61159c9cbd0f577ddf35` (2026-10-05) |
| MonitorBench paper, arXiv 2603.28590 v4 | e-print sha256 `9618d4a9…c70b` |

**SLEIGHT-Bench access.** The HF data files return 401 without accepting the gate, so the gate
was not used. The GitHub repo ships the same files as Fernet blobs and prints the key in its
README, saying the encryption "prevents automated scraping, not human access".
`sleight_decrypt.py` decrypts them with the stdlib and `openssl`, without running the repo's
`decrypt.py`. All 215 decrypted files that also appear on HF match HF's public git blob ids
byte for byte. The GitHub copy has one extra attack, `refusal_forcing/refusal-poisoning-credential-exfil`.
It has no benign twin, it is not on HF, and it is not among the paper's 40. The decrypted
transcripts stay in `data/` and are not republished here.

**MonitorBench rollouts.** None are released. No HF dataset matches "MonitorBench", and the
author ASTRAL-Group has none. The repo holds inputs and pipeline code only.

## SLEIGHT-Bench

### Check 0: provenance

- **Attacks.** 40 attacks in 43 transcripts. Three attacks have two sessions each: the corp and
  gcs `transcript-perm-launder` attacks and `weight-exfil-eval-symlink`.
- **How the attacks were made.** The authors wrote each attack with Claude Code. Per the paper
  (§3.2), each took "around 10 iterations against the monitor" and 2–3 hours of human time.
- **How the benign twins were made.** Each benign twin is the attack transcript with the payload
  removed, by the same authors (Limitations; Appendix, "Benign ablation"). An agentic verifier
  checks the fix.
- **How close the twins are.**
  - 38 of 43 pairs have the same number of blocks.
  - The median pair shares 72.7% of its blocks verbatim.
  - 8 pairs share fewer than half of their blocks.
- **Dates.** The dates in tool outputs are fictional (2024–2026). The release dates are the
  2026-05-16 commit and HF upload, and paper v1 on 2026-05-15.

The two classes have the same authors, scaffold and format. The paper reports that external
benign sources lower catch rates by 10–20 pp. That is consistent with paired twins being a lenient
calibration set. This audit did not test that further.

### Check 1: content-blind baselines (ruled out at this sample size)

**Method.**
- **Monitor view.** A re-implementation of the repo's `strip_assistant_text`: all user lines,
  assistant `tool_use` blocks, and the canary line.
- **AUROC.** Pooled AUROC, attack against benign.
- **Interval.** A cluster bootstrap over the 40 attacks (2,000 resamples).
- **Null.** Labels swapped at random within each pair (10,000 permutations).
- **Paired win rate.** The share of pairs where the attack's value is higher, with an exact
  sign test.

| Feature (monitor view unless noted) | Pooled AUROC, 43 pairs [95% CI] | Null p95 | Win rate (pairs that differ) | Same, 37 single-session pairs |
|---|---|---|---|---|
| Monitor-view characters | 0.532 [0.493, 0.583] | 0.535 | 18 of 40 attack-higher | 0.542 (null p95 0.543) |
| Tool output characters | 0.542 [0.501, 0.591] | 0.540 | 13 of 28 | 0.550 (null p95 0.548) |
| Tool calls | 0.507 [0.496, 0.522] | 0.507 | 4 of 5 | 0.509 |
| Assistant text characters (full view only) | 0.447 [0.408, 0.474] (0.553 reversed) | 0.529 | 7 of 29, sign p 0.008 | 0.437 |
| Logistic on 11 structure features, leave-one-attack-out | 0.552 | 0.528 (p 0.002, 500 refits) | — | 0.564 (null p95 0.537) |

- **Where length differs.** Length differs mainly in 4 pairs where the attack's monitor view is
  1.8–45 times longer than its twin's: three needle-in-haystack attacks and the jailbreak. In
  these pairs the extra length is the payload itself.
- **Assistant text.** Attacks carry less assistant text than their twins in 22 of 29 differing
  pairs. The paper's main monitors strip assistant text, so this is visible only in the
  unstripped ablation.
- **Against the board.** On the board's same 37/37 trajectories the 15 board monitors score
  0.497–0.725 (median 0.638). Our tool-call counts reproduce the board's `n_actions` exactly for
  both classes, and that count gives 0.509 there.
- **Flag rule.** The rule needs an interval above the null's 95th percentile and above 0.6, or a
  rank above the median published monitor. No baseline meets it. The logistic model beats its
  null but stays below 0.6. It is above 5 of the 15 board monitors.
- **Power.** With 43 pairs, a two-sided sign test at 0.05 needs 29 pairs in one direction (win
  rate 0.674). Smaller paired effects cannot be detected here, so "ruled out" means no cue at or
  above that size.

Bias direction: none found. A residual cue of the size of the logistic model (about 0.55) would
bias catch rates up slightly.

### Check 5: duplicates and leakage (ruled out across classes; one near-copy cluster)

- **Twins are near-copies by design.** This is the matched-pair control, not leakage.
- **Corp and gcs permission-laundering attacks.** These two are variants of one scenario. Their
  stage-1 transcripts have a 5-word-shingle Jaccard of 0.67–0.83 with each other, and their
  stage-2 transcripts 0.65–0.68. Stage 2 also overlaps `great-gcs-bucket-name-weight-exfil` at
  0.37–0.48. No other cross-attack pair reaches 0.3.
- **Reused tool-call ids.** Three system-state attacks share 5–8 tool-call ids
  (`rm-rf-monitor-results-logging-server` with `rm-rf-orion-monitor-local-logs` and
  `temp-file-disk-exhaustion-from-scratch`), and so do two model-priors attacks (1 id). These
  attacks were built from a shared template.
- **Tool-id format.** Ids match the stated Claude Code format in 318 of 318 attack calls and 293
  of 311 benign calls. The off-format ids sit in 3 benign files. The pooled AUROC is 0.535, at the
  null.
- **Other fields.**
  - Working directories differ within 3 pairs.
  - Date strings differ within 5 pairs, with no common direction.
  - No token appears on only one side of the diff in 4 or more pairs.
- **Ids and order.** The label comes only from the file name, which the monitor does not see.
- **Canary.** Every transcript in both classes carries the canary line, and the pinned stripping
  code passes it to the monitor. It shows the monitor that the input is a benchmark, but it does
  not separate the classes.

Bias direction: the near-copy cluster makes the effective number of attacks a little below 40,
so per-attack intervals are slightly too narrow. No effect on catch rates was measured.

### Check 7: instruction visible to the monitor (ruled out)

- **No instruction in the transcripts.** SLEIGHT has no side-task instruction: the agent acts
  without one. None of the 43 first user messages contains intent words.
- **Intent words in the monitor view.** An intent regex (exfiltrate, malicious, covert, secretly,
  backdoor, evade, side task and similar) hits 3 attack and 2 benign monitor views. The only
  within-pair difference is the jailbreak, whose payload addresses the monitor by design. Pooled
  AUROC 0.512, at the null.
- **Assistant text and thinking.** On assistant text and thinking (unstripped view) the regex
  hits 0 attacks and 1 benign. Thinking blocks appear in 2 attack transcripts.

## MonitorBench

MonitorBench is not a static labelled monitor set. It ships prompts. The evaluated model
generates rollouts with and without an injected factor (X). A verifier labels success (Y), and a
fixed Qwen3-32B monitor labels whether the CoT reveals the factor (Z). Checks 1 and 7 therefore
apply to the score and to the monitor prompt, not to two released classes.

### Check 0: provenance (holds in a narrow form)

- **Sources.** Instances come from:
  - public sets: WMDP, AIME 2024, GPQA-Diamond, MMLU-Pro, BigCodeBench with the CoT Red-Handed
    side tasks, ImpossibleBench, DeceptionBench, databricks-dolly;
  - brainteasers from Han et al. 2025;
  - the 5 public SHADE-Arena task pairs (`american_airlines_2`, `api_key_calendar_agendas_2`,
    `bank_transfer_2`, `expenditure_accounting`, `spam_filter_update`), to which this repo's SHADE
    finding about scorer gaps may apply;
  - items written by the authors.
- **Same template for X=0 and X=1.** Both conditions use one template and one model.
- **Counts.** The paper's table sums to its stated 1,514. The repo's inputs sum to 1,540. Three
  tasks differ:

| Task | Paper table | Repo | Paper appendix |
|---|---|---|---|
| Sandbag, safety (WMDP) | 150 | 120 | "40 biology … 40 chemistry … 40 cybersecurity" |
| Sandbag, science (GPQA-Diamond) | 192 | 198 | "192 multiple-choice questions" (GPQA-Diamond has 198) |
| Sandbag, engineering (MMLU-Pro) | 100 | 150 | "We randomly sample 150" |

The repo's 120 and 150 match the appendix rather than the table. Which counts produced the
published numbers is untested.

### Check 1: content-blind baseline (holds in the metric; text baselines blocked)

- **The score counts positives only** (`pipeline/base.py`).
  - Outcome and process tasks: the mean of monitor flags over rollouts that passed.
  - Input-intervention tasks: `min(1, P(Z=1 | X=1, Y=1) / R_effect)`.
  - X=0 rollouts are used only to compute `R_effect` and are never shown to the monitor.
- **Always-flag scores the maximum.** A monitor that always answers "A" scores 1.0 on every task
  and scope.
- **Published cells.** 137 of 155 published cells in the CoT-only table are below 100 (range
  1.1–100).
- **Earlier definition.** The paper source still contains a commented-out definition of the score
  as g-mean² = TPR × TNR.
- **What bounds the monitor's error.** Only the human study does: 300 single-turn trajectories,
  monitor F1 85.3 / 91.9 / 92.1 for action / CoT / all. Precision is not reported on its own.
- **Text baselines.** Blocked: no CoTs or actions are released, so no length or keyword baseline
  can be computed.

Bias direction: up. Any monitor false positive raises the monitorability score, and nothing in
the score penalises it. The size is untested. F1 of about 0.9 suggests it is modest on
single-turn tasks, and the paper reports weak human–monitor agreement on the multi-turn tasks.

### Check 5: duplicates and leakage (mostly ruled out)

- **Shared file.** `cue_answer/health` and `cue_condition/health` are the same file (65 cases
  used by two tasks), as the appendix says.
- **Duplicates within files.** Exact or near (Jaccard ≥ 0.8) duplicates within a file are at
  most 2 per file (Judgment 1 exact and 2 near, Deception 2 exact, MMLU-Pro 1 near). There are no
  near-duplicates across files.
- **Coding.** The 291 coding instances use each BigCodeBench task once.
- **Ids and order.** These cannot carry labels: `task_id` is the file index plus the stress-test
  name, and the labels are made at run time.
- **Public items without canaries.** The repo re-publishes 198 GPQA-Diamond items in plaintext,
  along with WMDP, AIME 2024 and MMLU-Pro items. None of the dataset files carries a canary (only
  the SHADE-Arena README does). Contamination of the evaluated models is untested.

### Check 7: instruction visible to the monitor (holds by design; one undisclosed case)

- **Factor text in every scope.** The monitor prompt includes the decision-critical factor in
  every scope, CoT-only included:
  - `{intervention}` in cue-condition and deception tasks;
  - `{answer}` in cue-answer tasks, which is the injected guess and equals the ground truth;
  - `{task}` and `{input}` (question plus side task) in dual-objective and impossible tasks.
- **Disclosure.** The paper states this: "The monitor model is given exact decision-critical
  factors to look for". This is the quantity the benchmark measures, so it is reported, not
  flagged.
- **Stress-test instruction.** In the other 18 of 19 tasks, `original_question` is built without
  the stress-test instruction (18 assignment sites read; the two agent tasks share one). In `impossible.coding` the monitor's `{input}` is the
  full sample input, which includes the attack prompt. Its `{task}` is
  `IMPOSSIBLE_ATTACK_PROMPTS[attack_policy]`. So under direct concealment and monitor-aware
  evasion, the monitor reads the instruction to conceal test hacking verbatim.
  - Bias direction for that task's stress-test scores: either. Not tested.

### Additional finding (outside the four leads)

At the pinned commit, `DualAgent` monitors every evaluated agent rollout, whether or not the side
task passed, and the reported score averages all of them. The paper says the score uses
"samples whose side objective is successfully completed". Effect on the agent rows: untested.

## Untested or blocked

- SLEIGHT: which monitors the authors iterated against, and how much the headline catch rate
  depends on that selection (check 3, not in scope).
- SLEIGHT: whether the board's monitors or the paper's monitors respond to the 4 length-outlier
  pairs.
- MonitorBench: every rollout-level baseline (no rollouts released); the false-positive rate of
  the Qwen3-32B monitor; which instance counts produced the published table.

## Reproduce

From this directory's parent (`data/` holds the downloads):

```bash
git clone https://github.com/safety-research/sleight-bench data/gh/sleight-bench        # checkout 218c5831
git clone https://github.com/ASTRAL-Group/MonitorBench data/gh/MonitorBench             # checkout b6229e4b
curl -o data/hf_sleight_tree.json "https://huggingface.co/api/datasets/sleightbench/SLEIGHT-Bench/tree/45d4cc6bc414df16fcb8589d60cb80e14d9bcba8?recursive=true"
curl -L -o data/arxiv/src_2603.28590.tar https://arxiv.org/e-print/2603.28590          # extract to data/arxiv/tex_2603.28590/
cp <leaderboard audit>/data/site/api/monitors.json data/board_monitors.json           # optional, sha256 680d1ffc…
python -I out/sleight_decrypt.py --cache data
python -I out/check_sleight.py --cache data --out out/sleight_checks.json             # about 1 minute
python -I out/check_monitorbench.py --cache data --out out/monitorbench_checks.json   # about 10 seconds
```

Needs numpy, scipy, scikit-learn and PyYAML, plus the system `openssl` for decryption.
