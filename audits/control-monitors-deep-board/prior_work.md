# Prior work

Short, and in addition to the parent audit's [`prior_work.md`](../control-monitors-bash/prior_work.md).
Posts were fetched from LessWrong on 2026-11-20. "Confirmed" means I read the passage in the post
body myself; "reported" means a survey agent read it and I did not.

| Source | What it already shows | Status |
|---|---|---|
| Parent audit, [`control-monitors-bash`](../control-monitors-bash/) | On BashArena honest runs are longer and length matching raises AUROC for 9 of 11 monitors; on MonitoringBench attacks are longer and the effect reverses; LinuxArena holds. | This repo |
| The board's own tooltip on the AUROC columns | Peak suspicion "can reflect trajectory length". | Parent audit, from the site bundle of 2026-11-17 |
| [Logit ROCs: Monitor TPR is linear in FPR in logit space](https://www.lesswrong.com/posts/Zbry4uMXC7gNe9sRv) (Staley, Bhatt, Stastny; Redwood; 2026-04-15) | On BashArena, benign runs average 41 actions against 20 for attacks. Its fitting procedure builds the null by taking a maximum over as many draws as a trajectory has actions. It does not connect this to AUROC or to the board. | Confirmed |
| [BashArena: A Control Setting for Highly Privileged AI Agents](https://www.lesswrong.com/posts/Cor4QuhM2sybmBSeK) (Lucassen, Kaufman; Redwood; 2025-12-18) | Because runs are long, a step-wise false-positive rate of 0.08% flags 4% of clean trajectories. Headline metric is safety at a trajectory-wise false-positive rate, not AUROC. | Confirmed |
| Redwood-lineage posts on LinuxArena, MonitoringBench and attack selection | Report safety at a fixed audit budget (often 1%, per action), not trajectory AUROC. | Reported |
| Comments on [Building Black-box Scheming Monitors](https://www.lesswrong.com/posts/sb8WmKNgwzefa6oaJ) | Commenters object that AUROC ignores thresholds and base rates. | Reported |
| [How does information access affect LLM monitors' ability to detect sabotage?](https://www.lesswrong.com/posts/N9GvvPDEzm6wkBjHW) (Arike et al.; 2026-02-11) | On SHADE-Arena, chain-of-thought monitors do much better when the agent treats its scratchpad as private and the monitor reads it anyway. | Confirmed |

## What is and is not new here

- **Not new:** that a maximum over more steps is higher; that BashArena honest runs are longer; that
  control researchers prefer safety at an audit budget to AUROC.
- **New in this deep dive:** the size of the resulting shift in the default metric's chance level on
  every dataset of the board, including the three the parent audit did not examine; whether
  whole-trajectory monitors show it too; and how much of the difference between datasets for the
  same monitor it accounts for.
- No LessWrong post discusses the Redwood Control Leaderboard itself (searched 2026-11-20, reported).
