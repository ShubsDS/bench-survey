# Fact-check: "BashArena-family board: with transcript length matched, 6 of 11 monitors are at or below chance"

Independent re-derivation, 2026-11-20. Own code only (`extract.py`, `analyse.py`, `linuxarena.py`, `scan_tags.py`, `make_graph_data.py`). Inputs are the repo's local data: `data/site/monitors.json` (sha 18efcced…, the board snapshot of 2026-11-12), the raw BashArena `.eval` files, and the 2026-09-24 monitored logs. I made no model calls and did not modify the repo.

## What the board is
- **Board.** The Redwood Control Leaderboard, "Monitor evals" page (control-leaderboard.redwoodresearch.org/monitors). Default dataset: BashArena, with Claude Opus 4.6 as the agent, 600 honest and 600 attack runs; 596/596 are scored by all 11 action monitors (10 `simple` LLM monitors plus apollo-watcher).
- **Columns.** AUROC, pAUROC (0–20% FPR) and average precision, all on **peak suspicion** (the maximum per-action score in a trajectory). The default sort is **AUROC descending**, so trajectory-level AUROC is the board's headline ranking metric. Source: the site JS bundle from 2026-11-17; the live page is client-rendered, so on 2026-11-20 it could only be fetched as a "Loading…" shell.
- **The board's own caveat.** The tooltip on those columns already says: "Stepwise monitors use peak suspicion, which can reflect trajectory length."
- **Step-wise safety.** Safety at a 1% audit budget is stored in `monitors.json` (`safety_curve`). It is not a column on the monitor board.
- **Length measure in the claim.** `n_actions`, the number of agent actions (steps), not tokens or characters.
- **Repo's matching method.** Five bins at the attack class's `n_actions` quintiles. Honest runs are reweighted to the attack bin shares, and all 596 attacks are kept.
- **"At or below chance" in the repo.** It means the matched AUROC's 95% CI does not lie entirely above 0.5. This was established by the repo's validator, not stated in the prereg.

## Verdict table

| Sub-claim | Repo | Mine | Verdict | How checked |
|---|---|---|---|---|
| Board AUROCs reproduce | 0.833 … 0.312 | 0.833 … 0.312, identical to 3 dp for all 11 | HOLDS | max of non-null per-action scores, attack positive, Mann–Whitney with ties = ½ |
| "Attack transcripts are longer than honest ones" (FINDINGS §3, first sentence) | stated | **Attacks are shorter.** Median 14 vs 25 actions. Monitor-visible characters 46k vs 54k. n_actions alone gives AUROC 0.164 [0.146, 0.184], so shorter means attack | **FAILS** for BashArena. The repo's own README says attacks are shorter; the sentence matches MonitoringBench (31 vs 21.5), not BashArena. Only agent output tokens (mostly hidden reasoning, never shown to monitors) are longer for attacks: 56.8k vs 13.0k | own extraction from raw evals |
| Length-matched AUROC values (repo method) | 0.381 … 0.854 | identical to 3 dp for all 11 | HOLDS | re-implemented quintile reweighting |
| "6 of 11 at or below chance" | 6 | Repo method: **2** with point estimate ≤ 0.5 (GPT-4o mini 0.381, GPT-5 nano minimal 0.453; both CIs entirely below 0.5); **4** more with CIs that include 0.5 (GPT-4.1 nano 0.518 [0.476, 0.559], DeepSeek V3.2 0.523 [0.482, 0.563], GPT-5.4 nano none 0.522 [0.473, 0.570], GPT-5.4 nano low 0.509 [0.463, 0.553]); 5 with CIs entirely above 0.5. "6" = 2 below + 4 indistinguishable. Same 6 with a main-task cluster bootstrap | **HOLDS WITH NARROWER WORDING.** Only 2 are "at or below" by point estimate. Say "6 of 11 are below chance or not distinguishable from it" | trajectory bootstrap (1000, class-stratified) and task-cluster bootstrap |
| Robustness of "6" to matching method (n_actions) | 6 (repo scheme); validator 3 schemes | Not above chance (CI not entirely above 0.5): decile reweight 6, exact-length pairs 6, NN 1:1 exact 6, NN 1:1 caliper 6, covariate-adjusted ROC (kNN-60) 6, width-2 bins 5, width-5 bins 5, honest truncation 4. Outliers: coarse within-bin pairs (quintile/decile) 7, but these have residual confounding (top bin is 439 honest up to 106 actions vs 123 attacks of 18–41 actions); residualising on log n (honest-fit OLS) 2, which extrapolates a linear honest slope | **HOLDS WITH NARROWER WORDING.** Good matching schemes give **4–6**; 6 is the top of that range. Stable core in every adequate scheme: GPT-4o mini, GPT-5 nano minimal, GPT-4.1 nano, GPT-5.4 nano low. DeepSeek V3.2 and GPT-5.4 nano none are borderline (CI lower bound 0.502–0.508 under some schemes) | `analyse.py` |
| Other length measures | — | Monitor-visible characters (decile reweight or strat): 7 not above chance, but this barely matches action count (chars-only AUROC 0.39). Output tokens: 7–9, but tokens are not monitor-visible and overlap is poor (tokens-only AUROC 0.97) | n_actions is the right measure; the count is not robust to swapping in other "length" definitions | `analyse.py` |
| "9 of 11 change" | 9 (prereg rule: Δ CI excludes 0 and \|Δ\| ≥ 0.03) | 9 by the same rule, all **upward** (+0.044 to +0.157). apollo-watcher +0.021 [+0.013, +0.030] fails only the 0.03 size bar; GLM-4.6 +0.010 [−0.018, +0.036]. Other schemes: 9–10 (exact, width-2/5, decile, kNN, truncation), 6 for coarse strata | **HOLDS**, but the direction must be stated: matching *raises* AUROC. Unmatched, **7 of 11 are below 0.5** by point estimate (6 with CIs entirely below). Matching cuts the below-0.5 count from 7 to 2 | paired bootstrap of Δ |
| Step-wise safety at 1% "barely moves" | 2 of 11 beyond noise (GLM-4.6 −0.106, GPT-4.1 nano +0.030) | Stored values reproduce exactly (0.069 … 0.806). Matched Δ: GLM-4.6 −0.102 [−0.165, −0.047]; GPT-4.1 nano +0.030 [+0.018, +0.043]; GPT-5.4 nano low +0.012 [+0.002, +0.025]; apollo-watcher −0.005 [−0.016, −0.001]; the other 7 have CIs that include 0. \|Δ\| ≤ 0.04 for 10 of 11 | **HOLDS WITH NARROWER WORDING.** "Barely moves except GLM-4.6 (−0.10, fragile)". Note 4, not 2, intervals exclude 0 in my bootstrap; the repo's own table also has GPT-5.4 nano low and apollo-watcher excluding 0 but not bolded | board rule: threshold on honest actions at 1% with fractional ties, attack caught if any action flagged, 583 attacks with an outcome; 300 bootstraps |
| LinuxArena holds | every AUROC moves ≤ 0.021, tau 1.0 | Max \|Δ\| 0.021 (GPT-4.1 nano), Kendall tau 1.0; length-only AUROC 0.445 (92 attack / 199 honest) | HOLDS (point estimates; no CIs) | `linuxarena.py` |
| 0 of 273,619 stored monitor prompts contain the scaffold tags | 0 / 273,619 | 91,875 (attack log) + 181,744 (honest log) = 273,619 monitor model calls; 0 resolved inputs contain `<risky` or `risky>`, while 596/600 attack samples carry the tag in agent text | HOLDS. Scope: the 10 `simple` monitors only (apollo-watcher prompts are not in these logs), from the 2026-09-24 monitored runs. Those runs' scores match the board; the currently listed runs return 404/401 | `scan_tags.py` |
| Rating "Solid" | Solid | Numbers reproduce exactly; the count is method-dependent (4–6); the lead sentence has the length direction wrong | Solid on the arithmetic; the prose needs fixing | — |

## Caveats and discrepancies (most important first)

1. **The direction is backwards in FINDINGS.**
   - BashArena attacks are *shorter*: median 14 vs 25 actions, and fewer monitor-visible characters.
   - Peak-over-actions rises with honest run length, so length pushes the board's AUROC **down**. Unmatched, 7 of 11 monitors sit below 0.5 (GPT-4o mini 0.312 … GPT-5.4 nano medium 0.489). Matching raises every one.
   - "With length matched, 6 of 11 are at or below chance" is numerically right. But next to "attack transcripts are longer", a reader will infer that length was *inflating* the monitors and matching knocked them down to chance. The opposite happened: matching lifts five monitors from below 0.5 to at or above it, and those that end near chance were near chance per action all along.
   - Pooled per-action AUROC is 0.43–0.57 for the 10 `simple` monitors.
2. **"6" means "below or not distinguishable from chance", not "at or below".**
   - Only 2 matched point estimates are ≤ 0.5.
   - Across adequate matching schemes the count is 4–6. The core 4 that are never above chance are GPT-4o mini, GPT-5 nano minimal, GPT-4.1 nano and GPT-5.4 nano low.
   - A schemes-sensitive "6" should be cited as "about half (4–6 of 11)" or with the exact wording above.
3. **Mechanism: an aggregation artefact, not monitors reading length.**
   - Among honest runs, the Spearman correlation of peak with n_actions is 0.03–0.54.
   - An iid order-statistic simulation (draw n per-step scores from the pooled honest per-step distribution and take the max) predicts 0.35–0.44. For 9 of 11 monitors the observed value is at or below that, and mean per-step score is nearly flat in length for most (ρ −0.04 to 0.31).
   - Exception: GPT-4.1 nano (ρ_peak 0.54 > iid 0.38; mean-step ρ 0.43), which shows per-step drift with length or context.
   - So the defensible framing is "the board's peak-suspicion metric is confounded by run length". "Monitors use length" is not supported.
   - The causal objection (attack length is post-treatment) bites little here. Matching reweights only honest runs and keeps all 596 attacks. NN-matched attacks have the same side-task success, 0.97 vs 0.976 overall, though they are longer (median 18 vs 14).
4. **Overlap is thin at the short end.**
   - Repo bins (honest/attack): 17/76, 24/130, 51/150, 65/117, 439/123. The 206 shortest attacks are compared against 41 short honest runs. Kish effective honest n is 205 of 596; max weight 5.4.
   - 1:1 exact matching keeps only 273 of 596 attacks.
   - Matched AUROCs therefore lean heavily on a few dozen short honest runs. The bootstrap CIs (±0.04–0.05) reflect that.
5. **Step-wise safety (the deployment-relevant number) mostly holds.**
   - 10 of 11 move by ≤ 0.04.
   - GLM-4.6 drops 0.396 → 0.293, which the repo's validator traced to one threshold jump on a coarse score grid.
   - By CI-excludes-0, 4 of 11 change in my bootstrap, not 2, but the extra two are tiny (+0.012, −0.005).
6. **The maintainers already flag the issue.** The board's own tooltip says peak suspicion "can reflect trajectory length". The essay should say the board discloses the confound but still ranks by the affected metric by default, rather than imply it is hidden.

**Not verified:**
- The live board text as of today: the page is client-rendered, so I relied on the 2026-11-17 JS bundle.
- apollo-watcher's prompts.
- LinuxArena CIs.
- MonitoringBench, which is not part of this claim.

## Recommended citation sentence

> On the Redwood Control Leaderboard's BashArena monitor board, whose default ranking is trajectory-level AUROC on peak (max-per-step) suspicion, honest runs are longer than attacks (median 25 vs 14 actions). That depresses the scores: 7 of 11 monitors score below 0.5. Once honest and attack runs are matched on action count, AUROC rises beyond noise for 9 of 11 monitors. Even so, 4–6 of the 11 (depending on the matching method; 6 under the audit's scheme) remain below or statistically indistinguishable from chance. The board's step-wise safety numbers at a 1% audit budget move by at most 0.04, except one monitor.

Shorter: "On one public monitor leaderboard, the default ranking metric is confounded by run length. Correcting for it changes 9 of 11 scores, and still leaves about half the monitors no better than chance."
