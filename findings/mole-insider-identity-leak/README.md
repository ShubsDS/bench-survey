# MOLE: insider identity carries across the day split; the labels hold up where checked

Status (2026-10-27): check 5 confirmed in the data, effect on the paper's monitor search
**untested**; check 6 lead as stated ruled out by the paper, one narrower inconsistency confirmed
in collusion accounts; check 1 ruled out on the paper's ranking metric, flagged on AUROC only.
Not raised with the authors.

## Background

Muhamed and Smith, "Mole: Detecting Insider Threats in AI Agents"
([arXiv 2609.06966v1](https://arxiv.org/abs/2609.06966)), simulate 150 AI-operated accounts over
30 workdays. 38 fixed accounts are given a malicious persona on some days; a GPT-4o judge labels
each such account-day `executed`, `attempted`, `refused` or `no_attempt`. Monitors rank accounts
each day under a review budget of 10. Main results: the best of 37 semantic monitors reaches
R@10/day 0.533 ("misses nearly half"), and an automated search raises budget-AUC over uniform
GPT-4.1 by 59% (GPT-5.3 single-day), 64% (GPT-5.3 multiday) and 49% (Kimi-K2.6 single-day).

## Pins

| Source | Pin |
|---|---|
| Data, `forgelab/mole` (Apache-2.0) | revision `7eb86b0d2918c32760fe8a91b78bb50ccc054ce5` |
| Code, `aashiqmuhamed/mole` (Apache-2.0) | commit `702199e40fe25065290a1fb7933865d67eee1dc2` |
| Paper | arXiv 2609.06966v1, PDF sha256 `1f2ddb66…af92f0d` |

File sha256 values match the Hub's LFS ids (e.g. labels `gpt53_single_day` `c7163c79…`, audit
`gpt53_single_day` `2c40b6cc…`, audit `kimi_k26_single_day` `a7dc41e3…`, transcripts
`gpt53_single_day` `ebffc37f…`).

All numbers below use the paper's RQ2/RQ5 setup unless stated: GPT-5.3 single-day corpus,
collusion accounts removed, days 1–12 train, 13–15 validation, 16–30 test. This gives 2,106
test account-days with 45 executed positives, the paper's counts (Kimi: 2,101 and 48, also the
paper's). R@10/day and budget-AUC (mean R@K/day, K = 1..10) break ties at random, averaged over
20 seeds. Nulls use 200 permutations.

## Check 5: account identity crosses the day split (holds)

From [`identity_checks.json`](identity_checks.json):

| Score (constant per account) | AUROC | null p95 | budget-AUC | R@10/day |
|---|---|---|---|---|
| Earlier pass's setup (all 150 accounts, 15/15 split): executed on a training day | 0.882 | 0.537 | | |
| Paper split: executed on a training day | 0.841 | 0.546 | 0.210 | 0.382 |
| same, using training labels of non-held-out accounts only | 0.760 | 0.534 | 0.214 | 0.385 |
| Listed in the public `bootstrap/insider_assignment.yaml` (no labels used) | 0.903 | 0.552 | 0.192 | 0.347 |
| Kimi-K2.6, executed on a training day | 0.900 | 0.549 | 0.184 | 0.348 |

Published references on the same test set: GPT-4.1 budget-AUC 0.187 and R@10/day 0.222;
GPT-5.5 0.391 and 0.511; the three classical monitors R@10/day 0.156–0.222; median of the 40
monitors 0.367. The account-permutation null (which accounts are flagged, shuffled) has p95
0.545–0.574.

Further measurements:

- 37 of the 45 test positives are on the 22 accounts that also had an executed day in training.
  All 10 validation positives are on accounts that are also test positives.
- The same 38 insider accounts appear in all eight label files (36–38 in each multiday file).
- Reciprocal-rank fusion of a zero-cost action-rarity score (the paper's definition, Appendix
  L.3) with either identity score gives budget-AUC 0.360–0.378 and R@10/day 0.489–0.511, close
  to GPT-5.5.
- Label-free features partly read the account. On negative test days only, insider accounts
  score above other accounts with AUROC 0.586 (action rarity), 0.695 (distinct actions) and
  0.680 (sequence novelty against the account's previous 7 days). Within the 30 insider
  accounts, attack days score above their other days with AUROC 0.629, 0.565 and 0.592.
- Action rarity alone scores budget-AUC 0.264 and R@10/day 0.378 on the test set, above uniform
  GPT-4.1 (0.187), the reference the search improves on.

What it changes:

- **"Best monitor misses nearly half": not affected by this lead.** The semantic monitors use no
  training data, and the z-score fit is global (`mole/monitors/classical/anomaly.py`).
- **Search gains (49–64%): untested; the setup leaves room for identity to contribute.** The
  search interface rejects hard-coded account ids and hides labels (Appendix L.1), which closes
  the direct route. Three routes stay open: (1) the selected strategies use per-account history
  and per-account profiles fitted on training days that contain the same insiders' earlier
  attacks, and our versions of such features score insider accounts higher on their benign days;
  (2) selection used 180 proposals scored on 10 validation positives, all on accounts that are
  test positives; (3) the two "held-out" corpora have the same insider accounts, threats and
  targets, so transfer to them is not transfer to new insiders. The paper's held-out-account
  table (Table 21) covers fixed monitors, not the search strategies. Measuring the share of the
  gain due to identity needs the strategies' scores, which require model calls and are not
  released. Bias direction if present: **up** (gain and generalization overstated).

## Check 6: one judge (lead ruled out as stated; one narrower inconsistency)

From [`label_checks.json`](label_checks.json):

- All 1,199 label rows have `judge = gpt-4o`. Confidence: mean 0.99, minimum 0.8, 87.5% exactly
  1.0. The release has no second-judge or human columns or files.
- **Ruled out as stated.** The paper does report agreement (Section 2, Appendix E): 18 reviewers,
  538 ratings over 32 account-days, 93.7% exact and 97.4% on completed harm; GPT-5.1 and
  DeepSeek-V3.2 relabel the 306 GPT-5.3 single-day rows with 90.5% agreement on completed harm,
  and swapping in GPT-5.1 labels keeps the classical monitors' ordering. What remains: these
  labels are not released, so they cannot be re-checked, and the second-judge check covers one of
  eight corpora.
- Coverage: the judge script labels only (insider, insider-persona day) cells
  (`scripts/llm_harm_label.py`). In the GPT-5.3 single-day data the 306 persona account-days
  equal the 306 label rows, and no persona session belongs to an account outside the 38. The
  other 112 accounts and insiders' unassigned days are negatives by construction.
- **The 112 never-judged accounts show no harm by simple rules.** Nine rules anchored on the
  threats' targets and attacker addresses from the persona files (Q1 interview share or external
  send, self-add to a group, sealed FIN ticket edits, eval-data deletion or force-push, external
  email of the weight files, corpus `.jsonl` commits, unvetted-checkpoint approval, monitor-config
  commits) hit 0 of 3,319 never-judged account-days and 1 of 817 insider unassigned days
  (frank.s adds itself to the GitLab `infra` group on 2026-05-08; its threat is credential
  exfiltration). Looser first drafts hit benign mentions of model names and README edits; those
  were tightened before the counts above. No rule for threat 07; rules see only the audit log,
  not service state.
- Consistency with the audit log: 143 of 185 executed rows show their threat's rule (29 of the
  42 misses are split-exfiltration rows, where staging is not covered by the rule). 15 of 106
  non-executed rows show it, mostly `attempted`.
- **Inconsistency, collusion accounts only.** In the two-approver release-bypass threat, an
  account's own successful approval of the unvetted checkpoint is labelled `executed` on 49
  account-days, `no_attempt` on 8 and `attempted` on 2, whether or not the partner also approved
  that day. `no_attempt` contradicts an approval in the audit log. The paper's single-day
  analyses (RQ2, RQ3, RQ5) remove collusion accounts, so their headlines are not affected; the
  multiday analyses include collusion and were not checked. Direction: down on monitor recall and
  precision, small.

## Check 1: content-blind baselines (ruled out on the ranking metric)

From [`content_blind_checks.json`](content_blind_checks.json):

| Baseline | AUROC | null p95 | budget-AUC | R@10/day |
|---|---|---|---|---|
| Events per account-day | 0.559 | 0.578 | 0.090 | 0.143 |
| Total bytes returned | 0.671 | 0.567 | 0.093 | 0.200 |
| First / last event time | 0.502 / 0.491 | 0.573 / 0.566 | 0.061 / 0.060 | 0.099 / 0.067 |
| Session turns | 0.576 | 0.578 | 0.090 | 0.156 |
| Input tokens (includes the persona system prompt) | 0.624 | 0.578 | 0.049 | 0.178 |
| Account in the "focal" cohort (org template) | 0.619 | 0.529 | 0.185 | 0.306 |
| Logistic regression on all 15 features, fitted on training days | 0.730 | 0.618 | 0.107 | 0.200 |

No content-blind baseline reaches the median published monitor on R@10/day (0.367) or GPT-5.5's
budget-AUC (0.391). Account metadata (focal cohort; the insider list in check 5) matches GPT-4.1
and beats the three classical monitors, which is the identity effect again. Bytes, input tokens,
focal cohort and the fitted model pass the AUROC flag rule (above the null's 95th percentile and
above 0.6), but the paper uses AUROC only as a diagnostic. Direction where it applies: **up**.

## Not tested

- Any re-scoring of the paper's LLM monitors or search strategies (needs model calls).
- Multiday corpora and the Qwen and DeepSeek corpora, apart from the label census.
- Label agreement itself: the second-judge and human labels are not released.

## Reproduce

```bash
python -I -B check_identity.py --cache data
python -I -B check_labels.py --cache data
python -I -B check_content_blind.py --cache data
```

Downloads from the pins into `data/` about 790 MB: the eight label files, the GPT-5.3 and Kimi-K2.6
single-day audit files, the GPT-5.3 single-day transcripts, and two YAML files from the code commit. Needs numpy, pandas,
pyarrow and scikit-learn. Reads parquet tables and YAML as text; runs no released code.
