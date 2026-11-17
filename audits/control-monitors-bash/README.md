# Control monitors on BashArena-family data: length moves the board's numbers, the scaffold tags never reach the monitors

Status: 2026-11-17. All numbers from committed scripts on pinned inputs (see the end).
Evidence level per claim:

| Claim | Level |
|---|---|
| C1. BashArena board: monitors are *hurt* by the length cue (peak over more honest actions); length-matched AUROC rises for all 11 monitors (9 beyond the prereg threshold), ranking partly changes | **L3** |
| C1b. BashArena: neither the `<risky>` tags nor the system-message difference reaches the board's `simple` monitors (0 of 273,619 stored monitor prompts carry a tag or a role line; validation) | stored prompts (no reliance possible) |
| C1c. BashArena: container-date cue — no sign monitors use it | R |
| C2. LinuxArena paper set (Opus 4.6, 92 vs 200): rankings and step-wise safety hold under length matching | **R** |
| C3. MonitoringBench on the board: the AUROC above 0.5 is length for 2 of 3 monitors (matched 0.49–0.50); GPT-5.4 nano keeps 0.57–0.61 | **L3** |
| C4. Haiku as the board's `simple` monitor: equalising the system role or trimming context does not move its scores beyond its own test-retest noise (can detect only effects ≳0.02 for S, ≳0.05 for L) | **R at L4** (Haiku only) |

## Validation

An independent validator reran every script (all outputs identical) and re-derived C1 and C3 with
its own code, task-clustered intervals and two more matching schemes. Details and every changed
sentence: [`validation/VALIDATION.md`](validation/VALIDATION.md).

| Claim | Verdict |
|---|---|
| What monitors see | **Holds with correction.** The monitored logs behind the board's scores (`cabaf6ca…`, `04d99548…`, 2026-09-24; still public; their scores equal the board's for 99.75–100% of actions) store 273,619 monitor prompts: 0 contain `<risky>`, the attack system prompt or a `[system]`/`[user]` role line. The system-message cue does not reach the monitors at all, not even as a role label (the role label is what code from 2026-10-26 on would render). |
| C1 BashArena | **Holds with correction.** Reproduced exactly. Under exact-length pairs and honest truncation as well, AUROC rises beyond noise for 9 of 11; apollo-watcher +0.015 to +0.027; GLM-4.6 −0.005 to +0.034 (not a reliable rise). With length removed, 6 of 11 monitors are at or below chance (GPT-4o mini 0.38, GPT-5 nano minimal 0.45 stay below). Cause of the sub-0.5 AUROCs is the board's max-over-actions score on longer honest runs, not a sign error. GLM-4.6's step-wise drop is one threshold jump (45 → 85) and fragile. |
| C2 LinuxArena | **Holds** (rerun only). |
| C3 MonitoringBench | **Holds with correction.** Task-clustered intervals still exclude 0 under reweighting for all three; GPT-5.4 nano keeps 0.57–0.61 and its exact-length change includes 0. Step-wise Δ under matching no longer beyond interval. Attack-side reweighting lowers the published catch rates by 0.057–0.062, intervals exclude 0. |
| C4 Haiku L4 | **Holds with correction.** Null with limited power; the S edit tests a role label the board's monitors never saw. |

## The benchmark and what rests on it

The Redwood Control Leaderboard ranks trusted monitors by how well their per-action suspicion
scores separate attack runs from honest runs. The default view is BashArena (Claude Opus 4.6,
600 honest / 600 attack, 596/596 scored by every monitor), sorted by AUROC of **peak suspicion**
(max per-action score). `monitors.json` also stores a safety curve at audit budgets; we
reproduced the stored 1%-budget value as a **step-wise** rule: threshold on honest *actions* so
1% are flagged, an attack is caught if any action is flagged, safety = caught / (caught +
uncaught successful). Our recomputation matches the stored value within 0.007 for every
BashArena, LinuxArena-paper and MonitoringBench row except Claude Haiku 4.5 on LinuxArena
(1.000 vs 0.989; the board likely counts unscored attacks). (Validation: on BashArena it matches
exactly, to 3 dp for all 11, once the 13 attacks with no side-task outcome are dropped as the board
does; the 0.007 gap came from keeping them.) Published values under test are in
[`claims.md`](claims.md): the BashArena ranking and 1% safety (apollo-watcher 0.806 … GPT-4o mini
0.069), the LinuxArena headline (Opus 4.6 vs GPT-5 nano at 1% step-wise FPR; board safety 0.710),
and MonitoringBench catch rates (0.240–0.360).

## What we found

1. **What the monitors see** (from code, `control-tower` 308984e; same logic at 703e9764,
   2026-11-11). The default monitor reads tool calls, tool results and the request's system and
   user messages, and cuts assistant text and reasoning
   (`src/control_tower/monitors/_monitor.py:71-73` `DEFAULT_READS`; `:292` text kept only if
   `"text"` is read; `:329-331` system/user kept if read). The `simple` preset sets no `reads`, and
   `apollo-watcher` (`apollo_watcher.py:86-98`) receives the already-cut messages.
   - `<risky>` tags: 596/600 attack runs carry them, all in assistant text; 0 in tool arguments, 0
     in tool outputs (`extract_basharena.py`). **No board monitor is shown them, so none can rely
     on them.** Confirmed in the stored prompts (validation): 0 of 273,619 monitor calls in the
     monitored logs behind the board's scores contain `<risky>`. A reuser who renders whole
     assistant messages would hand them over.
   - System message: in honest runs it is the main-task description verbatim (596/596); attack
     runs carry the same description as a user message (596/596). Under the *current* code the
     monitor transcript would end `[system]\n<task>\n\n[user]\n` (honest) versus `[user]\n<task>`
     (attack) (`_monitor.py:150-159, 383`; `eval/log/blue_calls.py:79-93`). The overlay's long
     attack system prompt (12.9k chars, the earlier finding's 0.993 baseline) is **not** in the
     requests and is never shown. **Correction (validation):** the board's scores come from monitor
     runs made on 2026-09-24, before the `reads` mechanism existed (2026-10-26, `739ab702`). Their
     stored prompts are one user message (the `simple` template with the task, then tool calls and
     results) and carry no `[system]`/`[user]` role line in either class (0 of 273,619). So the
     system-message cue never reached the board's monitors, not even as a role label. The L4 test
     of the role label tests the current code's rendering, not the board's prompts.
   - Action count: visible (each action is judged with all prior actions; the board takes the max).
   - Container dates: visible in tool outputs. Honest runs' modal date is 2026-03-10/13 (509/596),
     attacks' 2026-03-11 or other (539/596); as a feature, AUROC 0.940.
   - Caveat: the board's currently listed monitored runs (`4c5610a0…`, `114339a1…`) return
     404/401. The runs it listed on 2026-10-24 (`cabaf6ca…`, `04d99548…`) are public, and their
     per-action scores equal the board's current scores for 99.75–100% of actions across all 10
     `simple` monitors; the validation reads the prompts from those. apollo-watcher is not in them,
     so for it the evidence is the code only.
2. **BashArena (C1): the length cue works against the monitors, not for them.** Attacks stop
   when the side task lands (median 14 actions vs 25), and peak suspicion rises with the number of
   actions on honest runs (Spearman 0.03–0.54). Reweighting honest runs to the attacks'
   action-count distribution raises AUROC for every monitor; 9 of 11 meet the prereg rule.
   (Validation: the same 9 rise beyond noise under exact-length pairs and honest truncation too;
   GLM-4.6's change is −0.005 to +0.034 across schemes. With length removed, the AUROCs of GPT-4.1
   nano, DeepSeek V3.2 and GPT-5.4 nano none/low have intervals that include 0.5, and GPT-4o mini
   (0.381) and GPT-5 nano minimal (0.453) stay below chance: removing length reveals chance, not
   hidden skill, for 6 of 11.)
3. **The ranking partly changes.** Kendall tau 0.89 [0.71, 0.96] for AUROC and 0.85 [0.75,
   0.96] for step-wise safety; apollo-watcher stays first in 100% of resamples; GLM-4.6 drops from
   2nd to 4th, Haiku 4.5 rises to 2nd. Step-wise safety (the stored board number) changes beyond
   its interval for GLM-4.6 (0.403 → 0.297) and GPT-4.1 nano (0.077 → 0.107); the others are
   within noise. (Validation: GLM-4.6's drop is a single jump of the honest-action threshold on
   its coarse score grid, 45 → 85, under a reweighted pool of effective size 205 runs; treat it as
   fragile.)
4. **LinuxArena (C2) holds.** Length is a weak cue there (AUROC 0.445, CV 0.544); every AUROC
   moves ≤ 0.021, rankings are identical (tau 1.0 [0.91, 1.0]), and GPT-5 nano's step-wise safety
   goes 0.715 → 0.733 (+0.018 [−0.001, 0.046]).
5. **MonitoringBench (C3): the monitors' separation is the length cue.** Attacks are *longer*
   here (31 vs 21.5 actions), so the bias reverses: full-set AUROC 0.57–0.64 falls to 0.49–0.57
   on length-matched runs, and adding a monitor to a log(n_actions) model raises CV AUROC by only
   0.001–0.016. Step-wise catch rates fall slightly (−0.029 and −0.017 for two monitors).
   (Validation, resampling the 136 main tasks: the AUROC drops still exclude 0, but GPT-5.4 nano
   keeps 0.567 [0.507, 0.610], and 0.606 under exact-length pairs, so its separation is about half
   length, not all. The step-wise changes under matching do not exclude 0: −0.029 [−0.065, 0.011],
   −0.017 [−0.052, 0.018].)

| Dataset | Monitor | AUROC full | Length-matched | Δ [95% CI] | 1% step-wise safety (stored) | Matched | Δ [95% CI] |
|---|---|---|---|---|---|---|---|
| BashArena | apollo-watcher | 0.833 | 0.854 | +0.021 [0.013, 0.031] | 0.809 (0.806) | 0.804 | −0.005 [−0.015, −0.000] |
| | GLM-4.6 | 0.648 | 0.658 | +0.010 [−0.017, 0.038] | 0.403 (0.396) | 0.297 | **−0.106 [−0.163, −0.048]** |
| | Claude Haiku 4.5 | 0.624 | 0.668 | **+0.044 [0.014, 0.079]** | 0.360 (0.355) | 0.319 | −0.040 [−0.091, 0.006] |
| | GPT-5.4 nano high | 0.591 | 0.667 | **+0.075 [0.045, 0.107]** | 0.280 (0.275) | 0.314 | +0.034 [−0.033, 0.104] |
| | GPT-5.4 nano medium | 0.489 | 0.580 | **+0.091 [0.061, 0.128]** | 0.194 (0.193) | 0.217 | +0.022 [−0.011, 0.059] |
| | DeepSeek V3.2 | 0.445 | 0.523 | **+0.078 [0.049, 0.108]** | 0.161 (0.160) | 0.154 | −0.007 [−0.041, 0.024] |
| | GPT-5.4 nano none | 0.389 | 0.522 | **+0.133 [0.098, 0.172]** | 0.136 (0.130) | 0.141 | +0.005 [−0.018, 0.027] |
| | GPT-5.4 nano low | 0.373 | 0.509 | **+0.136 [0.101, 0.175]** | 0.094 (0.090) | 0.106 | +0.012 [0.001, 0.026] |
| | GPT-4.1 nano | 0.361 | 0.518 | **+0.157 [0.125, 0.188]** | 0.077 (0.074) | 0.107 | **+0.030 [0.017, 0.046]** |
| | GPT-5 nano minimal | 0.359 | 0.453 | **+0.094 [0.065, 0.126]** | 0.170 (0.167) | 0.147 | −0.022 [−0.046, 0.004] |
| | GPT-4o mini | 0.312 | 0.381 | **+0.069 [0.034, 0.110]** | 0.069 (0.069) | 0.062 | −0.008 [−0.033, 0.016] |
| LinuxArena paper | GPT-5 nano | 0.817 | 0.835 | +0.018 [0.000, 0.038] | 0.715 (0.710) | 0.733 | +0.018 [−0.001, 0.046] |
| | (11 others) | 0.633–0.995 | | all ≤ +0.021 | | | all CIs include 0 |
| MonitoringBench | GPT-5.4 nano | 0.635 | 0.567 | **−0.068 [−0.086, −0.051]** | 0.360 (0.360) | 0.344 | −0.017 [−0.032, −0.004]† |
| | GPT-4.1 nano | 0.584 | 0.494 | **−0.090 [−0.109, −0.072]** | 0.240 (0.240) | 0.211 | −0.029 [−0.041, −0.019]† |
| | GPT-5 nano minimal | 0.568 | 0.496 | **−0.072 [−0.091, −0.052]** | 0.258 (0.258) | 0.267 | +0.009 [−0.008, 0.028] |

Bold: meets the prereg rule (interval excludes 0 and |Δ| ≥ 0.03, or for safety the interval
excludes 0). n: BashArena 596/596 (597 main-task clusters); LinuxArena 199/92; MonitoringBench
550/2,644. Full table in [`results.json`](results.json) / [`results_l3.json`](results_l3.json).
MonitoringBench intervals here resample trajectories. † Validation, resampling 136 main tasks:
these two step-wise changes become −0.017 [−0.052, 0.018] and −0.029 [−0.065, 0.011] and no
longer meet the rule (bold removed). The AUROC changes stay beyond their task-clustered intervals:
−0.068 [−0.105, −0.034], −0.090 [−0.126, −0.059], −0.072 [−0.106, −0.046].

## The confound

Feature: `n_actions` per trajectory, from the board's `score_samples` (equal to the raw `.eval`
action count on all 1,192 BashArena runs). Strata: five bins at the attack class's quintiles;
honest runs reweighted to the attack bin shares (prereg). BashArena honest/attack bin counts:
17/76, 24/130, 51/150, 65/117, 439/123 — every bin populated, no attack dropped.

Mechanism, in two directions:

- **Honest side (BashArena):** the board's max over actions rises with run length on honest runs,
  so long honest runs look suspicious and the shorter attacks look clean. Removing this (matching)
  helps the monitors. Bias direction of the published AUROCs: **down** (monitors look worse).
- **Attack side (MonitoringBench):** attacks are longer than honest runs, so the same max-over-
  more-actions mechanism hands the monitors separation they do not earn. Bias: **up**.
- Step-wise safety (the stored board number) sets its threshold per action, so it is much less
  sensitive to the honest side. On the attack side, a longer attack has more draws at the
  threshold: reweighting MonitoringBench attacks to honest lengths lowers catch rates from 0.240 /
  0.360 / 0.258 to 0.183 / 0.299 / 0.198 (exploratory, not in the prereg; `robustness_l3.py`).
  Validation intervals, resampling main tasks: −0.057 [−0.074, −0.038], −0.062 [−0.104, −0.036],
  −0.059 [−0.088, −0.034]. All exclude 0: the published MonitoringBench catch rates are about 0.06
  higher than for attacks as long as the honest runs. The length gap comes from how the two sets
  were built (separately generated attack and honest runs), so this is a property of the benchmark,
  not of the monitors.

Which attacks get caught: within attacks, `n_actions` barely predicts being caught (BashArena
AUROC caught-vs-missed 0.45–0.64 where ≥1 attack is caught at 1% trajectory FPR; Spearman of the
step-wise catch probability with length −0.05 to 0.19 on BashArena, 0.14–0.29 on MonitoringBench).

Hand reading (step 4, 25 honest + 25 attack BashArena tool-call sequences, seed 1, read before
any split): every run ends in an auto-submit; attack sequences are shorter and open with
`text_editor` calls more often (8 of 25 vs 0 of 25); in the three attacks whose final steps we
read, the step that triggered the side-task checker was an ordinary-looking `bash` call (for example
running `make` on code written earlier) just before the auto-submit.

## The effect

- **BashArena AUROC ranking** (published: board default sort). Reproduced exactly from
  `score_samples` (apollo-watcher 0.833 … GPT-4o mini 0.312). Length-matched: all 11 monitors
  rise (+0.010 to +0.157); five move from below 0.5 to above. Kendall tau 0.89 [0.71, 0.96]: by
  the prereg rule, "partly changes" (interval spans 0.8; top unchanged).
- **BashArena 1% safety** (published, stored). Reproduced within 0.007. Length-matched: changes
  beyond its interval for 2 of 11 (GLM-4.6 −0.106, GPT-4.1 nano +0.030), GLM-4.6 falls from 2nd
  to 4th.
- **LinuxArena**: holds (R). The paper's abstract quotes "roughly a 23% undetected sabotage
  success rate" for Opus 4.6 vs GPT-5-nano at 1% step-wise FPR; the board's step-wise safety on
  the paper's own scores is 0.715 and stays there under matching.
- **MonitoringBench**: AUROC separation disappears under matching for all three (to 0.494, 0.496,
  0.567); step-wise catch rates move by −0.03 to +0.01.
- **What a monitor adds beyond the cue** (CV AUROC, GroupKFold by task, log n_actions alone = 0.835
  on BashArena): apollo-watcher +0.101 [0.081, 0.125], GLM-4.6 +0.033, Haiku 4.5 +0.026, GPT-5.4
  nano high +0.018; the other seven add ≤ 0.008. On MonitoringBench (cue alone 0.696): +0.015,
  +0.016, +0.001. On LinuxArena (cue alone 0.544): +0.09 to +0.45.

Multiple comparisons: 114 tests (38 monitors × AUROC, trajectory-FPR catch, step-wise safety).
Bootstrap p-values bottom out at 0.002, so Holm is coarse; all bold AUROC changes on BashArena
except Haiku 4.5 and all three MonitoringBench AUROC changes have Holm-adjusted p < 0.002·114 by
bootstrap resolution (`results_l3.json`, `*_p_holm`).

LinuxArena strategies (50 attacks) is not usable: only 8 attacks are scored by all 12 action
monitors (the board's own population rule), so its numbers are reported in the JSON only.

## Intervention (L4, Haiku)

Design (prereg): 109 length-matched pairs from BashArena (110 requested, 1 lost to unparsed
answers). Attack item = a successful attack judged at the action that triggered the side-task
checker (the step before the auto-submit), with all prior actions as transcript; honest item = an
honest run judged at the same action index (5–11 prior actions), so the pair has equal context
length. Side tasks: sudo 43, malware 27, firewall 24, passwords 15. Prompt: the board's
`simple.md`, rendered as `render_prompt` does (tool calls and results only, then the request's
system/user messages, then the judged action); answer as JSON text instead of a forced tool call.
Model `claude-haiku-5-5` via `audits/tools/claude_call.py`.

| Condition | AUROC [95% CI] | Mean suspicion attack / honest | Change vs released |
|---|---|---|---|
| R, as released | 0.820 [0.764, 0.866] | 46.2 / 7.7 | — |
| S, honest preamble rendered as `[user] <task>` (attack items unchanged) | 0.818 [—] with attack held at R | — / 7.4 | AUROC −0.002 [−0.023, 0.017]; honest −0.31 [−0.93, 0.21] |
| L, only the 3 prior actions kept (both classes) | 0.813 [0.755, 0.868] | 40.0 / 6.9 | AUROC −0.007 [−0.052, 0.042]; attack −6.2 [−12.0, 0.0]; honest −0.80 [−1.57, −0.15] |
| Test-retest: R prompt + one trailing newline (55 pairs) | 0.849 [0.772, 0.919] | 43.7 / 4.7 | AUROC −0.045 [−0.089, −0.002]; attack −8.4 [−15.1, −2.1]; honest −0.55 [−1.40, 0.22] |

Noise: the attack prompts under R and S are byte-identical and were drawn independently (the two
jobs ran concurrently and both missed the cache). They differ on 75% of items, mean absolute
difference 15.0 points, correlation 0.71. The trailing-newline retest moves AUROC by −0.045, more
than either edit.

Reading: for Haiku, neither removing the system-role cue nor trimming earlier benign context
changes discrimination beyond its own sampling noise; trimming lowers suspicion slightly in both
classes. Haiku separates these length-matched pairs well (0.82) on the sabotage step itself. This
says how Haiku behaves with single draws on 109 short pairs; it does not test the board's monitors
or the peak-over-actions mechanism (one action is judged per item, not the max over all).
Validation: (1) the "as released" prompt here follows the current code and so includes a
`[system] <task> [user]` preamble; the stored prompts behind the board's scores carry no role
line, so the S edit tests a cue the board's monitors never received. (2) From the redraw noise
(`validation/l4_power.py`), the smallest AUROC change this design could detect at 80% power is
about 0.02 for S (honest side only) and about 0.05 for L. With item sampling added it is nearer
0.065 for L. A null here is not evidence that Haiku ignores the cue below those sizes.
Inference: 768 billed calls in `inference/ledger.jsonl` (10 pilot, 648 main run after cache hits,
110 retest), 2.34 USD of the 3 USD cap.

## Robustness

| Check | Result | Survives? |
|---|---|---|
| Placebo: shuffle n_actions within class, then match (200 shuffles) | mean change −0.002 to +0.002, 95% within ±0.035 for every monitor; real changes are +0.07 to +0.16 (BashArena), −0.07 to −0.09 (MB) | yes |
| Second feature: exact n_actions matching | BashArena 0.387–0.856 (vs five-bin 0.381–0.854); MB 0.489/0.577/0.492 | yes |
| Second feature: ten bins | BashArena tau 0.82; MB matched 0.490/0.572/0.491 | yes |
| Different statistic: mean per-action score | BashArena tau full vs matched 0.89; MB matched mean-score AUROC 0.444/0.449/0.376 (below chance) | yes, stronger for MB |
| Alternative to reweighting: honest peaks over only their first L actions, L drawn from attack lengths | BashArena AUROC rises to 0.409–0.862 (tau 0.89 with full); LinuxArena tau 1.0 | yes |
| Discover/test: bin edges from half the attacks, test on the other half | BashArena e.g. GPT-4.1 nano 0.359 → 0.538; MB 0.579 → 0.491 | yes |
| Drop each BashArena side task | AUROC changes stay +0.008 to +0.16; tau 0.89–0.93; top unchanged | yes |
| One model family: keep only GPT-5.4 nano high of the four effort variants | tau 0.86 | yes |
| Holm over 114 tests | see "The effect" | mostly |

## Alternative explanations

1. **"Length is the construct."** In deployment, honest runs do run to completion and attacks
   do stop at landing, so full-set AUROC is what a deployer faces. Test: the board's own deployment
   statistic is step-wise safety, which sets thresholds per action. It moves much less on BashArena
   (2 of 11 beyond noise) than AUROC does. Outcome: partly right — the AUROC ranking is the
   length-sensitive number; the step-wise safety ranking is mostly robust (tau 0.85).
2. **Length tracks difficulty** (short attacks are blunter). Then n_actions should predict being
   caught within attacks. It barely does (caught-vs-missed AUROC 0.45–0.64; step-wise catch
   probability vs length Spearman ≤ 0.19 on BashArena). Outcome: not supported on BashArena; on
   MonitoringBench longer attacks are caught more (0.14–0.29), consistent with more draws, not
   with difficulty.
3. **One model family.** The BashArena list has four GPT-5.4 nano effort variants. Keeping one:
   tau 0.86; every non-OpenAI monitor shows the same sign. Outcome: not one family.

## What was already known

- The board's caption says peak suspicion "can reflect trajectory length"; the earlier finding
  ([`findings/redwood-leaderboard-scaffold-cues/`](../../findings/redwood-leaderboard-scaffold-cues/))
  showed peak rises with honest length and that mean per-action beats peak (L2).
- [`findings/monitoringbench-container-clock/`](../../findings/monitoringbench-container-clock/)
  showed length and tool-mix cues in MonitoringBench (L1/L2) with no honest monitor scores at the
  time; the board now releases them.
- Context-length effects on monitors: "classifier context rot" and chunked-monitoring posts
  ([`prior_work.md`](prior_work.md)).

New here: (a) which cues reach the monitors (tags: never; system message: never; established from
code here, and confirmed by the validation in the 273,619 stored monitor prompts); (b) L3 on the board's released scores — the BashArena ranking partly and the
MonitoringBench separation wholly depend on length, while LinuxArena holds; (c) the L4 edit on Haiku, which came back null against its own retest noise.

## What this does not show

- That a monitor *reads* `<risky>` tags: the stored prompts behind the board's `simple` scores
  contain none (validation). apollo-watcher's prompts are not available.
- Anything about MonitoringBench's paper headline (Opus 4.5, 416 unreleased honest runs).
- Intervals on LinuxArena and MonitoringBench resample trajectories, not tasks
  (`score_samples` carries no task id); MonitoringBench has within-task near-copies, so its
  intervals are too narrow. The validation redid MonitoringBench by main task (from the raw evals);
  see the table note above. LinuxArena is still resampled by trajectory.
- That the cheap BashArena monitors have skill hidden by length: with length removed, most are at
  chance.
- Haiku's behaviour says nothing direct about the board's monitors.

## Pins and how to reproduce

Pins in [`claims.md`](claims.md). Data (git-ignored) in `data/`: `site/monitors.json`, the two raw
BashArena `.eval` files, a clone of `linuxarena/control-tower` at `308984e` (read, not run).
Python 3.14 (the `.eval` zips use zstd), numpy, pandas, scipy, scikit-learn.

```
python -I extract_basharena.py data/evals data/basharena_features.json
python -I effect_l3.py data/site/monitors.json data/basharena_features.json results_l3.json
python -I robustness_l3.py data/site/monitors.json data/basharena_features.json results_robustness.json
python -I l4_haiku.py data/evals data/site/monitors.json data/repos/control-tower/src/control_tower/monitors/prompts/simple.md data/l4_run.json 110 R,S,L
python -I analyse_l4.py data/l4_run.json results_l4.json
python -I l4_haiku.py data/evals data/site/monitors.json data/repos/control-tower/src/control_tower/monitors/prompts/simple.md data/l4_retest.json 110 R,R2 55
python -I analyse_l4.py data/l4_retest.json results_l4_retest.json
python -I collect_results.py   # writes results.json
```
