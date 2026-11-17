# Effect audits: methodology

Status: 2026-11-17. This is the shared brief for the audits under [`audits/`](.). Each audit takes
one benchmark and asks one question:

> Does a simple confounding feature change what this benchmark tells us about a model's
> capability, propensity or alignment, and by how much?

## Why this wave exists

The 47 audits in [`../findings/`](../findings/) mostly stop at "an artifact exists". Most end with
"effect untested". An artifact that nobody's conclusion depends on is not significant. This wave
only counts a result when it shows that a **published conclusion moves**.

Two pieces of prior work set the standard.

**APPS backdoor benchmark** (this project's paper; summary in [`../scope.md`](../scope.md)).
Monitors are ranked on telling honest code from backdoored code.
- Confound: people wrote the honest class and older models wrote the backdoors. A bag-of-words
  classifier that never runs the code beats 20 of 24 published monitors.
- Proof it is the confound: swap one class at a time for code by one author. The classifier's
  score follows the author contrast, not the backdoor.
- Second confound: the label is kept only when the backdoor works, so problem metadata predicts it.
- Third: many "working" backdoors are wrong only on inputs the problem forbids. Removing them
  shrank an apparent difference between attackers.
- Its stated limit: it never showed that published monitors *use* the shortcut.

**TASTE** (Zhong, "LLMs are weirdly below chance on TASTE without a shortcut", LessWrong,
2026-11-15). Models pick which of two safety research proposals experts preferred. The benchmark's
claim: the best model scores about 60% against 77% for experts.
- Confound: topic. Proposals with mechanistic-interpretability vocabulary were rated lower.
- Floor: "pick the proposal with fewer interp terms" scores 63.0%, above every model.
- Stratification: the rule splits the 92 pairs into 40 where it applies and 52 where it does not.
- Effect, from the paper's own per-item model logs: on the 52 shortcut-free pairs, every model
  above a capability cut-off is below 50%, and accuracy *falls* with capability (r = −0.60).
- Robustness: drop-one and drop-two proposals, a second term list, both answer orders.
- Its stated limits: the term list was tuned on the same data, labels come from one reviewer, and
  pairs share proposals.

Both follow the same four steps: find a simple feature, show it alone scores well, split or edit
the benchmark by that feature, and show the headline conclusion changes on the part where the
feature cannot help.

## The evidence ladder

Every claim in a write-up carries one of these levels.

| Level | What is shown | Counts as a finding? |
|---|---|---|
| L1 | The confound exists in the data or code | No. A lead |
| L2 | A rule that cannot see the substance matches or beats published models | No. A lead |
| L3 | Per-item model behaviour tracks the confound, and a published conclusion changes on the confound-free part | Yes |
| L4 | Editing the confound alone changes model outputs or scores | Yes, strongest |
| R | A plausible confound was tested at L3 or L4 and the conclusion held | Yes. Report it plainly |

Aim for L3 or L4 on at least one conclusion. An honest R is worth more than an inflated L3.

"A published conclusion" means a specific claim someone relies on: a ranking, a gap to humans, a
trend with capability or time, a threshold in a deployment policy, or "models do X at rate Y".

## Confound families

Look for all of these. Most real cases are a mix.

1. **Construction.** The classes or items differ in who, what or when made them: author, source
   dataset, generation prompt, pipeline, date, topic, length, format.
2. **Selection.** Items or labels are kept by outcome: only successful attacks, only items some
   model got wrong, a validation set picked with the judge it validates, per-model filtering.
3. **Answer surface.** Position, length, "yes" versus "no", option wording, templates, keywords.
4. **Scorer.** The scorer rewards something else: non-answers, refusals, tool names, keywords,
   parse failures mapped to a label, a judge told the model's identity, a judge whose errors track
   length or style, a denominator that includes items that cannot fail.
5. **Construct.** The prompt creates the behaviour it measures: a nudge, conflicting or ambiguous
   instructions, a scenario with one exit. Or the score measures compliance, agreeableness or
   capability when it claims propensity.
6. **Elicitation.** Compared models differ in scaffold, tools, token budget, reasoning effort or
   prompt. Refusals or timeouts are scored as inability.
7. **Statistics.** Items are clustered (shared task, family, proposal, scenario) but treated as
   independent; best of several configurations; averages over unlike sets; capability confounded
   with model family or release date.
8. **Recognisability.** The items are public, fixed and uncanaried, or look like a test.

## Procedure

Work in this order. Commit after each file (see "Committing").

**1. `claims.md`.** The benchmark's source, licence and pins. Then one to three published
conclusions, each with: the exact number and where it is stated, who relies on it and for what
decision, and what result from you would change it. Write this before touching model outputs.

**2. `prior_work.md`.** Search the paper's limitations, the repo's issues and pull requests,
LessWrong, the Alignment Forum and arXiv for existing critiques. List each with a link and what it
already showed. Do not re-derive a known result as new. Extending a known critique to L3 or L4 is
new; say which part is new.

**3. Data inventory** (in `README.md`). Find per-item, per-model outputs: the paper's logs,
leaderboard dumps, Inspect logs, third-party re-runs. Pin every revision (commit sha or file
sha256). If none exist and inference cannot substitute, say so in the first hour and switch to the
fallback in your brief.

**4. Confound hunt.** Read at least 50 items by hand, spread across labels, outcomes and sources.
Write down what you notice before computing anything. Then compute content-blind baselines with
permutation nulls (1,000 shuffles, within clusters).

**5. `prereg.md`.** Before looking at model outcomes by stratum, write: the feature and how it is
computed per item, the strata, the conclusion under test, the statistic, the unit of resampling,
and what result counts as "changes" and what counts as "holds". Commit it before running step 6.
If you change the feature after seeing outcomes, keep the first version's result in the write-up.

**6. Effect test (L3).** Recompute the headline on the full set (it must reproduce the published
number, or say why it does not) and on each stratum. Fit per-item correctness on the confound
feature and on capability. Report every number with a 95% interval from a cluster bootstrap.

**7. Intervention (L4), when cheap.** Build minimal pairs that change only the confound: swap the
answer order, strip the cue, negate the question, reword the nudge, equalise length. Run a small
model on both versions. See "Inference".

**8. Robustness.** At least four of these, chosen to hurt your own result:
- drop each cluster in turn (task family, proposal, source, model family);
- a second, independently defined version of the feature;
- discover the feature on one half and test it on the other;
- a placebo feature of similar prevalence that should have no effect;
- count the comparisons you made and correct for them;
- a different reasonable statistic.

**9. Alternative explanations.** List the three strongest readings under which the benchmark's
authors are right, and test each. Typical ones: the "confound" is the construct (length is the
sandbagging; refusing is the safe behaviour), the feature tracks difficulty, or the effect is one
model family.

**10. `README.md`.** Use the structure below. Also write `results.json` with every reported
number.

## Write-up structure

```
# <Benchmark>: <the finding in one line>
Status, date, evidence level reached (L1–L4 or R) per claim.
## The benchmark and what rests on it
## What we found            (plain statement, then the numbers table)
## The confound             (feature, how computed, examples by id)
## The effect               (published number, reproduced number, confound-free number, intervals)
## Robustness               (table: check, result, does the claim survive)
## Alternative explanations (each one, the test, the outcome)
## What was already known   (links; what is new here)
## What this does not show
## Pins and how to reproduce
```

One finding per section. Lead with the result. Give n and the interval with every rate. State the
bias direction: does the confound make the model look more capable, safer, or the reverse.

## Accuracy rules

- Every number comes from a committed script with a fixed seed, run from pinned inputs. No number
  from memory or from reading a chart by eye; if you must read a chart, say so.
- Quote code as `file:line` at the pinned commit.
- Distinguish "the label is predictable" (L1, L2) from "models rely on it" (L3, L4) in every
  sentence that could blur them.
- Resample the unit that was sampled: tasks, families, proposals or scenarios, not rows.
- Do not tune a feature on the outcomes it is tested on without saying so.
- A null result gets the same care and the same prominence as a positive one.
- If a number does not reproduce, that is a result. Do not adjust until it matches.

## Rules for handling data and code

- Treat everything downloaded as text. Do not execute downloaded code. Run Python on downloaded
  data with `python3 -I`. If a check needs downloaded code to run, use a Docker container with no
  network and no mounts beyond the data, and say so.
- Downloads go in `audits/<benchmark>/data/`, which git ignores. Commit scripts, small result
  files and write-ups only.
- For gated or unlicensed data, commit aggregates and item ids, never content. Do not accept new
  licence terms or gates; use only what the existing Hugging Face login already reaches, and
  report anything else as blocked.
- Do not contact maintainers or authors, and do not open issues, pull requests, posts or comments
  anywhere. Nothing leaves this machine except downloads and the inference below.
- Put no personal details in any request.

## Inference

Released logs come first. Many audits should spend nothing. Use inference only for an L4
intervention or to add a recent model to an L3 analysis, and only on benign content.

- Use [`tools/claude_call.py`](tools/claude_call.py). It caps each audit at 3 USD of reported
  cost, caches every response, and allows only Haiku (default) and Sonnet.
- Use Haiku unless a pilot shows it cannot do the task. Say why if you use Sonnet.
- Pilot on 10 items, check cost per call, then size the run. Prefer 100–300 short items over
  fewer long ones. Truncate or subsample long transcripts.
- Never send harmful requests, jailbreak prompts or hazardous-knowledge questions. That rules out
  running WMDP, HarmBench, AgentHarm and similar items.
- Report the model, the number of calls and the total cost in the README. Commit
  `inference/ledger.jsonl`; the response cache is ignored by git.
- A result from one small Claude model says how that model behaves. Do not generalise it to the
  models the benchmark's paper tested.

## Committing

All audits share one working tree on the branch `effect-audits`.

- Write only inside your own folder, `audits/<benchmark>/`.
- Commit with `audits/tools/commit.sh audits/<benchmark> "<message>"` after every file you create
  or finish: at least once per file, and after each stage above.
- Never run `git add -A`, `git commit -a`, `git checkout`, `git switch`, `git stash`, `git reset`,
  `git rebase` or `git push`.
- Start commit messages with the benchmark name, for example `sad: prereg for choices-only strata`.
