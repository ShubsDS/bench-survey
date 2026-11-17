# control-monitors-bash: prior work

Searched 2026-11-17 (web search on LessWrong, arXiv, the Redwood blog; the leaderboard's own
notes; this project's findings). Items marked "snippet" were read only through search summaries,
not in full.

## This project (the starting point)

| Finding | What it showed | Level |
|---|---|---|
| [`findings/redwood-leaderboard-scaffold-cues/`](../../findings/redwood-leaderboard-scaffold-cues/) | BashArena 600/600: action count AUROC 0.831 (reversed), `<risky>` tags in 596/600 attacks, system message only in honest runs; board monitors 0.31–0.65; peak suspicion rises with length on honest runs (Spearman 0.05–0.52); mean per-action beats peak for 9/10 monitors. "Whether the board's monitors read the `<risky>` tags or the system message" untested. | L1/L2 |
| [`findings/basharena-checkers-and-length/`](../../findings/basharena-checkers-and-length/) | Auto-submit ends attacks when the side task lands; checker flaws. | L1 |
| [`findings/linuxarena-trajectory-baselines/`](../../findings/linuxarena-trajectory-baselines/) | Count features 0.90 (Haiku pair), LaStraj length alone 0.95 vs GPT-5 Nano live-max 0.35. Opus 4.6 headline pair untested. | L1/L2 |
| [`findings/monitoringbench-container-clock/`](../../findings/monitoringbench-container-clock/) | `ls -l` month separates MonitoringBenchHonest from attacks (0.998); tool-mix 0.87. Monitor use untested; no honest monitor scores released at the time. | L1/L2 |
| [`findings/monitoringbench-release-selection/`](../../findings/monitoringbench-release-selection/) | Release filtered on detection; near-copies; monitor prompt shows tool calls only, no agent prose. | L1 |

## External

- **The leaderboard itself** notes that "stepwise monitors use peak suspicion, which can reflect
  trajectory length" (board caption, site JS bundle, deployment `dpl_DxgZmY8D6vZZsDWo6Kg2jJ3jkawt`).
  So the length–peak mechanism is acknowledged in words; no stratified numbers are given.
- **Küçükkurt and Elasky, "Releasing benign trajectories for MonitoringBench"**
  ([LessWrong](https://lesswrong.com/posts/bdBoH23TCTFZkkfqp/releasing-benign-trajectories-for-monitoringbench)):
  step counts and lengths not matched between classes (stated by the authors).
- **"Classifier context rot: monitor performance degrades with context length"**
  ([LessWrong](https://lesswrong.com/posts/7vpvNM7viJqNWAdG7/classifier-context-rot-monitor-performance-degrades-with),
  [arXiv 2605.12366](https://arxiv.org/html/2605.12366)) — snippet: the same obvious attack is
  harder to detect inside a long transcript; evaluations ignoring context length may overstate
  safety. This is the attack-side mechanism (length hides attacks), opposite in sign to the
  peak-over-more-actions mechanism on honest runs.
- **Redwood blog, "Logit ROCs: monitor TPR is linear"**
  ([post](https://blog.redwoodresearch.org/p/logit-rocs-monitor-tpr-is-linear)) — snippet: builds
  a null by resampling attack trajectory lengths in BashArena because cost scales with benign
  messages flagged. Acknowledges length in the safety calculation; does not stratify monitors.
- **"How does information access affect LLM monitors"**
  ([LessWrong](https://lesswrong.com/posts/N9GvvPDEzm6wkBjHW/paper-how-does-information-access-affect-llm-monitors))
  — snippet: less-is-more effect; authors note a 10x transcript-length difference between
  attacker models as a possible confound.
- **"Using chunked monitoring to detect deception in long transcripts"**
  ([LessWrong](https://www.lesswrong.com/posts/orMEvTgtRig9qnsdL/using-chunked-monitoring-to-detect-deception-in-long))
  — snippet: recall rises with transcript length; warns label–length confounding can masquerade as
  a length effect.
- **"Catching split attacks across compactions"**
  ([LessWrong](https://lesswrong.com/posts/s9fmXPbbsBbBK6TZi/catching-split-attacks-across-compactions-in-long-context))
  — builds attacks by copying honest transcripts and adding calls, a design that limits length
  confounds.
- **LinuxArena paper** (arXiv 2604.15384v2) — reports safety at step-wise FPR; no length
  stratification found in the abstract.

## What is new here

None of the above (a) establishes, from code, which of the four BashArena cues reach the board's
monitors, (b) splits the board's released per-trajectory scores by action count to see whether the
rankings and 1%-FPR catch rates survive, or (c) edits a cue in place and rescores. The length
mechanism has been named (board caption, context-rot work) but not quantified on these rankings.
Extending the earlier L1/L2 findings to L3/L4 is the new part.
