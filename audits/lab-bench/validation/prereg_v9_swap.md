# Validator pre-registration: single-option swap on the Gibson subtasks (claim 2)

Written and committed by the validator before any `--run` of `validation/v9_swap.py`. The
construction (`--build`) has been run; it uses no model output.

## Why

The auditor's edit replaced three of four options and its key-centred control was added after
the result. The validator's hand read found the edit also (a) drops the "other gene" distractor G,
(b) adds a one-base-deleted variant (S2) that breaks the vector junction, and (c) makes the key the
unique longest option in 70% of Gibson items (0% originally). A cleaner test changes one option.

## Design

- Items: every PCR-gene-gibshindprimers and PCR-gene-gibssmaprimers item (80) for which the
  construction passes its checks: 62 (39 of them among the auditor's 50, 23 fresh). No item is in
  the content-screen exclusions; no item was refused before.
- Arms, both forced-choice with the auditor's prompt and the auditor's option order (hash of the
  item id, so the key's letter is the same in both arms):
  - `forced`: original options {K, S, G, W} (cached for the 39 overlapping items).
  - `swap1`: {K, S, WS, G}. Only W (wrong overlap + key body) is replaced by WS (wrong overlap +
    S's body). K, S and G are unchanged strings.
- Check (fixed, already applied): in `swap1`, S is the unique centre under both the validator's
  summed-Levenshtein rule and a 3-gram Jaccard rule; in `forced`, K is the Levenshtein centre on
  all 62.
- Calls: 62 + 23 = 85, about 0.18 USD at the observed 0.0021 USD per Gibson call. Stop at the cap.

## Statistic and decision

- Primary: paired accuracy drop forced − swap1, item bootstrap (2,000, seed 0).
- **Replicates "Haiku follows the centre"**: drop ≥ 0.10, 95% interval excluding 0, and S picked
  more often under swap1 than under forced.
- **Fails to replicate**: upper bound of the interval < 0.10.
- **Inconclusive**: anything else.
- Secondary, descriptive: pick rates of S, WS and G; per subtask; previous 39 vs fresh 23; accuracy
  in swap1 split by whether the key is the unique longest option (52% of items).
- Errors and unparsed answers count as wrong and are reported by bucket; refused items are not
  retried.
- Whatever the outcome, it is reported in `validation/VALIDATION.md` as the validator's result,
  Haiku only.
