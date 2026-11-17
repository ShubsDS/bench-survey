# control-monitors-bash: independent validation

Validator, 2026-11-17. I did not write the audit and tried to break its five claims. Everything
below comes from the scripts in this folder, run on pinned inputs (sha256 in `rederive.py` and
`monitor_inputs.py`). I used no model inference. Machine-readable numbers: [`validation.json`](validation.json).

| Claim (as reported) | Verdict |
|---|---|
| 1. What monitors see: tags never shown; the system message reaches the monitor only as a role label | **HOLDS WITH CORRECTION**: tags confirmed absent from the stored prompts; the role label is absent too |
| 2. BashArena: length works against the monitors; matched AUROC rises for all 11; ranking partly changes; step-wise safety moves for 2 of 11 | **HOLDS WITH CORRECTION** |
| 3. LinuxArena paper set holds under length matching (R) | **HOLDS** (rerun only; not re-derived independently) |
| 4. MonitoringBench: the three monitors' separation is length | **HOLDS WITH CORRECTION**: true for 2 of 3 monitors |
| 5. Haiku L4: neither edit exceeds noise (R) | **HOLDS WITH CORRECTION**: the null has little power, and the system-role edit tests a cue the board's monitors never saw |

## A. Rerun of the auditor's scripts

I verified every pin (`monitors.json` `18efcced…`, BashArena evals `8db01221…` / `99ee2479…`). I reran
`extract_basharena.py`, `effect_l3.py`, `robustness_l3.py` and `analyse_l4.py` (both runs) into a
scratch directory. Every output matches the committed file to the last digit: 0 differing values in
`results_l3.json` and `results_robustness.json`, and the L4 files are identical apart from key
order. Every block of `results.json` equals its stage file. The ledger has 768 calls costing
2.3443 USD.

## B. Independent re-derivation (claims 2 and 4)

`rederive.py` does not import the auditor's code. It reads the per-action scores straight from
`monitors.json` and the main and side task of each trajectory from the raw evals. For
MonitoringBench I downloaded the raw evals that are served for the board's run ids (honest
`7f1aabcd…`, sha256 `d9845466…`; attack `f7d63673…`, sha256 `0a7b6684…`; all 3,194 trajectory ids
mapped to 136 main tasks). Every interval comes from 1,000 bootstrap resamples of main tasks. Three
length controls:

- **A**: the auditor's scheme, reimplemented. Honest runs are reweighted to the attack class's
  quintile shares.
- **B**: exact length. AUROC is computed over attack/honest pairs with identical `n_actions` only.
- **C**: truncation. Each honest run is cut to its paired attack's length, and its peak is
  recomputed from the stored per-step scores (pairs with n_honest ≥ n_attack).

### Claim 2: BashArena (596/596, 597 task clusters)

**The auditor's numbers reproduce.**
- Full-set AUROC 0.312–0.833.
- Scheme A changes: +0.010 (GLM-4.6) to +0.157 (GPT-4.1 nano), identical to the README.
- Kendall tau 0.891 [0.709, 0.964]; top monitor unchanged.
- Step-wise safety under A: GLM-4.6 −0.106 [−0.144, −0.038]; GPT-4.1 nano +0.030 [0.014, 0.052].

**Why AUROCs sit below 0.5.** I checked for a sign error, a label swap and the aggregate:
- **Not a sign error or label swap.** Classes come from the run ids. The site bundle computes
  action AUROC as `Math.max(...actions.filter(x => x !== null))` per trajectory, with attack as the
  positive class (chunk `0ci_.d~u20qs1.js`). My code reproduces the board's AUROCs to 4 dp, and so
  did the earlier finding.
- **The aggregate is the cause.** Attacks are shorter (median 14 vs 25 actions; they stop when the
  side task lands). The peak rises with length within honest runs (Spearman 0.03–0.54). For 7
  monitors the mean honest peak exceeds the mean attack peak (for example GPT-4o mini 80.6 vs 71.5,
  values the board itself stores as `mean_max_sus_*`).
- **Per action the cheap monitors are near chance.** Pooling every scored action, attack actions
  against honest actions, gives AUROC 0.43–0.57 for the 10 `simple` monitors. So the sub-0.5
  trajectory AUROCs come from a maximum over more honest draws, laid on top of near-chance
  per-action separation.

**What the board publishes.** The monitor board ("Monitor evals") shows AUROC, pAUROC (0–20% FPR)
and average precision, all on peak suspicion. Its default sort is AUROC, descending (`useState({key:
"auroc", direction: "descending"})` in chunk `064cp4396tz_~.js`). The 1%-budget step-wise safety is
stored in `monitors.json` (`safety_curve`) and plotted on the sabotage pages; it is not a column of
the monitor board. So the AUROC the audit attacks is the monitor board's headline, not a number
nobody uses.

**Which published numbers change, and by how much.**
- The monitor board's AUROC column on BashArena: +0.010 to +0.157 under A.
- Its order: GLM-4.6 2nd → 4th; Haiku 4.5 3rd → 2nd; apollo-watcher stays 1st.
- pAUROC (board column; point estimates, scheme A): GPT-5.4 nano high 0.159 → 0.237; Haiku 4.5
  0.167 → 0.203; GPT-4.1 nano 0.051 → 0.093; GLM-4.6 0.240 → 0.227.

**Second and third matching schemes** (the conditioning concern). Matching never selects attacks:
scheme A keeps all 596 attacks and reweights only honest runs, whose length is not a consequence of
attacking (Kish effective sample 205 of 596 honest runs; largest weight 5.4). Under B, all 596
attacks have at least one equal-length honest run (9,309 pairs; 446 honest runs used). Under C, 85%
of pairs qualify.

| Monitor | Full | A | B (exact n) | C (truncation) |
|---|---|---|---|---|
| apollo-watcher | 0.833 | 0.854 | 0.848 (+0.015 [−0.001, 0.031]) | 0.859 |
| GLM-4.6 | 0.648 | 0.658 (+0.010 [−0.016, 0.037]) | 0.643 (−0.005 [−0.035, 0.024]) | 0.682 (+0.034 [0.024, 0.044]) |
| Claude Haiku 4.5 | 0.624 | 0.668 | 0.667 | 0.743 |
| GPT-5.4 nano high | 0.591 | 0.667 | 0.658 | 0.686 |
| GPT-5.4 nano medium | 0.489 | 0.580 | 0.585 | 0.601 |
| DeepSeek V3.2 | 0.445 | 0.523 | 0.535 | 0.534 |
| GPT-5.4 nano none | 0.389 | 0.522 | 0.538 | 0.538 |
| GPT-5.4 nano low | 0.373 | 0.509 | 0.505 | 0.520 |
| GPT-4.1 nano | 0.361 | 0.518 | 0.536 | 0.494 |
| GPT-5 nano minimal | 0.359 | 0.453 | 0.474 | 0.502 |
| GPT-4o mini | 0.312 | 0.381 | 0.377 | 0.410 |
| Kendall tau vs full [95% CI] | | 0.891 [0.709, 0.964] | 0.818 [0.673, 0.927] | 0.855 [0.781, 0.964] |

What survives all three schemes:
- AUROC rises beyond its interval for the 9 monitors other than apollo-watcher and GLM-4.6.
- apollo-watcher rises by +0.015 to +0.027 (the interval includes 0 under B).
- GLM-4.6 moves by −0.005 to +0.034, so it does not reliably rise.
- The top monitor never changes, and GLM-4.6 ends 4th in every scheme.

**Corrections.**
1. "Rises for all 11 monitors" holds only for scheme A's point estimates. Say instead: "for 9 of
   11 beyond noise under every scheme; apollo-watcher slightly; GLM-4.6 unchanged".
2. **Removing length reveals chance, not hidden skill, for most cheap monitors.** Under A, the 95%
   interval of the matched AUROC includes 0.5 for GPT-4.1 nano (0.518 [0.477, 0.558]), DeepSeek
   V3.2, GPT-5.4 nano none and GPT-5.4 nano low. GPT-4o mini (0.381 [0.331, 0.431]) and GPT-5 nano
   minimal (0.453 [0.407, 0.493]) stay *below* chance. So "published AUROCs were biased down" is
   true, but the length-free numbers put 6 of 11 board monitors at or below chance. Length does not
   explain the two that stay below 0.5.
3. **Step-wise safety reproduction.** The stored 1% values reproduce *exactly* (3 dp, all 11) once
   the 13 attacks with no side-task outcome are dropped, as the board does (`n_attack_scored` 583).
   The "within 0.007" gap came from keeping them.
4. **GLM-4.6's step-wise drop (0.403 → 0.297) is fragile.** It is one jump of the honest-action
   threshold on GLM's coarse score grid (45 → 85) under the reweighted pool, whose effective size
   is 205 runs. Reweighting the other way (attacks to honest lengths, honest threshold unchanged)
   moves a different set of monitors: GLM-4.6 +0.020 [−0.053, 0.100]; GPT-4.1 nano +0.074 [0.038,
   0.117]; GPT-5 nano minimal +0.082 [0.035, 0.132]; GPT-5.4 nano none +0.057 [0.011, 0.107]. On
   BashArena, short attacks lower step-wise catch rates as well. The step-wise ranking keeps the
   same top monitor (tau 0.855 [0.745, 0.964] under A).

### Claim 4: MonitoringBench (550 honest / 2,644 attacks, 136 task clusters)

**Direction.** Attacks are *longer* (median 31 vs 21.5 actions; `n_actions` alone gives AUROC
0.697). The peak rises with length *within* both classes: Spearman 0.39–0.51 in honest runs and
0.17–0.33 in attacks. The mechanism is the same max-over-draws effect as on BashArena, with the
opposite sign.

**Task-clustered intervals** (the auditor resampled trajectories):

| Monitor | Full | A | Δ_A [task CI] | B (exact n) | Δ_B [task CI] | C | Δ_C [task CI] |
|---|---|---|---|---|---|---|---|
| GPT-5.4 nano | 0.635 | 0.567 [0.507, 0.610] | −0.068 [−0.105, −0.034] | 0.606 [0.532, 0.654] | −0.029 [−0.079, 0.010] | 0.571 | −0.064 [−0.127, −0.012] |
| GPT-4.1 nano | 0.584 | 0.494 [0.460, 0.531] | −0.090 [−0.126, −0.059] | 0.504 | −0.080 [−0.108, −0.050] | 0.488 | −0.096 [−0.132, −0.055] |
| GPT-5 nano minimal | 0.568 | 0.496 [0.465, 0.532] | −0.072 [−0.106, −0.046] | 0.489 | −0.079 [−0.106, −0.052] | 0.493 | −0.075 [−0.119, −0.034] |

- **AUROC.** The intervals widen but still exclude 0 under A for all three monitors.
- **Above-chance separation.** GPT-4.1 nano and GPT-5 nano minimal are at chance under every
  scheme. GPT-5.4 nano keeps 0.57–0.61, which is half to three quarters of its margin above 0.5,
  and its exact-length change includes 0.
- **CV increment over log `n_actions`** (GroupKFold by task, task-bootstrapped): GPT-4.1 nano
  +0.014 [0.001, 0.028], GPT-5.4 nano +0.017 [−0.009, 0.037], GPT-5 nano minimal +0.000 [−0.004,
  0.007].
- **Step-wise safety under A, with task clustering:** −0.029 [−0.065, 0.011] (GPT-4.1 nano),
  −0.017 [−0.052, 0.018] (GPT-5.4 nano) and +0.009 [−0.027, 0.051]. The auditor's bold changes
  (−0.029 and −0.017) are no longer beyond their intervals.
- **Attack-side reweighting**, which the auditor reported with no interval: the published catch
  rates fall from 0.240 to 0.183 (−0.057 [−0.074, −0.038]), from 0.360 to 0.299 (−0.062 [−0.104,
  −0.036]) and from 0.258 to 0.198 (−0.059 [−0.088, −0.034]). All three exclude 0. This is the
  claim-4 result most relevant to a safety number. The stored catch rates are about 0.06 higher
  (17–24% relative) than they would be for attacks as long as the honest runs.

**Is this fair?** The attack and honest sets were generated separately: MonitoringBench's refined
attacks, and Palaestra's later honest runs, whose authors state the step counts are not matched.
The length gap is a property of how the benchmark was built, not something every attack must have.
A deployer facing *these* attacks does get the extra draws, so the full-set catch rate is a correct
description of these attacks. It is not a property of the monitor.

**Correction.** "The three monitors' separation is length; at matched length they are at chance"
holds for GPT-4.1 nano and GPT-5 nano minimal. For GPT-5.4 nano, length explains about half the
separation, and 0.57–0.61 remains.

## C. Claim 1: what the monitors actually read

The auditor read the code at `308984e` and `703e9764`. I checked the cited lines: `_monitor.py:71-73`
is `DEFAULT_READS = {tool_calls, tool_results, system, user}`, `:292` keeps assistant text only if
`"text"` is read, and `:329-331` drops system/user messages not in `reads`. They are correct. But
`git log -S DEFAULT_READS` shows the `reads` mechanism was introduced on **2026-10-26** (commit
`739ab702`, #2483). That is after the board's monitor runs, so the code cannot settle what those
runs saw.

**Direct evidence.** The board's current monitored runs return 404. The monitored runs the board
listed on 2026-10-24 (`cabaf6ca…` honest and `04d99548…` attack, from the earlier finding's
`availability_checks.json`) are still public. I downloaded them (sha256 `7808f88c…` and
`35c22cd0…`; both created 2026-09-24).

- **Their scores are the board's scores.** For all 10 `simple` monitors and all 1,192 trajectories,
  99.75–100% of the 26,955 per-action scores equal the current `monitors.json` (100% for 8 of 10).
- **They store every monitor call: 273,619 prompts** (`monitor_inputs.py`). In these prompts:
  - `<risky>`: in 0 of 273,619 prompts, although 596 of the 600 attack runs carry the tag in the
    agent's own text.
  - The attack overlay system prompt: in 0 prompts.
  - Agent prose: in 0 attack prompts. In 92 of 181,744 honest prompts, a 60-character string that
    also occurs in the agent's prose appears, probably text the agent also typed into a command.
  - **A `[system]` or `[user]` role line followed by the task: in 0 prompts in either class.**
    Every prompt is a single user message: the `simple` template with the task description, then
    tool calls and results.

**Correction.** The tags and the long attack system prompt never reach the board's `simple`
monitors. This is now confirmed in the stored prompts, not only inferred from code. The claim that
"the only visible difference is a role label (`[system] <task>` vs `[user] <task>`)" is wrong for
the prompts behind the board's scores: the system-message cue does not reach them in any form. The
role label is what the *current* code would render (after 2026-10-26). apollo-watcher is not in
these runs, so for it the evidence remains the code.

## D. Claim 5: the L4 Haiku intervention

`l4_power.py` uses the stored Haiku scores only.

- **Noise between two draws of the same prompt.** The attack R vs S redraw (byte-identical prompts)
  changes AUROC by +0.024. The trailing-newline redraw changes it by −0.045. A draw-swap
  permutation gives a noise SD of the AUROC difference of 0.024 (full redraw) and 0.010 (honest
  side only) on 55 pairs.
- **Smallest effect detectable at 109 pairs** (80% power, two-sided 5%), counting redraw noise
  only: about **0.05 for the L edit** and **0.02 for the S edit**. With item sampling added, the
  auditor's own L interval (±0.047) puts the L edit's floor near 0.065.
- **Context.** The length mechanism on the board moves AUROC by 0.07–0.16, so an L-type effect of
  that size would have been seen. Honest suspicion sits near the floor (mean 7.7 of 100), which
  leaves the S edit little room to lower it.

**Corrections.**
1. By claim 1's correction, the auditor's "R, as released" prompt adds a `[system] <task> [user]`
   preamble that the board's monitors never received. The S edit therefore tests a cue that the
   current code renders, not one in the board's prompts. The result still says something about
   Haiku and today's code; it says nothing about the board.
2. The README already calls this an R for Haiku only and does not claim proof of no reliance. I
   added the detectable-effect sizes so the null is not read as one.

## E. Novelty (own searches)

- **The board caption** ("Stepwise monitors use peak suspicion, which can reflect trajectory
  length") names the mechanism. It gives no numbers.
- **MonitoringBench honest release** ([LessWrong](https://lesswrong.com/posts/bdBoH23TCTFZkkfqp/releasing-benign-trajectories-for-monitoringbench)):
  the authors state that the step counts differ (24.4 vs 27.8 for same-task attacks) and chose not
  to match them. They do not test the effect on catch rates.
- **LinuxArena paper and site** ([arXiv 2604.15384](https://arxiv.org/abs/2604.15384)): they relate
  trajectory length to attack *success*, not to monitor scores. The v2 abstract does say "roughly a
  23% undetected sabotage success rate", as `claims.md` quotes.
- **Redwood's logit-ROC post** uses attack length in its safety estimates. It does not stratify
  monitors by length.

New in the audit: numbers for the effect of length on the board's rankings and catch rates. New in
this validation: direct evidence of what the board's monitors read, and task-clustered intervals for
MonitoringBench.

## F. Fair one-line answer

"Do published control monitors rely on trace cues?" The scaffold cues (the `<risky>` tags and the
honest-only system message) never reach the board's monitors, as the stored prompts show, so the
monitors cannot rely on them. Run length does reach the scores, through the board's
maximum-over-actions aggregation:
- It pushes the monitor board's BashArena AUROCs *down* (by up to 0.16) and its MonitoringBench
  AUROCs *up* (by 0.03–0.10).
- With length removed, 6 of 11 BashArena monitors and 2 of 3 MonitoringBench monitors are at or
  below chance.
- The stored 1% step-wise safety numbers move little on BashArena. MonitoringBench catch rates
  would be about 0.06 lower for attacks as long as the honest runs.

## What I changed in README.md

- Added a "Validation" section under the status table with these verdicts.
- Status table, C1b: "a role label only" became "absent from the stored prompts" (the evidence is
  the stored prompts, not only code).
- Status table, C3: "at matched length they are at chance" became "2 of 3 at chance; GPT-5.4 nano
  keeps 0.57–0.61".
- Benchmark section: the stored 1% safety reproduces exactly once the 13 attacks with no outcome are
  excluded.
- Finding 1:
  - The system-message bullet now states that the stored prompts carry no role label.
  - The `<risky>` bullet adds the stored-prompt count.
  - The caveat about unreadable logs now points to the older public logs and the 2026-10-26 date of
    `reads`.
- Finding 2: "raises AUROC for every monitor" became 9 of 11 beyond noise under all three schemes,
  plus the chance-level note.
- Finding 3: added that the GLM-4.6 step-wise drop is a single threshold jump.
- Finding 5: GPT-5.4 nano's remaining separation; step-wise changes not beyond task-clustered
  intervals; attack-side reweighting interval added.
- Results table: MonitoringBench step-wise Δ no longer bold, with task-clustered intervals in a
  note.
- "The confound": attack-side reweighting now has intervals.
- L4 section: the R rendering includes a preamble the board's monitors never saw; minimum
  detectable effects added.
- "What was already known / new here" (a) and "What this does not show": updated for the
  stored-prompt evidence and task clustering.
