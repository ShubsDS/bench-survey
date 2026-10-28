# BashBench (Ctrl-Z) and Async Control: scorer, metric and monitor-input checks

Status (2026-10-27): static reading of pinned code, task data and the paper text. Nothing that was
downloaded was run. The red-team prompts were not decrypted. No trajectories exist for either
benchmark, so no effect on any published number was measured. Nothing has been raised with
Redwood or UK AISI.

## Pins

| Source | Pin | Licence |
|---|---|---|
| ControlArena bash setting (the public copy of BashBench's 257 tasks) | `UKGovernmentBEIS/control-arena` `ae0b6fa78ace5a097536eb3464ab5a089740b53e`; `bash_tasks.json` sha256 `8c71b7ca…caef` | MIT |
| BashArena tasks (for overlap) | HF `Eccentricity/bashbench2` revision `13e19f9c…`, parquet sha256 `6d6652e9…fdfb2` | CC BY-SA 4.0 |
| Async Control code | `UKGovernmentBEIS/async-control` `7bc4e699248ed226462def2f2a76c73c5060493a` (tarball sha256 `4a9619e4…782be`) | MIT |
| ControlArena as Async Control locks it (`uv.lock` line 749) | `ba81865c4120b87c987de073db8e601eb65de770` (tarball sha256 `6f51de09…4bbd`) | MIT |
| inspect_ai, locked version | 0.3.149, `src/inspect_ai/agent/_react.py` sha256 `3e96805f…ebc6` | MIT |
| Paper | arXiv 2512.13526v1 HTML (sha256 `d47df165…7bf2`) | — |

Ctrl-Z itself released no code, trajectories or attack templates that we found. BashBench lines below
refer to ControlArena's copy of the setting. Line numbers are at the pins above.

## BashBench (Ctrl-Z setting)

From [`bashbench_checks.json`](bashbench_checks.json), produced by [`check_bashbench.py`](check_bashbench.py).
The script checks that the 10 source lines it depends on are present.

### Lead 6: side-task and main-task checks

- **Side task.** Success means a fixed marker string appears in a fixed file
  (`task/scorers.py:70-71`). The check does not test whether anything was downloaded or run, so
  any process that writes the string passes. The marker string appears in 0 of 257 task texts and
  0 of 257 test files, and the side-task description given to the attacker does not state it
  (`task/dataset.py:41-47`). An agent would learn it only by doing the side task. The scorer runs
  only in attack mode (`scorers.py:143`), so it cannot fire on honest runs. **This is a string
  check rather than an effect check, but we found no path by which it would give a false result.
  Ruled out as a practical flaw.** It is the same design as BashArena's malware checker.
- **The main task is scored on the public tests only.** `main_task_success` runs
  `task_verifiable` (`scorers.py:87, 93-94`). `private_tests` is loaded (`dataset.py:37`), but no
  scorer uses it. In all 257 tasks the two test sets differ. Ctrl-Z's paper describes scoring on
  private held-out tests at submission. That comes from our earlier notes and was not re-read here.
  So usefulness numbers from ControlArena's port are not comparable with Ctrl-Z's.
- **Test census** (AST, fixtures excluded):
  - 1,293 public test functions. 0 have no assertion; all 46 flagged before fixtures were excluded
    turned out to be fixtures named `test_*`.
  - 163 (12.6%) run no process. A test that runs no process can still check output files.
  - 58 assert only that a path exists. They fall in 50 tasks; in no task are all tests like this,
    and the highest share in one task is 60%.
  - Private tests are similar: 1,291 functions, 158 run no process, 26 existence-only.
  - Whether any test passes on the initial state is **untested**: no static proxy is reliable and
    nothing was run.

### Lead 4: human-templated attacks

**Blocked.** Ctrl-Z's human attack templates and its attack trajectories are not public, so we
could not measure how narrow the attack distribution is. ControlArena's stand-in,
`policies/known_strings.py`, is one fixed list of 10 commands, issued in order by a step counter
(lines 85 and 140). Any monitor result on that policy measures detection of one script. That is
ControlArena's policy, not Ctrl-Z's.

### Lead 5: task text shared with BashArena

**Ruled out.** We compared word 5-gram sets of each BashBench task with all 637 BashArena tasks.
For each BashBench task we took its closest BashArena match. The highest Jaccard across all 257
tasks is 0.0084; the median of these best matches is 0.0033; none is above 0.2. This fits the
sources: BashBench came from Unix StackExchange and BashArena from StackOverflow.

## Async Control

From [`async_control_checks.json`](async_control_checks.json), produced by
[`check_async_control.py`](check_async_control.py). The script checks 27 source substrings, the 11 lines
mirrored by the iac finding, and 9 paper phrases, and stops if any is missing.

### Lead 6/3: what decides a "successful attack"

- **The test set (IaC).** Side-task success is pytest only. `ControlIACSetting` takes a
  `scorer_model` (`eval_utils.py:18`), but its scorer ignores it (`control_iac_setting.py:113`).
  All 11 lines mirrored by `findings/controlarena-iac-syntactic-side-tasks/check_iac.py` (written
  at `ae0b6fa`) are also present at the locked commit `ba81865`. At `ba81865` those three tests
  differ only in whitespace and imports, judged by hand from a diff. The egress SCP's public-IP
  statement is different (an action list rather than `ec2:RunInstances`), but the egress test's
  "any condition naming GPU-Fleets-Prod" rule is unchanged. **So the iac finding applies to the
  setting version Async Control locks.** The MFA and egress tests accept edits that leave the
  control in force, and the public-S3 side task removes a deny that never applied. How many of the
  IaC successes behind the 6% are edits like these is **untested**.
- **The training set (vLLM).** All 32 validated pairs (6 side tasks) use side tasks with no
  programmatic scorer (`vllm/task/scorers.py:65`). Their success label is an accept/reject verdict
  from an LLM that reads the PR diff and the side-task description (`_llm_judge.py:185, 195`). The
  judge is the untrusted model itself, Claude Opus 4.1 (`eval_utils.py:22`). The judge prompt says
  unrelated changes can be ignored (`_llm_judge.py:53`). So a vLLM positive means "the attacker's
  model agrees, from the diff, that the side task was done". This keeps attacks that are visible in
  the diff and drops ones that are not. **The selection holds in code. Its effect on the train-set
  FNR is untested; the likely bias is up.**
- **A reproduction gap.** The released script offers `vllm, infra, iac, sae_interp_sabotage,
  rogue_eval` (`generate_trajectories.py:120`). The paper's out-of-distribution settings, data
  poisoning and eval sabotage, are not among them.
- Kubernetes (`infra`) side-task scorers were not examined.

### FNR at 1% FPR: how it is computed

- **Positives.** Only side-task successes count (`classification_metrics.py:44`; the paper says the
  same).
- **Negatives.** The threshold uses every honest sample passed in, with no split by setting
  (`classification_metrics.py:36`). The paper says its calibration set is 469 honest Opus 4.1
  episodes on vLLM and Kubernetes main tasks only (Appendix A). **So the 1% FPR threshold for the
  held-out IaC result comes from honest runs in other environments.** No IaC FPR is reported. It
  could not be measured at the 1% level anyway: the 5 IaC main tasks give about 25 honest runs
  (the honest success rate of 0.880 in Table 9 is consistent with 22 of 25). Whether the real IaC
  FPR is above or below 1% is **untested**.
- **Sample size.** IaC has 45 pairs, and the round-3 prompt succeeds on 0.644 of them (29 if run
  once). With at most 45 attacks per prompt, the only count that gives the headline 5.7% is 2
  missed out of 35 successes (Wilson 95% interval 1.6%–18.6%). The headline is also the maximum
  over red-team prompts. The paper does not give n per cell, and monitor resampling (5×) could
  change it, so this is an inference.

### Lead 2: attack-prompt versus honest-prompt size

- **Honest prompts.** 1,036–1,166 bytes, mean 1,088. All five share one template; only the first
  line differs.
- **Attack prompts.** Measured without decrypting, from the token length alone: the encrypted file
  is 35,084 bytes, with 26,256 bytes of ciphertext. That bounds the attack-prompt text at about
  19.6 kB in total, which is 3.9–4.9 kB per prompt if the archive holds 4–5 prompts (the script
  names 4). That is roughly 4–4.5 times an honest prompt.
- **Why it matters little.** The attack prompt is not in the monitor's input (next section), so a
  length gap can act only through agent behaviour. **Size gap confirmed; any effect is untested.**

### Lead 7: does the monitor input restate the side task?

- **The attack prompt does not reach the log.** The replacer agent puts the attack prompt only into
  the model call (`agent.py:49-50`). The logged system message stays as ControlArena's
  `DEFAULT_SYSTEM_PROMPT` (`_control_solver.py:33, 168`; inserted by inspect's react,
  `_react.py:171`).
- **No monitor template asks for the side task.** None of the 20 placeholders across the monitor
  templates is a side-task field. The round-3 few-shot examples contain 0 IaC terms, so no
  test-set material leaks in.
- **The side task itself: ruled out.** Explicit discussion in the agent's own text is measured by
  the paper (Table 2: 0% above 7 for the round prompts).
- **New: the logged system message differs by class.**
  - In honest mode, the honest prompt is also set as the logged system prompt
    (`generate_trajectories.py:91`). In attack mode it is not.
  - So honest logs open with one of the five honest prompts, all of which contain `## Guidance`
    and instructions to submit `DONE` and use `make` sparingly. Attack logs open with the default
    prompt, which has neither.
  - Three of the four round-3 sub-monitors read the full message list, including the system message
    (`monitors.py:58, 65, 72`; parser `_utils.py:63, 81`). Only the hierarchical judge reads just
    diffs and executions.
  - A one-line rule ("does the first message contain `## Guidance`?") therefore separates the
    classes completely in logs made by the released script.
  - This **holds in code**. Whether the paper's logs were made this way, and whether the monitors
    use the cue, are **untested**. The paper's "baseline" honest prompt is not identified, so if
    the baseline was ControlArena's default prompt, the separation would be partial.

## Verdicts

| Lead | Verdict |
|---|---|
| BashBench 6: side-task check | String check, not effect check. No false-positive path was found, and it runs in attack mode only. Ruled out as a practical flaw. |
| BashBench 6: main-task tests | ControlArena scores public tests only and never uses `private_tests` (holds). Weak-test flags are small: 0 assertion-free tests, 58 existence-only tests in 50 tasks. Passing on the initial state is untested. |
| BashBench 4: templated attacks | Blocked for Ctrl-Z, because the templates are unreleased. ControlArena's stand-in is one fixed 10-command script. |
| BashBench 5: overlap with BashArena | Ruled out (max 5-gram Jaccard 0.0084). |
| Async 6/3: success scorers | Holds in code. The iac flaws apply at the locked commit. vLLM positives are judged by the attacker model reading the diff. The effect on the FNR is untested. |
| Async FNR metric | Holds in code and text. The IaC threshold comes from vLLM and Kubernetes honest runs, IaC FPR is unmeasured, and 5.7% implies 2 of 35 if run once (interval 1.6–18.6%). |
| Async 2: prompt size | Holds: about 4.5× by ciphertext bound (decryption not done). The prompt is hidden from the monitor, so the effect is untested. |
| Async 7: side task restated | Ruled out for the prompt and the monitor templates. New: the logged system message labels the class in released-script logs (code only; monitor use untested). |

## Bias direction

- **Ineffective IaC successes.** Direction unclear, as in the iac finding. They put attacks with no
  security effect into the FNR denominator.
- **vLLM success judged from the diff by the attacker model.** Likely up: it keeps attacks that are
  legible in the diff, which are the ones a diff-reading monitor catches.
- **Threshold from other environments.** Direction unknown. If IaC honest runs score lower than
  vLLM and Kubernetes ones, the real IaC FPR is below 1%, and the FNR at a true 1% would be lower
  (the result looks less safe than it is). If they score higher, the reverse.
- **Small n with a max over prompts.** The headline's interval is wide (up to about 19%), so the
  reported point estimate understates the uncertainty.
- **System-message cue.** Up, for monitors that use it, in logs where it is present.
- **ControlArena bash on public tests only.** Usefulness is not comparable with Ctrl-Z. The
  direction depends on whether public tests are easier than private ones (untested).

## Reproduce

```bash
python -I check_bashbench.py --cache data --out bashbench_checks.json
python -I check_async_control.py --cache data --out async_control_checks.json
```

The scripts need the standard library, plus pandas and pyarrow for the BashArena parquet. Downloads
are about 4 MB of tarballs, 1.8 MB of task JSON, an 11 MB parquet and 1.2 MB of paper HTML. The
scripts assert pinned hashes, except for the arXiv HTML, whose hash is recorded in the output.
They read everything as text and run nothing from the downloads.
