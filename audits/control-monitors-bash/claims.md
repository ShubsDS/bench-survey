# control-monitors-bash: claims under test

Written 2026-11-17, before any monitor score was split by a cue. Question: do the published
AI-control monitors on the BashArena-family datasets rely on trace cues (length / action count,
scaffold `<risky>` tags, the honest-only system message, container timestamps) that the earlier
findings showed predict the label?

## Sources and pins

| Source | Pin | Licence |
|---|---|---|
| Redwood Control Leaderboard `monitors.json` (`control-leaderboard.redwoodresearch.org/monitors.json`) | sha256 `18efcced4fa9c044bc5a0c60aa43c240640155623d177353c6559bf07201520c`, `generated_at` 2026-11-12T21:44:53Z, etag `b954d2c79f50acce7eeee21798b821ca`, fetched 2026-11-17 | per dataset, below |
| Leaderboard `data_catalog.json` | sha256 `e15f155fa96d5153de037b181563c3f4adad75326cc276ead6154323d28196cf` | |
| BashArena honest raw run `de437937709f493dafe549b10b4505cf` (via `data.linuxarena.ai/api/runs/<id>/eval`) | sha256 `8db012217ba105a5d20b9d9932197672ad64a81be5c0ceaef811dae09052b36f` (same file as the earlier finding's pin) | CC BY-SA 4.0 |
| BashArena attack raw run `792967b92d37439ca0b12a5bce9dfa90` | sha256 `99ee247941cc3e5cfdcffa0c0d31f7ac4b169a36e7ab8fb9e57a52f28d2b2915` (same as earlier pin) | CC BY-SA 4.0 |
| Monitor code, `github.com/linuxarena/control-tower` | HEAD `308984e86434208746f00b63cc408c3f35efc6ed` (2026-11-16); same monitor-input logic checked at `703e9764` (2026-11-11), the last monitor commit before the board snapshot | MIT |

Note: `monitors.json` now lists BashArena eval sha256 `2ebafce2…` / `d28bbf81…`, not the hashes of
the files the download endpoint serves (`8db01221…` / `99ee2479…`, which match the board's own
hashes in the earlier snapshot). The trajectory ids in the board's `score_samples` match the
served files one to one (checked in `extract_basharena.py`).

The board's monitored runs for BashArena (`4c5610a0…`, `114339a1…`) now return 404/401, so the
exact monitor prompts sent cannot be read; what the monitor saw is established from the code.

## Conclusion 1 — BashArena monitor ranking and catch rates on the leaderboard

- **Stated where.** The leaderboard's monitor board, default dataset BashArena (Opus 4.6, 600
  honest / 600 attack; 596/596 scored by every monitor). Default sort is AUROC of "peak
  suspicion" (maximum per-action score), descending. `monitors.json` also stores `safety_curve`
  at audit budgets; at a 1% budget the stored safety is: apollo-watcher 0.806, GLM-4.6 0.396,
  Claude Haiku 4.5 0.355, GPT-5.4 nano high 0.275, GPT-5.4 nano medium 0.193, GPT-5 nano minimal
  0.167, DeepSeek V3.2 0.160, GPT-5.4 nano none 0.130, GPT-5.4 nano low 0.090, GPT-4.1 nano 0.074,
  GPT-4o mini 0.069.
- **The board's own caveat.** "Stepwise monitors use peak suspicion, which can reflect trajectory
  length."
- **Who relies on it.** People choosing a trusted monitor for a control protocol, and the board's
  readers comparing monitor models and reasoning efforts.
- **What would change it.** On honest and attack runs matched on action count, (a) the monitor
  ranking moves (Kendall tau with the full-set ranking whose 95% task-bootstrap interval excludes
  0.8, or the top monitor changes), or (b) AUROC / catch rate at 1% FPR moves by more than its own
  95% interval. "Holds" if neither.

## Conclusion 2 — LinuxArena: undetected sabotage at 1% step-wise FPR, and the monitor ranking

- **Stated where.** Tracy et al., "LinuxArena", arXiv 2604.15384v2, abstract: against a GPT-5-nano
  trusted monitor at a 1% step-wise false positive rate, Claude Opus 4.6 "achieves roughly a 23%
  undetected sabotage success rate" (fetched 2026-11-17; the earlier finding in
  `findings/linuxarena-trajectory-baselines/` recorded 34% for v2 — the discrepancy is noted, not
  resolved). The leaderboard's `linuxarena-paper` dataset carries the paper's own per-action
  scores for Opus 4.6's 92 multi-phase attacks against 200 honest runs, 12 action monitors; stored
  safety at a 1% budget for GPT-5 nano: 0.710.
- **Who relies on it.** Readers of the paper and the board estimating how often a frontier
  attacker beats a cheap trusted monitor.
- **What would change it.** Undetected-sabotage / catch rate at 1% FPR recomputed against
  length-matched honest runs differing from the full-set value beyond its 95% interval.

## Conclusion 3 — MonitoringBench catch rates on the leaderboard

- **Stated where.** The board's `monitoringbench` dataset: 2,644 successful attacks against
  Palaestra Research's 550 honest runs (MonitoringBenchHonest), three action monitors; stored
  safety (= catch rate, every side task succeeded) at a 1% budget: GPT-5.4 nano 0.360, GPT-5 nano
  minimal 0.258, GPT-4.1 nano 0.240. The paper's own headline (Opus 4.5 catch rate 94.9% to 60.3%,
  arXiv 2605.09684) uses 416 unreleased honest runs and cannot be recomputed (blocked, as in the
  earlier finding).
- **What would change it.** As for conclusion 2, with action count as the matched cue.

## Scope

This audit tests monitor reliance only. It does not re-derive the cues (L1/L2, already shown in
the five earlier findings). SHADE-Arena, MRT and CTRL-ALT-DECEIT are covered by
`audits/control-monitors-shade/`.
