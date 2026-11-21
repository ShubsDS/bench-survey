# Essay outline: benchmarks should survive adversarial scrutiny

Status: 2026-11-20. Argument structure only, built on the fact-checked versions of findings 1–4
in [`FINDINGS.md`](../FINDINGS.md). Numbers are from [`verdicts/`](verdicts/); figures are in
[`figures/`](figures/).

## Thesis

A benchmark number gets cited as a claim about a model: "resists injection", "the monitor catches
sabotage", "monitor A beats monitor B". Each such claim has cheap alternative explanations. Readers
will not run the checks that rule them out, so the benchmark should ship with them, and its headline
number should be the one that survives them.

The claim is not that these benchmarks are wrong. Their published numbers reproduce exactly. The
claim is that the headline number supports a narrower sentence than the one it is cited for.

A note on the title: "adversarial robustness" already means robustness of a model to adversarial
inputs. What the essay asks for is adversarial scrutiny of the benchmark itself.

## Three checks, one case each

Each case is one question an adversarial reader would ask, and what the answer does to the reading.

### 1. Did the test actually happen? (AgentDojo)

- **Cited as:** a low attack success rate means the model resists prompt injection.
- **Check:** in each "secure" run, did the agent ever see the injected text?
- **Result:** for the median of 20 models, 24% of "secure" runs never showed the agent the
  injection (up to 57% for one model). Adding runs where the model failed the injected task when
  asked directly, 48% for the median model, from 9% to 79%.
- **Strength:** the strongest of the three. The never-saw count is deterministic, covers all
  12,580 runs of the published models, and three detectors agree on every run. The second half is
  an upper bound.
- **Already disclosed:** the paper says weak models often fail the attacker's goal. It does not
  report exposure.
- **Figure:** `fig1_agentdojo_secure_runs`.

### 2. What could the measured system see? (MRT / SHADE-Arena)

- **Cited as:** monitors catch sabotaging agents almost perfectly.
- **Check:** what is in the monitor's input?
- **Result:** the "unaware" agents plan in tags the monitor reads. Deleting those plans from 30
  runs drops one monitor's AUROC from 0.998 to 0.85 (0.62–0.99 resampling the five tasks), mostly on
  one task.
- **Strength:** the design fact is solid. The size is not: 30 runs, one task carrying it, a monitor
  the paper did not use, and a post hoc deletion.
- **Lead with the paper's own numbers.** On 17 tasks it reports about 0.96 for unaware agents and
  about 0.67 for agents with a hidden scratchpad. That is better evidence for the same point than
  the re-scoring, which then serves as the matched illustration.
- **Figure:** `fig2_mrt_visible_plans`.

### 3. Does a nuisance variable drive the metric? (BashArena monitor board)

- **Cited as:** the board's default ranking orders monitors by detection skill.
- **Check:** match honest and attack runs on length.
- **Result:** the default metric takes a maximum over steps, and honest runs are longer, so 7 of 11
  monitors score below chance as published. Matching changes 9 of 11 scores, and 4–6 of 11 still
  cannot be told from chance.
- **Strength:** reproduces exactly from the board's data. The count depends on the matching method;
  the confound does not.
- **Already disclosed:** a tooltip says peak suspicion can reflect trajectory length. The board
  still sorts by it by default, and its step-wise safety metric is barely affected.
- **Figure:** `fig3_basharena_length`.

## The contrast case: a measurement that held (Palisade)

Use this as the counterexample, not as a fourth failure.

- Re-scoring by behaviour finds slightly more sabotage than reported (o3: 83 against 79 of 100).
  The measurement survived an adversarial re-score.
- The self-preservation reading came from press coverage. Palisade's paper attributes the behaviour
  mainly to unfinished tasks.
- Point for the essay: the standard is passable, and a robust measurement does not protect against
  a loose interpretation downstream.
- **Figure:** `fig4_palisade_reasons`.

## The same standard applied to the critique

This is the part that makes the essay credible, and it is the audit's own data.

- A second agent cut back the first agent's headline in 12 of 14 audits.
- The four strongest findings were then checked a third time, and all four needed narrower wording:
  four models chosen after the results were seen (AgentDojo), a length direction stated backwards
  (BashArena), one task carrying the effect (MRT), two releases merged into one sentence (Palisade).
- The re-checks needed no new model calls. They were possible only because all four projects
  released per-run logs, which is itself the practice the essay argues for.

## What the essay should not claim

- That any benchmark's main conclusion failed. None did.
- That the authors hid anything. In all three cases part of the issue is in the paper or on the
  board. The argument is that a caveat in an appendix or tooltip does not stop the headline number
  being cited without it.
- "56–70% for four models", "6 of 11 at or below chance", "attack transcripts are longer", "the
  paper's design states this", or "2 of 3,868" as a bare ratio. Each is corrected in `FINDINGS.md`.
- That 0.85 is how well a monitor catches agents that hide their plans.

## What to ask of a benchmark

1. Release per-run logs.
2. Report how many test cases were delivered, not only how many were passed.
3. State what each party in the evaluation can see.
4. Make the default headline metric the one that survives matching on obvious nuisance variables
   such as length.
5. Publish the adversarial checks that were run and what they changed.
