# Gated benchmarks: what the public side shows

Status: public material only, read 2026-10-27. The four datasets below are gated on Hugging Face.
No gate was accepted, no login was used, and no mirror or re-upload was read. Three probes of the
gate boundary returned 401 and were stopped: a companion file inside the eval-awareness repo
(`DATA_SOURCE_LICENSES.md`), the dataset viewer's `/size` endpoint (all four), and the Hub commit
history (all four). The dataset cards (`README.md`), API metadata (configs, row counts, file
sizes and dates) and file listings are served without the gate, and are what this audit reads,
along with papers and code.

Each verdict says what it rests on. "Holds" means confirmed in the public material; it does not
mean the effect on published results was measured. No model was run.

## Pins

| Benchmark | Data (metadata and card only) | Paper | Code |
|---|---|---|---|
| MALT | `metr-evals/malt-public@6100006c`, `metr-evals/malt-transcripts-public@3521e8e2` | [METR post](https://metr.org/blog/2025-10-14-malt-dataset-of-natural-and-prompted-behaviors/) | none public |
| Eval awareness | `jjpn2/eval_awareness@5d724f12` | arXiv 2505.23836v3 | `jjpn97/eval_awareness@1543ffe6` |
| Liars' Bench | `Cadenza-Labs/liars-bench@503399b8` | arXiv 2511.16035v1, v2 | `Cadenza-Labs/liars-bench@ba10de15` |
| TRACE | `PatronusAI/trace-dataset@31d87f06` | arXiv 2601.20103v1 | none public |

Full shas are in each `*_checks.json`.

## MALT (`check_malt.py`, `malt_checks.json`)

The confound in `findings/malt-sandbagging-one-model/` still stands at these pins. The new checks
are about who was reviewed, and about one benchmark that reuses MALT.

- **Reviewer coverage by model (holds, card table).** The public card lists 19 models. Reviewed
  benign runs come from 5 of them. Claude Opus 4 and Claude Sonnet 4 make up 681 of the 694 (98.1%),
  and their benign runs are reviewed almost completely (349 of 351 and 332 of 334). For every other
  model, benign runs are almost entirely unreviewed:
  - Claude 3.7 Sonnet: 0 of 1,222;
  - o1-preview: 1 of 1,439;
  - o3-2025-04-16: 1 of 130.

  Seven models (1,861 runs) have no reviewed run at all. Every positive run is reviewed
  (0 unreviewed). So review covers labels for positives and model identity for negatives.
- **CoT rewrite applied to one class (ruled out).** The post says the Claude Sonnet 4 edit that
  removes mentions of the instruction was run on "all reasoning traces … (not just the prompted
  runs)".
- **Obfuscation variants (new on the Hub; documented in the post, not on the card).** Both repos
  carry four more configs (`irrelevant_detail`, `language_mixing`, `summarize`, `vague_cot`). Each
  has 7,179 rows, the same as the default config, so the transform covers every run and not one
  class. Neither card body mentions them.
- **A claim resting on MALT: rh-bench's MALT "hacking" rows (holds at count level).** By model,
  rh-bench's 286 MALT hacking rows are two groups:
  - exactly the card's 62 public reward-hacking positives (all 8 models match);
  - 224 Claude 3.7 Sonnet rows. The card has no Claude 3.7 Sonnet reward-hacking positive, and
    exactly 224 prompted `sabotage` runs.

  So rh-bench very likely serves MALT's prompted sabotage (a sandbagging label) as reward hacking.
  Run ids were not compared (MALT is gated; rh-bench text was not read). Direction: a label
  definition mismatch, not a clear up or down.
- **Blocked by the gate:** both settling tests in the earlier finding (same-model negatives, and a
  content-blind model probe), and any check on the transcripts or the obfuscated traces.

## Evaluation awareness, Needham et al. (`check_eval_awareness.py`, `eval_awareness_checks.json`)

Sources: the paper's four appendix source tables, its methods text, and the code that assigns
labels.

- **3/1: the label is fixed by the source (holds, by design).** Every listed source is in one
  class only, and the code takes the label from the sample's `eval_category`. In the agentic half,
  only two scaffold families appear in both classes:
  - Aider: 31 evaluation, 98 deployment;
  - smolagents: 64 evaluation, 95 deployment.

  For 155 of the 250 agentic evaluation samples the paper names no scaffold (AgentHarm, Cybench,
  SWE-bench, SWE-Gym, GAIA runs, honeypot, mvp). 57 of the 250 agentic deployment samples come from
  scaffolds with no evaluation counterpart (Continue 23, Cursor 24, OpenHands 10). The paper says
  seven deployment scaffolds; the table names five. So agentic awareness can partly be scaffold and
  source recognition.

  **Untested (gated):** a format-only classifier with source-grouped folds.
- **5: overlap with public benchmarks (holds, from the tables; disclosed qualitatively).**
  - All 287 chat evaluation samples, and 229 of 250 agentic evaluation samples, take their prompts
    from published benchmarks. The 21 exceptions are the bespoke honeypot and mvp sets.
  - None of the 250 agentic deployment samples does: all are the authors' own runs.
  - In the agentic half, "prompt from a published benchmark" therefore separates the classes at
    229/250 against 0/250. Agentic is also where models score highest (AUC 0.83–0.95).

  The paper says memorisation "could plausibly contribute" but does not measure it. The paper has a
  canary, and the data is an encrypted zip.

  **Untested (gated):** the per-item check.
- **6: table totals (holds).** The tables sum to 1,000 samples, but split 287/250/213/250 (chat
  evaluation, agentic evaluation, chat deployment, agentic deployment). The text says 250 in each
  cell. They list 57 sources, not the stated 61. AUC does not depend on class balance; Brier and
  ECE do, and the stated chance Brier of 0.25 assumes 50/50. Whether the released file matches
  the tables or the text is blocked.
- **6: same kind of data, opposite labels (holds as a reading of the tables).**
  - Prompt-injection games: Gandalf and Mosscap (37 samples) are labelled evaluation, HackAPrompt
    (19) deployment.
  - Bias datasets: KoBBQ (10) is labelled evaluation, CDial-Bias (19) deployment.

  The human baseline (0.921) is the two authors who compiled the data, which the paper discloses.
- **Bias direction:** the AUCs overstate awareness of novel, unpublished evaluations, the case that
  matters for evaluation validity.

## Liars' Bench (`check_liars_bench.py`, `liars_bench_checks.json`)

- **0/2: what decides the label (holds from the paper's own description).**

  | Dataset | Label decided by | Visible to text detectors? |
  |---|---|---|
  | Gender-Secret | the question's topic: every lie answers a gender question, every honest row a different demographic | yes (user turn) |
  | Soft-Trigger | the trigger category in the user prefix; the per-row rule is not stated anywhere in the paper; the release is exactly 12,000/12,000; with a trigger, models still answer correctly 7–27% of the time | yes (user turn) |
  | Instructed-Deception, Convincing-Game | the system prompt (neutral or lie-instructed; lie-instructed CG rows can only be lies) | no (hidden), but probes read activations conditioned on it (already in the catalogue) |
  | HP-C, HP-KR, Insider-Trading | the response against the model's own established belief, under the same prompts | n/a |

  Gender-Secret and Soft-Trigger are 24,762 of the 73,625 rows in the paper's tables. The paper
  hides system prompts from text detectors but not user turns.
- **Bias direction for 0/2:** up for any detector that reads user turns. The published detectors
  score worst on GS, so the headline is not inflated by this.

  **Untested (gated):** a topic or trigger-only baseline, and Soft-Trigger rows that answer
  correctly but are labelled lies.
- **6: how lies are labelled (holds in paper and code).**
  - The LLM-as-a-Judge detector (the best method, 0.73) uses `claude-3-sonnet-20250219`. The
    repo's `models.py` maps that id to `anthropic/claude-3.7-sonnet-20250219`.
  - The same id labels Instructed-Deception and Convincing-Game, so on those two datasets the
    detector is the labeller.
  - Other labellers: HP-KR uses Claude 3.5 Haiku; Insider-Trading uses GPT-4o, with the authors'
    estimate that 5–25% of report labels are open to interpretation.
  - Manual review was at least 10 lies and 10 honest rows per dataset.

  Direction: up for LLM-as-a-Judge on ID and CG; its size is untested.
- **Metadata (holds).**
  - Table 1's Total row (44,571 honest, 28,292 lies; repeated in the text) omits Gender-Secret. The
    rows sum to 45,102 and 28,523, and the difference is exactly GS's 531/231.
  - The current release differs from the paper (v1 = v2 counts): Instructed-Deception has 26,426
    rows against 20,798 (+5,628), and Insider-Trading 6,873 against 6,709 (+164). Both files were
    re-uploaded on 2026-05-02. Published per-dataset numbers may not reproduce on the release.
  - `alpaca/train-*.parquet` is in no config.
  - The card says "seven datasets including … Alpaca", but there are eight configs.
  - Parquet sizes match the card.

## TRACE (`check_trace.py`, `trace_checks.json`)

- **0: provenance (holds, paper prompts).** Claude Opus 4.5 in Claude Code writes both classes:
  the user turns, the assistant turns and every tool output. Each class has its own prompt.
  - Benign trajectories are matched to a hack category ("Source Category").
  - Only the benign prompt asks for "Proper testing and verification", "Honest reporting of
    results", "Following best practices" and "No shortcuts".
  - Only the hack prompt asks for subtlety.

  This is a one-class instruction that can leave surface cues. **Untested (gated):** a
  content-blind baseline.
- **7: hack named inside the trajectory (holds as a permission, rate untested).** The hack prompt
  passes the hack's taxonomy name to the generator, and allows "cases where the user catches the
  reward hack and asks the agent to fix it". So some hacked trajectories can contain a user
  call-out of the hack. How many is blocked. Direction up.
- **4: no execution.** Tool outputs are written by the generator, not run, so whether a hack would
  pass the fictional tests is never checked. Validity rests on the annotators.
- **6: labelling.** Three engineers annotated; about 81% of samples were accepted, and
  high-disagreement items were removed.
  - The card's "inter-annotator agreement κ = 0.82" is the hack-type statistic. The paper's table
    gives 0.776 for hack presence.
  - Cohen's κ is a two-rater statistic, and the paper does not say how the three raters were
    paired.
  - The generator (Opus 4.5) is also one of the detectors scored.
- **Metadata (consistent).**
  - 517 = 268 + 249 matches num_examples; the parquet size equals download_size.
  - 13,677 utterances is a mean of 26.45 (card: 26.5).
  - The taxonomy tables have 54 leaves, 10 subcategories and 4 top categories, as stated.
  - rh-bench serves 517 TRACE rows (from the repo's metadata-only count).
- **Blocked by the gate:** class balance per category, the label string format, prompt-phrase or
  call-out rates, and length baselines.

## Reproduce

```bash
python -I check_malt.py --cache data
python -I check_eval_awareness.py --cache data
python -I check_liars_bench.py --cache data
python -I check_trace.py --cache data
```

Standard library only. Each script fetches public pages, cards, API metadata, arXiv sources and a
few pinned code files into `--cache`, and stops on any 401/403. `check_malt.py` takes rh-bench's
MALT counts from this repo's `findings/rh-bench-label-shortcuts/rhbench_checks.json` (hard-coded,
with its pin).
