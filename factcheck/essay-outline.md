# Essay outline: benchmarks should survive adversarial scrutiny

Status: 2026-11-21. Argument structure only, built on the fact-checked versions of findings 1–4
in [`FINDINGS.md`](../FINDINGS.md) and two follow-ups: AgentDojo re-run on current Claude models
([`agentdojo-deep-current-models`](../audits/agentdojo-deep-current-models/)) and the monitor board
across datasets ([`control-monitors-deep-board`](../audits/control-monitors-deep-board/)). Numbers
are from [`verdicts/`](verdicts/) and those two folders; figures are in [`figures/`](figures/).

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
- **Result, released logs (20 models, 2024 to February 2025):** for the median model, 24% of
  "secure" runs never showed the agent the injection (up to 57% for one model). Adding runs where
  the model failed the injected task when asked directly, 48% for the median model, from 9% to 79%.
- **Result, current models:** we re-ran the benchmark on Claude Haiku 5.5 and Sonnet 5.5. They were
  shown the injection in 192 of 194 and 174 of 174 runs, never followed it, and told the user
  about it almost every time. The never-saw share is 1% and 0%. Claude 3.7 Sonnet, the strongest
  model in the released logs, was already at 3%.
- **How to use both halves.** The case is no longer "this benchmark's secure runs are empty". It
  is: the share of delivered tests ran from 54% to 100% across models, so the same headline number
  mixed two things for some models and not for others, and a reader could not tell which without
  the logs. The essay ran the check on current models and reports that the problem is gone there.
- **Strength:** the released-log half is the strongest result in the essay. The never-saw count
  is deterministic, covers all 12,580 runs of the published models, and three detectors agree on
  every run. The failed-when-asked half is an upper bound. The current-model half is validated but
  comes from a text-only harness, two models and one developer; its attack success rate is not
  comparable with the published table.
- **Already disclosed:** the paper says weak models often fail the attacker's goal. It does not
  report exposure. A preprint from October 2026 (arXiv 2610.14477) measures exposure for four
  small local models and states the principle. Cite it as stating the principle first; read it
  before citing, since so far only an agent has.
- **A side observation, three runs only:** once agents warn the user about an injection, a scorer
  that matches a substring in the answer counts the warning as a successful attack. All 3 scored
  successes on the current models are of this kind.
- **Figures:** `fig1_agentdojo_secure_runs`; `fig_exposure` in the re-run's folder.

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
- **Across datasets:** a monitor with no skill would score 0.35–0.49 on BashArena and 0.57–0.59 on
  MonitoringBench. GPT-5.4 nano looks 0.25 apart on the two as published and 0.05 apart with length
  matched. The three other datasets show no detectable shift, so this is not a claim about the
  whole board.
- **Current models:** the attackers here are Claude Opus 4.5 and 4.6 and the monitors include
  GPT-5.4 nano. This case never rested on old models.
- **Already disclosed:** a tooltip says peak suspicion can reflect trajectory length. The board
  still sorts by it by default, and its step-wise safety metric is barely affected.
- **Figures:** `fig3_basharena_length`; `fig_chance_level` in the board follow-up's folder.

## The contrast case: a measurement that held (Palisade)

Use this as the counterexample, not as a fourth failure.

- Re-scoring by behaviour finds slightly more sabotage than reported (o3: 83 against 79 of 100).
  The measurement survived an adversarial re-score.
- The strong self-preservation reading is in press coverage. Palisade's paper attributes the
  behaviour mainly to unfinished tasks, though its July 2025 write-up raises self-preservation as
  one hypothesis.
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
- Then the strongest finding was tested for generality, and it failed: on two current Claude
  models AgentDojo's exposure problem is absent. The pre-registered rule said "does not carry
  over", and the essay says so. Extending the monitor-board finding to three more datasets also
  came back as no detectable shift.
- Our own re-run has the kind of problem the essay describes. The tool that calls the model adds
  hidden text to every request, including today's real date, which made agents hesitate over
  dates in a benchmark set in 2022–2024. It is reported as a limit, with a check that it did not
  change exposure.

## Answering "these are old models"

A reader will raise this first. The answer differs by case, and the essay should give it up front.

| Case | Models behind the result | Does it hold on current models? |
|---|---|---|
| AgentDojo | 20 models, 2024 to February 2025 | No, for the two tested: exposure is 99–100% |
| Monitor board | Attackers Claude Opus 4.5 and 4.6; monitors include GPT-5.4 nano | It is a current-model result, on two of the board's datasets |
| MRT / SHADE-Arena | The paper's 2025 agents; one small current monitor in the re-scoring | Not tested on current agents |
| Palisade | 2025 models | Not tested |

The general point survives this: whether a test was delivered is a property of the model as well
as the benchmark, so it has to be reported per model, and it has to be re-measured as models
change. A benchmark that reported it would have shown its own saturation.

## What the essay should not claim

- That any benchmark's main conclusion failed. None did.
- That the authors hid anything. In all three cases part of the issue is in the paper or on the
  board. The argument is that a caveat in an appendix or tooltip does not stop the headline number
  being cited without it.
- "56–70% for four models", "6 of 11 at or below chance", "attack transcripts are longer", "the
  paper's design states this", or "2 of 3,868" as a bare ratio. Each is corrected in `FINDINGS.md`.
- That 0.85 is how well a monitor catches agents that hide their plans.
- That current models benefit from non-exposure on AgentDojo. They do not.
- Any attack success rate or utility from the re-run next to the published table. The harness
  differs. Say "the fixed attack succeeded in none of 368 runs through our harness" and stop.
- That the monitor board's scores are unreliable in general. Two of seven datasets are clearly affected,
  and the metric control researchers use holds.

## What to ask of a benchmark

1. Release per-run logs.
2. Report how many test cases were delivered, not only how many were passed, per model, and
   again when new models are added.
3. State what each party in the evaluation can see.
4. Make the default headline metric the one that survives matching on obvious nuisance variables
   such as length.
5. Publish the adversarial checks that were run and what they changed.
