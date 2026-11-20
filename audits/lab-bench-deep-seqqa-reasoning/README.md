# LAB-Bench SeqQA: Sonnet 5.5's option-cue drop does not grow when it reasons step by step (0.958 → 0.875, 48 pairs, exact p = 0.22) — and every error is a gene-recall failure, not an option comparison

Status: complete, 2026-11-20, branch `audits-round3`. Pre-registration: [`prereg.md`](prereg.md),
committed in `0d84740` before any non-pilot call. Model: `claude-sonnet-5-5` only, no tools,
default extended thinking plus a visible step-by-step answer, forced choice,
`Caller(..., cap_usd=2.50, neutral_cwd=True)`. **Everything here is about Sonnet 5.5 under this
prompt. It says nothing about Opus or any published run.**

## The question

`../lab-bench-deep-seqqa` (validated) found that moving the option cue costs Sonnet 0.104 on 48
paired items under a **letter-only** prompt (5 vs 0 discordant, exact p = 0.063: "still cannot
tell"). Its validator then found that Haiku, on the same 30 Gibson pairs, drops 0.067 under that
prompt and **0.267 under a step-by-step forced prompt** (p = 0.021). Published runs let models
reason, so: does Sonnet's drop grow the same way? This folder runs the same 48 K/D pairs, same
options and option order, with the step-by-step prompt — the only change from the earlier Sonnet
run is the prompt.

## Result

| Arm | n | Accuracy | wrong | unparsed / refusals / errors |
|---|---|---|---|---|
| K (key-centred) | 48 | **0.9583** (46/48) | 2 | 0 / 0 / 0 |
| D (decoy-centred) | 48 | **0.8750** (42/48) | 6 | 0 / 0 / 0 |

| Contrast | n pairs | K − D | discordant (K-only / D-only) | exact p | 95% CI items | 95% CI subtasks |
|---|---|---|---|---|---|---|
| all six cue subtasks | 48 | **0.0833** | 5 / 1 | **0.219** | [0.000, 0.188] | [−0.033, 0.183] |
| Gibson only | 20 | 0.100 | 3 / 1 | 0.625 | [−0.100, 0.300] | [−0.150, 0.301] |
| the other four | 28 | 0.0714 | 2 / 0 | 0.500 | [0.000, 0.179] | [0.000, 0.175] |

**Verdict by the pre-registered rule: cannot tell** (the "yes" rule needed K − D ≥ 0.10 *and*
exact p < 0.05; the "no" rule needed an upper bound below 0.10, and it is 0.188). The earlier
folder's rule gives "still cannot tell" as well.

**Sonnet's drop does not grow under reasoning.** On the same 48 pairs, reasoning minus letter-only
difference-in-differences is **−0.021 [−0.104, 0.063]**: no detectable change, in contrast to
Haiku, where the same prompt change quadrupled the drop. The design had 97.5% power against a
Haiku-sized drop of 0.27 and 32% against 0.10 ([`power.json`](power.json)), so a 0.27-sized
effect is ruled out and a 0.10-sized one is not resolved either way.

**It does not follow the decoy centre.** Under D the new centre is picked at **0.021** against
**0.049** per other distractor; 1 of 6 D errors went to the centre, 5 to the "other gene" option.
On Gibson alone the centre was never picked (0.000 vs 0.075).

Per subtask (K → D, 6–10 pairs each): GC-percent 1.00 → 1.00; ORF-seq-AAseq 1.00 → 1.00;
PCR-seq-enzprimers 1.00 → 1.00; PCR-gene-enzprimers 0.90 → 0.70; PCR-gene-gibshind 0.90 → 0.90;
PCR-gene-gibssma 1.00 → 0.80. **All 8 errors of both arms fall on the three subtasks where the
gene sequence is not in the question**; the three computable subtasks were perfect in both arms
(18 pairs, 36 calls).

### Why it errs (reasoning text, labelled per `prereg.md`)

Labels in [`validation_labels.json`](validation_labels.json), read from a shuffled, letter-token
copy of each error ([`scripts/analyze.py`](scripts/analyze.py) writes it; the blinding is partial,
because the substitution missed bare letters in prose such as "Options X and C" — the labels do
not depend on which option was the centre, and no text names a centre).

| Label | D errors | K errors |
|---|---|---|
| **recall** (states or relies on a remembered *E. coli* gene sequence) | 5 (one with a correct frame argument applied to a mis-recalled start) | 1 |
| **computes and slips** (checks sites, frame, translation and errs) | 0 | 0 |
| **compares** (attributes the choice to which option the others resemble) | **0** | **0** |
| other / unclear | 0 | 1 (says it could not recall the gene and chose by primer design) |

Five of the six D errors say in so many words that they are working from memory, for example
"I recognised these sequences from memory rather than checking them against a database" and
"the start and stop assignments rest on my recall of the sequence". None of the eight errors says
it compared the options with one another. So on these items, with reasoning visible, Sonnet's
failures look like gene-identity recall on the subtasks where the sequence is withheld, not like
consensus-picking.

### Discordant pairs (recount from the cache)

Roles: 0 = key, 1 = shifted body (the decoy centre in D), 2 = other gene, 3 = rebuilt wrong-site
option. Full rows in [`results/discordant.csv`](results/discordant.csv); every arm's answer for
all 48 pairs is in [`results/runs_main.csv`](results/runs_main.csv).

| item id | subtask | key | K answer (role) | D answer (role) | centre role |
|---|---|---|---|---|---|
| `799f3052-f6e5-4e2f-84b3-c43ce418d740` | gibshind | A | D (2) | A (0) | 1 |
| `6452f1be-4efb-4146-8cdc-4ff48357560c` | gibssma | A | A (0) | C (2) | 1 |
| `df397f08-19db-442e-a6ba-7eb0b9a125a4` | gibshind | B | B (0) | D (2) | 1 |
| `0eafde3b-6246-4ff7-9954-2a55c593a086` | gibssma | B | B (0) | C (2) | 1 |
| `1421394f-98d4-4153-99c3-e11e668de733` | gene-enz | C | C (0) | A (2) | 1 |
| `44c3cf75-4d5e-4c94-a643-e2e0899babd3` | gene-enz | C | C (0) | B (1) | 1 |

The sixth D error, `70a336ff-90d7-4de8-9dcc-27963813a33f` (gene-enz), is wrong in both arms
(K answer D, role 2; D answer D, role 2) and so is not discordant.

## Evidence level

L4 for Sonnet 5.5 under this prompt, **inconclusive**: a drop of 0.083 with an interval reaching 0
and an exact p of 0.22 neither establishes nor rules out a 0.10-sized reliance. What *is*
established at this n: the Haiku-sized amplification (0.27) does not happen for Sonnet
(difference-in-differences −0.021 [−0.104, 0.063]), and Sonnet does not pick the decoy centre
(0.021 vs 0.049). The error labelling is a blind-ish read of 8 texts and is a lead.

## What this does and does not show

- It does show that the one prompt difference that quadrupled Haiku's drop leaves Sonnet's
  unchanged, so the earlier folder's "still cannot tell" for Sonnet is not an artefact of its
  letter-only prompt.
- It does not show that Sonnet ignores the cue: the upper bound is 0.188, and 48 pairs cannot
  resolve a 0.10 effect (32% power).
- It does not cover the 10-shot setting or tool use of published runs, visible-chain-of-thought
  variants other than this one, or any model but Sonnet 5.5. No per-item outputs of any published
  model exist.
- It does not re-verify the items: keys were verified by computation in the parent folder and
  again, independently, by its validator (160/160 sites, 40/40 GC, 40/40 longest forward ORF,
  40/40 blind hand-read picks).
- The 8 error texts are the model's own account of its reasoning; the extended-thinking tokens
  are not returned, so the account may not be the process.

## Pins and how to reproduce

- Items and arms: `../lab-bench-deep-seqqa/data/arms.json` and the 48 Sonnet pairs in that
  folder's `plans/b1_sonnet_pilot.json` + `plans/b2_sonnet_main.json`; SeqQA parquet
  `futurehouse/lab-bench` @ `5c77cec6…`, sha256 `5864776d…` (asserted at load).
- Prompt: the parent audit's template (`../lab-bench/scripts/haiku.py`), forced, quoted in
  `scripts/run.py`.
- Spend: 100 Sonnet calls, **2.1186 USD** of this folder's 2.50 cap
  ([`inference/ledger.jsonl`](inference/ledger.jsonl)); 4 of those were the cost pilot on two
  Gibson pairs outside the sample (0.0871 USD), mean 0.0212 USD per call. Responses are cached
  (git-ignored), so reruns cost nothing.
- Deviations from the prereg: none. The pilot cost 0.022 per call as assumed and the full 48
  pairs fitted.

```bash
cd audits/lab-bench-deep-seqqa-reasoning
P="../lab-bench/data/.venv/bin/python -I"
$P scripts/power.py              # -> power.json
$P scripts/run.py pilot          # 4 calls, items outside the sample
$P scripts/run.py main           # 96 calls -> results/runs_main.csv   (cached)
$P scripts/analyze.py            # -> results.json, results/discordant.csv, blind error texts
```

Seeds are 0 (1 for the error shuffle). Option orders are hashes of item ids, as in the parent.
