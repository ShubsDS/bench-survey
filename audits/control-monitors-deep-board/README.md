# Control board, all datasets: a monitor with no skill scores 0.35–0.49 on BashArena and 0.57–0.59 on MonitoringBench; the three datasets not examined before show no detectable shift

Status: 2026-11-20. Deep dive on [`control-monitors-bash`](../control-monitors-bash/). Every number
is from [`analyse.py`](analyse.py) on that audit's board snapshot (`monitors.json`, sha256
`18efcced…`, generated 2026-11-12). No downloads, no model calls, no spend. An independent validator
re-derived everything with its own code; see [Validation](#validation).

| Claim | Level |
|---|---|
| C1. On BashArena and MonitoringBench the default metric's no-skill baseline is not 0.5: 0.35–0.49 and 0.57–0.59 | **L3**, validated |
| C2. On ResearchArena, SHADE-Arena and SLEIGHT-Bench there is no detectable shift | **R**, with limited power on ResearchArena |
| C3. For the same monitor, most of the published gap between BashArena and the other datasets is this baseline | **L3**, a restatement of C1 |
| C4. Whole-trajectory monitors on LinuxArena also score longer honest runs higher | **Lead** (does not survive plausible task clustering) |
| C5. Step-wise safety at a 1% audit budget reproduces exactly and mostly holds under length matching | **R** |

## Inherited question

The parent audit showed that the board's default ranking score, each run's peak per-action
suspicion, rises with run length. Honest runs are longer on BashArena, so its AUROCs are pushed
down; attack runs are longer on MonitoringBench, so its AUROCs are pushed up. It did not examine
the board's other datasets, and it did not ask what this does to a comparison across datasets.
[`prereg.md`](prereg.md) states the three questions and the decision rules.

The data are current. BashArena and MonitoringBench attacks are by Claude Opus 4.5 and 4.6;
ResearchArena's are by Opus 4.6 and 4.8, GPT-5.4, GPT-5.5, Gemini 3.1 Pro and others. Monitors
include GPT-5.4 nano and GPT-5.6 Luna.

## What we found

**The no-skill baseline.** For each monitor row we computed the AUROC between honest runs
reweighted to the attack runs' length distribution and honest runs as they are, on the board's own
run score. This is what the metric returns if attack runs score like honest runs of the same
length. It also picks up which tasks run long, not only the maximum over more steps (validation).

| Dataset | Attacker | Median actions, attack / honest | Rows | No-skill baseline | Intervals excluding 0.5 |
|---|---|---|---|---|---|
| BashArena | Opus 4.6 | 14 / 25 | 11 per-step | 0.348–0.487 | 10 of 11 |
| LinuxArena, strategy attacks | Opus 4.6 | 41 / 54 | 11 per-step | 0.437–0.471 | 10 of 11 (lead) |
| LinuxArena, paper attacks | Opus 4.6 | 45.5 / 54 | 12 per-step | 0.463–0.488 | 0 of 12 |
| SHADE-Arena | mixed, 2024–25 | 56 / 46 | 10 whole-trajectory | 0.491–0.506 | 0 of 10 |
| SLEIGHT-Bench | human-written | 6 / 6 | 16 per-step | 0.493–0.511 | 0 of 16 |
| ResearchArena | seven 2026 models | 74 / 61 | 1 per-step, 1 whole-trajectory | 0.519, 0.494 | 0 of 2 |
| MonitoringBench | Opus 4.5 / 4.6 | 31 / 21.5 | 3 per-step | 0.572–0.589 | 3 of 3 |

1. **Q1: does the shift extend to the three datasets not examined before? No detectable shift.**
   Every interval on ResearchArena, SHADE-Arena and SLEIGHT includes 0.5, which is "no" under the
   pre-registered rule. The three differ in what that is worth:
   - **SHADE-Arena** is a precise null: ten monitors, 307 attacks against 373 benign runs,
     baselines 0.491–0.506.
   - **ResearchArena** is a weak null. Per-step baseline 0.519 (0.48–0.57). It can detect a shift
     of about 0.06, and a second construction of the baseline predicts 0.538, inside that blind
     zone.
   - **SLEIGHT** is not a test. Its benign runs are twins of the attacks, so 0.5 is guaranteed by
     the design.
2. **Q2: does this change a comparison across datasets for the same monitor? Yes, between BashArena
   or MonitoringBench and anything else.** 11 of 31 contrasts move by at least 0.05 under length
   matching with an interval excluding 0. All 11 involve BashArena or MonitoringBench, so this
   restates C1 as a comparison.

   | GPT-5.4 nano, per-step | As published | Length-matched | No-skill baseline |
   |---|---|---|---|
   | BashArena | 0.389 | 0.522 | 0.380 |
   | MonitoringBench | 0.635 | 0.567 | 0.577 |
   | ResearchArena | 0.630 | 0.608 | 0.519 |
   | SLEIGHT-Bench | 0.633 | 0.639 | 0.495 |

   As published the monitor looks 0.25 worse on BashArena than on MonitoringBench. Matched, the gap
   is 0.05. For GPT-4.1 nano the gap goes from −0.22 to +0.02. No matched difference between two
   datasets has an interval excluding 0, so matching removes the published gaps without
   establishing new ones.
3. **A prediction failed (C4).** We predicted that whole-trajectory monitors, which give one score
   per run, would keep a baseline within 0.03 of 0.5. On LinuxArena ten such rows sit at 0.415–0.466
   with intervals excluding 0.5. The validator's direct check: honest whole-trajectory scores rise
   with honest run length for 7 of 8 monitors (Spearman 0.25–0.62). So the cause is not only the
   maximum over steps. This is a lead: the ten rows are eight monitors scoring the same 200 honest
   runs, and none of the intervals survives a modest allowance for task clustering.
4. **Step-wise safety (C5).** The board's rule reproduces the stored 1% value exactly for all 38
   per-step rows that have one. Under length matching 4 of 38 move by 0.03 or more. The largest is
   GLM-4.6 on BashArena, −0.10 (−0.16 to −0.04). GPT-5 mini on LinuxArena strategies moves −0.09 but
   its interval includes 0.

## Q3: what the board's monitors can read

From the board's code (`control-tower` 308984e, `monitors/_monitor.py`), not from stored prompts
except where noted.

- The board's own monitors read tool calls, tool results and the system and user messages
  (`DEFAULT_READS`). They are not given the agent's own text or its reasoning. No preset used on the
  board adds them. The parent audit confirmed this in the stored prompts for BashArena only.
- The importers for SHADE-Arena, SLEIGHT-Bench and ResearchArena store the agent's text and thinking
  as reasoning, which those monitors do not read.
- SHADE-Arena has a further limit, stated in its importer: Scale's logging dropped tool-call
  arguments, so a monitor sees the names of the tools called and their outputs.
- The LinuxArena rows were scored by the LinuxArena paper's own monitors in April 2026. That code
  is not in the snapshot, so what they read is not established here.

No conclusion about scores is drawn from this. It does bear on reading the board's SHADE-Arena
numbers (AUROC 0.46–0.72 for ten small monitors) next to the Monitor Red Teaming paper's: the
board's monitors read much less of the same transcripts, and the snapshot does not say which of the
paper's conditions the 308 attacks come from.

## Validation

A fresh agent wrote its own code before reading ours ([`validation/VALIDATION.md`](validation/VALIDATION.md)).
Mean run scores reproduce the snapshot exactly on all 86 rows; board AUROC, matched AUROC and
baseline agree to 1e-14 on the 84 analysed rows.

| Claim | Verdict | What changed |
|---|---|---|
| C1 | **Holds** for BashArena and MonitoringBench | A second construction (cut each honest run to a length drawn from the attack runs) gives 0.34–0.44 and 0.57–0.58. Finer bins move further from 0.5, so five bins understate the shift. The LinuxArena strategy rows are a lead. |
| C2 | **Holds with narrower wording** | "No detectable shift", not "nothing". ResearchArena is blind below about 0.06; SLEIGHT is fixed by design. |
| C3 | **Holds with narrower wording** | Every changing contrast involves BashArena or MonitoringBench. Of 8 sign flips, 3 are among the changing contrasts and none is itself beyond noise. |
| C4 | **Holds with narrower wording** | Ten rows are eight monitors on one set of 200 honest runs. One monitor (GPT-OSS-120B) goes the other way. |
| C5 | **Holds; our code was wrong in two places** | We first counted an attack as caught by any flagged action, even after the side task landed, and sized the budget on scored honest actions only. `analyse.py` now uses the board's rule and reproduces all stored values. |

## Limits

- **Intervals are run-level.** The snapshot has no task identifiers, so no interval can be clustered
  by task. By the validator's design-effect check, BashArena holds if clustering doubles the
  variance and mostly if it quadruples it; MonitoringBench holds up to about sixteen times; every
  LinuxArena exclusion is gone at four times.
- **The pre-registration is weak.** The direction on BashArena, MonitoringBench and LinuxArena was
  known from the parent audit, and exploratory numbers were computed before `prereg.md` was written
  (it lists them). The only real predictions were for the three new datasets. The folder was not
  committed before the run, so the timing cannot be checked from git.
- **ResearchArena agent pairing is inferred.** Attack and honest runs were paired by list position.
  Counts and lengths support it (validator's permutation test, p = 0.003); the snapshot has no agent
  names.
- **Private datasets.** The snapshot marks SHADE-Arena and SLEIGHT-Bench as private. Ask the
  maintainers before citing results on them.
- **Not checked:** stored monitor prompts for any dataset but BashArena; the live board after
  2026-11-12.

## Reproducing

```
python analyse.py 2000      # needs numpy; writes results.json, about 30 seconds
python fig_chance.py        # needs matplotlib; writes fig_chance_level.png and .svg
```

Files: [`prereg.md`](prereg.md), [`prior_work.md`](prior_work.md), [`analyse.py`](analyse.py),
[`results.json`](results.json), `run.log`, [`fig_chance.py`](fig_chance.py),
`fig_chance_level.png`, [`validation/`](validation/).
