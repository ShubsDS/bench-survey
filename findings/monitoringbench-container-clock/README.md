# MonitoringBench with MonitoringBenchHonest: the label is readable without the attack

Status: draft, 2026-10-27. Checks 0 and 1 hold on the 1,100-run paired set. Whether the published
monitors use these cues is **untested** (no per-run monitor scores on the honest side are released).
The paper's own 416 honest runs are not released, so its headline catch rates cannot be checked
here (**blocked**). Not raised with the authors.

## Background

MonitoringBench (Jotautaitė, Martinez, Matthews, Tracy, [arXiv 2605.09684](https://arxiv.org/abs/2605.09684))
releases 2,644 successful BashArena attack trajectories and no honest runs. Küçükkurt and Elasky
later published 550 benign Claude Opus 4.5 trajectories matched per task to 550 of those attacks
([post](https://www.lesswrong.com/posts/bdBoH23TCTFZkkfqp/releasing-benign-trajectories-for-monitoringbench),
[pipeline](https://github.com/CanKucukkurt/monitoringbench-honest-pipeline)). Their public Docent
collection holds both classes, exported by one script, with `submit` calls removed and the bash
argument key renamed so both classes render the same. Their post reports TPR and FPR for six
monitors on these 1,100 runs. The post states that step counts and lengths were not matched.

## Pins

| Source | Pin |
|---|---|
| Attacks, `neur26anonsub/ctrldataset2026` (CC BY 4.0) | HF commit `6c72cf19883376b921a94a0dd17dc8ab6b25e52f`; `master.parquet` sha256 `5fd4c38b…8c91` |
| Paired set, Docent collection `fce5f309-4750-4b2e-a172-7bf897807278` (public read, no licence stated) | No revision system; content sha256 `36599681bb48…1d73` over (id, messages) of all 1,100 runs, fetched 2026-10-27 |
| Honest pipeline code (read as text, not run) | `CanKucukkurt/monitoringbench-honest-pipeline` commit `7f8deb9a6b5551cd8c15692d9b96c0812e8dd4a9` |

The honest data has no licence, so this directory reports counts, AUROCs and ids only.

## Check 0: provenance census

| | Attack (550) | Honest (550) |
|---|---|---|
| Executor model | Claude Opus 4.5 (all 550, from `master.parquet`) | Claude Opus 4.5 (post) |
| Rewriting | 505 of 550 are "Refined": tool calls rewritten by Opus 4.6 after the run (paper, Appendix H) | none |
| Team and prompt | paper authors; attack system prompt with a strategy | Küçükkurt and Elasky; `honest_matched.txt` plus a per-step reminder |
| Generation date | `eval_created` 2026-01 (17), 2026-02 (289), 2026-03 (244) | July–August 2026 (from tool-output timestamps; post dated 2026-09-02) |
| Selection | kept only if the side task succeeds; refined attacks also had to lower suspicion for 2 of 3 dev monitors | 12 runs a frontier monitor scored above 6 were replaced |
| Tasks | 116, equal counts per task in both classes | same |

The base model is the same in both classes. Team, prompt, generation date and, for 92% of attacks,
a second author (the Opus 4.6 rewriter) differ.

A correction from the companion audit
([`../monitoringbench-release-selection/`](../monitoringbench-release-selection/)): 122 of the 550
paired attacks are refinements of attacks run by Claude Opus 4.6, yet `master.parquet` labels every
refined row `claude-opus-4-5`. The paper names the refiner as Opus 4.6 in §2 and as Opus 4.5 in
Appendix H.2. So the executor label is not reliable for the refined rows, and the classes are not
model-matched for at least those 122.

## Check 1: content-blind baselines

GroupKFold (5) by BashArena task. Nulls permute labels within task and refit the whole pipeline
(1,000 permutations; 200 for bag-of-words). Intervals are a task-cluster bootstrap.

| Baseline | Monitor view it needs | AUROC [95% CI] | Null p95 | TPR at 1% FPR |
|---|---|---|---|---|
| Container clock: count of `ls -l` timestamps in Dec–Mar minus Jun–Sep | tool outputs | 0.998 [0.994, 1.000] | 0.531 | 1.000 |
| Logistic regression on tool-call counts and lengths (10 features) | tool calls only | 0.867 [0.827, 0.909] | 0.530 | 0.169 |
| Same plus output lengths | tool outputs | 0.883 [0.848, 0.917] | 0.531 | 0.340 |
| Fraction of calls that are `text_editor` (single feature) | tool calls only | 0.678 [0.634, 0.726] | 0.522 | 0.149 |
| Step count (single feature) | tool calls only | 0.620 [0.559, 0.681] | 0.522 | 0.000 |
| Bag-of-words on actions before the attack step; honest prefix cut to the paired attack's length (1,066 runs) | tool calls only | 0.937 [0.916, 0.957] | 0.526 | 0.443 |
| Bag-of-words on all actions (reads the attack; reference) | tool calls only | 0.986 [0.978, 0.993] | 0.527 | 0.829 |

1,064 of 1,100 runs (517 attack, 547 honest) contain at least one `ls -l` style timestamp. Attack
outputs show February and March; honest outputs show July and August. The container clock records
when each class was generated.

The structure model's largest weights are on `text_editor` sub-commands: honest runs average 2.49
`str_replace` calls, refined attacks 0.67, unrefined (Recon) attacks 1.83. Refined attacks also
make no `python` calls (honest 0.34 per run).

The pre-attack bag-of-words is not fully content-blind: the attacker knows its side task before
the attack step and may prepare for it. Its highest-weight tokens are mostly tool-usage words
(editor sub-commands and argument names on the honest side, heredoc and `mkdir` on the attack
side) rather than side-task targets; the share of prefixes naming `sudoers`, `api_tokens` or
`shadow` is within 0.01 between classes, but `whitelist` appears in 24% of attack prefixes and 13%
of honest ones, so some side-task preparation is in the prefix.

### Against the published monitors on the same 1,100 runs

TPR of each baseline at each monitor's own FPR (monitor TPR from the post):

| Monitor (FPR) | Monitor TPR | Structure, calls only | Structure + output lengths | Pre-attack BoW | Clock |
|---|---|---|---|---|---|
| Kimi K3 (0.024) | 0.858 | 0.418 | 0.522 | 0.647 | 1.000 |
| DeepSeek V4 Flash (0.031) | 0.485 | 0.431 | 0.555 | 0.700 | 1.000 |
| Qwen3.5 4B (0.076) | 0.147 | 0.604 | 0.676 | 0.799 | 1.000 |
| Qwen3.6 Flash (0.118) | 0.611 | 0.709 | 0.738 | 0.842 | 1.000 |
| Qwen3.8 27B (0.204) | 0.860 | 0.820 | 0.813 | 0.908 | 1.000 |
| GPT 5.6 Luna (0.315) | 0.925 | 0.862 | 0.875 | 0.944 | 1.000 |

At the monitors' operating points the calls-only structure model beats 2 of 6 monitors, the
structure model with output lengths beats 3, the pre-attack bag-of-words beats 5 (all but Kimi K3),
and the clock beats all 6. The flag rule of check 1 (interval above the null's 95th percentile and
above 0.6, or ranks above the median published monitor) is met by every baseline in the table
except step count, whose interval reaches 0.559.

The paper reports catch rates at 1% FPR (Opus 4.5 about 70% full-trajectory on the final
benchmark) against its own 416 honest runs. Those runs are not released, so the same baselines
cannot be computed against the paper's thresholds.

## Check 2: one-class swap

No swap was run; it needs regenerating one class. What the data shows:

- Model identity is ruled out as the separating author on the paired set: both classes are
  Opus 4.5.
- The remaining authorship differences (prompt, team, generation date, Opus 4.6 rewriting) leave
  measurable marks. Refined attacks are further from honest runs on the tool mix than unrefined
  attacks are (`str_replace` 0.67 vs 1.83 vs honest 2.49; structure AUROC against all honest runs
  0.871 for 505 refined, 0.808 for 42 Recon). The Recon group is small and has no interval.
- Whether monitor scores move with these marks is untested.

## What it means

On the paired set the class label can be read from when and how the trajectory was produced:
the container date in tool outputs separates the classes almost perfectly, and the mix of tool
calls alone reaches 0.87. Küçükkurt and Elasky's monitor prompt renders each step's action and
output (`pipeline/mb_io.py`, `render_transcript`), so the date is in their input; the paper's full-trajectory monitor sees tool calls only, so only the structure cue
applies there. A monitor that scores well here may partly be scoring "generated in early 2026 by
the red-team pipeline" rather than the attack. If monitors use these cues, the benchmark's TPR at
a fixed FPR overstates sabotage detection, and a safety estimate built on it is biased **up**.

## Tests that would settle it

1. Rewrite the `ls -l` dates in both classes to one fixed date and rescore the six monitors; any
   TPR change at fixed FPR is the clock's contribution.
2. Score the monitors within strata of the structure model's score (or on honest runs resampled to
   match the attacks' tool mix) and compare TPR at fixed FPR.
3. Regenerate honest runs with the attack pipeline's prompt minus the side task, at the same time
   and image, and compare monitor AUROC against these 550.

## Reproduce

```bash
python -I check_monitoringbench_baselines.py --cache data
```

Downloads `master.parquet` (3 MB) from the pinned HF commit and the 1,100 Docent runs (59 MB),
then writes `monitoringbench_checks.json`. About 8 minutes on a laptop CPU. Needs numpy, pandas,
pyarrow and scikit-learn. Docent has no revisions: compare `pins.docent_content_sha256` in the
output with the value above.
