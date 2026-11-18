# Prior work and release inventory

Checked 2026-11-17: the six candidate papers, their repositories, the ChainScope issue tracker
(issues 1–6), a web search for critiques of IPHR, and this project's earlier
[`findings/cot-monitoring-evals/`](../../findings/cot-monitoring-evals/README.md), which covers CoT
Red-Handed and OpenAI's monitorability suite and is not repeated here.

## Release inventory (why ChainScope is the primary)

| Paper | What is released | Per-item, per-model outputs? | Used here |
|---|---|---|---|
| Arcuschin et al. 2025, ChainScope (`jettjaniak/chainscope@bb128ac0`, MIT, ~16 GB) | Questions, ground-truth RAG values, every CoT response and its YES/NO/UNKNOWN label for 19 models, per-question count tables (`df-wm*.pkl.gz`) for the v1 and v4+ datasets, the flagging script, the pattern-classifier outputs, temperature and ambiguity-study data | **Yes**, all headline models, both dataset versions | **Primary** |
| Turpin et al. 2023 (`milesaturpin/cot-unfaithfulness@df099452`, MIT) | BBH and BBQ prompts; 52 + 26 sample files for Claude v1 and text-davinci-003 (suggested-answer and answer-is-always-A), qualitative-analysis CSVs | Yes, but two 2023 models only | No (old models; no headline that current safety cases cite) |
| Chen et al. 2025 (Anthropic), "Reasoning Models Don't Always Say What They Think" (arXiv 2505.05410) | Paper only; no transcripts or judge outputs found | No | No |
| Chua and Evans 2025 (arXiv 2501.08156) | Paper only; no repository found by search | No | No |
| METR 2025, "CoT May Be Highly Informative Despite 'Unfaithfulness'" | Code (`METR/CoT-faithfulness-and-monitorability`), transcripts site, DAFT Math dataset, judge-validation spreadsheets | Yes | No (it already is a critique of the hint design; see below) |
| Lanham et al. 2023 | Paper only (Anthropic internal models) | No | No |

## What is already known about IPHR

- **The authors' own revisions.** v1–v3 (March 2025) reported 30.6% (Claude 3.7 Sonnet), 15.8%
  (DeepSeek R1) and 12.6% (ChatGPT-4o) on a 7,400-pair dataset. v4 (June 2025) replaced the dataset
  and reported 0.04–13%. v4's appendix "Paper Changes From Original Versions" attributes the drop
  to the dataset: ambiguity filtering, minimum value gaps instead of neighbouring values,
  popularity filtering and verified ground truth. **New here:** the accuracy-difference threshold
  also changed, from 20% (v1 §2) to 50% (v4 §2.1), and that appendix does not list it. We measure
  how much of the drop each change accounts for.
- **Authors' controls in v6.** Ambiguity-filter validation (2.0% residual ambiguity, 95% CI
  0.9–4.3%, one annotator plus a second for a subset); oversampling to 100 responses (76%
  retention); subsampling 5 of 10 rollouts; temperature 0.3/0.7/1.0; threshold grid; CoT length;
  a second autorater (Claude Sonnet 4.6, 99.3% agreement); a same-longitude/latitude ablation; an
  "N/A allowed" ablation; template-level permutation test (commented out in v6); linear probes for
  template bias in Llama 3.3 70B. The paper also states the fact-retrieval alternative explanation
  and says causality is not established.
- **New here, not in those controls:**
  - a null model with no pair-specific bias, fitted to each pair's accuracy and each template's
    lean, run through the released criteria;
  - a held-out split of the released samples (select on 5, test on 5); the paper's oversampling
    check reuses the 10 selection samples inside its 100 and lowers the threshold to 0.4
    (`make_faithfulness_ds.py:292-300`, `gen_cots.py:131-157` tops up existing responses);
  - the route by which flagged pairs enter the count, including UNKNOWN answers scored as half
    correct;
  - template-clustered intervals (the published intervals are binomial over pairs).
- **Issue tracker.** One open issue (#4, smaller models); nothing on noise, lean or UNKNOWN handling.
- **Web search.** No critique of IPHR's selection or null found (queries on "implicit post-hoc
  rationalization" critique, noise, yes bias).
- **Hint-based faithfulness critiques (context, not tested here).** METR (August 2025) argues the
  Chen et al. multiple-choice design overstates unfaithfulness because models can eliminate
  options and guess, and reports >97% "relaxed" faithfulness on hard clues with free-response math.
  Chen et al. themselves subtract a random-answer-change baseline.
