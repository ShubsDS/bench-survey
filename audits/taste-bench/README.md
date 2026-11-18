# Taste-Bench: which option is the shown trajectory's own next step predicts the label

Status 2026-11-17. Round two. Not yet independently validated. The dataset gate was opened by the
repository owner during the audit; everything item-level was pre-registered first
([`prereg.md`](prereg.md), amendment 1, commit `6e3a776`, before the parquet files were
downloaded). Inference: Claude Haiku only, see "Inference".

**Bottom line.** Taste-Bench's construction leaves the answer readable from where each option
came from. In parallel forks the correct option is the shown trajectory's own next step; in
detour forks the *wrong* option is. A rule that never reads the substance — pick the option
whose words overlap more with the end of the prefix in parallel cells, less in detour cells —
scores a 60.4 Average (61.4 on held-out tasks), above every published model (best 59.7).
On detour engineering, "pick the option less grounded in the prefix" scores 61.7% against a best
published 48.1%, and half the published models are below 50% single-order there: they choose the
option the agent actually took. The paper reads the detour–parallel gap as "recognising a
mistake before the acting agent did"; the data fit "the label is the option the prefix does not
lead to" at least as well. Several narrower conclusions also move (below).

| Claim | Level | One line |
|---|---|---|
| C1 Label predictable from option origin (prefix overlap), signs opposite by construction | **L2** | held-out 65.9% parallel, 34.2% detour; floor Average 60.4 > 59.7 |
| C2 Published per-cell pattern tracks it (detour engineering below chance) | **L3 at cell level only; L4 for Haiku** | see "The effect"; per-item published logs are not released |
| C3 Unparsed replies change published ranks | **L3** | GLM-5.2 passes 3 models; Grok 4.20 is above chance among parsed replies |
| C4 "Detour harder than parallel in both domains" | fails in research | model-mean −0.1 points; 7 of 14 models |
| C5 Ranking precision | **L3** | same model and setting differs by 2.6 points between two paper runs, more than 8 of 13 adjacent gaps |
| C6 Horizon gradient is cell composition | **R** | composition predicts 3.6 of a 41.3-point gap |
| C7 Taste vs SWE-bench driven by the construction models | **R** | dropping GPT-5.6 Sol and GPT-5.5 gives r = 0.69 (69th percentile of drop-two) |
| C8 Options-only signal survives the filter | **L2 (paper's own numbers)** | GPT-4.1 from options alone 63.7% on released P-Eng ≥ 4 of 14 models |
| C9 Human review cannot test what it is cited for; end-to-end numbers not whole-task rates | L1 | arithmetic on published counts |

HAIKU_PLACEHOLDER
