# Helper context leak: pre-registration (A/B/A re-run)

Written 2026-11-20, before any new model call in this folder. Inventory and leak-sign counts over
the existing caches were computed before this file (they read cached replies, which is an outcome;
they are reported as L1 and do not change the design below).

## The question

Every model call in fourteen audits went through `audits/tools/claude_call.py`, which runs the
`claude` CLI from `<repo>/audits/<audit>/inference`. The CLI adds an environment block to every
request even with `--system-prompt`: working directory, git status of that directory, platform,
shell, a scratchpad path with file-handling advice, the model's name and id, its knowledge
cutoff, today's date, and the remaining USD budget (`--max-budget-usd 0.25`). Did that block change
any result an audit reported?

Only the directory-dependent part (working directory, git workspace, the audit name inside the
path) can be varied: `Caller(..., neutral_cwd=True)` runs from `/tmp/w`. Model name, cutoff, date
and budget are the same in both arms and are handled by reading prompts (step 5 of the brief), not
by this test.

## Step 0: what the block contains

Two calls in a separate folder (`arm_probe`): one from an audit's original `inference` folder, one
from `/tmp/w`, asking Haiku to reproduce verbatim everything in its context before the user
message. Used only to describe the block; the local path is redacted to `<repo>` before commit.

## Arms

For each sampled cached record (model, system, prompt, cached result):

- **L (leaky, test-retest):** the identical model, system and prompt, run now from the original
  audit's `inference` folder. `Caller("audits/helper-context-leak/arm_leaky", cap_usd=0.75)` with
  `run_cwd` set to that folder (one Caller instance per audit, same cache folder; a prompt shared by
  two audits is assigned to the first audit in the order below and run once).
- **N (neutral):** the same, `Caller("audits/helper-context-leak/arm_neutral", cap_usd=0.75,
  neutral_cwd=True)`.

The order of L and N is randomised per prompt (seed 0). At most 3 concurrent calls. L is not a
perfect replica of the original: the date (2026-11-17 for rounds one and two), the git status of
the repo and possibly the CLI version have changed since. So L-vs-cached agreement measures
run-to-run noise plus those drifts, and the clean contrast for the working directory is L vs N.

## Sample (seed 0, Haiku records only)

Excluded before sampling: Sonnet records (budget); prompts over 60,000 characters; free-text
generation with no parsed answer (lab-bench-deep-recall paraphrase and `qgen` prompts); the two
propensitybench scenarios that the API filter blocked; anything that reads as a harmful request on
inspection (counted).

Execution order (highest prior risk first, so a budget stop cuts the least important):

| Audit | n prompts | Strata / how arms are identified |
|---|---|---|
| propensitybench-deep-multiturn | one decision call per Haiku run (about 30) | per run (system prompt), the call with the longest prompt under 30,000 characters |
| propensitybench | 48 | mapped by reply text to `emulation_*.jsonl` / validation rows: probe 16, action late A 16, B1 late 8, P late 8 |
| sad | about 160 | rebuilt with the audit's own `pick_items` / `render` and `staleness` code: staleness all 16 non-invariant rows + 24 invariant; FHD a 30, b 30; INF a 20, b 20 (b duplicates collapse) |
| taste-bench | 150 | rebuilt with `b4_haiku.prompt`: H0 30; H1 and H2 on the same 60 (item, order) pairs, 30 detour and 30 parallel |
| control-monitors-bash | 20 | shortest R prompts that have an R2 (trailing newline) twin, 10 attack and 10 honest |
| control-monitors-shade | 16 | shortest 8 per system prompt |
| emergent-misalignment | 40 | 20 domain judge, 20 category |
| model-written-evals | 40 | random |
| cot-faithfulness | 40 | 20 yes/no, 20 forced choice |
| lab-bench | 40 | random, stratified by prompt type (with refusal option / without / options only) |
| lab-bench-deep-seqqa | 40 | random Haiku |
| lab-bench-deep-recall | 40 | random Haiku, excluding keys also in lab-bench |

## Parsing

Each audit's own parser, copied: SAD `\(?\b([AB])\b\)?` in the first 40 characters; taste-bench
`ANSWER: X`; lab-bench family `[ANSWER]X[/ANSWER]`, then `ANSWER: X` (then bare letter for
deep-seqqa); model-written-evals `l4_run.parse`; cot-faithfulness `parse_yn` / `parse_fc`;
emergent-misalignment leading YES/NO and first `\b[A-E]\b`; propensitybench `classify` /
`classify_probe`; multiturn: the tool name of a strict JSON tool call, else "text";
control-monitors-bash `"score": N`; shade the last numeric `<tag>n</tag>`. Unparsed is its own label.

## Outcomes per audit

1. Agreement with the cached parsed answer in L and in N (exact label; for monitor scores, within
   10 points on the 0-100 scale, and mean absolute difference).
2. Δ = agreement(L) − agreement(N), with a 95% interval from a paired bootstrap (2,000 resamples,
   seed 0) over the cluster: item for taste-bench and SAD (both conditions and orders of one item
   together), scenario for the two propensitybench folders, prompt elsewhere.
3. L–N agreement directly.
4. Share of replies in each arm that mention the environment (repo path, "benchmark", "audit",
   the scratchpad, the budget, the working directory or environment block), with the same regex as
   the inventory.
5. Reported arm differences recomputed on the sampled prompts with cached, L and N answers:
   taste-bench (H2 − H1) detour minus parallel; SAD choices-only (b) accuracy S vs R and the
   staleness agreement with the copied key; propensitybench misaligned count and probe YES count;
   control-monitors-bash attack − honest mean score; multiturn misaligned calls.

## Decision rule

A reported result needs a caveat if (a) for its audit, the interval for Δ lies wholly above 0 (N
agrees with the cached answers less than L does, beyond the interval), or (b) a recomputed reported
effect changes sign in N, or loses more than half its size in N relative to the cached answers on
the same prompts, while L does not. A Δ interval that includes 0 is reported as "no effect larger
than the upper bound of the interval", never as "no effect".

## Power

For paired binary agreement, Var(Δ) ≈ D/n, with D the discordant-pair share, about 2a(1−a) if L
and N each agree with the cache at rate a. The difference detectable with 80% power at two-sided
α = 0.05 is about 2.8·sqrt(D/n):

| n | a = 0.95 | a = 0.90 | a = 0.80 |
|---|---|---|---|
| 16 | 0.22 | 0.30 | 0.40 |
| 30 | 0.15 | 0.22 | 0.29 |
| 40 | 0.14 | 0.19 | 0.25 |
| 150 | 0.07 | 0.10 | 0.13 |

So per audit this test can only find large shifts (15 to 30 points of agreement) except in SAD and
taste-bench, where about 10 points is detectable. Recomputed arm effects on these samples are
small-sample estimates and are read only for sign and halving, not as replications.

## Budget

1.50 USD hard total for this task (0.75 per arm by the helper; step 0 under 0.02). Pilot the first
10 prompts of the order above, read cost per call, and cut the lowest-priority audits' n if the
projection exceeds 0.70 per arm. Any cut is reported.
