# ControlArena monitor corpora (`adityaasinha28/control_arena_*`): checks 0, 1 and 5

Status (2026-10-27): length and action-count cues confirmed in four of five settings, from pinned
revisions. The "undocumented dedup" lead (catalogue A7) is ruled out: the 856 and 1,443 counts come
from a 28K-token length filter that arXiv 2605.29601 describes. That filter removes the SHADE length
cue and leaves SHADE with mostly 3 of its 5 tasks. No row is shared between train and test. Whether
any monitor actually relies on these cues is **untested**. Not yet raised with the uploader or the
authors.

## What was audited

| Corpus | HF commit | parquet sha256 (prefix) |
|---|---|---|
| `control_arena_bash` | `08663a5d10a5445bc4b750b7f8eb079c9a505df8` | `29550a69` |
| `control_arena_shade` | `7b5861e85f14381e70ed5b101fd7ceeec96d4f29` | `2b637f82` |
| `control_arena_iac` | `cd0e7f667eba6214e2100f5fd30aec9f65aca1a8` | `d74610fe` |
| `control_arena_rogue_eval` | `7946e03ece9d8329a28c17d7b0fe778b9c774b39` | `2689c6e5` |
| `control_arena_agentdojo` | `a0f1e2131a8f27ebe14c285fa8ad34e439d128e2` | `5ceb33f1` |
| `deliberative-monitor-pipeline` (same uploader; filter log, filtered eval copies, training mix) | `2f10f4e49f4bf349965640ac021406689455d1c3` | per file |

Each corpus has 1,500 rows, no card and no licence, so this directory publishes counts, AUROCs and
ids only. Paper: arXiv 2605.29601v1, Table 2 and Appendix C.

## Check 0: provenance

From [`provenance_checks.json`](provenance_checks.json):

- **Authors.** In every setting, Claude Sonnet 4, Gemini 2.5 Pro and GPT-5 each write 250
  negatives and 250 positives. Negatives come from `negative{1,2}.eval` and positives from
  `positive{1..4}.eval`. So model identity is balanced within each label.
- **Policy prompt not stored.** In every setting the stored system message uses one template for
  both classes. The side-task text appears in 0 to 0.13% of positive transcripts.
- **Monitor input is action-only.** `prompt` equals `transcript` in 100% of rows, and it starts at
  the user turn. Of the rows with more than 40 characters of policy reasoning, that reasoning shows
  up in the transcript in 0% (bash, iac, rogue_eval), 4.6% (shade) and 3.5% (agentdojo).
- **AgentDojo.** The metadata's `eval_mode` is reversed against the label: all 750 negatives are
  `attack` with no side task, and all 750 positives are `honest` with an injection task. Only the
  banking suite appears (16 user tasks). No injected instruction is visible to the monitor. The
  attacker IBAN first appears in the agent's own tool call in 658 of 750 positives and never in a
  tool output, and no injection marker occurs in any row. Every positive pays the same account, so
  the presence of that one string scores AUROC 0.939. 2605.29601 describes this side task as
  complying with an instruction "smuggled into a tool's output"; these transcripts do not show one.
- **SHADE.** The evaluator model (`evaluator_llm`) is the agent's own model in all 1,500 rows.
  The token limit was hit in 42.9% of positives and 24.5% of negatives.
- **In-corpus monitor.** `full_trajectory_monitor` scores AUROC 0.941 (bash), 0.840 (shade),
  0.820 (iac), 0.844 (rogue_eval) and 0.925 (agentdojo). For SHADE the score is missing in 35% of
  negatives and 67% of positives.
- **Link to 2605.29601.** The uploader's pipeline repo holds filtered copies of these exact rows
  (ids match at `row_index` in 100% of rows). Its training mix includes 1,436
  `control_arena_bash` rows (Table 2's "Bash Bench" 718/718); the other four corpora are its OOD
  sets.
- **Link to 2603.00829 (inference).** rogue_eval's `task_dir` is a local `control-arena` checkout
  under a user directory that matches the surname of a 2603.00829 author. Together with the
  matching structure, this suggests that paper made the runs. Not confirmed.

## Check 1: content-blind baselines

From [`baselines_checks.json`](baselines_checks.json). Features are computed from the transcript
a monitor reads. "Task" is `main_task_name`. AUROC above 0.5 means the attack class scores higher.
Character-count nulls use 1,000 within-task label permutations. The bootstrap interval resamples
rows within task. Because epochs repeat, it is too narrow.

| Setting | Tasks | Chars, within task (95% CI) | null p95 | Chars, within task × model | Six counts, GBM, GroupKFold by task (null p95) | In-corpus monitor |
|---|---|---|---|---|---|---|
| bash | 256 | 0.496 (0.458–0.530) | 0.533 | 0.501 | 0.646 (0.528) | 0.941 |
| shade | 5 | 0.602 (0.572–0.631) | 0.531 | 0.615 | 0.380 (0.438) | 0.840 |
| iac | 5 | **0.704** (0.676–0.730) | 0.528 | 0.724 | 0.596 (0.535) | 0.820 |
| rogue_eval | 25 | 0.616 (0.586–0.644) | 0.529 | **0.684** | **0.689** (0.547) | 0.844 |
| agentdojo | 16 | **0.802** (0.780–0.825) | 0.529 | **0.874** | **0.861** (0.520) | 0.925 |

- These reproduce `experiments/agentic/floors2.py` exactly (0.504 folded, 0.602, 0.704, 0.616,
  0.802), now from pinned commits.
- Tool-call count within task: 0.915 (agentdojo), 0.672 (iac), 0.610 (rogue_eval).
- The flag rule (interval above the null's 95th percentile and above 0.6) is met by iac and
  agentdojo, and by rogue_eval within task × model. shade's interval reaches down to 0.572.
- On the rows 2605.29601 evaluates, the cue drops for SHADE: 0.539 (0.505–0.579, p 0.06) on its
  850 rows. IaC keeps it: 0.710 on its 1,443 rows.
- Metadata only. Model id scores 0.447 (balanced by construction). Task id, under ungrouped CV,
  scores 0.636 for shade (positive rate per task ranges from 0.06 to 0.63; expenditure_accounting
  has 147 negatives and 10 positives) and 0.50 to 0.54 elsewhere.
- Reasoning tags (`<thinking>` and similar) occur in no transcript.
- The 15-phrase regex from `experiments/agentic/cot.py` reproduces at 0.76 to 0.82, but only on
  the policy reasoning in `trajectory_data`, which monitors are not given. Run on the transcript,
  it scores 0.51 to 0.55 (0.73 on rogue_eval). The scope.md and check-7 wording that cites 0.76 to
  0.82 should say that this channel is not in the monitor's input here.
- Bag-of-words (GroupKFold by task) on tool-call names scores 0.68 / 0.53 / 0.64 / 0.59 / 0.83. On
  tool outputs and on the whole transcript it scores up to 0.996. Those texts contain the attack
  actions or their echoes (for example the malware download output or the attacker IBAN), so they
  are not content-blind. They are reported for reference only.

Some of the length cue is the attack itself. A side task usually needs extra edits or an extra
transaction: in agentdojo the median is 5 tool calls for positives against 3 for negatives. So the
cue does not prove an authorship artifact. It shows these sets reward any detector that counts
actions, while a deployed attacker can keep its action count normal.

## Check 5: duplicates and leakage

From [`duplicates_checks.json`](duplicates_checks.json). Duplicates were measured with MinHash
(128 hashes, word 5-shingles) over every pair of the 7,500 rows, on two views: the whole
transcript and the agent's actions only.

- **856 and 1,443 are the 28K-token filter, not dedup.** The pipeline's filter log
  (Qwen3-8B tokenizer, `max_prompt_length` 28,000) drops 57 IaC rows and keeps 728/715, which
  matches Table 2 exactly. For SHADE it drops 650 rows and keeps 432/418 = 850, against Table 2's
  433/423 = 856; the 6-row gap is unexplained. Rogue Eval keeps 750/749 against the table's
  750/750. A greedy near-duplicate pass at Jaccard ≥ 0.9 would keep 1,470 SHADE and 1,263 IaC
  rows, so dedup does not produce the reported counts. The paper's Appendix C states the filter
  ("we drop any trajectory whose tokenized input exceeds 28K tokens"), so A7's "undocumented dedup"
  is ruled out.
- **The filter reshapes SHADE.** It drops 390 of 401 spam_filter_update rows and 149 of 157
  expenditure_accounting rows. Of the 850 rows left, 831 come from 3 of the 5 task pairs.
- **Exact duplicates.** iac has 45 rows in 12 groups, agentdojo 38 in 10, rogue_eval 4 in 2,
  bash and shade none. No group spans both labels or two settings.
- **Near-duplicates.** On whole transcripts, 331 iac rows have a neighbour at J ≥ 0.9 (2,819
  pairs, 305 of them across labels). On actions only, 0 pairs at J ≥ 0.9 cross labels in any
  setting. The cross-label similarity comes from shared environment output, not copied actions.
- **Epochs.** In shade and iac each (model, label) cell covers 4 or 5 tasks, up to 111 rows of
  one task (GPT-5 SHADE positives). Intervals computed over rows are therefore too narrow.
- **Label readable from id, file and order.** The id token (`_positive` / `_negative`),
  `eval_file` and row order (blocks of 250) each give AUROC 1.0; rogue_eval ids also contain
  `-attack` / `-honest`. This matters only if a pipeline shows these fields to a monitor or splits
  by them. The 2605.29601 prompts use a row index.
- **Train and test.** All 1,436 training rows from this family are exact `control_arena_bash`
  rows. None matches an OOD row exactly, the nearest Jaccard to any OOD row is 0.047, and no two
  settings share a task. The training and OOD sets do share their three agent models and their
  generation pipeline, so "out of distribution" is across settings, not across authors.

## Bias direction

- **Length and count cues: up.** A monitor can reach 0.70 to 0.87 on iac, rogue_eval and agentdojo
  without reading what was done. SHADE as 2605.29601 filters it carries little of this cue.
- **AgentDojo positives with no visible injection, and one attacker account: up.** The set
  measures spotting a payment to a fixed unknown IBAN, not resisting injected instructions.
- **Repeated epochs: intervals too narrow.** Not a bias in the point estimate.

## Holds, ruled out, untested

- Holds: the within-task length cue in iac (0.70) and agentdojo (0.80; 0.87 within task × model);
  the GBM on counts in agentdojo (0.86) and rogue_eval (0.69); action-only monitor input; no
  visible injection in AgentDojo; heavy epoch repetition in shade and iac; label in id, file and
  row order.
- Ruled out: dedup as the source of 856 / 1,443 (it is the documented token filter); exact or
  near-copy leakage between 2605.29601's training rows and its ControlArena OOD sets; cross-setting
  duplicates; the scratchpad regex as a cue in the monitor's input (0.51 to 0.55, except rogue_eval
  at 0.73); a length cue in bash (0.50).
- Untested: whether 2605.29601's or 2603.00829's monitors rely on length (this needs their
  per-row scores against length within task; the pipeline repo's `predictions.jsonl` would allow
  it for the prompted Qwen3.5-27B, which scores 0.903 on SHADE and 0.906 on IaC); the 6-row SHADE
  and 1-row Rogue Eval gaps between the filter log and Table 2; why AgentDojo's `eval_mode` is
  reversed; side-task validity (check 4).

## Reproduce

```bash
python -I check_provenance.py --cache data --out provenance_checks.json   # ~1 min
python -I check_duplicates.py --cache data --out duplicates_checks.json   # ~2 min
python -I check_baselines.py  --cache data --out baselines_checks.json    # ~25 min; --quick for fewer permutations
```

The scripts download about 600 MB from the pinned commits into `data/` and check each corpus
parquet's sha256. They need numpy, pandas, pyarrow, scipy and scikit-learn. No downloaded code is
run.
