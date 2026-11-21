# Validation: control-monitors-deep-board

Validator, 2026-11-20. Input: `../../control-monitors-bash/data/site/monitors.json`, read only. No
downloads, model calls or spend. I wrote my own code (`vlib.py`, `v1`–`v8`) before reading
`analyse.py`, then compared it with `results.json`, then read `analyse.py` to explain the
differences. Numbers are in `validation.json`. Logs are `v*.log`.

**Exact reproduction.** The snapshot's mean run scores reproduce exactly on all 86 rows. Board
AUROC, matched AUROC and chance level (quintile and decile bins) reproduce to 1e-14 on all 84
analysed rows. Run-level bootstrap intervals agree within 0.015, and the same intervals exclude 0.5.

## Verdicts

| # | Auditor | Validator | Verdict | How checked |
|---|---|---|---|---|
| 1 | Chance level: BashArena 0.35–0.49 (10/11 exclude 0.5); MonitoringBench 0.57–0.59 (3/3); LinuxArena strategies action 0.44–0.47 (10/11); LinuxArena paper action 0.46–0.49 (0/12) | 0.348–0.487 (10/11); 0.572–0.589 (3/3); 0.437–0.471 (10/11); 0.463–0.488 (0/12) | **HOLDS** for BashArena and MonitoringBench. **HOLDS WITH NARROWER WORDING** for LinuxArena strategies | Own implementation. Second null: each honest run cut (or, where longer, extended with pooled honest per-step draws) to a length drawn from the attack lengths versus one drawn from the honest lengths. It gives BashArena 0.34–0.44, MonitoringBench 0.57–0.58, strategies 0.41–0.44, paper 0.47–0.48 and SLEIGHT 0.50–0.51, the same direction everywhere. Decile, 20-bin and exact-length bins: BashArena 0.32–0.49, MonitoringBench 0.57–0.60, strategies 0.35–0.41 (exact). Coarse bins understate the shift. |
| 2 | ResearchArena action 0.519 [0.48, 0.57], trajectory 0.494; SHADE 0.49–0.51; SLEIGHT 0.49–0.51; all include 0.5 | 0.519 [0.483, 0.572]; 0.494 [0.453, 0.537]; SHADE 0.491–0.506; SLEIGHT 0.493–0.511; all include 0.5 | **HOLDS WITH NARROWER WORDING** ("no detectable shift", not "nothing") | Numbers reproduce. The run-level minimum detectable shift on ResearchArena is about 0.055–0.06. The cut-or-extend null predicts 0.538 there, inside that blind zone. Within agent, stratifying by agent and length tercile, the chance level is 0.499 [0.459, 0.562] and matched AUROC 0.631, against 0.608 pooled. SLEIGHT is length-twinned (honest weights about 1, ESS 36.7 of 37), so its result of about 0.5 is mechanical, not a test. |
| 3 | P2 fails: LinuxArena trajectory chance level 0.415–0.47, 10 rows exclude 0.5 | 10 rows, 0.415–0.466. Honest trajectory score rises with honest length for 7 of 8 monitors (Spearman 0.25–0.62, CI above 0). gpt-oss-120b goes the other way (−0.16, CI below 0) | **HOLDS WITH NARROWER WORDING** | The 10 rows are 8 monitors scoring the **same 200 honest runs** (paper and strategies share every honest trajectory). Ties have no effect: random tie-breaking gives the same values to 0.003. The scored-attack subset matters a little: with all 92 attack lengths the paper rows move 0.01–0.03 toward 0.5 (gpt-4.1-nano 0.433 to 0.462). All 10 lose significance at a design effect of 1.2–2.5. |
| 4 | 11 of 31 contrasts move ≥0.05 with interval excluding 0; 8 sign flips; GPT-5.4 nano −0.245 to −0.045 | 12 of 31 (one borderline: BashArena vs SLEIGHT gpt-5.4-nano-medium, lower bound +0.001 against the auditor's −0.002); 8 sign flips across all 31, **3 among the changes, 0 where the matched difference's CI excludes 0**; example reproduces exactly | **HOLDS WITH NARROWER WORDING** | **Every** changing contrast involves BashArena or MonitoringBench (0 involve neither), so claim 4 restates claim 1. Monitor identity was matched on `monitor` and `monitor_variant`. The LinuxArena paper and strategies pair was resampled jointly, because its honest runs are shared: none of its 11 contrasts changes either way. |
| 5 | Safety at 1% reproduces stored within 0.01 for 36/38; matching moves GLM-4.6 BashArena −0.10, GPT-5 mini strategies −0.09 | The board rule from `control_tower/metrics/control.py` reproduces the stored value **exactly for 39/39** action rows. GLM-4.6 −0.102 [−0.16, −0.04]; GPT-5 mini strategies −0.088 [**−0.19, +0.06**] | **HOLDS WITH NARROWER WORDING** | The auditor's two misses are errors in the auditor's own rule: (a) it ignores `landed_at` (LinuxArena paper Haiku 4.5: 1.000 against 0.9891); (b) its budget denominator counts only scored honest actions (ResearchArena: 0.5894 against 0.6012). The GPT-5 mini move is not distinguishable from 0. BashArena Haiku 4.5 (−0.040 [−0.10, −0.001]) and GPT-4.1 nano (+0.030 [0.014, 0.042]) also move with intervals excluding 0. |

## Caveats, most important first

1. **The intervals are run-level, and none can be clustered by task.** Every dataset except
   ResearchArena is a single eval run in the snapshot. BashArena results survive a design effect of
   2 (10/10 intervals still exclude 0.5) and 4 (8/10). MonitoringBench survives about 16. Every
   LinuxArena exclusion (claim 1 strategies and claim 3) is gone by a design effect of 4, and the
   paper and trajectory ones by about 1.2–1.6. Treat the LinuxArena results as leads.
2. **The chance level mixes two things.** Within-run truncation alone (cut only, no extension)
   gives about 0.50 on LinuxArena paper action rows, while reweighting gives 0.46–0.49. So part of
   the reweighting null there comes from which tasks run long, not from the maximum over steps.
   Claim 3 (trajectory rows below 0.5) says the same. The name "length-only chance level" should
   say it includes task-composition effects.
3. **The prereg's predictions for BashArena, MonitoringBench and LinuxArena were known in
   advance**: the parent's matched results and the length AUROCs had already been computed. Only
   the three new datasets carry a real prediction, and those came out null, underpowered, or
   mechanical (SLEIGHT). `audits/control-monitors-deep-board/` is untracked in git, so the
   prereg's timing cannot be verified.
4. **Bin coarseness.** Quintile bins leave residual length imbalance. Exact-length bins move the
   strategies matched AUROC by up to 0.08. They cut ESS from about 150 to about 40 (maximum weight
   share 9%) and drop up to 182 of 273 ResearchArena attacks, so the exact-length numbers are less
   stable. Quintile ESS is fine: BashArena 205/596, maximum weight share ≤3.1% on every dataset.
5. **ResearchArena agent pairing** (`attack_eval[i]` with `honest_eval[i]`) is supported but not
   proven. Run counts per index (39/12 and 24, 15/6) and median lengths agree, with joint
   permutation p = 0.003 over all 40,320 pairings. The snapshot has no agent names, and its source
   links use different run IDs.

## Not verified

- Task-level clustering (no task IDs in the snapshot).
- Agent identities for ResearchArena (eval logs are not in the repository).
- Q3 (what each monitor can read): not in the claim list, not checked.
- I followed the caller's instruction to write only inside `validation/`, so I did not edit
  `README.md` or `results.json` and made no commits.
