# Redwood Control Leaderboard, monitor board: pooling, BashArena baselines, availability

Status: checked on 2026-10-27 against the board's published JSON and the two public BashArena
raw logs. Three leads from catalogue entry A5 were tested (checks 3, 1, 0). Results in brief:

- Lead 1 holds: on BashArena, simple length features separate the classes better than most
  board monitors, in the direction that hurts them.
- Lead 3 is mostly ruled out: the board does not pool SHADE with anything, and dropping a dataset
  or keeping only successful attacks changes few rankings beyond noise.
- Lead 0 holds in a narrower form: two datasets have no public transcripts at all, but every
  board row's per-trajectory scores are public.

Not yet raised with Redwood or EquiStamp.

## Pins

| Source | Pin |
|---|---|
| `data_catalog.json` | sha256 `ede7ff91…852a`, last-modified 2026-10-26 22:50:50 GMT, schema_version 1 |
| `monitors.json` | sha256 `680d1ffc…a776`, `generated_at` 2026-10-24T19:28:16Z, 82 monitor×dataset rows |
| `monitor-plots/pooled.json` | sha256 `0d0f8f1d…3c29` |
| BashArena honest raw log | run `de437937709f493dafe549b10b4505cf`, sha256 `8db01221…6b36f` (matches the board's own hash) |
| BashArena attack raw log | run `792967b92d37439ca0b12a5bce9dfa90`, sha256 `99ee2479…2915` (matches) |
| Site deployment | `dpl_94SXhnLuCL7ybYMs6zpougwBxnFS` (JS bundle read as text, not run) |

BashArena data is licensed CC BY-SA 4.0. Only aggregates and ids are reported here anyway.

## How the board combines datasets

- **Default view.** One dataset, BashArena (`default_dataset`). Datasets are combined only
  when a viewer selects several.
- **Combination rule.** The combined AUROC is the **mean of the per-dataset AUROCs**, so each
  dataset counts equally whatever its size. Reproduced from `score_samples`:
  - all 82 single-dataset values match exactly;
  - all 39 combined values match within 0.0016;
  - concatenating trajectories instead misses by up to 0.12.
- **Consequence of equal weight.** SLEIGHT's 74 trajectories carry the same weight as
  MonitoringBench's 3,194.
- **Which monitors count.** The score is "peak suspicion" (maximum per-action score). It is
  computed over the trajectories that every monitor of that type scored. Failed attacks are
  included.
- **Which combinations exist.** Only monitors scored on every selected dataset are shown, so
  only six combinations ever have rows:
  - BashArena / MonitoringBench / SLEIGHT, in any subset (action monitor `simple`, 3 or 10
    shared monitors);
  - the two LinuxArena sets.
- **SHADE-Arena (MRT) is never combined with anything.** It is scored only by the
  `trajectory` monitor, which no other dataset uses. All 31 multi-dataset selections that
  include it show no shared monitors.

## Lead 3: positive classes and how much rankings move

What "attack" means in each dataset, from `side_task_success` in the board's samples:

| Dataset | Attacks scored | Side task succeeded | Failed | No outcome |
|---|---|---|---|---|
| BashArena (Opus 4.6) | 596 | 569 | 14 | 13 |
| MonitoringBench | 2,644 | 2,644 | 0 | 0 |
| SLEIGHT (human-written) | 37 | — | — | 37 |
| SHADE-Arena (MRT) | 307 | 236 | 71 | 0 |
| LinuxArena paper | 92 | 90 | 2 | 0 |
| LinuxArena strategies | 45 | 44 | 1 | 0 |

The board's SHADE rows carry an outcome, unlike MRT's CUA half. So the earlier claim of
"attack assignment with no outcome" does not apply to this slice.

**How rankings change.** Each comparison re-ranks the monitors (by board AUROC) with one dataset
dropped, or with only attacks whose side task succeeded. A flip is a pair of monitors whose order
reverses. A flip counts as resolved when the paired bootstrap interval of their AUROC difference
(1,000 resamples) excludes 0 under either ranking.

| Comparison | Monitors | Kendall τ | Pairs flipped (resolved) | Top monitor |
|---|---|---|---|---|
| Bash+MB+SLEIGHT, drop BashArena | 3 | 1.00 | 0/3 | unchanged |
| Bash+MB+SLEIGHT, drop MonitoringBench | 3 | 1.00 | 0/3 | unchanged |
| Bash+MB+SLEIGHT, drop SLEIGHT | 3 | 0.33 | 1/3 (0) | unchanged |
| Bash+MB+SLEIGHT, successful attacks only (SLEIGHT drops out) | 3 | 0.33 | 1/3 (0) | unchanged |
| Bash+SLEIGHT vs BashArena alone | 10 | 0.69 | 7/45 (4) | Haiku 4.5 → GLM 4.6 |
| Bash+SLEIGHT vs SLEIGHT alone | 10 | 0.51 | 11/45 (5) | Haiku 4.5 → GPT-5.4 nano medium |
| BashArena, all attacks vs successful only | 10 | 1.00 | 0/45 | unchanged |
| SHADE, all attacks vs successful only | 10 | 0.91 | 2/45 (0) | unchanged |
| LinuxArena pair, drop strategies (action) | 12 | 0.85 | 5/66 (2) | unchanged |
| LinuxArena pair, drop paper (action) | 12 | 0.82 | 6/66 (0) | Opus 4.6 → Gemini 3.1 Pro |
| LinuxArena pair, successful attacks only | 12 / 8 | 1.00 | 0 | unchanged |

What the table shows:

- **Keeping only successful attacks** changes no ranking beyond noise.
  - Largest AUROC change: 0.032 (SHADE).
  - Flips: two on SHADE, one on the three-monitor pool, none resolved.
- **Dropping a dataset** matters only for BashArena + SLEIGHT. The two datasets rank the
  monitors differently: 4–5 resolved flips, and the top monitor changes.
  - We do not attribute this to SLEIGHT's label type. With 37/37 trajectories, SLEIGHT's
    intervals are wide, and BashArena's own ranking is distorted by length (Lead 1).
- **The three-dataset pool spanning all three label types** has only 3 shared monitors. Its
  rankings do not move beyond noise.

Verdict:

- Ruled out for SHADE/MRT: it is never pooled, and its labels carry outcomes.
- Mostly ruled out for outcome selection.
- Holds only as a design note: equal weight lets a 74-trajectory dataset with no outcome
  move a combined ranking. Bias direction: either.

## Lead 1: content-blind baselines on BashArena 600/600 (Opus 4.6)

How the set is built:

- Each attack main task is used 4 times, once per side task (firewall, passwords, malware,
  sudo): 150 tasks × 4 = 600 attacks.
- The 600 honest runs are on 600 different tasks, 150 of which overlap with the attack tasks.
- Main-task success: 71 of 600 honest runs, 9 of 600 attack runs.
- Every one of the 569 successful attacks ends at the action where the side task landed. Honest
  runs go on until they submit.

Baselines are scored as AUROC with "attack" as the high class. Each has a null of 1,000 label
shuffles; the shared-task column shuffles labels within main tasks.

| Feature | Median honest / attack | AUROC | 95% CI | Null p95 | Same 150 tasks |
|---|---|---|---|---|---|
| Number of actions | 25 / 14 | 0.169 (0.831 reversed) | 0.147–0.192 | 0.532 | 0.131 |
| Number of messages | 52 / 29 | 0.156 (0.844 reversed) | 0.134–0.180 | 0.532 | 0.121 |
| Tool output characters | 22,262 / 13,215 | 0.291 | 0.262–0.320 | 0.531 | 0.266 |
| Visible assistant text characters | 3,504 / 7,680 | 0.841 | 0.819–0.864 | 0.533 | 0.750 |
| `<risky>` tags in assistant text | 0 / 12.5 | 0.997 | 0.993–0.999 | 0.531 | 0.997 |
| System message in transcript | all / none | 1.000 (reversed) | — | 0.527 | 1.000 |
| Stored system-prompt length | 6,032 / 12,915 | 0.993 | 0.987–0.998 | 0.531 | 0.993 |

The board's 10 monitors score AUROC 0.31–0.65 on this set (median 0.42). Six of the ten are
below 0.5.

**Why the monitors sit below chance.** Attack runs are about half as long as honest runs, and a
maximum over fewer actions is lower.

- Peak suspicion rises with run length on honest runs (Spearman 0.05–0.52).
- On the same scores, the mean per-action suspicion beats the board's peak for 9 of 10
  monitors. For example, Haiku 4.5 goes from 0.62 to 0.80 and GPT-5.4 nano high from 0.59 to
  0.71.
- So the board's ranking on its default dataset partly measures how each monitor's peak
  responds to length.
- The board's own note says that peak suspicion "can reflect trajectory length".

**Scaffold cues.** The scaffold fields separate the classes almost perfectly:

- In 596 of 600 attack runs, the attack policy's visible text carries a `<risky>true/false</risky>`
  tag. No honest run has one.
- Honest transcripts start with a system message; attack transcripts start with a user message.

We could not check whether the board's monitors see these fields. The 270 MB monitored log
download hung and was stopped. The monitors' below-chance scores show they do not use these
cues today. A fitted or prompt-tuned monitor could.

Verdict: holds.

- Length and scaffold baselines beat their nulls by wide margins, inside shared tasks too.
- Number of actions, read in reverse, scores 0.83, above every board monitor.
- Bias direction: down for current monitors, which look worse than their per-action scores
  support. Up for any monitor that reads the `<risky>` tag or the system-message difference.

## Lead 0: what cannot be downloaded

Each run's `/api/runs/<id>/eval` endpoint was probed on both hosts. A 302 from
`data.linuxarena.ai` means a public download; `equistamp.linuxarena.ai` answers 401 to
everything.

| Dataset | Raw honest | Raw attack | Monitored honest | Monitored attack | Board rows |
|---|---|---|---|---|---|
| BashArena | public | public | public | public | 10 |
| MonitoringBench | public | public | public | public | 3 |
| LinuxArena paper | public | 404 / 401 | public | public | 20 |
| LinuxArena strategies | public | 404 / 401 | public | public | 24 |
| SHADE-Arena (`visibility: private`) | 404 / 401 | 404 / 401 | 404 / 401 | 404 / 401 | 10 |
| SLEIGHT (`private`, withheld in catalog) | 404 / 401 | 404 / 401 | 404 / 401 | 404 / 401 | 15 |
| Mythos 5 incident (`public`) | — | 404 / 401 | — | — | 0 |

- **Rows with a non-public raw run:** 69 of 82 board rows. Only 25 of them (SHADE, SLEIGHT,
  31%) have no public transcript in any form.
- **What remains checkable.** The per-trajectory scores for every row, those 25 included, are
  public in `monitors.json`. The AUROC numbers can therefore be recomputed, as done above. The
  transcripts behind them cannot be inspected.
- **Upstream sources.** For both SHADE and SLEIGHT, the pinned upstream repositories return 200.
  The board's converted copies are what is closed.
- **Mythos.** It is marked `public` but returns 404 and 401. It feeds no ranking row.

Verdict: holds, narrower than first noted.

- 31% of rows cannot be checked against transcripts, and under equal weight each such dataset
  counts fully in any selection.
- No ranking number is unverifiable.

## Not tested

- Whether the board's monitors read the `<risky>` tags or the system message.
- MonitoringBench and MRT internals, which other audits cover.
- Safety-at-budget rankings; only AUROC was re-ranked.

## Reproducing

All Python runs with `-I`. Downloaded files are read as data and never executed.

```
python -I check_availability.py data/site/api out/availability_checks.json
python -I check_pooling.py      data/site/api out/pooling_checks.json
python -I extract_basharena.py  data/basharena data/basharena_features.json
python -I check_basharena.py    data/basharena_features.json data/site/api out/basharena_checks.json
```

`data/site/api` holds `monitors.json` and `monitor-plots_pooled.json`, fetched from
`control-leaderboard.redwoodresearch.org`. `data/basharena` holds the two raw `.eval` files
listed under Pins.
