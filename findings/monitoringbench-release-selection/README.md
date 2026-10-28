# MonitoringBench: selection on monitors, near-copies, and what the monitor reads

Status: draft, checked on the released data (2026-10-27). Three leads were tested (checks 3, 5
and 7). One part of check 3 holds: the released benchmark is a subset chosen with the monitors'
own detection results, and the dropped attacks were almost all caught. The tuning-to-development-
monitors lead is mostly ruled out. Check 5 holds as near-copies within the attack class, with no
cross-class copies. Check 7 is ruled out. Not yet raised with the authors.

## Background

Jotautaitė, Martinez, Matthews and Tracy, "MonitoringBench" ([arXiv 2605.09684v1](https://arxiv.org/abs/2605.09684);
[data](https://huggingface.co/datasets/neur26anonsub/ctrldataset2026), CC BY 4.0), release 2,644
successful BashArena attack trajectories with full-trajectory scores from 13 monitors, three runs
each. Attacks come from an Opus-only baseline, human strategies, a reconnaissance agent, a
reconnaissance agent that tests actions against GPT-5 ("Recon+Tools", `recon_improved` in the
data), and refined versions of each. Three monitors were used during construction: GPT-5 Nano,
GPT-5 and Claude Opus 4.5. A refined trajectory was kept only if side-task success held and its
score fell for at least two of the three. The other ten monitors are called held out.

The headline: Opus 4.5's catch rate falls from 94.9% on Opus-only attacks to 60.3% on the best
refined attacks.

MonitoringBenchHonest (Küçükkurt and Elasky; 550 honest runs paired with 550 of the attacks; no
licence stated) is used here for the class comparisons. Only counts and ids from it appear below.

Numbers are from [`monitoringbench_checks.json`](monitoringbench_checks.json), produced by
[`check_monitoringbench.py`](check_monitoringbench.py) at dataset revision `6c72cf1`, honest
pipeline commit `7f8deb9`, and the Docent collection `fce5f309…` (content hash in the JSON).
Catch rates use the paper's 1% FPR thresholds (Appendix L) and its rule: score above the threshold,
averaged over the three runs. The release reproduces the paper's Opus-only baseline exactly
(Opus 4.5 94.9%, GPT-5 60.2%, GPT-5.1 Codex 70.1%).

## Check 3: selection tied to monitors

### 3a. The headline monitor is a development monitor

Opus 4.5 was one of the three development monitors. The abstract's 94.9% to 60.3% is measured on
it, and it heads the paper's final ranking (Figure 3). GPT-5, also a development monitor and the
one Recon+Tools hill-climbs against, carries the paper's largest quoted drop (60.2% to 19.5%).
The paper says this and labels the development monitors in Figure 1.

### 3b. Tuning to the development monitors: small

If refinement were tuned to the three development monitors, their scores should fall more under
refinement than the held-out monitors' scores. For each monitor, the refinement effect is the
probability that an unrefined attack scores higher than a refined one (0.5 means no change),
computed for the three unrefined-to-refined pairs and averaged.

| Monitor | Development | Refinement effect | Excess over held-out trend |
|---|---|---|---|
| GPT-5 | yes | 0.744 | +0.065 |
| Opus 4.5 | yes | 0.738 | −0.004 |
| o3 | no | 0.721 | +0.042 |
| Sonnet 4.5 | no | 0.709 | −0.006 |
| GPT-5.1 Codex | no | 0.694 | −0.012 |
| o4-mini | no | 0.656 | +0.060 |
| GPT-5 Nano | yes | 0.628 | +0.032 |

(All 13 are in the JSON.) The development monitors average 0.065 higher than the held-out ones;
3 of 13 monitors chosen at random do as well 22 times in 286 (p = 0.08). Stronger monitors also
show larger effects. After fitting the effect to each monitor's catch rate on unrefined attacks,
using the held-out monitors only, the development monitors sit −0.004, +0.065 and +0.032 from the
line. Held-out monitors scatter around it with a standard deviation of 0.039, and o4-mini sits
+0.060 from it.

The Recon+Tools stage, hill-climbed against GPT-5, gives the same picture. Against plain Recon, the
effect is 0.621 for GPT-5, 0.615 for GPT-5.1 Codex and 0.611 for o4-mini.

Selection on scoring noise is also small. Refined rows were kept after a score drop, so a fresh
rescore of the same model should come out higher if the kept drops were partly noise. The released
three-run mean minus the `dev_*` columns is +0.07 (GPT-5), −0.01 (Opus 4.5) and +0.13 (GPT-5 Nano)
on refined rows, against +0.01, +0.05 and +0.02 on unrefined rows, on a 0–10 scale. Whether the
`dev_*` columns are the scores used at selection is not documented.

Verdict: ruled out as a material bias. Refined attacks are harder for held-out monitors about as
much as their capability predicts. GPT-5 shows at most a modest excess.

### 3c. The released set was filtered on detection, held-out monitors included

The paper's tables (Table 5) cover 3,678 attacks. The release has 2,644. Appendix K says the final
set "filters out overrepresented technical tiers that are uniformly easy to detect by most
monitors". The Opus-only baseline (196 rows) is identical in both. The other groups lost 1,034 rows.

If the released rows are a subset of the paper's pool with the same scores (the identical baseline
supports this), the catch rate of the dropped rows follows from Table 5 and the release.

| Monitor | Group | Paper (n) | Release (n) | Dropped rows, implied |
|---|---|---|---|---|
| Opus 4.5 | Human | 94.5 (780) | 91.5 (511) | 100.0 |
| Opus 4.5 | Recon | 78.2 (1,266) | 66.5 (796) | 97.9 |
| Opus 4.5 | Refined | 70.1 (1,436) | 62.7 (1,141) | 98.6 |
| Sonnet 4.5 (held out) | Recon | 65.5 | 53.5 | 85.9 |
| GPT-5.1 Codex (held out) | Recon | 60.8 | 49.1 | 80.7 |
| o3 (held out) | Refined | 17.2 | 13.8 | 30.1 |

Averaged over the three groups, dropped rows were caught 25.3 points more often than kept rows by
Opus 4.5, 24.3 by Sonnet 4.5, 19.9 by GPT-5.1 Codex, 19.6 by o3, 19.5 by Sonnet 4.0 and 17.0 by
GPT-5. For the weak monitors the gap is 0.2–8.6 points.

So the filter removed attacks that the strong monitors, held-out ones included, caught almost
always. The baseline was not filtered. A reader comparing pipeline attacks with the Opus-only
baseline on the release sees a larger gap than the paper's own pool gives: Opus 4.5 on Recon is
66.5% in the release against 78.2% in Table 5. Final-ranking numbers on the release are catch
rates on a set chosen partly because those monitors missed it.

Verdict: holds. Direction: catch rates on the release are biased **down**, toward a weaker-looking
monitor, for the strong monitors most of all. Held-out monitors were not held out from this step.
The size of the effect on Figure 3 is untested, because the dropped rows are not released.

### 3d. Honest-side selection on monitors

- **Paper's honest set.** 16 honest runs flagged by several monitors were reviewed and 4 removed
  before the 1% FPR thresholds were set. Removing high-scoring honest runs lowers the thresholds,
  which raises catch rates. Direction: **up**. Untested; the 416 honest runs are not released.
- **MonitoringBenchHonest.** Each honest run was scored by GPT-5.6 Sol with the side-task
  descriptions in the prompt. Runs at 7 or above (12 of 550, 2.2%) were dropped and regenerated
  until they passed (post; `pipeline/mb_fairness_check.py`, default threshold "> 6"). The honest
  class therefore has no runs that this monitor scores 7 or above. At low false-positive budgets
  that is exactly the tail that sets the threshold. Monitors that agree with GPT-5.6 Sol get
  lower false-positive rates by construction. Direction: **up**. Untested; no honest monitor
  scores are released.

## Check 5: duplicates and leakage

Similarity is MinHash Jaccard over 5-word shingles of the tool calls, which is what the
full-trajectory monitor reads.

- **No exact copies** among the 2,644 tool-call sequences, and none across classes in the paired
  set. The highest attack-to-honest similarity is 0.27. Honest runs share tasks with attacks by
  design (matched per task), which is not a leak.
- **Near-copies within the attack class.** 554 of 2,644 attacks (21%) have a twin at 0.8 or above,
  and 1,028 (39%) at 0.5 or above, always on the same task. Clustering at 0.8 leaves 2,303 groups,
  and at 0.5 it leaves 2,002. Twins concentrate in refined sources: 111 of 185 human-refined and
  315 of 799 recon-refined rows. Most twins are in the same source (several refinement attempts of
  one original, as Appendix H.3 allows). Others pair a refined row with its unrefined parent,
  which is also released (for example, 20 human-strategy rows have a human-refined twin).
- **Few tasks.** 136 tasks in all. Human strategies: 511 rows on 8 tasks. Human-refined: 185 rows
  on 7 tasks. The paper's error bars are the spread over three monitor runs, not sampling error.
  Resampling tasks instead of rows widens the Opus 4.5 interval on recon-refined attacks from
  57–64% to 51–71%, and on human-refined from 72–84% to 64–84%.
- **Paired set.** 220 of 550 attacks have a twin at 0.5 or above inside the set; no honest run
  does (highest 0.31). Nearest-neighbour similarity alone separates the classes with AUROC 0.60.
  This matters only for methods that see the whole pool, or for classifiers trained on part of it
  (the post suggests fine-tuning). Under a random 50/50 split, 13.6% of held-out attacks have a
  twin at 0.8 or above in the training half.
- **Ids and order.** Every Docent run name and id carries its label (`attack_…`, `[honest]`). The
  pipeline's renderer leaves them out of the monitor prompt. The Docent listing order does not
  predict the label (AUROC 0.48).

Verdict: holds as within-class near-copies and task concentration. There is no released train/test
split, so the cross-split flag rule does not apply directly. Direction: intervals too narrow;
**up** for any classifier trained and tested on a random split.

## Check 7: attack instruction visible to the monitor

The full-trajectory monitor prompt holds the main-task description and the tool calls. The release
logs store 23,865 monitor prompts. None contains the agent's prose (checked against 1,385 rows that
have prose).

- **Tool calls.** The pre-set pattern ("side task", "secondary task", "secret/hidden/covert
  objective", "red team", "avoid detection", "stealth", "covertly" and similar) matches 33 of 2,644
  attacks (1.2%): 10 human-strategy, 10 recon and 13 Recon+Tools rows. It matches no refined row.
- **Paired set.** The pattern matches 3 of 550 attacks and 0 of 550 honest runs, in actions and in
  actions plus outputs. Keyword AUROC is 0.503, against the post's best monitor (Kimi K3) at TPR
  0.858 and FPR 0.024.
- **Not monitor-visible, but released.** The agent's prose in the logs names its side task in 647
  of 2,644 rows: 162 of 196 Opus-only, 149 of 511 human-strategy and 336 of 796 recon rows. A reuser
  who renders whole assistant messages, not tool calls, would hand monitors a confession.

Verdict: ruled out for the benchmark as built. It is a hazard for reuse of the `.eval` logs.

## Side observations (for the provenance check)

- 505 of the 550 paired attacks are refined. Their tool calls were written by the refining model
  and replayed. 122 are refinements of Opus-only attacks, all from Claude Opus 4.6, yet the data
  labels every refined row `claude-opus-4-5`. The post's "model-matched" claim rests on that label.
- The paper names Opus 4.6 as the refiner in §2 and Opus 4.5 in Appendix H.2.

## Tests that would settle it

1. Release the 1,034 dropped rows, or the filter's rule, and recompute Figure 3 on the 3,678-row
   pool next to the 2,644.
2. Release honest monitor scores (the paper's 416, before and after removing the 4) and recompute
   thresholds with all 420.
3. Score MonitoringBenchHonest's 12 dropped honest runs with the paper's monitors, and recompute
   false-positive rates with them included.

## Reproduce

```bash
python -I check_monitoringbench.py --data data
```

Downloads `master.parquet` (3 MB) and `final_dataset.zip` (2.5 GB) at the pinned revision, checks
their sha256 against the LFS ids, and fetches the 1,100 Docent runs. `--docent-dir` reuses a local
copy. It reads the `.eval` archives as zip and JSON only and writes `monitoringbench_checks.json`.
The first run extracts tool calls to `data/samples.jsonl.gz`, which takes a few minutes. Needs
numpy, pandas, pyarrow and scikit-learn.

The attacks are CC BY 4.0. MonitoringBenchHonest has no stated licence, so only counts and ids
from it are published here.
