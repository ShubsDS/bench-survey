# Prior work

Searched 2026-11-17: the paper, the anthropics/evals issues and pull requests, the Hugging Face
dataset discussions, LessWrong, arXiv, and the steering-reliability and LLM-questionnaire
literatures. Items marked "not re-read" were summarised from search results or memory and are
not relied on for any claim.

## On these files

| Source | What it already showed | Bearing on this audit |
|---|---|---|
| Perez et al. 2022, §5.2 ([ar5iv](https://ar5iv.labs.arxiv.org/html/2212.09251)) | LM-written advanced-AI-risk sets were generated twice, once with "(A)" and once with "(B)" as the behaviour answer, and combined into a balanced set; LM-written labels judged correct 93% of the time (§5.3). | Balances letter position only. Nothing found on the Yes/No direction of the key or on acquiescence. Appendices not fully read. |
| [anthropics/evals PR #3](https://github.com/anthropics/evals/pull/3) (open) | Duplicate rows, rows keyed beyond (B), 13 inverted sycophancy keys. | No mention of yes-bias or of the advanced-AI-risk key direction. The issues page shows no issues. |
| [HF discussions](https://huggingface.co/datasets/Anthropic/model-written-evals/discussions) | One thread on two identical files. | Nothing on keys or yes-bias. |
| Dev and Hobbhahn, "Improving Model-Written Evals for AI Safety Benchmarking", LessWrong, 2024-10-15 | Power- and wealth-seeking answer keys inverted (no counts, version unstated). | Key direction only. Validator's addition: their linked code ([Sunishchal/model-written-evals@65eb2fae](https://github.com/Sunishchal/model-written-evals), `utils.py:99-103`) swaps the key for both the human-written and LM-written power and wealth files. |
| [`findings/model-written-evals-inverted-labels/`](../../findings/model-written-evals-inverted-labels/) (this project) | Crowdworker survival, power and wealth keyed to the safe answer (validated); "always Yes" scores 0.79–0.93 on coordination and corrigibility (L2); CAA survival measures shutdown acceptance. | The starting point. It did not test whether any model's score or any steering effect follows the Yes key. |

## On steering vectors built from these files

**Tan et al. 2024**, "Analyzing the Generalization and Reliability of Steering Vectors", NeurIPS
2024 ([arXiv 2407.12404](https://arxiv.org/abs/2407.12404), §3, §5, Figs. 3, 4, 16). The closest
prior work.
- Uses Llama-2-7b-Chat and Qwen-1.5-14b-Chat on about 40 MWE datasets. The advanced-AI-risk
  sets are the **LM-written** versions (checked: every question in `repepo/raw_datasets/mwe/xrisk/`
  matches the LM-written file, apart from a few shared with crowdworker files).
- Randomises "whether 'A' or 'B' (and 'Yes' or 'No' where appropriate)" is the positive option.
- §5: the A/B and Yes/No splits "are often highly predictive of the steerability, explaining a
  large part of the variance in per-example steerability"; Fig. 3 caption: "a general trend
  towards preferring 'Yes' vs 'No'". It calls this a *steerability bias*: vectors move some
  items more than others depending on the position or token of the positive answer.
- It does not say that the source files are 92–99% Yes-keyed, does not decompose a published
  propensity level or a published CAA effect into a Yes part and a disposition part, and does not
  report numbers in the text (only bar charts).

**What is new here relative to Tan et al.** (i) The baseline propensity levels, not only
steerability; (ii) the specific CAA Table 3 and Table 10 numbers recomputed on Yes-keyed and
No-keyed halves from CAA's own released per-item outputs, with intervals; (iii) an intervention
(negated minimal pairs) rather than a variance decomposition over naturally occurring splits;
(iv) the CAA scorer giving zero credit to items keyed (C) or (E).

**Others checked.** Braun et al. 2025, "Understanding (Un)Reliability of Steering Vectors"
([arXiv 2505.22637](https://arxiv.org/abs/2505.22637)): MWE, Llama-2-7B-Chat; no discussion of
yes-bias or A/B bias found. Pres et al. 2024 ([arXiv 2410.17245](https://arxiv.org/abs/2410.17245)):
multiple-choice steering success need not carry to open-ended generation (a CAA corrigibility
example, App. D); no answer-bias analysis. Im and Li 2025
([arXiv 2502.02716](https://arxiv.org/abs/2502.02716)): abstract only, nothing on answer bias.
CAA itself (§3.2) notes activations cluster by answer letter; it does not discuss yes-bias.

## Acquiescence and response bias in LLM questionnaires

- Dentella, Günther and Leivada, PNAS 2023: a yes-response bias in grammaticality judgements of
  GPT-3 and ChatGPT; Hu et al., PNAS 2024 rebut it for all but one model.
- Dominguez-Olmedo, Hardt and Mendler-Dünner, NeurIPS 2024
  ([arXiv 2306.07951](https://arxiv.org/abs/2306.07951)): survey answers of 43 models are driven
  by ordering and labelling biases (an "A" bias); with orders randomised, answers approach
  uniform.
- D. Braun, Findings of EMNLP 2025 ([arXiv 2509.08480](https://arxiv.org/abs/2509.08480)): LLMs
  lean toward "no", not "yes", so human acquiescence does not simply transfer. A reason not to
  assume the direction of the bias.
- Not re-read: Tjuatja et al., TACL 2024 (models do not reproduce human survey response biases
  consistently); Röttger et al., ACL 2024 (forced-choice answers on the Political Compass shift
  under paraphrase); Zheng et al., ICLR 2024 (option-ID "token bias" in multiple choice).

## Summary: known versus new

Known qualitatively: multiple-choice LLM answers carry position and token biases, and steering
vectors on MWE are more effective on some Yes/No and A/B splits than on others (Tan et al.).
Not found anywhere: whether published MWE propensity levels or the published CAA effect sizes
survive on the No-keyed items, by how much, and whether negating the question flips a model's
answer. That is the contribution tested here. A null result would be reported as such.
