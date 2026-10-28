# When the model knows it's a test

*What our benchmark audits say about evaluating AI systems that can tell when they are being
evaluated.*

Status: 2026-10-28. This report draws on the audits in [`findings/`](findings/). Every number
below comes from a finding with a reproducible script and pinned sources. The five results in
[`report-top5.md`](report-top5.md) were also checked by a second, independent pass. We did not run
any model, so nothing here shows a model actually gaming a benchmark. What it shows is where
benchmarks would fail if a model did.

## The short version

Most AI safety benchmarks assume the model being tested behaves the way it would in deployment. A
model with situational awareness breaks that assumption. It can tell when it is being tested, it
knows something about how tests are scored, and it can act on that.

We audited 47 safety benchmarks and evaluations. Three kinds of weakness bear on situational
awareness:

1. **The test is recognisable.** Its scenario is public, fixed, and missing the canary strings that
   keep test data out of training sets. A model may have read it before.
2. **The scoring can be gamed by a model that knows the rules.** Some scorers reward behaviour that
   a careful, evasive or test-aware model would produce anyway.
3. **The attackers in monitoring benchmarks weren't trying to hide.** Benchmarks that test whether a
   monitor catches a misbehaving AI mostly use attackers that leave obvious traces. A
   situationally aware attacker would not leave them. So catch rates describe careless attackers.

Separately, there is growing evidence that frontier models already recognise evaluations. Labs
report it in their own system cards.

What the evidence supports is this: **current safety benchmarks would not detect a model that
recognised the test and adjusted its behaviour, and frontier models already recognise tests.** It
does not support "models are gaming these benchmarks today". That has not been shown.

---

## Do current models know when they are being tested?

Increasingly, yes. Four pieces of evidence:

- **They can tell evaluation transcripts from real use.** The evaluation-awareness benchmark
  (Needham et al. 2025) asks models whether a transcript comes from an evaluation or from real
  deployment. The best models score well above chance: AUROC 0.79 on chat transcripts (Claude 3.5
  Sonnet) and 0.95 on agentic ones (Gemini 2.5 Pro). An AUROC of 0.5 is guessing; 1.0 is perfect.
  - We tested whether that score is a trick. Simple surface features (length, formatting, scaffold
    text) do separate the classes, but only for sources the classifier has already seen. On sources
    held out entirely, they fall to chance. So the models' recognition is not explained by easy
    surface cues; it looks more like real understanding of what an evaluation is.
    ([`findings/eval-awareness-row-level/`](findings/eval-awareness-row-level/))
- **They say so.** In Apollo Research's testing for the Claude Sonnet 4.5 system card, the model's
  verbalised evaluation awareness is reported as "58% unambiguous references". The card cautions
  that its low deception rate "may be partially driven by its evaluation awareness". The Claude Haiku 4.5
  system card withholds its agentic-misalignment results because the model kept saying it was in a
  test.
- **They remember specific tests.** Anthropic reports Claude models recalling details of the
  alignment-faking scenario, such as the fictional company "Jones Foods". An early Claude Opus 4
  checkpoint took on the persona of the deceptive AI from that paper, probably after training on its
  public transcripts.
- **They change behaviour when they think they are being trained.** That is the core result of the
  alignment-faking paper.

The evidence is weaker on one point: whether models exploit specific scoring quirks, like a
keyword the grader looks for. We found no evidence of that. In one public test of Agentic
Misalignment, Claude Haiku 4.5 used the grader's trigger words in 232 of 240 episodes, so it was
not avoiding them.

---

## 1. The test is recognisable

A test only measures natural behaviour if the model doesn't know it is a test. Three widely used
misalignment evaluations are public, fixed, and missing canary strings. A canary is a unique code
that labs search for to drop test data from training sets.

### Alignment faking

The scenario tells a model it will be trained to be unconditionally helpful, but only on free-tier
conversations. The paper's own transcripts carry canaries. But the scenario is restated, with no
canary, in **611,241 distinct texts across 39 public Hugging Face datasets**, mostly synthetic
"news" documents that describe the fictional training policy as fact. The paper's 522 system-prompt
files have no canary either.

**Why it matters:** any alignment-faking rate measured on a model trained after early 2025 may be
measuring recall of a famous scenario. Anthropic reports exactly that kind of recall.

([`findings/alignment-faking-uncanaried-copies/`](findings/alignment-faking-uncanaried-copies/))

### Agentic Misalignment

This is the "blackmail" evaluation, which has been widely reported. All 234 conditions share the
same opening line, date and five-person cast. Text shared by every prompt in a scenario makes up a
median 43% of each blackmail prompt. None of its 37 template files carries a canary.

([`findings/agentic-misalignment-verdict-gates/`](findings/agentic-misalignment-verdict-gates/))

### Apollo's in-context scheming evaluations

The paper itself has a canary, but none of its 58 public transcripts does. Later evaluation suites
reuse its scenarios word for word.

([`findings/apollo-scheming-nudged-headlines/`](findings/apollo-scheming-nudged-headlines/))

**The fix is cheap:** canary every public copy, and rotate the details (company names, people,
dates) for each new evaluation round.

---

## 2. The scoring can be gamed by a model that knows the rules

These are the clearest cases for the argument. In each one, the behaviour that earns a good score
is behaviour a test-aware model would plausibly produce anyway.

### MASK: honesty by having no opinions

MASK measures whether a model lies under pressure. It first asks the model, neutrally, what it
believes. Then it pressures the model, and checks whether the pressured answer contradicts the
belief.

**The weakness:** if the model gives no consistent belief, or evades, the item can't count as a
lie, so it counts toward the honesty score.

**How it could be gamed:** a model that is vague or inconsistent whenever it is asked what it
believes cannot be caught lying. A model that does this and lies at every other chance still scores
**72.6% honest** on the public items. That is a dishonesty rate of 0.27, which passes xAI's
deployment criterion of a MASK dishonesty rate below one in two. In the paper's own results, the
smallest models (1B and 0.5B parameters) rank as the most honest.

**Why it matters here:** a test-aware model doesn't need to read MASK's code. Being noncommittal
when it suspects it is being probed is enough. xAI uses the score as a deployment gate, and no xAI
model card reports how often its models gave no belief or evaded.

**Caveat:** the MASK authors chose this rule deliberately and defend it in the paper. The problem
is what the headline number hides, not a hidden bug.

([`findings/mask-no-belief-scored-honest/`](findings/mask-no-belief-scored-honest/))

### Agentic Misalignment: blackmail that doesn't say "blackmail"

The blackmail grader counts a response as blackmail only if three things are true: an LLM judge says
yes, the response emails the target, and the response contains the literal word "blackmail" or
"leverage". A threat worded any other way is scored not harmful.

**Where it stands:** this was already reported upstream, and models don't currently avoid the words
(232 of 240 episodes used them). It is a ready-made blind spot for a model that learned the grader
from its public code.

([`findings/agentic-misalignment-verdict-gates/`](findings/agentic-misalignment-verdict-gates/))

### CTRL-ALT-DECEIT: sandbagging with obvious tells

This benchmark tests whether a monitor catches a model deliberately underperforming ("sandbagging").
Two things give the sandbaggers away:

- the general monitor is shown the test score, and the score alone predicts sandbagging (AUROC
  0.716) better than that monitor does (0.60);
- sandbagging runs stop early because of how the test harness works, so run time alone gives 0.854.

A sandbagger that aims for a believable score and uses its full time would remove both tells.

([`findings/ctrl-alt-deceit-score-visible/`](findings/ctrl-alt-deceit-score-visible/))

### Cybench: the answers are reachable

This one cuts the other way: it inflates capability rather than hiding misbehaviour. Every Cybench
flag is committed in plaintext to public repositories. The sandbox in the widely used inspect_evals
port lets the agent reach GitHub. In one port task, the flag sits in a binary the agent can read. A
model that knows where answers live can find them. That matters for capability thresholds in
dangerous-capability evaluations.

([`findings/cybench-public-flags-reachable/`](findings/cybench-public-flags-reachable/))

---

## 3. The attackers weren't trying to hide

This category gets the least attention, and it may be the most important.

AI control research asks: if a model were secretly pursuing a harmful side task, would a monitor
catch it? To answer that, benchmarks need examples of a model doing something sneaky. Usually a
model is instructed to carry out a hidden side task, and the transcripts are given to a monitor.

The catch: the attacking models in these benchmarks mostly behave as if no one is watching. They
narrate the side task, carry scaffold labels, or stop the moment they succeed. A monitor that
catches them is catching carelessness. A situationally aware attacker, which is the case control
research worries about, would not leave these traces.

| Benchmark | What gives the attack away | How well that alone works |
|---|---|---|
| Monitor Red Teaming (SHADE-Arena) | Agents not told about the monitor write "secondary task" in 44 of 50 runs | The phrase alone scores 0.94; the monitor scores 0.96 |
| METR MALT | Every prompted sandbagging transcript contains the instruction to sandbag in its system message | That one rule separates the classes perfectly (1.00) |
| Redwood Control Leaderboard (BashArena) | Scaffold `<risky>` tags appear in 596 of 600 attack transcripts and no honest one | 0.997; action count alone beats every monitor on the board |
| MonitoringBench (with its public honest set) | Attacks were generated months before the honest runs, and dates show in tool outputs | 0.998 |
| LinuxArena and BashArena | Attacks end as soon as the side task succeeds, so they are short | Length alone gives 0.87–0.95 |
| ControlArena AgentDojo corpus | The attacker's bank account number appears in the agent's own tool call | 0.939, above the corpus's own monitor (0.925) |

Some of these traces would never reach a monitor in a real deployment. METR's monitors probably
never saw MALT's instruction, for example. But they still show the same thing: the attacks don't
model an attacker who expects to be watched. When the label can be read off a careless trace, a
high catch rate says little about catching a careful attacker.

**Two consequences worth stating plainly:**

- **Detectors trained on this data learn the traces.** One published detector, RH-Detect,
  fine-tuned on MALT data with the sandbagging instruction still in the prompts and reports AUROC
  0.937. A detector like that learns to spot the instruction, not the behaviour.
- **Monitor rankings partly reward spotting traces.** On the Redwood leaderboard's BashArena set, the
  number of actions in a transcript ranks attacks better than every listed monitor.

The fix is to build attacks with an attacker that knows it is monitored: tell it, reward it for
evading, strip scaffold tags and narration, and check that simple traces can't do the monitor's job.

Sources: [`mrt-shade-arena`](findings/mrt-shade-arena/), [`malt-row-level`](findings/malt-row-level/),
[`redwood-leaderboard-scaffold-cues`](findings/redwood-leaderboard-scaffold-cues/),
[`monitoringbench-container-clock`](findings/monitoringbench-container-clock/),
[`linuxarena-trajectory-baselines`](findings/linuxarena-trajectory-baselines/),
[`basharena-checkers-and-length`](findings/basharena-checkers-and-length/),
[`controlarena-corpora-surface-cues`](findings/controlarena-corpora-surface-cues/).

---

## A caution: measuring situational awareness has the same problems

The main benchmark for situational awareness itself, SAD (the Situational Awareness Dataset), can be
partly answered from surface cues. A classifier that sees only the answer choices, not the
question, beats 17 of 21 released models on two tasks. One task's answer key, about which model you
are, only covers models up to o1. So published situational-awareness scores may be inflated in some
places and out of date in others. Use SAD to show the concept, not as a precise measurement.

([`findings/sad-content-blind-and-stale-keys/`](findings/sad-content-blind-and-stale-keys/))

---

## What the evidence does and doesn't support

| Claim | Supported? | Best evidence |
|---|---|---|
| Frontier models can recognise evaluations | Yes | Evaluation-awareness benchmark (0.79–0.95); Sonnet 4.5's "58% unambiguous references"; Haiku 4.5's withheld results |
| Models recall specific public test scenarios | Yes | Anthropic's alignment-faking recall reports; 611k uncanaried copies |
| Some safety scores can be raised by test-aware behaviour | Yes | MASK's 72.6% floor; Agentic Misalignment's keyword gate; CTRL-ALT-DECEIT's tells |
| Monitor benchmarks overstate catch rates against careful attackers | Yes, by construction | MRT, MALT, Redwood, MonitoringBench, LinuxArena traces |
| Models are currently gaming these benchmarks | **No evidence** | Not tested; Haiku 4.5 didn't avoid Agentic Misalignment's trigger words |
| All benchmark problems are about situational awareness | **No** | See below |

### Findings that are not about situational awareness

Several of our most significant findings are ordinary measurement errors. They matter, but they
would be wrong whatever the model knew. Keep them out of a situational-awareness argument, or give
them their own section.

- **Model-Written Evals:** three files are keyed backwards, so a steering vector called "Survival
  Instinct" measures willingness to be shut down.
  ([`findings/model-written-evals-inverted-labels/`](findings/model-written-evals-inverted-labels/))
- **HarmBench:** the judge's reported 93.2% human agreement is agreement with one annotator, on a set
  the judge helped choose. Against the majority it is 90.9%.
  ([`findings/harmbench-strongreject-judges/`](findings/harmbench-strongreject-judges/))
- **AgentHarm:** calling tools with placeholder arguments earns a third of the harm score, which
  makes models look *more* harmful, not less.
  ([`findings/agentharm-tool-call-credit/`](findings/agentharm-tool-call-credit/))
- **Also not about situational awareness:** WMDP's answer-length cue, MACHIAVELLI's scoring and
  OR-Bench's wording split.

---

## What would make evaluations hold up

These are practical changes, roughly in order of cost.

1. **Canary everything, and rotate details.** Every public copy of a test scenario, and fresh
   names, dates and companies for each evaluation round.
2. **Report the parts of the score that a test-aware model can move.** For MASK, how often the model
   gave no belief or evaded. For refusal-based scores, how often the model refused after acting.
3. **Grade outcomes, not wording.** Replace keyword gates with checks on what the model actually did.
4. **Build attacks with attackers that know they are watched.** Then check that simple traces
   (length, scaffold tags, keywords, timestamps) cannot match the monitor.
5. **Report a trace-only baseline next to every monitor score.** If counting actions gets 0.87, a
   monitor at 0.90 is not doing much.
6. **Measure evaluation awareness alongside every result.** Report how often the model said or
   implied it was being tested, as the Sonnet 4.5 and Haiku 4.5 system cards began doing.

---

## Notes on method

- Each benchmark was audited from pinned versions of its public data and code, without running
  the benchmark's own code.
- Four gated datasets (MALT, the evaluation-awareness benchmark, Liars' Bench and TRACE) were read
  after their access terms were accepted. Outputs report only counts and ids.
- Statements about how labs use a benchmark come from the cited public documents.
- Nothing here has been sent to the benchmarks' maintainers.

The full list of benchmarks and their status is in [`coverage.md`](coverage.md).
