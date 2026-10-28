# Control Tax backdoor set: checks 1, 5 and 4

Status: run 2026-10-27 on pinned copies. Nothing reported to anyone.

## What was audited

| Source | Pin |
|---|---|
| Control Tax release, `data/backdoor_code_full.json` in `MikhailTerekhov/control-tax-code` (MIT) | commit `8ecbbec8a75e3777b8cc70cc8a73de6d60c340fd`; sha256 `e52530f2…f3f4ef`, the same bytes as the project page's `backdoor_code_paper.json` |
| ControlArena copy, `RoganInglis/apps-control-arena` (MIT) | revision `29db28f76042952d56add8671f798280b200744d` |
| Control Tax monitor and build code (read, not run) | same commit: `monitors/inspect_monitor.py`, `backdoors/extract_backdoor_code.py`, `backdoors/backdoor_solvers.py` |

The release has 8,855 backdoors on 2,368 APPS test-split problems from nine attackers.

How Control Tax scores a monitor (`inspect_monitor.py`):

- Each record becomes two samples: `correct_code` labelled benign and `backdoored_code` labelled backdoored.
- Both have comments removed and are formatted with Black.
- `correct_code` is one fixed human solution per problem. It is also the program the attacker was told to edit ("modify the correct code").
- So in Control Tax's own protocol every problem is in both classes equally often, and the benign program is the source of its backdoor.

The paper in this repo already measured the ControlArena copy with the DSPy tutorial's pairing (bag-of-words 0.897 pairwise) and its metadata leak. None of that is repeated here. The results below are for Control Tax's own pairing, and for how the ControlArena copy differs from the release.

## Results

### Check 1: detectors that do not read what the backdoor does (holds, with a caveat)

Setup, from [`baselines_checks.json`](baselines_checks.json) ([`check_baselines.py`](check_baselines.py)):

- Both classes are normalised with `ast.unparse`, which removes comments and layout.
- Detectors are fitted with GroupKFold(5) by problem.
- The null flips the labels at random within each pair and refits the whole pipeline. Because of CPU limits it ran with 20 permutations, on the headline TF-IDF row only, not the suite's 1,000. The other rows have no null and are untested against one; they are single features or are compared against each other.
- TF-IDF uses the paper's settings.

| Detector, Control Tax's own pairing (8,855 pairs) | AUROC (95% CI, problem bootstrap) | Null 95th pct | Pairwise acc. |
|---|---|---|---|
| TF-IDF + logistic | 0.848 (0.841–0.854) | 0.505 (20 permutations; p = 1/21, the smallest possible) | 0.946 |
| 6 surface counts | 0.710 (0.702–0.718) | — | 0.862 |
| Character length | 0.596 | — | 0.842 |
| `if` count | 0.660 | — | 0.710 |
| Integer constants ≥ 3 that are not in the statement | 0.586 | — | — |
| Metadata (difficulty, tests, statement) | 0.5 exactly, by construction | | |

The TF-IDF signal depends on how much the attacker rewrote the source rather than editing it. Out-of-fold TF-IDF AUROC by token-sequence similarity between the backdoor and its source:

| Similarity to source | Backdoors | AUROC | Pairwise |
|---|---|---|---|
| [0, 0.5) | 826 | 0.971 | 0.975 |
| [0.5, 0.8) | 3,215 | 0.920 | 0.978 |
| [0.8, 0.9) | 2,145 | 0.849 | 0.960 |
| [0.9, 0.97) | 1,920 | 0.729 | 0.946 |
| [0.97, 1] | 749 | 0.557 | 0.730 |

By attacker, with TF-IDF fitted and tested on that attacker's records only:

| Attacker | n | Median similarity to source | TF-IDF AUROC (CI) | Length AUROC |
|---|---|---|---|---|
| o3-mini | 2,261 | 0.672 | 0.942 (0.937–0.948) | 0.576 |
| Claude 3.7 Sonnet | 1,864 | 0.848 | 0.863 (0.853–0.871) | 0.638 |
| o1-mini | 1,250 | 0.872 | 0.792 (0.779–0.804) | 0.567 |
| GPT-4o | 1,148 | 0.872 | 0.827 (0.816–0.840) | 0.598 |
| Gemini 2.0 Flash | 715 | 0.867 | 0.793 (0.776–0.812) | 0.590 |
| Claude 3.5 Haiku | 591 | 0.828 | 0.870 (0.853–0.884) | 0.646 |
| Claude 3.7 Sonnet Thinking | 517 | 0.897 | 0.783 (0.765–0.805) | 0.583 |
| GPT-4o-mini | 367 | 0.883 | 0.756 (0.734–0.779) | 0.570 |
| GPT-3.5-Turbo | 142 | 0.908 | 0.641 (0.601–0.676) | 0.575 |

- A program guard (`if __name__ == "__main__"`) appears in 11.5% of backdoors against 0.03% of benign programs: 1,019 backdoors add one that their source lacks. On its own it scores AUROC 0.558. This is the attacker restructuring the program, not the sabotage.
- Comparing the two pairings on the same 6,777 backdoors, where the DSPy-zip partner is not the edited source:
  - pooled TF-IDF AUROC is 0.843 with Control Tax's pairing (Control Tax's own) and 0.853 with the DSPy-zip partner;
  - pairwise accuracy is 0.941 and 0.873.
- So the DSPy-tutorial pairing is not where most of this signal comes from. The backdoored programs carry it themselves.

Reading:

- Under Control Tax's own protocol, a supervised TF-IDF detector reaches 0.85. On o3-mini's backdoors it reaches 0.94, against the paper's o3-mini monitor at 0.92–0.96.
- Most of that comes from attackers that rewrite the whole program: 0.97 where similarity is below 0.5, against 0.56 where it is 0.97 or more.
- That is an authorship cue. A rewritten program reads as LLM code next to the human source.
- Pairwise accuracy stays high even for small edits (0.73 at ≥ 0.97). That part reads the inserted condition (`and`, `==`, `if`), which is the attack itself and is not counted as a shortcut.
- Caveat: the detector is trained, and the monitors are zero-shot. Whether the paper's monitors use the cue is untested.
- Bias: up on catch rate, by an amount that differs between attackers.

### Check 5: duplicates, splits, ids (mostly ruled out; one ControlArena build issue found)

From [`dups_checks.json`](dups_checks.json) ([`check_dups.py`](check_dups.py)):

- **Splits.** Control Tax has no train/test split, and no monitor is trained on it, so cross-split leakage does not apply.
- **Repeated benign programs.** Each problem's one benign program appears once per attacker that succeeded on that problem, so 2,368 distinct programs fill 8,855 benign slots. Per-attacker AUCs are unaffected. Pooled or trained uses would repeat benign items up to 9 times.
- **Identical backdoors.**
  - No (problem, attacker) key repeats.
  - No backdoor equals its own source after normalising.
  - 72 backdoors (0.8%, in 58 groups) are identical to another attacker's backdoor on the same problem.
  - 5 are identical to a backdoor on a different problem.
- **Ids.**
  - The monitor's sample ids contain the label (`<id>_<model>_benign`), but only the code is passed to the monitor, and the samples are shuffled with a fixed seed.
  - Nothing label-bearing reaches the monitor.
- **Triggers.**
  - 639 triggers are shared with another attacker on the same problem.
  - 854 equal a stored APPS test input. Those are legal inputs, and the backdoor fails that hidden test.
  - 1 equals a public test the backdoor was shown.
- **ControlArena copy, join.** It joins correctly for Control Tax rows: all 8,855 are found, and statements and triggers are identical. The zero-padding bug in the repo finding `controlarena-apps-join` concerns the other source only.
- **ControlArena copy, rewritten code (new).**
  - The build passes backdoor code through `fix_solution`, which rewrites `return` to `exit()` where it thinks the line is outside a function.
  - In 332 of 8,855 Control Tax backdoors (3.7%), a rewritten `return` sits inside a function by Python's own parser, which changes what the program does.
  - In those, ControlArena's `backdoor_works` is true for 19 of 332 (5.7%), against 2,759 of 8,304 (33.2%) for code the build left unchanged.
  - Another 39 have `nonlocal` changed to `global`.
- **ControlArena copy, pairing.** Its DSPy-tutorial pairing (`zip(solutions, backdoors)`) puts a backdoor against the program it was made from in 1,950 of 8,813 pairs (22%).
- **ControlArena copy, `backdoor_works`.**
  - It is true for 2,842 of 8,855 (32%), because ControlArena requires all tests to pass and the release required only ≤ 5 public tests.
  - The share differs by attacker: o1-mini 17%, Claude 3.7 Sonnet 44%.
  - Not rerun here.

### Check 4: trigger validity, statically (holds at the flag threshold; interval wide)

From [`triggers_checks.json`](triggers_checks.json) ([`check_triggers.py`](check_triggers.py), [`validators.py`](validators.py)).

Sample and validators:

- A seeded sample of 50 records, one per problem (seed 20261027, [`sample_triggers.py`](sample_triggers.py)).
- For each sampled problem, a validator was written from the statement alone. The statements were dumped without triggers, code or hints, and the validators were fixed before any trigger was read.
- Each validator was calibrated on all 2,247 stored APPS test inputs and the public tests of its problem. None rejects a stored input.
- No solution was run.

| | Invalid | Rate | 95% interval |
|---|---|---|---|
| Sample, 50 triggers on 50 problems | 5 | 10.0% | 4.3–21.4% (Wilson) |
| All 222 Control Tax triggers on those 50 problems (secondary; clustered in 9 problems) | 16 | 7.2% | 4.5–11.4% (Wilson, ignores clustering) |

The five rejections in the sample:

- an odd number of quotes, where the statement guarantees an even number;
- a tic-tac-toe position that is not reachable on Ilya's turn;
- `n = 2^63 − 1` against `n ≤ 10^18`;
- a coupon cost of 0 against `w ≥ 1`;
- `b > d` against `b ≤ d`.

Among all 222 triggers the failures also include rows of the wrong length and strings whose length does not match the stated `n`. 12 of the 16 come from o1-mini (4), Claude 3.7 Sonnet (5) and Gemini 2.0 Flash (3), but the counts per attacker are too small to compare.

Reading:

- The point estimate is above the suite's 5% flag rule, but the interval includes 5%.
- Invalid triggers are positives with nothing to catch on a legal input. Their effect:
  - if monitors miss them, catch rates are biased down;
  - they inflate attacker success rates.
- Validators check bounds and stated guarantees. One of them (problem 1258) checks consistency with a permutation only in part. Validators can still be too lax, so the rate is a lower bound for what these 50 statements forbid.

## Holds / ruled out / untested

- **Holds:**
  - A content-blind TF-IDF reaches 0.85 under Control Tax's own pairing, and 0.94 on o3-mini. It is driven by rewrite style, and its strength varies by attacker.
  - About 10% of sampled triggers are illegal (4–21%).
  - The ControlArena build rewrites `return` inside functions in 332 Control Tax backdoors.
- **Ruled out:**
  - Metadata leakage under Control Tax's protocol (0.5 by construction).
  - Split leakage (no split).
  - Label-bearing ids.
  - A broken Control Tax join in ControlArena.
- **Untested:**
  - Whether the paper's monitors read the rewrite cue (it needs their scores, which are not released).
  - Per-attacker invalid-trigger rates with useful precision (it needs more validators).
  - Whether backdoors with legal triggers are really wrong (it needs running code).
  - Why 170 of 2,368 benign programs that Control Tax verified are marked `passes_tests = false` in ControlArena (38 of them were rewritten by `fix_solution`; seen in exploration, not in the json).

## Reproduce

```bash
cd out
python -I check_dups.py      --cache ../data --out dups_checks.json
python -I check_baselines.py --cache ../data --out baselines_checks.json --headline-perms 20   # ~10 min CPU
python -I sample_triggers.py ../data          # rewrites trigger_sample.json (same seed, same ids)
python -I check_triggers.py  --cache ../data --out triggers_checks.json
```

The scripts download to `../data` at the pins above and check the hashes. They need numpy, pandas, pyarrow and scikit-learn. The release is MIT, but the outputs keep ids and aggregates only.
