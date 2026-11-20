# Effect audits: methodology

Status: 2026-11-20, with sections added after rounds one and two. This is the shared brief for the audits under [`audits/`](.). Each audit takes
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

## Where to attack (added after round one)

Round one audited eight benchmarks ([`README.md`](README.md)). Read this section before choosing
what to test. It says where findings came from, where they did not, and which mistakes the
auditors made.

### Conclusions come in three layers, and they fail differently

| Layer | Example | Round-one outcome |
|---|---|---|
| The numbers | "o3 sabotaged 79 of 100 runs" | Reproduced in 8 of 8. Do not spend long here |
| Aggregate rankings and trends over many models | METR doubling time, AgentDojo ranking, SAD ranking | Held in every case (rank correlations 0.94–0.99). A confound that shifts all models alike cannot move a ranking |
| Single cells, differences between conditions, and what the number is said to mean | "low attack rate = robust", "resists shutdown = self-preservation", "AUROC 0.99 = monitors work" | **All four real findings were here** |

So aim at the third layer first: one model's score, a gap between two conditions, a comparison to
humans or to chance, a threshold, and the sentence that says what the score means.

### Traits that predict a broken headline

APPS and TASTE broke outright. The eight round-one benchmarks did not. The difference was these
traits. Score your benchmark on each in `claims.md` and attack the ones it has.

1. **The label comes from a process, not from a judgment of the substance.** Classes written by
   different sources (APPS), labels read off later outcomes, labels from one reviewer (TASTE),
   distractors written by a model. First test: can you predict the label from who or what made the
   item, without reading for meaning?
2. **Items were kept or dropped by model behaviour.** "Every item was missed by at least one judge
   model", adversarial filtering, pairs kept only where a model showed the effect. This produces
   below-chance scores and "stronger models do worse" by itself, through regression to the mean,
   for models related to the filter. First test: redo the selection on one half of the samples and
   measure the effect on the other half; compare models by their relation to the filter models.
3. **The headline is a gap near chance or a difference of two rates.** 60% against 50%, a
   compliance gap, an "unfaithfulness rate" of 5–15%. A small bias is enough. Differences of rates
   are also bounded by the base rate: a model that almost never complies cannot show a gap.
   First test: the same contrast on the odds scale, and with base rates matched.
4. **Few independent units.** 92 pairs that share proposals, 500 questions from 60 tasks, many
   prompt variants of 20 scenarios. First test: count the clusters, resample them, and find how
   many clusters carry the headline.
5. **Two free-text options.** The options themselves carry length, specificity, hedging, tone and
   vocabulary. First test: an options-only baseline, by rule and by a small model, on held-out
   items.
6. **An LLM judge decides a subjective criterion.** "Mentions the hint", "alignment-faking
   reasoning", "better decision". First test: blind hand labels on 50–100 items spread across the
   judge's verdicts, then check whether judge errors track length, model or condition.
7. **The scorer assumes the model was told something.** A prohibition, a rule, a role, a tool's
   limits. First test: read the rendered prompt, not the template or the paper.
8. **The best number belongs to the easiest condition.** The monitored agent narrates, the hint is
   blatant, the tool is named for what it does. First test: find the condition labels, and report
   the headline for the hardest disclosed condition.
9. **One outcome bucket holds unlike cases.** "Secure" held never-exposed runs; "attack success"
   held errors; "correct" can hold lucky letters. This was the single most productive attack in
   round one. First test: for each scored outcome, list every route into it and count each route.
10. **Scores aggregate over units of varying size.** A maximum, an "any" or a sum over steps,
    turns or tokens tracks length. First test: match on length and recompute.
11. **The answer key is unbalanced in polarity or letter.** Yes/no, A/B, agree/deny, "insufficient
    information". Scores then reward a lean. First test: the score by key polarity, and a
    balanced score.
12. **Little outside scrutiny.** Under a year old, one lab, no independent re-run, no issues
    filed. Heavily used leaderboards have had their cheap flaws found already.

### Order of attack

1. Render what the model actually saw for 20 items, and what the scorer actually did with 20
   outputs. Compare both with the paper's description. (Traits 7, 8, 9.)
2. Split every outcome bucket by route. (Trait 9.)
3. Tabulate the key by polarity, letter, position, length rank and source. (Traits 1, 11.)
4. Content-blind baselines with a held-out half: rules first, then a small model that sees only
   the options. (Traits 1, 5.)
5. Find the selection step in the construction code or paper, and test for regression to the
   mean. (Trait 2.)
6. Count clusters and redo the headline's interval. (Traits 3, 4.)
7. Only then stratify model results by the feature, with the checks below.

### Mistakes auditors made in round one

A refuter cut back six of eight headlines. Each of these happened. Run the check before you claim.

- **A split that manufactures the effect.** A stratum that differs in answer type or base rate
  will show a "collapse" with no confound present. For every stratified result, run a placebo
  split of the same sizes and the same answer-type mix, 1,000 times, and report where your result
  falls in that distribution.
- **Removal without a random control.** "Removing these items halves the score" means nothing
  until removing the same number of comparable items at random does not.
- **A rank correlation that hides single-model moves.** Report the largest rank change and the
  cells that move, not only the correlation.
- **Calling a disclosed design choice a mismatch.** Re-read the paper's method and limitations
  sections before claiming the release differs from the paper.
- **Counts rounded up.** "All monitors" was 9 of 11. Write the count.
- **Wording beyond the evidence.** "Mostly X" needs a blind-labelled sample that says so. A result
  on six items is a lead, whatever its size.
- **Causal words for correlational results.** "Explains", "drives" and "because" need an
  intervention.

### Mistakes auditors made in round two

A refuter cut back all six round-two headlines. Each of these happened.

- **Resampling items when items share a template.** Resample the template, subtask or task. With
  15 templates an item-level interval of ±0.03 became ±0.18.
- **Comparing a rule and a model on different scales.** Score the rule exactly as the models were
  scored (same penalty, same inputs). A rule that needs a field models never see is not a baseline.
- **A placebo that sees the label.** A placebo subset must be built without the answer key.
- **Sizing a run before checking the floor.** An intervention where every arm scores 0, or every
  arm scores 1, says nothing. Pilot the base rate in the exact format first, and stop if it is at
  the floor or ceiling.
- **Counting a category by its name.** Read 20 raw cases of every category before using it as
  compliance, refusal, error or success.
- **"New" findings that are in the paper's appendix.** Search the appendix and the released
  analysis notebooks, not only the main text.

## Deep dives (round three)

Round three opens no new benchmark. Each deep dive takes one question that an earlier audit left
open and tries to settle it. Two rounds showed that breadth finds little; the open questions are
where a result could still change a conclusion.

- **Folder.** `audits/<benchmark>-deep-<topic>/`. Write only there. Read the parent audit's
  `README.md`, `validation/VALIDATION.md`, `prereg.md` and scripts first, and reuse its downloads
  by path (`audits/<benchmark>/data/`). Do not edit the parent folder.
- **State the inherited question** at the top of `prereg.md`: what the parent audit established,
  what it left open, and which outcomes would count as "yes", "no" and "still cannot tell". Commit
  that before any outcome.
- **A null must be informative.** State the power of the design against the effect size the parent
  audit saw, at the right resampling unit. If the design cannot reach 80% power within budget, say
  so before running and either change the design or report the result as a lead.
- **Stronger model allowed.** Where the question is how a strong model behaves, Sonnet may be the
  primary model, with Haiku as a second model. The cap is still 3 USD per folder by the helper.
  Pilot 10 calls, read the cost, then size the run. A Sonnet result is about Sonnet: do not extend
  it to the models in a paper or a system card.
- **Controls for every intervention.** Each edited arm needs an arm that applies the same kind of
  edit without changing the feature under test, and the key must be verified as still correct
  after the edit (by computation where the task allows it).
- **No new outside access.** Do not download model weights, install system software, accept terms
  or contact anyone. If a question can only be settled that way, write exactly what is needed and
  stop.
- The write-up structure, accuracy rules, data rules and the evidence ladder above all apply.
  `claims.md` and `prior_work.md` may be short and point to the parent's.

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
  report anything else as blocked. Where a benchmark asks that items not be reposted in plain
  text, commit ids, hashes and aggregates only, even when the licence would allow more.
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

All audits share one working tree. Round one ran on the branch `effect-audits`, since merged to
`main`; round two ran on `audits-round2`, also merged. Round three runs on `audits-round3`. Do not
create or change branches.

- Write only inside your own folder, `audits/<benchmark>/`.
- Commit with `audits/tools/commit.sh audits/<benchmark> "<message>"` after every file you create
  or finish: at least once per file, and after each stage above.
- Never run `git add -A`, `git commit -a`, `git checkout`, `git switch`, `git stash`, `git reset`,
  `git rebase` or `git push`.
- Start commit messages with the benchmark name, for example `sad: prereg for choices-only strata`.
