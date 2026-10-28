# WMDP: content-blind cues in bio and cyber; few duplicates; few structural key defects

Audit date 2026-10-27. Checks 1 (content-blind baselines), 5 (duplicates) and 6 (key errors) of the
audit repo's check suite (`scope.md` §2). Nothing here has been reported to the maintainers.

## What was audited

Weapons of Mass Destruction Proxy (WMDP), Li et al.,
[arXiv 2403.03218](https://arxiv.org/abs/2403.03218);
data [`cais/wmdp`](https://huggingface.co/datasets/cais/wmdp) at revision
`7125571f22f032c56415e7980f48d877dd830ff8` (not gated). Three subsets, one `test` split each,
four choices per item, so chance is 0.25:

| Subset | Items |
|---|---|
| wmdp-bio | 1,273 |
| wmdp-chem | 408 |
| wmdp-cyber | 1,987 |

Parquet files, checked by sha256 against the Git LFS oids at that revision:

```
738cee28e11e4dcf9a0efc6b2c22b425bddda4b2b69477a11f38539c86cf00b7  wmdp-bio/test-00000-of-00001.parquet
b9e5f2be6c7526931ae8aeb2eea246baa4144d2ba8d0de1de09905aaa84912ce  wmdp-chem/test-00000-of-00001.parquet
ec65f7ba4a9cd1ef368618ebd2b90b6d930f9b9f053f67a926b82fd71d87b4fe  wmdp-cyber/test-00000-of-00001.parquet
```

Licence: the dataset card at that revision declares `license: mit` in its YAML front matter, so
this write-up still reports aggregates and item ids only, and no question or answer text.

Published numbers this bears on: the WMDP paper's Table 1 reports RMU unlearning taking bio from
63.7–75.3 to 30.7–34.0 and cyber from 44.0–52.0 to 28.2–30.8, with "25% is random". Later
unlearning work and frontier system cards read WMDP accuracy as hazardous knowledge, and
sandbagging evaluations read a low WMDP score as a model withholding what it knows.

## Results

All numbers from [`baseline_checks.json`](baseline_checks.json),
[`duplicate_checks.json`](duplicate_checks.json) and [`key_checks.json`](key_checks.json),
produced by the three scripts in `../scripts/`. Intervals are Wilson 95%; ties share credit.

### Check 1, content-blind baselines: holds on bio and cyber, not on chem

| Heuristic | bio (1,273) | chem (408) | cyber (1,987) |
|---|---|---|---|
| longest choice | **0.463** [0.436, 0.491] | 0.304 [0.261, 0.350] | 0.252 [0.234, 0.272] |
| shortest choice | 0.154 [0.135, 0.175] | 0.222 [0.183, 0.263] | **0.350** [0.330, 0.372] |
| most word overlap with the question | 0.264 [0.241, 0.290] | 0.241 [0.201, 0.284] | 0.283 [0.263, 0.303] |
| best fixed position | 0.266 [0.242, 0.290] | 0.265 [0.224, 0.310] | 0.266 [0.247, 0.286] |
| options only, question hidden | **0.387** [0.361, 0.414] | 0.294 [0.252, 0.340] | **0.353** [0.332, 0.374] |
| its permutation null, 95th pct | 0.277 | 0.286 | 0.264 |
| three-rule composite | **0.463** [0.436, 0.491] | 0.304 [0.261, 0.350] | **0.479** [0.457, 0.501] |

The options-only classifier is a logistic regression over TF-IDF of the choice text alone, scored
per item as the argmax of P(correct) over its four choices, under 5-fold GroupKFold with
near-duplicate items held in the same group. Its null is the same pipeline with the key permuted
within each item, 200 permutations. Bio and cyber sit above their nulls' 95th percentile; chem does
not (0.294 against 0.286).

Cyber is two populations. Half of it, 991 of 1,987 items, comes from four generated templates
(captured-packet field lookups, "which arguments will cause", "what number is returned", program
output). Splitting on that:

| Heuristic | cyber templates (991) | rest of cyber (996) |
|---|---|---|
| longest choice | 0.100 [0.083, 0.120] | **0.403** [0.374, 0.434] |
| shortest choice | **0.509** [0.477, 0.540] | 0.193 [0.169, 0.218] |
| pick 0 among all-numeric choices | **0.906** [0.825, 0.952] (85 items) | — (3 items) |

So the hand-written cyber items carry bio's length cue (0.403), and the generated items carry the
opposite one: the key is the shortest string in 50.9% of them, and where the four choices are all
numeric and one of them is 0, that 0 is the key about 91% of the time (85 such items inside the
templates; 78 of 88 across the whole subset). The composite row above is a
three-rule policy, fixed in the script: pick 0 among all-numeric choices, else the shortest choice
inside the templates, else the longest. Its rules were picked after seeing which family carries
which cue, so 0.479 on cyber (0.556 on the templates, 0.402 on the rest) is an upper bound for a
content-blind policy rather than a held-out estimate; the per-cue rows are the plainer numbers.

Two smaller cues:

- "All/none of the above"-type options are rare but usually keyed: 22 items in bio, accuracy 0.795
  [0.615, 0.927]; 7 in chem, 0.643 [0.250, 0.842]; 88 in cyber, 0.330 [0.240, 0.433].
- The key's position is uniform in every subset (chi-square against uniform: bio p = 0.62, chem
  p = 0.75, cyber p = 0.45). Ruled out.

What this means for the published numbers. On bio, picking the longest choice scores 0.463, above
every post-RMU accuracy in the WMDP paper's Table 1 (30.7–34.0) and above the "25% is random" line
the table invites readers to compare against. A model that keeps ordinary exam heuristics and
nothing else does not score 0.25 on this benchmark. Length and options-only cues are present in
some strength in 2 of 3 subsets.

### Check 5, duplicates: ruled out as a validity flaw, with one note on item diversity

WMDP ships a single `test` split per subset, so there is no train/test boundary to leak across.
Within and across the subsets:

| Measure | Count |
|---|---|
| Identical question and identical choice set | 2 pairs, both cyber (`cyber-122`/`cyber-1826`, `cyber-499`/`cyber-1149`) |
| Identical question, any choices | 5 groups (1 chem, 4 cyber) |
| Item-level 3-shingle Jaccard ≥ 0.5 | 121 pairs: 120 cyber–cyber, 1 chem–chem, 0 cross-subset |
| of those, ≥ 0.9 | 4 pairs |
| of those, not involving a generated cyber template | 21 pairs |
| Different questions, identical choice set | 9 groups (bio 3, chem 1, cyber 5) |

Exact duplicates are 2 of 3,668 items, 0.05%, below the 1% flag rule. The identical-choice-set
groups are mostly families of questions built over one small answer pool, which is a mild
content-blind cue inside a family but not a duplicate.

The diversity note: 991 of the 1,987 cyber items are four generated templates, so the subset holds
roughly 1,000 independent hand-written items plus four large machine-generated families.
Confidence intervals computed over items treat those families as independent.

Answerability from another item: the keyed choice occurs verbatim inside some other item's
question in the same subset, with none of that item's distractors occurring there, for 1.4% of bio,
0.5% of chem and 1.0% of cyber items at a 3-word minimum (4.0%, 6.1%, 1.7% at 2 words). At these
rates, and with shared terminology the likely driver, this was not pursued further.

### Check 6, key errors: structural defects are rare; domain re-keying untested

Only flags decided from an item's own structure were run, so none requires restating content:

| Flag | bio | chem | cyber |
|---|---|---|---|
| Identical question, disjoint choice sets | 0 | 1 pair (`chem-339`/`chem-340`) | 1 pair (`cyber-161`/`cyber-1756`) |
| Identical question and choices, different keyed text | 0 | 0 | 0 |
| A choice string repeated in the item, the key among the copies | 1 | 0 | 15 |
| A choice string repeated, key not among the copies | 1 | 0 | 20 |
| All-numeric choices with two numerically equal | 0 | 0 | 5 |
| Two or more "of the above"-type choices | 0 | 0 | 0 |
| Items with one of the defects above | 1 (0.08%) | 1 (0.25%) | 21 (1.06%) |

The two disjoint-choice pairs ask the same question over answer pools with nothing in common.

- `cyber-161`/`cyber-1756`: in one of the two the options are about a different subject from its
  own question stem, so its key cannot be checked against what the item asks. Called a defect.
- `chem-339`/`chem-340`: each key may be right inside its own pool, so this is a pair of items
  under one question rather than a wrong key. Marked uncertain, and counted in the table.

The repeated-choice items offer two identical strings of which one is keyed, so a grader marking by
position accepts one of two equally correct answers; where the repeat is a distractor, a guesser
faces three distinct options and chance is 1/3 on those items.

Below the 5% rate that would change a published conclusion, so the structural part of check 6 is
ruled out.

Untested: a hand sample per subset re-keyed against the question's domain content. Doing that for
bio and chem means reading and then justifying hazardous detail in writing, which this audit does
not do. The structural flags above are what can be established without it, and they do not bound
the domain key-error rate. The WMDP paper states each question was checked by at least two experts
from different organizations.

## Bias direction

One mechanism, read three ways. The cues let a model score above its hazardous knowledge.

- A WMDP score read as hazardous capability is therefore an upper bound: the model looks more
  capable, that is less safe, than it is. **Down** in this repo's convention.
- The same inflation applies to the residual score after unlearning. Post-RMU bio sits at
  30.7–34.0, below the 0.463 that the length cue alone scores, so that residual is not evidence of
  remaining hazardous knowledge and "driven to near chance" compares against the wrong floor. Read
  as "unlearning left something behind", the artifact biases **up**.
- For sandbagging, a model hiding its knowledge has to suppress the cues as well, and how far a
  cue-only score sits above 0.25 is part of what a low score is being compared against.

## What is new against prior work

Prior work on these cues covers bio only:

- Farrell, Lau and Conmy, [arXiv 2410.19278](https://arxiv.org/abs/2410.19278), Appendix A: the
  longest answer is correct in 42% of WMDP-Bio; "all of the above"-type options are "correct most
  of the time"; gemma-2b-it, prompted without the question, answers 39 of 172 items (23%)
  correctly under all 24 choice permutations, 72 of 172 at a 20-of-24 threshold.
- O'Brien et al., Deep Ignorance, [arXiv 2508.06601](https://arxiv.org/abs/2508.06601): the
  longest answer yields 46% on WMDP-Bio; they publish a 868-item "Robust MCQA" subset that drops
  items three other LLMs could guess choice-only, and a 1,076-item verified-cloze subset.
- Both cite Balepur et al. 2024 for choice-only answering in general. Thaker et al.,
  [arXiv 2410.02879](https://arxiv.org/abs/2410.02879), argue unlearning benchmarks including WMDP
  are weak measures, on different grounds.

Reproduced here: bio longest-answer 0.463, which agrees with Deep Ignorance's 46%.

New here:

- chem and cyber measured at all. Chem has a weak length cue (0.304) and no options-only signal
  above its null. Cyber's subset-level length cue is absent (0.252) because its two halves pull
  opposite ways; the hand-written half is at 0.403 and the generated half rewards the shortest
  choice (0.509) and the numeric 0 (0.906 on 85 items).
- a model-free options-only measurement: a fitted classifier over choice text with grouped
  cross-validation and a within-item key-permutation null, rather than prompting an LM. Bio 0.387
  and cyber 0.353 against null 95th percentiles of 0.277 and 0.264.
- intervals on the "of the above" cue (bio 0.795 on 22 items).
- the key-position distribution shown uniform in all three subsets. The 62% "A" rate reported for
  an RMU-modified model elsewhere is a property of that model, not of the keys.
- the duplicate and structural key-defect censuses, including the generated-template share of
  cyber (49.9%) and the 37 items with a repeated choice string.

## Reproduce

```bash
python -I check_baselines.py  --cache data --out baseline_checks.json --perms 200
python -I check_duplicates.py --cache data --out duplicate_checks.json
python -I check_keys.py       --cache data --out key_checks.json
```

Each script downloads the three parquet files from the pinned revision into `data/` if absent and
refuses to run if a file's sha256 does not match the pin. `check_baselines.py` takes about two
minutes at 200 permutations; the other two are seconds. Requires numpy, scipy, scikit-learn and
pyarrow.
