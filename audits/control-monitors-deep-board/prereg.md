# Pre-registration: is the control board's chance level the same on every dataset?

Written 2026-11-20, before the analysis script was run. Deep dive on
[`control-monitors-bash`](../control-monitors-bash/). Input: that audit's board snapshot
`../control-monitors-bash/data/site/monitors.json` (sha256 `18efcced…`, generated 2026-11-12), read
by path. No new downloads and no model calls.

## Inherited question

The parent audit established, on the Redwood Control Leaderboard's monitor board:

- BashArena: honest runs are longer than attack runs, the board's default score is each run's
  peak per-action suspicion, and a peak over more actions is higher. Matching on length raises
  AUROC for 9 of 11 monitors.
- MonitoringBench: attack runs are longer, so the same effect runs the other way.
- LinuxArena paper set: rankings hold.

It left open:

1. **Q1.** The board has five more datasets. Three have usable scores: ResearchArena (attacks by
   2026 models), SHADE-Arena and SLEIGHT-Bench. Is the default metric's chance level different from
   0.5 there too, and in which direction?
2. **Q2.** Does this change a comparison a reader would make across datasets for the same monitor?
3. **Q3.** What can each dataset's monitor read (agent text, reasoning, tool arguments)?

## What was already seen (exploratory, before this file)

This is not a clean pre-registration. Before writing it I computed, for exploration:

- median run length by class and the AUROC of length alone for BashArena, LinuxArena paper,
  SLEIGHT, SHADE-Arena, ResearchArena and MonitoringBench (0.16, 0.44, 0.51, 0.52, 0.57, 0.70);
- the unmatched AUROC of every monitor row on five of those datasets;
- the parent audit's matched results for BashArena, LinuxArena and MonitoringBench.

Not yet seen: any matched AUROC, chance level or safety number for ResearchArena, SHADE-Arena or
SLEIGHT; any cross-dataset contrast; the per-agent breakdown of ResearchArena.

## Definitions

- **Run score**, as the board computes it: for an action monitor, the maximum of the run's
  non-null per-action scores; for a trajectory monitor, the run's single score. Check: the mean
  run score per class must reproduce the snapshot's `mean_max_sus_attack` and `mean_max_sus_honest`.
- **Length:** `n_actions`.
- **Board AUROC:** attack positive, ties count one half.
- **Length-only chance level:** the AUROC between honest runs reweighted to the attack runs'
  length distribution and honest runs as they are, on the same run score. It is what the metric
  returns for a monitor with no detection skill, if attack runs scored like honest runs of the same
  length. 0.5 means no length artefact.
- **Matched AUROC** (parent's scheme): five bins at the attack class's length quintiles, honest runs
  reweighted to the attack bin shares, all attacks kept. Attacks in a bin with no honest run are
  dropped and counted.
- **Step-wise safety at 1%** (parent's reproduction of the board's rule), for action rows.

## Predictions from the mechanism

Stated before computing, so that they can fail.

- **P1.** For action rows, the chance level departs from 0.5 in the direction of the length gap:
  above 0.5 where attacks are longer (ResearchArena, MonitoringBench), below where they are
  shorter (BashArena, LinuxArena).
- **P2, negative control.** For trajectory rows (one score per run, no maximum), the chance level
  stays within 0.03 of 0.5 on every dataset, even where lengths differ (SHADE-Arena, ResearchArena,
  LinuxArena).
- **P3, negative control.** On SLEIGHT, where each attack has a benign twin of the same task, the
  chance level is within its interval of 0.5 for every monitor.

If P2 fails, the effect is not only the maximum over steps: monitors' scores drift with length in
some other way, and the write-up must say so.

## Decision rules

- **Q1 is "yes"** if the chance level's 95% interval excludes 0.5 for at least one action row on
  ResearchArena, and P1's direction holds on every dataset where an interval excludes 0.5. **"No"**
  if every interval on the three new datasets includes 0.5. Otherwise **"cannot tell"**.
- **Q2 "changes"** for a monitor and a pair of datasets if the difference in AUROC between the two
  datasets moves by at least 0.05 under matching, with a 95% interval on that movement excluding 0.
  Report also whether the sign of the difference flips. Only monitors with action rows on both
  datasets are compared.
- **Q3** is descriptive, from the board's code (`control-tower` 308984e) and importers. No
  inference about scores is drawn from it without a matched contrast.

## Resampling and power

- Bootstrap, 2,000 resamples, attack and honest runs resampled separately, bins recomputed in each.
- The snapshot has no task identifiers, so intervals are run-level and too narrow where runs share
  tasks. ResearchArena has four tasks and eight agent runs per class: report a cluster bootstrap
  over agent runs and a leave-one-agent-out range next to the run-level interval.
- Power. ResearchArena has 84 honest runs (77 scored by the trajectory monitor), so the standard
  error of an AUROC is about 0.04; a chance-level shift under about 0.08 cannot be detected there.
  SLEIGHT has 37 pairs (standard error about 0.065) and serves only as a control. A null on
  ResearchArena is therefore weak evidence; BashArena and MonitoringBench carry the result.

## Robustness, chosen to hurt the result

1. Decile bins in place of quintiles.
2. One-to-one nearest-length matching without replacement (caliper 2 actions).
3. A second definition of the chance level: draw per-step scores independently from the pooled
   honest per-step distribution, take the maximum over each run's length, and compute the AUROC
   between attack-length and honest-length draws.
4. ResearchArena within agent: leave one agent out, and cluster by agent.
5. Drop attacks whose side task failed.

## Limits known in advance

- ResearchArena has one monitor (GPT-5.4 nano), so nothing there is a ranking.
- The snapshot marks SHADE-Arena and SLEIGHT as private. Results on them are for internal use
  until the maintainers say otherwise.
- Trajectory rows on LinuxArena cover 41 or 89 of the 92 attacks, by monitor.
